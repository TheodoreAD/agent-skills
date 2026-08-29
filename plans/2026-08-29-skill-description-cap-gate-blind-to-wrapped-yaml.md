---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

## Context

Filed from a `power-user-linux-setup` session auditing how `~/AGENTS.md` and the installed skills
divide responsibility. Not written into this repo's tree because the session did not own it.

`tests/unit/test_skill_layout.py` exists to catch the one failure nothing else in the pipeline
notices — a skill that installs cleanly and then never triggers. Its own docstring says so. One of
its three checks does not work.

`parse_frontmatter` scans the frontmatter line by line and skips any line that is indented:

```python
if line.startswith((" ", "\t")) or ":" not in line:
    continue
```

A YAML double-quoted scalar wrapped across several lines therefore contributes only its first
physical line. Every continuation is discarded, and `test_description_is_present_and_within_limit`
measures a fragment rather than the value an agent actually matches on.

Measured 2026-08-29 across all ten skills — the gate's view against the real joined value:

| skill                | gate sees | actual   |
| -------------------- | --------- | -------- |
| `python-conventions` | 611       | **1304** |
| `session-harvest`    | 1000      | 1002     |
| `plan-docs`          | 996       | 998      |
| every other skill    | ≈ actual  | ≈ actual |

`python-conventions` is **280 characters over the documented 1,024-char cap** the test claims to
enforce, and it is the only skill that breaches it. The gate cannot see the one violation it was
written for, and the reason it cannot is that the violation is large enough to have needed wrapping.

The cap is not this repo's invention: Anthropic's skill-authoring reference states `description`
must be non-empty and at most 1,024 characters, and the file's own comment already records it as the
tightest limit among the agents that read this format.

Circumstantial support that this matters behaviourally rather than only formally: across 415 Claude
Code transcripts on this machine, `python-conventions` was invoked **twice**, in a repo family that
is almost entirely Python. That is the under-triggering this repo's
`plans/2026-08-22-skill-trigger-quality-review.md` opened on. An over-cap description is not proven
to be the cause, but it is the one mechanical defect measurable today.

## Open questions

[NEEDS CLARIFICATION: fix the parser, or take the YAML dependency? The module's docstring argues
against PyYAML — "it is a flat `key: value` block by the format's own spec, and adding PyYAML to a
repo whose only Python is this file buys nothing". That reasoning is what the bug disproves: the
block is not flat, because a value long enough to matter gets wrapped. A ~10-line continuation-aware
scan keeps the no-dependency stance; PyYAML makes the parser correct by construction and would also
catch a malformed block the scan silently tolerates. The no-dependency version is probably right,
but the docstring's justification has to be rewritten either way, since it is now on record as the
cause.]

[NEEDS CLARIFICATION: what happens to `python-conventions` once the gate can see it? The description
does not shrink to 1,024 by trimming filler — it is a list of covered topics, and cutting topics off
the end removes trigger vocabulary, which is the opposite of what
`2026-08-22-skill-trigger-quality-review.md` wants. The likelier answer is that the skill is over-
scoped rather than over-described, and the fix is a split — which is a design decision for that
plan, not for this one. Do not let the gate turn green by deleting trigger terms.]

[NEEDS CLARIFICATION: does any agent actually truncate at 1,024, and where? Claude Code was observed
loading the full 1,304-character description into a session's skill listing, so it does not enforce
the cap at read time. Whether the `skills` CLI, the API skill upload path, or another agent silently
truncates is unverified. It changes the severity — a hard truncation means the tail of
`python-conventions`' trigger vocabulary is already invisible in some places — but not the fix.]

## Recommended direction

Rough, in this order.

1. **Make the gate honest before deciding anything about content.** Continuation-aware parse, and a
   regression case asserting a wrapped value is measured whole — otherwise the same bug returns the
   next time someone simplifies the scanner. Test the parser, not just the skills, so the case
   survives a corpus where nothing happens to be wrapped.
2. **Then look at the failure it exposes**, which belongs to
   `plans/2026-08-22-skill-trigger-quality-review.md`, not here.
3. **Consider whether the same blindness exists elsewhere in the checks.** `name` is short and
   unaffected; a future field that can wrap would inherit the defect from the same function.

[DEFERRED: the layout gate checks structure only, by design. A description that parses, fits the cap
and still never triggers passes every check in this file. That is the trigger-quality plan's
territory and is only noted here so the two are read together.]
