---
status: idea
updated: 2026-09-12
---

# Attaching logs, reports and other outputs to a plan

## Context

Asked by the user 2026-09-12: _"we have no way to attach logs or other large output to docs using
plan docs, we need a way to tell the skill 'here are a bunch of outputs, copy them somewhere stable
so we don't depend on the original ones that might be in downloads or other ephemeral locations'.
Whether these should be committed, not sure, probably should depend on size and use, such as an
other agent's investigation would be useful to commit, but large logs or data dumps could be
avoided."_

Nothing in the convention handles this today. `new --for` writes an `## Evidence` section of prose,
and the four provenance fields it emits point at a harness transcript the skill itself says survives
only about 30 days — so the one evidence pointer the convention has is already ephemeral by design.
A plan citing a path under `~/Downloads` is worse than that: no stated expiry, just a file that
stops existing while the sentence naming it still reads as true.

Settled with the user in the same exchange: **split by size, with an explicit override.**

## What the corpus already does, and what this must not break

Read 2026-09-12, with the line numbers that matter:

- `plans_in` globs `*.md` **non-recursively** (`plans.py:1233`), and `family_plans` is built on it
  (`1264`). A per-plan sibling directory is therefore invisible to `list`, `absorb` and family
  scope, which is the fact that makes "next to the plan" viable at all.
- `is_plan_path` (`1889`), which `deleted_plans` (`1900`) filters on, counts **any** `.md` under the
  prefix as a plan. Deleting an attached report would show up in `archive` as a retired plan.
- `_take_plans` (`3170`), `cmd_move` (`3196`) and `cmd_graduate` (`3758`) move the `.md` and nothing
  else, so an absorbed plan would leave its attachments behind in the store.
- `misfiled_plans` (`4076`) walks the store's top-level directories and would report an attachments
  root as a root filed in the wrong tier, unless it is skipped the way `_unscoped` is.
- `cmd_uninstall` (`4389`) counts `rglob("*.md")` as plan files, so its refusal message would
  over-count. Cosmetic, but it is the message that guards an irreversible delete.
- `commit_paths` takes files, and a directory argument is refused deliberately — the whole-directory
  form was considered and rejected because it makes it easy to sweep a file the session never
  touched.
- `dprint` reflows committed markdown (`dprint.json`: markdown `textWrap: always`, `lineWidth 100`).
  `.log` and `.txt` are untouched.

## Recommended direction

`python3 <path> attach <plan> <file>... [--commit | --local]`, with two destinations:

1. **committed** — `<the plan's directory>/<the plan's stem>/<name>`, a sibling directory named for
   the plan, inside whichever git repository already holds that plan.
2. **local only** — `<the store for that repo's tier>/_attachments/<rel>/<the plan's stem>/<name>`,
   excluded through the store's `.git/info/exclude`.

[DECISION: **local attachments live in the store, not beside the plan.** Outside every working tree,
so a `git clean -X`, a removed worktree or a branch switch cannot take them; keyed on repo path plus
plan stem, neither of which changes when a plan moves between the repo and the store, so absorption
never has to move bytes; and the tier lookup already answers which store, so a sensitive root's
evidence cannot land in the half that may have a remote. `.git/info/exclude` rather than a committed
`.gitignore` because the exclusion is a machine-local fact about a machine-local directory, and
committing it would write a rule into the store's history for a path no clone of it will ever have.]

[DECISION: **size picks the default, use overrides it, and the skill says which is which.** The
script cannot see use; the agent can. 1 MiB per file as the line — an agent's investigation report
measures in tens of kilobytes and a screenshot in hundreds, while logs and dumps cross it — with
`--commit` and `--local` overriding per call.]

[DECISION: **the plan records name, size, destination, date, and a sha256 for a local attachment —
never the source path.** Independence from where the file came from is the whole request, and a
source path can carry a client directory name or a username into a published repo in a line nobody
reads twice. The digest is what lets a later reader tell the cited file from a different file of the
same name; for the committed half git already answers that.]

The section is `## Attachments`, written by the script rather than by hand, on the same argument as
`new`'s skeleton and `set-status`' two frontmatter lines: anything mechanical that a rule would
otherwise ask an agent to spell correctly every time.

Five existing behaviours change with it: `is_plan_path` learns the plan filename shape so an
attachment is never reported as a retired plan; `_take_plans`, `move` and `graduate` carry the
sibling directory with the plan; `commit <plan>` includes that plan's own sibling directory, bounded
to the plan being named rather than reopening the whole-directory form that was refused;
`misfiled_plans` skips the attachments root; and `uninstall`'s count ignores it.

Retirement keeps its shape. A committed attachment is deleted with the plan and stays reachable in
the same history `archive` already reads. A local one is **listed** at retirement and never deleted
automatically: it is not in git, so deleting it is the one irreversible step in a procedure built
entirely around being reversible.

[PITFALL: **a committed attachment is an ordinary file in that repository and goes through its
gate.** `dprint` reflows markdown, so an investigation report committed as `.md` stops being
byte-exact the first time the gate runs — silently, because the gate rewrites it and passes. The
rule that follows is worth stating in the skill: evidence that must stay verbatim goes local,
evidence that is meant to be read goes committed.]

Prior art, at knowledge depth rather than from a clone: Obsidian's "subfolder under current folder"
attachment setting and Hugo's page bundles are the same sibling-directory shape. `git-annex`,
`git-lfs` and DVC all solve the large-file half properly and are all refused by this skill's
stdlib-only, no-install constraint — and LFS would still push the bytes it exists to keep out of the
history.

## Open questions

[NEEDS CLARIFICATION: **whether a local attachment needs durability at all.** It lives on one disk,
and on a contractor device it lives in the tier that deliberately has no remote — so a plan can now
cite something whose only copy is local, which is the gap `2026-08-29-sensitive-tier-durability.md`
already holds open, made one step wider. Either the attach output says so at the moment it writes
the file, or the attachments area becomes part of whatever destination that plan eventually
settles.]

[NEEDS CLARIFICATION: **whether the size threshold should differ on a work device.** Part of the
reason to keep bytes out of git is that they get pushed — but on a work device the store's remote is
a sanctioned corporate repository, which is a real backup and usually tolerant of large files, so
committing a 20 MB log there may be better than keeping it local and unbacked. The alternative is
one number everywhere: simpler to explain, and wrong in a different direction on each device.]
