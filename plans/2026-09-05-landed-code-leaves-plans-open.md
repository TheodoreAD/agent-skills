---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: bb66cbe5-7369-4f49-a8e7-7949db5ff99a.jsonl
source_moment: 2026-09-05T09:09:33Z
---

# A plan whose code has landed still says `idea`, and nothing notices

## Context

`plan-docs` says to bump a plan's status with `set-status` as work proceeds, and its retirement
prompt in `absorb` trusts the status field it reads — a stated, known limit. This is the case that
limit hides: a session builds everything a plan designed, documents it, and never touches the plan.
The plan keeps saying `idea` with open questions the code has answered, `absorb` never raises it
because nothing is terminal, and the next session reading `list` sees live design work.

Two instances in `repo-tasks`, found 2026-09-05 only because the session read the code rather than
the plan. `plans/2026-08-25-release-without-release-branch.md` (namespace name, release-task home)
and `plans/2026-09-04-versioning-policy.md` (should `cut` push, where does the Release task live)
were last edited at `3ac26b0` on 2026-09-04; the answers landed the same evening in `e1d0306`,
`a04b2ce`, `33017fa`, `cc49ebb`, `02c3ed7` and the docs in `7da47dd`. The session that landed them
ended without a status bump on either plan. The harvest session nearly proposed building `trunkflow`
as the night's work before checking `git log` on the module.

This is the third shape in the harvest skill's misuse taxonomy: the rule is fine and was simply not
followed, so the fix is measurement or a mechanism rather than a rewording.

## Evidence

- The two plans' last plan-commit versus the code commits, all 2026-09-04, listed above; the
  reconciliation is `repo-tasks` commits `6850056` through `58317fa`, 2026-09-05.
- The harvest session's distinctive phrase to search for: the user answering "i don't want to do
  releases yet, those would need actual artifact stores to work with".

## Open questions

[NEEDS CLARIFICATION: is there a cheap detector? A plan names files, tasks and commits in prose; a
check that a plan's `updated:` predates the last commit touching any `src/` path the plan names
would flag both instances above and is a grep plus `git log -1 --format=%cd -- <path>` per name.
Against: prose names are noisy (a plan citing `quality.py` as context is not stale when `quality.py`
changes), so this may only work as a hint in `list`, never as a gate.]

[NEEDS CLARIFICATION: or is the fix on the landing side — `session-harvest`'s loose-ends pass asking
"did this session land something a plan designed, and does that plan say so?" That is where the
session with the knowledge is. The harvest already checks plan status for work the session finished;
the miss here is that the landing session apparently did not harvest at all, so a harvest step
cannot reach it.]

## Recommended direction

Measure first: across the family, how many plans in `idea`/`planned` name a task or module that
landed after the plan's `updated:`. If it is rare, a line in `plan-docs`' "Promoting a plan" is
enough; if it is common, the `list` hint is worth building.
