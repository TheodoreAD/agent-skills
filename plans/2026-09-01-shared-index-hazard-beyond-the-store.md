---
status: in-progress
updated: 2026-09-01
---

# The shared-index hazard beyond the store: a repo's own `plans/`, and the retirement deletion

## Context

Split out 2026-09-01 from `2026-08-29-store-index-shared-between-sessions.md`, now **retired**
(`plans.py archive --file` reads it back). That plan's finding landed: `plans.py commit` builds a
commit from `HEAD` plus one path through a private index, and `SKILL.md` tells sessions to use it
instead of `git add && git commit`. Its rationale is in `references/design-rationale.md` under "Why
committing one plan is a command rather than a git incantation".

Two of its questions were never answered, and both are about where the mechanism stops rather than
whether it works. They are here so that retiring a landed plan does not silently drop them.

## Open questions

[NEEDS CLARIFICATION: **does the hazard apply to a repo's own `plans/` too, and should `commit` be
the general advice rather than the store-specific one?** Parallel sessions on this machine share
every working tree, not only the store's, so in principle yes. It has been measured only in the
store — plausibly because two sessions rarely commit to the same repo within seconds of each other,
while the store is the one repository every session writes to. `SKILL.md` currently scopes the
instruction to store plans. Deciding this is a wording change plus, possibly, a broader claim in
`~/AGENTS.md`, whose "stage by path, never `git add -A`" rule is the same concern one level up and
already applies to every repo.]

**The retirement deletion is answered — landed 2026-09-01.** `commit` now takes a path the working
tree no longer has, resolving it against `HEAD` instead of `locate`, and stages the removal in both
halves of the retirement's ordinary states: the file merely removed, and `git rm` having already
staged it. Two findings came out of building it, both now in the code and its tests:

- `git add -- <path>` records a removal only while the index still holds the entry. Once `git rm`
  has staged the deletion there is nothing left for the pathspec to match and the same command is a
  fatal error — so the shared-index staging has to skip when the removal is already staged, while
  the private index, read from `HEAD`, takes both without special-casing.
- **`git rm` prunes the directory it just emptied**, which is the ordinary case for a store mirror
  holding one last plan. Resolving the repository from the file's parent then fails on a cwd that no
  longer exists and reads as "not a git repository", which it is not.

`SKILL.md`'s retirement step now names the command.

## Recommended direction

One question left, and it wants a measurement rather than a decision: whether any repo other than
the store has actually had a commit swept by a parallel session. The transcript store can answer it
the same way the 142-call figure was measured. Until it does, the honest state is that the hazard is
general in principle and observed only in the store, which is what `SKILL.md` says.
