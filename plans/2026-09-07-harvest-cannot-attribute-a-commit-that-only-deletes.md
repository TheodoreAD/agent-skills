---
status: landed
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_session: 11ef513d-37c0-4bc6-ba25-dd40d8551940.jsonl
source_moment: 2026-09-07T17:25:00+03:00
---

# `filed`'s store attribution marks a session's own absorption commits as another session's

## Context

`harvest.py`'s `store_commits()` decides `this_session` by asking whether a commit touches a path
**the transcript shows this session writing** — `written_paths(entries)`, which reads Write and Edit
tool calls. Its docstring argues the conservative direction is safe: unattributed "is the direction
that cannot make a false claim."

**For a deletion it makes exactly that false claim**, and the shape is not exotic — it is the single
most common way any session commits to the store. `plans.py absorb --apply` _moves_ a plan out of
the store into the repo; the session writes nothing at the store path, so no Write or Edit call
names it, so `this_session` is false for the commit that records the removal.

Confirmed 2026-09-07 in `power-user-linux-setup`, session `11ef513d-37c0-4bc6-ba25-dd40d8551940`.
That session absorbed three plans and committed each removal through `plans.py commit`.
`filed --until` then reported:

```
## store plans: /home/tdumitrescu/plans
    0 commit(s) this session, 20 from elsewhere, since session start
    (another session) 719a495a2  power-user-linux-setup: absorbed, take invoke-stubs 0.2.0
    (another session) 23d5aaa76  power-user-linux-setup: absorbed, announcing auto-mode session row
    (another session) 9268a77c4  power-user-linux-setup: absorbed, corpus re-score decision
```

All three are that session's, made minutes earlier, in the same session that then ran the harvest.
`0 commit(s) this session` is wrong in the one way the docstring says it cannot be.

**Related but not the same defect** — found while checking, after filing, whether either finding was
already owned:
[`plans/2026-09-02-correction-overlap-attributes-parallel-sessions.md`](2026-09-02-correction-overlap-attributes-parallel-sessions.md)
is `_correction_overlap` attributing _another_ session's pushes to this one. This is `store_commits`
attributing _this_ session's commits to another — the same subject, opposite direction, different
function. Two plans rather than one because the fixes do not overlap: that one is about which paths
the overlap set contains, this one about a signal that cannot see deletions at all. Worth reading
together if either is picked up, since a single attribution helper serving both is a plausible
outcome.

## Why it matters more than a mislabelled row

`SKILL.md` step 8 gives the label authority over what the harvest may then do: _"a row marked
`(another session)` is reported, never edited."_ So a harvest that follows the procedure correctly
will decline to correct its **own** absorption commits, on the grounds that they belong to somebody
else. The whole point of the `filed` subcommand — added the same day, in `2993385` — is that a
second harvest corrects what the first one filed rather than trusting memory; this defect points
that mechanism at the wrong set.

It is also self-concealing in the usual way: `0 commit(s) this session` is a plausible number for a
session that did no store work, and nothing distinguishes it from the true zero.

## What landed, 2026-09-08

[DECISION: **the argv route, plus an ordering constraint the question did not anticipate.**
`store_commits` reads this session's Bash commands as well as its write paths, so a commit whose
file this session _named_ is this session's. The docstring's "the direction that cannot make a false
claim" was corrected in the same commit, since it is only ever true for additions.]

[DECISION: **the heading is `(not attributed)`, not `(another session)`** — the third state the
second question asked for. The evidence establishes only that nothing tied the commit to this
session, and the two readings call for opposite next steps. The report now also says what to do when
a row is yours through a door the check cannot see: say so, rather than assuming either way.]

**The ordering constraint is the part worth keeping, because it is a false positive this plan's own
fix introduced and the first live run caught.** A bare name match attributed two commits a parallel
session made at 00:18 and 00:20 to this session, because this session ran `absorb --only <file>` on
those same filenames at 00:45. Both sessions legitimately name the same plan; what separates them is
that a command cannot have caused a commit which already existed when it ran. So the match now
requires the naming command's own instant to be at or before the commit's, and an unparseable
instant on either side falls back to not attributing.

That is exactly the parallel-session error the write-path-only version was guarding against,
arriving through the door opened to fix its opposite — which is the argument against the third
candidate above, now with a measurement behind it rather than a suspicion. **The two evidence
sources are not interchangeable: argv needs a timestamp that write paths never did.**

Verified on the session that made the change. Before: its own absorption-removal commit listed as a
stranger's. After: `1 commit(s) this session, 8 not attributable` — the one attributed row being the
pure deletion, and all six of a parallel session's commits correctly left alone.

## Recommended direction

Prefer the argv route: `store_commits()` already receives the transcript entries' written paths, and
the same walk can collect Bash command strings. A commit whose file appears in a `plans.py commit`
argument in this session's own transcript is this session's, ~~with no timestamp heuristic and no
new parallel-session risk~~. Keep the conservative default for everything it does not match, and
rename the heading so an unmatched row does not assert ownership it did not establish.

**Struck 2026-09-08, by the implementation:** the argv route carries exactly that risk and does need
a timestamp. Two sessions name the same plan file all the time — one filing it, another absorbing it
— and without ordering the second session's command claims the first session's commit. The
prediction was wrong in the direction that would have shipped it unguarded, which is why the
correction is left visible here rather than quietly rewritten. See "What landed" above.

Whatever the mechanism, the docstring's claim needs correcting in the same commit — "the direction
that cannot make a false claim" is what made this look safe, and it is only true for additions.

## Evidence

Distinctive phrase from the source session, for the transcript: "The `filed` output marked my own
three store commits as another session's."

The three commits are `719a495a2`, `23d5aaa76`, `9268a77c4` in `~/plans`, all authored
2026-09-07T15:08:4x+03:00, all with subjects beginning `power-user-linux-setup: absorbed,`.
`git -C ~/plans show --stat <sha>` shows each as a pure deletion, which is the condition that
triggers this.
