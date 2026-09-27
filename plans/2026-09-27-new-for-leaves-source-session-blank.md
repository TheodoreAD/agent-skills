---
status: idea
updated: 2026-09-27
---

# New --for leaves source_session blank

## Context

`plans.py new … --for <repo>` writes `source_session: # transcript filename, or blank`
(`skills/plan-docs/scripts/plans.py:2666`) and leaves it for the filer to fill in. The skill's own
PITFALL says this is "exactly what gets skipped", and it has now also been filled in **wrongly**.

On 2026-09-27, a background-job session (transcript `a953b16f-c02c-45d9-99e8-21a7277c781d`) filed
two plans for power-user-linux-setup:

- `2026-09-27-install-gog-and-gmailctl.md`
- `2026-09-27-install-rule-uses-package-health.md`

Both recorded `source_session: 1767aa06-adb4-4cf1-8b65-18ffec598c03.jsonl`. That id is the **job**
id, visible in the task-output paths the session was reading, and names no transcript. Nothing in
the file could tell a reader it was wrong. The session's own harvest caught it, because
`harvest.py
transcript` printed the real id, and the two plans were corrected the same day.

The right value was already in the environment. `plans.py` reads `$CLAUDE_CODE_SESSION_ID` at line
2423 to anchor the cross-repo guard, and in this session that variable held `a953b16f-…`, the
transcript stem. So the script held the answer and asked a human to type it.

## Open questions

[NEEDS CLARIFICATION: fill `source_session` automatically when `$CLAUDE_CODE_SESSION_ID` is set, as
`<id>.jsonl`, and leave the placeholder only when it isn't? This is the same move as `source_repo`,
which is already filled in. And `source_moment` as the current UTC instant, which is at least the
filing moment, if not the moment of the evidence?]

## Recommended direction

1. In `new --for`, write `source_session: <$CLAUDE_CODE_SESSION_ID>.jsonl` when the variable is set.
   Keep the placeholder on other harnesses, which is the tier-2/tier-3 split the guard already uses.
2. A test with the variable set and unset.
3. A PITFALL line in the SKILL.md section on plans that arrive from another repo: in a background
   job, the job id and the transcript id differ, and only the transcript id is a `source_session`.
