# Has someone already built this? The markdown-task-tracker survey

Surveyed 2026-08-28, while deciding whether plans should move out of each repo into one machine-wide
store. The headline finding is the reason this convention exists at all: **several projects store
tasks as markdown in a repo and do it well; almost none solve the cross-repo case, and the two that
do buy it with a database or a remote.**

Kept as its own file rather than folded into [`design-rationale.md`](design-rationale.md) because it
answers a different question — "why not adopt an existing tool" rather than "why is this convention
shaped this way". Extracted 2026-09-01 from the now-retired
`plans/2026-08-28-cross-repo-plan-store.md`.

[UNVERIFIED: **depth varies by row, and it matters.** `tasks.md`, `beads` and `Backlog.md` were read
against their actual source (clones under `$RESEARCH_HOME/repos/`, each with a `SOURCE.md`). Every
other project here was assessed at web-search/README depth only. Per the `research-library` skill, a
README can advertise a feature that was never implemented — so if any of them ever moves from
"surveyed" to "candidate", it needs the same source-level pass first.]

## Markdown-in-the-repo task trackers

| project                                                     | store                                                            | maturity (2026-08-28)                     | cross-repo                               |
| ----------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------- |
| [Backlog.md](https://github.com/MrLesk/Backlog.md)          | `backlog/` md files, YAML frontmatter                            | 6.5k★, MIT, TS, created 2025-06, active   | none — asked about on HN, unanswered     |
| [Markdown Projects](https://www.markdownprojects.com/)      | `.mdp/` folder-per-issue + milestones                            | MIT, published 2026-02, very new          | none stated                              |
| [git-issues](https://news.ycombinator.com/item?id=47973644) | `.issues/` YAML-frontmatter md, autocommit                       | Show HN, single Go binary                 | none                                     |
| [TrackDown](https://github.com/mgoellnitz/trackdown)        | `issues.md` on a dedicated `trackdown` branch, symlinked at root | 38★, GPL-3.0, 367 commits                 | mirrors from GitHub/GitLab/Gitea/Redmine |
| [TODO.md](https://github.com/todomd/todo.md) spec           | one `TODO.md`, GFM task lists as columns                         | 284★, 8 commits, effectively dormant      | pitched at multi-repo, no implementation |
| [tasks.md](https://github.com/tasksmd/tasks.md)             | `TASKS.md`, P0–P3 sections, per-task metadata                    | **7★**, created 2026-03, 333 commits, MIT | **yes — the only real one**              |

## Git-native, no files in the tree

- **[git-bug](https://github.com/git-bug/git-bug)** — 10k★, GPL-3.0, since 2018, still active.
  Stores bugs in git's own object database, CLI/TUI/web, with bidirectional bridges to GitHub,
  GitLab and Jira. The most mature thing in this space by a wide margin, and per-repo by design: a
  bug lives in the repo whose objects hold it. **It survived by _not_ putting files in the working
  tree** — the historical distributed-bug-tracker cohort that did (Bugs Everywhere, ditz, GitIssius)
  is dead.
- **[beads (`bd`)](https://github.com/gastownhall/beads)** — 26.7k★, MIT, Go, created 2025-10.
  Explicitly "a memory upgrade for your coding agent": a dependency graph with a `bd ready` query
  for unblocked work. **It reaches the same answer this convention did and ships it** — every issue
  carries a `source_repo` (`.`, `~/.beads-planning`, or an absolute path), `bd create` auto-routes
  by role, and _hydration_ aggregates the current repo plus the planning repo plus configured others
  into one `bd list`. Ownership per repo, unified discovery, arrived at independently by the
  most-adopted tool in the space.

## Why beads was not adopted, in its own words

Its own guidance is the honest counter-evidence and it points away from adopting it here:

> ### You DON'T need multi-repo if:
>
> - ✅ Working solo on your own project
> - ✅ Team with shared repository and trust model
> - ✅ All issues belong in the project's git history

All three hold on this machine. The listed reasons you _do_ need it — OSS forks, PR hygiene,
multi-persona splits — do not.

What adopting it would cost, read from the docs rather than the pitch: a Dolt database as the store
(`.beads/embeddeddolt/`, with JSONL demoted to an export that is explicitly "not the source of
truth" and not a backup), and a federation page of Dolt remotes, four data-sovereignty tiers, a
MySQL port plus a remotesapi port, and lease-reclaim rules including a documented footgun where
committing `node_id` to the git-tracked `.beads/config.yaml` leaves the guard "fully armed and fully
inert." That is fleet machinery for a single-user machine.

It is also hostile to the surrounding architecture: the `AGENTS.md` snippet `bd init` installs says
"do not create MEMORY.md files" and "Do not use markdown TODO lists for task tracking". beads wants
to own memory and tracking, which this family already assigns to `~/AGENTS.md`, each repo's own
instructions and `plans/`.

## Cross-repo aggregation patterns

- **[tasks.md](https://github.com/tasksmd/tasks.md) workspace mode** is the only surveyed project
  that solves cross-repo aggregation as designed. A workspace is a directory whose immediate
  children are repos each carrying a `TASKS.md`; registered workspaces live in
  `~/.config/tasks-md/workspaces.json`; `tasks next` aggregates across all of them and prints
  `<workspace>::<repo>:<task-id>`, and a task can declare `Blocked by: oncall-hub::api#fix` across
  repos. Its positioning is explicitly "AGENTS.md tells agents _how_ to work, TASKS.md tells them
  _what_ to work on." Verified in source (`packages/parser/src/workspace.ts`,
  `packages/cli/src/config/workspaces.ts`, `packages/cli/src/commands/workspaces.ts`, each with
  tests) — the feature is real; the project is five months old with 7 stars.
- **The Planning Repo Pattern** — one parent git repo whose `.gitignore` treats nested repos as
  opaque; planning documents tracked by the parent, each project keeping full git independence. No
  submodules, no version coupling. [UNVERIFIED: known only from a search summary — medium.com
  returns 403 to WebFetch on both the `medium.com/@jbpoley` and `jbpoley.medium.com` forms, and
  freedium.cfd does not resolve. Needs reading by some other route before it is relied on.]
- **Dendron multi-vault** — several vaults, each its own git repo, with one unified lookup namespace
  and results labelled by vault. The closest existing answer to "per-repo ownership, one search
  surface", and the shape this convention's `--scope family` listing arrives at. (Dendron itself is
  no longer maintained; the model stands.)
- **ADR practice** — the mainstream convention is per-repo `docs/adr/` with a central site generated
  on top once decisions cross many repos. [log4brains](https://github.com/thomvaill/log4brains)
  states the split directly: package-specific ADRs in each package repo, global ADRs central.
- **Obsidian symlink pattern** — one vault, external repos symlinked in. Widely used, and directly
  prohibited by the `research-library` skill's "no symlinks into project repos" rule, for the same
  ambient-read-path reason.
- **git submodule** for a shared `plans/` — the recurring complaint is workflow complexity, plus the
  hard constraint that a submodule cannot have two parents.

## Tracker → markdown mirroring

- [gh-issue-sync](https://github.com/mitsuhiko/gh-issue-sync) — 161★, Apache-2.0. Mirrors GitHub
  issues into `.issues/{open,closed}/123-slug.md` with YAML frontmatter, keeps pristine copies in
  `.issues/.sync/originals/`, and does **three-way conflict detection** (local vs original vs
  remote; both-changed is skipped with a warning, never merged). GitHub stays authoritative.
  `GH_ISSUE_SYNC_DIR` explicitly supports a centralized issue store.
- imdone-cli, `gh2md`, `github-issues-export-rs`, `offline-issues` — one-way export, varying
  liveness. git-bug's bridges are the mature version of the idea, minus the markdown.

**Every one of these makes the remote authoritative and the markdown a mirror, which inverts what
this convention is** — and none of them works offline.

## Counter-evidence worth keeping

- **GitLab's changelog crisis** is the standard citation for "tracked items in the repo cause merge
  conflicts at scale", and their fix was **file-per-entry in a directory** — which is what this
  convention already does. The conflict argument does not transfer to a solo owner with one file per
  plan; do not import it.
- **Fossil** rejects storing tickets in the source tree on two grounds: check-ins are immutable so a
  ticket cannot be added to a past one, and thousands of tickets clutter the tree. Only the second
  half transfers, and the retirement procedure is already the answer to it.
- **Backlog.md takes the opposite position on retirement**, and it is a defensible one. Confirmed by
  grep rather than inference — `src/` returns zero hits for cross-repo, multi-repo,
  multiple-repositories or workspaces, so the unanswered HN question was answered by the code — but
  its core loop ends with "preserve the record: keep the completed task with its reasoning and
  outcome as durable project history". Completed work moves to `completed/`, never out. This
  convention retires by _deleting_, having migrated the durable content first. Both are coherent;
  they cannot both be true, and Backlog.md is evidence that the retention answer is at least
  defensible.
- Its `MANIFESTO.md` is close to a statement of this convention's own philosophy from an independent
  direction: markdown as the durable substrate, local-first ownership, CLI canonical, MCP explicitly
  demoted to "a legacy, optional adapter", "humans and agents are both first-class users."
- Its per-item format is far heavier than a plan file — frontmatter carrying `dependencies`,
  `references` and a full `modified_files` list, plus `## Acceptance Criteria`,
  `## Definition of Done`, `## Implementation Plan`, `## Implementation Notes` and
  `## Final Summary` delimited by `<!-- SECTION:*:BEGIN/END -->` markers so the CLI can rewrite
  sections without touching prose. **The marker technique is worth stealing** for any generated
  section in a plan file.
