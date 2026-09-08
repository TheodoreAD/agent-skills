---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/repo-tasks
source_session: 20d8525a-71ae-4cb3-af8a-c3f83e0bcde7.jsonl
source_moment: 2026-09-08T02:15:00+03:00
---

# The harvest reports an unpushed store without saying what it costs, so the report invents a cost

## Context

`session-harvest`'s store bullet instructs a run to report committed-but-unpushed plans as "a real
second finding on the shareable half". It does not say **what the user loses** by leaving them
unpushed. A report has to say why an item is in it, so the gap gets filled — and on 2026-09-08 it
was filled with a claim that is simply false:

> until it happens, the three plans I filed this session sit in the store where only this machine
> can see them, so no future session gets offered them by `absorb`

Stated twice in one session, in the harvest report and again after a push, unchallenged both times
because it sounds like the mechanism working.

**`absorb` reads the local store directory and never the remote.** `plans.py` contains no `fetch`,
no `pull` and no `ls-remote`; every `origin` reference in it is `remote get-url`, reading the URL as
an identity string for frontmatter. The skill's own "What this skill reads, runs and writes" section
says **`Network: none`** outright. So a plan is visible to every session on the machine the moment
its file exists — push state has no bearing on the handoff at all.

The user caught it:

> why did we decide it's such a problem that the plans store is unpushed? i'm only working from one
> machine at a time in long stretches, and if i ever clone another repo to work on another machine i
> will make sure to have everything pushed before i start there, i feel we are over reporting these

## What a store push actually buys

One thing, and it is worth stating precisely so the next report does not re-derive it wrongly:

- **Not** cross-session handoff on the same machine — local directory, per above.
- **Not** cross-machine, for a user whose stated workflow is to push before starting elsewhere.
- **Only off-machine backup.** The store is the sole copy of plans that live in no repo, plus the
  in-transit copy of plans filed `--for` a repo that has not absorbed them yet, so a disk failure
  loses exactly those. That is a backup preference with a low-probability trigger, and it belongs to
  the user rather than to a checklist.

[DECISION: **commit urgency and push urgency are different findings with different owners, and the
skill currently blurs them.** Committing promptly is a real, live, same-machine concurrency cost —
`plan-docs` says a dirty store forces every other session into the add-a-new-file fallback instead
of editing, for as long as it lasts, and that is worth reporting every time. Pushing is a backup
decision on a single-machine workflow. The bullet should keep the first at full strength and demote
the second to a stated preference the user sets once.]

[PITFALL: **the wrong claim is attractive because the right mechanism is nearby.** `plan-docs`
genuinely does have a cross-session handoff story — `new --for` writes into the store and the next
session working in that repo is offered it by `absorb` — so "the handoff needs the store pushed" is
one plausible step away from something true, and reads as a correct recollection of the design
rather than as a guess. That is what let it be stated twice without being checked.]

## Open questions

[NEEDS CLARIFICATION: should the sweep report unpushed store commits at all by default? Options:
drop the row for a single-machine setup; keep it but state the actual cost (backup only) so no
report has to invent one; or make it configurable, since whether an unpushed store matters is
genuinely a property of the user's machine count rather than of the session. The middle option is
cheapest and fixes the observed failure without deciding anything for anyone.]

[NEEDS CLARIFICATION: does the same over-reporting apply to the **repo** ahead-count? Probably not —
an unpushed repo commit means the change is not in the product and CI has not seen it, which is a
real cost independent of machine count. Worth confirming the two are being reported for genuinely
different reasons rather than by one habit applied twice.]

[NEEDS CLARIFICATION: is there a general rule here worth writing into the skill — that a sweep row
must carry the consequence, not just the observation? Every other row in step 5 names what goes
wrong (an orphaned server serves `.env`, a masked exit invalidates a green claim). This row is the
one that names only a state, and it is the one that produced a fabricated consequence.]

## Recommended direction

State the cost in the bullet — one clause, "the only thing an unpushed shareable store risks is
off-machine backup" — and let the report say that rather than reaching for the handoff story. If the
user then wants the row gone entirely on a single-machine setup, that is a second, easy change on
top of an honest first one.
