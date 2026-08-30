---
status: landed
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` step 5 flattens "this correction fixes something already public"

## Context

Found by running the skill, 2026-08-30, from a `power-user-linux-setup` session. Filed rather than
edited directly per `~/AGENTS.md`'s cross-repo write rule; the contradiction between that rule and
this skill's steps 6–7 is already carried by
`2026-08-30-skill-install-command-and-cross-repo-write-rule.md` and is not re-raised here.

The session's shape, which is what produced the gap:

1. Added a package to `setup.toml` with a description arguing why it exists, and **pushed** it.
2. An hour later, absorbing plans filed by a parallel session, learned the argument was false — the
   client cannot do the thing the description said it was for, established from the client's own
   source and five failed attempts.
3. Committed the corrected description. Did not push, because the user had said not to.

So the repo's remote currently serves a justification known to be wrong, and the fix is sitting in
an unpushed commit.

## The gap

Step 5's git bullet is thorough about _whether_ there are unpushed commits, whose they are, and
whether the ahead-count was computed against a stale ref. It treats them as one kind of thing: work
not yet delivered.

**It has no notion of a commit whose subject is already published and now known to be wrong.** That
one is not deferred work — it is a live inaccuracy with a reader. Reported flat, it reads as "4
unpushed commits, push when convenient", and the one that matters is indistinguishable from three
plan updates.

[PITFALL: the flattening is worse when the correction is _small_. The wrong claim here was two
sentences inside a package description, so its commit looks like ordinary tidying next to commits
that add sections and merge plans. Size of diff is uncorrelated with whether something false is
being served, and an ahead-count sorts by neither.]

[PITFALL: this only arises because the session pushed mid-run rather than at the end, which is
normal and not the problem. Any harvest of a session that published anything before it finished
learning has the same exposure, and the window between the push and the correction is exactly when a
harvest is most likely to be invoked.]

## Recommended direction

Add one clause to step 5's git bullet, not a new bullet — the check is already looking at the
unpushed set, and this is a question to ask about each entry rather than a separate sweep.

Suggested shape: after naming which unpushed commits are this session's, ask whether any of them
**corrects something the session already pushed**. If so, it is not an ordinary unpushed commit and
does not belong in the same sentence: name it in "Needs action now" with what the remote currently
claims and for how long, so the user is deciding about a live inaccuracy rather than about a
backlog.

The signal is cheap and mechanical — a commit touching a path that an earlier commit _in the same
session_ already pushed:

```shell
git log origin/<branch>..HEAD --name-only --format='%h'      # paths in the unpushed set
git log <session-start-sha>..origin/<branch> --name-only     # paths this session already published
```

An overlap is not proof of a correction, but it is a short list to read, and it is empty for most
sessions.

[NEEDS CLARIFICATION: whether this should also fire when the _earlier_ session published the wrong
claim and this one is only fixing it. The overlap check above would not catch that — there is no
push by this session to intersect with. Arguably a different and much harder question ("is anything
this repo currently publishes known-wrong?"), which no harvest can answer in bounded time, so the
narrow same-session version may be the whole of what is worth building.]

[DECISION: neither refinement was built, and the clause ships narrow. "Published and wrong" versus
"published and now merely incomplete" is a judgement the agent makes while reading the short overlap
list, not a distinction the check can draw — and the clause names one signal rather than a category,
so it has nothing to overfire on. The other-session case is excluded by the same reasoning the plan
already gives: it has no push to intersect with, and the general question behind it is unbounded.]

## Migrated to

- **`skills/session-harvest/SKILL.md`, step 5's git bullet** — one clause after the "check who wrote
  the unpushed commits" rule, with the two-`git log` overlap signal, the instruction to name it in
  "needs action now" with what the remote currently claims, and the boundary that keeps it to the
  same-session case.

Deliberately not migrated: the session's own narrative (which package, which description). The shape
is what generalises, and the specifics belong to a repo this one does not name.
