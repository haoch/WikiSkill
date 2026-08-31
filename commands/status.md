---
description: Report a WikiSkill domain's current state — best validation score, iteration history, live skills, and wiki summary.
argument-hint: "<domain-name>"
---

Domain is `$ARGUMENTS`. Project root is the current working directory. If
`.wikiskill/<domain>/` doesn't exist, tell the user to run `/wikiskill:init <domain>` first.

Read and summarize concisely:

1. `.wikiskill/<domain>/state.json` (if present — if absent, say no iterations have run yet):
   best val score/fraction, current iteration, and the accept/reject history as one line per
   iteration.
2. `.claude/skills/<skill_prefix>-*/` — list each live skill's name and, from its `PURPOSE.md`,
   the one-line "Motivated by" pattern it traces back to.
3. `.wikiskill/<domain>/wiki/index.md` — the current pattern catalog, verbatim or lightly
   condensed if long.
4. The most recent 1-2 entries of `.wikiskill/<domain>/wiki/skill-impact.md`, so the user sees
   what's actively being tried.

Keep the whole report scannable — headers and short bullets, not prose paragraphs.
