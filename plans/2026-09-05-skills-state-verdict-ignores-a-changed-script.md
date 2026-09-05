---
status: idea
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

[NEEDS CLARIFICATION: should a differing `scripts/` produce the same verdict as a differing
`SKILL.md`, or its own? They have different remedies for the reader — a stale `SKILL.md` means
re-read the procedure from whichever side is ahead, a stale script means the next run executes old
code and cannot be re-read into correctness. Arguably the script case is the more urgent of the two
and should say so rather than being folded in.]

[NEEDS CLARIFICATION: whether `references/` should count. It differs for `plan-docs` here, and a
stale `references/` costs nothing at run time — nothing loads it unless the agent opens it, and a
reader opening it in the checkout gets the current one. Counting it may be how this check becomes
noisy enough to ignore, which is the failure the dirty/ahead/stale split was built to avoid.]

[NEEDS CLARIFICATION: whether the dirty and unpushed branches need the same treatment. They are
reached only when `same` is false, so a checkout that is dirty **only in `scripts/`** currently
reports "matches" and never reaches the branch that would have said "another session is
mid-restructure, touch nothing" — which is the case that rule was written for.]

## Recommended direction

Decide the verdict from both facts rather than one, and keep the three-cause split (`dirty`,
`ahead`, `stale`) that already works — the bug is the gate in front of it, not the branches behind
it. Test it the way the corpus tests these: a fixture skill whose `SKILL.md` is byte-identical and
whose `scripts/` differs, asserting the verdict does **not** say the copy matches. That case is
absent today, which is how a check with a `subdirs_differing` field shipped without consulting it.

Worth doing before the next harvest that fixes a script, since that is the run this misleads.
