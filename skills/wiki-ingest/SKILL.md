---
name: wiki-ingest
description: Ingest source documents into the LLM Wiki — extract content from raw/, summarize, create or update entity/concept pages with provenance, cross-reference, and update index.md and log.md. Use whenever the user adds a file (article, PDF, HTML, notes) to raw/ and wants it reflected in the wiki, even if they don't say "ingest" — phrases like "add this to the wiki", "file this article", "process the new sources", "이 문서 위키에 반영해줘" all count. Also use for batch requests like "ingest everything in raw/inbox". Do NOT use for answering questions about existing wiki content (query) or for health checks (lint).
---

# Wiki Ingest

You are performing the **ingest** operation of the LLM Wiki. The goal: turn a raw source
document into durable, cross-referenced, provenance-tracked wiki knowledge.

## Before you start

Read the repo's `CLAUDE.md` first if it is not already in context. It is the
**authoritative schema** — directory layout, hard rules, frontmatter fields, naming, and
index/log formats all live there, not here. If this skill and `CLAUDE.md` ever disagree,
`CLAUDE.md` wins; flag the discrepancy to the human.

Two rules matter so much during ingest that they bear repeating:

- `raw/` is immutable. Extraction output, normalized text, and scratch files go anywhere
  *except* `raw/` (use `/tmp/` or a `.scratch/` dir).
- Every claim you write must be traceable to the source being ingested or an existing
  cited page. Your background knowledge is not a source.

## Workflow

### 1. Extract the source

Run the extraction script to get clean markdown from the raw file:

```bash
python scripts/extract_source.py raw/<file> --out /tmp/extracted.md
```

It handles `.md`, `.txt`, `.html`, and `.pdf` (text-layer). If it reports failure —
scanned PDF, unsupported format, encoding it can't fix — fall back to reading the file
directly with your own tools and say in your report which path you took. If the script
lists referenced images, view the ones that plausibly carry information (charts,
diagrams, tables-as-images); skip decorative ones.

Read the extracted text **in full** before writing anything. Summarizing from a skim
produces confident-sounding pages with subtle errors that are expensive to find later.

### 2. Checkpoint with the human

Present 5–10 bullets of key takeaways in chat and ask what to emphasize, skip, or
correct. **Wait for the reply.** This is the cheapest moment to steer — after pages are
written, corrections cost a lint cycle.

Skip this pause only in batch mode (see below) or if the human explicitly said to
proceed without review.

### 3. Survey what the wiki already knows

Read `wiki/index.md` and open every existing page this source touches (entities and
concepts it mentions that already have pages). You need current content in context to
integrate rather than duplicate, and to spot contradictions in the next step. Do not
read unrelated pages.

### 4. Scaffold and write the source page

```bash
python scripts/new_page.py --wiki-root wiki --type source \
  --title "Readable Title" --sources "<raw-filename>"
```

The script creates the file with valid frontmatter (correct date prefix, kebab-case
slug, all required fields) and prints the path. Then fill in the body following
`references/page-templates.md` — read that file now if you haven't. A source page is a
*faithful summary of what this source says*, including claims you suspect are wrong;
disagreement is recorded as a conflict, not by silently omitting the claim.

### 5. Update or create entity and concept pages

For each entity/concept the source materially informs:

- Existing page → integrate the new information into the body, append the source slug to
  `sources:` in frontmatter, bump `updated:`. Integrate means *merge into the narrative*,
  not append a "From source X:" section at the bottom — sectioned-by-source pages become
  unreadable after five ingests.
- New page warranted → scaffold with `new_page.py --type entity|concept`. Apply the
  3-mention rule from `CLAUDE.md`: don't create stubs for things mentioned once.

Cite as you write: `(source: [[sources/<slug>]])` on each claim.

### 6. Check contradictions

Compare the new claims against what the pages said before your edits (you read them in
step 3). For each conflict, follow the contradiction protocol in `CLAUDE.md` — keep both
claims, add the `> ⚠️ Conflict:` note, do not adjudicate without clear evidence. Every
conflict goes in the final report.

### 7. Update index, overview, log

- `wiki/index.md`: add a line for each new page; revise the one-line summary of updated
  pages **if their gist changed**. The summary is the query router — write it to
  discriminate ("AI researcher; coined X; 3 sources"), not to describe generically.
- `wiki/overview.md`: update only if this source shifts the top-level synthesis.
- `wiki/log.md`: append one entry per the format in `CLAUDE.md`.

### 8. Commit and report

One git commit for the whole operation, message `ingest: <slug>`. Commit only now, when
index/log/pages are all consistent — a half-done ingest must never be committed.

Report in chat:

```
## Ingested: <title>
- Source page: [[sources/...]]
- Created: <n> pages (list)
- Updated: <n> pages (list)
- Conflicts: <list with one-line description, or "none">
- Open questions this source raises: <or "none">
```

## Batch mode

"Ingest everything in raw/inbox/" (or similar): process sources **one at a time**, each
through steps 1 and 3–8, skipping the per-source pause (step 2). One commit per source,
not one giant commit — this keeps git history usable as an audit trail and makes a bad
ingest revertable in isolation. Deliver all per-source reports together at the end,
plus a combined conflict list.

If two sources in the batch contradict *each other*, that is still a conflict — record
it even though neither claim predates the batch.

## Edge cases

- **Re-ingesting an already-ingested source** (same file or an updated version): do not
  create a second source page. Update the existing one, note the re-ingest in its body
  and in the log, and diff the claims — changed claims are treated as contradictions
  with provenance "same source, newer version".
- **Source is enormous** (book-length): propose splitting into chapter-level source
  pages before starting; get approval on the split.
- **Source contains no new information**: still create the source page (it is the
  provenance record) but say in the report that no entity/concept pages changed.
- **Extraction produced garbage** (mojibake, OCR noise): stop and tell the human rather
  than summarizing noise into confident prose.
- **The human's ingest request names a file that isn't in `raw/`**: ask them to add it;
  do not fetch content from the web into `raw/` yourself unless explicitly asked, and
  never write into `raw/` — instruct the human where to place it.

## Schema coupling warning

`scripts/new_page.py` encodes the frontmatter schema. If `CLAUDE.md`'s schema changes
(a `schema:` commit), the script must change in the same commit. If you notice the
script emitting frontmatter that no longer matches `CLAUDE.md`, stop and flag it —
do not hand-patch pages around a stale script.
