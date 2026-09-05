---
status: in-progress
updated: 2026-09-06
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

## The backlog is currently invisible to the thing meant to raise it

Measured 2026-09-06, and it is the finding that decides both questions below. **`absorb` printed no
retirement prompt at all.** The aged half fires at `updated + RETIREMENT_PROMPT_AFTER_DAYS` (3), and
15 of the 16 reached `landed` on 2026-09-05, one on 2026-09-04 — verified against git rather than
read off the stamps, by finding the first commit in which each file's frontmatter carried a terminal
status. Stamp and landing agree in all 16, so nothing is drifting; the plans are simply all new.

So the prompt is silent until **2026-09-08**, when 15 arrive in one run — and it shows five rows
before collapsing the rest to a count. Left alone, the first substantive run of the prompt is its
worst-case run, which is the exact outcome the inherited `DEFERRED` wanted scheduling to prevent.
Only `list`'s passive footer reports the pile in the meantime, and it is a footer on a command
nobody runs unless they are already thinking about plans.

## What the 16 actually are

| destination rationale file                         | plans | plan lines | file lines |
| -------------------------------------------------- | ----: | ---------: | ---------: |
| `skills/plan-docs/references/design-rationale.md`  |     6 |     ~1,030 |        880 |
| `skills/session-harvest/references/rationale.md`   |     5 |       ~575 |        450 |
| `skills/session-bash-audit/references/research.md` |     4 |       ~620 |        679 |
| `skills/skill-authoring/references/rationale.md`   |     1 |       ~170 |         83 |

2,331 lines, 35% of everything in `plans/`. 61 `DECISION` and 14 `PITFALL` tags to migrate or verify
as already-covered, and **5 `DEFERRED` across 4 plans, which block deletion** until they move to a
plan that stays.

## Decisions, 2026-09-06

[DECISION: **the unit is a batch per destination rationale file, not per age.** Oldest-first was the
inherited recommendation and it has nothing to sort on — 15 of the 16 landed on one day, so the age
spread is a day and any order is arbitrary. The measured cost says what to sort on instead: the
expensive half of a retirement is establishing what the destination already covers, which is a read
of an 83-to-880-line rationale file, and a batch pays that read once for four to six plans rather
than once each. It also surfaces the duplicate-content case that a per-plan order hides — six plans
migrating into one file are exactly the ones likely to be saying the same thing twice.]

[DECISION: **a plan is retired by the session that landed it, once the change is pushed** — not
after a wait. The session that landed it has already read the code and the destination doc, which
are the two expensive parts; a session three days later re-derives both from nothing. This settles
the tension the question named: the three-day throttle is about **nagging**, not readiness, so it
governs when `absorb` raises a plan for _someone else_ to pick up and says nothing about the session
holding the context. The gate is `pushed`, not `landed` — `plan-docs` warns that `landed` does not
mean published, and retirement deletes the file, so retiring an unpushed change deletes the reason
for something that is not in the product.]

**The two compose: the second decision is what stops this backlog re-forming, and the first is only
needed because it was not in force when these 16 landed.** Once landing sessions retire their own,
`absorb`'s aged prompt goes back to being an exception handler for plans that slipped through, which
is what it was designed as.

[DEFERRED: the one terminal plan in `power-user-linux-setup` is not this repo's to retire — writing
into another repo is out. It belongs to a session working there, and `absorb` will raise it in one.
Recorded here only so the machine-wide count is not read as an `agent-skills` number.]

## Recommended direction

Take one destination batch at a time, in the order of the table above, and prefer anything `absorb`
marks `STALLED mid-retirement` whatever its age and whatever batch it belongs to — those are minutes
rather than a session, and a half-retired plan is indistinguishable from a whole one in every
listing. None of the 16 is stalled: all carry no `## Migrated to`, so every one is a full
retirement.

Clear the 4 `DEFERRED`-carrying plans' tags into open plans first within each batch, since those are
the ones that cannot be deleted at the end of the pass and finding that out last wastes the batch's
destination read.

Retire this plan when the backlog it tracks is drained, not when the last batch is done: a standing
pile that regrows is a plan with a status, which is the whole argument for it being a file.
