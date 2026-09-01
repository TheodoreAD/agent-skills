---
status: idea
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

[NEEDS CLARIFICATION: which of the two documents is right. Reading `idea -> landed` as legitimate
(work that was done without ever being formally planned) argues the gate belongs on the transition
_out of `idea`_, whatever the destination — the strict reading of the skill. Reading it as a rare
shortcut argues for gating every terminal status on `NEEDS CLARIFICATION` as well as `UNVERIFIED`,
which is narrower and catches the case that precedes deletion. The second is cheaper and covers the
incident; the first is what the skill actually says.]

[NEEDS CLARIFICATION: whether `DEFERRED` should gate a terminal status too. The retirement procedure
already says a plan carrying live `DEFERRED` work is not deletable, and that rule is enforced by
nothing — it is prose in a numbered step. The same one-line table could carry it, which would make
the deletion gate real rather than advisory. Against: `DEFERRED` legitimately survives into a
retirement when the item has been migrated to another plan, so the check would need to be a warning
rather than a refusal, and a warning nobody must act on is how a gate stops being read.]

[NEEDS CLARIFICATION: whether a gate keyed on the target status can express this at all. Every entry
in `STATUS_GATES` is `{destination: tag}`; a rule about leaving a status needs the _current_ status
too, which the structure does not carry. A `{(from, to): tag}` mapping is one shape; a small
predicate per destination is another. Worth deciding before writing the fix, since the table is
cited in the skill as the encoding of the prose.]

## Recommended direction

Fix the documentation and the code in the same commit, whichever way the first question is settled,
because the two disagreeing quietly is the actual defect — either alone leaves the next reader
trusting a rule the other half does not implement.

Add a test for the transition that was accepted here. `tests/unit/test_plan_store.py` drives the CLI
for the gates it does cover, so the missing case is one parametrized entry rather than new
machinery, and it is the kind of hole that a test written from the _prose_ rather than from the code
would have caught on the day the table was written.
