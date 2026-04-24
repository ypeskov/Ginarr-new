# Best Practices for Skill Creators

Source: https://agentskills.io/skill-creation/best-practices

## Start from real expertise

Don't ask an LLM to generate a skill from scratch without domain context. Effective skills are grounded in real expertise.

### Extract from a hands-on task

Complete a real task with an agent, then extract the reusable pattern. Pay attention to:
- Steps that worked — the successful sequence
- Corrections you made — "use X instead of Y", "check edge case Z"
- Input/output formats
- Context you provided — project conventions, constraints

### Synthesize from existing artifacts

Good source material: internal docs, runbooks, API specs, code review comments, version control history, real failure cases.

## Refine with real execution

Run the skill against real tasks. Read execution traces, not just final outputs. If the agent wastes time, common causes:
- Instructions too vague (agent tries several approaches)
- Instructions that don't apply (agent follows them anyway)
- Too many options without a clear default

## Spending context wisely

### Add what the agent lacks, omit what it knows

Focus on project-specific conventions, domain procedures, non-obvious edge cases. Don't explain HTTP, PDFs, or databases.

```markdown
<!-- Too verbose -->
PDF files are a common format... pdfplumber is recommended...

<!-- Better -->
Use pdfplumber for text extraction. For scanned docs, fall back to pdf2image with pytesseract.
```

Ask: "Would the agent get this wrong without this instruction?" If no, cut it.

### Design coherent units

Like functions — encapsulate a coherent unit of work. Not too narrow (multiple skills for one task), not too broad (hard to activate precisely).

### Aim for moderate detail

Concise stepwise guidance with a working example > exhaustive documentation.

### Progressive disclosure for large skills

Keep SKILL.md under 500 lines / 5000 tokens. Move detail to `references/`. Tell the agent *when* to load each file: "Read `references/api-errors.md` if the API returns non-200."

## Calibrating control

### Match specificity to fragility

- **Give freedom** when multiple approaches are valid. Explain *why* instead of rigid directives.
- **Be prescriptive** when operations are fragile or a specific sequence must be followed.

### Provide defaults, not menus

Pick a default, mention alternatives briefly:
```markdown
Use pdfplumber for text extraction.
For scanned PDFs requiring OCR, use pdf2image with pytesseract instead.
```

### Favor procedures over declarations

Teach *how to approach* a class of problems, not *what to produce* for a specific instance.

## Patterns for effective instructions

### Gotchas sections

Highest-value content. Concrete corrections to mistakes the agent will make:
```markdown
## Gotchas
- The `users` table uses soft deletes. Include `WHERE deleted_at IS NULL`.
- `/health` returns 200 even if DB is down. Use `/ready` for full health.
```

### Templates for output format

Provide a template — agents pattern-match well against concrete structures.

### Checklists for multi-step workflows

Explicit checklists help track progress and avoid skipping steps.

### Validation loops

Do the work → run validator → fix issues → repeat until validation passes.

### Plan-validate-execute

For batch/destructive operations: create plan → validate against source of truth → execute.

### Bundling reusable scripts

If the agent reinvents the same logic each run, write a tested script and bundle it in `scripts/`.
