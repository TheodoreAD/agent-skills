---
status: landed
updated: 2026-09-02
---

# A broad "how do I go about X" request selects no skill at all

## Context

`plans/2026-09-01-python-refactor-audit-skill.md` shipped `python-refactor-audit` at 11/12 and is
retired; the measurement lives in `skills/python-refactor-audit/references/prior-art.md` and the
pitfall in `skills/skill-fitness/references/measurements.md`. What that plan left open is the case
it could not close, and this plan owns it.

**Case 1 of `refactor-audit-candidate.json` is a reproducible miss to silence.** The prompt is the
flagship one — "this module is 3,000 lines and nobody has ever reviewed it as a whole — how do I
restructure it without breaking anything?" — and across two live runs of three probes each it fired
the skill **once in six**. Every other case in the suite held at 3/3 both times, precision 1.0,
nothing stolen.

Two causes are already ruled out, which is what makes this worth its own plan rather than a redraft:

- **Not truncation.** `fitness.py budget` after the run reported no new truncated listing and no new
  bare-name observation, so all 36 probes saw the full description. The priority-0.0 hypothesis for
  a brand-new skill is refuted for this case and must not be reused to explain it.
- **Not vocabulary**, which is the corpus's usual cause of a miss to silence. The description
  already carries the prompt's own words nearly verbatim — "auditing a file nobody has reviewed as a
  whole", "how to restructure it safely" — and three narrower prompts for the same skill fire 3/3 on
  that same wording. The same sentence also selected nothing for the rejected extend option, so it
  is the **request shape** that is hard, not this description.

The working hypothesis is therefore about the request, not the skill: a broad "how do I go about X"
seems to be answered directly rather than routed, while a narrow "which tests may I edit during a
rename" routes. If that generalises it is a fact about the whole corpus, not about one skill, and it
would change how descriptions are written everywhere.

## Open questions

[DECISION: **it does not reproduce — answered by the test this tag asked for, 2026-09-02.** Two of
the three broad prompts fired 3/3 and the third selected a defensible alternative, so the finding is
not about request shape and does not belong in `skill-fitness`' guidance as a rule. It is recorded
there as a refuted heuristic instead, which is the honest destination.]

[DECISION: **moot, and it was conditional on the refuted premise.** "If a broad request is answered
directly rather than routed" is the antecedent, and it is false — broad requests were routed. There
is nothing here to document as a limit.]

[DECISION: **the usage-data assumption moves to the successor rather than being resolved here.** It
was never really about this plan's hypothesis: it questions whether usage-weighted priority lifts an
entry that truncation has already been ruled out for, which applies to any skill missing for reasons
other than listing pressure. `2026-09-02-python-conventions-misses-its-own-vocabulary.md` carries
the live version of it, restated against the pair that actually reproduces.]

## Recommended direction

Do not redraft the description. That is settled — with vocabulary and truncation both ruled out, a
redraft is a guess, and an unmeasured wording is the one move `skill-fitness` says not to make.

Run the three-skill generalisation test first, because it is cheap and it decides which repo-level
document owns the answer. `trigger.py run skills/skill-fitness/evals/refactor-audit-candidate.json`
re-measures the original case at the same time; each run costs 12 cases x 3 probes.

## Outcome, 2026-09-02: the hypothesis is refuted

The generalisation test this plan asked for was run — three matched pairs differing only in breadth,
one per high-usage skill, three runs each, in `skills/skill-fitness/evals/broad-request-shape.json`.

**Broad prompts fired 3/3 for both `plan-docs` and `session-bash-audit`**, so "a broad _how do I go
about X_ request is answered directly rather than routed" is not true of this corpus. The plan
predicted all three broad halves would miss; two fired perfectly and the third selected
`python-refactor-audit`, which is arguably the correct skill for it.

**What the same run found instead is the opposite shape**: the narrowest, most in-vocabulary prompt
in the suite — "Should this return a bare tuple or a `NamedTuple`?" against a description containing
the word `NamedTuple` — selected nothing in two runs of three. Truncation was ruled out the same way
as before: no new truncated listing and no new bare-name observation after the run.

That is a different plan, and it has one:
`2026-09-02-python-conventions-misses-its-own-vocabulary.md` carries the surviving thread, including
this plan's original unexplained case and the two causes already eliminated, so neither is
re-derived.

[DECISION: **retired rather than rewritten.** Its title, its framing and its recommended direction
are all built on a hypothesis that measurement contradicted, so editing it in place would leave a
file whose name asserts something known to be false. The successor's name says what was actually
found.]

## Migrated to

- `skills/skill-fitness/evals/broad-request-shape.json` — the suite, with the reasoning for the
  matched-pair design in its `about`.
- `skills/skill-fitness/references/measurements.md`, "The ledger of failed heuristics" — entry 6,
  the refutation itself, plus the suite-design lesson that an `expect` set by the author is a
  hypothesis too and a failure against a wrong expectation is evidence of nothing.
- `plans/2026-09-02-python-conventions-misses-its-own-vocabulary.md` — the live thread.
