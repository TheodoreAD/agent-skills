---
status: idea
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

[UNVERIFIED: symlinks. `iterdir()` with `is_dir()` follows them, so a symlinked repo can plausibly
enroll twice under two paths, or resolve outside `projects_root` entirely. Not tested; the decision
to follow or skip has not been made either.]

[UNVERIFIED: an unreadable directory raises out of `iterdir()` uncaught, so a permissions problem
anywhere under the root crashes the command instead of being reported as a problem. Not tested.]

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

[NEEDS CLARIFICATION: whether to make every existing root explicit so that "matched only by
`default`" becomes a meaningful signal. If each of this machine's roots gets its own `[roots]`
entry, then a root falling through to `default` means exactly "this appeared since you last decided
anything", and `doctor` can list those as awaiting categorisation with no new state, no seen-markers
and no registry. The cost is a one-off pass over the existing roots and the loss of `default` as a
shorthand. The alternative is to keep `default` as the real answer and accept that new collections
are categorised silently.]

## Recommended direction

1. **`doctor` validates the invariants** and reports each failure with its diagnosis:
   root-is-a-repo, bare repo, neither-repo-nor-collection, unreadable, and any repo excluded by the
   depth limit.
2. **Only root-is-a-repo hard-fails**, and it fails wherever the walk is used rather than only in
   `doctor` — every answer downstream of it is wrong, so continuing is worse than stopping.
3. **Categorisation stays a conversation**, through the existing `install --explain` → question →
   `config set` path, with `doctor` naming which collections still lack an explicit answer.

[DEFERRED: the marker question. The user's proposal was a git attributes file in a specialized
collection. Verified 2026-08-29 that a `.gitattributes` above a repo affects nothing —
`git check-attr` reports `unspecified` — because git reads attributes from inside the working tree,
from `$GIT_DIR/info/attributes` and from the global `core.attributesFile`, never from a parent of
the repo root. So it works as an inert marker but not as specialization, and the mechanism that
actually specializes a root is an `includeIf "gitdir:<path>"` in the user's git config, which lives
in the config rather than the directory and so cannot double as a marker. Needs the user's intent
before anything is built.]
