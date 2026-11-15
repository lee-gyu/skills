#!/usr/bin/env python3
"""EPUB을 AI 에이전트가 읽기 쉬운 Markdown 파일들로 변환한다.

사용법:
    python epub-to-md.py book.epub [-o OUTPUT_DIR] [--max-chars N] [--images] [--force]

출력 (기본: .output/{filename-id}/converted/):
    index.md        메타데이터, 파일 목록, 원본 목차
    NNN-{제목}.md   목차 항목이 가리키는 문서 단위로 나눈 섹션
    images/         --images 지정 시 추출한 그림
"""

from __future__ import annotations

import argparse
import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urldefrag
from xml.etree import ElementTree

from _common import VENV_HINT, Section, clean_markdown, fail, resolve_output_dir, write_output

try:
    from bs4 import BeautifulSoup
    from markdownify import MarkdownConverter
except ImportError as error:
    fail(f"필요한 패키지를 불러올 수 없습니다 ({error}). {VENV_HINT}")

Toc = list[tuple[int, str, str]]  # (level, 제목, zip 내부 문서 경로)
DC_FIELDS = {"title": "제목", "creator": "저자", "publisher": "출판사", "language": "언어", "date": "발행일"}


def local(tag: str) -> str:
    """XML 네임스페이스를 뗀 태그 이름."""
    return tag.rsplit("}", 1)[-1]


def resolve(base: str, href: str) -> str:
    """base 문서 기준 상대 href를 zip 내부 경로로 바꾼다 (#fragment는 버린다)."""
    path = unquote(urldefrag(href)[0])
    if not path:
        return base
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), path))


def read_package(book: zipfile.ZipFile):
    """OPF에서 메타데이터, manifest, 읽기 순서(spine)를 읽는다."""
    container = ElementTree.fromstring(book.read("META-INF/container.xml"))
    opf_path = next(el.get("full-path") for el in container.iter() if local(el.tag) == "rootfile")
    opf = ElementTree.fromstring(book.read(opf_path))

    meta: dict[str, list[str]] = {}
    manifest: dict[str, tuple[str, str, str]] = {}  # id -> (경로, media-type, properties)
    spine_ids: list[str] = []
    ncx_id = None
    for el in opf.iter():
        name = local(el.tag)
        if name in DC_FIELDS and "purl.org/dc" in el.tag and (el.text or "").strip():
            meta.setdefault(DC_FIELDS[name], []).append(el.text.strip())
        elif name == "item" and el.get("href"):
            path = resolve(opf_path, el.get("href"))
            manifest[el.get("id")] = (path, el.get("media-type", ""), el.get("properties", ""))
        elif name == "spine":
            ncx_id = el.get("toc")
        elif name == "itemref":
            spine_ids.append(el.get("idref"))

    spine = [manifest[i][0] for i in spine_ids if i in manifest and "html" in manifest[i][1]]
    info = {key: ", ".join(dict.fromkeys(values)) for key, values in meta.items()}
    return info, manifest, spine, ncx_id


def read_toc(book: zipfile.ZipFile, manifest: dict, ncx_id: str | None) -> Toc:
    """EPUB3 nav 문서 또는 EPUB2 NCX에서 목차를 읽는다."""
    toc: Toc = []
    nav_path = next((path for path, _, props in manifest.values() if "nav" in props.split()), None)
    if nav_path:
        soup = BeautifulSoup(book.read(nav_path), "html.parser")
        nav = soup.find("nav", attrs={"epub:type": "toc"}) or soup.find("nav")
        top = nav.find("ol") if nav else None

        def walk_nav(ol, level: int) -> None:
            for li in ol.find_all("li", recursive=False):
                label = li.find(["a", "span"], recursive=False)
                if label and label.get_text(strip=True):
                    href = label.get("href")
                    path = resolve(nav_path, href) if href else ""
                    toc.append((level, " ".join(label.get_text().split()), path))
                child = li.find("ol", recursive=False)
                if child:
                    walk_nav(child, level + 1)

        if top:
            walk_nav(top, 1)
    if toc:
        return toc

    ncx_path = manifest[ncx_id][0] if ncx_id in manifest else None
    ncx_path = ncx_path or next((p for p, kind, _ in manifest.values() if "dtbncx" in kind), None)
    if not ncx_path:
        return toc
    ncx = ElementTree.fromstring(book.read(ncx_path))

    def walk_ncx(node, level: int) -> None:
        for point in node:
            if local(point.tag) != "navPoint":
                continue
            label = next((el for el in point if local(el.tag) == "navLabel"), None)
            text = " ".join("".join(label.itertext()).split()) if label is not None else ""
            src = next((el.get("src", "") for el in point if local(el.tag) == "content"), "")
            if text:
                toc.append((level, text, resolve(ncx_path, src) if src else ""))
            walk_ncx(point, level + 1)

    for nav_map in ncx.iter():
        if local(nav_map.tag) == "navMap":
            walk_ncx(nav_map, 1)
    return toc


def encrypted_paths(book: zipfile.ZipFile) -> set[str]:
    try:
        root = ElementTree.fromstring(book.read("META-INF/encryption.xml"))
    except KeyError:
        return set()
    return {unquote(el.get("URI", "")) for el in root.iter() if local(el.tag) == "CipherReference"}


def save_image(book: zipfile.ZipFile, path: str, image_dir: Path, saved: dict[str, str]) -> str | None:
    """zip 안의 그림을 image_dir에 저장하고 파일 이름을 돌려준다."""
    if path not in saved:
        try:
            data = book.read(path)
        except KeyError:
            return None
        name = re.sub(r"[^\w.\-]", "_", posixpath.basename(path))
        if name in saved.values():
            name = f"{len(saved)}-{name}"
        image_dir.mkdir(exist_ok=True)
        (image_dir / name).write_bytes(data)
        saved[path] = name
    return saved[path]


def to_markdown(book: zipfile.ZipFile, path: str, image_dir: Path | None, saved: dict[str, str]):
    """XHTML 문서 하나를 (첫 제목, Markdown)으로 변환한다."""
    soup = BeautifulSoup(book.read(path), "html.parser")
    body = soup.body or soup
    for tag in body.find_all(["script", "style", "svg", "head"]):
        tag.decompose()
    for link in body.find_all("a"):  # 책 내부 링크는 변환 후 깨지므로 텍스트만 남긴다
        if not re.match(r"(https?|mailto):", link.get("href", "")):
            link.unwrap()
    for img in body.find_all("img"):
        alt = (img.get("alt") or "").strip()
        name = save_image(book, resolve(path, img.get("src", "")), image_dir, saved) if image_dir else None
        if name:
            img["src"] = f"images/{name}"
        else:
            img.replace_with(f"[그림: {alt}]" if alt else "")

    heading = body.find(re.compile(r"^h[1-6]$"))
    title = " ".join(heading.get_text().split()) if heading else ""
    markdown = MarkdownConverter(heading_style="ATX", bullets="-").convert_soup(body)
    return title, clean_markdown(markdown).strip()


def split_text(text: str, max_chars: int) -> list[str]:
    """max_chars를 넘는 텍스트를 문단 경계에서 나눈다. 절반 이상 찼으면 제목 앞에서 끊는다."""
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    buffer: list[str] = []
    size = 0
    for block in text.split("\n\n"):
        at_heading = block.startswith("#") and size > max_chars // 2
        if buffer and (size + len(block) > max_chars or at_heading):
            parts.append("\n\n".join(buffer))
            buffer, size = [], 0
        buffer.append(block)
        size += len(block) + 2
    if buffer:
        parts.append("\n\n".join(buffer))
    return parts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EPUB을 Markdown 파일들로 변환한다.")
    parser.add_argument("input", help="변환할 EPUB 파일")
    parser.add_argument("-o", "--output", help="출력 폴더 (기본: .output/{filename-id}/converted)")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=60000,
        help="파일 하나에 담을 최대 글자 수. 0이면 섹션을 더 나누지 않는다 (기본: 60000)",
    )
    parser.add_argument("--images", action="store_true", help="그림을 images/ 폴더에 추출한다")
    parser.add_argument("--force", action="store_true", help="이전 변환 결과를 지우고 다시 변환한다")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.input)
    if not source.is_file():
        fail(f"파일을 찾을 수 없습니다: {source}")
    try:
        book = zipfile.ZipFile(source)
    except zipfile.BadZipFile:
        fail(f"올바른 EPUB 파일이 아닙니다: {source}")

    with book:
        try:
            info, manifest, spine, ncx_id = read_package(book)
            toc = read_toc(book, manifest, ncx_id)
        except (KeyError, StopIteration, ElementTree.ParseError) as error:
            fail(f"EPUB 구조를 읽을 수 없습니다: {error!r}")
        if encrypted_paths(book) & set(spine):
            fail("DRM으로 암호화된 EPUB입니다. DRM이 없는 파일만 변환할 수 있습니다.")

        out_dir = resolve_output_dir(source, args.output, args.force)
        image_dir = out_dir / "images" if args.images else None
        saved: dict[str, str] = {}

        titles: dict[str, str] = {}
        for _, title, path in toc:
            if path:
                titles.setdefault(path, title)

        # 목차 항목이 가리키는 문서에서 새 섹션을 시작하고, 나머지 문서는 앞 섹션에 이어 붙인다.
        groups: list[tuple[str, list[str]]] = []
        for path in spine:
            heading, markdown = to_markdown(book, path, image_dir, saved)
            if not markdown:
                continue
            if path in titles or not titles or not groups:
                groups.append((titles.get(path) or heading or posixpath.basename(path), [markdown]))
            else:
                groups[-1][1].append(markdown)

    sections = []
    for title, texts in groups:
        parts = split_text("\n\n".join(texts), args.max_chars)
        for i, part in enumerate(parts, 1):
            name = title if len(parts) == 1 else f"{title} ({i}/{len(parts)})"
            sections.append(Section(name, part))

    meta = {"제목": info.get("제목") or source.stem}
    meta.update({key: value for key, value in info.items() if key != "제목"})
    write_output(out_dir, source, "epub-to-md.py", meta, sections, [(l, t, "") for l, t, _ in toc])


if __name__ == "__main__":
    main()
