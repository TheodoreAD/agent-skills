---
status: idea
updated: 2026-08-30
---

# `session-harvest` never re-checks the claims the session itself committed

Filed from a `repo-tasks` session, 2026-08-30, by the harvest that found the gap in itself.

## The gap

Step 1 already says that anything shaped like a convention must be checked for truth **before being
proposed** — added after a harvest nearly wrote a wrong pytest claim into a shared doc. That check
is scoped to candidates the harvest is about to route.

It does not cover the larger surface: **claims the session already wrote into files, hours earlier,
during ordinary work.** Those are committed, they read as settled, and no step in the procedure
looks at them again. A long session that writes plans and `contributing/` pages as it goes can
commit a dozen causal claims, and the harvest will faithfully report where each file went without
ever asking whether any of it is true.

The asymmetry is what makes it worth a step: a candidate proposed at harvest time gets scrutiny
precisely because it is being proposed, while a claim written at hour two is never revisited by
anything.

## What it cost, this run

The session wrote into a committed plan:

> `uv run --with deptry` **deleted and recreated this repo's `.venv`** rather than layering an
> overlay over it, **because the tool's resolution wanted a different interpreter than the venv
> had.**

The observed half was certain — it was in the command's own output. The `because` clause was
inference stated as measurement, and it was **wrong in a way that would have misdirected the next
reader**: it blames deptry's resolution. Isolated afterwards in a throwaway project, the real
trigger is that `uv run` resolves the interpreter from uv's own default rather than from the
existing venv, and destroys the environment when they differ — `--with` is irrelevant, and a bare
`uv run` does the same thing.

That correction only happened because the finding was also a `~/AGENTS.md` candidate, so step 1's
truth-check caught it on the way out. **A claim with no onward destination would have shipped
unchecked**, which is the ordinary case rather than the exception.

## Recommended direction

A step between the loose-ends pass and the live-state sweep, or a bullet inside step 1: list the
files this session committed (`git log <session-start-sha>..HEAD --name-only`), and re-read the
**causal and comparative** claims in them — "because X", "faster than Y", "only when Z". Not every
sentence; the ones asserting a mechanism the session inferred rather than measured.

Two properties keep it bounded:

- The list is short, and the session already knows which claims it reasoned to versus measured.
- The tell is linguistic and greppable enough to start with — `because`, `rather than`, `so that`,
  `which means` — in files the session itself touched.

## Open questions

[NEEDS CLARIFICATION: does this belong in `session-harvest` at all, or is it a `plan-docs` concern?
The claims land in `plans/*.md` and `contributing/*.md`, which that skill owns, and it already has a
vocabulary for exactly this distinction — `[UNVERIFIED: ...]` marks a claim designed but not proven.
The honest framing may be that the failure is a **missing tag** at write time rather than a missing
audit at harvest time, in which case the fix is in `plan-docs`' tagging guidance and the harvest
step is a backstop for when it was skipped.]

[NEEDS CLARIFICATION: how does this interact with the report's length? The harvest report is already
long, and a per-claim audit could add a section nobody reads. It may be better as a silent pass that
reports only what it changed — the way this run corrected the plan and mentioned it in one line —
rather than as a new report section listing everything it checked and found fine.]

[UNVERIFIED: one occurrence. Whether sessions routinely commit inferred causal claims, or whether
this run was unusual for how much it wrote, is unmeasured — `rg -c 'because' plans/` across a few
repos would say, and would also say whether the greppable-tell approach has a tolerable hit rate
before anyone builds on it.]
