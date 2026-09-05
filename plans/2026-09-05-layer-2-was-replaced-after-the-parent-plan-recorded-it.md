---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 86b6d25d-eb68-4751-b989-ad45931ef62a.jsonl
source_moment: 2026-09-05T17:25:20+03:00
---

# Layer 2 was replaced hours after it landed, and the parent plan still describes the old one

## Context

`plans/2026-09-05-a-piped-gate-that-cannot-lie.md` in this repo is `status: planned` and records
layer 2 as landed in `repo-tasks` (`ba9e8e6`..`4c0bd3a`). **Layer 2's mechanism was replaced the
same day**, in `repo-tasks` commits `d322392`..`7db8b29`, pushed 2026-09-05, CI green. The parent
plan has not been told, and neither has `2026-09-05-quiet-gate-changes-what-the-instruments-see.md`,
which is filed in the store against this repo and reasons throughout from the old shape.

Nothing here is a complaint about either plan. The replacement happened in a different session, in a
different repo, hours after both were written, and no mechanism carries a correction backwards to a
plan that has already been absorbed — which the plan-docs skill already records as a property of
filing rather than as a one-off.

## What actually changed

The user's objection, verbatim from the session that made the change: _"the point is the rule of
least surprise for users."_ Fold-by-default changed what every consumer saw on upgrade having asked
for nothing, covered eleven of ~90 `c.run` call sites so two output shapes coexisted, and turned
`UnexpectedExit` into `Exit` unconditionally.

|                  | layer 2 as the parent plan describes it               | layer 2 as it now is                                               |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------------------------ |
| default          | folded, verdict last                                  | **stock invoke** — echo, stream, `UnexpectedExit`                  |
| how to change it | `INVOKE_QUALITY_VERBOSE=1` restores streaming         | `REPO_TASKS_RUN_REPORT` turns reporting **on**                     |
| where it lives   | `quality.py`, `c.run(hide=True, warn=True)` per step  | `runner.py`, a `Local` subclass swapped via `config.runners.local` |
| what it covers   | the eleven gate steps                                 | every `c.run` passing `echo=True` (~90 sites)                      |
| line shape       | `ruff check . ……… ok (0.4s)`                          | `ruff check . \| ok \| 0.0s \| All checks passed!`                 |
| verdict          | `quality.precommit: PASS  15 steps, 592 passed, 4.5s` | `quality.precommit \| PASS \| 15 steps \| 4.6s`                    |

The measurement that justified layer 2 is unchanged and was not discarded — it moved. All 812 piped
gate runs were agent sessions, and layer 1 already puts a `CLAUDECODE`-guarded snippet in those
shells, so the variable is set there rather than typed. That half is **not done**: filed as
`2026-09-05-agent-shells-set-repo-tasks-run-report.md` for `power-user-linux-setup`, and until it
lands **no agent session is in report mode at all**.

## 1. The scheduled measurement will measure the wrong thing

The parent plan's `## Verification` schedules `audit.py --days 7 --compare <baseline>` a week after
each of layers 1 and 2, with a baseline saved before layer 2 precisely so its effect is separable.

That comparison is now between a baseline taken against fold-by-default and a week of sessions
running **stock invoke**, because the env var is set nowhere. The honest reading of a null result is
"layer 2 was not in effect", and the honest reading of any result at all is unavailable until the
`power-user-linux-setup` half lands. A run made without knowing this would read a null as "the quiet
gate did not reduce piping", which is the opposite of what it would show.

This compounds with, and does not duplicate,
`2026-09-05-quiet-gate-changes-what-the-instruments-see.md`: that one says the **instrument** moved
under the baseline, this one says the **subject** did. Either alone invalidates the comparison.

[DECISION: do not re-baseline yet. The measurement wants a week of sessions actually in report mode,
so the sequence is: land the `power-user-linux-setup` export, save a fresh baseline **then**, and
date the week from there. Re-baselining now would anchor to a week nobody was in either mode.]

## 2. The CI property in layer 2's rationale is deliberately not preserved

Layer 2's own text gives this as one of the two properties that "matter more than the line count":

> The verdict is the **last line**, so a `| tail -3` still shows the truth even where layer 1 is
> absent (CI logs, a machine without the snippet).

The replacement **drops that for CI on purpose**, and the reasoning is recorded in `repo-tasks`'
`contributing/quality-gate.md`: a GitHub Actions log is scrolled by a human reading a failure, and
full streaming is what belongs there; nothing about the piping measurement applies to CI, which
never pipes.

That is a real disagreement between two written designs rather than an oversight, and it is the one
thing in this plan that may want reversing rather than recording.

[NEEDS CLARIFICATION: should CI set `REPO_TASKS_RUN_REPORT`? Against: a CI log has no context limit
and a human reads it linearly, so folding hides the failure's neighbours for no gain, and CI never
pipes so layer 1's absence costs nothing there. For: layer 2's stated property was that the verdict
survives _anywhere_ layer 1 is absent, and a green CI log of ~50 lines per job is the case where one
verdict line is genuinely nicer. Note the asymmetry — a failing step replays its output in full
either way, so the disagreement is only about what a **green** CI log looks like.]

## 3. Smaller corrections to the two existing plans

- `quiet-gate-changes-what-the-instruments-see.md` §2's `claims` false positive is now **worse, not
  better**, and its cause is intact: `PASS` beside a count is still the string, and a session
  demonstrating the shape still quotes it. This session's own `claims` run returned 7, of which 4
  were table rows quoting tool output (`| basedpyright | 1 | 0 errors, 0 warnings, 0 notes |`) and
  one was a quotation of the **old** format inside an explanation of what changed. So the "working
  on it inflates it" shape now fires on sessions discussing the format as well as demonstrating it.
  A fenced-code-block signal would not have caught the table rows.
- That plan's §1 names `0165577` "a pipe inside quotes is not a pipe" as an instrument commit
  straddling the baseline. Still unpushed in the checkout as of this harvest, along with `88bfd42`
  and `8445edc`, so the installed `audit.py` does not have it — a run using the installed copy and a
  run using the checkout still disagree.

## Evidence

- `repo-tasks` `d322392` (the runner, added unused), `27937b1` (the switchover), `75bb548` (docs),
  all pushed 2026-09-05, CI and Security green on `7db8b29`.
- `repo-tasks` `plans/2026-09-05-run-reporting-as-an-opt-in-agent-mode.md`, `status: in-progress`,
  carries the full design, the decisions and the verification. **Read that rather than this** — this
  plan exists only to tell this repo that its parent plan moved.
- The mechanism was probed before it was designed: `config.runners.local` is invoke's own extension
  point (`Context.run` builds its runner from that key; the stock config already holds `Local`
  there), so no monkeypatch. `UnexpectedExit.__str__` prints only the last ten lines of hidden
  output, which is why report mode raises `Exit` instead.
- The distinctive phrase to search the source transcript for is the user's own framing, _"without
  the env var, everything runs normally"_.

## Recommended direction

1. Update `a-piped-gate-that-cannot-lie.md`'s layer 2 section in place to describe what shipped, and
   mark its verification as blocked on the `power-user-linux-setup` export rather than on a date. In
   place, not as a second file — one plan per topic.
2. Answer the CI question above; it is the only open design decision here.
3. Leave the layer-3 work alone. Nothing in this affects it, and the checkout is mid-restructure.
