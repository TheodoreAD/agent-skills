---
status: landed
updated: 2026-09-05
---

# `skills-state` says the install matches when only the skill's scripts changed

## Context

Found 2026-09-05 by the session that had just fixed two bugs in `harvest.py` and ran step 0's own
check afterwards:

```
session-harvest    | installed copy matches the checkout
plan-docs          | installed copy matches the checkout
session-bash-audit | install is stale against a clean, pushed checkout — a re-install is the remedy
```

The installed `session-harvest/scripts/harvest.py` did not contain the function committed an hour
earlier. `rg -c '_contains' ~/.agents/skills/session-harvest/scripts/harvest.py` returns nothing.

## The cause, confirmed

`skill_state` computes both facts and lets only one decide:

```python
same = _same_file(installed / "SKILL.md", source / "SKILL.md")
state |= {"skill_md_identical": same, "subdirs_differing": _subdir_diffs(installed, source), ...}
if same:
    state["verdict"] = "installed copy matches the checkout"
```

`subdirs_differing` is reported in the payload and never read again. So the verdict answers "is
`SKILL.md` identical", while its wording claims the whole copy. The same call that printed the three
clean-looking verdicts above also printed, in `--json`:

| skill                | `skill_md_identical` | `subdirs_differing`         |
| -------------------- | -------------------- | --------------------------- |
| `session-harvest`    | `True`               | `['scripts', 'references']` |
| `plan-docs`          | `True`               | `['references']`            |
| `session-bash-audit` | `False`              | `['scripts', 'references']` |

Two of the three rows contradict their own verdict, in the payload, on the same run.

## Why this one matters more than its size

Step 0 exists because a harvest can silently execute a version older than the source — "skipping
exactly the checks most recently added, and reporting a clean run because it never looked". A skill
whose **script** is stale is precisely that failure, and it is the more likely half: `SKILL.md` is
prose that changes when the procedure changes, while `scripts/` changes on every bug fix. This
repo's own convention says anything derivable belongs in `scripts/` rather than the body, so the
share of a skill that this check cannot see is designed to grow.

It also has the shape three other findings this week had: an instrument reporting clean because it
measured the wrong thing, with the right thing already in hand. `find-exempt` had the flag list and
was missing one entry; `claims` had the code block and did not look at it; here the diff is computed
and discarded one line before the branch that needed it.

## Open questions

[DECISION: **the same three branches, plus a clause of its own.** A stale `scripts/` takes the same
dirty/ahead/stale verdict as a stale `SKILL.md`, because the three causes of a difference are the
same three whichever part differs — but it appends "the stale part includes `scripts/`, which this
session EXECUTES rather than reads". Two verdict vocabularies for one question would have to be kept
in step; one vocabulary with a clause about the remedy does not, and the remedy is the only thing
that actually differs: a stale `SKILL.md` can be re-read from whichever side is ahead, and a stale
script cannot.]

[DECISION: **`references/` does not count.** It is read on demand and inert, so a difference there
changes no run — and `_subdir_diffs` was split into `scripts` and `references` in the first place
because a directory-scoped comparison "fired the most expensive branch in the procedure on a
references-only commit" on 2026-08-30. Letting it back into the verdict would have re-created that
defect one level up. It is still reported, in its own wording: "installed copy matches, except
`references/` — read on demand and inert, so nothing to do".]

[DECISION: **yes, and that was the sharper half of the bug.** The dirty and unpushed branches sat
behind `if same:`, so a checkout dirty **only in `scripts/`** never reached the branch that says
another session is mid-restructure — the exact case that rule exists for, unreachable since it was
written. The gate is now computed from both facts, so all three branches see every difference.]

## What landed

The verdict is decided by `SKILL.md` identity **and** a differing `scripts/`, with `references/`
excluded by design. The move-since-session-start note moved into `_with_move_check` when the verdict
grew an early return, so it cannot be appended by one branch and missed by another — which is the
shape of the defect being fixed, one level down.

Four tests, and the three new ones each cover a branch that could not previously be reached: a
changed script with a byte-identical `SKILL.md`, a references-only difference, and a checkout dirty
only in `scripts/`. Run against this machine afterwards, all three installed skills changed verdict
and all three are now true — `session-harvest` DIRTY rather than matching, `plan-docs` matching
except `references/`, `session-bash-audit` stale in both `SKILL.md` and `scripts/`.

## Recommended direction

Decide the verdict from both facts rather than one, and keep the three-cause split (`dirty`,
`ahead`, `stale`) that already works — the bug is the gate in front of it, not the branches behind
it. Test it the way the corpus tests these: a fixture skill whose `SKILL.md` is byte-identical and
whose `scripts/` differs, asserting the verdict does **not** say the copy matches. That case is
absent today, which is how a check with a `subdirs_differing` field shipped without consulting it.

Worth doing before the next harvest that fixes a script, since that is the run this misleads.

## Migrated to

- **`skills/session-harvest/references/rationale.md`, "Why step 0's own instruments kept reporting
  clean"** — this plan's best observation, generalised: an instrument reporting clean while the
  contradicting field sits in the same payload, three times in one week, and why the payload beside
  a narrow verdict is the first place to look. Also why `references/` deliberately stays out of the
  verdict, since letting it in would re-create the 2026-08-30 defect.
- **`harvest.py`'s comment above `stale_script`** — the cause, the incident, and why `scripts/` is
  the likelier half to be stale as this repo pushes derivable content out of skill bodies. Verified
  present.
- **`tests/unit/test_harvest.py`** — the three previously unreachable branches: a changed script
  with a byte-identical `SKILL.md`, a references-only difference, and a checkout dirty only in
  `scripts/`.

Not migrated: the three-row verdict output and the `skill_md_identical`/`subdirs_differing` table.
They are the evidence, and the fix they argued for is in code with tests on every branch they
exposed.
