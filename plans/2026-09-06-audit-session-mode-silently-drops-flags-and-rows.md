---
status: idea
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

**1. `--json` is silently ignored in session mode.** `argparse` accepts it (`type=Path`), the run
prints its normal text report, and no file is written and nothing says so. Reproduced this session:
`audit.py --session <id> --until <boundary> --json <path>` exited 0, printed the report, and the
path did not exist afterwards. `--save-baseline` is skipped by the same early return; that one is
arguably right on the merits — a single session is not a corpus baseline — but it is equally silent.

The cost is specific rather than theoretical: **the harvest's adherence step is always a `--session`
run**, so the machine-readable form is unavailable in precisely the mode the harvest uses, and a
caller who wants the tags has to re-derive them by hand. It also breaks the corpus's own uniformity
rule, which `plan-docs` states as a rule earned by measurement: a flag available on some invocations
and not others costs a retry every time an agent assumes uniformity.

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

[NEEDS CLARIFICATION: **print counts beside rates in the session view, or one decimal place?** A
count is unambiguous and is what a session-sized denominator actually wants — `head/tail=1 (0.5%)` —
but it widens an already-long line. One decimal place is narrower and still reads as a rate, which
is the thing that misleads. A third option is to print rates only above some n and counts below it,
which trades a clear rule for a threshold nobody can defend — the same objection this corpus already
made to a staleness threshold.]

[NEEDS CLARIFICATION: **fix the early return, or move the flag handling into both paths?** Moving
`--json` above the `if args.session` branch is one line and covers it, but `report_session` builds a
different call set (one transcript, `--until`-filtered), so the dump would need that set rather than
`load_calls`'. The honest options are: hoist the tag-dump into a helper both paths call, or have
session mode reject the flags it cannot honour with a message. **Rejecting is worth taking
seriously** — this corpus's own position is that a flag that silently does nothing is worse than one
that errors, and `--save-baseline` in session mode should probably refuse rather than be quietly
skipped.]

[NEEDS CLARIFICATION: **which rows belong in the session view at all?** `RATE_COLUMNS` was built for
the per-model corpus table, and a session view has inherited it without the question being asked.
`rg-replace` is the instance that surfaced it, but `find-not-fd`, `grep-r-not-rg` and `find-exempt`
are in the same position — computed, and absent from the summary line. Adding all of them widens a
line that is already long, so the real question is whether a session view wants the same columns as
a corpus view or a different, shorter set aimed at what one session can act on.]

[NEEDS CLARIFICATION: **does `EXPECTATIONS` want an `rg-replace` entry, and in which direction?**
The table's vocabulary is `down` and `zero`. `zero` is defensible — the flag is never wanted, and
`--replace` spelled in full is unaffected — but the corpus has a standing objection to a verdict
nobody can satisfy, and the deliberate absences of `grep-r-not-rg` and `find-exempt` are precedent
for leaving a well-followed rule unjudged. Decide it with the row's own numbers in hand: zero bare
`-r` in the last measured corpus, against 32 real bundle instances.]

## Recommended direction

Take the `--json` half first: it is the smaller change, it has no design question worth arguing, and
it is the one blocking a caller that exists today. The row question is genuinely open and is better
decided alongside `2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md`, which already owns
what a row's reporting should look like and now carries the `rg-replace` per-bundle breakdown —
**that plan asks how the row should report, this one asks whether it reports at all**, and answering
them in the wrong order would design a breakdown for a row no session view prints.
