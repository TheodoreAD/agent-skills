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

[DECISION: **not BMAD — build our own skill and borrow `bmad-preview-ticketing`'s design (MIT,
credited in the skill's `references/`).** Decided by the user 2026-09-28: "it's too invasive". It is
the closest prior art by a wide margin (see "Prior art, read at source" below). Read from its
source: it writes `_bmad/custom/` config and the ticket tree into `{project-root}`, which an
employer or client repo cannot take, and those repos are where a lead's Jira epics come from. It
needs BMAD core, since activation runs `{project-root}/_bmad/scripts/resolve_config.py` and offers
to install the `bmad` skill when that is missing. Its export is prose: the `write`/`query` verbs in
`config/*-ticketing.toml` are instructions the agent follows. And it is a preview still in motion,
having already replaced BMAD's previous epic and story skills (`removals.txt:85-92`).]

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
cheap mitigation that is not sync: record, per exported item, the export date and a digest of the
issue **as read back right after creation** — not of what was sent, since every tool rewrites
content on the way in and that digest would report drift on day one. A later read-only comparison —
the agent fetching the ticket through the CLI or MCP — can then say "changed in the tracker since
export" without anything flowing back. The plan's exported sections should say they are the state
**as exported on <date>**, so a reader does not take them as current.

## Prior art, read at source 2026-09-28

Cloned into `$RESEARCH_HOME/repos/` and read by two research passes: BMAD Method, spec-kit and two
spec-kit Jira extensions (`mbachorik/spec-kit-jira`, `ashbrener/spec-kit-jira-sync`), CCPM, Task
Master, Backlog.md, `sooperset/mcp-atlassian`, `atlassian/atlassian-mcp-server`, `jira-cli`, and
Linear's SDK schema. Kiro and `acli` are closed, so those came from their vendors' docs pages. Issue
threads were not read, because the `gh` token returned 401.

**On the drafting side, BMAD's `bmad-preview-ticketing` is this plan's design, already built.** Epic
folder, per-story entries in build order, requirement ids that stories `covers`, a validation pass
run by a context-free subagent that "no path, mode, or setting skips", findings sorted into fix,
suggest and ask, declined suggestions recorded as dated `Decision:` lines so they are not raised
again, per-tracker type and status maps, parents-first creation, and `tracker_id`/`remote` written
back after each write. Its `checks.set` lines are the scripted half of gap analysis stated in prose:
"together the tickets account for every requirement … except scope deferred with the user", and
"citing an id alone is not coverage".

**Its typed note lines map onto `plan-conveyor`'s five tags with nothing left over**, which is the
evidence that the tag vocabulary does not need growing for this: `Open question:` and `Unknown:` are
`NEEDS CLARIFICATION`, `Decision:` is `DECISION`, `Parked:` is `DEFERRED`, and `Assumption:` is
`UNVERIFIED`. An `Unknown:` blocking readiness in BMAD is `NEEDS CLARIFICATION` blocking `planned`
here.

**spec-kit contributes the gap taxonomy and the coverage report.** `clarify.md` rates each of a
fixed list of commonly-missed areas Clear, Partial or Missing: out-of-scope declarations, lifecycle
and state transitions, error, empty and loading states, observability, security and privacy,
compliance, external-service failure modes, import and export formats, rate limiting, conflict
resolution. `analyze.md` reports requirements with zero tasks and tasks with no requirement, as a
coverage table.

**Every exporter that writes keys back only at the end loses them on a mid-run failure.** CCPM
renames its files after all issues exist; `spec-kit-jira` writes its mapping at its final step and
says itself that "re-running creates new issues unless you manually update the mapping".
`spec-kit-jira-sync` is the counter-example: identity labels on every issue, a vendor-neutral JSON
payload validated against a schema, dry run, and fail-closed on a tracker read error. Its stance is
the one worth noting against the user's answer: disk authoritative, Jira "a unidirectional,
read-only mirror" that the next reconcile restores after reporting the drift. That is still no
two-way sync, and it is the natural second version if drift turns out to matter.

**Avoid tuning the story count.** Task Master asks for "approximately {{numTasks}}" tasks and tells
the model to fill the requirement document's gaps, so it invents scope rather than flagging it; CCPM
says "prefer simplicity over completeness". BMAD's rule is the opposite and the right one: "split,
never shrink" — a placeholder or simplified version is a second slice.

**On the export side, the tools lose content in specific, readable ways.** `mcp-atlassian`'s
markdown-to-ADF converter makes every source line its own paragraph, so dprint-wrapped prose arrives
as one paragraph per line, and an indented or nested list item becomes a paragraph beginning with a
literal `-`. Its `batch_create_issues` **drops the parent link silently**: `parent` is skipped and
an epic-link alias only logs a warning. Its read-back flattens ADF to plain text. The official
remote server drops an unrecognised parameter without error and returns markdown from `getJiraIssue`
even when ADF is asked for. No Jira tool has an idempotency mechanism; Linear's create accepts a
client-supplied id, which is the only real one seen.

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
key; the coherence review wants them read as one set, which a single file makes trivial. BMAD
settled a third answer that serves both: the epic file plus a `tickets.toml` beside it holding one
entry per story in build order, with a story file written only when that story is refined or
published. Leaning toward that shape, stated in markdown rather than TOML if the entry fields stay
few.]

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
notation. The evidence points at a checklist: Atlassian's own `spec-to-backlog` skill writes a
`## Acceptance Criteria` section of `- [ ]` items into the description, and `mcp-atlassian` turns a
column-0 `- [ ]` list into a native Jira task list. BMAD writes full Given/When/Then only for bugs
and refined stories, and otherwise one `Verify:` line. Lean: a checklist whose every item fails
before the story and passes after it (BMAD's test), Given/When/Then optional per item, and
Definition of Done kept separate — Backlog.md: "AC defines product scope/behavior, DoD defines
completion hygiene". Where it lands in the tracker is per destination instance: the description by
default, a `customfield_…` by mapping.]

[NEEDS CLARIFICATION: **hierarchy depth.** Epic and story only, or sub-tasks, bugs and spikes too.
The format should use neutral names mapped per tracker: Linear calls an epic a project, GitHub uses
parent and sub-issues, GitLab has epics.]

[NEEDS CLARIFICATION: **the transport: `jira-cli` or an MCP server.** Reopened by the user
2026-09-28, who has built a system before on `jira-cli` and TOML ticket files. It "doesn't play very
well with powershell, perhaps i didn't put enough time into it". MCP is attractive because it solves
auth in one place, so a CLI token stops being a problem. But `jira-cli` would be a good, stable way
if its auth can be solved elegantly and it can be used effectively on Linux first and then Windows.
MCP is still worth exploring, costed against context and against the complexity of an issue body —
headings, paragraphs and Jira's own format. The axes, with what is known:

- **Auth.** `jira-cli` reads its token from `JIRA_API_TOKEN`, then `.netrc` (`_netrc` on Windows),
  then the OS keyring through `zalando/go-keyring` under service `jira-cli`
  (`internal/cmd/root/root.go:160-169`). The keyring is Secret Service on Linux, which is the
  desktop keyring already unlocked at login here, and Credential Manager on Windows. So "store the
  token once in the OS keyring, never in an environment variable or a file" looks available on both
  platforms, and is the elegant answer to test first. `mcp-atlassian` takes an API token, a personal
  access token or OAuth; the official remote server takes OAuth 2.1, or an API token only if an
  admin enables it.
- **Windows.** `jira-cli` rates its own Windows support "partial" (README platform badge).
  PowerShell's quoting of multi-line bodies and `--custom key=value` pairs is the likely friction.
  Passing the body through a file or stdin rather than an argument sidesteps most of it, and is
  worth testing before blaming the tool.
- **Body format.** Each transport converts differently, and none is lossless. `jira-cli` goes from
  markdown to wiki markup through blackfriday and posts to the v2 API, where Jira converts it again;
  `mcp-atlassian` converts markdown to ADF line by line; the official server converts server side,
  where it cannot be inspected. **Owning the conversion ourselves** — the script emits Jira's format
  directly (ADF for Cloud, wiki markup for Server/Data Center) — makes the result the same whichever
  transport carries it, at the cost of a converter to maintain. Needs weighing against accepting one
  tool's losses.
- **Context cost of MCP.** Every tool schema a server exposes sits in the agent's context.
  `mcp-atlassian` narrows this with `TOOLSETS` and `ENABLED_TOOLS`. Measure a narrowed server's real
  cost before deciding, rather than estimating it.
- **Health.** `jira-cli` has not released in 393 days and has one main maintainer. `mcp-atlassian`
  released v0.23.1 on 2026-08-19, and releases every few days.
- **Lossless read** (for the drift check and the later import): only `jira-cli issue view --raw` was
  seen returning the raw issue JSON.

The payload being tracker-neutral keeps this decision swappable, so it does not block the drafting
format. It does decide who converts the body.]

### CLI and MCP alternatives, surveyed at source 2026-09-28

Asked for by the user: are there alternatives worth having to `jira-cli`, and which other Jira MCP
servers exist. Thirteen more clones under `$RESEARCH_HOME/repos/`; health figures from
`package_health.py`. The Appfire page returned HTTP 429 and the `acli` FAQ 404, so neither was
assessed properly.

**Nothing displaces `jira-cli` as a CLI.** `go-jira` is dead (last release 2020), and its Windows
keyring is a stub that errors. `acli` is Cloud only and closed, and its create has no `--priority`.
`pycontribs/jira` has one active maintainer and is 426 days since a release. `atlassian-python-api`
is healthy (5.0.5, 13 days ago, 29 contributors a year) but is a library with seven runtime
dependencies and no keyring. Every other candidate keeps the token in a plaintext file, an
"encrypted" file keyed from the machine id, or an environment variable.

**The one real alternative is no CLI at all: a standard-library Python script calling Jira's REST
API directly.** Estimated 250–350 lines of `urllib`, `json` and `base64`. REST v2 takes a
wiki-markup string on both Cloud and Data Center, so one description format serves both. Create is
`POST /rest/api/2/issue`, links `POST /rest/api/2/issueLink`, and a lossless read
`GET /rest/api/2/issue/{key}`. Auth is `Basic email:token` on Cloud and `Bearer <PAT>` on Data
Center. With Python `keyring` as the store, it takes the token from `keyring get` and needs neither
`secret-tool` nor `ctypes`.

[NEEDS CLARIFICATION: **a REST script makes this skill create the tickets, which the original
request placed outside it** ("the actual management of tickets/issues would not be the
responsibility of plan-conveyor"). The trade is real in both directions. For it: no binary to
install on either platform, one description format, a raw read, and none of `jira-cli`'s PowerShell
or release-cadence risk. Against it: every Jira API change becomes this skill's to track, and the
boundary that kept ticket management out of this corpus is gone. The launcher keeps the boundary,
since `jira-cli` still does the talking. Decide which, or keep the launcher now and the script as
the fallback. The user, 2026-09-28: decide after the keyring proof has run.]

**Three facts from the survey that constrain every option:**

- **Search moved on Cloud.** `pycontribs/jira` warns that the old `search` API is deprecated on
  Cloud, and `jira-cli` uses `/rest/api/3/search/jql` there and `/rest/api/2/search` on Data Center.
  The identity-label duplicate check must use the new endpoint on Cloud. `go-jira` calls only the
  old one.
- **The epic parent is not one field.** Cloud takes `parent: {key}`. Data Center takes a
  per-instance Epic Link custom field, and creating an epic there also needs an Epic Name. So it is
  detected at runtime, which `mcp-atlassian` does by trying `parent` first.
- **A real checklist exists only in Cloud's rich-text format.** Only `mcp-atlassian` was seen
  turning `- [ ]` into a native task list. Through wiki markup — v2, which `jira-cli` and the REST
  script both use — acceptance criteria can only be bullets. That bears on the acceptance-criteria
  question above: the checklist is the drafting format, and a list of bullets is what a v2 transport
  delivers.

**Other MCP servers:** none reads a Linux or Windows keyring (only one reads the macOS Keychain), so
the launcher is the auth answer whichever server is chosen.

- **`mmatczuk/jira-mcp` (Go) matches the payload almost one-to-one.** It has four tools. Its
  `jira_write` takes an `items[]` batch with a dry run, and a create takes priority, labels,
  `parent_key` and `links`, with link names resolved to ids. It converts markdown to ADF on v3, and
  can route wiki markup through v2. Its `jira_read` passes ADF through raw, and it validates
  required fields before creating. Against it: Cloud only, basic auth from environment variables, 11
  stars, one maintainer, although it released 12 days ago.
- **`b1ff/atlassian-dc-mcp` (TypeScript)** is the Data Center option. It has about 16 tools with no
  allowlist, and a wiki-markup description with a free-form `customFields` map. Its token is a mode
  `0600` file outside macOS. It released 41 times last year, with 20 contributors.
- **`aashari/mcp-server-atlassian-jira`** exposes five generic REST verbs, so its context cost is
  minimal and its reads are raw. It is Cloud only and 299 days since a release.
- **`atlassian-labs/mcp-compressor`** is not a server: it collapses any server to two tools
  (`get_tool_schema`, `invoke_tool`), and could make the official OAuth server cheap in context. It
  stores its OAuth tokens as JSON files.

[DECISION: **the user's earlier `jira-cli` and TOML system cannot be read**, and the design proceeds
without it. It was built inside a corporation with no access now, against a Data Center instance.
The user now has a Jira Cloud account, and assumes the CLI abstracts the difference, since **only
basic features are wanted**. Recorded 2026-09-28. The source supports that assumption as far as
setup goes: `jira init` takes `--installation cloud|local` and
`--auth-type basic|bearer|mtls|
cf-access`. So Cloud is an email plus API token (`basic`), and Data
Center a personal access token (`bearer`) (`internal/cmd/init/init.go:40-43`).]

### Proving `jira-cli` auth from the keyring, read at source 2026-09-28

The user's next step: prove keyring auth on Linux before choosing the transport. MCP is tried later
and stays in this plan, and other Jira MCP servers are surveyed alongside CLI alternatives.

- **`jira-cli` only ever reads the keyring.** Its two `keyring.Get("jira-cli", login)` calls are the
  only keyring calls in the codebase (`api/client.go:40`, `internal/cmd/root/root.go:169`), so
  storing the token is a separate step that this skill, or the machine setup, owns. [DECISION:
  **Python `keyring` is the credential store, not `secret-tool`.** The user's preference,
  2026-09-28. It is already on this machine (`[packages.python-keyring]` in
  `power-user-linux-setup`'s `setup.toml`), and it is one tool on Linux and Windows alike, where
  `secret-tool` is Linux-only.]

- **On Linux, `go-keyring` finds what Python `keyring` writes — read at source, not yet run.**
  `go-keyring` searches the login collection for `username=<login>` and `service=jira-cli`
  (`keyring_unix.go:56-78`). Python `keyring`'s default scheme writes `username` and `service` plus
  an `application` attribute (`keyring/backend.py:281-297`, `backends/SecretService.py:89`). A
  Secret Service search matches items carrying at least the attributes asked for, so the extra one
  should not matter. `keyring set jira-cli <login>` reads the token from a pipe when stdin is not a
  terminal (`keyring/cli.py:186-194`). So `zenity --password | keyring set jira-cli <login>` stores
  it through a GUI prompt, using the `zenity` already installed for `askpass-zenity`, and the token
  never appears in a terminal, a shell history or an agent transcript.
- **On Windows the two do not meet, twice over — read at source.** `go-keyring` reads a generic
  credential named `jira-cli:<login>` and returns its bytes unchanged
  (`keyring_windows.go:24,
  125-127`). Python `keyring` writes the credential under the bare
  service name, `jira-cli` (`backends/Windows.py:134-145`), and through `pywin32`, whose string
  blobs are UTF-16 — which is why its own reader tries UTF-16 first (`backends/Windows.py:51-62`).
  So `jira-cli` would not find the credential, and would read NULs between the characters if it did.

[NEEDS CLARIFICATION: proposed by this session, not yet agreed — **solve auth once, outside every
transport: Python `keyring` holds the token, and a launcher hands it to the tool's environment for
that one process.** `keyring get jira-cli
<login>` supplies `JIRA_API_TOKEN` to the `jira` child
process only — never exported into a shell, never written to a file — which works identically on
Linux and Windows and does not depend on any tool's own keyring support. The same launcher serves an
MCP server that reads its token from the environment (`mcp-atlassian` does), so this is the "auth
solved in one place" the user wanted from MCP, without choosing MCP for it. The launcher calls the
`keyring` CLI rather than importing the library, because a skill script is standard library only. It
follows from the two findings above; agree it or reject it.

The launcher is **a script in the skill's `scripts/`** (say `jira_run.py issue view KEY --raw`), not
an alias or a shell function. An alias only substitutes text and cannot fetch a secret. A zsh
function is machine config the published skill cannot rely on, and PowerShell cannot scope a
variable to one command, so the token would sit in the session's environment. The script is one
implementation on both platforms with no shell quoting in between, and it can feed `jira` a body
from a file, which sidesteps the multi-line-argument quoting that PowerShell makes hard. A shell
function for a human typing `jira` can still live in `power-user-linux-setup`; the skill never
depends on it.]

- **The proof, in order:** create an API token in the Atlassian account; store it with
  `zenity --password | keyring set jira-cli <login>`; run
  `jira init --installation cloud --auth-type basic` with the site and the login email; then run a
  read (`jira me`, a one-issue `jira issue list`) **with `JIRA_API_TOKEN` unset and no `.netrc`**.
  Those are the two sources `jira-cli` checks before the keyring, so either one being present would
  make a pass meaningless. Then run the same read through the launcher. On Linux both should pass;
  on Windows only the launcher is expected to.

  [UNVERIFIED: every claim in this section was read from source on 2026-09-28 and none has been run.
  The Linux match depends on Secret Service's subset search and on both libraries using the same
  collection.]

## Recommended direction

1. **Prove `jira-cli` auth through the OS keyring on Linux against the user's Jira Cloud account**,
   per the section above, before the transport is chosen. MCP servers are tried afterwards.
   Backlog.md's `<!-- SECTION:*:BEGIN/END -->` markers are the technique for letting a script
   rewrite a generated section without touching the prose around it.

2. **The epic states goal, non-goals, exit criteria and requirements with stable ids, and this is
   gated.** Without them "what is missing" has nothing to be judged against, and they are the part
   most often left implicit. BMAD's exit criteria ("Done when") are three to six checks, each of
   which fails today.

3. **Gap analysis in three parts, split by what can be derived.**
   - **Scripted, both directions:** every requirement id covered by at least one story's `covers`,
     every story covering at least one id (an orphan is scope creep), and `blocks` links checked for
     cycles and build order. The report says "citing an id is not coverage" beside the table rather
     than claiming it can check that.
   - **Prose, a prompt to think rather than a detector** — the reasoning `plan-conveyor`'s absorb
     section settled 2026-09-09: spec-kit's missed-area taxonomy (above), plus BMAD's dependency
     questions — shared setup has exactly one owning story, a handoff is named in both stories'
     descriptions — plus migration or backfill, rollout and kill switch, and removal of the old
     path.
   - **A readiness gate** in the shape `set-status planned` already has: a story is not ready with
     an open `NEEDS CLARIFICATION`, missing acceptance criteria, or criteria that cannot fail before
     the story; an epic is not exportable until every story is. **An open question that cannot be
     settled before export becomes a spike story** rather than blocking the export.
   - **Run the prose half as a review with no context from the drafting session**, where the harness
     offers one, and record a declined suggestion as a `[DECISION: …]` so it is not raised again —
     both from BMAD. Degrade to an inline pass where it does not, and say so.

4. **Export is a tracker-neutral JSON payload emitted by a script**, never an agent reading markdown
   and composing MCP calls, which fails silently. The shape, from the export-target pass:
   `{"schema": "tracker-export/1", "source": …, "items": [...]}`, each item carrying `local_id`,
   `kind`, `title`, `description_md`, `acceptance_criteria`, `labels`, `components`, `priority`,
   `parent` and `links` **as local ids**, an `identity_label`, and `key` once known. Tracker
   specifics — project key, issue type names, custom field ids, link type names — live in a
   per-destination config, never in the payload. The script:
   - **Joins wrapped lines so each paragraph is one line and flattens nested lists**, because
     `mcp-atlassian` makes every source line a paragraph.
   - **Orders items parents first, then prerequisites**, and emits links as a second pass that runs
     only once every key exists.
   - **Gives every item a stable identity label** (`plan-<epic-stem>-<local_id>`). The agent
     searches for it before creating, so a lost writeback cannot create a duplicate either.
   - **Is applied one item at a time through the single-issue create**, never a batch tool — the
     only Jira batch tool read drops the parent link.
   - **Writes each key back the moment it exists**, then reads the new issue back through the same
     tool and stores a digest of **that** read as the drift baseline. A digest of what was sent
     would flag drift immediately, since every tool rewrites content on the way in.
   - **Defaults to a dry run, and fails closed**: a tracker read that errors writes nothing.

5. **Confidentiality at export.** On a contractor device an epic drafted in the sensitive store and
   pushed into one client's tracker can carry another client's names. The export runs `scan` with
   the private terms **minus the destination's own** — a new mode for `scan`, since today it only
   knows public versus private. The skill itself is published, so its templates and fixtures use
   invented names only.
