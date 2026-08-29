---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `plan-docs` should ask about retirement on its session sweep, not report it in a footer

## Context

Requested directly, 2026-08-29, at the end of a `repo-tasks` session that had just left two plans at
`landed` and reported them to the user under "decisions waiting" — which happened only because a
harvest ran. Nothing in `plan-docs` itself would have raised them.

Retirement is already fully specified. `plan-docs` has a "Retiring a plan" section with a five-step
procedure, a deletion gate (`tags --file … --tag DEFERRED|UNVERIFIED`), an inbound-reference check
(`refs`), and `archive` to read a retired plan back out of git. The convention is not missing a
mechanism. **What it is missing is a trigger.** `plans/` is defined as "a working set that empties
out", and nothing ever asks anyone to empty it.

### The passive signal exists and is being ignored

`list` prints a footer — "N plan(s) at a terminal status await retirement — `--all` to see them" —
and `--scope family` repeats it. Measured this session, machine-wide:

| repo                     | terminal plans                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `agent-skills`           | `2026-08-28-plans-outside-the-repo.md`, `2026-08-29-bare-repo-at-projects-root.md`  |
| `ingesta`                | three, the oldest updated 2026-08-27                                                |
| `power-user-linux-setup` | `2026-08-28-ssh-add-and-askpass-friction.md`                                        |
| `repo-tasks`             | `2026-08-26-integration-tier-version-fixture.md`, `2026-08-26-quality-tool-gaps.md` |
| `olx-polite-mcp`         | `2026-08-18-favorites.md` — `abandoned`, untouched 11 days                          |

The table is left as measured. Since then, `2026-08-29-bare-repo-at-projects-root.md` has been
retired and deleted — read it back with `plans.py archive --show` rather than looking for the file.
That is one of the nine cleared by a session that happened to be working on it, which is exactly the
sporadic, depends-on-who-turns-up clearing this plan argues is not a mechanism.

Nine plans, five repos. Two of the nine reached terminal status in the session that asked for this,
so the backlog grows faster than it drains. The footer has been printing throughout.

[PITFALL: one of the nine is not merely unretired but **stalled mid-retirement**.
`power-user-linux-setup`'s ssh plan already carries a `## Migrated to` section — step 4 of the
procedure, the commit that is supposed to immediately precede deleting the file. The steps after it
never ran. So the failure is not only "nobody starts"; it is also "nobody is reminded to finish",
and a half-retired plan is indistinguishable from a whole one in every listing.]

### Why the sweep is the right place

`absorb` is already the documented once-per-session first call, and it is already silent when it has
nothing to say — the exact property that makes it cheap enough to run unconditionally. It is
therefore the only command in the skill guaranteed to run in a session that is not otherwise
thinking about plans.

It currently says nothing about retirement. Demonstrated in this repo, this session: `absorb`
printed a filing notice for one incoming plan while `repo-tasks` held two `landed` ones, and
mentioned neither.

## Open questions

[NEEDS CLARIFICATION: which command carries the prompt — `absorb` or `list`? `absorb` is the
once-per-session ritual and reaches sessions that never ask about plans, which is where the backlog
actually accumulates. `list` already computes the count and is where someone is already thinking
about plan state, but it is called ad hoc and often, so prompting there risks asking three times in
one session. A split is possible — `absorb` asks, `list` keeps its footer — but two surfaces for one
concern is how the "shared stores" bullet in `session-harvest` ended up wrong.]

[NEEDS CLARIFICATION: what does "ask" mean when the script cannot do the work? Retirement is a
judgement procedure — triage the content by lifecycle, find a home for the rationale, write
`## Migrated to`, fix inbound references, delete — not a command. So the prompt is an offer to spend
a chunk of the current session on something the user did not come here for. That is a real cost and
it argues for the prompt naming it: "retiring these two will take most of a session" is a different
question from "shall I tidy up?".]

[NEEDS CLARIFICATION: every session, or throttled? Nine plans across five repos means a naive
"always ask" fires in most sessions in most repos, and a prompt that is declined repeatedly trains
its own dismissal — the same alarm-fatigue failure that made the footer useless. Options: ask only
above a threshold, ask only about plans terminal for longer than N days, ask once per repo per day,
or ask only when the current session is the one that made the plan terminal. The last is the
narrowest and catches the case that produced this request, but it does nothing about the nine
already there.]

[NEEDS CLARIFICATION: should a stalled retirement be a louder case than an unstarted one? A plan
with a `## Migrated to` section has had its expensive half done — the triage and the migration — and
is waiting on reference fixes and a delete, which is minutes. It is both the cheapest to finish and
the most likely to be lost, since nothing distinguishes it in any listing. Detecting it is one grep
per terminal plan.]

[NEEDS CLARIFICATION: does the prompt belong to `plan-docs` at all, or to `session-harvest`? The
harvest already surfaced these two, under "decisions waiting", and its whole subject is state a
session would otherwise lose. Against: the harvest is invoked explicitly and rarely, so it reaches
even fewer sessions than `absorb` does; and `plan-docs` owns the lifecycle, so a retirement trigger
living in another skill is the same split-ownership problem as the last question. Worth deciding
deliberately rather than by whichever skill is edited first.]

## Recommended direction

Rough, and the questions above come first.

1. **Put it on `absorb`**, as one more thing that command reports when it applies — it is the only
   once-per-session call, and it already has the silence-when-empty property that makes an
   unconditional check acceptable.
2. **Ask with `AskUserQuestion`, one question for the set**, matching how `absorb` already proposes
   the plans it found rather than asking per file.
3. **Name the cost in the question.** An offer to retire is an offer to spend session time; the
   option text should say roughly how much, and "not now" must be a first-class answer rather than
   the implied one.
4. **Throttle by something, and say which.** A prompt that fires in every session in every repo is
   the footer again with more steps.
5. **Detect the stalled case separately** — a terminal plan already carrying `## Migrated to` is a
   different, much cheaper offer, and should read as "finish this" rather than "start this".

[DEFERRED: nothing here proposes retiring the nine that exist. That is a real backlog needing real
sessions, and it should be scheduled deliberately rather than folded into the plan that adds the
prompt — otherwise the first run of the new prompt is also its worst-case run.]

[PITFALL: **the gate was bypassed, and the bypass was invisible because it needed no `--force`.**
This plan spotted `2026-08-29-bare-repo-at-projects-root.md` sitting at `landed` while carrying an
`[UNVERIFIED:]` tag, which `plan-docs` says blocks that status, and could not tell whether the gate
had been skipped or the tag added later. Answered 2026-08-29 by the session that did it: it set the
status by **editing the frontmatter directly** rather than running `set-status`, so the gate never
ran and there was nothing to refuse. The underlying tag was in fact resolved — the depth-1
assumptions it named were covered by tests in the same commit — but that was luck of sequencing, not
the gate working.

The general shape is what matters here: `set-status` is a gate only for whoever chooses to call it,
and hand-editing two frontmatter lines is easier than the command. `--force` exists and is described
as the thing the convention does not do, which quietly frames bypassing as something loud; this one
was silent. Worth deciding whether the retirement prompt this plan proposes should re-run the gates
over what it finds, rather than trusting the `status` field it reads.]
