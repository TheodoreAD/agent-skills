---
status: in-progress
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

All settled with the user the same day, over three passes — one of which reversed the first.

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

[DECISION: **the tree checked is the store's, not the target repo's.** Confirmed by the user
2026-08-29. `git -C <store> status --porcelain` decides whether a filing session may edit an
existing store-held plan or must add a new file referencing it. This is the check that bites in
Stage 1, where the writing actually happens — the target repo's tree is never written to by a filing
session at all, which is the point of the whole design.

It also means the check is about **one** repository rather than one per target, so it is a single
cheap call regardless of how many repos a harvest produces plans for.]

[DECISION: **absorption is the reconciler; there is no separate unification pass.** Settled with the
user 2026-08-29 after both earlier readings were rejected. A split created because the store was
dirty is paired back up at the next absorption, which is typically a fresh session in the owning
repo but is not required to be one — it is simply the first moment both halves are in one tree with
one session owning them.

The signal is the reference the dirty-store rule already requires the second plan to carry, checked
against both directories so it pairs with a filed plan or one already committed. Deterministic, and
it costs the author nothing they were not already told to write. Guessing from similar titles was
rejected: a false pair is worse than a missed one, because it proposes destroying a distinct plan.

**The script finds the pairs; the agent merges the prose; the user accepts.** Same split as
everywhere else in this skill — mechanics in `plans.py` where they are testable, judgement in the
session. No tooling edits plan prose.]

[PITFALL: **a pair skipped at absorption is never re-surfaced.** The pairing lives in prose, and
once absorbed the plans are ordinary repo plans that cite each other, which is indistinguishable
from the many legitimate cross-references plans carry. So the consolidation prompt is one-shot. The
alternative — a marker in the file — was considered and rejected, since a marker on every
dirty-store split is a tag nobody would clear. Accepted, and stated in `SKILL.md` so the prompt is
not treated as a reminder that will come back.]

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

The store is a transit area for repo-routed repos, not a second home. The user's stated cycle,
2026-08-29:

> build feature → harvest → write plans to the central store for another repo → stop. Then in the
> target repo: build feature → harvest → write plans wherever needed → new session → call plan-docs
> → consolidation proposed before anything else → user accepts → consolidation happens, committed in
> both repos → resume the regular flow of displaying the most likely plans to continue on.

[DECISION: **consolidation commits to both the target repo and the store, and this is not the
cross-repo commit the plan exists to prevent.** Worth stating because it looks like one. The session
consolidating _is_ the session working in the target repo: it commits to its own repo, which is
ordinary, and to the store, where it only removes the file it just absorbed. Nothing lands in a
third party's tree. The distinction the whole design rests on is not "never touch two repositories",
it is "never write into a working tree that is not yours".]

[DECISION: **"usually a fresh session" is agent state, not script state, so the skill owns the
trigger and the script owns the answer.** `plans.py` is stateless and cannot tell a first call from
a fifth; proposing on every invocation would make the feature an irritation within a day. The script
reports what is absorbable and performs it on request; `SKILL.md` says to propose it once, on the
first plan-docs call of a session. Putting the once-per-session rule anywhere else cannot work.]

[DECISION: **silence when there is nothing to absorb.** The stated flow says consolidation comes
before anything else, which is right when there is something waiting and friction when there is not
— a request to capture a quick idea should not become a triage prompt. So the proposal appears only
when the store actually holds plans for this repo, and costs nothing at all otherwise. This is a
softening of "before anything else", agreed as the intent rather than the letter.]

The pieces:

3. **`absorb`, reporting and performing.** Per file this is already `move <file> --to repo`; what is
   missing is the set view and the bulk form. Bulk matters because the proposal is one question, not
   one per plan.
4. **A `list` footer**, in the same shape as the existing "N plan(s) await retirement" line, so a
   session that skipped the proposal still sees the backlog.
5. **A cross-repo guard**, last, because warning about a workaround before its replacement exists
   just blocks people.

[DECISION: **`new` refuses, everything else warns.** Once `--for` exists there is no legitimate
reason to create a plan in another repo's tree, so that one is an error naming the alternative — a
warning would be read past by exactly the agent that needed it. Commands acting on files that
already exist (`graduate`, anything aimed by `--path`) warn instead, since those have real uses and
a false refusal blocks work. The session's repo is cwd, never `--path`: `--path` names what a
command is _about_, cwd is where the session lives, and keeping them distinct is what makes the
detection possible at all.]

[PITFALL: absorbing means committing markdown into the target repo, so **the target's quality gate
runs before that commit** like any other. Doc-only commits that skipped the gate are already the
most common cause of red CI in these repos, and a bulk absorb touching several files at once is
exactly the shape that trips a formatter.]

[DECISION: **a name collision on absorption refuses, exits non-zero, and destroys neither copy.**
Two plans sharing `YYYY-MM-DD-topic.md` means both were written about the same topic on the same
day, which is a merge — the same conclusion the consolidation pairing reaches by a different route.
Renaming around it would be the one outcome that hides exactly the case worth noticing. The other
absorbable plans in the same run still move; only the colliding one is held back, so one conflict
does not block the batch.]

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
