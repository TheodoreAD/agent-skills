---
status: landed
updated: 2026-09-08
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

## What the measurement said, and what landed 2026-09-08

The recommendation was to measure before choosing between a line in `plan-docs` and a `list` hint.
Measured across 8 repos and 167 open plans:

| signal                                                              | count | share |
| ------------------------------------------------------------------- | ----- | ----- |
| open plans naming a source file that moved after their `updated:`   | 72    | 43%   |
| …restricted to files named three or more times (the plan's subject) | 23    | 14%   |

[DECISION: **neither branch of the recommendation — the cheap detector does not exist, and the
landing-side check does.** 43% is not a hint, it is a property of every open plan; the first
question predicted exactly this ("a plan citing `quality.py` as context is not stale when
`quality.py` changes") and the number confirms it. The subject proxy brings it to 14%, and what
remains is structural rather than tunable: **a session that edits a file makes every plan about that
file look stale**, and no signal available to a script separates a design that landed from a subject
that merely moved. So nothing was added to `plan-docs`' `list`, where a hint firing on one open plan
in seven would be read once and then ignored.]

[DECISION: **the second question's answer — the fix is on the landing side, in the sweep.** That is
where the session with the knowledge is. `sweep` now lists this repo's open plans that name a source
file the session wrote, three times or more, and that were last touched before the session began,
and asks whether the session landed what any of them designed. It says its own measured rate beside
the rows, and `set-status` remains the only thing that changes a status.

The question's own objection to this — "the landing session apparently did not harvest at all, so a
harvest step cannot reach it" — is right and is why the check is worth having anyway rather than why
it is not: it converts a miss that no session catches into one that any _subsequent_ harvest in that
repo catches, since the plan stays open until somebody bumps it.

Verified on the session that built it: three candidates, one of them a plan whose pattern change
that same session had landed an hour earlier and left at `idea`.]
