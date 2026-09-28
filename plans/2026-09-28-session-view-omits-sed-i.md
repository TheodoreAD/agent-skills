---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/power-user-linux-setup
source_session: b73129dd-6136-41c3-a026-8e871581bc14.jsonl
source_moment: 2026-09-27T22:09:00Z
source_plan:
---

# The per-session view omits `sed-i`, so a breach of the Edit rule reads as clean

## Context

`session-bash-audit/scripts/audit.py` defines a `sed-i` row ("in-place edit via shell; Edit has its
own gate") and counts it, but `SESSION_ROWS` does not include it, so the per-session view a harvest
reads never prints it. `heredoc`, its sibling under the same deployed rule ("Edit/Write over
`sed -i`/heredocs"), is in the view. `env-prefix`, `python-c` and `label-echo` are likewise defined
and absent.

This is the same defect the `bash-c` comment in that file records being fixed on 2026-09-28 — "it
was not in the session view, so a session that typed the wrapper three times after being told not to
read 0% everywhere" — for a different row. A shape of misuse the author thinks of as the same fix,
recurring one row over.

## Evidence

- A power-user-linux-setup harvest, 2026-09-28, of a 355-call session.
  `audit.py --session … --until
  …` printed every row at 0 except `chain 1` and `bash-c 1`. The
  session had run exactly one `sed -i` (rewriting `zsh.configure(MockContext())` to
  `zsh.configure(_ctx())` across `tests/unit/test_zsh.py`, around 22:07Z), which the reporting
  session remembered and the view did not show.
- Category, per session-harvest step 2: the rule was **not followed** once, and the instrument could
  not see it — a measurement gap, not a wording one.

## Recommended direction

Add `sed-i` to `SESSION_ROWS` beside `heredoc`, and decide deliberately for `env-prefix`, `python-c`
and `label-echo` — either in the view, or a comment saying why a defined row is kept out of it. A
test that every row in the pattern table is either in `SESSION_ROWS` or named in an explicit
exclusion list would stop the next one arriving the same way.
