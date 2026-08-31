# WikiSkill workspace architecture

Shared reference for every `wikiskill-*` command and agent. Read this before touching a domain
workspace so file formats stay consistent across iterations.

Paper: [arXiv:2608.27454](https://arxiv.org/html/2608.27454) — see `README.md` at the plugin root
for the plan-English summary of the algorithm this implements.

## Workspace layout

A "domain" is one evolving skill library for one task family (e.g. "changelog-writing",
"sql-review"). Everything for a domain lives under `.wikiskill/<domain>/` in the *user's* project
(never inside the plugin install), except the live skills themselves, which go straight into
`.claude/skills/` so Claude Code picks them up the normal way with no copy step.

```
.wikiskill/<domain>/
  config.json
  tasks/
    train/*.json
    val/*.json
    test/*.json
  raw/
    iter-<k>/
      <task-id>.json
  wiki/
    index.md
    logs.md
    skill-impact.md
    patterns/
      <pattern-slug>.md
  staging/
    wikiskill-<domain>-<skill-name>/
      SKILL.md
      PURPOSE.md
  snapshots/
    accepted/
      wikiskill-<domain>-<skill-name>/...   (mirrors .claude/skills/wikiskill-<domain>-*)
  state.json

.claude/skills/
  wikiskill-<domain>-<skill-name>/
    SKILL.md
    PURPOSE.md
```

The `wikiskill-<domain>-` prefix on every live skill directory exists so a domain's whole skill
set can be found (`ls .claude/skills/ | grep wikiskill-<domain>-`), copied elsewhere for reuse
across projects, or cleanly removed, without touching skills from other domains or from other
plugins.

## `config.json`

```json
{
  "domain": "changelog-writing",
  "skill_prefix": "wikiskill-changelog-writing",
  "max_iterations": 10,
  "grader": { "type": "llm-judge" }
}
```

`grader.type` is either `"llm-judge"` (default — the `wikiskill-grader` subagent judges each
transcript against the task's `success_criteria`) or `"script"` with a `"command"` field: a
shell command that receives one JSON object on stdin `{"task": <task file contents>, "answer":
"<inference agent's final answer text>"}` and must print `{"pass": true|false}` (and may add a
`"reason"` field) to stdout. Use a script grader for tasks with a mechanically checkable answer
(e.g. code that must pass a test suite); it's more reliable than an LLM judge for those.

## Task files (`tasks/{train,val,test}/*.json`)

One task per file, filename doubles as a human-readable id if `id` is omitted:

```json
{
  "id": "task-001",
  "prompt": "The instruction to hand the inference agent, exactly as a user would phrase it.",
  "success_criteria": "Free-text rubric the grader checks the final answer against. Be specific and checkable — this is the only signal the whole loop optimizes against.",
  "context_files": []
}
```

`context_files` is an optional list of paths (relative to the domain workspace or absolute) the
inference agent should be told about as task setup — e.g. a sample input file to operate on.
Leave it `[]` for pure text/reasoning tasks.

Train tasks drive skill discovery. Val tasks drive the accept/reject gate — keep val disjoint
from train, and expect roughly 3-10 tasks per split for the loop to be worth running at all.
Test tasks are only ever touched by `/wikiskill:test`, never by `/wikiskill:evolve`.

## Raw traces (`raw/iter-<k>/<task-id>.json`)

Written once per (task, iteration) by the orchestrating command right after grading. Immutable —
never edited or deleted by any later step, including rejected iterations.

```json
{
  "task_id": "task-001",
  "iteration": 3,
  "split": "train",
  "prompt": "...",
  "transcript": "full text of the inference agent's reasoning/tool-call/output trace",
  "final_answer": "...",
  "grade": { "pass": false, "reason": "..." }
}
```

## Wiki layer (`wiki/`)

- `index.md` — a short catalog: one bullet per pattern file, its one-line takeaway, and which
  skill(s) it motivated. Kept current by the Wiki Maintainer every iteration; this is the first
  thing the Skill Proposer reads.
- `patterns/<slug>.md` — one file per distinct failure mode, successful strategy, or workaround.
  Edited *incrementally* (append a new section, replace a stale one, insert a caveat) — never
  wholesale rewritten, so the file's history stays legible as a growing case log. Suggested
  shape per pattern file:

  ```markdown
  # <Pattern name>

  ## Observed in
  - iter-1/task-003 (fail), iter-2/task-003 (fail), iter-2/task-007 (pass)

  ## What happens
  <the failure mode or successful strategy, in concrete terms>

  ## Root cause / why it works
  <analysis>

  ## Suggested skill guidance
  <the concrete instruction this should become in a SKILL.md>
  ```
- `logs.md` — append-only evolution log, one entry per iteration, written by the Wiki Maintainer
  and extended with the gate outcome once known:

  ```markdown
  ## Iteration 3
  - Train pass rate: 4/6
  - Patterns touched: off-by-one-in-date-ranges (updated), missing-null-check (new)
  - Skill proposal: patch `wikiskill-changelog-writing-date-ranges` (see skill-impact.md)
  - Val result: 5/6 (previous best 4/6) -> **accepted**
  ```
- `skill-impact.md` — the audit trail of every proposal, one entry per iteration, appended by the
  Skill Proposer when it proposes and completed by the orchestrating command once the gate
  decides:

  ```markdown
  ## Iteration 3 — proposal
  - Target: wikiskill-changelog-writing-date-ranges (patch)
  - Motivated by: patterns/off-by-one-in-date-ranges.md
  - Summary: <one line of what changed and why>
  - Validation score: 5/6 (best so far: 4/6)
  - Outcome: accepted
  ```

  The wiki is never rolled back regardless of outcome — a rejected proposal's entry stays in
  `skill-impact.md` as a permanent record of "this was tried and didn't help," which is itself
  useful signal for the next iteration's Skill Proposer.

## `state.json`

```json
{
  "best_val_score": 0.83,
  "best_val_fraction": "5/6",
  "iteration": 3,
  "history": [
    { "iteration": 1, "val_score": 0.5, "outcome": "accepted" },
    { "iteration": 2, "val_score": 0.5, "outcome": "rejected" },
    { "iteration": 3, "val_score": 0.83, "outcome": "accepted" }
  ]
}
```

Only `scripts/wikiskill_gate.py` writes this file. Never hand-edit it or edit it from an agent
prompt — the whole point of the gate is that acceptance is a deterministic numeric comparison,
not an LLM's judgment call.

## Skill files (`SKILL.md` + `PURPOSE.md`)

`SKILL.md` is a normal Claude Code skill: YAML frontmatter with `name` and `description`, then the
procedural content itself, exactly as it should read to help a fresh agent do the task better.
Nothing WikiSkill-specific belongs in it — it must stand alone as a good skill.

`PURPOSE.md` is the WikiSkill-specific companion, linking the skill back to *why* it exists:

```markdown
# Why this skill exists

- Motivated by: [[off-by-one-in-date-ranges]] (`wiki/patterns/off-by-one-in-date-ranges.md`)
- First proposed: iteration 2 (rejected — see skill-impact.md)
- Current version accepted: iteration 3
- Evidence: raw/iter-2/task-003.json (fail), raw/iter-3/task-003.json (pass)
```
