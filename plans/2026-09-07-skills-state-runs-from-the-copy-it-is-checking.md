---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/power-user-linux-setup
source_session: 3ad94750-3d54-410e-9c1b-9ad44ffc7e14.jsonl
source_moment: 2026-09-07T11:08:03+03:00
---

# `skills-state` answers the staleness question from inside the stale copy

## Context

Step 0 of `session-harvest` exists because a harvest can silently run an older version of itself.
The command that detects it is `skills-state`, and on a stale install **that command is itself the
old version** — so the check that guards against running superseded code is the one piece of code
whose superseding it cannot report.

Observed 2026-09-07 from a `power-user-linux-setup` harvest. `skills-state` correctly reported
`session-harvest` as "install is stale … the stale part includes scripts/", listing six commits. It
was right, and it was run from `~/.agents/skills/session-harvest/scripts/harvest.py` — one of the
stale files it was reporting on. The diff was benign this time: the checkout's `harvest.py` added
`last_activity` and `parentage` (both in `sweep`), and nothing in `skills-state`, `boundary` or
`transcript` had changed, so every step-0 answer was the same one the current code would have given.

That is luck rather than design. The three subcommands a harvest runs **before** it can know the
install is stale are `boundary`, `transcript` and `skills-state`, and a commit touching any of them
produces the same shape as everything else this step is written about: an answer that reads exactly
like a current one.

## Open questions

[NEEDS CLARIFICATION: **which of three fixes, and the cheapest may be sufficient.** (a)
`skills-state` re-execs itself from the checkout when it finds its own skill stale and re-prints —
self-correcting, but a script that re-runs itself from a path it discovered is a bigger promise than
this needs. (b) It prints one line naming which of its own subcommands differ between install and
checkout, so the reader knows whether the answers already collected are affected — that is what the
SKILL.md prose already asks the reader to work out by hand, and it is one `git diff --stat` away.
(c) `SKILL.md` says plainly that the three pre-check subcommands ran from the copy under test and to
re-run them from the checkout when `scripts/` differs, which costs nothing and is the same
instruction the step gives for every _other_ command.]

[NEEDS CLARIFICATION: **is the ordering fixable at all?** The boundary has to be the first command
of the run, and it comes from the same script. Taking it from the checkout would require resolving
the checkout first, which is `skills-state`'s job — so some call is always made before the staleness
answer exists. That argues for (b) or (c) over (a): the aim is to make the reader's exposure legible
rather than to remove it.]

## Recommended direction

(c) plus the reporting half of (b): a sentence in step 0, and a line in the subcommand naming which
of its own entry points differ. Both are additive, neither changes what the command does.

Filed alongside `2026-09-07-diff-skill-md-instead-of-rereading.md`, which another session filed the
same day about the SKILL.md half of step 0. They are adjacent, not halves of one topic — that one is
about how the reader should consume a difference the check reports, this one about the check's own
blind spot — but whoever absorbs them should read both before deciding.

## Evidence

Session `3ad94750-3d54-410e-9c1b-9ad44ffc7e14.jsonl`, 2026-09-07, in `power-user-linux-setup`.
Distinctive phrase: _"Step 0 flags a stale install of the harvest skill itself — including
`scripts/`, which this run has already executed."_ The run then diffed both files and switched to
the checkout for `turns`, `sweep` and `claims`, which is the manual version of the fix proposed
above.
