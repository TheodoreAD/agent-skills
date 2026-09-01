---
status: idea
updated: 2026-09-02
---

# `python-conventions` misses a prompt containing a word its own description contains

Successor to `2026-09-01-broad-how-do-i-requests-select-no-skill.md`, **retired 2026-09-02** because
its hypothesis was tested and refuted. That plan proposed that a broad "how do I go about X" request
is answered directly rather than routed; the test that was supposed to confirm it found the opposite
shape instead, and this plan carries what survived.

## What was measured

`evals/broad-request-shape.json`, three matched pairs differing only in breadth, one pair per
high-usage skill, three runs each:

| case                                                           | expected             | got                         |
| -------------------------------------------------------------- | -------------------- | --------------------------- |
| broad, "design work scattered across repos…"                   | `plan-docs`          | `plan-docs` **3/3**         |
| narrow, "create a plan file…"                                  | `plan-docs`          | `plan-docs` **3/3**         |
| broad, "agents keep ignoring my shell rules…"                  | `session-bash-audit` | `session-bash-audit` 3/3    |
| narrow, "measure how often my sessions pipe through head…"     | `session-bash-audit` | `session-bash-audit` 3/3    |
| broad, "module has grown… clean up how its data is shaped"     | `python-conventions` | `python-refactor-audit` 3/3 |
| **narrow, "Should this return a bare tuple or a NamedTuple?"** | `python-conventions` | **nothing 2/3**             |

Both negatives held 3/3.

**So breadth is not the variable.** Broad prompts fired reliably for two skills, which is what the
retired plan predicted would fail.

## The finding that replaces it

**A prompt containing `NamedTuple`, against a description containing `NamedTuple`, selected nothing
in two runs of three.** That is the narrowest and most in-vocabulary prompt in the suite, and it is
the one that missed.

Ruled out already, so nobody re-derives them:

- **Not truncation.** `fitness.py budget` after the run reported no new truncated listing and no new
  bare-name observation, so all 24 probes saw the full description. `python-conventions` is 949
  characters against the 1024 cap.
- **Not vocabulary**, in the usual sense — the matching term is present verbatim in both.
- **Not breadth**, per the table above.

The one live suspect is **contention with `python-refactor-audit`**, which took the broad case 3/3.
`fitness.py overlap` ranked that pair third by shared vocabulary on 2026-09-01 (sim=0.08, 13 shared
terms) and flagged no shadowing in either direction — but that was measured before the audit skill
gained a measurement table naming shapes like tuples and dicts, which is `python-conventions`'
subject matter.

## Open questions

[NEEDS CLARIFICATION: is the case-1 result a steal or a correct routing? On reflection
`python-refactor-audit` is arguably right for "this module has grown for weeks and nobody has
reviewed the whole thing — how do I clean up how its data is shaped", which is its stated territory.
If so, the suite's `expect` was wrong rather than the corpus, and only the narrow miss counts. That
distinction has to be settled before either result is cited, and it is a judgement about the two
descriptions' intended boundary rather than something a run can answer.]

[NEEDS CLARIFICATION: does the narrow miss reproduce, and is it specific to that prompt? Two of
three is a small sample and selection is not deterministic. The cheap next step is the same case at
more runs, plus two or three sibling prompts on the same subject ("dataclass or Pydantic here?",
"should this be a TypedDict?") — if they all miss, the description has a problem; if only the
NamedTuple one does, it is worth checking whether the audit skill is taking it.]

[UNVERIFIED: that `overlap` would now flag the pair. It was clean on 2026-09-01, and
`python-refactor-audit`'s description has not changed since — only its body did, which selection
does not read. So the expectation is that `overlap` still says nothing, and if the narrow miss is
real, that is a finding about `overlap`'s sensitivity rather than about the pair.]

## Recommended direction

Re-run the narrow case at higher `--runs` with the sibling prompts before touching any wording. The
retired plan's own conclusion still governs: with truncation and vocabulary ruled out, a redraft is
a guess, and an unmeasured wording is the one move `skill-fitness` says not to make.

If it does reproduce, the question to answer first is the boundary between the two skills, not the
wording of either — `python-conventions` owning "what should this value be" and
`python-refactor-audit` owning "this module grew, what is wrong with its shape" was the measured
split when the audit skill was created, and it is worth re-checking that the split still holds now
that both have been edited.
