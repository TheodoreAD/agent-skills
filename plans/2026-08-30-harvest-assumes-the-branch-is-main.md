---
status: idea
updated: 2026-08-30
---

# The ahead-count is written `origin/main`, and the plans store is on `master`

## Context

`session-harvest`'s live-state sweep says to check unpushed work with
`git log origin/<branch>..HEAD`. The placeholder is right and every run has to substitute something
for it — and the substitution a session reaches for is `main`.

Measured 2026-08-30 during a harvest: the plans store is on **`master`**, so
`git log origin/main..HEAD --oneline | wc -l` printed **`0`**. Not an error, not a warning — a
plausible, calm zero, for a store that was in fact **32 commits ahead**, six of them the session's
own. The run only caught it because the next command listed the branch for an unrelated reason.

[PITFALL: This is the same failure the sweep's own `git fetch` bullet is written about — a count
computed against a ref that does not answer the question, printing a number indistinguishable from
the true one — and the existing wording does not catch it, because that bullet is about a _stale_
ref and this is a _nonexistent_ one. `git log` treats an unknown revision on the left of `..` as
empty rather than as an error when the output is being counted, so nothing surfaces it. A harvest
whose entire purpose is finding unpushed work reported the opposite of the truth.]

## Open questions

[NEEDS CLARIFICATION: Whether to name the command or the failure. The rest of the sweep's bullets
were rewritten to open on the command to type, after prose versions failed repeatedly — this would
follow that pattern with `git rev-parse --abbrev-ref @{u}` (or
`git rev-parse --abbrev-ref
origin/HEAD`) rather than a sentence about branch names. The
counter-argument is that the sweep already has two "type this exact command" bullets and a third
makes the step read as a script.]

[NEEDS CLARIFICATION: Whether anything else in the family assumes `main`. The store is the known
case; `plans.py` resolves its own remote correctly, and the harness repos are all `main`. Worth one
`git -C <repo> branch --show-current` sweep across the machine's repos before wording the rule, so
it says how common the exception actually is.]

## Recommended direction

One line in the live-state sweep's git bullet: resolve the branch rather than assuming it, and say
that an unknown ref on the left of `..` counts as zero rather than failing — which is what makes
this indistinguishable from a clean result.

Worth noting where it goes in the bullet: **before** the `git fetch` sentence, not after. A fetch
that succeeds against the right remote still leaves the count wrong if the branch is wrong, so the
existing "read the fetch's exit code" advice passes cleanly through this bug.
