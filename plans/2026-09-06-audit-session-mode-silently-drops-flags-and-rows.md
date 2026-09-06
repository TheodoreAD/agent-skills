---
status: in-progress
updated: 2026-09-06
---

# `audit.py --session` is a second-class path: it drops flags and a row, silently

## Context

Found 2026-09-06 by a harvest running step 5's adherence check on itself. Both halves are the shape
this corpus keeps finding in its own instruments — **an option that is accepted and does nothing**,
and **a measure that is computed and never displayed** — and both are invisible from the output,
which is what makes them worth a plan rather than a fix-in-passing.

`report_session` is the `--session` path and it returns before the tail of `main()`:

```python
if args.session:
    report_session(args)
    return
...
if args.json:
    args.json.write_text(...)
    print(f"\nwrote {args.json}")
```

## The two findings, both reproduced

**1. `--json` is silently ignored in session mode.** _Fixed 2026-09-06; the description below is
what it did._ `argparse` accepts it (`type=Path`), the run prints its normal text report, and no
file is written and nothing says so. Reproduced this session:
`audit.py --session <id> --until <boundary> --json <path>` exited 0, printed the report, and the
path did not exist afterwards. `--save-baseline` is skipped by the same early return; that one is
arguably right on the merits — a single session is not a corpus baseline — but it is equally silent.

The cost is specific rather than theoretical: **the harvest's adherence step is always a `--session`
run**, so the machine-readable form is unavailable in precisely the mode the harvest uses, and a
caller who wants the tags has to re-derive them by hand. It also breaks the corpus's own uniformity
rule, which `plan-docs` states as a rule earned by measurement: a flag available on some invocations
and not others costs a retry every time an agent assumes uniformity.

[DECISION: **both, one per flag — hoist `--json`, refuse `--save-baseline`.** Landed 2026-09-06. The
dump moved into a `dump_json(calls, path)` helper and `report_session` now returns the calls it
reported on, so the session path dumps its own `--until`-filtered set rather than `load_calls`'; a
JSON disagreeing with the rates printed beside it would have been worse than none. `--save-baseline`
takes the other half of the option, because one session's rates genuinely are not a corpus baseline
— it is `ap.error` now, exit 2, rather than a silent skip. Two tests, both confirmed failing against
the pre-change script: it exited 0 and wrote no file in either case.]

**2. `rg-replace` is computed and appears in no session-facing output.** It is a defined pattern
(`audit.py` line ~327) and it is in **none** of the three places that decide what a reader sees:

| list           | what it drives                     | `rg-replace` in it |
| -------------- | ---------------------------------- | ------------------ |
| `RATE_COLUMNS` | the per-run summary line           | **no**             |
| `SAMPLE_TAGS`  | the `== <tag> (n) samples ==` dump | **no**             |
| `EXPECTATIONS` | the `n/m expectations met` verdict | **no**             |

So a session can commit the anti-pattern and its adherence line will not mention it, in either
direction — there is no row to read as zero.

[PITFALL: **this session is the instance, which is the part that makes it worth filing.** The run
that found it had, earlier the same evening, retired the plan that measured `rg-replace` and
migrated its reasoning into `references/research.md` — and then typed
`rg -rn 'cd' --files-with-matches …`, the `-rn` bundle that is 27 of the 32 real instances that plan
recorded. It returned nothing, which is the documented signature, and was caught by eye. **The
adherence line for that session reported `11/11 expectations met` and every rate at 0%.** Authoring
a rule is not evidence of following it; here, measuring a rule was not evidence of measuring it
either.]

## A third display property, found by nearly filing it as a defect

**`0%` in a session view does not mean zero.** Rates print as `:.0%`, so on a session-sized
denominator a single instance rounds away: this run piped exactly one command to `head -40`, and the
line read `head/tail=0%` at n=215, because 1/215 is 0.47%.

Recorded because the near-miss is the useful part. That zero was read as a missed tag, the predicate
was tested directly against the exact command — it returns `True` and tags `head/tail`,
`search|head` and `grep/find` — and only then did the arithmetic explain it. **The instrument was
right and the display was lossy**, which is a different fault from the two above and would have been
filed as the same one.

The consequence for a reader is small but real, and it lands on this corpus's own procedure: a
harvest that reads `head/tail=0%` and reports "zero" is over-claiming by up to one or two calls, in
the section where a session's own adherence is stated. At corpus scale (tens of thousands of calls)
the rounding is invisible; at session scale it is the difference between none and a couple.

[DECISION: **counts beside rates, and the width objection dies with the one-line shape.** Both this
question and the next one were arguments about horizontal space in a line that is already 229
characters for 11 rows. A session view has **one** row — the corpus table is wide because it is
models × rows — so it does not have to be a line at all. Printed vertically, one row per line with
its count and its rate, there is no width budget to spend and nothing to trade off:

```
head/tail     227   53%
rg-replace      2    0%
```

Measured 2026-09-06 over 7 days, 67 sessions: median session n=247, so one call is 0.40% and rounds
to `0%` — and the rows where that bites are the low-frequency ones. Of the 30 sessions with at least
one `rg-replace`, **13 would print `0%`**; `find-not-fd` 9 of 20, `redirect-then-filter` 5 of 9,
`find-exempt` 2 of 3. A false zero on roughly half the sessions that have the finding is not a
rounding curiosity. One decimal place was the cheap fix and is rejected: `0.4%` is honest and still
makes the reader do arithmetic to learn that it means one call.]

[DECISION: **all of them, which is what dropping the line shape buys.** The question was only ever
hard because every added row cost horizontal space; vertically it costs one line, and a row a
session cannot act on costs one line saying `0`. So `rg-replace`, `find-not-fd`, `grep-r-not-rg` and
`find-exempt` join the view, and the corpus's `RATE_COLUMNS` stops being the session view's column
list — it keeps its own job, which is the per-model table where width is a real constraint. **A zero
that is printed is the point**: the original finding here was that a session can commit `rg-replace`
and read an adherence line that does not mention it in either direction. A row nobody prints cannot
be read as zero, and a row printed as `0` can.]

[DECISION: **not this row — the bundle sub-row, once it exists.** The question offered `down` or
`zero` for `rg-replace`, and the row's own numbers refuse both. Re-measured 2026-09-06 over 30 days,
31,011 calls, 86 tagged: `-rn` × 62, **bare `-r` × 13**, `-ril` × 6, `-rln` × 4, `-rl` × 2,
`--replace` × 1. The bare `-r` count was **zero** when this question was written and is now 13, so
the premise it was to be decided on has expired — and every one of the 13 is the deliberate
extraction idiom, `rg -o -r '' <pattern> <path>`, which is correct usage of a real flag. `zero` on
the row would therefore be a verdict nobody can satisfy, which this corpus already objects to;
`down` would push against legitimate use.

The split the numbers actually want is bundle (74) against deliberate (14): a flag group carrying
letters besides `r` is the accident, a lone `-r` or `--replace` is the idiom. **`zero` is defensible
on the bundle and only on the bundle** — so the expectation waits on the per-bundle breakdown that
`2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` inherited, exactly the ordering both
plans guessed at. One live failure in the window, worth citing when that row is built:
`rg -n "…" <path> -r 2>/dev/null` — a bare `-r` whose value the shell ate as a redirect, exit 123,
with the error message discarded by the same redirect.]

## What is done, and what is left

**Done 2026-09-06 — the flags half.** `skills/session-bash-audit/scripts/audit.py`: `dump_json` is a
helper both paths call, `report_session` returns its calls, `--save-baseline` errors under
`--session` instead of being skipped. Two tests in `tests/unit/test_audit.py`, and the SKILL.md
`--session` section now states both behaviours. It was the smaller change, it had no design question
worth arguing, and it unblocked a caller that exists today: the harvest's adherence step.

**Decided 2026-09-06 — the rows half**, in the three decisions above, taken with
`2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` open beside it as the sequencing
required. Two of the three collapsed into one answer: they were both arguments about horizontal
space, and a session view does not need to be a line. The third turned out not to belong to this
plan at all — the expectation goes on the bundle sub-row, which the other plan owns.

**Built 2026-09-06, same day.** `SESSION_ROWS` is the session view's own list — `RATE_COLUMNS` plus
`echo-exit`, `git-C-mutating`, `search|head`, `grep-r-not-rg`, `find-not-fd`, `find-exempt` and
`rg-replace` — printed one per line, count then rate, with `RATE_COLUMNS` left to the corpus table
it was written for. `exit-masked` carries the gate-versus-listing split and `rg-replace` its flag
spellings, both from the other plan. Five tests, and the first run on its own session reported
`rg-replace 1 (-rn x 1)`: **the row the plan was written about caught this session's own `rg -rn`**,
which is the shape the original finding said would go unreported.

[PITFALL: **the same defect was one level further in, and nothing would have found it by reading.**
`EXPECTATIONS` judged `find-not-fd` while `rates()` computed `RATE_COLUMNS` plus two — and
`find-not-fd` was in neither, so `compare` read it as absent from both runs and skipped it as "a
pattern added since this baseline was saved", every time, silently, permanently. A judged row that
is never computed and a computed row that is never displayed are the same defect; this plan found
the second and only turned up the first because building the view meant listing the rows. `rates()`
now returns `SESSION_ROWS`, and a test asserts every `EXPECTATIONS` key is computed.]

One consequence to carry into the build, because it reverses an assumption made here: **the numbers
in these decisions were measured with an instrument that was wrong until this morning.**
`strip_heredoc` was dropping every command after a heredoc
(`2026-09-06-audit-strip-heredoc-drops-the-rest-of-the-command.md`), so any session-scale figure
quoted before it landed is a floor. The rounding counts above were taken after the fix.
