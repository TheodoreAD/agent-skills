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

## What the backlog actually is

Assigned by counting each skill's name in each plan, which is a starting point and **not** the
answer — see the batches below.

**The backlog is drained: 16 to 0, in four batches on 2026-09-06.** 2,331 lines of plan, 61
`DECISION` and 14 `PITFALL` tags, all either migrated to a rationale file or verified already
present in the code, the tests or a skill body.

The destination table that used to sit here is dropped rather than updated. It was built by counting
each skill's name in each plan, and it mis-assigned a plan in **three of the four batches** — the
correction outlived the table, and it is below.

## Batch 1, 2026-09-06: the two on-disk-location plans

`2026-09-03-where-skills-put-things-on-disk.md` and
`2026-09-03-sensitive-store-is-world-readable.md` — retired, in three commits: migration, then
reference fixes plus deletion.

**The name-counting assignment was wrong about both, and it is worth knowing how.** Both counted as
`plan-docs` plans; both migrated almost entirely to **`skill-authoring`**, because the rules they
produced are corpus-wide rules about what any skill may do, and only their store-specific
consequences belong to `plan-docs`. The count measures what a plan _talks about_, and the
destination is decided by what a plan _concludes_. So the table above is a batching hint, and the
first step of every batch is confirming the destination by reading — which is cheap, since that read
is the batch's shared cost anyway.

What the pass actually cost, against the estimate inherited above: **under an hour for the pair**,
where the estimate for a "content already shipped" plan was an hour each. The saving was entirely
the shared read, and the second plan is a sub-case of the first — a two-plan batch where the second
is free is the shape to look for when choosing the next one.

The other finding: **most of both plans was already shipped, and none of the migration was
mechanical.** `skill-authoring`'s `SKILL.md` already carried every rule, better worded than the plan
that produced them. What had no home anywhere was the _why_ — the platformdirs measurement, the
rejected git-URL keying, the severity-tier argument, and the record of a check that was built and
deliberately deleted the next day. That last one is the case for doing this at all: nothing else on
disk explains why the mode is set and never checked, so the next reader to notice the asymmetry
would have re-added the warning.

## Batch 2, 2026-09-06: the five assigned to `session-harvest`

Four of them genuinely were, and they turned out to be **one finding in four files**: every one was
a step 0 instrument that failed in the way step 0 exists to catch. Two reported clean while wrong,
two failed loudly but named the wrong cause. The rationale section that resulted existed in no
single plan — which is the outcome `plan-docs` predicts for a rationale home organised by the
question a reader arrives with, confirmed here rather than assumed. Everything else in the four was
code contract, verified present in `harvest.py`'s comments and tests rather than dropped on faith;
that verification was the whole of the work and it went quickly.

**The fifth, `2026-08-29-external-contributions.md`, was a `plan-docs` plan** — the second
mis-assignment, and by the same mechanism as batch 1's: it discusses `session-harvest` while
concluding about cross-repo filing. Retired anyway, into `plan-docs`' rationale, since the batch had
already paid for reading it.

Two things worth carrying:

- **A 334-line plan with 17 decisions is not 17 times the work**, because almost every decision had
  already become a rule in `SKILL.md`. What was missing was uniformly the _rejected_ half — the
  same-day `origin:` reversal, the two ways a cwd-based guard fails, why a dirty store means add
  rather than wait. **Retirement is mostly a search for what was decided against**, since the
  conclusions are what shipped.
- **A `DEFERRED` whose condition is met becomes a plan, and this one's condition was met by the
  session doing the retiring.** Its second tag said "worth its own plan if the same-tree pain
  persists after cross-repo commits stop" — and this session hit four instances of it without
  looking. `2026-09-06-two-sessions-share-one-working-tree.md` carries it with that evidence. The
  first tag was checked the same way and found landed, so it was recorded as not carried rather than
  copied forward.

## Batch 3, 2026-09-06: the four assigned to `session-bash-audit`

Three of the four were, and the fourth —
`2026-09-02-skill-output-must-be-actionable-by-its-runner.md` — was `skill-fitness`'s and
`skill-authoring`'s, a **third** mis-assignment by the name count and the one where the count was a
literal tie. Three for three across the batches, which settles it: the count says what a plan
discusses, and a plan discusses the tool it found the problem in while concluding about the tool
that has to change.

Two things this batch adds that the first two did not:

- **One plan needed no migration at all.** `2026-09-05-rg-replace-counter-matches-its-own-prose.md`
  had been written into `research.md` at landing time, in full — the argument, both measured
  instances, the before/after table and the `PITFALL`. Retirement was purely the checking, and it
  took minutes. **That is what a retirement costs when the landing session did the migration**,
  which is the case the same-day decision above is trying to make normal.
- **A `DEFERRED` can be merged rather than rehomed.** Its per-bundle-breakdown tag went to
  `2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md`, which turns out to be the same
  question with a different row in front of it: one rate covering outcomes that are not comparable,
  where the fix is a short list rather than a second column. Appending to the plan that owns the
  concern beat a new file, and the pairing was only visible because both were read in one pass.

The other `DEFERRED`, on making `--note` mandatory, was **not** carried: it reads as deferred work
and argues itself down in its own text. A tag that concludes against itself is a settled no, and
recording it as one is the honest handling — not a new plan nobody will act on.

## Batch 4, 2026-09-06: the last five, and the first honest spread

Five plans into **four** different skills' rationale files — the first batch where the spread is
real rather than an artefact of the name count. It is also the batch that shows what the count was
measuring: these five each concluded about the skill they were mostly _about_, which is why the
assignment happened to work here and failed three times before.

The two findings worth carrying:

- **A plan can be entirely already-migrated and still owe its rejected alternatives.** Every rule in
  all five was in a skill body, and in two cases better worded than the plan. What was missing every
  time was the same shape: the option not taken, and the measurement that killed it — skip versus
  fold for worktrees, manifest versus disclosure, fetch versus don't. Four batches in, this is the
  single most reliable statement about what a retirement is actually for.
- **The objection that kills a fix is often retired by measuring it.** The worktree fix was argued
  against on the grounds that detecting a worktree costs a `git` call per candidate. It costs none —
  `.git` is a file whose `gitdir:` line names the main checkout, and the walker already stats that
  path. The plan that recorded the objection also recorded its own refutation, which is the pattern
  worth noticing: an objection stated in a plan is a claim, and claims in plans are measurable.

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
