# TODO

Features not yet scheduled for implementation. Short description per entry; details come when we start the work.

## Multi-vault support

`GINARR_VAULT_ROOT` currently pins the bot to exactly one chat-memory vault: all writes (logs, new notes) go there, recall searches there.

Add the ability to attach **secondary vaults** alongside the primary:

- **Primary vault** — unchanged; the only destination for writes.
- **Secondary vaults** — read-only for recall/search. The agent can reference notes from them but never modifies them.

Use cases: shared knowledge bases across personas, read-only archive of a previous vault, or household-shared notes alongside private memory.
