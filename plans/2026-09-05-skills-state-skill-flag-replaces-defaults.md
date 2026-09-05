---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: bb66cbe5-7369-4f49-a8e7-7949db5ff99a.jsonl
source_moment: 2026-09-05T09:09:33Z
---

# `harvest.py skills-state --skill` replaces the default set instead of adding to it

## Context

`session-harvest`'s step 0 says: `skills-state --since <start>` compares "this skill and the others
a harvest leans on; add `--skill <name>` for anything else this run used". Read as written, passing
`--skill plan-docs` should report plan-docs _and_ session-harvest. It reports plan-docs only — the
help says `--skill` is "repeatable (default: the ones a harvest uses)", so naming one drops the
defaults, and the harvest's own skill is the one that goes unchecked. Confirmed 2026-09-05: a
harvest passed `--skill plan-docs --skill invoke-task-conventions`, got two clean rows, and only a
second call naming `session-harvest` explicitly found that its `SKILL.md` had moved after session
start and had two unpushed commits — the finding step 0 exists for.

## Evidence

- The two calls and their outputs are in the session named in the frontmatter, immediately after the
  harvest's `sweep` call; the distinctive phrase is the second call's
  `--skill session-harvest
  --skill session-bash-audit`.

## Open questions

[NEEDS CLARIFICATION: make `--skill` additive to the defaults, or reword the SKILL.md sentence to
say "replaces"? Additive matches the prose and the intent — the harvest's own skill should never be
the one skipped — and `--all` already exists for the replace-everything case.]

## Recommended direction

Make `--skill` extend the default set, with a test that `--skill x` still reports session-harvest.
