---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` tells itself to commit into a repo the session is not in

## Context

Filed from a `power-user-linux-setup` session, 2026-08-30, rather than edited in directly — which is
the whole point of the plan below.

The user's instruction that produced this, given when a harvest asked whether to push a skill fix it
had already committed here:

> we don't act on other repos any more, unless we have some very complex work that needs back and
> forth. that should be in the skills and/or agents.md already. if something needs adjusing in
> another repo, make a plan.

`session-harvest`'s steps 6–7 and its "Self-update mechanics" section instruct the opposite, in
detail and by name: locate `agent-skills`, edit `skills/session-harvest/SKILL.md`, run that repo's
gate, and **"commit — locally, without asking, per step 7"**. Every harvest run in any repo is
therefore told to make a commit in a repo its session does not belong to, on the reasoning that "a
deferred skill fix is a skill fix that does not happen".

That reasoning was sound when it was written and is now obsolete: `plan-docs` grew
`plans.py new <topic> --for <repo>`, which writes into that repo's store mirror **outside every
working tree**, so nothing crosses and the next session in the owning repo is offered it by
`absorb`. The fix is no longer deferred — it is delivered, just not as a commit. `session-harvest`'s
own routing filters already say exactly this for _candidates_ ("A candidate belonging to another
repo is _filed_ there, not queued here"); the self-update mechanics were never brought in line with
the rule the same document states two sections earlier.

The inconsistency is invisible from inside a run: the self-update section reads as the authoritative
instruction for skill fixes, and following it feels like compliance.

## What this run already did, and what it costs

Before the instruction arrived, this session followed the section as written: commit `abb9903` on
`agent-skills`' `main`, unpushed, gate green. Its content is the second item below. Whether that
commit stays or is dropped in favour of this plan is the user's call — noted here so a session
absorbing this plan does not rediscover a mystery commit.

## Two changes, one small and one structural

1. **The `depends_on` bullet in step 5 over-reports readiness.** It was written for work _parked_
   because a repo was mid-restructure, and says to report a plan ready once the named repo's tree is
   clean. But `plan-docs` documents a different meaning for the same tag — "sibling repos this plan
   can't fully land without" — and for that kind an idle repo proves nothing, because the blocker is
   a change that repo has not made. Applied literally on 2026-08-29 it would have announced seven
   plans ready: eight tagged plans in one repo, three sibling repos all clean, exactly **one** of
   the eight queue-shaped. The bullet should say to sort the tagged plans into the two kinds and
   report readiness only for the first. (This is what `abb9903` contains.)

2. **The self-update mechanics should route through `new --for`, not through a commit.** A harvest
   that finds a skill defect writes a plan into the skill repo's store mirror, commits it _in the
   store_, and reports it — leaving the owning repo untouched. That keeps step 6's real requirement
   ("default to fixing now, not filing it for later") while satisfying the one-session-one-repo
   rule, because filing to the store _is_ acting now.

## Open questions

[NEEDS CLARIFICATION: what happens to the "very complex work that needs back and forth" exception
the user named? A multi-step skill redesign genuinely wants a session in `agent-skills`, not a
relayed plan. Probably: the harvest never does it inline, and instead files the plan and says
plainly that this one wants its own session there. Worth stating in the skill rather than left to
judgment, since every skill fix will feel like it qualifies.]

[NEEDS CLARIFICATION: does the same correction apply to `plan-docs`' and other skills' self-update
guidance, or is `session-harvest` the only one that instructs a cross-repo commit? One grep across
the skills answers it, and doing them in one pass is cheaper than one at a time.]

[NEEDS CLARIFICATION: where does the rule itself belong — restated in each skill, or once in
`~/AGENTS.md` with the skills deferring to it? The user's phrasing ("that should be in the skills
and/or agents.md already") leaves it open. `~/AGENTS.md`'s "Running a command against a different
repo than the session's project" already says substantial cross-repo work belongs in its own
session; what it does not say is that a _commit_ in another repo is out regardless of size, which is
the part every skill's self-update section walked past.]

## Recommended direction

Do 2 before 1 — the structural fix is what stops the next harvest re-creating the same problem, and
1 is a two-line edit that rides along. Both are single-file edits to
`skills/session-harvest/SKILL.md`, plus whatever the second open question turns up.
