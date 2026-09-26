---
status: idea
updated: 2026-09-26
---

# `claims` still misses "checks pass", and counts a quoted phrase as a claim

## Context

Found by this session's own harvest on 2026-09-26, the same day `558c814` taught `claims` to count a
green stated as a test count. Run on the session that made that change, `claims` reported **3
gate-green messages, all 3 false**, and missed every real one.

- **Counted, not claims:** two messages quoting the phrase "Green, 707 tests" while describing the
  fix, and one naming the plan file `…-claims-misses-a-gate-green-…`.
- **Missed, real claims:** "Checks pass for the second fix", "the full checks pass", "The quality
  checks and the client/employer name scans passed". None of them has a test count or the word
  "gate", and no alternation covers "checks pass".

## Evidence

A candidate alternation, `\bchecks?\b[^.\n]{0,15}\bpass(?:es|ed)?\b`, was measured the same day over
this machine's transcripts. It adds 31 lines to 1,191. Read in full, roughly two thirds were real
claims ("Ruff and type checks pass", "`inv check` passes cleanly"). The rest were prose: "fix the
`status` task's version-check call to pass `cfg`", "the check that the pass moved anything", and a
check that "passed with a deliberately corrupted expectation", which is a claim about a broken check
rather than a green. That is too noisy to add as it stands.

## Open questions

[NEEDS CLARIFICATION: is there a narrower form, such as "checks pass" only at the start of a
sentence or after a tool name (`ruff`, `dprint`, `inv check`)? Or should `claims` stop trying to
recognise phrasings and count messages that follow a gate call in the transcript instead? The second
is the same move the GATE_RE plan weighs, deriving from what ran rather than from a word list.]

[NEEDS CLARIFICATION: quoted phrases. A claim-shaped phrase inside quotes or backticks, and a
filename containing "gate-green", are both mentions rather than claims. Blanking quoted spans before
matching, as `audit.py` does for commands, would drop them, but it would also drop a real claim that
happens to quote a command's output.]

## Recommended direction

Decide together with `2026-09-13-gate-re-has-no-term-for-the-confidentiality-scan.md`, which owns
the same question for `audit.py`: whether a word-list matcher is the right mechanism at all.
