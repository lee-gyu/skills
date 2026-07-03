#!/usr/bin/env python3
"""Extract clean markdown text from a raw source file (.md, .txt, .html, .pdf).

Usage:
    python extract_source.py raw/some-article.html --out /tmp/extracted.md

Prints a short report (format detected, char count, images referenced) to stdout.
Never writes anywhere under raw/. Exits non-zero with a clear message when it
cannot extract reliably — the calling agent should then read the file directly
and mention the fallback in its ingest report.
"""

import argparse
import html
import html.parser
import re
import sys
import unicodedata
from pathlib import Path


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Stdlib-only HTML -> text with minimal structure preservation."""

    SKIP = {"script", "style", "noscript", "template", "head", "nav", "footer"}
    BLOCK = {"p", "div", "section", "article", "li", "br", "tr",
             "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.images = []
        self._skip_depth = 0
        self._heading = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "img":
            src = dict(attrs).get("src", "")
            if src:
                self.images.append(src)
                self.parts.append(f"\n![image]({src})\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = int(tag[1])
            self.parts.append("\n\n" + "#" * self._heading + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in self.BLOCK:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = None
            self.parts.append("\n")
        elif tag in self.BLOCK and not self._skip_depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth and data:
            self.parts.append(data)

    def text(self):
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def extract_html(data: bytes) -> tuple[str, list[str]]:
    text = data.decode("utf-8", errors="replace")
    parser = _HTMLTextExtractor()
    parser.feed(text)
    return parser.text(), parser.images


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            sys.exit(
                "ERROR: no PDF library available (tried pypdf, PyPDF2).\n"
                "Fallback: read the PDF directly with your own tools, or "
                "`pip install pypdf` and retry."
            )
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        t = page.extract_text() or ""
        pages.append(f"<!-- page {i} -->\n{t}")
    text = "\n\n".join(pages)
    # Heuristic: a text layer that is mostly empty means a scanned PDF.
    alnum = sum(c.isalnum() for c in text)
    if alnum < 50 * max(1, len(reader.pages)):
        sys.exit(
            f"ERROR: extracted only {alnum} alphanumeric chars from "
            f"{len(reader.pages)} pages — likely a scanned/image PDF. "
            "Fallback: view the PDF pages directly (it is an image source), "
            "and note in the ingest report that content came from visual reading."
        )
    return text


def quality_gate(text: str, label: str) -> None:
    """Refuse to hand the agent garbage it might confidently summarize."""
    if len(text.strip()) < 80:
        sys.exit(f"ERROR: extraction from {label} produced almost no text "
                 f"({len(text.strip())} chars). Read the file directly instead.")
    bad = sum(1 for c in text if unicodedata.category(c) == "Co" or c == "\ufffd")
    if bad / max(1, len(text)) > 0.01:
        sys.exit(f"ERROR: extraction from {label} looks like mojibake "
                 f"({bad} replacement/private chars). Check the file's encoding; "
                 "do not summarize this output.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="path to the raw source file")
    ap.add_argument("--out", help="write extracted markdown here (default: stdout)")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_file():
        sys.exit(f"ERROR: {src} is not a file.")
    if args.out and Path(args.out).resolve().is_relative_to(
            (src.parent if src.parent.name == "raw" else src).resolve().parent / "raw"):
        sys.exit("ERROR: refusing to write under raw/ — it is immutable.")

    suffix = src.suffix.lower()
    images: list[str] = []
    if suffix in (".md", ".markdown", ".txt"):
        text = src.read_bytes().decode("utf-8", errors="replace")
        images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
        kind = "text/markdown (passthrough)"
    elif suffix in (".html", ".htm"):
        text, images = extract_html(src.read_bytes())
        kind = "html"
    elif suffix == ".pdf":
        text = extract_pdf(src)
        kind = "pdf (text layer)"
    else:
        sys.exit(f"ERROR: unsupported extension '{suffix}'. "
                 "Read the file directly with your own tools.")

    quality_gate(text, src.name)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        dest = args.out
    else:
        print(text)
        dest = "stdout"

    report = [f"OK: {src.name} [{kind}] -> {dest}",
              f"  chars: {len(text)}"]
    if images:
        report.append(f"  images referenced ({len(images)}): " + ", ".join(images[:10])
                      + (" ..." if len(images) > 10 else ""))
    print("\n".join(report), file=sys.stderr)


if __name__ == "__main__":
    main()
