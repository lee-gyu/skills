# lee-gyu/skills

## Installation

```bash
# Codex
codex plugin marketplace add lee-gyu/skills
codex plugin add lee-gyu-skills@lee-gyu-skills

# Claude
claude plugin marketplace add lee-gyu/skills
claude plugin install lee-gyu-skills@lee-gyu-skills
```

## Update

```bash
codex plugin marketplace upgrade lee-gyu-skills
claude plugin marketplace update lee-gyu-skills
```

## markdown-rules

같은 규칙을 플랫폼별 방식으로 제공한다. 원본은 `skills/markdown-rules/SKILL.md`이다.

| 플랫폼 | 호출 |
| --- | --- |
| Claude | `/lee-gyu-skills:markdown-rules [요청]` (`commands/markdown-rules.md`) |
| Codex | `$markdown-rules` 스킬을 명시적으로 지정 (자동 호출 비활성화) |

`commands/markdown-rules.md`는 생성 파일이다. 원본을 수정한 뒤 `pnpm sync-commands`로 갱신한다.
