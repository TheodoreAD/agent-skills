---
status: landed
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

## Open question, answered 2026-09-04

**Yes, tell a no-baseline run to save one, and the objection does not hold.** It rested on a
baseline saved from a non-compliant session "enshrining that session's rates as the reference" — but
nothing in `audit.py` reads a baseline as a target. `EXPECTATIONS` is directional: every entry is
`down` or `zero`, so the verdict is computed against the _delta_, never against the baseline's
absolute numbers. A baseline measured on a bad day therefore sets a bar the next run must beat,
which is the useful case rather than the dangerous one — and the alternative, saving only from a run
whose numbers you like, is what actually corrupts the series, since it makes the reference a
selection rather than a measurement.

The advice belongs in `session-bash-audit` beside the flag, and it is one sentence.

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

## Migrated to

- `skills/session-harvest/SKILL.md` step 5 — the reworded baseline sentence ("run the audit anyway
  and drop `--compare`") plus a PITFALL recording that the first wording said "skip this step".
  Landed 2026-09-03 in `718c05e` / `ceb712d`; this plan was the record of why.
- `skills/session-bash-audit/SKILL.md` — the answer to the open question, beside the flag it is
  about: save the first baseline even when its numbers are bad, because `EXPECTATIONS` is
  directional and a curated reference is the thing that would actually corrupt the series. Commit
  `7403e79`, 2026-09-04.

Not migrated: the session id and the 23%-over-189-calls measurement, which were evidence that the
narrow reading was the useful one rather than a rule anybody needs to follow.
