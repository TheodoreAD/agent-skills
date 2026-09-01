---
status: idea
updated: 2026-09-01
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

[NEEDS CLARIFICATION: does the pattern reproduce outside this pair? The cheap test is to take three
skills that currently fire reliably and write one deliberately broad "how do I go about X" prompt
for each, then run them. If all three miss, the finding is about request shape and belongs in
`skill-fitness`' guidance; if only this one does, it is about `python-refactor-audit` after all and
the vocabulary conclusion above needs revisiting.]

[NEEDS CLARIFICATION: whether anything in a description can counter it. If a broad request is
answered directly rather than routed, no wording reaches it — the model never gets as far as the
listing. That would make this a limit to document rather than a bug to fix, which is a different
outcome from the one a redraft assumes.]

[UNVERIFIED: that usage data will help. The shipping decision deferred this to "the next fitness
audit, when the skill also has real usage behind it", on the assumption that usage-weighted priority
lifts the entry. But truncation is already ruled out for these probes, so priority may change
nothing here — the assumption is worth checking before the audit is planned around it.]

## Recommended direction

Do not redraft the description. That is settled — with vocabulary and truncation both ruled out, a
redraft is a guess, and an unmeasured wording is the one move `skill-fitness` says not to make.

Run the three-skill generalisation test first, because it is cheap and it decides which repo-level
document owns the answer. `trigger.py run skills/skill-fitness/evals/refactor-audit-candidate.json`
re-measures the original case at the same time; each run costs 12 cases x 3 probes.
