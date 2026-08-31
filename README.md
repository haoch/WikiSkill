# WikiSkill Claude Code Plugin

A Claude Code plugin implementation of **WikiSkill** —
[arXiv:2608.27454](https://arxiv.org/html/2608.27454), "compiling agent experience into a
durable, cumulative wiki of knowledge, gated skill evolution from it."

Point it at a folder of your own worked examples for some recurring task (a "domain"), and it
grows a real, installed `.claude/skills/` library for that domain over successive iterations —
distilling failures and successes into a persistent knowledge base, and only ever keeping a skill
change that's proven to improve held-out validation accuracy.

## How it works

The paper organizes an agent's experience into three layers. This plugin implements each one
directly as real files in your project, plus four Claude subagents that play the paper's four
roles:

| Layer | Where it lives | What builds it |
|---|---|---|
| **Raw** — immutable execution traces | `.wikiskill/<domain>/raw/iter-<k>/*.json` | the `wikiskill-inference` subagent, one run per task |
| **Wiki** — a persistent, never-rolled-back knowledge base of patterns, an index, an evolution log, and a proposal audit trail | `.wikiskill/<domain>/wiki/` | the `wikiskill-wiki-maintainer` subagent |
| **Skills** — the active, executable skill set | `.claude/skills/wikiskill-<domain>-*/` | the `wikiskill-skill-proposer` subagent, one atomic change per iteration |

One iteration of `/wikiskill:evolve <domain>`:

1. Run every `tasks/train/*.json` task through the **Inference Agent**, with the current live
   skills' full content pasted directly into its prompt (not discovered — the paper found that
   giving the inference agent wiki access *during training* actually hurts skill quality, so it
   never sees the wiki, only whatever skills are currently live).
2. Grade each transcript against the task's `success_criteria` (LLM-judge by default, or a
   script grader you supply for mechanically-checkable tasks).
3. Sample a budget-limited, pass/fail-stratified subset of this iteration's traces.
4. The **Wiki Maintainer** root-causes the failures and reinforces what worked, editing
   `wiki/patterns/*.md` incrementally (append/extend, not rewrite) and refreshing
   `wiki/index.md` / `wiki/logs.md`. This step's edits are permanent — they're kept even if the
   iteration's skill proposal below is rejected.
5. The **Skill Proposer** (a ReAct-style explorer that reads the wiki index and specific pattern
   files on demand, rather than everything at once) drafts exactly one new skill or one patch to
   an existing skill.
6. The candidate skill set is validated against `tasks/val/*.json`.
7. **Gate**: a small deterministic script (`scripts/wikiskill_gate.py`, no LLM judgment involved)
   accepts the candidate only if validation accuracy *strictly* improves on the best score so far
   — otherwise it rolls the live skills back to the last accepted version. Either way the wiki
   keeps what it just learned; only the skill set is subject to rollback.
8. Repeat, until validation hits 100% or you run out of iterations.

`/wikiskill:test <domain>` runs one held-out pass over `tasks/test/*.json` with whatever's
currently accepted, without touching the wiki, skills, or gate state — for a final number once
you're done evolving.

Full file formats (task JSON schema, wiki page shapes, `state.json`, `skill-impact.md`) are in
[`reference/architecture.md`](reference/architecture.md).

### Simplifications vs. the paper

- No paired-bootstrap significance testing — the paper only used that to compare baselines in
  its own experiments, not as part of the evolve/gate algorithm itself.
- The Inference Agent's "no wiki access during training" rule is enforced by never telling it
  the wiki paths and scoping it to the task at hand, not by a hard filesystem sandbox.
- One skill set per domain rather than the paper's cross-model transfer experiments — to reuse a
  domain's skills elsewhere, just copy its `.claude/skills/wikiskill-<domain>-*/` directories.

## Requirements

- Claude Code with plugin support.
- `python3` on your `PATH` (stdlib only, no extra packages) — used by the two deterministic
  scripts (`scripts/wikiskill_gate.py`, `scripts/wikiskill_sample.py`).

## Install

From this repo:

```bash
claude plugin marketplace add https://github.com/haoch/WikiSkill
/plugin install wikiskill
```

Or, to try it locally without publishing anywhere, run Claude Code with this repo as a plugin
directory:

```bash
claude --plugin-dir /path/to/WikiSkill
```

## Quickstart

```
/wikiskill:init changelog-writing
```

This scaffolds `.wikiskill/changelog-writing/` with `config.json`, empty wiki files, and one
worked example train task. Edit `tasks/train/*.json` to add a handful more examples of the task
(each with a specific, checkable `success_criteria`), and add a few disjoint `tasks/val/*.json`
— these drive the accept/reject gate, so keep them separate from train. `tasks/test/*.json` is
optional and only touched by `/wikiskill:test`.

```
/wikiskill:evolve changelog-writing 5
```

Runs up to 5 iterations of the loop above, reporting train pass rate / val score / accept-or-
reject after each one.

```
/wikiskill:status changelog-writing
/wikiskill:test changelog-writing
```

`status` reports the current best score, iteration history, live skills, and wiki pattern
catalog. `test` gives a final held-out number without mutating anything.

You can also just describe what you want in plain language ("I want to grow a skill for writing
good PR descriptions from examples") — the bundled `wikiskill` skill will route you to the right
command.

## Plugin contents

```
.claude-plugin/plugin.json      # manifest
skills/wikiskill/SKILL.md       # discoverable natural-language entry point
commands/{init,evolve,status,test}.md
agents/wikiskill-{inference,wiki-maintainer,skill-proposer,grader}.md
reference/architecture.md       # file/schema reference shared by all commands and agents
scripts/wikiskill_{gate,sample}.py
```
