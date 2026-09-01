---
status: idea
updated: 2026-09-01
---

# The record-shape residue the encapsulation pass deliberately left

## Context

`plans/2026-09-01-plans-py-encapsulation-pass.md` restructured `plans.py` over nine commits and is
retired; the worked example lives in `skills/python-refactor-audit/references/pilot.md`. This plan
carries the three items that pass scoped out on purpose, each recorded there as its own small commit
"before or after" and none of them done. It exists so they are not lost with the file.

All three are the same complaint the pass was about — a shape that is anonymous or mutable where the
rest of the file's records are named and frozen — and none of them is urgent.

## Open questions

[DEFERRED: **`fill_details` mutates the `Retired` it is handed and returns it**, and `Retired`,
`PlanFile`, `RepoInfo` and `_Walk` are unfrozen where the rest of the file's records are frozen.
Scoped out of the pass because the conventions class build-then-enrich as ordinary local mutation,
and bundling it there would have made a large mechanical diff harder to verify as
behaviour-preserving. Its own commit.]

[DEFERRED: **`holding: list[tuple[str, int]]` threaded through `doctor` and `_print_doctor`** is the
same anonymous shape one layer out from what the pass's step 2 counted. The measurement never saw it
because it counted anonymous _returns_, not parameters — which is itself worth knowing before
trusting that count as a clean sweep.]

[DEFERRED: **`_plan_payload(rel, plan)` could take a `ScopedPlan`** now that one exists. The
smallest of the three, and the one most likely to be done in passing by whatever next touches that
function.]

[NEEDS CLARIFICATION: whether these are worth a deliberate pass at all, or should simply be done by
whoever next edits each site. The pass's own stopping rule — the current structure is not impeding
the work, and the restructure serves a speculative need — arguably applies to all three: nothing has
gone wrong because `Retired` is mutable. The honest answer may be to leave this plan open as a
record and let the sites be fixed opportunistically, rather than scheduling a diff that moves no
count.]

[NEEDS CLARIFICATION: whether the parameter-side count should be measured before deciding. The pass
measured anonymous returns and got 22 -> 5; nobody has counted anonymous _parameters_, so the size
of this residue is unknown. One ast walk answers it, and a count near zero settles the question
above by itself.]

## Recommended direction

Measure the parameter side first — it is one script and it decides whether this is three sites or
thirty. If it is three, close this plan by doing them opportunistically and record that as the
outcome rather than leaving it open forever. The oracle rules from
`skills/python-refactor-audit/SKILL.md` apply unchanged: the 65 CLI-driven tests in
`test_plan_store.py` may not change by a character, and a type change under a name every caller uses
needs the output-diff second oracle, captured back to back.
