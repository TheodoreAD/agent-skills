---
status: idea
updated: 2026-09-10
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
  verdict and its remedy. Fixed 2026-09-09: `session-harvest` step 0 now says the verdict is a
  reading rather than a fact, and carries the ninety-second interval precisely so it is not read as
  a long-interval precaution.
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

[DECISION: **rules-only, and the measurement now exists to say so.** Three of the four became
`session-bash-audit` rows on 2026-09-10 and the first corpus run — 14 days, **26,319 calls** — reads
`git-add-all` 81, `git-undo-relative` **1**, `store-write-by-git` 174. The undo rule is holding
almost perfectly, and its single hit is `git -C ~/plans reset --soft HEAD~1`: a relative-ref reset
in the one directory several sessions write to at once, which is the rule's own worst case. So the
answer to this question is yes, rules-only — and what was missing really was only that nothing
measured them.]

[NEEDS CLARIFICATION: **would a cheap read-time signal help, or only add noise?** The shapes
available are all approximations — a `git status` diffed against the session's last one, a check
that `HEAD` has not moved since a file was read, a warning when the ahead-range contains a commit
this session did not author. The last is the most precise and the easiest: a session knows which
SHAs it created. Against: a session that reads its own commits from `git log` cannot distinguish
them from a parallel session's by content, so this needs the session to record what it committed,
which is state.]

[NEEDS CLARIFICATION: **whether `session-harvest`'s sweep should report it at all.** It already
reports the ahead-count and already had a false positive from exactly this cause — the
correction-overlap plan, retired 2026-09-08 and readable through `plans.py archive`, where
`published this session` meant "published by anybody today". That plan is the evidence that a naive
parallel-session signal misattributes; it is also evidence the data is right there.]

## What the correction-overlap plan answered, 2026-09-08

That plan is now landed and retired, and this one was waiting on it, so the answer belongs here
rather than in a history nobody will think to read.

**It needed no shared primitive, and that is the finding.** This plan's direction was that if the
fix required a session to know which of the commits in front of it are its own, that primitive
should land once and serve both. It did not. Four sweep checks made the same mistake — a time window
read as an attribution — and **every repair was per-site, with a different evidence source each
time**: the transcript's write paths for the correction check, "did this session run `docker` at
all" for the disk step, the session's own `library.py` argv for the research store, and argv plus an
ordering test for store commits. The one thing closest to a shared helper, `_named_before`, arrived
from the store-commit fix and carries an ordering constraint the write-path route never needed.

**And the fourth site could not be finished by attribution at all.** What survives every filter
there is a set that honestly contains most of a long session's files, so the repair was the label:
the line now reports commits on both sides of a push rather than claiming a correction. A check
whose label its evidence cannot support has two repairs, and only one of them is always available.

So the general-case build this plan was holding out for does not exist in the shape it expected.
What the four cases share is a reading habit, not a mechanism.

## Recommended direction

**Rules-only, and the open question is now whether anything measures adherence to them.** The
per-site outcome above is the argument the parent plan already made from the other end — filing
conventions cannot fix concurrent edits, and neither can one attribution helper. Every survival on
the measured evening came from a rule an agent remembered: commit by pathspec, undo by SHA,
`plans.py commit`'s private index, `git log origin/<branch>..HEAD` before pushing.

That leaves one thing worth building and it is not a signal. `session-bash-audit` already measures
whether this machine's Bash rules are followed, and **none of the four is in its pattern set** —
checked 2026-09-08 against `PATTERNS` in `audit.py`: no row matches `git add -A`, a relative-ref
`reset`, an `origin/<branch>..HEAD` read before a push, or a `git -C <store> commit` where
`plans.py commit` was owed. The nearest are `git-mutating` and `git-C-mutating`, which ask whether a
verb was ask-gated rather than whether it was safe here. Each of the four has the shape the audit
measures well — a literal command form, present or absent in a transcript — so measuring them would
say whether the rules-only answer is holding, which is the question this plan has actually been
asking since the condition it inherited was met.

[PITFALL: `git-mutating` fires on `git add` and `git commit` alike, so a run of it is not evidence
about pathspec discipline in either direction. A rate read off that row would say the rules are
being followed while `git add -A` sat inside it uncounted.]

Still open, and unaffected: whether a cheap read-time signal would help or only add noise. Prefer
measurement first — a signal built before anyone knows the rules are being missed is a guess with a
maintenance cost.

## What the measurement said, 2026-09-10

The rows landed and the numbers argue against building anything. `git-undo-relative` at **1 hit in
26,319 calls** is a rule being followed, and a read-time signal for it would fire never and be
trusted anyway. `git-add-all` at 81 is the one with room, and the fix for it is the rule that
already exists rather than a warning: name the paths.

**`store-write-by-git` at 174 turned out not to be about this plan at all**, and that is the useful
part. Reading the samples — which the row's own instruction demands — a large share are
`git -C <store> add <paths>` immediately followed by `plans.py scan --mode staged`: a session
obeying the scan-before-you-commit rule, which needs something staged, with a command that
deliberately does its own staging through a private index. **Two `plan-docs` rules pull against each
other**, and that is where the number belongs, not here.

[NEEDS CLARIFICATION: what should a session do to satisfy both? `scan --mode staged` needs an index
and `plans.py commit` refuses to depend on one, which is the whole point of the private index. A
`--mode` that scans named paths without staging them would resolve it, and so would `commit` running
the scan itself; the second is the one that removes the decision rather than moving it. Filed here
because this plan's measurement found it, but it is `plan-docs` work and wants its own file if it
grows.]
