#!/usr/bin/env python3
"""Scaffold a wiki page with schema-valid frontmatter.

Usage:
    python new_page.py --wiki-root wiki --type source --title "LLM Wiki Gist" \
        --sources "llm-wiki-gist.md" --tags "knowledge-management,agents"

Rules encoded here (keep in sync with CLAUDE.md — same commit on schema change):
  - type -> directory: source->sources/, entity->entities/, concept->concepts/, note->notes/
  - source pages get a YYYY-MM-DD- filename prefix (ingest date)
  - filenames are kebab-case ASCII slugs
  - required frontmatter: type, title, created, updated, sources, tags, status
Prints the created path on stdout. Refuses to overwrite an existing page.
"""

import argparse
import datetime
import re
import sys
import unicodedata
from pathlib import Path

TYPE_DIR = {"source": "sources", "entity": "entities",
            "concept": "concepts", "note": "notes"}


def slugify(title: str) -> str:
    s = unicodedata.normalize("NFKD", title)
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        sys.exit("ERROR: title produced an empty slug (non-ASCII title?). "
                 "Pass an explicit --slug with an ASCII transliteration.")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wiki-root", default="wiki")
    ap.add_argument("--type", required=True, choices=sorted(TYPE_DIR))
    ap.add_argument("--title", required=True)
    ap.add_argument("--slug", help="override the auto-generated slug")
    ap.add_argument("--sources", default="",
                    help="comma-separated raw-source slugs backing this page")
    ap.add_argument("--tags", default="", help="comma-separated tags")
    ap.add_argument("--status", default="current",
                    choices=["current", "needs-review", "superseded"])
    args = ap.parse_args()

    root = Path(args.wiki_root)
    if not root.is_dir():
        sys.exit(f"ERROR: wiki root '{root}' not found — run from the repo root, "
                 "or pass --wiki-root.")

    today = datetime.date.today().isoformat()
    slug = args.slug or slugify(args.title)
    if args.type == "source" and not re.match(r"\d{4}-\d{2}-\d{2}-", slug):
        slug = f"{today}-{slug}"

    page_dir = root / TYPE_DIR[args.type]
    page_dir.mkdir(parents=True, exist_ok=True)
    path = page_dir / f"{slug}.md"
    if path.exists():
        sys.exit(f"ERROR: {path} already exists. Update the existing page instead; "
                 "if this is a deliberate re-ingest, edit it rather than recreating.")

    def yaml_list(csv: str) -> str:
        items = [x.strip() for x in csv.split(",") if x.strip()]
        return "[" + ", ".join(items) + "]"

    fm = (
        "---\n"
        f"type: {args.type}\n"
        f"title: {args.title}\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"sources: {yaml_list(args.sources)}\n"
        f"tags: {yaml_list(args.tags)}\n"
        f"status: {args.status}\n"
        "---\n\n"
        f"# {args.title}\n\n"
        "<!-- body: see wiki-ingest references/page-templates.md -->\n"
    )
    path.write_text(fm, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
