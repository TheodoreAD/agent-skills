---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/power-user-linux-setup
source_session: 0f1cf863-8d2d-4023-b8de-0202ff9c1837.jsonl
source_moment: 2026-09-28
source_plan:
---

# `audit.py --session <id>` redirects a job's own transcript to its later resumption

## Context

This reports a fact, so `source_plan` is blank. `_job_transcript` in
`skills/session-bash-audit/scripts/audit.py` redirects `--session <id>` to the job record's
`linkScanPath` whenever `~/.claude/jobs/<id[:8]>/state.json` has `sessionId == <id>`. It runs before
the exact-stem lookup, so it wins even when a transcript named exactly `<id>.jsonl` exists.

That is right for the 2026-09-01 case its docstring records, where the id-named file was a
stranger's session. It is wrong for a background job that was **resumed later**. The resumption
writes a new transcript, and the job record's `linkScanPath` and `resumeSessionId` move to it. The
id-named file is still the job's own original run, and the redirect then sends it to the resumption.

## Evidence

Hit while re-scoring a corpus row in power-user-linux-setup's
`plans/2026-09-02-agents-md-adherence-sample-corpus.md`, with `audit.py` at `1d565d8`:

- `audit.py --session 21c18768-649d-4753-9dca-e23e5b9555d3 --until 2026-09-13T18:42:02+03:00`
  printed `# 21c18768 is a background job's id, not a transcript id — reading 296b7b18-….jsonl`,
  then `no Bash calls found`.
- `~/.claude/jobs/21c18768/state.json` holds `sessionId: 21c18768-…`, `resumeSessionId: 296b7b18-…`
  and `linkScanPath` naming `296b7b18-….jsonl`, `createdAt 2026-09-06`, `updatedAt 2026-09-26`.
- `21c18768-649d-4753-9dca-e23e5b9555d3.jsonl` exists in the ingesta project directory (11.6 MB,
  last written 2026-09-13). Passing that **path** gives 721 calls, reproducing the figures the job's
  own harvest filed on 2026-09-13 to within one `chain` call. `296b7b18-….jsonl` is a 456 KB
  transcript from 2026-09-26 with one Bash call.

This time it failed loudly: the resumption had no calls before the boundary. With a later boundary
it would have printed a well-formed, wrong row, which is the failure the redirect was written to
prevent.

## Open questions

[NEEDS CLARIFICATION: which file is right when both exist? The two cases on record disagree. On
2026-09-01 the id-named file was a stranger's session. Here it is the job's own pre-resume run.
Existence alone cannot tell them apart. Candidates: refuse and print both paths, asking for a path;
measure both and label them; or prefer the id-named file when the record carries a `resumeSessionId`
that differs from `sessionId`, which is this case's signature. Only the first option cannot be wrong
silently.]

## Recommended direction

When a job record redirects **and** a transcript named exactly `<id>.jsonl` exists, stop guessing:
print both paths with their sizes and last-write times, and exit non-zero asking for
`--session
<path>`. Add a test with a fake jobs directory holding a resumed record, and cite this
case in `_job_transcript`'s docstring next to the 2026-09-01 one.
