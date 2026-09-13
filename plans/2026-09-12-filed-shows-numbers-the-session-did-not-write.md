---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: db005386-041e-4f80-acbe-6e944677e6fa.jsonl
source_moment: 2026-09-12T09:12:00Z
source_plan: # reports a fact about the tool's output
---

# `harvest.py filed` prints number-bearing lines from plans the session only appended to

## Landed, 2026-09-13

Retire once the commits are pushed; the reasoning lives in `measurement_lines`' docstring and
step 8.

[DECISION: **attribute by the transcript's own writes, not by a git diff, and hedge the rest**
(`6254193`). The transcript does hold what is needed — not the file's prior state, but the text this
session put in: a Write's content, and an Edit's `new_string` lines that its `old_string` did not
already hold, so the anchor lines an Edit repeats are not claimed. Compared with whitespace removed,
because the gate reflows and re-pads after every write. Everything else is printed
`(authorship unestablished)`, the same hedge the store commits use. On `db005386` all five
`consumer-transitions` lines come back hedged and none claimed.]

The sample limit was a second defect: a long shared plan's first six number lines are its oldest, so
the session's own were never printed. The two lists are now limited separately.

## Context

`session-harvest`'s step 8 says of `filed`: "Re-derive each measurement it prints and **edit the
file**". That is right for a plan this session wrote, and wrong for one it appended a section to —
and `filed` cannot currently tell the two apart, because it lists any plan file the session wrote to
and then greps the **whole file** for lines carrying numbers.

Observed 2026-09-12 in `repo-tasks`, harvest #1 of session `db005386`. The session appended one
section to `plans/2026-08-25-consumer-transitions.md`; `filed` listed that plan with five sample
lines, **none of them written by this session**:

```
/home/.../repo-tasks/plans/2026-08-25-consumer-transitions.md
    - `inv quality.precommit` here: 0 errors, 0 warnings, 294 unit tests.
    | `power-user-linux-setup` | up to date     | 0 errors, 0 warnings, 353 tests | n/a             |
    | `scaffoldapy`            | up to date     | 0 errors, 0 warnings, 27 tests  | 10/10 e2e, 78s  |
```

Those are measurements from sessions on 2026-08-26 and 2026-09-08, in a plan several sessions share.
Followed literally, the instruction sends a harvest to re-derive and edit another session's
five-day-old numbers — expensive, and an edit nobody asked for in a file somebody else is
accumulating.

[PITFALL: **the failure is the same shape the `(not attributed)` fix already corrected one row
down**, which is why it is worth fixing rather than living with. That fix stopped `filed` asserting
a commit was "another session's" when the check simply could not see the door it came through; this
is the mirror — asserting a _line_ is this session's when the only evidence is that the session
touched the file. Both read as specific and both are unfalsifiable from the output alone.]

**Reproduced 2026-09-13 on this plan itself.** The `agent-skills` session that absorbed it added one
paragraph — the cross-reference below — and its harvest's `filed` then listed this file with the
three number-bearing lines from the evidence block above: `294 unit tests`, `353 tests`, `27 tests`.
None were that session's writes; all three came from the filing session in `repo-tasks`. A second
repo and a second session, and the smallest possible edit, which is the case the label or diff has
to get right.

**Related, kept apart:** `2026-09-09-harvest-attribution-reads-a-path-as-authorship.md` is the
commit-level form of the same error — `filed` crediting a commit because this session wrote or read
a path in it. Separate because that one is about commits and command classification, this one about
lines and a diff; but the label that plan settles on is the one this plan's hedge should reuse, so
the two halves of `filed` do not hedge in two voices. Absorbed together 2026-09-13.

## Open questions, answered 2026-09-13

- **Attribute by diff, or label and leave it?** Both halves, from the transcript rather than from
  git: lines found in this session's own writes print plainly, and the rest carry the label. A
  session-start diff would also have credited a line another session added after the start.
- **Does the same reasoning reach the store rows?** It did, and write-or-name turned out not to be a
  real signal of authorship there either. Both lists now print the same hedge for the same kind of
  evidence.

## Recommended direction

1. **Cheapest honest fix first**: mark the sampled lines as "whole file, not only this session's
   writes" in the output, so the step's instruction is read against what the data supports.
2. If the diff is wanted, take it from git rather than from the transcript — the transcript's edit
   records give the new text, not the file's prior state, and a plan the session created has no
   prior state at all (that case is already unambiguous and needs no diff).
3. Worth a test either way: a fixture plan with a pre-existing number-bearing line and one appended
   by the session under test is a two-line assertion that pins whichever rule is chosen.
