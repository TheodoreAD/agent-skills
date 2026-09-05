---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: 25ea8788-b99d-43a2-9611-2d0c1f207694.jsonl
source_moment: 2026-09-05T23:43:48+03:00
---

# Three existing plans confirmed by one harvest — evidence, not new findings

## Context

**This file is evidence for three plans that already exist here, and it asks to be merged into them
rather than kept.** A harvest in `power-user-linux-setup` hit all three in one run; each is already
owned, so filing three separate plans would split three corpora that are already accumulating, and
the skill's own rule says an owned finding's numbers belong in the plan that owns it. Filing at all
is only because a session outside this repo may not write here.

Merge each section into its named plan and delete this file. Nothing below is a proposal, and none
of it changes any of the three decisions already recorded.

## 1. Into `2026-09-05-skills-state-should-resolve-its-own-since.md`

A third instance, and the largest over-count on record. That plan reports 9-vs-8 commits from
substituting midnight local, and a second session that reordered the block by hand with no wrong
number.

This run substituted **14:00 local** — the only bound to hand at step 0, since `transcript` has not
run yet — and got **10** moved commits for `session-harvest`, **3** for `plan-docs` and **6** for
`session-bash-audit`. Re-run with the real start (`2026-09-05T16:36:54.394Z`, from `transcript`):
**5**, **0** and **3**.

The `plan-docs` row is the one worth adding, because it is a different failure from an inflated
count: 3 became **0**. The wrong value said `plan-docs` had moved after the session began, which
routes into the "re-read `SKILL.md` from whichever side is ahead" branch — the most expensive branch
in step 0 — for a skill that had not moved at all. The commits it named were real and all predated
the session; only the comparison was wrong. So the flag's cost is not only that a number reads high,
it is that a **clean skill can be routed into the staleness branch**, and nothing downstream of that
would have revealed the mistake.

Consistent with the plan's existing decision; no change to it.

## 2. Into `2026-09-03-two-plans-one-subject-absorb-cannot-pair.md`, its "second, smaller instance"

That section records `skills-state`'s verdict for `plan-docs` moving between two harvests **thirteen
hours apart**, with the remedy inverting. The same thing happened here **within one step 0, ninety
seconds apart**, and the pair is worth recording because the interval is what makes it feel safe.

- 23:43:5x — `session-harvest`:
  `checkout DIRTY (SKILL.md itself is uncommitted) — work in progress;
  a re-install cannot deliver it, so report and move on`.
- 23:45:2x — same repo, same skill:
  `unpushed skill work (1 commit(s)) — the push belongs to whoever
  authored them`.

A parallel session committed `4345dce` at 23:44:21, in the gap. Two different rows of step 0's own
four-row table, two different actions, ninety seconds apart, with nothing in either output hinting
the other reading existed. The existing section's proposed fix — one clause saying the verdict is a
reading rather than a fact — covers this unchanged; what this instance adds is that "re-read it at
report time" is not a long-interval precaution, and a harvest that runs `skills-state` once at the
top and reports it at the bottom is exposed even on a fast run.

## 3. Into `2026-09-05-store-commit-has-no-multi-file-form.md`

Reproduced verbatim, from a session that had not read that plan. Three plans were absorbed together
and the natural call was one commit for the set:

```
plans.py commit <a>.md <b>.md <c>.md -m "power-user-linux-setup: absorbed, three plans leave the store"
plans.py: error: unrecognized arguments: <b>.md <c>.md
```

Recovered as three commits, one per file, with three messages that each describe one third of one
logical change. Adds nothing to the diagnosis; useful only as a second occurrence in a different
repo on a different day, which is what separates an awkwardness from a shape.

## Recommended direction

Merge, then delete. If any section turns out to add nothing its plan does not already say, drop that
section rather than carrying it — a confirmation that changes no decision is worth one line at most,
and three of them are not worth a file.
