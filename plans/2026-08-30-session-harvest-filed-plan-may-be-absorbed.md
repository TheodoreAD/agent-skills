---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# A plan filed earlier in the session may be gone by the time the report names it

## Context

From a `repo-tasks` session, 2026-08-29/30, running `/session-harvest`.

Early in that session a plan was filed for another repo —
`plans.py new attribution-session-url-still-emitted --for github.com-personal/power-user-linux-setup`,
committed in the store as `af471bb`. Hours later, at harvest time, `SKILL.md`'s report format asks
for a "**To a plan in another repo**" group naming "the filename and target repo".

By then the file did not exist. A parallel session had absorbed it into
`power-user-linux-setup/plans/`, merged its content into that repo's existing
`2026-08-29-attribution-session-url-off.md`, and committed the store-side deletion in `aee0aca`. The
store commit this session made was also already pushed — by that other session, not this one.

So a report written from the session's own memory would have named a path that no longer exists, and
would have said "unpushed" about a commit that was published. Both statements read as ordinary
status lines; nothing in them looks like a guess.

## Why the existing checks do not catch it

Step 5 sweeps unpushed commits, processes, CI and shared stores. None of those covers _a file this
session created in the store_, because the store is version-controlled and clean — absorption is a
normal, committed operation by the session that owns the target repo, not damage. The check is not
"is something broken" but "is what I am about to report still true".

It is the same class as the bullet already there for parallel sessions and the ahead-count: on a
machine running several sessions, this session's record of what it did is not evidence about the
current state.

## Recommended direction

One additive bullet, in the report section's "**To a plan in another repo**" group (it belongs with
the reporting rule rather than in step 5, because it is about what the report claims):

> Before naming a filed plan, confirm it is still in the store. Another session may have absorbed it
> into the target repo — normal, and it means the work arrived — in which case say so, and check
> whether your store commit was pushed by that session rather than reporting it as pending. `ls` the
> store directory and `git -C $PLANS_HOME branch -r --contains <sha>` answer both.

Small enough to land with the other `session-harvest` edits already queued, and it needs the same
care as those: the skill's source was being edited by a live session while this was written, so this
is filed rather than applied.

Deliberately **not** merged into `plans/2026-08-29-session-harvest-plans-store-sweep.md` on
absorption 2026-08-30, though both are about the harvest and the store: that one adds a bullet to
step 5's loose-state sweep and this one adds a line to the report format, which is the distinction
this plan draws itself. Land them in one pass — they touch the same file for the same reason — but
they are not one edit.
