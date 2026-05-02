# Roadmap

Active and historical implementation plans. Plan docs are in Russian (per the owner's convention) with `[ ] / [x]` checkboxes; mark items completed inline as work progresses, and either keep the file or move it under `archive/` once everything is closed.

## Active

- [auto-wiki.md](auto-wiki.md) — extend chat-memory into a Karpathy-style LLM-managed wiki: rename `chat-memory` → `Auto-Wiki`, `notes/` → `wiki/`, add `lint-indexes`, `ingest-and-weave`, `lint-wiki` skills.

## Deferred

- [vector-index-future.md](vector-index-future.md) — local embedding + sqlite-vec layer as secondary index for semantic recall. Deferred until corpus growth (~200 entities) makes file-based recall miss connections; current SPEC anti-vector clause was aimed at cloud-vector pattern and does not block the local-only setup.
