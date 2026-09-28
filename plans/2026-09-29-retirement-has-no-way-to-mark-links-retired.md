---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/ingesta
source_session: e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl
source_moment: 2026-09-28T20:59:00Z
source_plan:
---

# Retirement has no way to mark links to a retired plan

## Context

`plan-conveyor`'s retirement step 5 says to fix inbound references, and that a surviving pointer
"must say _retired_". `refs` finds them; nothing rewrites them. `rename` has `--update-refs` for the
same job one lifecycle step earlier; retirement has no equivalent.

In a repo whose gate runs a relative-link checker (ingesta's does), every markdown link to a deleted
plan fails the gate, so the rewrite is not optional and it is the bulk of a batch retirement's work.

## Evidence

- One session retired sixteen plans in batches. It wrote a throwaway script (`retire_links.py` in
  its scratchpad) that turns `[text](<plan>.md)` into `text (<note>)`, and called it **14 times**.
- **Its first version corrupted tag markers.** The regex `\[([^\]]+)\]\(<plan>\)` let the captured
  text span back to an earlier `[` — the opener of a `[DECISION:` or `[NEEDS CLARIFICATION:` block
  several lines up — so the replacement deleted that bracket in seven plans. It was caught only by
  reading the output (`rg "retired 2026-09-28"` showed lines starting with a stray `[`) and reverted
  with `git checkout`; the fix was excluding `[` and `]` from the capture.
- The deletion commits in `ingesta`: `b477f63`, `2ad8dce`, `e19ee1a`.

## Recommended direction

A `refs --mark-retired "<note>"` (or `retire` subcommand) that rewrites each inbound markdown link
to plain text plus a note, using a capture that cannot cross a bracket, and leaves prose mentions
and section citations alone — the judgement step 5 already describes. Same review stance as
`--update-refs`: print every rewrite, apply only when asked.
