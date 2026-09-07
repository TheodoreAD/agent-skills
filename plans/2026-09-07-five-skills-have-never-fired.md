---
status: idea
updated: 2026-09-07
---

# Five of fourteen skills have never been invoked, and two of them were used by hand the same day

## Context

Measured 2026-09-07 by `fitness.py report --root skills`, from `~/.claude.json` usage counts and the
transcript store. Five skills show `last_seen: never`, with zero auto-selections and zero explicit
invocations:

| skill                        | listing chars | what it covers                          |
| ---------------------------- | ------------: | --------------------------------------- |
| `python-refactor-audit`      |           925 | restructuring an existing Python module |
| `python-testing-conventions` |           765 | what a test should cover, pytest shape  |
| `polite-mcp-conventions`     |           748 | the `*-polite-mcp` repos                |
| `mcp-python-conventions`     |           680 | MCP server internals                    |
| `mcp-server-shipping`        |           557 | packaging and registering a server      |

Together they are **3,675 chars of listing** — a third of this corpus's 10,981 — bought and never
used. The listing budget plan filed alongside is where that cost is argued; this one is about why
they do not fire.

**The sharpest instance is `python-refactor-audit`.** The session that measured this ran both of its
scripts, by hand, in the same hour — `count_shapes.py` and `find_mutations.py` over eight modules —
because a human asked for "the python code ones". The skill that owns those scripts was never
selected, and nothing in the request named it.

## What the measurement can and cannot say

`usage` counts selections, so a zero is unambiguous about the outcome and silent about the cause.
Three candidates, and they want different fixes:

- **No matching request has come up.** True by construction for `polite-mcp-conventions` (its repos
  have not been worked on in the window) and plausibly for the two MCP skills. Nothing to fix; the
  skill is insurance.
- **The request came up and another skill took it.** `overlap` reports `python-conventions` as
  possibly shadowing both `python-refactor-audit` (sim 0.080, 13 shared terms) and
  `python-testing-conventions` (sim 0.057) — the parent skill's description is longer and mentions
  restructuring and tests in passing.
- **The request came up and no skill fired.** The `count_shapes.py` case above, which is this one:
  the work was done, the tools were the skill's own, and the skill was not consulted.

[NEEDS CLARIFICATION: which of the three each skill is in. `trigger.py` answers it directly — score
a handful of real requests from the transcript store against the installed set and see which skill
wins — and that is a measured answer rather than a reading of the descriptions. It costs `claude -p`
runs, so decide whether to spend them here.]

## Open questions

[NEEDS CLARIFICATION: **is "never fired" a defect at all for a reference skill?** A convention skill
that nobody has needed is not the same as one that loses a request it should have won. The corpus
already argues that a rate nobody can satisfy is worse than none — the same logic may apply to a
usage count for a skill covering work that has not happened. If so the finding is only about the two
Python ones, and the other three are simply idle.]

[NEEDS CLARIFICATION: **if a skill is idle but its scripts are used, does the skill need a trigger
change or does the script need a home?** `python-refactor-audit`'s scripts earned their keep the day
this was filed while its `SKILL.md` did not. Splitting the tools out of the skill is one answer;
wording the description so a "audit this module" request reaches it is another.]

## Recommended direction

Run `trigger.py` over a small set of real requests taken from the transcript store — including the
one that ran the two scripts by hand — before touching any description. Published measurement puts
unmeasured model-authored descriptions below having no skill at all, and this corpus's own rule is
that a description is measured rather than reworded on a hunch.
