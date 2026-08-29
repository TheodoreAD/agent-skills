---
status: idea
updated: 2026-08-29
---

## Context

The user asked 2026-08-29 whether `plan-docs` works with a repo cloned directly into `projects_root`
— `~/projects/<repo>` — rather than the `~/projects/<root>/<repo>` shape this machine happens to
use. It does, but two things behave wrongly at depth 1, both found by testing against a scratch
projects root rather than by reading.

Discovery is fine: `repo_paths` checks for `.git` before descending, so a depth-1 repo is found and
gets `rel = "<repo>"`. Routing and the confidentiality scan are where it breaks.

## The two defects

[PITFALL: **a `[roots]` entry can never match a depth-1 repo, and the failure is silent.**
`_match_rule` walks prefixes with `range(len(parts) - 1, 0, -1)`, which is empty when `rel` has a
single segment — so `[roots] "loose-repo" = "repo"` is skipped entirely and the repo falls through
to `default`. Reproduced 2026-08-29 against a scratch root: `where` reported
`read store, write store (default)` while a `[roots]` entry naming that exact repo sat in the
config, unread.

Arguably the semantics are defensible — `[roots]` keys are prefixes, and a bare repo has no prefix —
but a config entry that matches nothing and says nothing is a trap either way. A `[repos]` entry
does work, verified in the same run.]

[PITFALL: **a depth-1 repo is treated as an organisation by `private_terms`, so its name is split
into ordinary words that then poison `scan`.** The splitting is deliberate for roots — a root called
`<org>.com-bitbucket-<team>` has to match an `@<org>.com` address too — and the code comment says
explicitly that only root names are split "because splitting repo names too would gate on ordinary
words like `telemetry`". But `private_terms` iterates `projects_root.iterdir()`, and at depth 1 a
repo _is_ one of those entries, so it gets the organisation treatment.

Measured 2026-08-29: a repo at `~/projects/loose-repo`, not listed in `public_roots`, produced the
private terms `loose`, `loose-repo` and **`repo`**. A gate that flags the word "repo" in every
document is a gate that gets switched off, which is precisely the noise-then-ignored failure the
splitting rule was written to avoid.]

## It works today, with two config caveats

Tested 2026-08-29 against a scratch root containing one bare repo and one `<root>/<repo>` client
tree. With both caveats applied the bare repo routes correctly and contributes **no** private terms
at all — the only terms derived came from the client root, split correctly:

- **List it in `public_roots`.** This skips the organisation-splitting branch entirely, so the
  second defect below disappears. It is also semantically right: `public_roots` means "names that
  may be disclosed", and a personal repo's name is one.
- **Route it with `[repos]`, not `[roots]`.** `[repos] "<name>" = "repo"` matches exactly; the
  `[roots]` form is silently ignored, per the first defect.

So the honest summary is "supported, with two things you have to know" rather than "broken" — which
lowers the urgency of the fixes without removing the case for them, since both caveats are invisible
until someone hits them.

[DECISION: **a bare repo lands in the non-sensitive tier only if it is in `public_roots`.** Asked by
the user 2026-08-29 while thinking about the tier split, which landed the same day; the boundary is
`shareable_roots`, which falls back to `public_roots` while unset. A depth-1 repo is its own root,
and tier follows root membership — so a bare repo **not** listed defaults to the _sensitive_ tier,
which is the opposite of what "I put it at the top level because it is my own" would suggest.

The same single `public_roots` entry therefore does both jobs: it stops the scan poisoning and it
puts the repo in the shareable tier. That convergence is real evidence for reusing `public_roots` as
the tier boundary rather than adding a second key — the deferred question in the tiers plan — though
it is evidence of convenience, not proof the two questions can never diverge.]

## Recommended direction

Both fixes are small and independent.

1. **Make a `[roots]` entry that can never match an error, or make it match.** The cheaper honest
   option is validation: at config load, a `[roots]` key that names an existing depth-1 _repo_
   rather than a directory of repos is a mistake, and saying so beats silently ignoring it. The
   alternative — letting `[roots]` match a whole `rel` — collapses the distinction between "a
   directory containing repos" and "a repo", which is the distinction the two sections exist to
   draw.
2. **Only split a directory's name when it actually contains repos.** `private_terms` should skip
   the organisation-splitting branch for an entry that is itself a git repository, and fall through
   to the per-repo handling that adds the whole name without splitting it. That keeps the
   `<org>.com-…` case working and stops ordinary words entering the term list.

[UNVERIFIED: whether anything else keys off `rel.split("/")[0]` in a way that assumes depth ≥ 2.
`doctor` groups by that value and would show a bare repo as a root containing one repo, which is
cosmetically odd but not wrong. The `backlog`/`list` footer uses it to decide whether a row names a
non-public repo. Neither looks harmful, but neither was tested at depth 1.]

[DEFERRED: this repo's own layout has no depth-1 repos, so nothing here is currently biting. It
matters for anyone adopting the skill with a flat `~/projects/<repo>` layout, which is the more
common convention — the `<host>-<org>/<repo>` shape this machine uses is the unusual one. That makes
it a portability defect rather than a local one, and this repo publishes the skill.]
