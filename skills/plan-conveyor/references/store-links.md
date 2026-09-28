# Store links: which folder holds a repository's plans

Every message `plans.py` prints about store links ends with a pointer to a section of this file. The
message already says what happened and what to run. This file says why, for a reader who wants to
decide rather than follow.

## What a link is

A store keeps a repository's plans in one folder. Which folder is **recorded**, in a file at the
root of each store:

```toml
# ~/plans-sensitive/repos.toml
"github.com/acme-corp/billing" = "github.com-acme/billing"
"github.com/acme-corp/billing-legacy" = "github.com-acme/billing" # an alias
"local:a1b2c3d4e5f6" = "github.com-acme/playground"
```

Before links existed, the folder was simply the clone's path under `projects_root`. That broke as
soon as one repository had two clones — `billing/` and `billing-hotfix/billing/`, say — because each
clone got its own folder and never saw the other's plans. A link makes the folder a decision
recorded once, which every clone of the repository then finds.

- **The left side is the repository's identity**: its `origin` remote as `<host>/<owner>/<repo>`,
  whatever the transport (ssh, https) and ignoring letter case, or `local:<first commit>` for a
  repository with no remote, or its own `file://` path when it has no commits yet.
- **The right side is a folder inside that store.** Its name is only a name. Folders keep the
  path-shaped names they always had, so the store still reads like `~/projects`.
- **Several names may share a folder** — a renamed remote, a first push — and one name never points
  at two.
- **The table lives in the store**, committed with it, so a second machine that pulls the store gets
  the links too. One table per store, so a private repository's name never enters the shareable
  store, which may have a remote.

A repository with no link yet routes to its clone path exactly as before, and its **first write into
the store records the link** and commits it. `plans.py link` shows the current answer for the clone
you are in; `plans.py links` shows every table.

## Which remote

**Seen as:** "can't tell which repository this clone belongs to", or "this clone's remotes belong to
repositories with different plans folders".

A clone's identity comes from its `origin` remote. Without `origin`, a clone with exactly one remote
uses that one. With several, which one it is really a checkout of is not written down anywhere
`plans.py` can read. Picking by name (the first alphabetically, say) would silently split one
repository's plans the moment another clone of it has `origin` pointing elsewhere.

`plans.py link --remote <name>` answers it once. It links that remote's repository to this clone's
folder, and from then on every clone whose remotes include it finds the link. Choose the repository
the plans are _about_: usually the upstream one, or the fork if the plans are about the fork's own
changes.

## Renamed, or first push

**Seen as:** "this clone looks like a repository that already has plans under another name", or
"this clone's plans folder already belongs to another repository name".

Something that looks new is often not. Two cases:

- **First push.** A repository with no remote was linked by its first commit (`local:…`). Once it
  has an `origin`, its identity changes, and its first commit still matches the old link.
- **Renamed remote.** The host renamed the repository, and `origin` was updated. The folder at this
  clone's path is already linked to the old name.

Creating a new folder silently would strand the old plans. So `plans.py` stops and asks:

- `plans.py link --to <folder>` — the same repository under a new name. The new name becomes an
  alias of the existing folder, and the old one stays, so plans that already record it keep
  matching.
- `plans.py link --new [<folder>]` — a genuinely different repository that happens to share history
  (a template, a hard fork). It gets a folder of its own, by default at its clone path, and a
  different name when that path is taken.

## Shareable and private

**Seen as:** "refused, because this plan could be published".

On a machine that splits the store, the **shareable** store may have a remote and the **private**
one never does. Which one a repository's plans go in is decided by where its clones sit — a root
listed in `shareable_roots` (or `public_roots`) is shareable, everything else private — and, once it
is linked, by the link.

The two can disagree when a second clone sits under a different root, and the answer depends on the
direction:

| linked in | this clone under | result                                                                                    |
| --------- | ---------------- | ----------------------------------------------------------------------------------------- |
| private   | a shareable root | the private folder is used, silently. It is the stricter store, so nothing can leak.      |
| shareable | a private root   | **store writes stop.** A plan written here may carry private context into a pushed store. |

In the refused direction there are two ways out:

- `plans.py link --move-to private` moves the repository's whole folder, its local attachments and
  its links into the private store, and commits both stores. From then on every clone writes there.
  If the shareable store was already pushed with those plans in it, they are still in its history —
  removing them from the latest commit does not unpublish them, and purging history is a separate
  decision.
- Or move the clone under a shareable root, if nothing private will ever be written from it.

Reading the repository's plans keeps working throughout. Only writes into the store stop.

## Listed twice

**Seen as:** "stopped, because the plans index is inconsistent".

One repository is linked in both stores. Only one can be right, and writing into the wrong one could
publish private plans, so every store write for that repository stops until it is resolved.
`plans.py links fix` shows both folders side by side and says which commands resolve it. Nothing is
picked automatically.

## Moving onto links, and repairing them

`plans.py links fix` builds and repairs the tables. It is safe to run any number of times.

- **Dry run by default.** It lists what it would do in three groups: _automatic_, _needs your
  decision_, _left alone_. `--yes` applies only the automatic group; each decision is its own
  command.
- **Automatic:** a folder whose plans all record one repository is linked to it; a folder whose
  plans record no repository but that has a clone at exactly its path takes that clone's identity;
  `repo:` values written as raw URLs are rewritten to the identity.
- **Needs your decision:** two folders for one repository
  (`plans.py links merge <folder> --into
  <folder>`), one folder holding several repositories'
  plans, a folder nothing identifies (`plans.py links claim <folder> <identity>`), two names that
  differ only in letter case, and the two cases above that stop writes.
- **Left alone:** empty folders, which git never tracked anyway. `--yes --prune-empty` removes them.
- **Nothing moves unless you choose it.** Existing folders keep their names, so an older installed
  `plans.py`, which ignores the table, keeps writing to the same place meanwhile.
- **It refuses on a store with uncommitted changes**, because another session may be holding a file
  there, and commits once per store.
