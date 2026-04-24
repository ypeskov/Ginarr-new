# Evaluating Skill Output Quality

Source: https://agentskills.io/skill-creation/evaluating-skills

## Test cases

A test case has three parts:
- **Prompt**: realistic user message
- **Expected output**: description of success
- **Input files** (optional)

Store in `evals/evals.json` inside the skill directory:

```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "...",
      "expected_output": "...",
      "files": ["evals/files/input.csv"],
      "assertions": [
        "The output includes X",
        "Both axes are labeled"
      ]
    }
  ]
}
```

Tips: start with 2-3 cases, vary prompts (casual/precise), cover edge cases, use realistic context.

## Running evals

Run each test twice: **with skill** and **without** (baseline). Use clean context per run (subagents or separate sessions).

### Workspace structure

```
skill-workspace/
└── iteration-1/
    ├── eval-test-name/
    │   ├── with_skill/
    │   │   ├── outputs/
    │   │   ├── timing.json
    │   │   └── grading.json
    │   └── without_skill/
    │       ├── outputs/
    │       ├── timing.json
    │       └── grading.json
    └── benchmark.json
```

## Writing assertions

Add after first run. Good assertions are verifiable:
- "The output file is valid JSON" — programmatically checkable
- "The bar chart has labeled axes" — specific, observable
- "The report includes at least 3 recommendations" — countable

Avoid: "The output is good" (vague), exact string matching (brittle).

## Grading

Evaluate each assertion: **PASS** or **FAIL** with evidence quoting the output.

```json
{
  "assertion_results": [
    { "text": "...", "passed": true, "evidence": "Found chart.png in outputs" },
    { "text": "...", "passed": false, "evidence": "X-axis has no label" }
  ],
  "summary": { "passed": 3, "failed": 1, "total": 4, "pass_rate": 0.75 }
}
```

## Aggregating results

Compute per-configuration stats in `benchmark.json`:
- pass_rate (mean, stddev)
- time_seconds (mean, stddev)
- tokens (mean, stddev)
- delta between with/without skill

## Iteration loop

1. Give eval signals + current SKILL.md to LLM → propose improvements
2. Review and apply changes
3. Rerun in new `iteration-<N+1>/` directory
4. Grade, aggregate, human review
5. Repeat until satisfied

Guidelines: generalize from feedback, keep skill lean, explain *why*, bundle repeated scripts.
