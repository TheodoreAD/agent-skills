---
status: idea
updated: 2026-09-28
---

# Epics and stories drafted as plans before they become tracker tickets

## Context

Raised by the user 2026-09-28, with an explicit invitation to push back: plans should be able to sit
behind tickets that will be created in Jira (or another tracker — the ticket format, acceptance
criteria and the rest, matters more than the platform), including epics linked to stories. Creating
and managing the tickets is a CLI's or an MCP server's job, not this corpus's. What is wanted is the
**process**: gather several plans into one coherent unit that becomes an epic, work out what is
missing given the epic's direction, scope and purpose, and arrive at a solid deliverable before any
tracker object exists.

This is the first concrete case for `2026-09-01-is-a-tracker-in-the-loop.md`, and in a direction
that plan never listed: the tracker as a **downstream destination** of plans, rather than an inbox
(b) or the store (c). That plan carries the reverse direction — pulling existing epics in — which
the user wants planned but not built in the first version.

### Settled in the grilling session, 2026-09-28

[DECISION: **a new skill, not an extension of `plan-conveyor`.** `plan-conveyor` owns where a plan
lives and how it moves through its lifecycle; drafting stories, writing acceptance criteria, scoping
an epic and finding its gaps is a different responsibility with different triggers ("draft an epic",
"write stories for …"). Folding it in would widen a description that is already about 1,000
characters and a `SKILL.md` already at 1,686 lines, and would make its trigger contend with every
planning request. The new skill shares the store as a **location contract** — it reads the same
config and environment variables — per the shared-location decision in
`2026-09-03-skill-dependencies-and-bundling.md`, and never imports `plans.py`.]

[DECISION: **the plan stays the full record after export, and there is no sync.** Chosen by the user
over a handoff (ticket owns the content, plan keeps rationale only) and over retiring the draft
outright: the epics and stories are not expected to change often, it is the easier compromise, and
two-way sync is a different level of commitment that is not being taken on now.]

[DECISION: **the user drafts as lead or backlog owner.** So a draft may legitimately carry priority,
not only content — the concern that pre-filled fields anchor a team applies to an individual
contributor drafting for others, not to the person who owns the backlog.]

[DECISION: **the first version is pre-export only.** Gap analysis and refinement happen on drafts.
Pulling an existing epic and its stories back in — ones that never came from a plan — is wanted and
is planned in `2026-09-01-is-a-tracker-in-the-loop.md`, not built here.]

## Pushback that shaped the direction

**A plan is not a story.** A plan is problem- and design-shaped, written for the implementer. A
story is outcome-shaped, carries acceptance criteria, and is written for the team and the backlog
owner. The mapping is many-to-many: one plan can yield three stories and three plans one. So
gathering plans into an epic makes those plans **inputs the epic cites**, not files it absorbs —
`migrate` deletes its sources, which is wrong while those plans still guide implementation.

**"Plan-conveyor doesn't manage tickets" is not quite true of the export boundary.** Ticket creation
through a CLI or MCP is not atomic: the epic is created, the fourth story fails, and a naive re-run
creates a second epic. So each item's key must be written back into its draft the moment it exists,
the export must be resumable, and the epic must be created first because its children need its key.
That writeback is this skill's job even though creating the tickets is not.

**Keeping the plan as the full record makes drift silent, and "rarely changes" is exactly the
assumption that keeps it silent.** The rare edit made in the tracker is the one nobody checks. The
cheap mitigation that is not sync: record, per exported item, the export date and a digest of what
was sent. A later read-only comparison — the agent fetching the ticket through the CLI or MCP — can
then say "changed in the tracker since export" without anything flowing back. The plan's exported
sections should say they are the state **as exported on <date>**, so a reader does not take them as
current.

## Open questions

[NEEDS CLARIFICATION: **where an epic lives.** Plans route per repo; epics routinely span repos, and
a tracker project is not a git repo. Writing an epic into one repo's `plans/` while gathering other
repos' plans is the cross-repo write `plan-conveyor` forbids. Candidates: the store at project level
(`<store>/<root>/<project>/`), which a flat `~/projects/<repo>` layout does not have; `_unscoped/`;
or a new area keyed by tracker project. One collision to avoid whichever wins: a directory named for
a plan's stem is already that plan's attachments directory, so "an epic is a directory beside its
plan" is taken.]

[NEEDS CLARIFICATION: **one file per story, or stories as sections of the epic file.** Stories are
lifecycled independently (one exported, one deferred), which argues for files carrying an `epic:`
key; the coherence review wants them read as one set, which a single file makes trivial. Leaning
toward files plus a script that renders the epic as a set.]

[NEEDS CLARIFICATION: **the status after export.** No existing status means "exported, not built" —
`landed` means implemented. The vocabulary already has payload-carrying statuses
(`blocked on <reason>`, `superseded by <plan>`), so `tracked in <KEY>` fits its shape. Adding a
status is a `plan-conveyor` change, since `set-status` owns the vocabulary and its drift check —
that is the one place the two skills cannot stay fully separate.]

[NEEDS CLARIFICATION: **the fields a draft owns.** Proposed: title, issue type, description,
acceptance criteria, parent, blocks/relates links, labels or components, and priority (the user is
backlog owner). Story points, sprint and assignee are left to the tracker. Whether "As a … I want …
so that …" is required or optional — it is theatre for platform work, so optional is the lean.]

[NEEDS CLARIFICATION: **acceptance-criteria format.** Given/When/Then, a checklist, or EARS
notation. Separately, where acceptance criteria land in the tracker: most Jira instances have no
standard field for them — it is a per-instance custom field or a section of the description — so the
field mapping is per destination instance, not per skill.]

[NEEDS CLARIFICATION: **hierarchy depth.** Epic and story only, or sub-tasks, bugs and spikes too.
The format should use neutral names mapped per tracker: Linear calls an epic a project, GitHub uses
parent and sub-issues, GitLab has epics.]

[NEEDS CLARIFICATION: **which CLI or MCP server is the export target**, since its input shape
decides the payload's. Needs a source-level look at the candidates before the payload is designed.]

## Recommended direction

1. **Prior-art pass first**, cloned into `$RESEARCH_HOME` and read at source depth, before any
   format is fixed.

   [UNVERIFIED: known here only from memory, not read at source — BMAD Method generates epics and
   stories with acceptance criteria from a requirements document; GitHub's spec-kit goes from a spec
   to a plan to tasks; Kiro writes requirements in EARS notation. Each is directly on this skill's
   ground and may already have settled the format.]

   Backlog.md, already surveyed in `plan-conveyor`'s `references/prior-art-task-trackers.md`,
   contributes one technique worth taking: `<!-- SECTION:*:BEGIN/END -->` markers, so a script can
   rewrite a generated section without touching prose around it.

2. **The epic states goal, non-goals and exit criteria, and this is gated.** Without them "what is
   missing" has nothing to be judged against, and they are the part most often left implicit.

3. **Gap analysis in three parts, split by what can be derived.**
   - **Scripted:** scope traceability — every in-scope item covered by at least one story, every
     story tracing to a scope item (an orphan is scope creep), and blocks-links checked for cycles
     and ordering. This needs scope items to carry stable identifiers.
   - **Prose, a prompt to think rather than a detector** — the reasoning `plan-conveyor`'s absorb
     section settled 2026-09-09: story kinds that usually go missing — migration or backfill,
     rollout and kill switch, observability, permissions, error states, docs, removal of the old
     path.
   - **A readiness gate** in the shape `set-status planned` already has: a story is not ready with
     an open `NEEDS CLARIFICATION`, missing acceptance criteria, or criteria that cannot be tested;
     an epic is not exportable until every story is. **An open question that cannot be settled
     before export becomes a spike story** rather than blocking the export.

4. **Export is a tracker-neutral JSON payload emitted by a script**, never an agent reading markdown
   and composing MCP calls, which fails silently. Markdown-to-tracker formatting loss (Jira Cloud's
   rich-text format, tables, nested lists) is handled at the payload boundary. A dry run is the
   default. Keys, export date and digest are written back per item as each is created, so a re-run
   resumes rather than duplicates.

5. **Confidentiality at export.** On a contractor device an epic drafted in the sensitive store and
   pushed into one client's tracker can carry another client's names. The export runs `scan` with
   the private terms **minus the destination's own** — a new mode for `scan`, since today it only
   knows public versus private. The skill itself is published, so its templates and fixtures use
   invented names only.
