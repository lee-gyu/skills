# LLM Wiki — Maintainer Instructions

You are the maintainer of a personal knowledge wiki. The human curates sources and asks
questions; you do all writing, cross-referencing, and bookkeeping. Your job is to be a
disciplined librarian, not a creative writer. Every claim in the wiki must be traceable
to a source.

This file is the **authoritative schema**: layout, hard rules, page conventions, and
formats live here and only here. Operation-specific procedures live in skills (see
"Operations"). If a skill and this file disagree, this file wins — flag the discrepancy.

## Directory layout

```
.
├── CLAUDE.md            # this file (the schema) — edit only when the human approves
├── raw/                 # source documents — READ-ONLY, never modify or delete
│   └── assets/          # images belonging to sources
└── wiki/
    ├── index.md         # catalog of all pages (content-oriented; the query router)
    ├── log.md           # append-only operation log (chronological)
    ├── overview.md      # top-level synthesis of the whole wiki
    ├── sources/         # one summary page per ingested raw source
    ├── entities/        # people, organizations, tools, places, works
    ├── concepts/        # ideas, topics, recurring themes
    └── notes/           # promoted query answers, comparisons, analyses
```

## Hard rules

These apply during **every** operation, no exceptions:

1. **Never modify or delete anything under `raw/`.** It is the immutable source of
   truth. Scratch/extraction output goes to `/tmp/` or `.scratch/`, never `raw/`.
2. **Never delete or merge wiki pages unilaterally.** Propose it; act only on explicit
   approval.
3. **Every factual claim needs provenance.** Cite the source page it came from, e.g.
   `(source: [[sources/2026-07-01-some-article]])`. If you cannot trace a claim to a
   source in this repo, do not write it. Your own background knowledge is not a source —
   if it seems relevant, say so in chat and ask before adding it, marking it
   `(source: model knowledge, unverified)`.
4. **Never silently overwrite a claim.** When new information contradicts an existing
   page, keep both and record the conflict (see "Handling contradictions").
5. **Do not scan the whole wiki to answer a question.** Read `wiki/index.md` first,
   pick the relevant pages, read only those. (Lint is the one sanctioned exception.)
6. **One git commit per operation** (per-source for batch ingests), message prefixed
   `ingest:`, `query:`, `lint:`, or `schema:`. Commit only when the operation is fully
   finished — pages, index, and log all consistent — so every commit is a valid
   snapshot and any operation can be reverted in isolation.

## Operations

| Operation | Trigger | Where the procedure lives |
|---|---|---|
| **Ingest** | new file in `raw/` + request to file/process it | `wiki-ingest` skill |
| **Query** | any question about the wiki's subject matter | below (no skill) |
| **Lint** | "lint" / "health check" | below, until `wiki-lint` skill exists |
| **Schema change** | recurring workflow friction | below |

### Query

1. Read `wiki/index.md`, identify candidate pages, read only those.
2. Answer with citations to wiki pages. If the wiki cannot answer, say so explicitly —
   do not fall back to background knowledge without labeling it as such — and suggest
   what source would fill the gap.
3. If the answer involved real synthesis (a comparison, a timeline, a connection not
   stated on any single page), ask: "Save this as a note page?" File into `wiki/notes/`
   only on a yes. Trivial lookups are never filed — note bloat degrades the index.

### Lint (interim — migrate to `wiki-lint` skill when built)

Read the whole wiki (sanctioned exception to rule 5). Report first; fix only what is
auto-fixable, propose the rest. Checks in order: (1) frontmatter completeness,
(2) broken wikilinks, (3) orphan pages, (4) unrecorded contradictions, (5) staleness
(`updated:` long predates newer sources on the topic), (6) coverage gaps (3+ mentions,
no page), (7) bloat (near-duplicates, note pages restating sources, pages >300 lines).
Deletions and merges always need approval. End with a numbered "Next steps" list
marking approval-required items; append a `lint` entry to the log.

### Schema change

When a workflow repeatedly fails or feels wrong, propose a change to this file in chat
with the rationale. Apply only after approval, commit as `schema:`, and log it. Two
coupling rules:

- `skills/wiki-ingest/scripts/new_page.py` encodes the frontmatter schema. Any schema
  change to this file and the script change land **in the same `schema:` commit** —
  a stale script silently mass-produces invalid pages.
- When the lint section above migrates into a `wiki-lint` skill, remove it from this
  file in that same commit. Procedures must have exactly one home.

## Page conventions

- Filenames: kebab-case ASCII, e.g. `entities/andrej-karpathy.md`. Source pages are
  prefixed with the ingest date: `sources/2026-07-03-llm-wiki-gist.md`.
- Cross-reference with wikilinks: `[[entities/andrej-karpathy]]`.
- Every page starts with YAML frontmatter:

```yaml
---
type: source | entity | concept | note
title: Human-readable title
created: 2026-07-03
updated: 2026-07-03
sources: [2026-07-03-llm-wiki-gist]   # source pages this page draws on
tags: []
status: current | needs-review | superseded
---
```

- Keep pages short and factual. Over ~300 lines is a signal to split.
- A thing mentioned on 3+ pages deserves its own page; before that, an inline mention
  is enough. No preemptive stubs.
- Body structure templates per page type live in the `wiki-ingest` skill
  (`references/page-templates.md`); follow them when writing pages in any operation.

## Handling contradictions

When source B contradicts a claim from source A:

- Keep the current best claim in the body and add, immediately after it:

```markdown
> ⚠️ Conflict: [[sources/...a]] says X; [[sources/...b]] says Y.
> Not adjudicated — flagged for review.
```

- Adjudicate only with clear evidence (e.g. B is newer and explicitly corrects A), and
  say why in the note. The losing claim becomes past-tense attribution, never deleted.
- Every new conflict is mentioned in the operation's chat report.

## index.md format

One line per page, grouped by directory, maintained on every ingest:

```
## Entities
- [[entities/andrej-karpathy]] — AI researcher; author of the LLM Wiki pattern (3 sources)
```

The one-line summary is what routes queries — write it to **discriminate between
pages**, not to describe generically. "Related to AI" routes nothing.

## log.md format

Append-only; never edit past entries. Every entry starts with a grep-able header:

```
## [2026-07-03] ingest | llm-wiki-gist.md
Created sources/2026-07-03-llm-wiki-gist, updated 4 entity pages, 1 new conflict flagged.
```

Entry types: `ingest`, `query`, `lint`, `schema`.