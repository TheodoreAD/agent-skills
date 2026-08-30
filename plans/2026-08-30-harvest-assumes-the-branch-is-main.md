---
status: landed
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

[PITFALL: The calm zero is the pipe, not `git log`. This plan originally recorded the cause as git
treating an unknown revision on the left of `..` as empty when the output is being counted. Checked
2026-08-30 against the same store: `git log origin/main..HEAD --oneline` exits **128** with
`fatal: ambiguous argument 'origin/main..HEAD': unknown revision or path not in the working tree` —
loud, and unmissable. Adding `| wc -l` is what discards the exit code and leaves `0` as the only
number on the line. So this is the third instance of the failure the sweep already prohibits twice —
a pipe destroying the signal on `git fetch` and on `gh run watch` — landing this time on the
ahead-count itself, compounded by a branch name nobody resolved.]

[DECISION: name the command, not the failure — resolved in favour of
`git rev-parse --abbrev-ref '@{u}'`. The counter-argument was that the sweep already carries two
"type this exact command" bullets and a third makes the step read as a script. It loses because the
two existing ones were themselves rewritten into that shape after prose versions failed repeatedly,
and this bullet's own evidence is a session that had the prose in front of it.]

[DECISION: assuming `main` is wrong more often than it is right, so the rule is unconditional rather
than a caveat about the store. Measured 2026-08-30 across every clone under this machine's projects
root: 71 repos, of which 22 are on `main` — fewer than the 23 on `master`, with the remaining 26 on
a feature branch. The exception framing the plan was drafted with does not survive the count.]

## Design

One insertion in `skills/session-harvest/SKILL.md`, step 5's git bullet, placed **before** the
`git fetch` sentence: a fetch that succeeds against the right remote still leaves the count wrong if
the branch is wrong, so the existing "read the fetch's exit code" advice passes cleanly through this
bug. It carries the resolve-the-branch command, the 22-of-71 measurement, and the unpiped-count rule
with the exit-128 evidence.

## Files touched

- `skills/session-harvest/SKILL.md` — step 5, the "Git state, every repo the session touched"
  bullet.

## Verification

- `git -C <the plans store> rev-parse --abbrev-ref '@{u}'` → `origin/master`, the ref the bullet now
  tells a run to compute.
- `git -C <the plans store> log origin/main..HEAD --oneline` → exit 128,
  `fatal: ambiguous argument`.
- The same command with `| wc -l` → `0`, exit 0. The two runs are the whole finding.
- Branch tally across the projects root: 22 `main`, 23 `master`, 26 other, 71 total.
- `inv quality.precommit`.

## Migrated to

- **The rule itself** → `skills/session-harvest/SKILL.md`, step 5's git bullet: resolve the branch
  with `git rev-parse --abbrev-ref '@{u}'`, run the count unpiped, placed ahead of the fetch check.
- **Both decisions and the corrected mechanism** → `skills/session-harvest/references/rationale.md`,
  "Why the sweep's checks name a command rather than the mistake (2026-08-30)". It is written as the
  general case rather than as this plan's story, because the same pipe failure already governs the
  `git fetch` and `gh run watch` bullets and had never been stated once in one place.

Not migrated: the verification transcript above — the two commands are in the rationale section that
needs them, and re-running them is cheaper than reading a log of someone else having run them. No
inbound references (`refs` returned 0) and no section-shaped citations, so nothing needed
repointing.
