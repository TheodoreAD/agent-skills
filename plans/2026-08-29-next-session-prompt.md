---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` should end by writing the next session's opening prompt

## Context

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

### What it would have had to carry, from the session that asked for it

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

## Open questions

[NEEDS CLARIFICATION: does the prompt assert state or name the checks that re-derive it? Asserting
is what makes it useful — "push `103b0b6`, then absorb the incoming plan" is actionable in a way
"run `git status`" is not. Naming checks is what makes it survive a week on the shelf. The likely
answer is both, split visibly: a short "here is what was true at <timestamp>" block that the reader
is told to re-verify, and the commands to do it with. But an unread caveat is not a safeguard, so
the split has to be structural rather than a sentence of hedging.]

[NEEDS CLARIFICATION: where does it live, and what makes the next session read it? The user works
only through prompts, so the minimum viable form is a pasteable block at the end of the report — but
that dies with the terminal scrollback, which is the problem being solved. A file needs something
pointing at it: `~/AGENTS.md` (loaded every session, but this is repo-specific and would cost every
unrelated session), the repo's own `AGENTS.md` (right scope, wrong content — that file is
instructions, and `plan-docs` explicitly forbids status narrative in it), or the store (routed, but
nothing reads it at session start except `absorb`). `absorb` already being the once-per-session call
makes it the obvious carrier, which is the same conclusion
`2026-08-29-retirement-prompt-on-the-session-sweep.md` reached for a different feature — worth
deciding those two together rather than bolting both onto the same command independently.]

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

## Recommended direction

Rough, and the questions above come first.

1. **Structure it as verify-then-act, not as a list of facts.** Each item pairs the command that
   re-derives its state with the action to take if it still holds. That makes staleness visible at
   read time instead of invisible.
2. **Timestamp it, and let the reader see the age**, so a prompt from last week is obviously one to
   re-derive rather than one to trust.
3. **Cap it hard — three to five items.** "The most likely and immediate things" is the request; a
   prompt that lists everything is the harvest report again, and the harvest report is already not
   being carried forward.
4. **Carry only what a cold start cannot re-derive.** An unpushed commit shows up in `git status`; a
   _deliberately deferred_ cross-repo sweep does not, and neither does the reason it was deferred.
   Prefer the second kind.
5. **Decide the carrier together with the retirement prompt**, since both point at `absorb` and two
   independent additions to one command is how a single surface acquires two half-designs.

[DEFERRED: the failure this feature addresses has a cheaper partial fix that should be priced first
— the harvest already knows which items are urgent, and simply _writing them into the plan that owns
each one_ costs nothing extra and is already the skill's routing rule. The genuine residue is the
items belonging to no plan, which may be a much smaller set than the request assumes. Worth counting
on the next few harvests before building anything.]
