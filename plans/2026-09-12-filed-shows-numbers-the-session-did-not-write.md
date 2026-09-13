---
status: idea
updated: 2026-09-12
source_repo: github.com-personal/repo-tasks
source_session: db005386-041e-4f80-acbe-6e944677e6fa.jsonl
source_moment: 2026-09-12T09:12:00Z
source_plan: # reports a fact about the tool's output
---

# `harvest.py filed` prints number-bearing lines from plans the session only appended to

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

**Related, kept apart:** `2026-09-09-harvest-attribution-reads-a-path-as-authorship.md` is the
commit-level form of the same error — `filed` crediting a commit because this session wrote or read
a path in it. Separate because that one is about commits and command classification, this one about
lines and a diff; but the label that plan settles on is the one this plan's hedge should reuse, so
the two halves of `filed` do not hedge in two voices. Absorbed together 2026-09-13.

## Open questions

[NEEDS CLARIFICATION: attribute by diff, or label and leave it? A diff of the session's own writes
against the file as it stood at session start is the exact answer, and it needs the pre-session
content — `git show <sha-at-session-start>:<path>` where the plan is committed, nothing where it is
not. A label is one line and always available: "lines may predate this session; re-derive only what
this session wrote." The label is honest and cheap; the diff is what the step's instruction actually
assumes.]

[NEEDS CLARIFICATION: does the same reasoning reach the store rows? A store commit is attributed by
write-or-name, which is a real signal; the number-bearing lines have none. Worth checking whether
the two lists should print their confidence differently rather than looking alike.]

## Recommended direction

1. **Cheapest honest fix first**: mark the sampled lines as "whole file, not only this session's
   writes" in the output, so the step's instruction is read against what the data supports.
2. If the diff is wanted, take it from git rather than from the transcript — the transcript's edit
   records give the new text, not the file's prior state, and a plan the session created has no
   prior state at all (that case is already unambiguous and needs no diff).
3. Worth a test either way: a fixture plan with a pre-existing number-bearing line and one appended
   by the session under test is a two-line assertion that pins whichever rule is chosen.
