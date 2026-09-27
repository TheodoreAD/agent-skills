---
status: landed
updated: 2026-09-28
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

[DECISION: **fill `source_session`, leave `source_moment`** (decided with the user 2026-09-28).
`new --for` writes `<id>.jsonl` when `$CLAUDE_CODE_SESSION_ID` names exactly one transcript that
exists, through the same lookup the session anchor uses, and keeps the placeholder otherwise. A job
id fails that check, so the 2026-09-27 mistake cannot be written automatically either.
`source_moment` stays the filer's: it means when the evidence happened, and the filing instant would
be a plausible, precise and wrong value, which is worse than a blank that asks.]

## Recommended direction

1. In `new --for`, write `source_session: <$CLAUDE_CODE_SESSION_ID>.jsonl` when the variable is set.
   Keep the placeholder on other harnesses, which is the tier-2/tier-3 split the guard already uses.
2. A test with the variable set and unset.
3. A PITFALL line in the SKILL.md section on plans that arrive from another repo: in a background
   job, the job id and the transcript id differ, and only the transcript id is a `source_session`.

## Migrated to

- **The fill and the job-id pitfall** — `skills/plan-conveyor/SKILL.md`, "Plans that arrive from
  another repo"; `claude_transcript` in `plans.py`, whose docstring carries the incident
  (`e514be7`).
- **Why `source_moment` stays blank** — `e514be7`'s message only: the field's template comment
  already says it is the moment of the turn, which is the whole argument.
