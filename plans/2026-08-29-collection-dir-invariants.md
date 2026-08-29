---
status: in-progress
updated: 2026-08-29
---

## Context

`plan-docs` discovers repos by walking `projects_root` and stopping at each `.git`. Nothing checks
that the tree it walks is shaped the way the walk assumes, so several malformed layouts produce
wrong answers silently rather than errors. The user set out the intended shape 2026-08-29 and asked
what was missing; this records the invariants, the failures found by testing, and how a collection
gets its policy.

**No repo on this machine moves.** These are checks over the existing layout, not a reorganisation.

## The model

A **repo collection directory** is any directory on the path from `projects_root` down to a repo.
`projects_root` itself is one; so is each root under it; so is each intermediate level in a
`<root>/<project>/<repo>` hierarchy.

[DECISION: **collection-ness is derived, never configured and never asked.** A directory is a
collection if and only if it is not a repo and has at least one repo beneath it. That falls out of
the walk that already exists, so there is nothing to declare, nothing to keep in sync, and no
registry to go stale — which is the same reason discovery itself stays implicit.]

Invariants, as stated by the user and refined by what testing found:

| rule                                                          | strength                       |
| ------------------------------------------------------------- | ------------------------------ |
| a collection MUST NOT be a git repo                           | hard error — see below         |
| a directory inside a collection is a repo **or** a collection | otherwise it is reportable     |
| a repo must be a repo to be routed                            | already true by construction   |
| collections may be specialized by a marker                    | open — see the marker question |

The second was stated as "any directory inside a collection MUST be a repo". That would outlaw the
interior level of a three-level hierarchy, which this machine uses, so it is refined to repo **or**
collection: leaf or interior node. A directory that is neither — no `.git`, no repos anywhere
beneath — is the genuinely reportable case.

Not handled, deliberately: converting a repo into a plain directory afterwards, or comparable
exotica. The user ruled these out and nothing here tries to detect them.

## What testing found

[PITFALL: **`projects_root` itself being a git repo is catastrophic and silent, and it is the one
invariant that must hard-fail.** Verified 2026-08-29: with a `.git` at the root, `repo_paths`
returns `["."]` — the entire tree collapses to a single repo named `.`, every real repo becomes
invisible to every command, and `private_terms` derives almost nothing, so the confidentiality gate
silently empties while still reporting success. A gate that reports "0 hits" because it can no
longer see anything is the worst failure available in this tool.]

[PITFALL: **a bare repo is neither a repo nor a collection, and is currently mistaken for the
latter.** Verified with `mirror.git` in a collection: it has no `.git` child, so the walker descends
into `objects/`, `refs/` and `hooks/` looking for repos. It finds none, so nothing bogus enrolls —
but the directory name still enters the private-term list through the `iterdir` pass, split into
`mirror` and `mirror.git`, and the walk is wasted. It deserves its own diagnosis rather than being
silently treated as an empty collection.]

[PITFALL: **the depth limit fails silently.** `MAX_REPO_DEPTH = 3`, so a repo at depth 4 is never
found by anything — not `list`, not `doctor`, and critically not `scan`, whose whole job is to know
every name under the root. No error, no mention. Given collections nest, a repo below the limit is
invisible rather than excluded.]

[DECISION: **symlinked directories are never followed.** Tested 2026-08-29, and the risk is worse
than duplication. Git resolves symlinks — `rev-parse --show-toplevel` from inside a linked directory
returns the real path — so **routing** is always correct while **discovery** is not, and the two
disagree:

- A link to a repo _inside_ the root enrolls that repo a second time under the link's path.
  Measured: one plan file listed as two plans in two locations, and the link name entered the
  private-term list as though it were a distinct repo.
- A link to a repo _outside_ the root is worse. Discovery accepts it, so it is counted and its name
  reaches the term list, while `where` inside it refuses with `needs-decision` — "not under
  projects_root, so its store path cannot be mirrored". Discovered but unusable.

Skipping makes discovery and routing agree. The cost is that deliberately symlinking an external
repo into the tree no longer enrols it — but that never worked, per the second case, so nothing that
functioned is lost. `doctor` reports the skip so someone who intended enrolment learns why it is not
happening.]

[DECISION: **an unreadable directory is reported, not fatal.** `iterdir()` raised uncaught, so a
permissions problem anywhere under the root crashed whichever command was running. Now caught per
directory: the subtree is skipped with a note, and everything readable still answers.]

## How a collection gets its policy

Two things need deciding per collection, and neither is "is this a collection":

- its **route** — `repo`, `store`, or `both`
- whether its name is **disclosable**, which drives `scan` and, under
  `plans/2026-08-29-store-sensitivity-tiers.md`, the store tier

The mechanism exists: `install --explain` prints these as decisions, the agent puts them to the user
with `AskUserQuestion`, `config set` records the answers. Nothing new is needed for the initial
pass.

[PITFALL: **a `default` turns every later collection into a silent decision.** With
`default =
"store"` set — as it is here — a newly cloned root never triggers a question: `where`
returns `ok` and the plans go to the store. For a client root that is exactly right. For a
**personal** root it is quietly wrong, and wrong in a way nothing surfaces: a store-routed repo's
mirror _is_ its permanent home, so `absorb` correctly does nothing, and the plans accumulate in the
store forever without ever reaching the repo they belong to. The safe default is right for the
common case and wrong for the rare one, which is precisely why it would go unnoticed.]

[DECISION: **every root is categorised explicitly in the config, and `doctor` flags any that is
not.** Settled with the user 2026-08-29: the route is a user choice that has to persist, and the
tooling alerts when it needs to change. Done the same day — the seven employer and client roots each
got a `[roots]` entry via `config set`, which changes no behaviour (they already reached the same
answer through `default`) but converts the config into a record of what has been decided.

`default` returns to being a safety net rather than the answer, so a root reaching it now means
exactly "this appeared since you last decided anything". No seen-markers, no registry, no second
source of truth — the signal is the absence of a config entry.]

## What was built

All of it, 2026-08-29. `walk_projects` returns the repos and the layout problems together; `doctor`
reports them; `repo_paths` is a thin wrapper so every existing caller inherits the invariants for
free.

Only root-is-a-repo hard-fails, and it fails wherever the walk is used rather than only in `doctor`
— every answer downstream of it is wrong, so continuing is worse than stopping. `doctor` catches it
specifically and reports it with the locations, since the command whose job is diagnosing should not
die with the same message every other command already gives.

[PITFALL: **the first version reported 24 problems on a healthy machine, which is a failed gate by
this codebase's own standard.** Two categories were over-reporting, and only running it against the
real tree showed it.

`too deep` fired for every directory at the depth limit — ordinary `src/`, `docs/` and `poze/`
folders — burying the real findings. Now it peeks one level for a `.git` and reports only when a
repo is genuinely being excluded: on this machine that took the category from 8 entries to zero.

`no repos` fired for every playground and scratch directory. Correct by the letter of the invariant
and useless in practice, since acting on none of them is the right answer. It moved behind
`--strict`, with a count in the enrolled block so it stays discoverable — a permanent entry inside
`problems (N)` is how a problems list stops being read.

24 down to 8, then to 0 once the roots were categorised.]

The marker question — whether a specialized collection should carry a git attributes file — moved to
`plans/2026-08-29-collection-specialization-marker.md` on the user's instruction, since it is the
one detail here they do not want to solve now and it was the only thing holding this plan open.
Nothing in the implementation needs it: collection-ness is derived from the tree and policy comes
from the config.
