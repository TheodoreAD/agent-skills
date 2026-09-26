---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/repo-tasks
source_session: a9904181-df08-4eb5-945e-8aab9336d457.jsonl
source_moment: 2026-09-26
source_plan: plans/2026-08-25-consumer-transitions.md
---

# `claims` counts "gate green" and misses "Green, 707 tests"

## Context

**This belongs with `plans/2026-09-13-gate-re-has-no-term-for-the-confidentiality-scan.md`**, which
already owns the shape — a matcher whose vocabulary was written for one phrasing, under-reporting
silently — and which cites the `claims` instance from 2026-09-06 as prior art: _"`claims` reported
`0 green-gate messages` for a session whose text said 'both CI legs green' six times, because its
vocabulary was the local gate's."_ That instance was filed and fixed; `claims` now counts CI claims
in a separate bucket, which this session saw working. Filed as its own plan rather than added to
that one because that plan is `agent-skills`' own and not this session's to edit.

Found during a `session-harvest` run in `repo-tasks` on 2026-09-26. Nothing was written to
`agent-skills`.

## Evidence

`python3 $H claims --until <boundary>` reported:

```
# 1 message(s) told the user a gate or suite was green
# 2 message(s) told the user CI was green — counted apart, see below
```

The session's own assistant text contains **four** such assertions across three messages. The one
`claims` found, and the one it missed:

| said                                     | counted |
| ---------------------------------------- | ------- |
| `..., gate green, 716 tests.`            | yes     |
| `Green, 707 tests. Now the reporter ...` | **no**  |
| `10 passed in 89.17s` (the canary tier)  | as CI   |

So the miss is one phrasing: a gate-green claim that **does not contain the word "gate"**. The same
session said it both ways within fifty minutes, which is what makes this a vocabulary gap rather
than a stylistic quirk of one run — the second sentence had a heading two lines above it doing the
work the word "gate" does in the first.

**Counted by hand from the transcript**, with a pattern covering `gate (passed|green)`,
`green,? N tests`, `all N pass` and `N passed`, over `type == "assistant"` text blocks. Four
matches, three distinct messages.

## Why it is worth fixing rather than noting

It changed nothing this run and that is the argument, not the objection. `pipefail` was in force, 8
of the 10 masked calls wrapped a suite, and every green stood on a real exit code — so the
under-count cost nothing **this time**. The number's whole purpose is the other case: a session
without `pipefail` where the re-run comes back red, and the count is how many sentences in the
conversation are then known to be wrong. Under-reporting there understates a live inaccuracy with a
reader, in the one zone of the report reserved for what needs action now.

The `session-harvest` step that reads this number already carries the rule that caught it — _"a zero
from any of these instruments is a claim, and you are holding the evidence to check it"_ — and it
generalises one step further than it currently states: **a suspiciously low count wants the same
check as a zero.** One is not zero, so nothing in the wording prompted the hand count; it happened
because the reading session remembered saying it more often.

## Recommended direction

Add the phrasing to the matcher rather than broadening it toward "any sentence with 'green' in it",
which would start counting prose about greenness — this very plan would score. The narrow addition
is a test-count assertion adjacent to a success word: `green, N tests`, `all N pass`, `N passed`,
with the gate/suite noun optional, since the number is what makes it a claim about a run rather than
a remark.

Worth checking two adjacent shapes while in there, both of which this session also produced and
neither of which is obviously in or out:

- **A bare count with no success word at all** — "716 passed in 2.06s" quoted from gate output.
  Reads as a claim to a user, and is the commonest way a green gets asserted.
- **A claim about a repo's CI made from `gh run list --json`** — already bucketed apart and
  correctly so, but the separation only holds while the reading is JSON; a session that watches
  through a filter and then says "green" is making the masked-exit claim in CI clothing.

And extend `session-harvest`'s own "check a zero you have reason to doubt" rule to cover a low
count, since that is the sentence that would have prompted this hand check rather than luck.

## Verification

Done in `558c814`. `harvest.py claims --session a9904181-…` on the originating session now lists
"Green, 707 tests" among the gate claims, and the canary's "10 passed in 89.17s" moves from CI to
gate. `test_a_green_with_a_test_count_is_a_claim_without_the_word_gate` holds the must-match and
must-not-match cases. Across this machine's transcripts the change adds 53 counted lines to 1,135,
and a random 40 of them read as real claims.

## Migrated to

- **The code itself:** the comment above `GREEN_CLAIM_RE` in
  `skills/session-harvest/scripts/harvest.py` records the incident, why the count rather than the
  noun is required, and the corpus measurement.
- **Usage docs:** `session-harvest/SKILL.md`'s doubtful-zero rule now covers a count lower than the
  session remembers, with this incident as its dated evidence.
- **Deliberately not migrated:** the second adjacent shape, a CI green claimed after watching
  `gh run list` through a filter. Telling it apart needs the command that preceded the sentence,
  which a sentence matcher cannot see. The skill's CI paragraph already asks the reader whether the
  run was read as JSON.
