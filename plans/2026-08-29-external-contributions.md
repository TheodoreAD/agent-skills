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

So the transport is built. What is missing is **meaning, and a defined hand-off.**

## What is actually missing

1. **Nothing records that a plan came from outside.** The pulse note above was hand-stamped
   `origin: external` by an agent inventing a field. Nothing writes it, nothing reads it, nothing
   validates it — the exact "half-tagged is worse than untagged" failure this convention warns about
   elsewhere.
2. **`--to store --path <other repo>` is an override, not an expression of intent.** It happens to
   do the right thing. A first-class `new <topic> --for <repo>` would say what is meant and stamp
   the provenance without an agent having to know the trick.
3. **There is no accept path.** `graduate` moves an unscoped plan into a repo. A store-held
   contribution _for a repo-routed repo_ has no defined equivalent, so nothing says how repo B takes
   ownership when it decides to.
4. **No triage view.** `list --scope repo` shows a filed contribution mixed in with the repo's own
   plans. "What has been filed against this repo from outside that I have not accepted" is the
   question a session should open with, and it cannot be asked.

## The design question, stated precisely

[DECISION: **provenance is a separate axis from status, and the user's instinct to add frontmatter
is right.** `status` is lifecycle — where the work has got to. Where it came from is orthogonal: an
external bug report can be at any status, and a roadmap item can be too. Encoding provenance as a
status value (`status: reported`) would break the lifecycle vocabulary, which is why this is a
field.]

Beyond that, three things are genuinely open, and the shape of the whole feature depends on them.

[NEEDS CLARIFICATION: **is provenance one axis or two?** "Where it came from" (roadmap vs field
report) and "has the owning repo accepted it" are different questions. Conflating them means
"accepted external bug" cannot be expressed. Two candidate designs:

- **Location is acceptance.** One immutable field `origin: internal | external`; living in the store
  means not yet accepted, and graduating it into the repo's `plans/` _is_ the acceptance. Elegant —
  no second field, and the existing `graduate` verb becomes the accept action. **But it breaks for
  store-routed repos:** a client repo's plans live in the store permanently and can never be
  graduated anywhere, so acceptance would be unexpressable exactly where the store matters most.
- **Two fields.** `origin:` plus an explicit acceptance state. Uniform across routes, at the cost of
  a second thing to keep accurate — and a field nobody updates is worse than no field.

The first is cleaner and the second is more honest. Deciding needs the user to say whether external
contributions against store-routed (client) repos are in scope at all.]

[NEEDS CLARIFICATION: **is "kind" a third axis, or inferable?** The user's framing pairs provenance
with a bug/feature-request distinction. Those may be the same axis (external ⇒ came from use, so bug
or request) or two (an external contribution can be a pure idea; an internal one can be a bug found
by its own maintainer). Adding `kind: bug | feature | idea` is a taxonomy, and this convention has
so far resisted taxonomies — five tags, one status vocabulary, no categories. Worth resisting again
unless the distinction changes what anyone _does_.]

[NEEDS CLARIFICATION: **does the store become the new contention point?** Both sides now commit
there: the filing session writes a contribution, the owning session later removes it on acceptance.
Two sessions committing to one git repository is the thing being escaped. It is probably still far
better — the files are distinct, the commits are tiny, and nothing is ever edited concurrently — but
"probably better" is not a design. At minimum the convention must require staging by explicit path
in the store, never `git add -A`, for the same reason the machine's own rules already require it in
shared repos.]

## Where this touches `session-harvest`

`session-harvest` is the other half of the user's complaint, and it currently makes the problem
worse: it routes findings to "that repo's `plans/`", which for a finding about another repo means
precisely the cross-repo commit being designed out. Once filing is first-class, harvest's rule
becomes "a finding about the repo you are in goes to its plans; a finding about any other repo is
filed as an external contribution" — no cross-repo commit, ever, from a harvest.

## Recommended direction

Not settled, pending the questions above, but the shape that follows from what already exists:

1. `new <topic> --for <repo>` — files against another repo, stamps provenance, never touches that
   repo's tree. Thin wrapper over machinery that already works.
2. A frontmatter field for provenance, validated the way `status` is, so it cannot drift.
3. An accept verb, generalising `graduate` beyond the unscoped area.
4. `list --inbox` (naming aside) — what has been filed against this repo and not yet accepted, which
   is the question a session should open with.
5. A `session-harvest` rule change so findings about other repos route here automatically.

[PITFALL: the goal is "cross-repo **commits** almost never happen", not "cross-repo awareness never
happens". Awareness is the thing that makes a repo family navigable and it is already built. Stating
the goal as "cross-repo work almost never happens" risks removing the `depends_on` and family views
that are doing useful work, which would be a loss. Worth keeping the distinction explicit in
whatever this becomes.]

[DEFERRED: none of this addresses two sessions working the **same** repo, which shares one working
tree on this machine and is the harder half of "who committed what when". Filing conventions cannot
fix concurrent edits to the same tree. Worth its own plan if the pain persists after cross-repo
commits stop.]
