---
name: md-summarize
description: 주어진 데이터 소스를 기반으로 분석하여 markdown 형식으로 요약/정리합니다.
argument-hint: "[init|progress|verify]"
disable-model-invocation: true
---

# md-summarize

주어진 데이터 소스를 분석하여 핵심 내용을 추출하고, 이를 Markdown 형식으로 요약/정리하는 기능을 제공한다.

## workflow

argument에 따라 다음과 같은 작업을 수행한다.

### init

다음의 워크플로우에 따라 작업을 실행합니다.

1. 데이터 소스를 식별한다. (pdf, html, docx 등)
2. 해당 데이터 소스를 AI 에이전트가 쉽게 파싱할 수 있는 md 형태로 변환한다. (이때 도구는 scripts/에 있는 변환 스크립트를 사용한다.)
3. 변환된 데이터 파일을 ".output/{filename-id}/converted/" 경로에 저장한다. (예: ".output/book1/converted/")
4. 먼저 데이터 소스의 핵심 주제, 구조를 분석해서 ".output/{filename-id}/0_summary.md"에 저장한다.
5. 이 책을 여러 턴에 걸쳐 분석/요약하기 위해 작업 계획을 수립하여 ".output/{filename-id}/1_plan.md"에 저장한다. (이 파일은 전체 작업 계획과 현재 진행 상황을 함께 포함한다.)

### progress

"init" 작업이 끝난 뒤 실행할 수 있다. 다음의 워크플로우를 따른다.

1. ".output/{filename-id}/1_plan.md"에 저장된 작업 계획을 기반으로 현재 진행해야 하는 작업 내용을 식별한다.
2. 계획된 작업을 이어서 진행한다.
3. 현재 턴의 작업이 종료되면, 진행 상황을 업데이트하고, 필요 시 작업 계획을 수정하여 ".output/{filename-id}/1_plan.md"에 저장한다.
4. 작업 진행 기록을 ".output/{filename-id}/3_log.md"에 저장한다.

### verify

"progress" 작업이 끝난 뒤 실행할 수 있다. 다음의 워크플로우를 따른다.

1. ".output/{filename-id}/1_plan.md"에 저장된 작업 계획과 진행 상황을 검토한다.
2. 분석/요약 결과가 계획과 일치하는지 확인한다.
3. 필요 시 추가 분석/수정을 수행하고, 최종 결과를 ".output/{filename-id}/4_verify.md"와 작업 기록(3_log.md)에 저장한다.

## scripts/

현재는 pdf, epub 파일만을 md로 변환하는 작업을 지원한다.
다른 형식의 경우 별도의 변환 스크립트를 작성하여 scripts/에 추가하라고 가이드한다.

1. `./scripts/pdf-to-md.py`: PDF 파일을 Markdown 형식으로 변환하는 스크립트이다.
2. `./scripts/epub-to-md.py`: EPUB 파일을 Markdown 형식으로 변환하는 스크립트이다.

스크립트는 스킬 폴더의 `.venv`로 실행한다. 실행 환경 구성, 실행 방법, 옵션은 [references/py-venv.md](references/py-venv.md)를 따른다.
변환 결과의 `index.md`에 전체 구조와 파일 목록이 정리되어 있으므로 분석은 이 파일부터 읽는다.
