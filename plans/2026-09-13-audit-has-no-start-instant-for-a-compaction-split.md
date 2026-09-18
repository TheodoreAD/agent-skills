---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/ingesta
source_session: 21c18768-649d-4753-9dca-e23e5b9555d3.jsonl
source_moment: 2026-09-13T18:42:02+03:00
source_plan:
---

# `audit.py` has an end instant and no start instant, so a compaction split is found by subtraction

## Context

A `session-harvest` of a seven-day `ingesta` background job, compacted once, measured its Bash
adherence and found the session was two sessions: before the compaction's continuation turn
(`2026-09-12T19:17:19Z`) chains ran 67%, `head/tail` 48%, heredoc 32%; after it, 1%, 0% and 0%. The
whole-session row (47%, 33%, 22%, at the session's second harvest) describes neither half. Filed as
a corpus row for `power-user-linux-setup` as
`2026-09-13-adherence-sample-ingesta-compaction-split.md`.

## Evidence

`audit.py` takes `--until` and nothing for the other end, so the after-compaction half could only be
derived by running the audit twice (to the boundary, and to the compaction instant) and subtracting
the counts by hand. That works for counts and does not work for anything else the audit prints:
samples, the gate/listing split of `exit-masked`, and the truncation line all describe the whole
prefix.

Nothing prompted looking for the split either. The harvest's audit step reads one row; the step
happened to be noticed only because the session's own recent calls looked nothing like its totals.

## Recommended direction

Two changes, and the second is the one that finds the next instance.

- `--since <instant>` beside `--until`, so a window is two flags and every section of the output
  describes it.
- The transcript already marks a compaction — the continuation turn that opens "This session is
  being continued from a previous conversation". When a session has one, the audit could print the
  rates for each segment beside the whole, since a long session that was compacted is exactly the
  one whose whole-session row misleads. `session-harvest`'s `turns` already finds that turn.
