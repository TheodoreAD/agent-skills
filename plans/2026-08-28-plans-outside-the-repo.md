---
status: in-progress
updated: 2026-08-28
depends_on: [power-user-linux-setup]
---

## Context

`plan-docs` assumed a plan can be committed to the repo it is about. That holds for the personal
family and fails everywhere else: most of the repos this user works in belong to an employer or a
client, where adding a `plans/` directory is not available — the repo is large, under review
pressure, and not theirs to shape. The planning still happens; it just had nowhere to live, so it
evaporated with the session.

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
mirrors the full relative path at whatever depth the repo actually sits.

[DECISION: **This is a parallel path, not a rework.** Settled with the user 2026-08-28: the personal
family's per-repo `plans/` stays exactly as it is, all 56 files stay put, and nothing migrates. The
store exists only for repos that cannot hold their own plans. The discovery-vs-relocation question
in `plans/2026-08-28-cross-repo-plan-store.md` is unaffected and still answered "discovery" for the
personal family — this is a third case neither branch of that plan covered.]

[DECISION: **A capability of `plan-docs`, not a new skill.** Everything except location is identical
(status vocabulary, tags, promotion, retirement, the deletion gate); a sibling skill's `description`
would have to be about creating and tracking plans, which is `plan-docs`' description nearly
verbatim, and this repo's `AGENTS.md` says trigger contention is fixed by redrawing the boundary
rather than by wording; and the trigger can only be evaluated from inside the other skill's flow — a
session learns the repo can't hold a plan when it goes to write one. The machine-specific half is
declared in the skill the way `research-library` declares `$RESEARCH_HOME`.]

Full reasoning for the decisions below now lives in
[`skills/plan-docs/references/design-rationale.md`](../skills/plan-docs/references/design-rationale.md)
§ "Where a plan lives: the repo, or the store outside it" — this file keeps only what is still live.

## Design

### 1. Routing config — `~/.config/plan-docs/config.toml`

XDG path, `$PLAN_DOCS_CONFIG` overriding it (which is also what the tests use, so no test can touch
the real one). Three modes per repo — `repo`, `store`, `both` — where `both` carries an explicit
`write` target, because switching is a state and it runs in both directions: a repo leaving in-repo
plans behind (`{ mode = "both", write = "store" }`) and one adopting them
(`{ mode = "both", write = "repo" }`) must both keep reading what is already filed.

Precedence: exact `[repos]` entry → longest `[roots]` prefix → `default` → no answer.

[DECISION: **An unmatched repo asks; it does not fall back.** Settled with the user 2026-08-28.
`plans.py where` exits 3 with `verdict: needs-decision` when no rule matches and no `default` is
set. Both silent answers fail invisibly — guessing `repo` creates a directory inside someone else's
repository, guessing `store` files the plan somewhere the user never named. The answer is written to
config, so the question is asked once per repo, not once per session.]

### 2. Store layout — `$PLANS_HOME`, default `~/plans`

`<store>/<repo's path under projects_root>`, at full depth, computed from
`git rev-parse --show-toplevel` rather than from cwd so a subdirectory resolves identically. The
root directory names already encode host and organisation: no slug function, no origin-URL parsing,
no collision between two clients' `api`.

[DECISION: **Frontmatter carries the origin URL, not the path.** The store path is already the
file's own location, so a `repo:` field repeating it would be a second copy of one fact — two fields
that can disagree. The origin URL is the identity location cannot express: it survives the clone
being moved or renamed. Falls back to the relative path when a repo has no `origin`.]

[DECISION: **Local git, no remote, ever by default.** `init-store` runs `git init`, writes the
README, never adds a remote, and warns if one exists. Local history is the whole benefit and carries
no disclosure risk; one personal remote accumulating several employers' internal architecture is the
specific outcome designed against. Never symlinked into a work repo, for the reason
`research-library` already states. Treated as unbacked-up.]

[DEFERRED: per-root sync. A remote for one root, against that employer's actual sanctioned
destination and policy, stays wanted and unbuilt — the store is local-only until a specific root has
a specific answer.]

[DEFERRED: what happens when an engagement ends. A client root's subtree becomes dead weight and
possibly material that should not be retained at all; the options are delete the subtree, archive it
out of the store, or leave it. This is the one question with a legal dimension rather than a design
one, and it should be answered before the store accumulates years of it. Nothing in the
implementation depends on it — the store is a plain directory tree, so any of the three remains
available.]

### 3. `skills/plan-docs/scripts/plans.py` — the deterministic half

Stdlib, read-only except where stated. `where`, `new`, `list`, `tags`, `set-status`, `move`, `refs`,
`config`, `init-store`. Everything routing touches is a path computation, a frontmatter rewrite, an
anchored grep, or a gate that is a grep returning empty — as prose each costs an agent several file
reads and gets the anchoring subtly wrong; as a command each is one call whose output is the answer.

`set-status` enforces the two gates the convention previously only described: `planned` refuses
while a `[NEEDS CLARIFICATION:` remains, `landed` while an `[UNVERIFIED:` does.

### 4. Where the routing rule fires from

From the skill, via the script: `plans.py where` is the entry point, and its exit 3 is what forces
the question rather than a rule someone has to remember.

[DEFERRED: a one-line pointer in the always-loaded instructions file, for sessions that write a plan
without loading `plan-docs`. That file belongs to `power-user-linux-setup`, and its
`plans/2026-08-28-pulse-capture.md` has the same `portable.md`-vs-`this-setup.md` question about its
own routing rule; decide both there, together, not here.]

### 5. Machine setup (`power-user-linux-setup`)

A `[packages.plan-store]` entry exporting `PLANS_HOME` from `zshenv`, mirroring
`[packages.research-library]` exactly, plus whatever owns the store's git identity: this machine has
no global `user.name`/`user.email` — identity comes from `includeIf` rules per project root — and
`~/plans` sits outside all of them, so a fresh store cannot commit until one is set.

## Files touched

- `skills/plan-docs/scripts/plans.py` — new; routing, creation, index, tags, gates, references.
- `tests/unit/test_plan_store.py` — new; 29 tests against a fake `$HOME` and projects root.
- `skills/plan-docs/SKILL.md` — command list up front, routing section, environment assumptions,
  every mechanical step repointed at the script; `description` extended with the store triggers.
- `skills/plan-docs/references/design-rationale.md` — new section carrying the reasoning.
- `README.md` — the skill row, and the corrected claim about skills reaching outside the repo.
- `~/.config/plan-docs/config.toml`, `~/plans` — this machine, not this repo.

## Verification

Done 2026-08-28, all green:

- `inv quality.precommit` — 80 tests pass, ruff/basedpyright/dprint clean.
- Real-corpus read-only run of `list`, `tags --tag DECISION` and `refs` over this repo's own four
  plans: correct statuses, correct per-file tag counts, both inbound references to
  `2026-08-28-cross-repo-plan-store.md` found.
- `where` against a real depth-3 work clone (root/project/repo) resolves to the mirrored store path,
  confirming the depth measurement above is actually handled.
- This machine's config and store created: `default = "store"`, `github.com-personal = "repo"`,
  `~/plans` initialized as git with no remote and one commit.

[DEFERRED: the `[packages.plan-store]` entry in `power-user-linux-setup` (§5). Until it lands,
`PLANS_HOME` is unset and the script's `~/plans` default is what makes the store resolve — correct,
but undeclared to anything else on the machine.]
