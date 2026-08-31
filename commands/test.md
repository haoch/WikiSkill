---
description: Run one held-out evaluation over a WikiSkill domain's test split, using whatever skill set is currently live/accepted. Never mutates the wiki, skills, or state.json.
argument-hint: "<domain-name>"
---

Read `${CLAUDE_PLUGIN_ROOT}/reference/architecture.md` for file formats. Domain is `$ARGUMENTS`,
project root is the current working directory, `PREFIX` is `config.json`'s `skill_prefix`. If
`.wikiskill/<domain>/tasks/test/` has no task files, tell the user and stop.

This command is read-only with respect to the workspace and skills: it must not edit
`wiki/*`, `state.json`, `.claude/skills/`, or `staging/` — it only measures.

For each `tasks/test/*.json` task: concatenate the current live `.claude/skills/<PREFIX>-*/
SKILL.md` bodies, run it through the `Agent` tool with `subagent_type: wikiskill-inference`
exactly as in `/wikiskill:evolve`'s inference step, then grade it per `config.json`'s `grader`
setting (LLM-judge via `subagent_type: wikiskill-grader`, or the configured script). Save each
trace under `.wikiskill/<domain>/raw/iter-test-<ISO-date>/<task-id>.json` with `"split": "test"`
(a fresh timestamped subdirectory each run, so repeated test runs don't clobber each other, but
nothing under `iter-<k>` from evolution is touched).

Report the final test accuracy as a fraction and percentage, plus a one-line note per failing
task (task id + grader's reason), so the user sees exactly what's still missed by the current
skill set.
