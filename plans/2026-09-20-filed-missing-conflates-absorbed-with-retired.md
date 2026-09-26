---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/freshful-polite-mcp
source_moment: 2026-09-20T17:08:20Z
source_session: 2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl
source_plan:
---

## Context

`session-harvest`'s `filed` subcommand marks a plan file it cannot find as
`MISSING (absorbed, or moved)`, and `SKILL.md` step 8 tells the reader what to do about it:

> a row marked `MISSING` has been absorbed into the repo that owns it, and there the correction is a
> new filing rather than an edit.

There is a third cause the label does not name and the instruction is wrong for: **the plan was
retired by this same session.** A landed plan is deleted as the last step of its own lifecycle, in
the repo the session is working in — that is `plan-docs`' documented retirement, not an absorption,
and there is nothing to correct and nobody to file for.

The two look identical to `filed`, because both are "this session wrote this path and the path is
gone".

## Evidence

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-freshful-polite-mcp/2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl`

Harvest #2 of that session, 2026-09-20, distinctive phrase `harvest #2 of this session`. `filed`
listed six plan files, four of them `MISSING`:

```
plans/2026-09-06-robots-guard-startup-failure-cached.md            MISSING (absorbed, or moved)
plans/2026-09-06-check-availability-404-vs-parse-error.md          MISSING (absorbed, or moved)
plans/2026-09-18-order-detail-dropped-createddate.md               MISSING (absorbed, or moved)
<store>/power-user-linux-setup/2026-09-18-direnv-never-fires-...md MISSING (absorbed, or moved)
```

**Only the fourth was absorbed** — by `fff83a9` in the store, "power-user-linux-setup: absorbed
three filed plans into the repo", which is exactly the case the instruction is written for and where
"it landed and is worth saying so" is the right report line.

The first three were **retired by this session an hour earlier**: landed, `Migrated to` sections
committed, references rewritten, then `git rm` and pushed (`a50b2e6`). Following the instruction
literally would have meant filing corrections against three plans the session had deliberately
deleted, into a repo that owns them and did not absorb anything.

[PITFALL: the failure is quiet and reads as diligence. Filing three spurious corrections produces
plans that look ordinary in `absorb`'s queue, aimed at files that no longer exist, and the session
that picks them up has to reconstruct why they were filed before it can conclude they should not
have been. The wrong action here costs another session's time rather than this one's, which is why
nothing in the run would have surfaced it.]

[PITFALL: retirement is the _expected_ end state for a plan a session lands, so this is not an edge
case. `plan-docs` says the landing session retires in the same session once pushed — so any harvest
that follows a landing in the same session hits this, and a well-run session hits it more often than
a sloppy one.]

## Open questions

[DECISION: **the label stops asserting a cause; `filed` does not diagnose it.** Settled 2026-09-26.
The alternative was three git queries — a deletion in the plan's own repo is a retirement, a store
deletion paired with a repo addition is an absorption, no deletion commit is a move. It would work,
but the reader tells the cases apart at a glance, and `(not attributed)` was already fixed once the
same way: state only what the check established. `MISSING (cause not determined)` plus a footer
naming the three remedies.]

[DEFERRED: whether the same conflation affects the `## plan files this session wrote` list's purpose
at all. Its job is "confirm the file is still there before naming it" in the report's opening
groups, and for that a bare MISSING is sufficient — it is only step 8's correction instruction that
needs the cause. Possibly the fix is entirely in `SKILL.md` and not in the script.]

## Recommended direction

Lean toward the second open question: change what the label claims rather than teaching the script
to diagnose. The `(not attributed)` precedent is directly on point — that row was corrected from
asserting "another session" to stating only what the check established, for the same reason and
after the same kind of instance.

Then adjust the `SKILL.md` sentence so the instruction branches on the cause instead of assuming
absorption, and say plainly that a plan this session retired needs nothing.

Filed from a session in `freshful-polite-mcp`, which cannot edit this repo.

## Verification

Landed 2026-09-26 in `06421c9`, taking the recommended direction: the label is now
`MISSING (cause not determined)` and a footer names the three remedies. Covered by
`test_a_missing_plan_row_names_no_cause` and `test_no_missing_footer_when_every_plan_is_present`,
which drive `_print_filed` with a vanished row directly rather than staging a real retirement.

## Migrated to

- **The label and why it names no cause** — the comment above the `MISSING` mark in
  `skills/session-harvest/scripts/harvest.py` (`_print_filed`).
- **The three remedies and the 2026-09-20 instance** — `skills/session-harvest/SKILL.md` step 8, the
  paragraph opening "A row marked `MISSING` says only that the file is gone".
- **Not migrated:** the first open question's three-query diagnosis. Rejected rather than deferred —
  the reader tells a retirement from an absorption at a glance, and the `(not attributed)` precedent
  already chose the honest label over a script diagnosis once. The `[DEFERRED]` question resolved
  itself: the fix needed the script (the label) and the skill (the instruction) both.
