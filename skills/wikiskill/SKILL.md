---
name: wikiskill
description: Grow a durable, reusable Claude Code Agent Skill library for a task domain from your own worked examples, using the WikiSkill self-improvement loop (arXiv 2608.27454) — a persistent wiki of failure/success patterns plus a validation-gated skill set. Use when the user wants to evolve, self-improve, or auto-generate agent skills from example tasks/transcripts, mentions "WikiSkill", or asks how to turn accumulated experience on a recurring task into a skill.
---

# WikiSkill

This plugin implements the three-layer architecture from
[arXiv:2608.27454](https://arxiv.org/html/2608.27454): a raw layer of execution traces, a
persistent wiki of patterns distilled from them, and a skills layer that only changes when a
proposed change is validated to actually help — full details in
`${CLAUDE_PLUGIN_ROOT}/reference/architecture.md` and the plugin `README.md`.

If the user is asking about this conversationally rather than invoking a command directly, route
them to the right one:

- Never used this before, or no `.wikiskill/<domain>/` yet -> `/wikiskill:init <domain>`
- Has a workspace with train/val tasks filled in, wants to grow/improve skills ->
  `/wikiskill:evolve <domain> [iterations]`
- Wants to know where things stand (best score, current skills, wiki patterns) ->
  `/wikiskill:status <domain>`
- Wants a final held-out number without touching anything -> `/wikiskill:test <domain>`

Don't try to run the loop's steps ad hoc yourself outside these commands — `/wikiskill:evolve`
encodes the exact ordering (inference -> grade -> sample -> wiki maintain -> propose -> validate
-> gate) that keeps the wiki/skill-impact audit trail and the validation gate meaningful. If the
user describes a task domain they want a skill for but has no example tasks yet, help them write
2-3 `tasks/train/*.json` and at least 1 `tasks/val/*.json` file (schema in
`architecture.md`) before suggesting `/wikiskill:evolve` — the loop can't discover anything
without examples to fail and succeed on.
