---
status: landed
updated: 2026-09-02
---

# Two proposed additions to `absorb`: a next-session prompt, and a retirement prompt

Merged 2026-08-30 with `2026-08-29-retirement-prompt-on-the-session-sweep.md`, now **merged away and
deleted** (`plans.py archive --show` reads it back). They were always one decision: both were
requested on 2026-08-29, both concluded that `plans.py absorb` is the only once-per-session call and
therefore the carrier, and two independent additions to one command is how a single surface acquires
two half-designs. **Decide the surface once, for both, before building either.**

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
already exists for, and `plans.py list` already surfaces `in-progress` above everything else. It was
written as the now-retired `plans/2026-08-29-store-tier-split-follow-ups.md`
(`plans.py archive --show` reads it back).

**The experiment ran to completion on 2026-08-30 and it worked**, which weakens the case for
building anything further: a session opened on that plan, ran each item's check, and every item was
either done or turned out to have grown since it was written. The plan was retired the same day —
the delete-when-done expiry happened on its own, because a plan with a status has a retirement
procedure and a "prompt" would not have. The honest answer from two real attempts is that most of a
handoff falls on the `plans/` side of the boundary, and what is left may not justify a mechanism.
The residue worth measuring is ordering and immediacy — a plan file says what is open, not what to
do first.]

These four were the open questions, and all four were answered by what shipped rather than by
argument. They are kept as the questions they were, each with the answer attached.

[DECISION: **both, split structurally — verify-then-act.** The question was whether the prompt
asserts state or names the checks that re-derive it: asserting is what makes it useful ("push
`103b0b6`, then absorb the incoming plan" is actionable where "run `git status`" is not), naming
checks is what makes it survive a week on the shelf, and an unread caveat is not a safeguard. What
shipped pairs each item with the command that re-derives its state and the action if it still holds,
which is the split made structural rather than hedged in a sentence.]

[DECISION: **per-repo, with a test rather than a ban for the cross-repo line.** A per-machine prompt
has nowhere natural to live and reaches sessions it is irrelevant to. Another repo earns a line only
when the item is high-risk or irreversible **and** would change what the next session in this repo
does — an unpushed commit or an open plan elsewhere fails the second half, because that repo's own
session is handed those by `absorb`.]

[DECISION: **neither: printed, never written.** Append-vs-replace was a question about a file, and
the answer was that there is no file. An append-only file would have been a second lifecycle store
with no retirement mechanism — the objection `session-harvest` already makes to parking plan content
in memory — and replacing loses the trail. Printing dissolves both, plus the storage lifecycle and
most of the staleness objection, because the user pastes it into the next session within minutes.]

[DECISION: **the boundary against `plans/` is subtraction, not a definition.** Anything durable
belongs in a plan; what is left is ordering, immediacy and the perishable. The mechanical test that
shipped is stronger than the prose one this question was reaching for: run the next session's own
opening moves — `absorb`, `list`, `git status` plus the ahead-count — and include only the delta.
The cap of five is what keeps the prompt from becoming a plan with no status field.]

[DECISION: **built 2026-09-01, in `session-harvest` step 9, as a printed paste-ready block and not a
file.** The user asked for it a third time, naming the two constraints that resolve most of the open
questions above, and said the reason it keeps disappointing: "I keep asking for this manually and I
don't give all the details."

That is the answer to the DEFERRED below, and it arrived as evidence rather than as a count. The
item belonging to no plan is not the residue — **the residue is the spec.** Step 9 already existed
and said only what to leave out, so every prompt was improvised from whatever the session happened
to remember, which is precisely how it fills with marginal detail. The feature was never a store; it
was a rule for what earns a slot.

Three things settle the design, and each closes a question above:

- **Printed, never written.** The user pastes it into the next session within minutes, which is the
  only reason it may assert anything at all. This dissolves append-vs-replace, the storage
  lifecycle, and most of the staleness objection in one move — the two earlier attempts failed
  because they built an artefact that outlived its accuracy. Nothing to retire, because nothing is
  stored.
- **Built by subtraction.** The next session's own opening moves — `absorb`, `list`, `git status`
  plus the ahead-count — already print the incoming plans, the open work and the dirty state. Run
  them and include only the delta. This is the mechanical test for "marginal", and it is why the
  prompt is short: on a properly harvested session most candidates fail it.
- **Verify-then-act, capped at five plus an opening line.** Each item pairs the command that
  re-derives its state with the action if it still holds, which is the shape the NEEDS CLARIFICATION
  above landed on — and the cap is what keeps it from becoming a plan with no status field.

What survives subtraction is three kinds: **ordering** (nothing on the machine says what to do
first), **perishable state with a short fuse** (a running process, a CI run, a skill edited but not
re-installed), and **a decision not yet in any file** — the last being a self-check rather than a
category, since a non-empty one means step 2's routing failed.

The cross-repo rule was already absolute in step 9 and is now a test rather than a ban: another repo
earns a line only when the item is high-risk or irreversible **and** would change what the next
session in this repo does. An unpushed commit or an open plan elsewhere fails the second half — that
repo's own session is handed those by `absorb`.]

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

The table is left as measured. Two of its rows are gone since:
`2026-08-29-bare-repo-at-projects-
root.md`, and `2026-08-28-plans-outside-the-repo.md` on
2026-08-30 — read either back with `plans.py archive --show` rather than looking for the file. Both
were cleared by a session that happened to be working on that repo, which is exactly the sporadic,
depends-on-who-turns-up clearing this argues is not a mechanism: seven remain, and nothing has asked
about any of them.

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

[DECISION: **`absorb` carries it; `list` keeps its footer.** The split the question feared is not
one, because the three surfaces have three different triggers rather than one concern spread thin:
`absorb` runs once at the top of a session and speaks for the aged backlog; `list` is called ad hoc
and keeps the passive count it already computes; `session-harvest` reports what _this_ session made
terminal, which `absorb` structurally cannot see, running as it does before this session has landed
anything. That last point is also the answer to "does this belong to `plan-docs` or to
`session-harvest`" — it belongs to both, at different moments, and neither can cover the other's.]

[DECISION: **"ask" means one `AskUserQuestion` with the cost inside it and "not now" as a real
answer.** The script prints the sets and says so; the judgement stays with the agent, because
retirement is a procedure and not a command. What the prompt must not do is ask "shall I tidy up?",
which invites a yes to work the user has not been told the size of.]

[DECISION: **throttled by age — terminal for three days or more — and capped at five rows.** Age
beat the three alternatives on one property: it needs no state. A per-repo-per-day throttle or an
above-a-threshold counter has to remember what it asked and when, which is a second lifecycle store
with no retirement of its own — the objection this convention makes to parking anything outside
`plans/`. Three days rather than one so a Friday landing does not nag on the Saturday. The fourth
option, "ask only when this session made it terminal", is not `absorb`'s to take: `absorb` runs
before this session has landed anything, and `session-harvest` already owns that case. The row cap
is the answer to alarm fatigue that the age threshold alone does not give, since the backlog it
draws from is machine-wide.]

[DECISION: **yes — its own group, above the aged one, and raised whatever its age.** A plan carrying
`## Migrated to` is waiting on reference fixes and a delete, which is minutes, so it reads as
"finish this" and not "start this". Detection is one regex against text `read_plan` already has in
hand, so it costs nothing per plan.]

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

1. ~~**Build the retirement prompt.**~~ **Built 2026-09-02**, to this line exactly — see "What
   landed" below.
2. ~~**Price the next-session prompt against doing nothing.**~~ **Built 2026-09-01** — see the
   DECISION in Part 1. The pricing question was answered from the wrong end: the count of items
   belonging to no plan is indeed small, and the thing that was missing was never a store but a
   specification for what earns a slot. What shipped is close to the shape this line predicted —
   verify-then-act, timestamped, capped at five — plus the rule that makes it short, which is to
   subtract everything the next session's own opening commands already print.

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

## Migrated to

Retired 2026-09-05. Two parts, two destinations, and most of Part 2 turned out to need neither.

- **Part 1's history** — the five-row staleness table measured inside one hour, the `[PITFALL:]`
  about a written prompt failing silently, both failed attempts and what each proved, the user's _"I
  keep asking for this manually and I don't give all the details"_ that finally specified it, and
  the three constraints with the questions each closes — to
  `skills/session-harvest/references/rationale.md`, as "Why the next-session prompt is printed and
  never stored", placed immediately after the no-memory-tier section, which is where the second
  failed attempt is already recorded.
- **Part 2's decisions** — dropped, verified present. `plan-docs`' **"The retirement prompt `absorb`
  also carries"** already states all four: the two groups and the stalled one raised at any age, the
  three-surfaces-three-triggers split, age-as-throttle with the "it needs no state" argument and the
  Friday-landing reason for three days rather than one, the row cap, and the one-question rule with
  "not now" as a real answer. It also carries the nine-plans-across-five-repos measurement and the
  known limit about trusting the status field. Migrating any of it would have shipped a second,
  diverging copy.
- **The `[DEFERRED:]` backlog** — to `plans/2026-09-05-retire-the-terminal-plan-backlog.md`, which
  is the live work this plan correctly refused to fold into itself. Three of the backlog were
  retired the day that file was created, and four more landed the same day, so it opens with the
  count going the wrong way.
- **Part 1's other `[DEFERRED:]`** — dropped, because this plan answers it itself: "That is the
  answer to the DEFERRED below, and it arrived as evidence rather than as a count." The cheaper
  partial fix was priced and the residue turned out to be the specification rather than a set of
  items.
- **The status-gate `[PITFALL:]`** — dropped. It is in `plan-docs`' `SKILL.md` as the rule and its
  measurement, and its reasoning is in that skill's design rationale, both migrated there earlier
  the same day from the plan that owned it.
- **The no-harness-memory-store ruling** — dropped. It has its own rationale section, its own
  `~/AGENTS.md` clause and its own sentence in the skill's `description`.
- **The two backlog tables** — dropped. Both were true on one day, and the current count is in the
  backlog plan.

## What landed, 2026-09-02

Part 2 shipped, in `plans.py` and `SKILL.md`, with tests. Both halves of this plan are now built, so
the surface question the plan opened with is answered by the pair rather than by either alone:
`absorb` says what is owed and `session-harvest` step 9 says what to do first.

`absorb` now prints two groups after whatever it filed, and stays silent when both are empty:

- **`STALLED mid-retirement`** — the plan carries `## Migrated to`, so step 4 is done and steps 5–6
  never ran. Raised at any age, with "Minutes, not a session" attached. This is the case the
  `[PITFALL:]` above found sitting in the machine-wide backlog, invisible in every listing.
- **awaiting retirement** — terminal for three days or more, oldest first, five rows before the rest
  collapse to a count and a `list --status landed`.

Then one closing line telling the agent to put it to the user as a single question with the cost in
it, and to treat "not now" as a real answer.

Three constants carry the choices so they are one edit rather than a hunt:
`RETIREMENT_PROMPT_AFTER_DAYS = 3`, `RETIREMENT_PROMPT_ROWS = 5`, and `MIGRATED_RE`, which moved up
to the shared constants and gained `MULTILINE` — `archive` matches it one line at a time and
`read_plan` now searches a whole file for it, the flag being inert for the first caller.

`PlanFile` gained one field, `migrated`, computed where the text is already in hand, so the stalled
detector costs no extra read. Five tests cover it: the backlog raised, a freshly-terminal plan left
alone, the stalled group kept separate from the aged one, the row cap, and the uncapped `--json`
payload.

**Not done, and deliberately:** the existing backlog is still there. Retiring it is the
`[DEFERRED:]` above and wants scheduled sessions, not the first run of a new prompt.

**Known limit, stated in the skill:** the prompt trusts the `status` field it reads, so a plan whose
status was hand-edited past the gate looks identical here. That is the `[PITFALL:]` above, and it is
why "`status:` and `updated:` are `set-status`' output" now sits at the top of `plan-docs` — the
retirement prompt does not re-run the gates over what it finds, and would only be trading one
unverified reading for another if it did.
