#!/usr/bin/env python3
"""PDF를 AI 에이전트가 읽기 쉬운 Markdown 파일들로 변환한다.

사용법:
    python pdf-to-md.py book.pdf [-o OUTPUT_DIR] [--max-pages N] [--no-toc] [--images] [--force]

출력 (기본: .output/{filename-id}/converted/):
    index.md        메타데이터, 파일 목록, 원본 목차
    NNN-{제목}.md   목차(북마크) 기준으로 나눈 섹션. 각 페이지 앞에 <!-- page: N --> 표시
    images/         --images 지정 시 추출한 그림
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

from _common import VENV_HINT, Section, fail, resolve_output_dir, write_output

try:
    import pymupdf
    import pymupdf4llm
except ImportError as error:
    fail(f"pymupdf를 불러올 수 없습니다 ({error}). {VENV_HINT}")

Range = tuple[str, int, int]  # (제목, 첫 페이지, 마지막 페이지), 페이지는 1부터


def split_by_pages(title: str, first: int, last: int, max_pages: int) -> list[Range]:
    """페이지 범위를 max_pages 이하의 비슷한 크기로 나눈다."""
    count = last - first + 1
    parts = math.ceil(count / max_pages)
    if parts <= 1:
        return [(title, first, last)]
    size = math.ceil(count / parts)
    starts = range(first, last + 1, size)
    return [
        (f"{title} ({i}/{len(starts)})", start, min(start + size - 1, last))
        for i, start in enumerate(starts, 1)
    ]


def split_by_toc(
    toc: list[tuple[int, str, int]], first: int, last: int, level: int, title: str, max_pages: int
) -> list[Range]:
    """페이지 범위를 목차 기준으로 나눈다.

    max_pages를 넘는 범위만 한 단계 더 깊은 목차 항목으로 쪼개고,
    더 깊은 항목이 없으면 페이지 수로 나눈다.
    """
    if last - first + 1 <= max_pages:
        return [(title, first, last)]
    inner = [entry for entry in toc if entry[0] > level and first <= entry[2] <= last]
    if not inner:
        return split_by_pages(title, first, last, max_pages)

    sub_level = min(entry[0] for entry in inner)
    starts: dict[int, str] = {}
    for entry_level, entry_title, page in inner:
        if entry_level == sub_level:
            starts.setdefault(page, entry_title)
    pages = sorted(starts)

    ranges: list[Range] = []
    if pages[0] > first:  # 첫 하위 항목 앞에 남는 페이지
        lead_title = "앞부분" if level == 0 else title
        ranges += split_by_pages(lead_title, first, pages[0] - 1, max_pages)
    for i, page in enumerate(pages):
        end = pages[i + 1] - 1 if i + 1 < len(pages) else last
        ranges += split_by_toc(toc, page, end, sub_level, starts[page], max_pages)
    return ranges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PDF를 Markdown 파일들로 변환한다.")
    parser.add_argument("input", help="변환할 PDF 파일")
    parser.add_argument("-o", "--output", help="출력 폴더 (기본: .output/{filename-id}/converted)")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=30,
        help="파일 하나에 담을 최대 페이지 수. 0이면 나누지 않는다 (기본: 30)",
    )
    parser.add_argument("--no-toc", action="store_true", help="목차를 무시하고 페이지 수로만 나눈다")
    parser.add_argument("--images", action="store_true", help="그림을 images/ 폴더에 추출한다")
    parser.add_argument("--force", action="store_true", help="이전 변환 결과를 지우고 다시 변환한다")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.input)
    if not source.is_file():
        fail(f"파일을 찾을 수 없습니다: {source}")
    try:
        doc = pymupdf.open(source)
    except Exception as error:
        fail(f"PDF를 열 수 없습니다: {error}")
    if not doc.is_pdf:
        fail(f"PDF 파일이 아닙니다: {source}")
    if doc.needs_pass:
        fail("암호로 보호된 PDF입니다. 암호를 해제한 뒤 다시 시도하세요.")

    out_dir = resolve_output_dir(source, args.output, args.force)
    image_dir = out_dir / "images"
    options = {"page_chunks": True, "header": False, "footer": False, "show_progress": False}
    if args.images:
        options.update(write_images=True, image_path=str(image_dir))
    print(f"변환 중: {source.name} ({doc.page_count}쪽)", flush=True)
    chunks = pymupdf4llm.to_markdown(doc, **options)

    page_count = doc.page_count
    pages = {chunk["metadata"]["page_number"]: chunk["text"].strip() for chunk in chunks}
    if args.images:  # 그림 링크를 섹션 파일 기준 상대 경로로 바꾼다
        prefix = re.escape(str(image_dir))
        pages = {n: re.sub(prefix + r"[/\\]", "images/", text) for n, text in pages.items()}

    blank = sum(1 for n in range(1, page_count + 1) if len(pages.get(n, "")) < 20)
    if blank * 2 >= page_count:
        print(
            f"경고: {page_count}쪽 중 {blank}쪽에서 텍스트를 거의 추출하지 못했습니다. "
            "스캔본이라면 OCR 엔진이 필요합니다 (references/py-venv.md의 OCR 항목 참고).",
        )

    metadata = doc.metadata or {}
    title = (metadata.get("title") or "").strip() or source.stem
    toc = [
        (level, entry_title.strip(), page)
        for level, entry_title, page, *_ in doc.get_toc()
        if 1 <= page <= page_count
    ]
    if args.max_pages <= 0:
        ranges = [(title, 1, page_count)]
    else:
        ranges = split_by_toc([] if args.no_toc else toc, 1, page_count, 0, title, args.max_pages)

    sections = []
    for section_title, first, last in ranges:
        body = "\n\n".join(f"<!-- page: {n} -->\n\n{pages.get(n, '')}" for n in range(first, last + 1))
        location = f"p.{first}-{last}" if last > first else f"p.{first}"
        sections.append(Section(section_title, body, location))

    meta = {
        "제목": title,
        "저자": (metadata.get("author") or "").strip(),
        "페이지 수": f"{page_count} (위치의 페이지 번호는 PDF 파일 기준 순번)",
    }
    converter = f"pdf-to-md.py (pymupdf {pymupdf.__version__})"
    write_output(out_dir, source, converter, meta, sections, [(l, t, f"p.{p}") for l, t, p in toc])


if __name__ == "__main__":
    main()
