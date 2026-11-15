# Python 실행 환경 (.venv)

`scripts/`의 변환 스크립트는 스킬 폴더(SKILL.md가 있는 폴더) 안의 `.venv`로 실행한다.
아래 명령의 `<스킬 폴더>`는 이 스킬이 설치된 실제 경로로 바꾼다.

## 요구 사항

- Python 3.11 이상. `pymupdf` 2.x가 3.11 미만을 지원하지 않는다.
- 디스크 약 250MB. `pymupdf`가 레이아웃 분석용 `onnxruntime`을 함께 설치한다.
- 의존성 목록은 `scripts/requirements.txt`에 있다.

## 구성

`.venv`가 이미 있으면 [확인](#확인)만 하고 넘어간다.

### uv 사용 (권장)

시스템 Python이 3.11 미만이어도 uv가 맞는 버전을 내려받아 쓴다.

```bash
cd <스킬 폴더>
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r scripts/requirements.txt
```

### uv가 없을 때

3.11 이상의 Python으로 직접 만든다.

```bash
cd <스킬 폴더>
python3.12 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
```

Windows에서는 `.venv/bin/python` 대신 `.venv\Scripts\python.exe`를 쓴다.

### 확인

```bash
<스킬 폴더>/.venv/bin/python -c "import pymupdf, pymupdf4llm, markdownify; print(pymupdf.__version__)"
```

버전(2.1 이상)이 출력되면 준비된 것이다.

## 실행

venv를 활성화할 필요 없이 `.venv`의 Python으로 스크립트를 직접 실행한다.
출력 기본 경로(`.output/{filename-id}/converted/`)는 현재 폴더 기준이므로, 결과를 둘 작업 폴더에서 실행한다.

```bash
<스킬 폴더>/.venv/bin/python <스킬 폴더>/scripts/pdf-to-md.py <파일.pdf>
<스킬 폴더>/.venv/bin/python <스킬 폴더>/scripts/epub-to-md.py <파일.epub>
```

`{filename-id}`는 파일 이름에서 자동으로 만든다 (예: `My Book (2nd).pdf` → `my-book-2nd`).
다른 이름을 쓰려면 `-o .output/book1/converted`처럼 출력 폴더를 직접 지정한다.

| 옵션 | 대상 | 설명 |
| --- | --- | --- |
| `-o, --output DIR` | 공통 | 출력 폴더를 지정한다. |
| `--images` | 공통 | 그림을 `images/`에 추출하고 본문에 링크를 남긴다. |
| `--force` | 공통 | 이전 변환 결과(`index.md`, `NNN-*.md`)를 지우고 다시 변환한다. |
| `--max-pages N` | pdf | 파일 하나의 최대 페이지 수. 기본 30, 0이면 나누지 않는다. |
| `--no-toc` | pdf | 목차(북마크)를 무시하고 페이지 수로만 나눈다. |
| `--max-chars N` | epub | 파일 하나의 최대 글자 수. 기본 60000, 0이면 더 나누지 않는다. |

### 출력 구조

```text
.output/{filename-id}/converted/
├── index.md        # 메타데이터, 파일 목록(위치·줄 수·글자 수), 원본 목차
├── 001-{제목}.md   # 목차 기준으로 나눈 섹션
├── 002-{제목}.md
└── images/         # --images 지정 시
```

- `index.md`를 먼저 읽으면 전체 구조와 파일별 분량을 알 수 있다.
- PDF 섹션에는 페이지마다 `<!-- page: N -->` 표시가 있다. N은 PDF 파일 기준 순번이다.
- PDF의 반복되는 머리글/바닥글(쪽 번호 등)은 제거된다.

## OCR (스캔본 PDF)

텍스트 레이어가 없는 스캔본은 변환 결과가 비어 있고 스크립트가 경고를 출력한다.
OCR 엔진을 venv에 추가하면 다음 실행부터 자동으로 사용한다.

```bash
uv pip install --python <스킬 폴더>/.venv/bin/python rapidocr
```

영문 스캔본에서 동작을 확인했다. 한글 스캔본의 인식 품질은 확인하지 않았으므로 결과를 직접 검토한다.

## 문제 해결

| 증상 | 원인과 조치 |
| --- | --- |
| `No module named 'pymupdf4llm'` 또는 `'bs4'` | `.venv`가 아닌 Python으로 실행했거나 의존성이 설치되지 않았다. [구성](#구성)을 다시 따른다. |
| 설치 중 `pymupdf>=2.1`을 찾지 못함 | venv의 Python이 3.11 미만이다. `.venv`를 지우고 3.11 이상으로 다시 만든다. |
| `출력 폴더가 비어 있지 않습니다` | 이미 변환한 파일이다. 기존 결과를 쓰거나 `--force`로 다시 변환한다. |
| `DRM으로 암호화된 EPUB입니다` | DRM이 걸린 파일은 변환할 수 없다. DRM이 없는 원본이 필요하다. |
| 스킬 업데이트 후 `.venv`가 사라짐 | 스킬 폴더가 교체되면 `.venv`도 없어진다. [구성](#구성)을 다시 실행한다. |
