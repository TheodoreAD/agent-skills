---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Two proposed additions to `absorb`: a next-session prompt, and a retirement prompt

Merged 2026-08-30 with `2026-08-29-retirement-prompt-on-the-session-sweep.md`. They were always one
decision: both were requested on 2026-08-29, both concluded that `plans.py absorb` is the only
once-per-session call and therefore the carrier, and two independent additions to one command is how
a single surface acquires two half-designs. **Decide the surface once, for both, before building
either.**

The two are not equally alive. The next-session prompt has been argued down to a small residue by an
actual attempt; the retirement prompt has a measured backlog behind it and is the stronger of the
two.

## Part 1 — the next-session prompt

Requested 2026-08-29: the harvest should append a prompt for the next session, catching the most
likely and immediate things.

The gap is real and specific. A harvest ends in a report ordered least- to most-urgent, whose last
zone — "Needs action now" — is deliberately the highest-value part. That report is **prose, read
once, by a user who is about to close the session.** Nothing carries it forward. The next session
starts cold, re-derives what it can from `git status` and `plans/`, and re-derives nothing about
ordering, blockers, or what was deliberately deferred five minutes before the window closed.

There is no prior art to build on: neither `session-harvest` nor `plan-docs` has any next-session or
handoff mechanism today (the one occurrence of "handoff" in `SKILL.md` means something else — work
owed to a _parallel_ session).

### What it would have had to carry

A `repo-tasks` session, ending with: one unpushed commit, an incoming filed plan awaiting `absorb`,
a batched cross-repo sweep deliberately deferred by the user across three repos, nine plans owed
retirement, and a `[DEFERRED:]` tag that had just come due because the restructure it was waiting on
landed mid-session. None of that is derivable from a cold start; all of it was in the report.

### The design constraint is staleness, and it is not hypothetical

**A next-session prompt is a snapshot of live state, and on this machine live state changes under
you.** Measured inside the single hour that produced this request:

| assertion, when written                   | how it went stale                                                          |
| ----------------------------------------- | -------------------------------------------------------------------------- |
| "`absorb`: silent, nothing waiting"       | a parallel session filed a plan for this repo minutes later                |
| "the plans store is clean"                | went dirty, then clean, then dirty again — twice                           |
| "6 plans await retirement"                | became 9, partly by this session's own subsequent status fix               |
| the store "has no remote, deliberately"   | a two-tier split landed mid-session; the shareable tier may have one       |
| "nothing is filed for `agent-skills` yet" | trusted from a 10-minute-old check; a duplicate plan was filed as a result |

The last row is the one that matters most: a stale assertion did not merely mislead, it **caused
duplicated work**. A prompt asserting yesterday's state to a session that trusts it is that same
failure with a longer fuse.

[PITFALL: the natural implementation — write the report's last zone into a file — produces exactly
the artefact that fails this way, and it fails silently. A confidently-worded stale prompt and an
accurate one read identically, which is the same silent-by-construction shape the skill's own
CI-poll and stale-fetch bullets are about. Whatever this becomes, it cannot be a list of asserted
facts.]

[DECISION: **the prompt was re-filed as an ordinary plan, and the "prompt" framing was the thing
that had to go.** Settled 2026-08-29 by writing a real one twice. The four items it carried were
follow-up work — merge these plans, retire that one, absorb across repos — which is what `plans/`
already exists for, and `plans.py list` already surfaces `in-progress` above everything else. See
`plans/2026-08-29-store-tier-split-follow-ups.md`.

This weakens the case for building anything. The honest answer from one real attempt is that most of
a handoff falls on the `plans/` side of the boundary, and what is left may not justify a mechanism.
The residue worth measuring is ordering and immediacy — a plan file says what is open, not what to
do first — plus the delete-when-done expiry, which nothing else provides.]

[NEEDS CLARIFICATION: does the prompt assert state or name the checks that re-derive it? Asserting
is what makes it useful — "push `103b0b6`, then absorb the incoming plan" is actionable in a way
"run `git status`" is not. Naming checks is what makes it survive a week on the shelf. The likely
answer is both, split visibly: a short "here is what was true at <timestamp>" block that the reader
is told to re-verify, and the commands to do it with. But an unread caveat is not a safeguard, so
the split has to be structural rather than a sentence of hedging.]

[NEEDS CLARIFICATION: per-repo or per-machine? The session that asked for this touched `repo-tasks`,
wrote to the plans store, and read three sibling repos. A per-repo prompt is easy to route and
misses the cross-repo work, which is precisely the part that gets forgotten. A per-machine one has
nowhere natural to live and reaches sessions it is irrelevant to.]

[NEEDS CLARIFICATION: appended, or replaced? "Append" was the word in the request, and appending
gives a history of what each session left behind. But an append-only file is a second lifecycle
store with no retirement mechanism — the exact objection `session-harvest` already makes against
parking plan content in memory. Replacing each time keeps it honest at the cost of losing the trail,
which may not be a cost at all, since the trail is in git.]

[NEEDS CLARIFICATION: what is the boundary against `plans/`? Anything durable belongs in a plan;
that is settled. What is left for the prompt is ordering, immediacy, and things too small or too
perishable to earn a file — "push this", "absorb that", "the blocker on X lifted". If the prompt
starts carrying reasoning it has become a plan with no status field, which is the failure mode the
whole convention exists to prevent.]

[DEFERRED: the failure this feature addresses has a cheaper partial fix that should be priced first
— the harvest already knows which items are urgent, and simply _writing them into the plan that owns
each one_ costs nothing extra and is already the skill's routing rule. The genuine residue is the
items belonging to no plan, which may be a much smaller set than the request assumes. Worth counting
on the next few harvests before building anything.]

## Part 2 — the retirement prompt

Requested directly, 2026-08-29, at the end of a `repo-tasks` session that had just left two plans at
`landed` and reported them to the user under "decisions waiting" — which happened only because a
harvest ran. Nothing in `plan-docs` itself would have raised them.

Retirement is already fully specified: a "Retiring a plan" section with a five-step procedure, a
deletion gate (`tags --file … --tag DEFERRED|UNVERIFIED`), an inbound-reference check (`refs`), and
`archive` to read a retired plan back out of git. The convention is not missing a mechanism. **What
it is missing is a trigger.** `plans/` is defined as "a working set that empties out", and nothing
ever asks anyone to empty it.

### The passive signal exists and is being ignored

`list` prints a footer — "N plan(s) at a terminal status await retirement — `--all` to see them" —
and `--scope family` repeats it. Measured 2026-08-29, machine-wide:

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
sporadic, depends-on-who-turns-up clearing this argues is not a mechanism.

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
thinking about plans. It currently says nothing about retirement: demonstrated 2026-08-29, `absorb`
printed a filing notice for one incoming plan while `repo-tasks` held two `landed` ones, and
mentioned neither.

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
with a `## Migrated to` section has had its expensive half done and is waiting on reference fixes
and a delete, which is minutes. It is both the cheapest to finish and the most likely to be lost,
since nothing distinguishes it in any listing. Detecting it is one grep per terminal plan.]

[NEEDS CLARIFICATION: does the prompt belong to `plan-docs` at all, or to `session-harvest`? The
harvest already surfaced these two, under "decisions waiting", and its whole subject is state a
session would otherwise lose. Against: the harvest is invoked explicitly and rarely, so it reaches
even fewer sessions than `absorb` does; and `plan-docs` owns the lifecycle, so a retirement trigger
living in another skill is the same split-ownership problem as the surface question above.]

[DEFERRED: nothing here proposes retiring the nine that exist. That is a real backlog needing real
sessions, and it should be scheduled deliberately rather than folded into the change that adds the
prompt — otherwise the first run of the new prompt is also its worst-case run.]

[PITFALL: **the status gate was bypassed, and the bypass was invisible because it needed no
`--force`.** `2026-08-29-bare-repo-at-projects-root.md` sat at `landed` while carrying an
`[UNVERIFIED:]` tag, which `plan-docs` says blocks that status. Answered 2026-08-29 by the session
that did it: it set the status by **editing the frontmatter directly** rather than running
`set-status`, so the gate never ran and there was nothing to refuse. The underlying tag was in fact
resolved — the depth-1 assumptions it named were covered by tests in the same commit — but that was
luck of sequencing, not the gate working.

The general shape is what matters: `set-status` is a gate only for whoever chooses to call it, and
hand-editing two frontmatter lines is easier than the command. `--force` exists and is described as
the thing the convention does not do, which quietly frames bypassing as something loud; this one was
silent. Worth deciding whether a retirement prompt should re-run the gates over what it finds,
rather than trusting the `status` field it reads.]

## Recommended direction

**Decide the surface first, once.** Both halves point at `absorb`, and the question "what may
`absorb` say beyond what it filed?" has one answer, not two.

Then, in order of confidence:

1. **Build the retirement prompt** — it has a measured backlog, a cheap detector, and a mechanism
   already fully specified behind it. Put it on `absorb`, ask with `AskUserQuestion` as one question
   for the set, **name the cost in the question** ("retiring these two will take most of a
   session"), make "not now" a first-class answer, throttle by something and say which, and detect
   the stalled case separately so it reads as "finish this" rather than "start this".
2. **Price the next-session prompt against doing nothing.** Count, over the next few harvests, how
   many urgent items belong to no plan at all. If the answer is small, the feature is the harvest
   writing urgency into the plans that already own each item, and nothing gets built. If something
   does get built, it is verify-then-act — each item pairing the command that re-derives its state
   with the action to take if it still holds — timestamped so its age is visible, capped at three to
   five items, and carrying only what a cold start cannot re-derive.

**One candidate is ruled out outright for either half: a harness's own memory store.** Stated by the
user 2026-08-29, after a session filed a real prompt into Claude Code's per-project memory directory
and was corrected: no memories, for any harness, for any project, for any reason. Project data and
user-wide practices are not to be vendor-locked. The carve-out is harness _configuration_ —
`settings.json`, hooks, keybindings — which is expected to differ per harness because it is about
the tool, not about the work. That is a harder constraint than the "staging area" wording in
`~/AGENTS.md` implied, and it disqualifies the option on grounds unrelated to staleness: automatic
loading at session start is worth nothing if only one vendor's sessions get it. Whatever either half
becomes has to be a plain file any agent can read, reachable by a documented command rather than by
a harness feature.
