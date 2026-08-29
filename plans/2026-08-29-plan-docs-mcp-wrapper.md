---
status: idea
updated: 2026-08-29
---

## Context

Raised 2026-08-29 while reworking `plan-docs`' command surface
(`plans/2026-08-29-plan-docs-ergonomics.md`): should the skill be an MCP server instead of, or as
well as, a skill? Split out of that plan once it was settled as "not now", so the ergonomics work
could close with nothing outstanding while the question stays answerable later rather than lost.

**The answer for now is no, and the bar for revisiting is deliberately high.** The user's position,
stated the same day: get the skill working well first, and do not do this any time soon if that
succeeds. This file exists to record why, and what would have to change.

## Why not, today

[DECISION: **stay a skill; build no MCP server, and specifically not both.** Three reasons, in
weight order.

An MCP server's tool schemas load into every session in every repo, whether or not anything is
planned. That is a permanent per-session context tax, and the work that raised the question was
motivated by cutting token cost — a listing went from 117 lines to 64. Paying that back as a
standing cost in every unrelated session would be a net loss that never appears in any single
measurement.

The valuable half of this skill is judgement, not mechanism: what may not be written in a published
repo, when a plan is deletable, how to triage content at retirement, why a route is configuration
rather than a per-session call. MCP tools carry no prose a model reads before deciding. So the skill
would survive an MCP anyway, the MCP would duplicate only the mechanical half, and there would be
two artefacts to keep in sync — which is the failure mode, not the cost.

`--json` already is the structured interface, uniform across every reading command as of 2026-08-29.
MCP would change the transport, not the contract.]

## What would have to change to revisit

Any one of these, and none of them is true today:

- **A harness with no shell.** The whole design assumes `python3 <path> <command>` is available. An
  agent surface without Bash cannot use this skill at all, and MCP is the answer to that, not a
  preference.
- **Trigger reliability that description wording cannot fix.** Always-visible tools are selected
  differently from a skill that must first match a description. If `plan-docs` keeps failing to fire
  on requests it should own _after_ the description work, that is evidence. The cheaper fix was
  applied first: the description now names "what plans do we have" and "what should I work on next",
  which it did not before. Whether that was enough is exactly what
  `plans/2026-08-22-skill-trigger-quality-review.md` is for — so **that plan's outcome is the input
  to this one**, and this should not be reopened before it produces a result.
- **A second consumer.** One machine's agent sessions do not justify a server. Something else
  needing programmatic access to plan state might.

## If it is ever built

[DECISION: **a thin wrapper importing `plans.py`, in its own repo, never a reimplementation.** The
`mcp-server-shipping` skill owns the packaging conventions (`[project.scripts]`, `uv tool install`
from a local checkout or git, `claude mcp add` and scope choice). This repo publishes vendor-neutral
artefacts only, so the server does not live here. `SKILL.md` would then say "use the MCP tools if
present, else the script" — the skill remains the home of the judgement either way, which is the
whole argument above.]

[PITFALL: **the moment there are two artefacts, the rules drift.** The reason to keep the skill
authoritative is not tidiness. A rule that exists in `SKILL.md` and not in the server's tool
descriptions is a rule that stops applying whenever an agent reaches for the tools — and the rules
in this skill are the confidentiality ones. Any future wrapper must derive its tool descriptions
from the script, not restate them.]

## Open questions

[NEEDS CLARIFICATION: does the context cost actually scale the way the decision above assumes? The
argument rests on "every tool schema loads in every session", which is true of a conventionally
registered MCP server but may not be true of every registration scope or of on-demand tool
discovery. Worth measuring rather than asserting before this is ever reopened — the decision would
not change lightly, but the stated reason should be accurate.]
