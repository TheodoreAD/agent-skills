---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/power-user-linux-setup
source_session: 8e1ea2df-8de1-4cd1-873d-5a0f058aaa6d.jsonl
source_moment: 2026-09-13T14:15:12Z
source_plan:
---

# `harvest.py claims` counts calls past `--until` in its denominator

## Context

`claims` prints `# <masked> of <total> Bash calls masked their exit code behind a filter`. The
numerator honours `--until`: `skills/session-harvest/scripts/harvest.py` filters the masked list
with `before(stamp, args.until)`. The denominator does not. It is
`total_bash = len(bash_calls(transcript.entries))`, a few lines further down, with no cutoff. So the
line puts a window-limited count over a whole-transcript count, and the harvest's own inspection
calls are included in the second.

That runs against the skill's own reasoning for `--until`, that "a figure that includes this sweep
measures the sweep". The harvest's calls are unpiped by design, so they only ever **dilute** the
rate: a session with 5 masked calls out of 32 would print `5 of 39` (13%) instead of 16%. The same
value goes out under `--json` as `bash_calls`.

Small cost: the numerator is right, and a zero stays a zero. It matters once someone reads the ratio
as a rate or compares it with `audit.py`. That script does apply `--until` to its call count, so the
two instruments disagree about the size of the same window.

## Evidence

- Session `8e1ea2df-8de1-4cd1-873d-5a0f058aaa6d.jsonl`, a harvest whose step-0 boundary was
  `2026-09-13T14:15:12Z`. `claims --until 2026-09-13T17:15:12+03:00` printed "0 of 39 Bash calls
  masked their exit code behind a filter".
- Same session and boundary, `audit.py --until 2026-09-13T17:15:12+03:00`: "this session: 32 Bash
  calls, excluding 10 at or after 2026-09-13T17:15:12+03:00 — the run's own sweep".
- 39 − 32 = 7: the harvest's own calls between the boundary and `claims` running (`boundary`,
  `transcript`, `skills-state`, a `diff`, `turns`, plus `sweep` and `claims` issued in parallel).
- Found by reading the code after the two counts disagreed, not by a failing test.

## Open questions

None.

## Recommended direction

Apply `before(stamp, args.until)` to `total_bash` as well, so both halves of the line describe one
window. Add a unit test in `tests/unit/test_harvest.py`: a transcript with calls on both sides of
the boundary, asserting the denominator excludes the later ones. Optionally print the excluded count
the way `audit.py` does ("excluding N at or after …"), so the two instruments' headers read alike.
