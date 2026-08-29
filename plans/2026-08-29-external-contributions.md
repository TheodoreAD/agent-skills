---
status: idea
updated: 2026-08-29
---

## Context

Raised by the user 2026-08-29, from lived pain rather than from design: _"today I need to stop
sessions and always worry about who committed what when and who is about to commit cross-repo, and
we should arrive at a situation where cross repo work almost never happens, and everything is
captured in plans/tasks."_

The trigger was concrete. A session working in `agent-skills` found a problem belonging to
`power-user-linux-setup`. The only way to record it against that repo was to write and commit a file
into that repo's working tree — from a session that had no business being there, possibly while
another session was working in it, on a machine where parallel sessions **share one working tree**.
That is the whole failure: a foreign commit appearing under someone else's feet.

The user's proposal: treat these as **external contributions**, filed outside the target repo, and
use the distinction to separate _the project's own roadmap_ from _bugs and feature requests arising
from using the thing_. Open question raised at the same time: does this want frontmatter?

## What already works, which is more than expected

Before designing anything, the honest inventory — three of the four mechanics exist:

- **Writing a plan about repo B without touching repo B.** `new <topic> --to store --path <B>` puts
  it in `$PLANS_HOME/<B's path>`, outside every working tree. Exercised live 2026-08-29 to file the
  `Claude-Session` trailer note against `power-user-linux-setup` from an `agent-skills` session: no
  file in that repo changed, no commit landed in it.
- **Repo B's own session seeing it.** `list --scope repo` reads the repo's `plans/`, its store
  mirror _and_ the unscoped area regardless of route, as of 2026-08-29. So a contribution filed from
  outside is visible to the session that owns the repo, with no commit having crossed.
- **Cross-repo awareness without cross-repo commits.** `list --scope family` and the `depends_on` →
  "waiting on this repo" view already answer "what is pending on me from elsewhere".

So the transport is built. What is missing is **a defined hand-off, and a rule that stops the
foreign commit happening at all.**

## What is actually missing

1. **`--to store --path <other repo>` is an override, not an expression of intent.** It happens to
   do the right thing. A first-class `new <topic> --for <repo>` would say what is meant, so no agent
   has to know the trick.
2. **Nothing drains the store back into the repo that owns the work.** A plan filed for a
   repo-routed repo sits in the mirror indefinitely; nothing tells the session working in that repo
   that it is there, and nothing moves it in.
3. **Nothing stops or warns about the foreign commit.** The whole problem is available by default —
   an agent that writes into another repo's `plans/` gets no resistance from any tool.

Two items that were here have been struck. An "accept path" turned out not to be missing: accepting
is promoting the plan's status, which already exists and already gates. And a provenance marker
turned out not to be wanted — see below.

## The design question, stated precisely

The rest was settled with the user the same day. One question is still open, at the end.

[DECISION: **no `origin:` field, and no provenance axis at all — this is a single-user system.**
Reversed by the user 2026-08-29, a few hours after it was settled the other way in this same file.
The reversal is the right call and the earlier decision was designed for a situation that does not
exist.

`origin:` existed to mark a contribution as "raised by somebody else, triage it before an agent acts
on it". On this machine there is one person filing plans, no connection to an external work tracker,
and no mirroring. So every plan is the user's own and validated by construction; the field would be
written by convention and read by nothing, which is the exact "half-tagged is worse than untagged"
failure this convention warns about elsewhere.

**The distinction is deferred, not rejected.** When mirroring or an external tracker arrives, the
question comes back in its real form — how to separate ideas the user validated by having them from
ideas that arrive needing triage before agents treat them as actionable. That is the moment to
design it, with the actual inbound shape in hand.]

[DECISION: **route plus location already says everything a marker would have, so nothing is lost.**
A plan in `<store>/<repo>/` where that repo is routed `repo` is by definition awaiting absorption —
that repo's own route says its plans belong in its tree, so a file in the mirror is in transit. The
identical file under a store-routed client repo is at its permanent home. The two are distinguished
by data that already exists and cannot drift, with no frontmatter, no migration of existing plans,
and no field for anyone to forget to set.]

[DECISION: **no `kind:` field; bug versus feature request stays out of the frontmatter.** Settled
with the user 2026-08-29. A `kind:` only earns a place if it changes what someone does, and a bug
and a feature request are both work with the same lifecycle, the same gates and the same retirement
rules. The convention has held to five tags and one status vocabulary with no categories. The
distinction stays evident from the title and `## Context`, where it costs nothing to maintain.]

[DECISION: **filing must work against every repo, client and work repos included** — settled
2026-08-29. With provenance dropped this costs nothing extra: filing is a write to the store mirror,
which every repo has regardless of route.]

[PITFALL: this plan settled `origin:` in the morning and dropped it the same afternoon, on the same
evidence, because the first pass designed for a multi-contributor future rather than the single-user
present. The general lesson is the one this convention already states about speculative work,
applied to frontmatter: a field is a contract every future plan pays for, so the bar is a reader
that exists now, not a reader that might.]

[DECISION: **the store contention is answered by a dirty-tree rule, not by locking.** The user's
answer, 2026-08-29: a harvest producing plans for another repo **creates a new plan and references
the existing ones when the tree is dirty**, recording in that new plan that a later pass should
unify them. When the tree is clean, it may update or expand existing plans directly.

The insight is that a new file never conflicts. Two sessions writing distinct new files to one git
repository do not contend in any way that matters — the cost is duplication, and duplication is
recoverable later by a pass that has both halves in front of it. Editing an existing file while
another session holds it is the thing that is not recoverable. So the rule trades a tidy tree for a
safe one, and buys the tidiness back with a second pass.

The convention still requires staging by explicit path in the store, never `git add -A`, for the
same reason the machine's own rules already require it in shared repos.]

[NEEDS CLARIFICATION: **which tree does "dirty" mean, and how is it checked?** Two readings, and
they lead to different code. If it is the **target repo's** tree, the check is
`git -C <target> status --porcelain` and it is about whether a session is mid-work there — but under
Stage 1 nothing is written into that tree anyway, so what it would gate is the Stage 2 absorption
and any edit to plans already committed there. If it is the **store's** tree, the check is whether
another session has uncommitted work in the store, and it gates whether a filing session may edit an
existing store-held plan. Both are plausible and both may be wanted; the sentence that settled this
covered the target repo, so that is the assumption unless corrected.]

[NEEDS CLARIFICATION: the sentence stating this rule was "make a second pass that unifies plans a
part of the newly created plan should", which reads as a slip. Taken to mean: the newly created plan
must itself record that a unification pass is owed, so the duplication is not silently left for
someone to discover. Worth confirming, since an alternative reading — that a second pass runs
automatically as part of the same harvest — is a materially different feature.]

## Where this touches `session-harvest`

`session-harvest` is the other half of the user's complaint, and it currently makes the problem
worse: it routes findings to "that repo's `plans/`", which for a finding about another repo means
precisely the cross-repo commit being designed out. Once filing is first-class, harvest's rule
becomes "a finding about the repo you are in goes to its plans; a finding about any other repo is
filed as an external contribution" — no cross-repo commit, ever, from a harvest.

## Recommended direction

Two stages, in order. No frontmatter changes in either.

### Stage 1 — file it, never commit it across

1. **`new <topic> --for <repo>`** — writes into that repo's store mirror, never touches its tree. A
   thin wrapper over `--to store --path`, which already works; the point is that it states intent,
   so no agent has to know the trick.
2. **`session-harvest` files rather than commits across.** A finding about the repo the session is
   in goes to that repo's plans as today; a finding about any other repo is filed. This is the rule
   change that removes the foreign commit, and it is most of the value of the whole plan.

### Stage 2 — absorb, from inside the repo that owns it

The store is a transit area for repo-routed repos, not a second home. A session actually working in
repo B drains it, on B's own schedule, committing only to B.

3. **A nudge, not a scan the user has to remember.** `list` at repo scope already reads the store
   mirror; it needs a footer line saying how many plans are waiting to be absorbed, in the same
   shape as the existing "N plan(s) await retirement" line. That line is the trigger for the whole
   stage.
4. **An absorb verb.** Per file this is already `move <file> --to repo`. What is missing is the bulk
   form and the rule about when — see the open question on dirty trees.
5. **A cross-repo warning.** Once absorption exists, writing into another repo's tree is a mistake
   rather than a workaround, and the tooling should say so at the moment it is attempted.

### The two skills have to cooperate, not each decide

`session-harvest` must not reimplement any of this. It decides _what is worth recording_; where the
file goes, whether the target tree is safe to touch, and whether an existing plan may be edited are
`plan-docs` questions, and the answers belong in `plans.py` where they are testable. Harvest calls
it and follows what it says. Two skills each holding half a rule is how the halves drift apart.

[PITFALL: the goal is "cross-repo **commits** almost never happen", not "cross-repo awareness never
happens". Awareness is the thing that makes a repo family navigable and it is already built. Stating
the goal as "cross-repo work almost never happens" risks removing the `depends_on` and family views
that are doing useful work, which would be a loss. Worth keeping the distinction explicit in
whatever this becomes.]

[DEFERRED: none of this addresses two sessions working the **same** repo, which shares one working
tree on this machine and is the harder half of "who committed what when". Filing conventions cannot
fix concurrent edits to the same tree. Worth its own plan if the pain persists after cross-repo
commits stop.]
