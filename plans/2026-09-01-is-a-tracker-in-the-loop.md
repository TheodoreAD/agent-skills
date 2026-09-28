---
status: idea
updated: 2026-09-01
---

# Is a tracker in the loop at all?

## Context

Split out 2026-09-01 from `2026-08-28-cross-repo-plan-store.md`, now **retired** — that plan's
recommendation (keep per-repo ownership, add a discovery layer) shipped as the store plus
`plans.py list --scope family`, and its survey and decisions moved into the skill's own
`references/`. This question is the one part of it the user explicitly held open: "the user wants
more time on it", recorded 2026-08-29.

The user raised continuously mirroring a tracker (GitHub Issues named) down to markdown.
`gh-issue-sync` and git-bug's bridges both prove the mechanism works, and both make the remote
authoritative and the markdown a mirror — which inverts what `plan-docs` is, and fails offline.

Three shapes were named: a tracker is **(a)** not involved, **(b)** an inbox only, or **(c)** the
store. `power-user-linux-setup`'s own `plans/2026-08-23-github-issues-plan-lifecycle.md` already
leans toward (b), which is compatible with everything the convention has settled since.

## What has narrowed it since

**(c) is effectively dead.** The store's "local git, no remote by default" decision exists so that
no single personal remote accumulates several employers' internal architecture, and an issue _is_ a
remote. A tracker could only ever hold the personal family's plans — one of eight project roots on
this machine — so it cannot be the store without either splitting the corpus or breaking the rule
the tier split exists to enforce. The `device` setting since made this sharper: on a work device the
one store is treated as sensitive outright.

**The strongest argument for a tracker is spent.** "One place that answers what is pending across
everything" was the motivation, and `list --scope family` answers it — 121 plans across 8 locations
on this machine, in one command, with no remote involved.

So what is left for (b) is genuinely only the inbox case: something arrives as an issue (a bug
report, a request from someone who is not you) and has to become a plan. That is a much smaller
question than the one this started as, and possibly one `plans.py new` already answers by hand.

## A fourth shape arrived, 2026-09-28

The user asked for epics and stories to be drafted as plans and then created in a tracker (Jira
named, the ticket format mattering more than the platform) through a CLI or MCP server. That is
**(d): the tracker as a downstream destination of plans**, which none of (a)–(c) covered. It is
designed in `2026-09-28-tracker-bound-epics-and-stories.md` as a new skill, pre-export only in its
first version, with the plan staying the full record and no sync.

[DECISION: **the inbox case is real.** Answered by the user 2026-09-28: existing epics and stories
that never came from a plan must be pullable into drafts, to gap-check and extend them. Not in the
first version of the drafting skill, but wanted, so this plan now owns that import rather than the
question of whether a tracker is involved at all.]

## Pulling existing epics and stories in

A sketch, to be designed once the drafting format in the sibling plan is settled — the import has to
produce exactly that format, so designing it first would fix the format by accident.

- **One-way, per the boundary below.** The agent fetches the epic and its children through the same
  CLI or MCP server the export uses, and a script turns that payload into drafts. Nothing here talks
  to a tracker directly.
- **The read path decides how much survives, and the tools differ sharply** (read at source
  2026-09-28, detail in the sibling plan's prior-art section). `mcp-atlassian` flattens a ticket's
  rich text to plain text, so list and table structure is gone; the official Atlassian server
  returns markdown even when the raw format is asked for; `jira-cli issue view --raw` returns the
  raw JSON, the only lossless read seen. An import that is to be edited and re-exported needs the
  lossless one.
- **BMAD already does this**: in `bmad-preview-ticketing`, a ticket the tracker knows and the local
  tree does not gets its file at the first query. Read its `board.md` before designing this.
- **An imported draft is tracker-authoritative from birth**, the reverse of an exported one. It
  carries its key and a digest of what was fetched from the start, so the same drift comparison the
  export writes can run on it.

[NEEDS CLARIFICATION: **what "work on them" means once imported.** Adding new stories under an
imported epic is an export of new items with a recorded parent key — already covered by the drafting
skill. Editing an imported story and pushing the edit back is an **update to an existing ticket**,
which is the first step onto the sync ground this plan's boundary rules out. Decide whether edits to
imported items are written back at all, or stay local notes until someone applies them by hand.]

## Open questions

[NEEDS CLARIFICATION: if (b), what does the boundary look like? An issue that becomes a plan is a
one-way import, not a sync — the moment it is two-way, the remote is authoritative for something and
the offline case breaks. `gh-issue-sync`'s three-way conflict detection is the prior art for doing
it properly, and its existence is also the argument that doing it properly is more machinery than an
inbox needs.]

[UNVERIFIED: reconsidering any surveyed tool means reading it at source depth first. Everything in
`skills/plan-docs/references/prior-art-task-trackers.md` except `tasks.md`, `beads` and `Backlog.md`
was assessed at README depth, and the Planning Repo Pattern article was never readable at all
(medium.com returns 403 to WebFetch on both URL forms; freedium.cfd does not resolve). Per the
`research-library` skill, a README can advertise a feature that was never implemented.]

## Recommended direction

The case this was waiting for arrived on 2026-09-28, and closing it as (a) is off the table. (c)
stays dead. What remains is the import sketched above, designed after the drafting format in
`2026-09-28-tracker-bound-epics-and-stories.md` settles, and bounded as a one-way import unless the
open question above deliberately chooses otherwise.
