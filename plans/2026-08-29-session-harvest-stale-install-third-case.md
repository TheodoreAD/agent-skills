---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` step 0: the third case, and why this fix is filed rather than made

**Duplicate, discovered seconds after this was committed.** A parallel session filed
`2026-08-29-session-harvest-step-0-misreads-uncommitted-work.md` for the same finding, from a
different repo, on the same day — its version is the fuller one, with a three-case table and a
companion plan about the sweep. Fold this file into that one on absorption and delete it; the only
part not obviously covered there is the last section below, on why the fix could not be made in
place.

The collision is itself evidence for the finding: two sessions hit the same gap within hours, and
neither could see the other's work until one of them wrote to the store.

## Context

Step 0 tells a harvest to diff each installed skill against its checkout and, on a difference, "say
so and offer to re-install first". It assumes one cause: the installed copy is stale and the
checkout is the truth.

A harvest on 2026-08-29 hit a third case the step does not describe. `plan-docs` differed — but the
checkout was **dirty**, carrying 672 uncommitted insertions across `skills/plan-docs/`,
`tests/unit/test_plan_store.py` and `README.md` from a parallel session mid-implementation. Nothing
was ahead of `origin/main`, so the difference was entirely unpushed work in progress.

Offering a re-install there is wrong in a way that reads as right: the installer clones from the
**remote**, so it would deploy the last pushed version — which is what is already installed. The
offer costs a round trip and delivers nothing, and accepting it would look like the problem was
handled.

The correct action is neither "proceed" nor "re-install": report the difference, say it is another
session's unpushed work rather than a stale install, and carry on using the installed copy after
confirming the commands actually used are unaffected by the diff. In this run they were — `tags`,
`set-status` and `scan` predate the change, which was about splitting the store into two tiers by
sensitivity.

## Recommended direction

One additive paragraph under step 0, roughly:

> A difference has three causes, not one. Check `git -C <checkout> status --short` and
> `git log origin/<branch>..HEAD` before offering anything: a **clean checkout ahead of the
> install** is the stale install the step assumes, and a re-install fixes it. A **dirty checkout**
> is unpushed work in progress — very likely a parallel session's — and a re-install would fetch the
> last pushed version, which is what is already installed; report it as in-flight rather than stale,
> confirm the commands this run needs are not in the diff, and use the installed copy. Confirmed
> 2026-08-29 on `plan-docs`, mid-store-split.

[NEEDS CLARIFICATION: Whether "confirm the commands this run needs are not in the diff" is worth
spelling out as a mechanical check, or stays a judgment call. It was cheap here because the diff was
one coherent feature; it would not be on a diff touching argument parsing broadly.]

## Why this is filed rather than edited in place

Step 6 says to default to editing the skill source now, because a deferred skill fix is one that
does not happen. That default collided with the finding itself: `agent-skills` is the repo with the
parallel session in it, and its quality gate auto-formats the whole tree — so running it, as every
commit into that repo is required to, would have rewritten five files another session is actively
editing.

Filing through `plans.py new --for` is the mechanism that exists for exactly this and is not the old
defer-and-hope: it writes outside every working tree, touches nothing, and the next session working
in `agent-skills` is offered it. Worth noting in step 6 alongside the "edit now" default, so the
next harvest does not have to re-derive the exception — the gate, not the file, is what makes a
same-repo edit unsafe while another session is live.
