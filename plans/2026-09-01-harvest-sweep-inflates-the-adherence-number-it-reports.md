---
status: landed
updated: 2026-09-02
---

# The harvest's own sweep inflates the adherence number it reports

Found by `/session-harvest` in an `ingesta` session, 2026-09-01, while running step 5's
self-adherence check on itself.

## Context

Step 5 tells the harvest to measure the session's Bash discipline with `session-bash-audit`, on the
grounds that "the transcript says what the session intended; this says what it actually typed" —
which is right, and is why the check earns its place. The problem is that the sweep runs **before**
the measurement and its calls are counted in it.

Measured on that session, same harvest, minutes apart:

| when                 | calls | `head`/`tail` |
| -------------------- | ----- | ------------- |
| sweep begun          | 127   | 37%           |
| report being written | 136   | 40%           |

Nine calls, three points. The direction is the finding rather than the size: the sweep moves the
number the sweep exists to report, and it moves it the wrong way.

**It is not incidental to how the sweep is written — it is what the sweep asks for.** Step 5's
checklist is a series of inspections whose natural written form is piped: `ss -ltnp` read alongside
`ps`, a store listing, a plans-directory search, a `--samples` run. Every one of those is a
long-output command being narrowed, which is the shape `~/AGENTS.md` prohibits and which
`session-bash-audit` counts. So a skill that reports on rule adherence prescribes a procedure that
breaks the rule, and no reader of its report can see how much of the figure is the procedure's.

The `~/AGENTS.md` rule has an answer for this and the skill does not repeat it: count first
(`rg -c`, `wc -l`) rather than pre-truncating, and let the harness's own truncation handle the rest.
Most of the sweep's inspections could be written that way.

## A second sample, and it moves the other way

Same day, a background job in `agent-skills`, measured at the two points this plan prescribes:

| when                 | n   | `head`/`tail` | `git-C-own-repo` | `heredoc` | met  |
| -------------------- | --- | ------------- | ---------------- | --------- | ---- |
| sweep begun          | 101 | 6%            | 22%              | 18%       | 8/11 |
| report being written | 132 | 6%            | 17%              | 14%       | 9/11 |

Thirty-one calls, and the score **improved**. So the effect is not that a harvest inflates its own
number — it is that **the sweep's calls are a different population from the working session's, and
they drag the rate toward the sweep's own shape.** In the `ingesta` session that shape was piped
inspections and the rate rose; here the sweep was plain unpiped commands run from the repo's own
cwd, and it diluted a `git -C` habit the working session had.

That sharpens the fix rather than changing it. "Exclude the sweep's calls" is right for both
directions; "the harvest inflates the figure" is right for only one, and stating it that way would
have made this sample look like a refutation instead of a confirmation. The claim to carry forward:
**a figure that includes the sweep measures the sweep, not the session** — in whichever direction
the sweep happens to lean.

## Open questions

[NEEDS CLARIFICATION: whether the fix is to exclude the sweep's calls or to rewrite the sweep. The
audit script already takes `--session`; a `--until <timestamp>` or an "exclude calls after the
harvest was invoked" flag would make the figure describe the working session, which is what the
watch in `power-user-linux-setup` is actually tracking. Rewriting the checklist's commands is the
other half and is worth doing regardless — the skill should not be teaching a shape it elsewhere
reports as a miss.]

[NEEDS CLARIFICATION: whether the report should state both numbers. A harvest that says "37% during
the work, 40% including this sweep" is honest and costs one line; one that says "40%" is quietly
reporting on itself and attributing it to the session.]

## Also worth recording

A second, smaller thing from the same run: `--samples N` prints no sample calls when combined with
`--session <id>`, so a harvest that wants to name the offending shapes cannot get them from the tool
and has to read the transcript by hand. Not obviously a bug — the session path may simply not thread
them — but it is the one thing that would have made this filing concrete rather than statistical.

Filed alongside `2026-09-01-adherence-sample-11-a-harvest-that-raised-its-own-rate.md`, which is the
same run's numbers filed for `power-user-linux-setup`, where the watch lives. This is a new concern
rather than an addition to that one: that plan is a sample, this is about the instrument.

## Outcome, 2026-09-02

Both halves landed, and both open questions were answered by doing them rather than choosing between
them.

- **Exclude, or rewrite the sweep? Both, as the plan suspected.** `session-bash-audit` gained
  `--until <ISO>`, and `session-harvest` step 0 now records the boundary with `date -Is` as its
  first command — it has to be first, because every later step adds calls of the sweep's own
  character. Step 5 passes it.
- **Report both numbers? Yes**, one line, in the plan's own phrasing: the first number is the
  session, the second is the honesty.

**The title is now wrong and the plan's own second sample is why.** "Inflates" was the claim from
one run; the second moved the other way. What shipped is the corrected claim — a figure including
the sweep measures the sweep, in whichever direction it leans — recorded in `_before`'s docstring so
the next reader of that flag finds the reasoning, not just the behaviour.

The `--samples` note under "Also worth recording" turned out to have a plain cause rather than a
threading problem: the `--session` branch never called the sampler at all. Fixed in the same commit,
which is what makes the flag usable for naming offending shapes rather than only counting them.

Confirmed live 2026-09-02 on this session: 59 calls before the boundary at 2% `head`/`tail` against
14% for the whole session, which is the population difference the plan describes, measured.

## Migrated to

- `skills/session-bash-audit/scripts/audit.py` — `--until`, its `_before` helper carrying the
  two-directional evidence and the keep-untimestamped-calls reasoning, and the `--samples` fix.
- `skills/session-harvest/SKILL.md` — the step 0 boundary, the `--until` invocation, the
  report-both-numbers rule, and the unpiped-inspections instruction that stops the sweep teaching
  the shape it measures.
