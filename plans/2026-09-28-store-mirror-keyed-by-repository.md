---
status: in-progress
updated: 2026-09-28
---

# Store mirror keyed by repository

## Context

Asked for by the user 2026-09-28: parallel checkouts of one repository — separate clones, not
worktrees — each get their own directory in the plans store, so a plan written from one checkout is
invisible from the others. Plan-conveyor should identify a project by the repository, not by where a
clone of it happens to sit.

**Why it happens.** `resolve()` in `scripts/plans.py` keys the store mirror on the checkout's path
under `projects_root`. The 2026-09-04 fix already moved a _linked worktree_ onto its main checkout
(`linked_worktree_of(root) or root`), and its comment states the principle — "the store mirror is
keyed on the REPOSITORY, never on this particular checkout". A second clone has its own `.git`, so
that step cannot see it, and it gets a mirror of its own. `list --all` has the same assumption from
the other side: it walks the clones under `projects_root` and derives each store directory from a
clone path, so a store directory with no clone at that exact path is never listed at all.
`references/design-rationale.md`'s "Why the store mirrors the clone path" chose the path on purpose
("no slug function, no origin-URL parsing") and did not consider two clones of one repository.

**Measured on this machine 2026-09-28** with `plans.py orgs --repos` and a remote read per clone,
described by shape because every instance is under a work root:

- one work root holds **three clones of one repository**, each inside a wrapper directory named for
  what that checkout is for: `<root>/<repo>-<purpose>/<repo>`, all with the same `origin`.
- a second work root holds **two clones of one repository**, `<root>/<repo>` and
  `<root>/_tests/<repo>`, with the same `origin`.
- six clones have no remote at all.
- neither affected root has a mirror in the store yet, so nothing needs migrating for these cases.

**What already exists.** Every store-held plan carries `repo:` frontmatter — every one on this
machine holds the origin URL (19 of 19 at the first count, 12 of 12 later the same day, after
another session absorbed some), and a clone with no remote gets its path there instead
(`write_plan`, and the `migrate`/`move` paths). `parse_remote` normalises ssh, scp-like and https
spellings to `host / owner / name`, and returns None for a local path or `file://`.

## Direction: an explicit link table, not a path convention

Set by the user 2026-09-28: **the store must not rely on a store directory being 1:1 with a projects
path. The link from a repository to its store directory is configuration, recorded and
unambiguous.** Of the three naming shapes considered (directory named for the remote; path layout
with a recorded link; root plus remote path), the path layout with a recorded link was chosen. A
directory keeps a human-readable path-shaped name, and the name carries no meaning — the link does.

### Identity: what a clone is

In order, first answer wins:

1. **The remote**, normalised by `parse_remote` to `<host>/<owner>/<repo>`, spelling kept — so
   `git@github.com:acme-corp/billing.git` and `https://github.com/acme-corp/billing` are both
   `github.com/acme-corp/billing`, and a clone typed `Acme-Corp/billing` matches it because remote
   identities compare ignoring letter case (see "Case" below). Which remote is decided below, under
   "No `origin`".
2. **No remote: the root commit**, `local:<first 12 of the root commit's sha>`. Every clone of a
   repository shares it, including a clone of a clone whose origin is a local path, and it survives
   the clone being moved or renamed. A `file://` path would not: it differs per clone and changes on
   a move, which is the exact failure this plan removes. With several root commits (merged
   histories), take the lexically smallest.
3. **No commits yet: `file://<absolute clone path>`** — the only case with no better answer, and the
   one a first commit replaces. Relinking then goes through the rules below.

A linked worktree resolves to its main checkout first, as today.

### The link table

One file per store tier, `<store>/repos.toml`, committed in that store:

```toml
# identity = directory, relative to this store
"github.com/acme-corp/billing" = "github.com-acme/billing"
"github.com/acme-corp/billing-legacy" = "github.com-acme/billing" # alias: renamed upstream
"local:a1b2c3d4e5f6" = "github.com-acme/playground"
```

[DECISION: **in the store, not in `~/.config/plan-conveyor/config.toml`.** The table describes the
store's own layout and has to travel with it: a store pulled on a second machine is useless without
its links, and the config file is per machine by design (SKILL.md: "a second machine with a
different set of clones needs a different file"). The config keeps routing policy, and the store
keeps what is in it.]

[DECISION: **one table per tier.** An identity from a sensitive root never enters the shareable
store's table, because the shareable tier has a remote.]

The rules the table has to keep, checked by `doctor`:

- an identity maps to exactly one directory, while a directory may carry several identities
  (aliases, for a renamed remote or a fork deliberately merged with its upstream);
- every store directory holding plans is in the table, so a directory left out is reported as an
  orphan rather than silently unlisted;
- every plan's `repo:` names an identity linked to the directory the plan sits in.

### Lookup

**From a session in a clone** (`new`, `list`, `absorb`, `set-status` — everything that goes through
`resolve()`):

1. `git rev-parse --show-toplevel`, then from a worktree to its main checkout.
2. Compute the identity as above.
3. Look it up in **both** tiers' tables. Found: that directory, in that tier. The clone's own path
   no longer decides anything here, so a clone outside `projects_root` resolves too.
4. Not found: the path rules decide the tier, as today, and the clone's path under `projects_root`
   names a new directory. The link is written to that tier's `repos.toml`, and the new `repos.toml`
   is committed together with the first plan.
5. Not found, **but** the step 4 name is already a directory linked to a different identity, or this
   clone's root commit matches a linked `local:` identity: stop with `needs-decision`, naming both,
   and point at `plans.py link`. That is the renamed-remote and first-push case, and a silent new
   directory is the failure to avoid.

**`list --all`** iterates the tables' entries, not the clones: every linked directory is listed
whether or not a clone of it exists on this machine. Clones are matched back by identity only to
print where each one is checked out.

**`--for <x>`** accepts an identity, a remote URL, or a clone path; the last two are turned into an
identity first, so filing "for" any clone of a repository lands in the same directory.

### New commands

```
plans.py link                       # show this clone's identity, tier and linked directory
plans.py link --to <dir>            # link this clone's identity to an existing directory (alias)
plans.py link --rename <new-dir>    # move the linked directory, rewriting the table
plans.py link --remote <name>       # no origin: say which remote this clone's identity comes from
plans.py link --new                 # a lookup matched an old identity, but this is a new repository
plans.py link --move-to private     # move this repository's link and folder to the private store
plans.py link --dir <d> --identity <id>   # claim an orphan folder for a repository
plans.py links                      # the whole table, both tiers, with orphans and clone locations
plans.py links fix [--yes] [--prune-empty]   # propose (default) or apply the Migration repairs
plans.py links merge <dir> --into <dir>   # fold one repository's second folder into its first
```

## Worked examples (invented names)

Setup: `projects_root = ~/projects`, a sensitive root `github.com-acme` whose remote owner is
`acme-corp`, stores `~/plans` and `~/plans-sensitive`.

1. **Wrapper-directory clones.** `billing`, `billing-hotfix/billing`, `_scratch/billing`, all
   `origin = git@github.com:acme-corp/billing.git`. The first `new` runs from the hotfix clone and
   finds no link. It creates `~/plans-sensitive/github.com-acme/billing-hotfix/billing/` and links
   `github.com/acme-corp/billing` to it. Every later session in any of the three clones resolves
   there. `link --rename github.com-acme/billing` tidies the name once; nothing else changes.
2. **A clone is moved.** `mv ~/projects/github.com-acme/billing ~/projects/archive/billing`. Same
   identity, same directory, no action. Today it would silently start a second mirror.
3. **A local-only repo gets a second clone.** `playground` has no remote, root commit
   `a1b2c3d4e5f6…`, linked as `local:a1b2c3d4e5f6`.
   `git clone ~/projects/github.com-acme/playground playground-exp` gives the copy a local-path
   origin, which `parse_remote` rejects, so it falls to the root commit: same identity, same
   directory.
4. **That repo is pushed for the first time.** Adding `origin = github.com/acme-corp/playground`
   changes the identity, so the lookup misses. But the root commit matches the linked
   `local:a1b2c3d4e5f6`, so `resolve` stops and asks. `link --to github.com-acme/playground` adds
   the new identity as an alias, and the old one can then be dropped.
5. **Upstream renames the repo.** `billing` becomes `billing-service` and `origin` is updated. A
   miss, and step 5 of the lookup catches it: the would-be directory is already linked to
   `github.com/acme-corp/billing`. `link --to` records the alias. Plans keep their directory, and
   their old `repo:` values stay valid through the alias.
6. **A fork and its upstream.** `github.com/me/billing` and `github.com/acme-corp/billing` are two
   identities and get two directories, which is right by default. Merging them is one `link --to`, a
   deliberate act.
7. **Same repo name in two projects.** Bitbucket-style `PAY/ledger` and `OPS/ledger` have different
   identities, so two directories named after their clone paths, and no collision.
8. **Second machine.** The shareable store is pulled on a laptop where `agent-skills` is checked out
   at `~/code/agent-skills`, outside `projects_root`. The identity is found in the table, so it
   resolves to `github.com-personal/agent-skills` anyway.

## Settled 2026-09-28

All three were answered by the user the same day, accepting the recommendations below. That answer
came with two requirements: **handling letter case without creating a clash**, and **messages a user
can act on without knowing the implementation**, especially for the store refusal. Both are
specified below and under "Messages".

### 1. What `repo:` holds

[DECISION: **the normalised identity, spelling kept, compared ignoring case.**

Today it is the raw `origin` URL (`git@github.com:TheodoreAD/agent-skills.git`), or the clone path
when there is no remote. **Nothing reads it**: in `plans.py` it is only written (`write_plan`, the
`move`/`migrate` paths) and stripped when a plan moves into a repo. So the format is free to change
with no consumer to break.

A raw URL records how _one clone_ was made, not which repository it is. Two clones of one repo can
disagree on the transport (`git@github.com:acme-corp/billing.git` from an ssh clone,
`https://github.com/acme-corp/billing` from an https one), and Bitbucket Server adds a port and an
`ssh://` scheme. Plans in one directory would then carry two strings for one repo, so a grep for one
misses the other, and `doctor` could not compare `repo:` with the table without normalising first.

**Write the normalised identity** — the same string the table's key uses, so
`rg -i 'repo: github.com/acme-corp/billing'` over the store answers "which plans belong to this
repository" directly. The `local:` and `file://` forms go in the same field, so `repo:` becomes one
field whose value names its own kind. The existing raw values are normalised by the migration. Only
the transport is lost, and no plan needs it.

**Case: kept as spelled, compared ignoring case** — how the macOS and Windows filesystems treat file
names. `parse_remote` lowercases the host and keeps the owner's and name's case. GitHub accepts any
capitalisation in a clone URL, so `TheodoreAD/agent-skills` and `theodoread/agent-skills` can both
turn up for one repository, and an exact comparison would split it into two folders — the bug this
plan removes, reached by a different route.

- **Stored as first seen.** `repo:` and the table key keep the spelling of the clone that linked
  first (`github.com/TheodoreAD/agent-skills`), which reads as the host shows it.
- **Looked up ignoring case** for remote identities. A match that differed only in capitalisation
  prints one line, `matched github.com/TheodoreAD/agent-skills (ignoring letter case)`, so a merge
  on a host where case does matter is visible rather than silent.
- **`file://` compares exactly**, because a Linux path is case-sensitive. `local:` is hex and always
  lower, so the question never arises.
- **Two table keys that differ only in case** are reported by `doctor` and the migration as a
  decision, never merged automatically.
- Cost: a search for one repository's plans across the store needs `rg -i`, since spellings may vary
  between plans written before the table fixed one. `links` answers the question directly.

Chosen by the user 2026-09-28 over two alternatives. **Lowercasing everything** — the first decision
— gives up readability and still cannot be uniform, because `file://` must keep its case. **Exact
everywhere** is uniform but brings back the split. Measured the same day over every clone under
`projects_root`: 68 remote URLs, 63 distinct identities, **0 that differ only in case**. So nothing
here depends on the choice today, and the rule is for the clone typed from memory later.]

[UNVERIFIED: that every host this machine uses (GitHub, a Bitbucket Server instance, Azure DevOps)
matches repository paths case-insensitively. It does not block shipping — the "ignoring letter case"
note and the `doctor` check make a wrong assumption visible instead of silent — but it belongs in
the design rationale once checked.]

### 2. A clone with remotes but no `origin`

[DECISION: **`origin` if present, else whichever remote is already linked, else ask.**

Measured 2026-09-28 over every clone under `projects_root`: 65 have `origin`, 6 have no remote at
all, **0 have remotes but no `origin`**, and 3 have two or more remotes. So today this case is
hypothetical. The realistic way to get there is `git remote rename origin upstream` followed by
adding a fork as `fork`.

`remote_of` currently takes `origin`, else the lexically first remote. In that example that is
`fork`, while another clone of the same repository with `origin` pointing at upstream keys to
upstream. The result is two identities, two directories and silent disagreement: the failure this
plan exists to remove.

The rule:

1. `origin` present: it is the identity, and no other remote is consulted. A fork checkout whose
   `origin` is the fork keys to the fork, matching the "fork and upstream are separate by default"
   example above.
2. No `origin` and **exactly one** hosted remote: that remote. There is nothing to choose between,
   so asking would be a question with one answer. This refines the rule as first written, which
   asked here too; the concern was picking one of several by spelling, and one is not several.
3. No `origin` and several hosted remotes: look up **every** remote's identity in the tables. If
   exactly one is linked, use it, which is unambiguous and needs no question. If several are linked
   to different directories, stop and name them.
4. No `origin`, several remotes, and none linked yet: `needs-decision`, rather than picking one by
   spelling. `plans.py link --remote <name>` answers it by linking that remote's identity. Nothing
   per clone needs recording, because from then on step 3 finds the link.]

**Progress.** Step 1 of the recommended direction landed 2026-09-28: `clone_identity` (rules 1, 2
and 4's "cannot say" answer; step 3's table lookup belongs to `resolve()`), `identity_key`, and the
`Links` table with `read_links`/`write_links`, in `scripts/plans.py` under "repository identity",
with tests in `tests/unit/test_plan_store.py`. Nothing calls them yet, so routing is unchanged until
step 2.

Step 2 landed the same day: `resolve()` routes through `store_route()`, the first store write
records and commits the link, `repo:` holds the identity, and attachments, archive sources,
`absorbed_from` and the family listing follow the resolved folder. Verified on this machine before
committing: with no links anywhere, `list --scope family --json` is byte-identical to the installed
version's. One refinement over the design above: **a refusal stops store writes only and rides on an
ok route**, rather than being a needs-decision verdict, because the verdict also blocked `list` and
the plan says reads keep working. The `link` command (show, `--remote`, `--to`, `--new`,
`--move-to private`) landed with it, since the messages name it.

Steps 3 to 6 landed the same day: `references/store-links.md` with one section per message, the
tests that every command a message names parses and every section it cites exists, `links` (show,
`fix`, `merge`, `claim`) with `doctor` reporting the decisions, and `SKILL.md` and the rationale
rewritten. One addition over the design: `links claim <folder> <identity>`, because an orphan folder
needed a command to resolve it and the planned `link --dir --identity` would have been a second
spelling of the same act. The dry run of `links fix` on this machine is all automatic: four folders
to link, 15 `repo:` values to rewrite, five empty folders left behind by absorption.

Owed: step 7 — push, re-install, then `links fix --yes` on this machine.

### 3. The table's store and the path rule disagree

[DECISION: **the stricter store wins silently; the looser one refuses; both is corruption.**

Today the store comes from the path alone (`cfg.store_for(rel)` → `tier_of(rel)`: a root in
`public_roots` is shareable, and everything else is sensitive). With a table, a repository's store
is wherever its link sits, so a second clone under a different root can disagree. That makes this a
confidentiality question, not a tidiness one, because the shareable store has a remote. So the
answer should differ by direction, not be one rule for both:

- **Link sensitive, path shareable → use the sensitive link, with no warning.** Example: a client's
  `acme-corp/billing`, linked from its clone under the client root, is cloned a second time under
  the personal root for an experiment. The repository is the client's wherever it sits, and writing
  into the stricter store cannot leak anything. No warning, but not invisible either: `where` and
  `link` print it on the store line —
  `store: private (this repository is linked there; this
clone's own folder would have chosen shareable)`
  — so the question "why did my plan go there?" has an answer on screen.
- **Link shareable, path sensitive → refuse.** Example: an open-source library linked from a
  personal clone is also cloned under a client root because the client uses it. A plan written from
  there may carry client context, such as why the client needs a patch, and the link would send it
  to the store with a remote. The refusal names two ways out: move the whole repository's link to
  the sensitive store, or a `[repos]` entry declaring that clone path shareable, a written statement
  that client context does not apply there.
- **Identity linked in both tables → corruption**, reported by `doctor` and fatal to every write,
  since there is no safe way to pick.

This reverses the earlier lean ("the existing link wins, with a warning"), which would have allowed
the leaking direction.]

[NEEDS CLARIFICATION: the "declare this clone path shareable" way out needs a config key that does
not exist yet. Today `[repos]` entries carry `mode`/`read`/`write` and the store is decided by
`public_roots` alone. The candidate is `[repos] "<path>" = { tier = "shareable" }`, set through
`config set` like every other key. Decide its name when building it.]

### Also keyed by path, found while answering these

`Config.attachments_dir(rel, stem)` puts a plan's local-only attachments under
`<store>/_attachments/<rel>/<stem>`, keyed on the clone path too. It has to follow the link table,
or a plan resolved through a sibling clone loses sight of its own attachments.

## Messages

Required by the user 2026-09-28: whoever reads a decision or a refusal — the user months from now
included — will not remember identities, tiers or link tables. **Every message that stops a command
has the same four parts, in this order:**

1. **What was found**, in the reader's terms: the clone's path, the repository, the plans folder and
   how many plans it holds. Never an internal name alone (`identity`, `tier`, `rel`).
2. **Why it matters**, in one or two sentences.
3. **The choices**, each one a complete command that can be pasted as is, with a one-line
   consequence. A recommended choice is marked, when there is one.
4. **What happened**: always "Nothing was written" for a stop, plus a pointer to the section of
   `references/store-links.md` that explains the background, for a reader who wants more.

Two rules keep the messages from rotting, each of which has already bitten this corpus once (a
message naming a subcommand that did not exist):

- a test renders every message and asserts that each command in it **parses** against the real
  argument parser, so a renamed flag fails the suite instead of misleading a reader;
- the messages are the documented interface. `SKILL.md` names the situations and says "follow the
  message", rather than restating the choices in prose that can drift from the code.

The drafts, with invented names:

```text
plans: can't tell which repository this clone belongs to.
  clone:    ~/projects/github.com-acme/billing
  remotes:  fork      -> github.com/me/billing
            upstream  -> github.com/acme-corp/billing
  There is no remote called "origin", and neither of these has a plans folder yet. Plans are
  kept per repository, shared by every clone of it, so guessing could put this clone's plans
  somewhere its other clones never look.
  Choose one:
    plans.py link --remote upstream   # share plans with every clone of acme-corp/billing
    plans.py link --remote fork       # keep your fork's plans separate
  Nothing was written. More: references/store-links.md#which-remote
```

```text
plans: this clone looks like a repository that already has plans under another name.
  clone:        ~/projects/github.com-acme/playground
  remote now:   github.com/acme-corp/playground
  known before: local:a1b2c3d4e5f6 (same first commit), plans folder
                github.com-acme/playground, 4 plans
  This usually means the repository was pushed for the first time, or its remote changed.
  Choose one:
    plans.py link --to github.com-acme/playground   # same repository: keep its 4 plans (usual)
    plans.py link --new                             # a different repository that shares history
  Nothing was written. More: references/store-links.md#renamed-or-first-push
```

```text
plans: refused, because this plan could be published.
  clone:        ~/projects/github.com-acme/vendored-lib   (under github.com-acme, a private folder)
  repository:   github.com/someone/lib
  plans folder: ~/plans/github.com-personal/lib           (the SHAREABLE store, pushed to its remote)
  This repository's plans are kept in the shareable store, but this clone sits under a private
  folder. A plan written from here may mention private work (a client, a ticket, why they need
  a change), and the shareable store would publish it on its next push.
  Choose one:
    plans.py link --move-to private                      # ALL this repository's plans go private
    plans.py config set repos.github.com-acme/vendored-lib.tier shareable
                                                         # you confirm nothing private is written here
  Nothing was written. More: references/store-links.md#shareable-and-private
```

```text
plans: stopped, because the plans index is inconsistent.
  repository: github.com/acme-corp/billing is listed in BOTH stores:
                ~/plans/repos.toml            -> github.com-acme/billing
                ~/plans-sensitive/repos.toml  -> github.com-acme/billing
  Only one can be right, and picking one could publish private plans. No command writes plans
  for this repository until it is resolved.
    plans.py links fix     # shows both folders' contents side by side and asks which to keep
  Nothing was written. More: references/store-links.md#listed-twice
```

The messages say "private" and "shareable". The code's `sensitive` stays internal, because "private"
is the word a reader recognises. The store directory names print alongside, so nothing is hidden.

## Migration

"Migration" is really two jobs using one command: **first adoption**, building the tables from
today's path-keyed store, and **repair**, for setups that are already wrong or drift later (an old
installed `plans.py`, a hand edit, a second machine). So it is not a one-shot script. `links fix` is
idempotent and safe to re-run, `doctor` runs its read-only half on every call, and first adoption is
simply the first time it has anything to do.

### Rules it keeps

- **Nothing moves unless you choose it.** Existing folders keep their names. That keeps old
  installed copies of `plans.py`, which ignore `repos.toml`, writing to the same folders throughout
  the rollout. `skill-authoring-taudelta`'s rename pitfall is exactly an old copy looking somewhere
  new state has moved away from.
- **Dry run by default.** `links fix` prints what it would do in three groups — _automatic_, _needs
  your decision_, _left alone_ — and changes nothing. `links fix --yes` applies only the automatic
  group. Every decision is a separate, explicit command, never applied in bulk.
- **Refuses on a dirty store**: uncommitted changes mean another session may be holding a file. The
  message names the dirty files and says to retry once that session commits.
- **One commit per store**, message listing what was linked and rewritten. The private store is
  committed and never pushed, as today.
- **Order: push, re-install, then run it** — the sequence `skill-authoring-taudelta` gives for any
  change that moves state.

### What it finds, and what happens to each

| Found in a store folder                                                 | Group     | What happens                                                                                                                                                                                                   |
| ----------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| every plan's `repo:` normalises to one identity                         | automatic | linked; raw `repo:` values rewritten to the identity                                                                                                                                                           |
| plans with no `repo:`, and a clone at exactly the folder's path         | automatic | the clone's identity is linked and written into each plan — the old 1:1 path assumption, used once as evidence and never again as a rule                                                                       |
| `repo:` holding a path (a no-remote clone, today's fallback)            | automatic | the clone at that path supplies `local:<root commit>`, or `file://` when it has no commits                                                                                                                     |
| an empty folder (no plans, no attachments)                              | left      | listed; git never tracked it, so `--prune-empty` removes it and nothing else does                                                                                                                              |
| **two or more folders for one identity** (parallel clones, today's bug) | decision  | proposes the target folder (the clone path whose last segment is the repo's name, shallowest first); `links merge <dir> --into <dir>` moves plans and their attachments, listing any filename collisions first |
| plans in one folder naming two or more identities                       | decision  | lists each identity with its plans; you either split them or declare an alias                                                                                                                                  |
| a folder with no `repo:` anywhere and no clone at its path              | decision  | orphan: `link --dir <folder> --identity <id>` claims it, or `archive` retires its plans                                                                                                                        |
| two table keys or `repo:` values that differ only in letter case        | decision  | nothing merged; shown side by side, with an alias command if they really are one repository                                                                                                                    |
| **a folder in the shareable store whose repository is now private**     | first     | printed above everything else, never automatic: `link --move-to private`. If it has been pushed already, the message says so and points at the history-purge guidance                                          |
| an identity listed in both stores                                       | first     | the corruption message above                                                                                                                                                                                   |

Attachments under `_attachments/<old path>/` move with their plans whenever a plan's folder changes,
and are re-keyed when the folder is linked. In-repo `plans/` directories are not touched: a
repository in `mode = "repo"` has no store folder to link.

### On this machine, 2026-09-28

The shareable store holds one path-shaped folder per personal repo. Every plan in them carries a raw
`repo:` URL that agrees with its folder, and several folders are empty, left behind by absorbed
plans. So first adoption here is all _automatic_ or _left alone_: link each non-empty folder,
normalise the URLs, list the empties. The private store holds no plans yet, and the two parallel
clone groups under work roots have no folders, so the duplicate case does not arise. It will be
exercised by tests, not by this machine.

### A second machine

The table travels with the store. A machine that pulls it resolves its own clones by identity
wherever they sit. If two machines each run first adoption before syncing, `repos.toml` gains one
line per repository on each side. Different keys merge cleanly in git. The same key with two
different folders is a real conflict, and it is the "two folders for one identity" row above.

## Recommended direction

1. `repository_identity(root)`, one comparison function (ignoring case for remotes, exact for
   `file://`) used everywhere identities meet, and the table reader and writer. Tests for each
   worked example above go in `tests/unit/test_plan_store.py`.
2. `resolve()` looks up the table before falling back to the path. `list --all` and
   `attachments_dir` follow the table.
3. The messages, each with its parse-the-commands test, and `references/store-links.md` holding the
   background the messages point at.
4. `link`, `links`, `links fix`, `links merge`, and `doctor`'s read-only checks.
5. `SKILL.md`: a short section naming the situations and saying "follow the message".
6. Rewrite `references/design-rationale.md`'s "Why the store mirrors the clone path" to say the path
   is now only the default name, citing this plan's measurements.
7. Ship in the order push, re-install, then run `links fix` on this machine.
