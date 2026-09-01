---
status: idea
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

[NEEDS CLARIFICATION: **the retirement deletion cannot go through `commit` at all, and nothing says
what to use instead.** Confirmed 2026-09-01: `cmd_commit` resolves its argument with
`candidate.is_file()` or `locate(...)`, and both require the file to exist —
`plans.py commit plans/<a deleted plan>.md` fails with `no plan named …` before any git call.
Retirement is exactly the case where the file is gone, so the one step the convention describes as
irreversible is also the one still done with a bare `git rm`/`git commit` in a shared index.

Three shapes, unpriced: teach `commit` to accept a path that no longer exists (the private-index
machinery already stages a deletion correctly — `git add -- <path>` stages a removal, so only the
argument resolution is in the way); give retirement its own command; or leave it as a documented
exception and say so, which is at least better than the current silence.]

## Recommended direction

Answer the retirement one first — it is a concrete gap in a mechanism that already exists, and the
fix is plausibly a few lines in argument resolution plus a test that retires a plan through the
command. The general-vs-store question is a wording decision that wants a measurement first: whether
any repo other than the store has actually had a commit swept, which the transcript store can answer
the same way the 142-call figure was measured.
