---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `plan-docs` forbids writing a plan into another repo, but not writing _anything_ else

## Context

Stated by the user 2026-08-29, when a `repo-tasks` session offered to edit
`power-user-linux-setup`'s `~/AGENTS.md` fragment directly:

> this should be something plan-docs clears up, we never write to another repo unless it's a very
> complex process that requires a lot of back and forth to fix. this should be one or more plans
> that go to the central plan store for any repo that is not the current one

The skill already enforces exactly half of this, and enforces it well. "Something that belongs to a
repo you are not in" forbids writing a _plan file_ into another repo's working tree, `new` refuses
and names `--for`, and the session-anchor tiers exist because cwd cannot be trusted. What none of
that covers is the far more common case: the session is not filing a plan at all, it is about to
make an ordinary _edit_ — a config fragment, a doc, a source file — in a repo it does not belong to.

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

[NEEDS CLARIFICATION: where does this rule live — `plan-docs`, or `~/AGENTS.md`? The user said
"plan-docs should clear this up", which is a clear answer for the _mechanism_ half. But the rule
fires when no plan is being written, which is when the skill is least likely to have loaded, and
`~/AGENTS.md` already carries a "Running a command against a different repo than the session's
project" rule that this sits directly beside. Possibly both: the always-loaded file states "file it,
don't do it" and points at the skill for how.]

[NEEDS CLARIFICATION: does the rule cover _reading_ another repo? Reading is how a plan filed for
that repo gets written accurately, and the existing rules already treat read-only cross-repo verbs
as fine. Worth stating so nobody over-applies the prohibition and files a plan describing a change
they never verified was needed.]

[NEEDS CLARIFICATION: how does this interact with a repo that has no live session and obviously
never will — a scratch clone, a vendor checkout? The rule reads as absolute, which is probably right
(the cost of the rule having exceptions is that every session re-litigates whether this one
qualifies), but it has not been stated either way.]

## Recommended direction

1. Widen the "Something that belongs to a repo you are not in" section from plan files to work in
   general, keeping the existing plan-file enforcement as the concrete mechanism.
2. Quote the escape hatch rather than restating it, so it stays narrow.
3. Consider a one-line pointer from `~/AGENTS.md`'s cross-repo rule, since that is the one loaded on
   every turn.

## `session-harvest` states the same thing, but as an exception

`plans/2026-08-29-session-harvest-stale-install-third-case.md` closes with "Why this is filed rather
than edited in place", and reaches the same mechanism from the other end — a harvest that wanted to
edit `agent-skills` directly, and filed instead. But it justifies filing as an _exception_, on two
contingent facts: a parallel session was live in that repo, and that repo's gate auto-formats the
whole tree, so committing would have rewritten files someone else was editing.

Both facts are true and neither is the reason. Under the rule as the user states it, filing is the
**default**, and it does not depend on whether a session happens to be live there — a repo with no
live session today has one tomorrow, and a rule that requires checking first is a rule every session
re-litigates.

So `session-harvest`'s step 6, which currently opens "Default to editing the source now, not filing
it for later; a deferred skill fix is a skill fix that does not happen", needs the same inversion:
filing through `plans.py new --for` **is** the immediate action, not the deferral it warns against.
The warning it carries is still right about defer-and-hope; it just no longer describes filing.

[DECISION: change the default rather than adding a condition to it. A conditional default is one
each session evaluates differently, which is how this session ended up proposing to edit two files
in another repo an hour after correctly filing a plan for a third.]

## Worked example, if one is wanted

Five plans were filed to the store from a single `repo-tasks` session on 2026-08-29 rather than
edited into their repos: this one, `power-user-linux-setup`'s
`2026-08-29-python-floor-rule-in-the-global-agents-md.md`, `ingesta`'s
`2026-08-29-python-floor-tiers-settled.md`, and two more for this repo —
`2026-08-29-plans-store-sweep-no-remote-premise-is-stale.md` and
`2026-08-29-session-harvest-step-0-cannot-see-a-stale-loaded-copy.md`. The last two are corrections
to plans this repo had already absorbed, which is the shape the rule handles worst if it is
optional: the session that finds the error is never the session that owns the file.
