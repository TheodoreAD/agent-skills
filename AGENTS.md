# Agent instructions for agent-skills

Cross-tool instructions for AI coding agents working in this repo. Universal conventions live in
`~/AGENTS.md` — nothing there is repeated here, only what is specific to this repo. `CLAUDE.md` is a
plain symlink to this file, not a wrapper that imports it, so every harness reads byte-identical
content.

## What this repo is

A published set of Agent Skills, installed by consumers through the
[`skills` CLI](https://github.com/vercel-labs/skills) (`npx skills add TheodoreAD/agent-skills`). It
is not a machine setup, not a library, and not a Claude Code plugin. The only artifact formats
admitted here are the vendor-neutral ones: `SKILL.md` (plus its `references/`, `scripts/`,
`evals/`), `AGENTS.md`, and MCP. A vendor manifest — `.claude-plugin/`, a marketplace entry, a
harness-specific rules directory — does not belong in this repo even as a convenience.

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
- A skill directory may hold `references/`, `scripts/` and `evals/`, and nothing else. `evals/` was
  added 2026-08-31 for trigger cases — JSON files of prompts with the skill each should select, run
  by `skills/skill-fitness/scripts/trigger.py`. Write them for a **pair** the fitness analyzer
  flagged rather than a fixed number per skill, and include should-not-trigger cases: a suite of
  positives alone passes for a description that fires on everything.

**Don't reword a description on a hunch — measure it.** `skills/skill-fitness/` reports which skills
compete, which never fire, and what the skill listing costs; its `trigger.py candidate` mode scores
a proposed description against the real installed set before it is adopted. Published measurement
(SkillsBench, 47,150 skills) puts unmeasured model-authored skills _below_ having no skill at all,
while curated ones are well above it — so drafting wording is fine and shipping it unmeasured is
not.

## Skill scope, and what must not be here

Every skill has to work for someone who has only this repo. A rule that depends on one machine's
setup — a specific dotfile, a locally-installed task runner, a repo that exists on one box — belongs
in that machine's own `AGENTS.md`, not in a published skill. Where a skill genuinely needs an
environment assumption (a directory, an env var), it must say so in the skill itself rather than
failing mysteriously.

The README's **Scope** column records how portable each skill is. Keep it accurate when a skill
changes; a skill that quietly grows a personal dependency is worse than one that declares it.

## This repo is published: never name a client in it

**No file here — skill, plan, commit message, test fixture — may name an employer, client, internal
project, work repo, work email address or ticket prefix.** This repo is public on GitHub and
installed by strangers via `npx skills add`. Anything committed is published the moment it is
pushed, and a push cannot be taken back by an edit.

Write about that work by its shape instead: "a work root with a `<project>/<repo>` hierarchy", "a
client repo under review pressure", "work root A". Every measurement in this repo's plans is
expressible that way — the counts and the structure are the evidence, the names never were.

The check is mechanical, so run it rather than reading for it:

```shell
python3 skills/plan-docs/scripts/plans.py scan --mode staged   # before every commit
python3 skills/plan-docs/scripts/plans.py scan                 # whole working tree
```

It derives the forbidden terms from the machine's own project roots, so nothing has to be listed
here — which is the point: a list of clients is itself the thing that must not be in a public repo.
Fixtures use invented names (`client.com-bitbucket`, `github.com-acme`) for the same reason.

Confirmed live 2026-08-28: a plan committed here listed six employer/client root directory names and
one client's internal project path, and was pushed. The rule and the scanner both exist because that
happened.
