---
status: landed
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

[DECISION: **(c) plus the reporting half of (b) — settled with the user 2026-09-07 and built the
same day.** `SKILL.md` says the three pre-check subcommands ran from the copy under test, and
`skills-state`'s verdict names which of its own subcommands actually differ. (a), re-execing from
the checkout, was refused as a bigger promise than the problem needs: a script that re-runs itself
from a path it discovered, to remove an exposure that cannot be removed anyway.

**The ordering is not fixable, and that is what settles it.** The boundary is the run's first
command and comes from the same script; taking it from the checkout means resolving the checkout
first, which is `skills-state`'s own job. Some call always precedes the staleness answer, so the aim
is a legible exposure rather than none.]

[DECISION: **compare per definition, not per file.** A file-level diff answers "something changed",
which is the question the reader already has. Reachability from each `cmd_*` entry point — through
module-level functions **and** constants, since a changed pattern is the commonest way a
subcommand's behaviour moves while its own body stays byte-identical — answers "does this affect
what I have already read". On the session that filed this it would have printed `sweep` and nothing
else, which is the whole finding. Three-valued like the sweep's other checks: a file that will not
parse reports that it could not tell, never "nothing differs".]

[DECISION: **the note fires only when the running script is the copy being judged.** A harvest that
has already switched to the checkout is executing current code and has nothing to re-run, so warning
it would be the check misreading its own situation — the shape this whole plan is about. The
condition is `Path(__file__)` under the installed skill, which is the fact itself rather than a
proxy for it.]

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

## Migrated to

- **The behaviour** — `skills/session-harvest/scripts/harvest.py`: `entry_points_differing`, its
  `_module_definitions`/`_reachable` helpers, and `_note_own_staleness`, which appends to the
  verdict only when the running script is the copy being judged.
- **The rule a reader follows** — `SKILL.md` step 0, the paragraph saying the three pre-check
  subcommands ran from the copy under test and what the verdict now tells them about it.
- **The reasoning** — `references/rationale.md`, "What step 0 owes a reader once it has found a
  difference (2026-09-07)", which also carries the rejected re-exec option and why the comparison is
  per definition rather than per file. That section covers this plan and the SKILL.md diff plan
  together, and says why the two were nonetheless kept apart as plans.
- **Tests** — `tests/unit/test_harvest.py`: the per-definition comparison, the unparsable-file case,
  the two verdict branches, and the harvest already running from the checkout.

Not migrated: the observation that this instance was benign, which is in the rationale as the
measurement rather than as a reassurance — the next one need not be.
