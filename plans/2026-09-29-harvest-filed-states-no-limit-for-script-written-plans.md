---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/ingesta
source_session: e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl
source_moment: 2026-09-29T01:09:00+03:00
source_plan:
---

# `harvest.py filed` states no limit for plans written by a script

## Context

`filed` builds "plan files this session wrote" from the edit-tool writes in the transcript. A plan
changed inside a Bash call — a `python3 - <<'EOF'` block, `git rm`, a `plans.py` subcommand — is not
in it. `sweep` states the same seam on its own rows
(`limit: reads this session's own edit-tool
writes`, and an `exposure:` count of inline-script
calls); `filed` prints neither, so its list reads as complete.

That list is the one step 8 says to open the report with — "where did everything go".

## Evidence

- The session above listed **11** plan files. It actually touched roughly **30** in `ingesta` and
  the store: fifteen retired plans deleted with `git rm` after `## Migrated to` sections appended by
  heredoc, and a dozen live plans whose links were rewritten by a script. Two of the eleven were
  correctly `MISSING (retired by this session …)`; the other thirteen retirements were absent
  entirely.
- The same run's `sweep` printed `exposure: 67 call(s) this session ran an inline script`, which is
  the number `filed` needed beside its list.

## Recommended direction

Print the same `limit:` and `exposure:` lines under `filed`'s plan list. Optionally add plans named
in this session's `git rm` and `plans.py` argv, which the transcript does show, so the most common
script-side case — a retirement — is listed rather than only warned about.
