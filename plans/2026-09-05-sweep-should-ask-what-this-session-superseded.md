---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 86b6d25d-eb68-4751-b989-ad45931ef62a.jsonl
source_moment: 2026-09-05T17:25:20+03:00
---

# `session-harvest` step 5 has no check for what this session made stale elsewhere

## Context

Step 5 asks, thoroughly, what is dangling **for** this session: unpushed commits, orphaned
processes, CI, the absorb queue, `depends_on` plans this repo is waiting on. Every one of those
points outward from the session.

Nothing asks the inverse: **did this session's work invalidate something already written down in
another repo?** A plan describing a mechanism the session just replaced is not dangling state, not a
process, not a git finding and not an unkept promise — no check reaches it, and the plan itself
cannot notice, because the session that wrote it is gone.

## What it cost, this run

A `repo-tasks` session replaced the gate-output mechanism that `agent-skills`'
`plans/2026-09-05-a-piped-gate-that-cannot-lie.md` (`status: planned`) records as its landed
layer 2. Two plans in that repo now describe an implementation that no longer exists, and — the part
that matters — that plan's `## Verification` schedules `audit.py --days 7 --compare <baseline>` a
week later, with a baseline saved specifically to isolate layer 2's effect. That comparison would
now run against a week of sessions in **neither** mode, and a null result would read as "the quiet
gate did not reduce piping", the opposite of what it would show.

The harvest found it, but not because any step asked. It surfaced while chasing step 5's "is this
finding already owned" thread for an unrelated `head`/`tail` rate, which is luck rather than
procedure — and the skill's own step 6 names that exact signal: _"the run's best finding came from
something no step asked for. Both mean the procedure is mis-aimed, and the second is the easier to
overlook because the finding still got made."_

## Two neighbours already filed, and why this is not either of them

Both were filed against this repo the same day, from the same `repo-tasks` work, and all three are
"step 5 only sees this machine". Read them together on absorption; merge only if they genuinely
collapse.

- `2026-09-05-sweep-misses-downstream-consumers-of-a-pushed-library.md` — what a push **obliges**
  elsewhere: consumers install `main`, so they need sweeping. **Forward** in time, and about code.
  This plan is the inverse: what a change **invalidates** in something already written. Its example
  is in fact the same session, and both findings are true of it at once — the consumers are unswept
  _and_ the parent plan is stale.
- `2026-09-05-an-absorbed-plan-cannot-be-corrected.md` — a filed plan going stale between filing and
  absorption, where the filing repo changed its mind. Same family, different window: that one is
  about a plan in transit, this one about a plan long since absorbed, landed and retired, whose
  **implementation** was later replaced by a third session.

The distinguishing cost is the one neither neighbour has: a **scheduled measurement**. A stale
description is read by a human who can notice; a `--compare` run a week later emits a number with no
signal that its subject moved.

## Recommended direction

A sweep bullet, and a mechanical half in `harvest.py`.

**The bullet** — after "Whether a finding is already owned", which is its reactive twin:

> - **What this session made stale somewhere else.** Every other check here asks what is dangling
>   _for_ this session. A plan in another repo describing a mechanism this session just replaced is
>   the inverse, and nothing surfaces it: it is not dangling, not a process, not git state, and the
>   session that wrote it is gone. The cost is not the stale prose — it is a **scheduled measurement
>   whose subject moved**, which produces a confident wrong number rather than an error. Ask it
>   whenever this session changed a mechanism rather than adding one, and search the other repos'
>   `plans/` and the store for the thing changed, not for this repo's name.

**The mechanical half**: `sweep` already knows every path this session wrote to. For a session that
modified or deleted a source file, grep the store and sibling repos' `plans/` for the **basenames of
files it changed or removed** (`steps.py`, `quality.py`) and for the short SHAs of commits its own
work replaced, and list any plan naming one. Cheap, bounded, and it would have found this instance:
`quiet-gate-changes-what-the-instruments-see.md` names `ba9e8e6`..`4c0bd3a` verbatim, and the parent
plan names `repo_tasks/quality.py`.

[DECISION: report candidates, never a verdict. Whether a plan is actually stale needs reading it — a
plan naming `quality.py` may be about something else entirely. The same shape as the `depends_on`
bullet, which lists the tagged plans and leaves the sorting to the reader for the same reason.]

[NEEDS CLARIFICATION: scope of the search. Sibling repos' `plans/` plus both store tiers is the
obvious set and is what the sensitive tier makes awkward — a `repo-tasks` session has no business
reading a client's plans, and the shareable tier alone would have found this instance. Recommend
shareable store plus the repos under `projects_root` that already keep `plans/`, and say so in the
output rather than searching everything.]

[DEFERRED: the deletion case is the sharper one and is not covered by basenames alone. This session
deleted `steps.py` outright; a plan citing it now cites nothing, and `plan-docs`' `refs` answers
exactly this question for a plan file but not for a source file. Possibly `refs` grows a
`--path <source file>` mode rather than `harvest.py` growing a second implementation.]

## Evidence

- The filing this produced: `2026-09-05-layer-2-was-replaced-after-the-parent-plan-recorded-it.md`,
  in this repo's store mirror.
- `repo-tasks` `d322392`..`7db8b29`, pushed 2026-09-05, CI green — the replacement.
- The distinctive phrase to search the source transcript for is _"Layer 2 of
  `a-piped-gate-that-cannot-lie` — a multi-layer design I replaced without knowing it existed"_.

## What this run found no fault with

Recorded so the next harvest does not re-litigate them: step 0's `skills-state` correctly read a
**dirty** checkout across all four skills, named the right remedy (none — another session is
mid-restructure) and stopped a re-install being offered; the `--since` re-read branch correctly
fired on a commit that was not this session's, and diffing installed-vs-checkout `SKILL.md` was the
cheap way to act on it; and `turns` recovered the whole brief including the answer that carried the
run's second half.
