---
status: landed
updated: 2026-09-05
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

[DECISION: **a store plan is committed the moment it is written, never at the end of a session.**
Added by the user 2026-08-29. This and the dirty-store rule above are the same rule from two ends:
the add-a-new-file fallback is cheap precisely because dirty windows are short, and dirty windows
are short only if nobody sits on an uncommitted plan. A session that batches its store commits until
the end forces every other session, for that whole period, into a fallback it did not need.

The moment is after the content is written, not at `new` — `new` produces an empty skeleton, so
committing there would record nothing useful and leave the file dirty again immediately. `new --for`
prints the exact command as its closing line so the timing is in front of the agent at creation.]

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
   change that removes the foreign commit, and it is most of the value of the whole plan. **Landed
   2026-08-29**, by the harvest of the session that built this: its cross-repo routing filter now
   reaches for `new --for`, and `depends_on` keeps its distinct meaning — _this_ work cannot land
   until another repo changes, a dependency rather than a delivery. Exercised on that same run,
   routing two `~/AGENTS.md` corrections to the repo owning the fragments.

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

[PITFALL: **the cwd-based guard is blind in the case that matters most, and no better signal
exists.** Raised by the user 2026-08-29 immediately after it was built; the challenge was correct.
Whether cwd survives between an agent's Bash calls is unreliable in both directions — a reset and a
persisted `cd` were both observed inside the single session that built this. Two failure modes:

- **Blind.** With no `--path`, the target repo and "this session's repo" are both derived from cwd.
  They drift together, compare equal, and the guard cannot fire — the plan lands in whatever repo
  cwd wandered into.
- **Misfires.** With an explicit `--path` naming the session's real repo while cwd has drifted, a
  correct action is refused, and the suggested `--for` would file to the store rather than the repo.

**Both are now fixed** — see the anchor decision below. The `repo:` line each create prints was
added as the fallback mitigation and stays, because it is true regardless of what any comparison
did.]

[DECISION: **the session is anchored to the repo it started in, via its transcript directory.**
Found 2026-08-29 after the user asked whether a session could be tied to its starting repo — the
first answer, that no such signal existed, was wrong and had been reached by checking only for
`CLAUDE_PROJECT_DIR`.

`CLAUDE_CODE_SESSION_ID` _is_ exported, and Claude Code writes each session's transcript to
`<config>/projects/<encoded project path>/<session id>.jsonl`. The directory holding this session's
file therefore names the repo the session belongs to, fixed when the session began and unaffected by
any later `cd`. Measured the same day: the guard now fires on a create from a drifted cwd with no
`--path` — the case it was previously blind to — and stops refusing a correct `--path` naming the
session's real repo.

The encoding replaces every non-alphanumeric with `-`, so it is lossy and ambiguous to reverse.
Candidate repos are encoded and compared rather than the directory name being decoded, with cwd's
repo tried first so the projects-root walk only happens in the drifted case that actually needs it.

Absent or unmatched — another harness, a subagent, a moved transcript — it falls back to cwd, which
is the previous behaviour rather than a failure. The environment assumption is declared in
`SKILL.md`, as this repo's rules require of a skill that depends on one.]

[DECISION: **three anchor tiers, and only the middle one is Claude-specific.**
`$PLAN_DOCS_SESSION_REPO` first, the Claude transcript second, cwd last. Added 2026-08-29 when the
user asked to be sure a non-Claude harness had a fallback — it did (cwd), but that is the tier that
cannot detect drift, so "works" and "works as well" were not the same thing. The neutral variable
closes that: any harness exporting `PLAN_DOCS_SESSION_REPO="$(git rev-parse --show-toplevel)"` at
session start gets a guard exactly as strong as Claude Code's, verified against a drifted cwd with
the Claude variables unset.

An explicit value beats an inferred one, so the variable wins over the transcript. A value that is
not inside a git repository **raises** rather than falling back — silently degrading the guard
someone just tried to strengthen is the worst of the three outcomes.]

[DECISION: **`doctor` reports the tier in use and lists the cwd fallback as a problem.** A degraded
guard that never says it is degraded is worse than no guard, because it is trusted. This is the same
argument as the store's git-identity check: a condition that silently disables a safety property has
to be visible from the command whose job is telling you what is broken.]

[DEFERRED: a machine-level rule that an agent asks the user before `cd`-ing into another repo at
all, raised by the user 2026-08-29 as secondary to the above. It belongs in `~/AGENTS.md` rather
than this skill, since it governs every Bash call and not just plan filing — filed as a note in the
store for `power-user-linux-setup`.]

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

### Retirement happens where the plan lives permanently

[DECISION: **a repo that keeps its own plans must absorb a filed plan before retiring it.** Raised
by the user 2026-08-29 to keep history walkable, and enforced: `set-status` refuses a terminal
status on a plan still in the store mirror of a repo-routed repo, and names `absorb`.

Retirement deletes the file, and `archive` reads a retired plan back out of the deletion commit. So
retiring from the store would put that plan's whole record — drafting, landing, deletion — in the
store's history while the repo's history holds nothing, and `archive` run inside the repo it belongs
to would find it missing. One plan, two histories, and the cheap-deletion rule stops holding.

Only terminal statuses are blocked. Marking a filed plan `in-progress` before absorbing is harmless,
because nothing has been deleted yet. And a **store-routed** repo is unaffected: its plans live in
the store permanently, so that is where their history belongs.]

[PITFALL: **`locate` obeyed the route, so `set-status` could not see a filed plan at all** — the
same route-limits-reads bug already fixed for the per-repo listing, still present in the by-filename
lookup and therefore in `set-status`, `move`, `refs` and `tags --file`. Found only because the first
version of the guard's test passed for the wrong reason: the terminal statuses were rejected by "no
plan named …" rather than by the guard, and the non-terminal case failing is what exposed it. A test
that passes for the wrong reason is worse than one that fails, and only the case expected to succeed
revealed it.]

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

## Migrated to

- **`skills/plan-docs/SKILL.md`, "Something that belongs to a repo you are not in"** — `new --for`,
  the three anchor tiers and their table, the dirty-store add-a-file rule, commit-the-moment-it-is-
  written, the store being the tree that is checked, and the two habits (read the `repo:` line,
  never `cd` without asking).
- **`skills/plan-docs/SKILL.md`, "Absorbing what was filed for this repo"** — `absorb` reporting and
  performing, the once-per-session trigger and the silence when nothing waits, one question for the
  set, committing to both repositories and why that is not the forbidden cross-repo commit, a name
  collision being a merge, and the one-shot nature of the pairing prompt.
- **`skills/plan-docs/SKILL.md`, "Retiring a plan"** — absorb-before-retire, with the one-plan-one-
  history reason.
- **`skills/plan-docs/references/design-rationale.md`, "Why filing carries no provenance and no
  `kind:` field"** — both refusals, the same-day `origin:` reversal and the lesson it carries, and
  why route-plus-location makes the refusal free.
- **`skills/plan-docs/references/design-rationale.md`, "Why the cross-repo guard is anchored to the
  session's start, not to cwd"** — the blind and misfiring failure modes, the wrong first answer
  about whether a signal existed, the transcript-directory mechanism, and why the explicit variable
  raises rather than degrading.
- **`skills/plan-docs/references/design-rationale.md`, "Why a dirty store means 'add a file', not
  'wait' or 'lock'"** — the asymmetry that makes duplication the cheap failure.
- **`plans/2026-09-06-two-sessions-share-one-working-tree.md`** — the second `DEFERRED` below, whose
  condition is now met: cross-repo commits have stopped and the same-tree pain has not.
- **`plans.py` and its tests** — `new --for`, `absorb`, the `list` footer, the guard's
  refuse-versus- warn split, and the `locate`-obeyed-the-route bug are all code with tests,
  including the test that first passed for the wrong reason.

Deliberately not migrated:

- **The first `DEFERRED`, on asking before `cd`-ing into another repo.** It landed: `plan-docs`'
  `SKILL.md` states it, and `~/AGENTS.md` has since gone further and prohibits _writing_ to another
  repo outright, which is the stronger form of the same concern. Its store note for
  `power-user-linux-setup` has been absorbed there.
- **"What already works, which is more than expected" and "What is actually missing"** — an
  inventory of a gap that has since been closed, item by item, by the work this plan describes.
- **The staged plan of work.** Both stages landed; the commits are the record.
