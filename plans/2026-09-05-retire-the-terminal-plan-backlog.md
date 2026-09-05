---
status: in-progress
updated: 2026-09-05
---

# The terminal-plan backlog, and retiring it deliberately

## Context

Inherited 2026-09-05 from `2026-08-29-next-session-prompt.md` when that plan was retired. That plan
built the retirement prompt `absorb` now carries, and scoped one thing out of itself:

> [DEFERRED: nothing here proposes retiring the nine that exist. That is a real backlog needing real
> sessions, and it should be scheduled deliberately rather than folded into the change that adds the
> prompt — otherwise the first run of the new prompt is also its worst-case run.]

That was correct and is still live, so it needed a file rather than deletion. `absorb` has been
raising the backlog at the top of every session since 2026-09-02; this is the plan the raising
points at.

The concern is **not** the prompt, which works — it is the standing pile the prompt reports, and the
fact that a plan is retired by a judgement procedure rather than by a command, so nothing drains it
except a session deciding to spend time on it.

## Where it stands, 2026-09-05

Measured with `plans.py list --scope family --all --limit 0` after this session's two retirements:

| location                 | terminal plans |
| ------------------------ | -------------: |
| `agent-skills`           |             16 |
| `power-user-linux-setup` |              1 |

Three were retired on 2026-09-05, in the session that inherited this: the status-gate hand-editing
plan, the harvest script-extraction plan, and the next-session-prompt plan this one came out of.
Four more reached `landed` in the same session — the four script-bug fixes — so **the backlog grew
by four while three were drained**, which is the shape the original measurement found on 2026-08-29
and is the reason this needs scheduling rather than opportunism.

## What a retirement actually costs, measured on three

Worth recording because the estimate is what the scheduling decision turns on, and the spread is
wide:

- **A plan whose content is already shipped** — the status-gate one — is roughly an hour: read it,
  find that the rule is in `SKILL.md` and the reasoning is nowhere, write one rationale section,
  move the one live tag, fix two references, delete.
- **A plan that is mostly a "what landed" record** — the harvest script one — is faster, because
  most of it is code contract that gets dropped once verified against the code. The verification is
  the work: two of its decisions turned out to be in a docstring and a test module docstring
  verbatim.
- **A large plan with two parts and ten decisions** — the next-session one — is the expensive shape,
  and the cost is not length. It is that its two halves migrate to two different skills' rationale
  files, and that most of its Part 2 turned out to be in `plan-docs`' skill body already, which can
  only be established by reading both.

Roughly: three retirements filled most of a session that was also doing other work.

## Open questions

[NEEDS CLARIFICATION: is the right unit a scheduled session, or two or three per session that has
other business? The three done on 2026-09-05 were the second kind and worked, but they were also the
three `absorb` had flagged as aged — the ones with the most obvious case for going. A dedicated
session may be the only thing that clears the ones nobody would pick.]

[NEEDS CLARIFICATION: whether a plan landed **today** should be retired in the same session that
landed it. `plan-docs` says `plans/` is a working set that empties out, which argues yes, and the
three-day throttle exists so a Friday landing does not nag on the Saturday — which argues the
throttle is about nagging, not about readiness. Four plans landed on 2026-09-05 and were
deliberately left, because a plan is easier to retire once its change has survived a few days.]

[DEFERRED: the one terminal plan in `power-user-linux-setup` is not this repo's to retire — writing
into another repo is out. It belongs to a session working there, and `absorb` will raise it in one.
Recorded here only so the machine-wide count is not read as an `agent-skills` number.]

## Recommended direction

Take them oldest-first in small batches, as `absorb` reports them, and prefer the ones it marks
`STALLED mid-retirement` whatever their age — those are minutes rather than a session, and a
half-retired plan is indistinguishable from a whole one in every listing.

Retire this plan when the backlog it tracks is drained, not when the last batch is done: a standing
pile that regrows is a plan with a status, which is the whole argument for it being a file.
