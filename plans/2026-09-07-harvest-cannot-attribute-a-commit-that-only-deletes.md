---
status: idea
updated: 2026-09-07
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

## Open questions

[NEEDS CLARIFICATION: what is the right attribution signal? Three candidates, and none is obviously
best. **Deleted paths** — read `--diff-filter=D` names as well as written ones, and treat a path
this session _read or absorbed_ as attributable; narrow and targeted, but "absorbed" is not
currently a thing the transcript records as a path event. **The transcript's own commands** — a
`plans.py commit` call names the file it commits in argv, so scanning Bash inputs for the store path
attributes the commit without inferring anything; this is the most direct evidence and is already in
the entries the script walks. **Commit time against session window plus a `plans.py` call in the
window** — cheapest, and the closest to how the image rows are handled, but it re-introduces exactly
the parallel-session error the docstring is guarding against.]

[NEEDS CLARIFICATION: should the unattributed heading say _why_ a row is unattributed? A row that is
another session's and a row the script could not attribute are different findings with different
next steps, and both currently print as `(another session)`. The image rows have the same structure
and solved it with a separate heading; the store rows may want the third state —
`attribution
unavailable` — rather than a binary.]

## Recommended direction

Prefer the argv route: `store_commits()` already receives the transcript entries' written paths, and
the same walk can collect Bash command strings. A commit whose file appears in a `plans.py commit`
argument in this session's own transcript is this session's, with no timestamp heuristic and no new
parallel-session risk. Keep the conservative default for everything it does not match, and rename
the heading so an unmatched row does not assert ownership it did not establish.

Whatever the mechanism, the docstring's claim needs correcting in the same commit — "the direction
that cannot make a false claim" is what made this look safe, and it is only true for additions.

## Evidence

Distinctive phrase from the source session, for the transcript: "The `filed` output marked my own
three store commits as another session's."

The three commits are `719a495a2`, `23d5aaa76`, `9268a77c4` in `~/plans`, all authored
2026-09-07T15:08:4x+03:00, all with subjects beginning `power-user-linux-setup: absorbed,`.
`git -C ~/plans show --stat <sha>` shows each as a pure deletion, which is the condition that
triggers this.
