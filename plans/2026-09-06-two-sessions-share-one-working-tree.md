---
status: idea
updated: 2026-09-06
---

# Two sessions in one working tree, which no filing convention can fix

## Context

Inherited 2026-09-06 from `2026-08-29-external-contributions.md` when that plan was retired. That
plan designed cross-repo filing — `new --for`, `absorb`, the anchored guard — and scoped one thing
out of itself:

> [DEFERRED: none of this addresses two sessions working the **same** repo, which shares one working
> tree on this machine and is the harder half of "who committed what when". Filing conventions
> cannot fix concurrent edits to the same tree. Worth its own plan if the pain persists after
> cross-repo commits stop.]

**The condition it set is met.** Cross-repo commits have stopped — the guard refuses them and
`~/AGENTS.md` now states the prohibition outright — and the same-tree pain has not. It is now the
_only_ remaining half of the user's original complaint: _"I need to stop sessions and always worry
about who committed what when."_

## The pain has persisted, measured on one evening

Every one of these is from the single session of 2026-09-06 that retired the parent plan, which was
not looking for them:

- **A commit landed in the shared tree mid-session, from a session working elsewhere.** `4345dce` at
  23:44:21, between two `skills-state` calls ninety seconds apart — which inverted that check's
  verdict and its remedy, recorded in `2026-09-03-two-plans-one-subject-absorb-cannot-pair.md`.
- **A plan was filed for this repo at 23:50**, after this session's own `absorb` had reported one
  waiting and before its next command, so the count it had just read was already wrong.
- **The plans store held three deletions belonging to another session's absorption** at the moment
  this one committed its own two. Nothing distinguished them from this session's work except knowing
  which files it had touched.
- **Two commits sat at the base of `main` that this session did not make**, so its own push would
  have published them.

None of that is a defect in any tool. Each is the ordinary consequence of two sessions sharing one
checkout, and each was survivable only because a rule already existed for it — commit by pathspec,
undo by SHA, `plans.py commit`'s private index, `git log origin/<branch>..HEAD` before pushing.

## What the existing answers cover, and what they do not

**Covered, and by now well covered.** `~/AGENTS.md`'s "Unexplained git/file state in a working tree"
carries the behavioural half: stage by path and never `git add -A`, undo by SHA rather than a
relative ref, check the ahead-range before pushing, and the sharpest one — a local commit is not a
private holding state, because any other session's push carries it. `plan-docs` adds the store's
private-index `commit` and the dirty-store fallback of adding a new file rather than editing a held
one.

**Not covered: everything is a rule an agent must remember, and there is no signal.** The store's
dirty check is one call away from being wrong the moment another session writes, and this session
watched exactly that happen twice. Nothing tells a session that a file it is about to edit is open
in another session, that the commit it is about to make sits on top of somebody else's, or that the
tree changed under it since its last read. The harness's own file-changed-on-disk notices are the
closest thing that exists, and they fire after the fact.

## Open questions

[NEEDS CLARIFICATION: **is there anything to build, or is this correctly a rules-only problem?** The
parent plan's own conclusion was that filing conventions cannot fix concurrent edits, and that may
generalise: a lock is refused elsewhere in this corpus for a directory several independent agents
write to, and the same argument applies to a checkout. The honest answer may be that the rules are
the mechanism and what is missing is only that nothing _measures_ whether they are followed.]

[NEEDS CLARIFICATION: **would a cheap read-time signal help, or only add noise?** The shapes
available are all approximations — a `git status` diffed against the session's last one, a check
that `HEAD` has not moved since a file was read, a warning when the ahead-range contains a commit
this session did not author. The last is the most precise and the easiest: a session knows which
SHAs it created. Against: a session that reads its own commits from `git log` cannot distinguish
them from a parallel session's by content, so this needs the session to record what it committed,
which is state.]

[NEEDS CLARIFICATION: **whether `session-harvest`'s sweep should report it at all.** It already
reports the ahead-count and already had a false positive from exactly this cause
(`2026-09-02-correction-overlap-attributes-parallel-sessions.md`, where `published this session`
meant "published by anybody today"). That plan is the evidence that a naive parallel-session signal
misattributes; it is also evidence the data is right there. Decide that plan first — this one may
turn out to be its general case rather than a separate build.]

## Recommended direction

Do nothing mechanical yet. Resolve `2026-09-02-correction-overlap-attributes-parallel-sessions.md`
first, since it is the same question with a concrete instrument attached and a measured false
positive to test against. If its fix needs a session to know which commits are its own, that is the
primitive this plan wants, and the two should land together rather than as two designs for one fact.
