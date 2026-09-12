---
status: idea
updated: 2026-09-12
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

## A third answer to the second question: a skill that only a person invokes

Proposed by the user 2026-09-12, and it is a direct answer to the open question above rather than a
new topic — _"we might want to explore skills that are only user triggered, never context triggered,
so we can have more targeted skills with attached scripts saved easily, rather than having to
constantly worry about trigger contention."_

The appeal is real and this corpus has the measurements to say so. Trigger contention is not
hypothetical here: `fitness.py overlap` ranks pairs sharing vocabulary, `trigger.py` exists because
a static score was refuted by a live run, and the rule that a new skill's description must not steal
a sibling's is enforced by nothing but care. Meanwhile the listing is **already over budget at a
200k-token window** — 11,601 characters of descriptions against 8,000 — so every added skill makes
the shared surface worse for the ones already there. A skill nobody has to select is a skill that
costs neither.

**The cost model forks on one unverified fact, and everything else follows from it.**

[NEEDS CLARIFICATION: **can a skill be invokable by name while absent from the model-visible
listing?** If yes, a user-only skill is genuinely free: no contention, no listing characters, and
`python-refactor-audit`'s scripts get a home without their `SKILL.md` competing for requests it does
not want. If no — if a skill must be listed to be invokable — then the idea saves contention and
**not** budget, which is a much weaker case, because the listing is the resource currently
exhausted. Nothing gathered so far answers it: the specification's progressive disclosure defines
tier 1 as "the `name` and `description` fields are loaded at startup for **all** skills", and every
loader read renders both, which points at "no" — but that is the default path, not proof that no
exclusion exists.]

[NEEDS CLARIFICATION: **is there any mechanism at all, or would this have to be invented?** The
spec's frontmatter is six keys and none of them is a trigger mode; `allowed-tools` is the only
experimental one and it constrains tools rather than selection. So the options are a spec proposal,
a vendor-specific flag, or a convention with no enforcement — and the middle one collides with this
repo's own principle that anything vendor-specific is plumbing and never a carrier for instructions.
Worth noting the principle is already being amended once, for a distribution manifest; amending it
twice for a selection flag is a different and larger claim.]

[UNVERIFIED: **that invocation by name works without the listing.** Both harnesses do accept a named
invocation — Claude Code takes `/skill-name`, and Codex's prompt says "if the user names a skill
(with `$SkillName` or **plain text**)" — and Codex additionally has a documented tier that strips
every description and renders names alone, which is at least proof that a name-only listing is a
state the system can be in. Whether a skill can be _deliberately_ put in that state, per skill, is
the question. `references/naming.md` in `skill-authoring` records what was established about both.]

**What would make this decidable cheaply**: one skill, marked however the harness allows, and a
`trigger.py run` over requests that should and should not select it. That is the same
draft-then-measure loop this plan already recommends, applied to a mechanism rather than to wording.

[DEFERRED: **the adjacent half of the same request** — a place for the measurement scripts this
session produced, and a way to check the corpus against public surfaces (install counts, registry
presence, name collisions, scanner verdicts). Partly started: `skill-authoring`'s `names.py` now
answers the collision half, and
`plans/2026-09-02-skill-risk-ratings-are-user-facing-and-unwatched.md` already owns the
scanner-verdict monitor and should not be duplicated. What has no home is the corpus-harvesting
apparatus, parked at `$RESEARCH_HOME/measurements/2026-09-12-pitch-and-skill-corpora/` outside
version control. If the answer above is that user-only skills are viable, that apparatus is the
obvious first tenant.]
