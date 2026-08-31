---
description: Scaffold a new WikiSkill domain workspace (.wikiskill/<domain>/) with empty wiki files and one example task, ready to fill in and evolve.
argument-hint: "<domain-name>"
---

Read `${CLAUDE_PLUGIN_ROOT}/reference/architecture.md` first — it defines every file/format this
command creates.

The domain name is `$ARGUMENTS` (trimmed, lowercase, hyphens only — if the user gave something
else, slugify it and tell them what you used). If it's empty, ask the user what domain to
initialize before doing anything else.

Determine the project root as the current working directory (where `.claude/` and `.wikiskill/`
belong — this is the user's project, not the plugin install). If `.wikiskill/<domain>/` already
exists, stop and tell the user (don't overwrite an existing workspace) — point them at
`/wikiskill:status <domain>` instead.

Create, using the `Write` tool:

1. `.wikiskill/<domain>/config.json`:
   ```json
   {
     "domain": "<domain>",
     "skill_prefix": "wikiskill-<domain>",
     "max_iterations": 10,
     "grader": { "type": "llm-judge" }
   }
   ```
2. `.wikiskill/<domain>/tasks/train/example-001.json`, and empty-but-present
   `.wikiskill/<domain>/tasks/val/.gitkeep` and `.wikiskill/<domain>/tasks/test/.gitkeep`. The
   example train task should be a real, working, minimal example *relevant to the domain name*
   the user gave (not a placeholder lorem-ipsum task) — write a genuinely plausible one-task
   example of the kind of thing this domain is for, with a specific, checkable
   `success_criteria`, following the schema in `architecture.md`.
3. `.wikiskill/<domain>/wiki/index.md` — header only: `# <domain> — wiki index` plus a line
   noting no patterns yet.
4. `.wikiskill/<domain>/wiki/logs.md` — header only: `# <domain> — evolution log`.
5. `.wikiskill/<domain>/wiki/skill-impact.md` — header only: `# <domain> — skill impact log`.
6. `.wikiskill/<domain>/wiki/patterns/.gitkeep`.
7. `.wikiskill/<domain>/staging/.gitkeep` and `.wikiskill/<domain>/snapshots/.gitkeep`.

Do **not** create `state.json` — its absence is exactly what tells `/wikiskill:evolve` to run the
baseline pass first. Do **not** create anything under `.claude/skills/` yet — the domain starts
with zero skills, which is a valid starting point (the loop can propose a brand new skill from
iteration 1).

When done, tell the user, briefly:
- the workspace path created
- that they should now edit `tasks/train/example-001.json` and add a handful more train tasks,
  plus a few `tasks/val/*.json` (disjoint from train — used for the accept/reject gate) and
  optionally `tasks/test/*.json` (held out, only touched by `/wikiskill:test`)
- that `/wikiskill:evolve <domain>` is the next step once tasks are filled in
