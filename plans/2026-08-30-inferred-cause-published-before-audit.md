---
status: idea
updated: 2026-08-31
---

# An inferred cause is written as fact, published, and audited too late

Merged 2026-08-31 from `2026-08-30-harvest-does-not-recheck-claims-the-session-wrote.md`, which
owned the harvest-audit half and is **merged away and deleted** —
`plans.py archive --show 2026-08-30-harvest-does-not-recheck-claims-the-session-wrote.md` reads it
back. That plan's own account of the cause was itself wrong, and is corrected in place below rather
than appended, so the wrong version does not stand above the right one.

## The gap

`session-harvest` step 1 already says anything shaped like a convention must be checked for truth
**before being proposed**. That check is scoped to candidates the harvest is about to route.

It does not cover the larger surface: **claims the session already wrote into files, hours earlier,
during ordinary work.** Those are committed, they read as settled, and no step looks at them again.
A long session that writes plans and `contributing/` pages as it goes can commit a dozen causal
claims, and the harvest will faithfully report where each file went without ever asking whether any
of it is true.

The asymmetry is what makes it worth a step: a candidate proposed at harvest time gets scrutiny
precisely because it is being proposed, while a claim written at hour two is never revisited.

## What it cost — one fact, asserted three times, wrong twice

All three versions concerned why a `uv run` invocation destroyed a project's `.venv`. They were
written into a `repo-tasks` plan, in this order:

1. **"because the tool's resolution wanted a different interpreter than the venv had"** — blamed
   `deptry`, the tool named on the command line. Wrong; `deptry` was irrelevant.
2. **"`uv run` resolves the interpreter from uv's own default rather than from the existing venv"**
   — written _by the first harvest, as the correction to (1)_, from a scratch-project measurement.
   **Also wrong**: there was no default in play.
3. **The actual cause**: `~/.zshenv` exports `UV_PYTHON=3.14`, which uv reports as
   `Using Python request 3.14 from explicit request`, so every uv invocation on that machine asks
   for 3.14 whatever the project declares.

[PITFALL: **the correction step is itself a place where inferred causes get written.** Version (2)
was produced by the machinery meant to catch version (1), under time pressure, from a measurement
that was real but incomplete — the scratch project reproduced the destruction without ever asking
_why_ uv wanted 3.14. A run that has just found one wrong because-clause is in exactly the frame of
mind to write another, and it has just earned the confidence to state it plainly.]

## The audit works, and it is too late

Both wrong versions were caught by a harvest and by nothing else, so the audit earns its place. But
version (2) was written during the first harvest and **pushed** with nineteen other commits before
the second harvest found it. For roughly forty minutes the repo published a confident causal
explanation that was false, inside a `[PITFALL:` tag — the shape a future reader trusts most.

Version (1) only got corrected at all because it was also a `~/AGENTS.md` candidate, so step 1's
truth-check caught it on the way out. **A claim with no onward destination ships unchecked**, which
is the ordinary case rather than the exception.

## Recommended direction

Two controls, because the audit alone fires after the commit and sometimes after the push.

**At write time, which is the cheaper half and already in `plan-docs`' vocabulary:** a
because-clause the session did not measure gets `[UNVERIFIED:` when it is written, not a confident
sentence a later pass may or may not revisit. Both wrong versions would have been tagged under that
rule, and neither would have read as settled.

**At harvest time, as the backstop for when that was skipped:** a step between the loose-ends pass
and the live-state sweep — list what this session committed
(`git log <session-start-sha>..HEAD --name-only`) and re-read the **causal and comparative** claims
in those files: "because X", "faster than Y", "only when Z". Not every sentence; the ones asserting
a mechanism the session inferred rather than measured. Two properties keep it bounded: the list is
short, and the tell is greppable enough to start with — `because`, `rather than`, `so that`,
`which means`.

Both halves point the same way on ownership: the fix probably belongs in `plan-docs`' tagging
guidance rather than in `session-harvest`'s procedure, with the harvest step as the backstop.

## Open questions

[NEEDS CLARIFICATION: is "did you measure the because-clause, or infer it?" a question a session can
reliably answer about itself in the moment? Version (2) felt measured — a scratch project, a
reproducible table — and was still an inference about the mechanism behind the numbers. If the
distinction is not reliably self-assessable, the tagging rule degrades to tagging everything, which
is the same as tagging nothing. This is the sharper form of the original plan's question about
whether the fix belongs to `plan-docs` or to `session-harvest`, and it has to be answered first: a
tagging rule nobody can apply is not a fix wherever it lives.]

[NEEDS CLARIFICATION: how does the harvest half interact with the report's length? The report is
already long, and a per-claim audit could add a section nobody reads. Better as a silent pass that
reports only what it changed than as a section listing everything it checked and found fine.]

[UNVERIFIED: two occurrences, both in one session and both about the same underlying fact, so this
is one incident observed twice rather than two independent data points. Whether inferred causal
claims are a general pattern across sessions is unmeasured — `rg -c 'because' plans/` across a few
repos would say, and would also say whether the greppable-tell approach has a tolerable hit rate
before anyone builds on it.]
