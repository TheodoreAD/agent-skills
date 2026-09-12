---
status: landed
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

## Design

### 1. One command, two destinations

```shell
python3 <path> attach <plan> <file>...            # size decides
python3 <path> attach <plan> <file>... --commit   # this is evidence someone will read
python3 <path> attach <plan> <file>... --local    # this is bulk, or must stay byte-exact
```

1. **committed** — `<the plan's directory>/<the plan's stem>/<name>`, a sibling directory named for
   the plan, inside whichever git repository already holds that plan.
2. **local only** — `<the store for that repo's tier>/_attachments/<rel>/<the plan's stem>/<name>`,
   where `rel` is the repo's path under the projects root, or `_unscoped`.

[DECISION: **local attachments live in the store, not beside the plan.** Outside every working tree,
so a `git clean -X`, a removed worktree or a branch switch cannot take them; keyed on repo path plus
plan stem, neither of which changes when a plan moves between the repo and the store, so absorption
never has to move bytes; and the tier lookup already answers which store, so a sensitive root's
evidence cannot land in the half that may have a remote. The exclusion goes in the store's
`.git/info/exclude` rather than a committed `.gitignore`, because it is a machine-local fact about a
machine-local directory and committing it would write a rule into the store's history for a path no
clone of it will ever have.]

A destination that already exists is **refused**, never overwritten and never renamed around — the
same answer `_take_plans` gives a name collision, and for the same reason: two files claiming one
name is a question for a person.

### 2. Size picks the default, a flag overrides it, one configurable number

[DECISION: **one threshold everywhere, `[attachments] commit_limit_kb`, default 1024.** Settled with
the user 2026-09-12 against deriving it from whether the store has a sanctioned remote. Deriving is
more accurate — committing is only more durable than local when something actually receives the push
— and it makes the threshold move when an unrelated key changes, which is the kind of coupling
nobody remembers. One number, changeable per machine, is explainable in a sentence: raise it on a
box whose store pushes somewhere you trust.]

The script cannot see _use_; the agent can, which is what `--commit` and `--local` are for. The
skill states the rule in one line: evidence someone will read goes committed, bulk output and
anything that must stay byte-exact goes local.

### 3. What the plan records

An `## Attachments` section, written by the script rather than by hand — the same argument as
`new`'s skeleton and `set-status`' two frontmatter lines. One row per file: name, destination, size,
the date, a sha256 for a local attachment, and the directory a local one lives in.

[DECISION: **the source path is never recorded.** Independence from where the file came from is the
whole request, and a source path can carry a client directory name or a username into a published
repo in a line nobody reads twice. The digest is what lets a later reader tell the cited file from a
different file of the same name; for the committed half, git already answers that.]

### 4. Durability of the local half: said, not solved

[DECISION: **`attach` states that a local copy is the only one, and nothing else pretends to fix
it.** Settled with the user 2026-09-12. The alternatives were copying to a second destination —
which invents the destination `2026-08-29-sensitive-tier-durability.md` has deliberately not chosen,
and every copy made for durability is one to find and destroy if an engagement ends — or refusing
local attachments until a durable destination exists, which blocks the feature on exactly the
machine that asked for it. So the output says it at the moment it writes the file, the plan's own
row says `local
only`, and the gap stays owned by the plan that already owns it, where a destination
gets chosen once for everything.]

Retirement keeps its shape. A committed attachment is deleted with the plan and stays reachable in
the same history `archive` already reads. A local one is **listed** at retirement and never deleted
automatically: it is not in git, so deleting it is the one irreversible step in a procedure built
entirely around being reversible.

### 5. The five assumptions that have to change

`is_plan_path` stops counting a file inside a plan-stem directory, or anywhere under `_attachments`,
as a plan — by excluding those two shapes rather than by requiring a date-prefixed name, so a legacy
plan with an older filename is still found by `archive`. `_take_plans`, `move` and `graduate` carry
the sibling directory with the plan, refusing when the destination already has one. `commit <plan>`
includes that plan's own sibling directory — bounded to the plan being named, which is not the
whole-directory form that was refused. `misfiled_plans` skips the attachments root the way it skips
`_unscoped`. `uninstall`'s plan count ignores it.

[PITFALL: **a committed attachment is an ordinary file in that repository and goes through its
gate.** `dprint` reflows markdown, so an investigation report committed as `.md` stops being
byte-exact the first time the gate runs — silently, because the gate rewrites it and passes. That is
the concrete reason `--local` exists for things that must stay verbatim.]

[PITFALL: **`scan` sees a committed attachment and cannot see a local one.** A log copied into a
repo is scanned for private names like any other tracked file, which is right. A local one is
outside every working tree, so a client name inside it is never flagged — and never published
either, which is what makes that acceptable rather than a hole. Worth saying in the skill so the
asymmetry is not discovered as a bug.]

Prior art, at knowledge depth rather than from a clone: Obsidian's "subfolder under current folder"
attachment setting and Hugo's page bundles are the same sibling-directory shape. `git-annex`,
`git-lfs` and DVC all solve the large-file half properly and are all refused by this skill's
stdlib-only, no-install constraint — and LFS would still push the bytes it exists to keep out of the
history.

## Files touched

- `skills/plan-docs/scripts/plans.py` — the `attach` command and its destination logic; the
  `## Attachments` writer; the `[attachments]` config table and its `config set` validation; the
  five behaviours in section 5.
- `skills/plan-docs/SKILL.md` — a section on attaching evidence, the commit-or-local rule, the two
  pitfalls, and the disclosure block, which must gain the paths this writes and the
  `.git/info/exclude` line it maintains.
- `skills/plan-docs/references/design-rationale.md` — why the local half lives in the store, why the
  threshold is one configurable number, and why durability is stated rather than solved.
- `tests/unit/test_plan_store.py` — see below.

## Verification

New tests: a small file lands beside the plan and is recorded; a file over the limit lands in the
store's attachments area with a digest, and the output says it is the only copy; `--commit` and
`--local` override the size; a collision is refused; `absorb` and `move` carry the sibling
directory; `archive` does not report an attached `.md` as a retired plan; `misfiled_plans` ignores
the attachments root; `commit <plan>` includes the sibling directory; an unscoped plan keys under
`_unscoped`; `config set attachments.commit_limit_kb` validates.

Then the real thing: attach an agent's investigation report and a multi-megabyte log to a live plan
on this machine, and check the plan reads correctly, the gate passes, and `plans.py commit` carries
what it should.

Run 2026-09-12 against a real repo and a real store in a throwaway `$HOME`, one command per step: a
46-byte report was committed beside the plan and a 3 MB log went to the store's attachments area;
the sha256 in the plan's row matched `sha256sum` on the file; `git status` in the store stayed
clean, because `install`'s exclude line covers the area; `commit <plan>` carried the plan and the
report and nothing else, under one message; `refs` named both halves with the local one marked
final; and `move --to store` carried the committed directory while the local one stayed where its
key puts it. Nothing in the real store or the projects tree was touched.

## Migrated to

- `skills/plan-docs/references/design-rationale.md`, "Why a plan's evidence has two homes, and the
  split is size (2026-09-12)" — the four `DECISION`s, why the local half lives in the store rather
  than beside the plan or under an XDG directory, the large-file tools this skill's constraints rule
  out, and why durability is stated rather than solved.
- `skills/plan-docs/SKILL.md`, "Attaching evidence to a plan" — the command, the table that decides
  which half a file belongs in, both `PITFALL`s, the rule that attachments travel with their plan,
  the disclosure block, and the retirement line in step 3 of "Retiring a plan".
- `skills/plan-docs/scripts/plans.py` with `tests/unit/test_plan_store.py` — `attach`, the
  `[attachments]` key, the five behaviours that assumed one plan is one markdown file, and their
  tests.

Deliberately not migrated: the file-and-line inventory of what would break. It was the map for doing
the work, every entry on it is now either code or a test that fails without it, and a list of line
numbers is wrong within a week.
