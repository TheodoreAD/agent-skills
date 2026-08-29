---
status: planned
updated: 2026-08-29
---

## Context

The store is a local git repository with no remote, deliberately — the reasoning is in
`plans/2026-08-28-plans-outside-the-repo.md`, and it is that one personal remote accumulating
several employers' internal architecture is the outcome to avoid. The consequence, stated in
`SKILL.md` itself, is "treat it as unbacked-up".

The user reopened this 2026-08-29 and proposed a **two-tier split by root, with the sensitive tier
gitignored** so the rest can be pushed.

**The split is right. The gitignore mechanism is not**, for three reasons below — two of which are
silent failures rather than inconveniences.

Measured before arguing, 2026-08-29: the store currently holds **2 plans, both for a public personal
repo**, in 4 commits, with 0 retired plans. So nothing sensitive is in it today. But
`default =
"store"` routes all seven employer/client roots there, so this is a question about the
steady state, not about today.

## Status: designed, approved, deliberately unbuilt

[DECISION: **two git repositories is the agreed shape, and none of it is being built yet.** Settled
with the user 2026-08-29. The design below is approved rather than proposed — a future session
should implement it, not redesign it — but there is no user for it today: the store holds two plans,
both for a public personal repo, and no client work is running. Building a two-tier routing system
for a tier nobody is writing to is the same speculative work this repo's conventions reject
elsewhere, and the same argument that killed the `origin:` field a few hours earlier in
`plans/2026-08-29-external-contributions.md`.

**The trigger is the first plan actually written for a store-routed repo.** At that moment the
sensitive tier acquires content, and everything below becomes worth having. Until then the store
stays exactly as `SKILL.md` describes it: one local repository, no remote, treated as unbacked-up.]

[DECISION: **superseded 2026-08-29 — this is the next plan to execute.** The user named it directly
rather than waiting for the trigger above, which stays recorded because the reasoning behind it is
still sound; it simply is not what decided the timing. The shareable tier gets a private GitHub
remote, the sensitive tier stays local-only and unbacked, and the argument for that asymmetry is the
decision immediately below: the sensitive tier is empty, and an empty tier loses nothing.

What tips it now rather than later is that the store has stopped being empty. Three plans were filed
into it on 2026-08-29 that exist **nowhere else** — two for `power-user-linux-setup` and one
carrying two `~/AGENTS.md` corrections — so the durability gap this plan opens with is no longer
hypothetical.]

[DECISION: **the sensitive tier ships with no backup, and that is accepted rather than overlooked.**
Settled with the user 2026-08-29, answering the objection this plan raises against itself below. It
is acceptable precisely because the tier is unused — an empty tier loses nothing. It stops being
acceptable the moment the trigger above fires, so whoever implements this should treat the
non-vendor destination in the deferred note as part of the same piece of work rather than a
follow-up.]

## Why a remote is wanted at all, stated properly

[DECISION: **the argument is not "backups are nice" — it is that the convention makes a durability
promise it cannot keep.** `plan-docs` says deleting a retired plan is cheap _because_ its history is
retrievable through `archive`. For a repo-held plan that history is on a hosted remote. For a
store-held plan it exists on exactly one disk. The same document that says deletion is safe because
history survives also says to treat the store as unbacked-up. That is an architectural
inconsistency, and it is the real reason to revisit.]

## Why gitignore is the wrong mechanism

[PITFALL: **gitignoring the sensitive roots destroys the store's reason to be a git repository, for
exactly the repos it exists to serve.** The retirement rule says a store-held plan's durable half
goes into the repo it is about, and "what is left after that migration is reasoning that belongs to
nobody but you, and it stays in the store's git history, which is why the store is a git repository
at all." Gitignore those roots and there is no history for them: `archive` retrieves nothing,
retirement stops being reversible, and the justification for deleting the file collapses. The result
is durability for the tier with another copy and none for the tier that has no other copy — exactly
backwards.]

[PITFALL: **the dirty-store check goes silently blind.** Verified 2026-08-29: a write to a
gitignored path does not appear in `git status --porcelain` at all. So writing a client plan would
never mark the store dirty, the "add a new file rather than edit one another session may hold"
fallback would never fire for sensitive plans, and two sessions could edit the same client plan with
no signal. The check would report clean about a tier it cannot see — worse than having no check,
because the answer is trusted.]

[PITFALL: **path-based exclusion protects the wrong thing.** The risk is not "a file inside a client
directory", it is "a client's name inside any file". An unscoped idea or a plan for a personal repo
can easily name client work, because that is work the user thinks about. Gitignore gives confidence
proportional to path while the leak is content-shaped. The existing `scan` is the content-shaped
answer and already derives the right terms — verified running inside the store, 61 private terms
from the machine's own roots, which is precisely the list a push gate needs.]

## Recommended direction

### Two git repositories, not one repository with exclusions

- **Shareable tier** — `_unscoped/` and personal-repo mirrors. Its own repo, may have a remote.
- **Sensitive tier** — every root not marked shareable. Its own repo, local-only, **with full
  history**, so `archive` and the retirement rule keep working where they matter most.

Both keep the path-mirroring layout. The alternative shape — one tree with the sensitive root as a
nested repo named in the outer `.gitignore` — keeps one browsable directory but reintroduces the
status blindness above for any command that targets the outer repo, and nested repositories are a
standing source of confusion. Two directories is the plainer answer.

### The tier boundary already exists in config

`public_roots` already partitions roots into "names may be disclosed" versus confidential, which is
almost exactly this axis.

[DEFERRED: whether to reuse `public_roots` as the tier boundary or add a separate key defaulting to
it. Reuse is less config and no drift between two lists that would nearly always agree. But they are
not the same question — a root could have a public name and sensitive content, or the reverse — and
overloading one key for two purposes is cheap now and expensive at the moment they first disagree. A
build-time decision, not a blocker: it does not change the shape agreed above, and it is better
answered against a real second root than in the abstract.

Evidence for reuse, 2026-08-29: for a repo cloned directly into `projects_root`, one `public_roots`
entry already has to do two jobs — it keeps the repo's name out of the derived private-term list,
and under this design it also decides the tier. Having those disagree would mean a repo whose name
may be published but whose plans may not, or the reverse, which is possible but was not the case in
any layout examined. See `plans/2026-08-29-bare-repo-at-projects-root.md`.]

### A content gate before any push, not just a path split

`plans.py scan --mode tree` inside the shareable tier is the pre-push check: it fails on any client,
employer or internal name, derived from the machine rather than from a maintained list. This is what
actually protects the remote, with the tier split as structure rather than as the safety mechanism.

## How this plays with the flows that exist today

| flow                    | impact                                                            |
| ----------------------- | ----------------------------------------------------------------- |
| `new --for <repo>`      | picks the store by the target root's tier; shape unchanged        |
| dirty-store check       | must check **the store this write targets**, not "the store"      |
| commit-immediately rule | unchanged, per tier                                               |
| `absorb`                | unaffected — only repo-routed repos, which are all shareable tier |
| `archive`               | must search both stores; `archive_sources` already handles a list |
| `list --scope family`   | reads both                                                        |
| `doctor`                | reports both, their git state, and which has a remote             |
| `scan`                  | gains a role: the pre-push gate on the shareable tier             |
| `install` / `where`     | creates and routes to two stores                                  |

Contained rather than small: mostly "the store" becoming "the store for this tier". Nothing about
the plan format, the status vocabulary or the tags changes.

[DECISION: **binary tiers now, not per-root destinations.**
`plans/2026-08-28-plans-outside-the-repo.md` already defers per-root sync — "a remote for one root,
against that employer's actual sanctioned destination and policy" — and that still needs a real
per-employer answer that does not exist. A binary shareable/local-only split is buildable today and
generalises later, since the tier lookup is the same hook a per-root destination would use.]

[DEFERRED: whether the sensitive tier ever gets an encrypted remote (`git-remote-gcrypt`, or restic
to any host), which would give it durability without a vendor holding anything readable. It changes
the concentration objection materially, and it does not answer a contract that forbids third-party
storage at all — and it adds a key whose loss is worse than no backup, because it looks like one.
Out of scope until the plain split exists.]

[DEFERRED: a non-vendor destination for the sensitive tier — external drive, NAS, second machine —
which closes the durability gap with no disclosure question at all. Accepted as absent for now
because the tier is unused, per the decision at the top. **Implement it in the same pass as the
split**, not after: the moment the tier has content, leaving it unbacked reproduces exactly the
failure this plan criticises gitignore for, which is durability everywhere except where it matters.]
