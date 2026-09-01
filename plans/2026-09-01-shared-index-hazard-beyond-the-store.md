---
status: landed
updated: 2026-09-02
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

## Outcome, 2026-09-02

**The remaining question wanted a measurement and got one.** Across the whole transcript store,
23,045 Bash calls:

| commit calls                    | count | symptom observed |
| ------------------------------- | ----: | ---------------: |
| targeting an ordinary repo tree |  1514 |            **0** |
| targeting the store             |   269 |            **1** |

So the answer to "should `commit` be the general advice?" is **no, and the scoping in `SKILL.md` is
already right**. The hazard is general in principle and observed only where the plan predicted it
would be: the store is the one repository every session writes to, while two sessions rarely commit
to the same repo within seconds of each other. `~/AGENTS.md`'s "stage by path, never `git add -A`"
carries the general form for every repo, which is the correct level for it.

[PITFALL: **the first cut of this measurement was 17 hits across six repos and every one was
false.** The phrase "no changes added to commit" is `git status`'s ordinary wording for an unstaged
tree, so a search for the symptom text alone finds mostly healthy status output. Filtering to calls
that are actually `git commit` dropped it to one. The plan-level lesson is the one this repo keeps
relearning: run the inner command once and look at what it returns before believing a count built on
it.]

The measurement's own blind spot is recorded with the finding rather than left implied: it sees the
**loud** failure, where the sweep took everything staged and the follow-up commit had nothing left.
A partial sweep commits successfully with an extra file and is silent — which is the case that
needed `git log -- <path>` to find the first time. "The loud case is store-only" is the claim; "the
silent case does not happen" is not.

## Migrated to

- `skills/plan-docs/references/design-rationale.md`, "Why committing one plan is a command rather
  than a git incantation" — a `[DECISION:]` carrying the 1,514-to-269 split, why the scoping stays
  as it is, and the blind spot above.

Nothing else outstanding: the retirement-deletion half landed 2026-09-01 and its two findings are
already in the code and its tests.
