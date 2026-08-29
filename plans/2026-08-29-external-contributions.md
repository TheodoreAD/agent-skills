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
3. **No triage view.** `list --scope repo` shows a filed contribution mixed in with the repo's own
   plans. "What has been filed against this repo from outside that nobody has taken on" is the
   question a session should open with in a repo others file against, and it cannot be asked.

An "accept path" was the fourth item here. It turned out not to be missing — see the decisions
below: accepting a contribution is promoting its status, which already exists and already gates.

## The design question, stated precisely

[DECISION: **provenance is a separate axis from status, and the user's instinct to add frontmatter
is right.** `status` is lifecycle — where the work has got to. Where it came from is orthogonal: an
external bug report can be at any status, and a roadmap item can be too. Encoding provenance as a
status value (`status: reported`) would break the lifecycle vocabulary, which is why this is a
field.]

The rest was settled with the user the same day. One question is still open, at the end.

[DECISION: **one field, `origin:`, and no acceptance field — acceptance is the existing status
vocabulary.** Settled with the user 2026-08-29, and it is a better answer than the "location is
acceptance" design this plan originally recommended.

The triage question — "what has been filed against this repo that nobody has taken on" — is
`origin: external` **and** `status: idea`. That needs no new state, because the status vocabulary
already covers every transition: **accepting** is promoting off `idea` (to `planned`, `in-progress`,
or `blocked on …`), and **rejecting** is `abandoned`, which already means killed before landing.

Crucially the query is **location-independent**, which is what makes it work for store-routed client
repos where nothing can ever be graduated into a `plans/` directory. Location-as-acceptance would
have hardcoded into the filesystem a distinction that one field expresses in one place, and would
have been unexpressable exactly where the store matters most.]

[PITFALL: the accepted imprecision is that `origin: external` + `status: idea` cannot distinguish
"never looked at" from "looked at, still worth doing, left at `idea`". `updated` moves when the
owner touches it, which is a weak signal and not a reliable one. This is a deliberate trade against
a third state nobody would maintain — but it means the inbox view is "not yet promoted", not
"unread", and should be worded that way rather than implying it tracks attention.]

[DECISION: **no `kind:` field; bug versus feature request stays out of the frontmatter.** Settled
with the user 2026-08-29. A `kind:` only earns a place if it changes what someone does, and a bug
and a feature request are both work with the same lifecycle, the same gates and the same retirement
rules. The convention has held to five tags and one status vocabulary with no categories, and
`origin:` already carries the roadmap-versus-field-report signal that motivated the question. The
distinction stays evident from the title and `## Context`, where it costs nothing to maintain.]

[DECISION: **external contributions must work against every repo, client and work repos included.**
Settled with the user 2026-08-29. This is why `origin:` is a field rather than a location: the store
then holds two kinds of thing — plans that live there because the repo cannot take them, and
contributions filed from elsewhere — and the field is what tells them apart, at any location.]

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

Settled except where noted. Five pieces, each independently shippable:

1. **`origin:` frontmatter**, one field, two values. **Absent means internal**, so every existing
   plan on the machine stays valid and nothing needs migrating — only a filed contribution carries
   the field. Validated the way `status` is, so it cannot drift into a third invented value.
2. **`new <topic> --for <repo>`** — files against another repo, stamps `origin: external`, never
   touches that repo's tree. A thin wrapper over `--to store --path`, which already works; the point
   is that it says what is meant, so no agent has to know the trick.
3. **An inbox view** — `origin: external` and `status: idea`, at repo scope. Naming open; it is the
   question a session should open with in a repo other people file against. Word it as "not yet
   promoted", never "unread", per the pitfall above.
4. **No accept verb is needed.** Accepting is `set-status <file> planned`, which exists and already
   runs the promotion gate. Rejecting is `set-status <file> abandoned`. A store-held contribution
   for a repo-routed repo may additionally be moved with `move --to repo` once accepted, but that is
   a filing choice, not the acceptance itself.
5. **A `session-harvest` rule change** so a finding about any repo other than the one the session is
   in is filed as an external contribution rather than committed across.

[PITFALL: the goal is "cross-repo **commits** almost never happen", not "cross-repo awareness never
happens". Awareness is the thing that makes a repo family navigable and it is already built. Stating
the goal as "cross-repo work almost never happens" risks removing the `depends_on` and family views
that are doing useful work, which would be a loss. Worth keeping the distinction explicit in
whatever this becomes.]

[DEFERRED: none of this addresses two sessions working the **same** repo, which shares one working
tree on this machine and is the harder half of "who committed what when". Filing conventions cannot
fix concurrent edits to the same tree. Worth its own plan if the pain persists after cross-repo
commits stop.]
