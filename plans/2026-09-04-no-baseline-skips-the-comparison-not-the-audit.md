---
status: idea
updated: 2026-09-04
---

# "Skip this step" reads as skip the audit, when it means skip the comparison

## Context

`session-harvest`'s step 5 gained this wording on 2026-09-03 (commits `718c05e`, `ceb712d`), and it
is right about the thing it was fixing — a shipped baseline measures the author's machine, so
comparing against it reports how your setup differs from theirs rather than how your session
differed from your rules:

> The baseline is one **you** saved with that skill's `--save-baseline`, which writes to
> `~/.local/state/session-bash-audit/` by default; **skip this step** if you have never saved one,
> since comparing against a baseline measured on somebody else's machine reports how your session
> differs from their setup rather than from your rules.

**"This step" is the whole bullet, and the bullet is the audit.** Read literally by a session with
no saved baseline — which is every session until somebody saves one — it says not to run `audit.py`
at all. That drops the comparison, which is correct, and also drops the raw rates and `exit-masked`,
which is not: `exit-masked` needs no baseline to be meaningful, and the two paragraphs immediately
below the snippet depend on having it.

Those paragraphs are load-bearing. "If `exit-masked` is above zero, this session's own green results
are unverified — re-run the gate before believing any of them" is the check that has already caught
three red commits pushed on a filtered gate, and `claims --until` exists to count the assertions
made on top of it. A reader who follows the skip instruction never reaches either.

## Evidence

Session `179f0c44-e084-4cd3-918e-77568655e419`, `ingesta`, 2026-09-04, boundary
`2026-09-04T11:34:47+03:00`. `~/.local/state/session-bash-audit/` did not exist, so the condition
held exactly. The run took the narrow reading — dropped `--compare`, ran the audit anyway — and that
is where its most useful number came from: **23% exit-masked across 189 calls**, and five messages
telling the user a gate or suite was green, every one of them from a `| tail`-ed run.

The re-run exited 0 and all five claims held, which is the outcome that makes this easy to dismiss.
The point is that the session could not have known that without running the audit the skip
instruction would have cancelled.

## Open questions

[NEEDS CLARIFICATION: **whether a no-baseline run should be told to save one.** `--save-baseline`
exists and costs one flag, so the natural closing sentence is "save one now, so the next harvest has
something to compare against". Against it: a baseline saved from a session that has just been
measured as non-compliant enshrines that session's rates as the reference. Possibly the advice is to
save one only from a run whose numbers the user is content with, which is a judgement rather than a
step — and it may belong in `session-bash-audit` rather than here.]

## Recommended direction

Reword to name what is skipped rather than "this step": run the audit either way, and drop only
`--compare` when no local baseline exists. Roughly:

> The baseline is one **you** saved with that skill's `--save-baseline`, which writes to
> `~/.local/state/session-bash-audit/`. **Without one, run the audit anyway and drop `--compare`** —
> the rates and `exit-masked` stand on their own, and only the comparison needs a baseline. Never
> compare against a baseline measured on somebody else's machine: it reports how your session
> differs from their setup rather than from your rules.

Small and additive. The 2026-09-03 correction stays intact; what changes is that the escape hatch
stops cancelling the two paragraphs that follow it.
