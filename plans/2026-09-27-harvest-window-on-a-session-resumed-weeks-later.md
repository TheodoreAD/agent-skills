---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl
source_moment: 2026-09-27T19:47:51Z
---

# Every "since session start" window in the harvest is meaningless on a session resumed weeks later

## Context

`session-harvest` derives almost every window from the transcript's `started:` instant. That is the
right anchor for a session harvested the day it ran, which is every measurement behind the skill. It
is the wrong one for a session resumed after a long gap, and nothing in the report says which kind
of session it is looking at.

Measured 2026-09-27, harvesting a session whose work ran on 2026-09-07 and which was resumed twenty
days later purely to harvest it:

| the check               | what it reported                            | what was this session's |
| ----------------------- | ------------------------------------------- | ----------------------- |
| `skills-state --since`  | 14 commits "moved since start" on one skill | 0                       |
| `filed`, store commits  | 191 not attributable                        | 3                       |
| `sweep`, research store | 207 entries "changed by something else"     | 0                       |
| `sweep`, docker images  | 10 created "during the window"              | 0                       |

Every one of those is correctly labelled — the attribution work the skill has already done is what
keeps the report honest, and each row says plainly that it is not this session's. The problem is
volume and prescription, not correctness:

- **`filed` printed roughly 190 commit rows**, one per store commit in twenty days, burying the
  three rows that were this session's own. The subcommand's whole value here — "did my filings land"
  — was answered in the first four lines and then drowned.
- **`skills-state` prescribed its most expensive step on a window that guarantees a hit.** Over
  twenty days every actively-developed skill has moved, so "SKILL.md moved after this session began
  — re-read it" fires unconditionally. The skill already worries about exactly this for the
  `--since` value: too early "prescribes the procedure's most expensive step on evidence that does
  not support it". A long gap is that failure arriving through a correct instant rather than a
  guessed one.

The session's own last working call is knowable — the transcript has it — and the gap between it and
the harvest boundary is the fact that changes how every row above should be read.

## Evidence

Session `65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-invoke-stubs/`, harvested
2026-09-27T22:47:51+03:00 with `boundary`, against a session that started 2026-09-07T11:24:34Z and
whose last working Bash call was about forty-five minutes later the same day.

The row counts above are from that run's own output. Nothing was wrong with any of them; the run
simply spent most of its reading budget discounting them by hand, and a reader skimming the report
would have had to do it again.

### Second sample, 2026-09-27, in this repo

Reproduced the same day by an `agent-skills` harvest, session
`21615ec2-5eca-4393-a831-d24275fb2551`, which began 2026-09-13T11:49:34Z and whose entire working
span was 2026-09-27 — a **14-day** gap, arrived at by resumption rather than by a deliberate late
harvest. So the shape is not specific to harvesting an old session on purpose; an ordinary
long-lived session reaches it by sitting idle.

| the check               | what it reported                                      | what was this session's |
| ----------------------- | ----------------------------------------------------- | ----------------------- |
| `skills-state --since`  | 9 commits "moved since start" on `session-bash-audit` | **2**                   |
| `filed`, store commits  | 116 not attributable                                  | **1**                   |
| `sweep`, research store | 148 entries "changed by something else"               | 1                       |

`skills-state` fired the expensive re-read prescription on all nine, and the seven that were not
this session's were a fortnight of another session's work on a skill this run only ever called as a
script. The `filed` wall was 116 rows to find one, exactly as described above.

**One thing this sample adds: the prescription was answerable without any window change.** The run
discounted `plan-conveyor`'s single moved commit in one line, because the subcommand's own "none of
it applies if every one of those commits is this session's own" carve-out held there — and could not
discount `session-bash-audit`'s nine, because seven were not. That split is the useful signal and it
is already computed; what the report lacks is any statement of **how old the window is**, which is
the one fact that tells a reader whether to expect the carve-out to do any work. Argues for the
recommended direction below (print the gap) over the anchor change, on this evidence.

## Open questions

[DECISION: **the anchor stays at session start** (decided with the user 2026-09-28). The question
was whether to anchor at the session's last activity before the boundary instead. Against it, and
decisive: for an ordinary same-day session the two instants are minutes apart and the change buys
nothing, and the second sample showed the attribution already discounting correctly where the
commits were this session's. What a resumed session lacked was the window's age, which the printed
gap now supplies.]

[DECISION: **`filed` folds its `(not attributed)` rows past ten**, newest first, into a count line,
and `--verbose` lists them all — the shape `sweep`'s may-have-landed section already uses (decided
with the user 2026-09-28). Ten is not measured; it is small against the 116 and ~190 observed and
large against the 1 and 3 rows that were the session's own. Only the unattributed tail folds: this
session's rows, the `(authorship unestablished)` rows and the counts line always print.]

## Recommended direction

Print the gap first, whatever else is decided: one line in `boundary` or `transcript` saying how
long ago the session's last working call was, so a reader knows which kind of report they are
holding before they read a single row. That is cheap, it needs no window change, and on a same-day
session it prints something unremarkable.

Then decide the anchor question. If the answer is to re-anchor, `skills-state` is the check that
benefits most, because it is the one whose output turns directly into "go and re-read four files".

**Gap printed 2026-09-28.** `transcript` prints `idle gap:` — the widest stretch between two
consecutive transcript entries, with its two instants — and, past `LONG_IDLE` (one day), a note that
every `started:`-anchored window spans it. `--json` carries it as `longest_idle`. It lives in
`transcript` rather than `boundary` so the harvest's first command still cannot fail on transcript
resolution. The `filed` fold followed the same day; both decisions are above.

## Migrated to

- **The gap and why the anchor stays** — `skills/session-harvest/SKILL.md`, the paragraph opening
  "`transcript` prints the session's longest idle gap"; the code and both samples' figures are in
  `longest_idle`'s docstring in `harvest.py` (`2415103`).
- **The `filed` fold** — the same SKILL.md, under "`python3 $H filed --until <the boundary>`", and
  the comment on `UNATTRIBUTED_SHOWN` (`3209e06`).
- **Not migrated**: the two sample tables row by row, and the four-check census of the first run.
  The destinations cite the figures that decided each question; `plans.py archive` reads the rest
  back from here.
