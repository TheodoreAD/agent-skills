---
status: in-progress
updated: 2026-09-28
source_repo: github.com-personal/ingesta
source_session: 20a2d59c-46f5-4aba-af3d-967f7ac699d9.jsonl
source_moment: 2026-09-28T18:26:30Z
source_plan:
---

# `plans.py push` says too little: not which commits it published, not why it failed, and not that the set moved after the scan

**Merged on absorption, 2026-09-28**, from two plans filed for this repo the same evening about the
same command's output, both merged away into this file under a name covering both:
`2026-09-28-store-push-names-no-outgoing-commit.md` (from ingesta, the success path, whose
frontmatter this file keeps) and `2026-09-28-store-push-failure-hides-git-stderr.md` (from
invoke-stubs, the failure path). The second asked to be merged "if the fix is one change to `push`'s
output", and it is: both are fixed by `push` naming what it is about to publish and what git said
back. Both originals are in the shareable store's history, removed by its absorption commit
`e61e8ba`.

## Context

`~/.agents/AGENTS.md` says, under "Unexplained git/file state": before pushing, read
`git log origin/<branch>..HEAD`; a commit there you did not make belongs to another live session
that may still mean to amend or reorder it, so say so and ask before your push publishes it.

`plan-conveyor` says to push a store with `plans.py push`, never `git push`, and that command prints
only a count. So the documented path for a store push is the one path where the global rule has
nothing to read.

## Evidence

### Success path: a foreign commit published unnamed (ingesta)

Rule shape: **followed the documented command, and the rule it sits beside was not applied.** The
ingesta session named in the frontmatter committed one store removal (`2a80cdab4`) and, on the
user's "Push, then pin 3.14" answer at the moment above, ran `plans.py push`. Output:

```
outgoing:  2 commit(s) — scanning @{upstream}..HEAD
scanned:   clean, against 61 private term(s)
pushed:    ok
```

The second commit was
`2b1261df6 power-user-linux-setup: absorb the FORCE_COLOR plan and the gh-SHA
adherence samples`,
made by a parallel session 98 seconds after this session's own. The session only learned whose it
was by running `git log` after the push, and reported it to the user as already published. The scan
was clean, so nothing confidential went out; what went out was a commit its author had not chosen to
publish.

### Failure path: git's error dropped (invoke-stubs)

`source_repo: github.com-personal/invoke-stubs`,
`source_session: b418c54c-c032-4559-9cf3-6370d926625b.jsonl`, `source_moment: 2026-09-28T19:51:50Z`
— that session ran `plans.py push` on the shareable store. Whole output, exit 1:

```
store:     /home/tdumitrescu/plans  [shareable]
outgoing:  1 commit(s) — scanning @{upstream}..HEAD
scanned:   clean, against 61 private term(s)
FAILED:    git push did not succeed
```

Nothing from git. A `git fetch` right afterwards showed the remote had not moved, so it was not a
non-fast-forward rejection. The store was now 2 ahead instead of 1: a parallel
power-user-linux-setup session had committed `3b820f3` (an absorption) at 22:51:47 +03:00, inside
the window of this push. The likeliest cause is the two sessions pushing at once, but that is a
guess, because the one line that would say (git's stderr) was dropped.

What it cost: the cause went unknown, and the session had to reconstruct state with three read-only
git calls. The push was then deliberately left to the other session, so nothing was lost.

### The scan and the push read different sets (confirmed from code, 2026-09-28)

The invoke-stubs plan asked whether a commit landing between the scan and the push goes out
unscanned. **It does.** `_push_one` in `skills/plan-conveyor/scripts/plans.py` resolves the range
symbolically (`outgoing_range` returns the string `@{upstream}..HEAD`), runs `git log` over it for
the scan, and then runs a bare `git push`, which publishes whatever `HEAD` is at that later moment.
Nothing pins the scanned tip. Had the invoke-stubs push succeeded, `3b820f3` would have been
published without being scanned. So this is a hole in the confidentiality gate, not only a reporting
gap — the sharper of the three findings, and the one to fix first.

## Done 2026-09-28

All three parts of the recommended direction below are implemented in
`skills/plan-conveyor/scripts/plans.py` (`_push_one`, `_run_push`, `push_command`,
`outgoing_range`), with tests in `tests/unit/test_plan_store.py` and a paragraph in the SKILL.md
push section. `push` now names foreign commits; it does not stop on them. What is left is the open
question below, which is a decision rather than a fix.

## Open questions

[NEEDS CLARIFICATION: whether the store should follow the global "name foreign commits before
pushing" rule at all. It is a shared log that every session pushes wholesale, and asking per foreign
commit may be pure friction there — in which case the global rule wants an explicit exception for
the store rather than a silent one.]

## Recommended direction

One change to `push`, three parts:

1. **Pin the tip.** Resolve `HEAD` to a SHA once, scan `@{upstream}..<sha>`, and push
   `<sha>:refs/heads/<branch>` rather than a bare `git push`. A commit landing after the scan then
   stays local for the next push, which scans it.
2. **List the outgoing commits**, one line each (short SHA and subject), the same way `absorb` lists
   plans. That makes the global rule applicable when it applies and costs nothing when every commit
   is the pusher's. Whether a foreign commit should then stop the push, or just be named, is the
   question above.
3. **On a non-zero `git push`, print git's stderr** under the `FAILED:` line, verbatim.
