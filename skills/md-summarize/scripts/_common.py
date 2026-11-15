"""md-summarize 변환 스크립트 공용 헬퍼: 출력 경로 결정, 섹션 파일과 index.md 작성."""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

SECTION_FILE = re.compile(r"^\d{3,}-.*\.md$")
VENV_HINT = "references/py-venv.md를 따라 실행 환경(.venv)을 구성한 뒤 다시 실행하세요."


@dataclass
class Section:
    title: str
    text: str
    location: str = ""  # 원본 내 위치 (예: "p.12-34")


def fail(message: str):
    print(f"오류: {message}", file=sys.stderr)
    sys.exit(1)


def slugify(text: str, max_len: int = 40) -> str:
    """파일/폴더 이름으로 쓸 수 있는 슬러그. 한글 등 유니코드 문자는 유지한다."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w]+", "-", text).strip("-_")
    return text[:max_len].rstrip("-_") or "untitled"


def clean_markdown(text: str) -> str:
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def resolve_output_dir(source: Path, output: str | None, force: bool) -> Path:
    """출력 폴더를 정하고 준비한다. 기본값은 .output/{filename-id}/converted/."""
    out = Path(output) if output else Path(".output") / slugify(source.stem, 60) / "converted"
    if out.exists() and not out.is_dir():
        fail(f"출력 경로가 폴더가 아닙니다: {out}")
    if out.is_dir() and any(out.iterdir()):
        if not force:
            fail(f"출력 폴더가 비어 있지 않습니다: {out} (다시 변환하려면 --force)")
        # 이전 변환 결과만 지운다. 그 외 파일은 건드리지 않는다.
        for old in out.iterdir():
            if old.is_file() and (old.name == "index.md" or SECTION_FILE.match(old.name)):
                old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_output(
    out_dir: Path,
    source: Path,
    converter: str,
    meta: dict[str, str],
    sections: list[Section],
    toc: list[tuple[int, str, str]],
) -> None:
    """섹션별 md 파일과 전체 구조를 담은 index.md를 쓴다.

    toc: (level, title, location) 목록. level은 1부터 시작한다.
    """
    if not sections:
        fail("변환된 내용이 없습니다. 원본에 추출 가능한 텍스트가 있는지 확인하세요.")

    width = max(3, len(str(len(sections))))
    show_location = any(s.location for s in sections)
    rows = []
    for i, section in enumerate(sections, 1):
        name = f"{i:0{width}d}-{slugify(section.title)}.md"
        info = [source.name, f"{i}/{len(sections)}", section.title, section.location]
        header = " | ".join(part for part in info if part).replace("--", "—")
        body = clean_markdown(section.text)
        (out_dir / name).write_text(f"<!-- {header} -->\n\n{body}", encoding="utf-8")

        cells = [str(i), f"[{name}]({name})", section.title.replace("|", "\\|")]
        if show_location:
            cells.append(section.location)
        cells += [f"{body.count(chr(10)) + 2:,}", f"{len(body):,}"]
        rows.append("| " + " | ".join(cells) + " |")

    columns = ["#", "파일", "제목"] + (["위치"] if show_location else []) + ["줄 수", "글자 수"]
    align = ["---"] * (len(columns) - 2) + ["---:", "---:"]
    lines = [f"# {meta.get('제목') or source.stem}", ""]
    lines.append(f"- 원본: `{source.resolve()}`")
    lines.append(f"- 변환: {converter}")
    lines += [f"- {key}: {value}" for key, value in meta.items() if value and key != "제목"]
    lines += ["", "## 파일 목록", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(align) + " |")
    lines += rows
    if toc:
        lines += ["", "## 원본 목차", ""]
        base = min(level for level, _, _ in toc)
        for level, title, location in toc:
            suffix = f" ({location})" if location else ""
            lines.append(f"{'  ' * (level - base)}- {title}{suffix}")
    (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(len(s.text) for s in sections)
    print(f"변환 완료: {out_dir}/ (섹션 {len(sections)}개, 약 {total:,}자)")
    print(f"구조 요약: {out_dir / 'index.md'}")
