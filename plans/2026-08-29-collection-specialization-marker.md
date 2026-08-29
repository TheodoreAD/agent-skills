---
status: idea
updated: 2026-08-29
---

## Context

Split out of `plans/2026-08-29-collection-dir-invariants.md` on 2026-08-29 at the user's request:
everything else in that plan is built, and this is the one detail they explicitly do not want to
solve now. Parked here so the parent plan is not held open by it.

The original proposal was that a **specialized** repo collection directory — one that is not a plain
`projects/`, which would more likely be configured globally — SHOULD carry a git attributes file
marking it as such.

## Why it is not obvious

[PITFALL: **a `.gitattributes` above a repo is inert.** Verified 2026-08-29: with
`collection/.gitattributes` setting `*.md text=lf-only` and a repo at `collection/repo`,
`git check-attr text -- x.md` inside that repo reports `unspecified`. Git reads attributes from
inside the working tree, from `$GIT_DIR/info/attributes`, and from the global `core.attributesFile`
— never from a parent of the repo root. So the file works as an inert marker but specializes
nothing, and naming it `.gitattributes` would mislead every future reader into thinking it is
functional.]

The mechanism that actually specializes a collection is an `includeIf "gitdir:<path>"` in the user's
git config — which lives in the config rather than in the directory, and so cannot double as a
marker sitting in the tree.

## Open questions

[NEEDS CLARIFICATION: what the marker is actually for. Two readings, and they want different things:
a **detection** aid, so tooling can tell a specialized collection from a plain one — for which
`.gitattributes` is a poor choice of name and something explicit would be better; or genuine
**per-collection git behaviour**, which needs the `includeIf` mechanism and no file in the tree at
all. The user has said this is not worth solving now, so it should not be guessed at.]

[DEFERRED: nothing in the current implementation needs it. `plan-docs` derives collection-ness from
the tree (not a repo, has repos beneath it) and reads policy from its own config, so no marker is
required for anything that exists today. This is a nice-to-have whose absence costs nothing.]
