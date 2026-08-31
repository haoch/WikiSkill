---
description: Run the WikiSkill evolution loop for a domain — inference over train, wiki maintenance, one atomic skill proposal, validation, and a strict accept/rollback gate — for N iterations or until validation hits 100%.
argument-hint: "<domain-name> [iterations]"
---

Read `${CLAUDE_PLUGIN_ROOT}/reference/architecture.md` first — every path and file format below
refers to it. Parse `$ARGUMENTS` as `<domain> [iterations]`; if `iterations` is omitted, use
`max_iterations` from `.wikiskill/<domain>/config.json`. Project root is the current working
directory. Let `PREFIX` = `config.json`'s `skill_prefix`.

If `.wikiskill/<domain>/` doesn't exist, tell the user to run `/wikiskill:init <domain>` first
and stop. Read `config.json` now and keep its `grader` setting in mind for every grading step
below.

## Baseline (only if `state.json` doesn't exist yet)

Run one validation pass (see "Validation pass" below) using whatever's currently live under
`.claude/skills/<PREFIX>-*/` (normally nothing, for a brand new domain), saving each task's raw
trace to `.wikiskill/<domain>/raw/iter-0/<task-id>.json` with `"split": "val"` exactly as step 3
does for later iterations — the baseline's failures are exactly what motivates iteration 1's
patterns, so they must be recoverable later even in a fresh session, not just known from this
session's own context. Then run:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wikiskill_gate.py baseline \
  --project-root "$(pwd)" --domain <domain> --skill-prefix <PREFIX> \
  --val-score <fraction> --val-fraction "<x/y>"
```

This seeds `state.json` and snapshots the (possibly empty) baseline as the initial accepted set.
Do not treat this baseline pass as iteration 1 — iteration numbering starts at 1 with the first
real proposal below.

## One iteration (repeat up to `iterations` times, or until early-stop)

Let `k` = next iteration number (`state.json`'s `iteration` + 1).

1. **Inference over `tasks/train/*.json`.** For each train task: read the full body (past the
   frontmatter) of every currently-live `.claude/skills/<PREFIX>-*/SKILL.md`, concatenate them,
   and use the `Agent` tool with `subagent_type: wikiskill-inference` to solve the task, passing
   the concatenated skill bodies followed by the task's `prompt` (and any `context_files`
   content) in the prompt text. Capture its full transcript and the text after `FINAL ANSWER:`.
2. **Grade each transcript** against that task's `success_criteria`: if `config.json`'s grader is
   `llm-judge`, use the `Agent` tool with `subagent_type: wikiskill-grader`, passing the task
   prompt, `success_criteria`, transcript, and final answer; parse its `{"pass": ...}` JSON. If
   the grader is `script`, run its `command` via `Bash` with `{"task": ..., "answer": ...}` piped
   to stdin and parse the printed JSON instead.
3. **Save raw traces.** Write each task's result to
   `.wikiskill/<domain>/raw/iter-<k>/<task-id>.json` per the schema in `architecture.md`, with
   `"split": "train"`.
4. **Sample traces** for the Wiki Maintainer:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wikiskill_sample.py \
     --domain-workspace .wikiskill/<domain> --iteration <k>
   ```
   This prints the file paths to hand it (don't hand it every raw trace — that's what this
   script prevents).
5. **Wiki Maintainer.** Use the `Agent` tool with `subagent_type: wikiskill-wiki-maintainer`,
   giving it the workspace path, current `wiki/index.md` and `wiki/logs.md` contents, and the
   sampled trace paths from step 4 (it will `Read` them itself). Let it edit
   `wiki/patterns/*.md`, `wiki/index.md`, and append to `wiki/logs.md`. This step's edits are
   final regardless of what happens later in this iteration.
6. **Skill Proposer.** Use the `Agent` tool with `subagent_type: wikiskill-skill-proposer`,
   giving it the workspace path, current `wiki/index.md`, current `wiki/skill-impact.md`, and a
   one-line train-outcome summary (pass rate + failing task ids). It writes a full candidate
   skill set into `.wikiskill/<domain>/staging/<PREFIX>-*/` and appends a pending entry to
   `wiki/skill-impact.md`.
7. **Promote the candidate.** Remove any existing `.claude/skills/<PREFIX>-*/` directories, then
   copy every `.wikiskill/<domain>/staging/<PREFIX>-*/` directory into `.claude/skills/`. This is
   now the candidate skill set under validation.
8. **Validation pass** over `tasks/val/*.json` — same procedure as step 1–2 but with `"split":
   "val"` traces (still save them under `raw/iter-<k>/`, they're informative too). Compute
   `val_score` = passes / total as a fraction 0..1, and `val_fraction` as `"p/total"`.
9. **Gate:**
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/wikiskill_gate.py gate \
     --project-root "$(pwd)" --domain <domain> --skill-prefix <PREFIX> \
     --val-score <val_score> --val-fraction "<val_fraction>"
   ```
   This handles the accept-and-snapshot or reject-and-rollback of `.claude/skills/<PREFIX>-*/`
   for you — do not implement that logic yourself, and do not second-guess its accept/reject
   decision. Parse its JSON output.
10. **Close out the bookkeeping.** Append the "Val result: ... -> accepted/rejected" line to
    `wiki/logs.md`'s entry for this iteration, and fill in the blank "Validation score" /
    "Outcome" lines in `wiki/skill-impact.md`'s pending entry from step 6.
11. Report this iteration's result to the user in one or two lines: train pass rate, val
    score, accept/reject, and best-so-far.
12. If the gate's `early_stop` is true, or `k` has reached the requested iteration count, stop
    the loop and give a short final summary (best val score, how many skills are now live, where
    to find them). Otherwise continue to the next iteration.

Keep the user updated with a one-line status after every iteration rather than going silent for
the whole loop — this can take a while for larger task sets.
