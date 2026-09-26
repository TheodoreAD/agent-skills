---
status: idea
updated: 2026-09-26
---

# `GATE_RE` has no term for the confidentiality scan, so a masked one reports as a listing

## Context

Found 2026-09-13 by a harvest auditing its own session. The session had three `exit-masked` calls
and `audit.py` reported them as `0 wrapped a gate, 3 a listing`. All three were the same command:

```shell
python3 ~/.agents/skills/plan-docs/scripts/plans.py scan --path <a store directory> 2>&1 | head -5
```

`plans.py scan` is the **confidentiality gate** — the check `~/AGENTS.md` and this repo's own
`CLAUDE.md` both require before every commit to a repo that is or might become public, and the one
whose failure publishes a client's or employer's name into a history that cannot be edited back. It
is not a listing.

`GATE_RE` in `skills/session-bash-audit/scripts/audit.py` matches test, lint and type-check runners:

```python
r"\b(inv\s+\S*(quality|test|check|precommit)|pytest|basedpyright|ruff\b|mypy|npm\s+(run\s+)?test"

r"|cargo\s+test|make\b|tox|nox|pre-commit\s+run)"
```

Nothing in it reaches `plans.py scan`. `--path` does not contain `check`, and the vocabulary was
built from the CI-shaped gates the adherence corpus was measuring.

**The consequence is a specific wrong sentence in the one place the skill tells you to trust the
number.** `session-harvest`'s step 5 says, in as many words: _"when `m` is zero the greens were
never at risk, whatever the shell does: no claim rested on a masked exit code, because no masked
call was a gate. That is a shorter and stronger answer than the pipefail check below, it needs no
extra command"_ — and it names that branch as the common shape for a session that runs its gate
unpiped and pipes only listings. A harvest following it correctly would have stopped at "0 gates
masked, nothing to check" while three confidentiality gates sat behind a `head -5`.

**This run did not stop there, and the reason is worth recording rather than the outcome.** The same
skill carries a separate rule — _"a zero that agrees with what you hoped is the one to check, and
the tell is a zero on a row you have a specific reason to expect a hit on"_ — and the reason to
expect a hit was that the three masked commands were visible in the same output. So the safety net
held, by a rule written for exactly this and confirmed twice before on the neighbouring matcher.

## Open questions

[DECISION: **This is the same failure as `claims` having no term for CI, on a different matcher.**
Confirmed 2026-09-06 and already filed: `claims` reported `0 green-gate messages` for a session
whose text said "both CI legs green" six times, because its vocabulary was the local gate's.
`GATE_RE` is that shape one layer over — a vocabulary assembled from the gates that happened to be
in view when the split was built, reported as a complete answer.

Worth stating as a pattern rather than as two incidents, because the fix for each is a term and the
fix for the class is not: **every matcher in this skill that classifies a command by a word list
will under-report the gates nobody had in mind when the list was written**, and each under-report is
silent and reads as a clean result. The gate/listing split is newer than the corpus it was derived
from (a median of 14 distinct masked command shapes per session, per `masked_gate`'s own docstring),
so the list has never been audited against the shapes it does not match.

A third instance followed on 2026-09-26, on `claims` again: a gate-green claim that never uses the
word "gate". It was fixed on its own matcher in `558c814`, and its now-retired plan,
`2026-09-26-claims-misses-a-gate-green-said-without-the-word-gate.md`, is readable with
`plans.py archive`.]

[NEEDS CLARIFICATION: **Which terms to add, and whether a word list is the right mechanism at all.**
The narrow fix is one alternation — `plans\.py\s+scan`, and probably `scan\s+--mode` for the
spelling that names a mode rather than a path. Cheap, correct, and it fixes this instance only.

The wider question is whether a gate should be recognised by **what it is** rather than by its name.
A gate is a command whose exit code is load-bearing, and this family already has a marker for that
idea in prose: the repo's own quality gate, the confidentiality scan, and the deletion gates in
`plans.py set-status` are all "refuses on a hit" commands. Nothing enumerates them. An alternative
worth weighing before adding a term: read the list from the repos themselves — the commands
`AGENTS.md` and `CLAUDE.md` actually instruct a session to run before committing — which is the same
move `scan` itself makes for private terms, deriving them from the machine rather than from a list
somebody maintains.

Against that: it is a lot of machinery for a row that is already a secondary signal, and a
derived-list bug is harder to see than a missing word. Not obvious; decide before implementing.]

[PITFALL: **A missing term here is worse than a missing term in `claims`, because of what the two
answers are used for.** A `claims` miss under-reports how many times a session told the user
something was green — embarrassing, and the re-run settles it. A `GATE_RE` miss tells a harvest it
may **skip the verification step entirely**, and the gate it skipped verifying is the one whose
failure mode is irreversible: a push cannot be taken back, and the scan is what stands between a
client's name and a published history.

On this machine the exposure is currently bounded by something unrelated to this skill — `PIPE_FAIL`
is set in every agent shell, so the pipeline reported `scan`'s real exit code and the three greens
were true. That is the guard doing its job and it is not a reason to leave the term out: the same
shape in CI, in a container, or on a machine without that snippet loses the exit code, and the skill
itself says so two paragraphs below the branch this bug fires in.]

## Recommended direction

1. **Add the term**, as the immediate fix — `plans.py scan` in `GATE_RE`, with a comment naming why
   a confidentiality gate belongs in a list that otherwise reads as test runners.
2. **Re-score the corpus rows that reported `0 wrapped a gate`**, since that verdict is what the
   harvest skill tells a reader to act on. How many of the 67 sessions' zeros are this bug is
   unknown and is one re-run with the widened pattern.
3. **Then decide the wider question above** — a maintained word list against a list derived from
   what the repos instruct — rather than treating step 1 as the whole answer. Step 1 is what makes
   the next harvest correct; it does nothing about the next gate nobody thought of.
4. **Say in `session-harvest` that the zero-gates branch rests on a word list**, so a reader taking
   the cheap exit knows what it assumes. One clause, in the paragraph that currently presents it as
   strictly stronger than asking the shell.

## Evidence

Session `58cd1fad-94b4-4517-a1bc-286cfc1142b9`, harvested 2026-09-13. 56 Bash calls to the harvest
boundary, `exit-masked 3 (5%) — 0 wrapped a gate, 3 a listing`, and the three samples printed
underneath it are all `plans.py scan`. `setopt` confirmed `pipefail` in force, and an unpiped re-run
of the scan against the same content returned `0 hit(s)`, so nothing was published that should not
have been — the finding is the classification, not a leak.
