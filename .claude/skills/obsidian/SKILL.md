---
name: obsidian
description: >
  Read, search, create, and edit notes in the user's Obsidian vault.
  Use when the user asks to find a note, save something to Obsidian,
  check TODO, read a specific note, or says "obsidian", "vault", "заметка", "записать".
allowed-tools: Read Edit Write Glob Grep Bash(ob sync --path *)
metadata:
  author: openclaw
  version: "1.0"
---

# Obsidian Vault Access

## Vault Location

`$HOME/obsidian-vaul` (main-1 vault, bidirectional sync via obsidian-headless)

## Vault Structure

| Folder | Content |
|---|---|
| `_Dashboard` | Home page, TODO list, keys |
| `BG` | Bulgaria life — health, auto, contacts |
| `Dev Notes` | Technical notes, commands, configs |
| `General` | Personal — contacts, accounts, misc |
| `Investments` | Portfolio, tickers, plans |
| `Krokobot` | Bot-related notes |
| `Orgfin.run` | Business project notes |
| `Poems` | Poetry |
| `Resume` | CV sections and output |
| `RingCentral` | Work notes |
| `Slava` | Notes about Slava |
| `US Green Card` | Immigration docs |

## Operations

### Search for a note
```bash
# By filename
Glob: ~/obsidian-vaul/**/*keyword*.md

# By content
Grep: pattern in ~/obsidian-vaul/ with glob *.md
```

### Read a note
Use the Read tool with the full path.

### Create a note
Use Write tool. Place in the appropriate folder. Use standard markdown.

### Edit a note
Use Edit tool. Read the note first.

### Force sync after changes
```bash
ob sync --path ~/obsidian-vaul
```
Run this after creating or editing notes to push changes to other devices immediately.

## Rules
- **Never delete notes** without explicit user confirmation
- **Sensitive data** — vault contains personal info (accounts, addresses, medical). Never expose in Telegram group chats. Only share with Yura in DM.
- **Language** — match the language of existing notes. Most are in Russian.
- **Obsidian links** — use `[[Note Name]]` format for internal links
- After writing/editing, run `ob sync` to push changes
