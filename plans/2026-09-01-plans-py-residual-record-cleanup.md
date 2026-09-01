---
status: landed
updated: 2026-09-02
---

# The record-shape residue the encapsulation pass deliberately left

## Context

`plans/2026-09-01-plans-py-encapsulation-pass.md` restructured `plans.py` over nine commits and is
retired; the worked example lives in `skills/python-refactor-audit/references/pilot.md`. This plan
carries the three items that pass scoped out on purpose, each recorded there as its own small commit
"before or after" and none of them done. It exists so they are not lost with the file.

All three are the same complaint the pass was about — a shape that is anonymous or mutable where the
rest of the file's records are named and frozen — and none of them is urgent.

## What was open, and how each resolved

The tags are struck here rather than left standing, because all five are answered below and a
retired plan carrying open markers is a backlog nobody can act on.

1. **`fill_details` mutating `Retired`, and four unfrozen records.** Done — three froze for free,
   `Retired` took `replace`. See the DECISION below for why the build-then-enrich exemption did not
   cover it.
2. **`holding: list[tuple[str, int]]`.** Done — it is `RepoPlanCount` now.
3. **`_plan_payload(rel, plan)` taking a `ScopedPlan`.** Done.
4. **Whether a deliberate pass was warranted at all, or the sites should be fixed
   opportunistically.** Warranted, but only because the measurement said so first: the residue was
   one anonymous parameter and four mutations, all in one file, which is a single sitting rather
   than a project. Had the parameter count come back at thirty, the honest answer would have been
   the opposite.
5. **Whether to measure the parameter side before deciding.** Yes, and it was the decisive step —
   see the table above.

## Outcome, 2026-09-02

**Measured first, as the direction below says, and the measurement changed the answer.** An ast pass
counting parameters as well as returns found the residue was smaller than the three items suggested
in one direction and better-founded in another:

| signal                          | before | after | note                                 |
| ------------------------------- | -----: | ----: | ------------------------------------ |
| anonymous tuple returns         |      0 |     0 | the pass had already swept these     |
| anonymous tuple **parameters**  |      1 | **0** | `_print_doctor(holding: …)`          |
| attribute mutations, whole file |      4 | **1** | the one left is `Workspace.__init__` |
| `dict` parameters / fields      |   9/11 |  9/11 | unchanged **on purpose** — see below |

All three deferred items are done, in four commits, each verified with the output oracle:
`RepoPlanCount` names the repo/count pair, `_plan_payload` takes the `ScopedPlan` its caller already
held, and the records are frozen — `PlanFile`, `RepoInfo` and `_Walk` for free, `Retired` with
`replace` in the two functions that enriched it.

[DECISION: **the 20 dict parameters and fields are all legitimate, checked one by one against the
record-versus-mapping test rather than counted.** Every one is either keys arriving from outside —
the TOML parsers' `raw`, `roots`, `repos`, `about` — or a local accumulator keyed by data
(`grouped`, `waiting`, `counts`). None is a record wearing a mapping's clothes, so the count staying
flat is the right result and not unfinished work. This is what the audit skill means by reading the
after-numbers honestly.]

[DECISION: **`Retired` was frozen even though the conventions sanction build-then-enrich mutation.**
The sanctioned case is "building a result before returning it", local to one function. `Retired` was
written to in two functions after it had been handed on, which is the boundary-crossing record the
`frozen=True` default is aimed at. `mark_live` also returned `None` while mutating its argument;
returning the list is the more honest signature.]

## Recommended direction

Measure the parameter side first — it is one script and it decides whether this is three sites or
thirty. If it is three, close this plan by doing them opportunistically and record that as the
outcome rather than leaving it open forever. The oracle rules from
`skills/python-refactor-audit/SKILL.md` apply unchanged: the 65 CLI-driven tests in
`test_plan_store.py` may not change by a character, and a type change under a name every caller uses
needs the output-diff second oracle, captured back to back.

## Migrated to

- The four commits themselves, `001e2c7`, `05eeead`, `86db9a1` and `c351e17` — each one property,
  each message saying what moved and what verified it.
- `skills/python-refactor-audit/SKILL.md` — the transferable half: count parameters as well as
  returns, since a return-only measurement is exactly what let the `holding` parameter survive the
  original pass unseen.

Nothing else migrated. The two open questions are answered above by measurement rather than by
argument, and the counts that did not move are explained where they sit.
