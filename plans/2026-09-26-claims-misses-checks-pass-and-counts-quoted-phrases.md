---
status: idea
updated: 2026-09-29
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

## The CI-green row misses it too

Merged here on absorption 2026-09-29 from `2026-09-29-claims-ci-matcher-misses-checks-passed.md`,
filed from repo-tasks without knowing this plan existed. Same gap, the other row: `GREEN_CI_RE` in
`skills/session-harvest/scripts/harvest.py` needs one of `ci|workflow|check run|actions` within 40
characters before a pass word on the same line, or a pass word within 25 characters before one of
`ci|workflow|check run`, with no newline between.

A repo-tasks harvest, 2026-09-29 at boundary `2026-09-29T00:54:24+03:00`, reported
`0 message(s) told the user CI was green` for a session whose closing message, before the boundary,
opened:

> Both pushes went through, and all three checks on the repo-tasks push passed:
>
> - **CI:** quality check, unit tests on Python 3.11 to 3.14, and macOS.

"checks" is not "check run", and "CI" sits on the next line. Nothing was at risk in that session (0
of 187 calls masked, and the CI result came from `gh run watch --exit-status`), which is why it is a
wrong zero rather than a false green. The skill's own text says a zero on a row the reader has a
reason to expect a hit on is the one to check, and this is the row where the reader had one.
Transcript `0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl`, assistant message at
`2026-09-28T21:53:45Z`, phrase "all three checks on the repo-tasks push passed".

That filing proposed adding `checks?` to both `GREEN_CI_RE` alternations and letting the look-ahead
cross one newline into a list that names CI, or matching "passed" followed by a bullet naming a
workflow, with this sentence pinned as a fixture. The noise measurement above bears on it directly:
a bare `checks? … pass` alternation was a third prose. Requiring a CI-naming word within one newline
is narrower than that candidate, so it wants its own measurement rather than inheriting either
verdict.

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
