---
name: outline-writer
description: Create and publish a new Markdown document in the fixed "LLM MCP" Outline collection through the outline_docs MCP connector, then return the created document title and URL. Use only when the user explicitly invokes or names the outline-writer skill; do not auto-trigger for ordinary writing, note-taking, or Outline-related requests.
---

# Outline Writer

Create exactly one new Outline document from the user's requested topic, notes, or source text.

## Workflow

1. Interpret the user's explicit `outline-writer` request and determine a concise document title and complete Markdown body.
2. Write the body as clear, structured Markdown appropriate to the request.
   - Do not begin the body with a top-level `#` heading. Pass the document title separately through the `title` parameter.
   - Preserve important facts, code, links, and requested structure from the user's input.
   - Do not invent unsupported factual claims when the user supplied source material.
3. Call only `outline_docs.create_document` to create the document.
   - Set `collectionId` to `828c4845-e63c-424c-8bcb-af62ce2b9567` (the `LLM MCP` collection).
   - Set `title` to the chosen document title.
   - Set `text` to the completed Markdown body.
   - Set `format` to `markdown`.
   - Set `publish` to `true`.
   - Do not use templates, parent documents, document search, update, move, or delete operations.
4. After creation succeeds, return only the created document's title and URL in a compact response. Do not repeat the full document body unless the user explicitly asks for it.

## Failure Handling

- If `outline_docs.create_document` is unavailable or returns an error, report that the document could not be created and include the useful error detail available from the tool.
- Do not fall back to another collection or another document-writing connector.
- Do not retry by using a different Outline operation.

## Output Format

Use this form after successful creation:

- 제목: `<created document title>`
- URL: `<created document URL>`
