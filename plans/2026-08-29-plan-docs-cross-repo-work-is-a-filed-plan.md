---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Work that belongs to another repo is filed as a plan, not performed

Merged 2026-08-30 with `2026-08-30-session-harvest-self-update-crosses-repos.md`. One rule, two
skills that contradict it: `plan-docs` states it about plan files only, and `session-harvest`'s
self-update mechanics instruct the opposite outright.

## Context

Stated by the user 2026-08-29, when a `repo-tasks` session offered to edit
`power-user-linux-setup`'s `~/AGENTS.md` fragment directly:

> this should be something plan-docs clears up, we never write to another repo unless it's a very
> complex process that requires a lot of back and forth to fix. this should be one or more plans
> that go to the central plan store for any repo that is not the current one

And again 2026-08-30, to a harvest asking whether to push a skill fix it had already committed in
`agent-skills` from a `power-user-linux-setup` session:

> we don't act on other repos any more, unless we have some very complex work that needs back and
> forth. that should be in the skills and/or agents.md already. if something needs adjusing in
> another repo, make a plan.

### `plan-docs` enforces half of it

"Something that belongs to a repo you are not in" forbids writing a _plan file_ into another repo's
working tree, `new` refuses and names `--for`, and the session-anchor tiers exist because cwd cannot
be trusted. What none of that covers is the far more common case: the session is not filing a plan
at all, it is about to make an ordinary _edit_ — a config fragment, a doc, a source file — in a repo
it does not belong to.

The reasoning transfers unchanged. Parallel sessions on this machine share one working tree, so an
edit appearing in another repo under a session already working there is the same failure the
plan-file rule exists to prevent. It is arguably worse: a stray plan file is inert and obvious,
while an edit to a file that repo's session is holding is a real conflict, and the commit that
carries it is one nobody in that repo asked for.

[PITFALL: the gap is not that the rule is missing — it is that the rule is stated as being about
plan files, so a session reading it concludes it has complied by using `--for`, and then edits that
repo's source anyway. Confirmed live 2026-08-29: a `repo-tasks` session, having just used `--for`
correctly for one thing, proposed as its recommended option to edit two files in
`power-user-linux-setup` and run that repo's deploy task. The skill it had loaded did not say no,
because the thing being written was not a plan.]

### `session-harvest` instructs the opposite, by name

Steps 6–7 and the "Self-update mechanics" section tell every harvest, in any repo, to locate
`agent-skills`, edit `skills/session-harvest/SKILL.md`, run that repo's gate, and **"commit —
locally, without asking, per step 7"**. The reasoning offered is that "a deferred skill fix is a
skill fix that does not happen".

That reasoning was sound when it was written and is now obsolete:
`plans.py new <topic> --for
<repo>` writes into that repo's store mirror **outside every working
tree**, so nothing crosses and the next session in the owning repo is offered it by `absorb`. The
fix is no longer deferred — it is delivered, just not as a commit. The skill's own routing filters
already say exactly this for _candidates_ ("A candidate belonging to another repo is _filed_ there,
not queued here"); the self-update mechanics were never brought in line with the rule the same
document states two sections earlier. The inconsistency is invisible from inside a run: the
self-update section reads as the authoritative instruction for skill fixes, and following it feels
like compliance.

`plans/2026-08-29-session-harvest-step-0-misreads-uncommitted-work.md` reaches the same mechanism
from the other end — a harvest that wanted to edit `agent-skills` directly and filed instead — but
justified filing as an **exception**, on two contingent facts: a parallel session was live in that
repo, and that repo's gate auto-formats the whole tree, so committing would have rewritten files
someone else was editing. Both facts are true and neither is the reason. Under the rule as the user
states it, filing is the **default**, and it does not depend on whether a session happens to be live
there — a repo with no live session today has one tomorrow, and a rule that requires checking first
is a rule every session re-litigates.

[DECISION: change the default rather than adding a condition to it. A conditional default is one
each session evaluates differently, which is how a session ended up proposing to edit two files in
another repo an hour after correctly filing a plan for a third.]

## What the rule should say

Roughly: **work that belongs to another repo is filed as a plan for that repo, not performed.**
`plans.py new <topic> --for <repo>` is the mechanism that already exists; the plan describes the
change in enough detail that a session inside that repo can execute it, and that session absorbs it
on its own schedule.

The escape hatch the user named is narrow and worth quoting rather than paraphrasing: "unless it's a
very complex process that requires a lot of back and forth to fix". That is not "unless it is small"
— a one-line fragment edit is exactly the case that felt too small to file and is not. It is about a
change that cannot be described faster than it can be done jointly.

## Open questions

[NEEDS CLARIFICATION: where does this rule live — `plan-docs`, `session-harvest`, or `~/AGENTS.md`?
The user said "plan-docs should clear this up", which answers the _mechanism_ half. But the rule
fires when no plan is being written, which is when the skill is least likely to have loaded, and
`~/AGENTS.md`'s "Running a command against a different repo than the session's project" already says
substantial cross-repo work belongs in its own session — what it does not say is that a _commit_ in
another repo is out regardless of size, which is the part every skill's self-update section walked
past. Possibly all three: the always-loaded file states "file it, don't do it" and the skills defer
to it.]

[NEEDS CLARIFICATION: is `session-harvest` the only skill instructing a cross-repo commit? One grep
across the skills answers it, and doing them in one pass is cheaper than one at a time.]

[NEEDS CLARIFICATION: what happens to the "very complex work that needs back and forth" exception
inside a harvest? A multi-step skill redesign genuinely wants a session in `agent-skills`, not a
relayed plan. Probably: the harvest never does it inline, files the plan, and says plainly that this
one wants its own session there. Worth stating in the skill rather than left to judgment, since
every skill fix will feel like it qualifies.]

[NEEDS CLARIFICATION: does the rule cover _reading_ another repo? Reading is how a plan filed for
that repo gets written accurately, and the existing rules already treat read-only cross-repo verbs
as fine. Worth stating so nobody over-applies the prohibition and files a plan describing a change
they never verified was needed.]

[NEEDS CLARIFICATION: how does this interact with a repo that has no live session and obviously
never will — a scratch clone, a vendor checkout? The rule reads as absolute, which is probably right
(the cost of exceptions is that every session re-litigates whether this one qualifies), but it has
not been stated either way.]

## Recommended direction

1. **Route `session-harvest`'s self-update mechanics through `new --for`, not through a commit.** A
   harvest that finds a skill defect writes a plan into the skill repo's store mirror, commits it
   _in the store_, and reports it — leaving the owning repo untouched. That keeps step 6's real
   requirement ("default to fixing now, not filing it for later") while satisfying the
   one-session-one-repo rule, because filing to the store _is_ acting now. Step 6's opening —
   "Default to editing the source now, not filing it for later; a deferred skill fix is a skill fix
   that does not happen" — needs the same inversion: its warning is still right about
   defer-and-hope, it just no longer describes filing.
2. **Widen `plan-docs`' "Something that belongs to a repo you are not in" from plan files to work in
   general**, keeping the existing plan-file enforcement as the concrete mechanism, and quote the
   escape hatch rather than restating it so it stays narrow.
3. **Consider a one-line pointer from `~/AGENTS.md`'s cross-repo rule**, since that is the one
   loaded on every turn.

Do 1 before 2 — the structural fix is what stops the next harvest re-creating the problem.

**Landed already**, from the merged plan and kept so nobody re-opens it: `abb9903` fixed step 5's
`depends_on` bullet, which reported a plan ready once the named repo's tree was clean. `plan-docs`
documents a second meaning for the same tag — "sibling repos this plan can't fully land without" —
for which an idle repo proves nothing, because the blocker is a change that repo has not made.
Applied literally on 2026-08-29 it would have announced seven plans ready when exactly one was. That
commit was made in this repo from a `power-user-linux-setup` session, which is the thing this plan
says not to do; it is kept rather than reverted, and noted here so a later session does not
rediscover it as a mystery commit.

## Worked example, if one is wanted

Five plans were filed to the store from a single `repo-tasks` session on 2026-08-29 rather than
edited into their repos: this one, `power-user-linux-setup`'s
`2026-08-29-python-floor-rule-in-the-global-agents-md.md`, `ingesta`'s
`2026-08-29-python-floor-tiers-settled.md`, and two more for this repo —
`2026-08-29-plans-store-sweep-no-remote-premise-is-stale.md` and
`2026-08-29-session-harvest-step-0-cannot-see-a-stale-loaded-copy.md`. The last two are corrections
to plans this repo had already absorbed, which is the shape the rule handles worst if it is
optional: the session that finds the error is never the session that owns the file. All five were
absorbed by the owning repos' own sessions, unprompted, within a day.
