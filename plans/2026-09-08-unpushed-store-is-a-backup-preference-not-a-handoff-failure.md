---
status: landed
updated: 2026-09-09
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

[DECISION: **the middle option — keep the row and state the actual cost.** Shipped 2026-09-09. The
row survives because it is a real thing to know once a year; what changed is that it now names
off-machine backup as the whole of what it risks, so no report has to invent a consequence. Dropping
it was rejected as deciding for the user, and making it configurable as a setting nobody would find
a reason to change once the honest wording exists.]

[DECISION: **no, and it was checked rather than assumed.** The repo ahead-count keeps its urgency:
an unpushed repo commit means the change is not in the product and CI has never seen it, true
whatever the machine count. Worth the check because the two rows look alike and one habit applied
twice would have demoted both — which is the failure this plan is about, arriving from the other
side.]

[DECISION: **yes, and it goes at the top of step 5 rather than in this bullet.** A row that reports
a fact and stops leaves the reporting session to supply the reason, and it will — plausibly, out of
the nearest thing it remembers. Every other row in step 5 already names what goes wrong; this was
the only one that did not, and it is the one that produced a fabricated consequence, which is as
close to a controlled experiment as this corpus gets. The rule carries a corollary the original
question did not: when a row's cost is small, say that it is small, because a stated small cost
cannot be inflated and an unstated one can.]

## What landed, 2026-09-09

The skill bullet, the general rule at the top of step 5, and the printed rows — the last because a
rule whose evidence the tool does not print is a rule the next run re-derives differently, which is
this corpus's standing argument and exactly what happened here.

## Migrated to

- **The general rule, and this row as its evidence** -> `session-harvest` step 5's preamble.
- **The two costs and the refusal of the handoff story** -> the store bullet in step 5, with the
  wrong claim named as a `PITFALL` so it is refused explicitly rather than merely not stated.
- **Both halves as printed output** -> `_print_store`, held by
  `test_the_store_rows_name_their_own_cost_and_the_two_costs_differ` and
  `test_a_clean_store_is_not_lectured_about_costs_it_is_not_paying` — the second because the lines
  hang off findings rather than off the section, which is the alarm-fatigue shape this corpus
  refuses everywhere else.

Deliberately not migrated: the user's own words, which are the evidence for the decision rather than
a rule anyone needs to re-read.
