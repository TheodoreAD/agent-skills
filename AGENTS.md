# Agent instructions for agent-skills

Cross-tool instructions for AI coding agents working in this repo. Universal conventions live in
`~/AGENTS.md` — nothing there is repeated here, only what is specific to this repo. `CLAUDE.md` is a
plain symlink to this file, not a wrapper that imports it, so every harness reads byte-identical
content.

## What this repo is

A published set of Agent Skills, installed by consumers through the
[`skills` CLI](https://github.com/vercel-labs/skills) (`npx skills add TheodoreAD/agent-skills`). It
is not a machine setup, not a library, and not a Claude Code plugin. The only artifact formats
admitted here are the vendor-neutral ones: `SKILL.md` (plus its `references/` and `scripts/`),
`AGENTS.md`, and MCP. A vendor manifest — `.claude-plugin/`, a marketplace entry, a harness-specific
rules directory — does not belong in this repo even as a convenience.

## Build & test

- `inv dev-env.setup` once after cloning — creates `.venv` and wires direnv to it.
- `inv quality.precommit` before considering a change done. Markdown is not exempt: `dprint` reflows
  prose, and a `SKILL.md` reflow is the most common CI failure in this repo family.
- `pytest` — `tests/unit/test_skill_layout.py` validates every skill's frontmatter and layout. It is
  the gate a new skill has to pass, so add the skill and run the suite rather than eyeballing the
  frontmatter.

## Authoring a skill

**Cut a skill by responsibility, and give it a trigger that cannot contend with another skill's.**
Two skills whose `description` fields both plausibly match the same request is the failure mode to
design against — the agent picks one, and which one is not predictable. If a new skill's trigger
overlaps an existing one, the fix is redrawing the boundary between them, not wording the
description more carefully.

- `description` is the field agents actually match on. Write it as a list of concrete situations
  ("Use when …, …, or …"), not as a summary of the skill's contents. Everything a reader needs in
  order to decide _whether to open the file_ goes here; everything else goes in the body.
- Keep the body to what an agent must follow. Reasoning, prior art, measurements and rejected
  alternatives go in `references/` — loaded only when the agent needs them.
- Cite evidence with a date when a rule came from something that actually happened ("Confirmed live
  2026-08-23: …"). A rule with a story attached survives review; a bare assertion gets softened by
  the next editor who disagrees with it.
- When a rule is observed being missed in practice, strengthen its language rather than lengthen its
  explanation.

## Skill scope, and what must not be here

Every skill has to work for someone who has only this repo. A rule that depends on one machine's
setup — a specific dotfile, a locally-installed task runner, a repo that exists on one box — belongs
in that machine's own `AGENTS.md`, not in a published skill. Where a skill genuinely needs an
environment assumption (a directory, an env var), it must say so in the skill itself rather than
failing mysteriously.

The README's **Scope** column records how portable each skill is. Keep it accurate when a skill
changes; a skill that quietly grows a personal dependency is worse than one that declares it.
