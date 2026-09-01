---
status: landed
updated: 2026-09-02
---

# The status gate checks the target status, while the skill describes a transition

## Context

`plan-docs`' SKILL.md states the `NEEDS CLARIFICATION` rule as a property of **leaving `idea`**:

> `[NEEDS CLARIFICATION: …]` — open question — at retirement: **must be zero to leave `idea`**

The implementation states it as a property of **arriving at `planned`**:

```python
# The two gates SKILL.md states in prose, as data. Everything else is a free transition.
STATUS_GATES = {"planned": "NEEDS CLARIFICATION", "landed": "UNVERIFIED"}
```

Those coincide only on the `idea -> planned` path. Every other way out of `idea` is ungated:
`idea -> in-progress` and `idea -> landed` both leave `idea` with open questions intact, and
`landed` is checked for `UNVERIFIED` alone.

**Found by walking into it, 2026-09-02.** `set-status <plan> landed` was accepted on a plan carrying
**two open `NEEDS CLARIFICATION` tags and three `DEFERRED`**, and printed nothing but
`status: idea -> landed`. The tags were in fact stale — the questions had been answered in the body
during the same sitting — but nothing in the command knew that, and the next step after `landed` is
deletion.

## Why this is not the bypass plan

`plans/2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` records two sessions changing a
status by editing frontmatter, so the gate never ran. This is the opposite and arguably worse: the
gate **ran, and passed**. A session doing exactly the right thing — reaching for the command instead
of the editor — gets an approval that reads as verification and is not one for the tag that matters.

Both plans are about the same field and should be read together, but they want different fixes and
merging them would blur that.

## Evidence

- The rule as written: `skills/plan-docs/SKILL.md`, the tags table.
- The rule as implemented: `skills/plan-docs/scripts/plans.py`, `STATUS_GATES`.
- The live case: `plans/2026-09-01-plans-py-residual-record-cleanup.md` was moved `idea -> landed`
  with 2 `NEEDS CLARIFICATION` and 3 `DEFERRED` open. Its retirement commits are `045e74c` and
  `333524d`; the tags were resolved by hand in the first of those, which is what the gate should
  have required rather than left to the author noticing.
- The comment above `STATUS_GATES` claims it encodes "the two gates SKILL.md states in prose". It
  encodes one of them faithfully and re-scopes the other, which is why nobody caught it by reading:
  the code and the comment agree with each other.

## Open questions

[DECISION: **the code was right about the shape and the skill was right about the substance, so the
skill's wording changed and the code gained a gate.** The strict reading — gate the transition _out
of `idea`_ whatever the destination — was rejected on evidence rather than taste:
`idea ->
in-progress` with questions open is the ordinary way work starts, and a gate refusing it
would be routinely `--force`d, which is how a gate stops being read. What actually needed protecting
is the transition that precedes deletion. So `landed` now gates on `NEEDS CLARIFICATION` as well as
`UNVERIFIED`, `in-progress` stays free, and the skill's "must be zero to leave `idea`" — which
described neither the old behaviour nor the new — now reads "blocks `planned` and `landed`".]

[DECISION: **`DEFERRED` stays prose, not a gate.** Its own argument settled it: a `DEFERRED` item
legitimately survives a retirement once it has been migrated to a plan that stays, which is the
common case rather than the exception, so a refusal would be wrong more often than right and a
warning nobody must act on is how a gate stops being read. The retirement procedure's step 2 keeps
it, where the reader is already deciding what to migrate.]

[DECISION: **the destination-keyed table expresses it fine; it just needed a tuple.** The question
assumed a rule about _leaving_ a status, which the structure genuinely cannot carry — but that rule
was rejected above, and what replaced it is a rule about arriving at `landed`, which is exactly what
`{destination: tags}` is for. `STATUS_GATES` values became tuples and the lookup loops over them; no
`(from, to)` mapping and no per-destination predicate. Worth recording that the structural objection
dissolved once the design question above it was answered the other way.]

## Recommended direction

Fix the documentation and the code in the same commit, whichever way the first question is settled,
because the two disagreeing quietly is the actual defect — either alone leaves the next reader
trusting a rule the other half does not implement.

Add a test for the transition that was accepted here. `tests/unit/test_plan_store.py` drives the CLI
for the gates it does cover, so the missing case is one parametrized entry rather than new
machinery, and it is the kind of hole that a test written from the _prose_ rather than from the code
would have caught on the day the table was written.

## Outcome, 2026-09-02

Fixed in code and prose in one change, as the direction below asks, because the two disagreeing
quietly was the defect rather than either one alone.

**The test was written first and watched to fail.** `test_landed_gate_blocks_on_open_questions_too`
asserts the transition this plan was filed about, and it failed on the unfixed code exactly as
reported — `assert 0 == 1`, the plan going `idea -> landed` with a question open. Its counterpart,
`test_in_progress_is_not_gated_on_open_questions`, passed before and after: it pins the behaviour
the strict reading would have broken, so the fix cannot drift into refusing the ordinary case.

**Then the fix refused this plan.** Running `set-status … landed` on this file listed its own three
open questions and exited 1 — the plan that reported the hole being stopped by the gate that closed
it, which is the only verification worth having here.

One cosmetic slip caught in the same run: the new listing printed the tag name twice, because a
hit's text already opens with it. Fixed before committing.

## Migrated to

- `skills/plan-docs/scripts/plans.py` — `STATUS_GATES` values are tuples, `landed` gates on both
  tags, and the comment above the table records why `in-progress` and `abandoned` are deliberately
  free.
- `skills/plan-docs/SKILL.md` — the tags table's `NEEDS CLARIFICATION` row, plus a paragraph under
  it stating that the gate keys on the status being moved _to_, and that the `landed` clause is a
  fix rather than a description.
- `tests/unit/test_plan_store.py` — the two tests above, the second of which exists to keep the fix
  from over-reaching.

Not migrated: the observation that the code and its own comment agreed with each other, which is why
reading never caught this. It is true and it generalises, but it is a remark about review rather
than a rule anyone can act on.
