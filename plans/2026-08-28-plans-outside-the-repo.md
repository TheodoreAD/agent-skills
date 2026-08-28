---
status: idea
updated: 2026-08-28
depends_on: [power-user-linux-setup]
---

## Context

`plan-docs` assumes a plan can be committed to the repo it is about. That holds for the personal
family and fails everywhere else: most of the repos this user works in belong to an employer or a
client, where adding a `plans/` directory is not available — the repo is large, under review
pressure, and not theirs to shape. The planning still happens; it just has nowhere to live, so it
evaporates with the session.

Measured 2026-08-28, `~/projects`:

| root                  | repos at depth 1 | at depth 2 |
| --------------------- | ---------------- | ---------- |
| `github.com-personal` | 22               | 1          |
| work root A           | 22               | 1          |
| work root B           | 7                | 0          |
| work root C           | 4                | 3          |
| work root D           | 4                | 0          |
| work root E           | 3                | 0          |
| work root F           | 2                | 0          |
| work root G           | 2                | 0          |

Seven of the eight roots are employer or client work. **No repo outside `github.com-personal` has a
`plans/` directory today**, so this is a clean adoption with nothing to unwind.

**Repos are not uniformly one level under a root.** Three roots hold repos at depth 2 — a
Bitbucket-style `<project>/<repo>` hierarchy in two work roots, and a grouping directory under
`github.com-personal/exercise/`. Any "mirror `<root>/<repo>`" rule breaks on those; the store path
has to mirror the full relative path at whatever depth the repo actually sits.

[DECISION: **This is a parallel path, not a rework.** Settled with the user 2026-08-28: the personal
family's per-repo `plans/` stays exactly as it is, all 56 files stay put, and nothing migrates. The
store exists only for repos that cannot hold their own plans. The discovery-vs-relocation question
in `plans/2026-08-28-cross-repo-plan-store.md` is unaffected and still answered "discovery" for the
personal family — this is a third case neither branch of that plan covered.]

## Open questions

[NEEDS CLARIFICATION: **a new skill, or a capability of `plan-docs`?** The user's own framing, and
the decision this plan exists to make. The case for extending `plan-docs` looks stronger on three
independent grounds, but it should be decided rather than defaulted:

1. **Everything except location is identical.** Status vocabulary, tags, the promotion gate, the
   retirement procedure, the deletion gate — all apply unchanged. A separate skill either restates
   them or cross-references a skill the agent may not have loaded.
2. **Trigger contention is close to unavoidable.** A new skill's `description` would have to be
   about creating and tracking plans, which is `plan-docs`' description nearly verbatim. Two
   descriptions matching "write a plan for this" is the exact failure this repo's `AGENTS.md` says
   to design against, and it is unresolvable by wording — the boundary would have to be redrawn,
   which is the same as not splitting.
3. **The trigger can only be evaluated from inside the other skill's flow.** A session does not know
   at prompt time that this repo can't hold a plan; it finds out when it goes to write one. A skill
   whose trigger fires only after another skill has already loaded is a branch in that skill, not a
   sibling of it.

The case against: the machine-specific half — `$PLANS_HOME`, the `~/projects` mirroring — fails this
repo's "every skill has to work for someone who has only this repo" bar unless declared, and folding
it into `plan-docs` puts a machine assumption inside the family's most-used skill. That is real, and
the answer is the `research-library` shape: declare the assumption in the skill rather than hide it.
`research-library` became publishable exactly that way.]

[NEEDS CLARIFICATION: **where does the routing rule fire from?** If it lives only in `plan-docs`, it
reaches a session that loaded that skill — which is most planning sessions, but not one that writes
a plan without invoking it. `~/AGENTS.md` is always loaded and would catch the rest, at the cost of
a rule naming a specific directory layout in the always-loaded file. `power-user-linux-setup`'s
`plans/2026-08-28-pulse-capture.md` has the same question about its own routing rule and the same
`portable.md`-vs-`this-setup.md` tension; decide both together.]

[NEEDS CLARIFICATION: **does the store sync, and at what granularity?** Local-only git gives history
with no disclosure risk and no setup. A remote gives durability across a machine loss, which is the
whole reason this user version-controls anything. But one personal remote holding several employers'
material at once is not an option, so a remote implies per-root remotes and per-root policy checks.
Lean local-only until a specific root has a specific sanctioned destination.]

[NEEDS CLARIFICATION: **what identifies the repo in frontmatter — clone path or origin URL?** The
path is what the routing rule already computes and needs no lookup; the origin URL survives the
directory being moved or renamed, and is what a human reads to know which repo is meant. Both is
cheap and probably right, but two fields that can disagree is exactly the rot `plan-docs` warns
about elsewhere.]

[NEEDS CLARIFICATION: **what happens when an engagement ends?** A client root's plans become dead
weight, and possibly material that should not be retained at all. Options: delete the root's
subtree, archive it out of the store, or leave it. This is the one question with a legal dimension
rather than a design one, and it should be answered before the store accumulates years of it.]

## Recommended direction

### Layout — mirror the repo's path under `~/projects`, at whatever depth

```
~/plans/
  README.md
  <relative path of the repo root under ~/projects>/
    YYYY-MM-DD-topic.md
    decisions/<topic>.md
```

So a `~/projects/<work root>/<project>/<repo>/` clone gets
`~/plans/<work root>/<project>/<repo>/`, and a depth-1 repo gets a depth-1 store
path. The existing root directory names already encode host and organisation, so there is nothing to
invent: no slug function, no origin-URL parsing, and no collision when two clients both have a repo
called `api`.

**Compute the path from the repo root, never from cwd** — `git rev-parse --show-toplevel`, then its
path relative to `~/projects`. Working in a subdirectory must land in the same store directory as
working at the root, and the depth-2 measurement above is why a fixed-depth rule cannot do this.

`export PLANS_HOME="${HOME}/plans"` from a `[packages.plan-store]` entry in
`power-user-linux-setup`, mirroring `[packages.research-library]`'s `zshenv` export exactly.

### Routing

- repo under `github.com-personal/` → its own committed `plans/`, unchanged
- any other root → `$PLANS_HOME/<relative path>`
- not under `~/projects` → ask

Key it off the root rather than off whether `plans/` already exists: a **new** personal repo has no
`plans/` yet and would otherwise route to the store on its first plan. An escape hatch either way (a
personal repo that shouldn't carry plans, a client repo that welcomes them) is a per-repo override,
not a change to the rule.

### What `plan-docs` gains, if that is the route

One section, and nothing else changes:

- the routing rule above, with its environment assumption declared the way `research-library`
  declares `$RESEARCH_HOME`
- frontmatter gains a field naming the repo, because location no longer implies it — the one thing
  the in-repo case gets for free
- the **design rationale** role from "Where retired content goes" maps to `<repo>/decisions/` in the
  store, which the 2026-08-28 roles change already made expressible without naming a path

Status, tags, promotion, retirement, the deletion gate: shared, untouched, no restatement.

### Handling of client and employer material

This is the part to settle before the first file is written, not after.

The store must be a git repository with **no remote configured by default**. Local history is the
entire benefit and carries no disclosure risk; pushing is a separate, deliberate decision made per
root against that employer's actual policy. A single personal remote accumulating several clients'
internal architecture, ticket references and code excerpts is the specific outcome to design
against, and it is the default outcome if a remote is added casually.

Never symlink the store, or any subtree of it, into a work repo — the same rule `research-library`
already states, for the same reason: it would put the content back inside a tree that repo-scoped
agent reads walk, which is what keeping it outside every repo exists to prevent.

Treat it as unbacked-up unless something is arranged deliberately, exactly as
`~/.config/power-user-linux-setup/overrides.toml` already is.

### Prior art

`beads` reached the same shape independently and is the closest precedent in the whole survey behind
`plans/2026-08-28-cross-repo-plan-store.md`: `bd init --contributor` routes planning issues to a
store outside the repo (`~/.beads-planning`) specifically so experimental work never appears in a PR
to a repo you do not own, and `BEADS_DIR` overrides repo discovery entirely. Its own guidance — "you
DON'T need multi-repo if working solo on your own project… all issues belong in the project's git
history" — is the argument for keeping this a parallel path rather than the default, which is what
the decision above already settles.
