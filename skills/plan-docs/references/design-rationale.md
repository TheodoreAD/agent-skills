# Design rationale for the `plan-docs` convention

This is the deep version of [`SKILL.md`](../SKILL.md) — why the convention looks the way it does,
what it borrows from established prior art, and what it deliberately rejects. It lives inside the
skill directory, not in a `contributing/`-style doc in whichever repo authored the skill, so it
travels with every copy the skill's distribution mechanism produces — a reader in any repo that has
this skill installed gets the same reasoning a reader of the source repo would.

## Why frontmatter, not filename/prose parsing

A plan's lifecycle state needs to be visible without opening the file (skimming a directory listing,
running a status report across many plans) and without re-deriving it from prose that might say
"landed" in one sentence and mean something looser than the formal sense. A small, closed-vocabulary
YAML frontmatter block is the cheapest mechanism that's both human-editable and machine-greppable —
no parser beyond a YAML frontmatter reader, no ambiguity about what a given value means.

## Status vocabulary, in full

```yaml
status: idea | planned | in-progress | blocked on <reason> | landed | abandoned | superseded by plans/<file>.md
updated: YYYY-MM-DD
depends_on: [<repo-name>, ...] # optional
```

- **`idea`** — exploratory only: open questions, no committed build order. Use inline
  `[NEEDS CLARIFICATION: ...]` markers (borrowed verbatim from GitHub Spec Kit's `spec.md` template)
  for each unresolved point instead of a loose prose list — it's greppable
  (`rg "NEEDS CLARIFICATION" plans/`) across every idea-stage plan in the repo at once, so nothing
  requires opening every file to find what's still unresolved. Resolve every marker before promoting
  to `planned`.
- **`planned`** — full design written (Context/Design/Files touched/Verification), not yet started.
  Named to match Spec Kit's and Rust RFC's own vocabulary for the same stage, rather than inventing
  a new word for something that already has a common name.
- **`in-progress`** — actively being implemented, not yet landed. The single most valuable addition
  over a smaller status set: without it, "fully designed, not started" and "half-built, then went
  quiet" are indistinguishable months later, which defeats the entire point of tracking status at
  all.
- **`blocked on <reason>`** — started (or planned), then stalled on something external: an upstream
  fix, a decision, hardware, another repo's change (see `depends_on` below). The reason lives inline
  in the status string — same string-folding pattern as `superseded by`, no separate field to
  maintain. Mirrors Rust RFC's `postponed` and PEP's `Deferred`, without either's multi-year
  governance weight.
- **`landed`** — implemented and verified. **Transient, not a resting state** — see "Retirement, not
  archiving" below. This is the one place this design deliberately parts ways with ADR/PEP
  convention, where the equivalent status (`accepted`/`Final`) is permanent.
- **`abandoned`** — explicitly killed before landing. Also transient.
- **`superseded by plans/<file>.md`** — a `landed` plan whose decision was later reversed by another
  plan; the replacement's path is folded directly into the status string rather than living in a
  separate field. Also transient, once the successor itself lands.

No `created:` field: the filename's date already is the creation date, and repeating it violates the
general principle of not adding a field "just in case" it's useful. `updated:` is the one genuinely
new fact frontmatter adds — freshness at a glance, without `git log` or parsing the filename.

### `depends_on`: cross-repo dependencies

A single-machine, poly-repo setup (a shared tooling repo, several small standalone-tool repos, and
whatever else this skill gets installed into) means a plan in one repo can genuinely require a
change in another repo first. `depends_on: [<repo-name>, ...]` — a flat list of bare repo names —
records that fact structurally instead of only in prose. It complements rather than duplicates
`blocked on <reason>`: `depends_on` is the structural, greppable fact of _which_ repos a plan
touches (usable across an entire multi-repo tree, e.g. `rg "^depends_on:" */plans/*.md` from the
parent directory that holds every repo as a sibling), while `blocked on <reason>` is the lifecycle
statement of _why work is currently stalled_, which may or may not be about a cross-repo dependency
at all. Optional, omitted by default — most plans are single-repo and gain nothing from it.

## Tag vocabulary

The `status` field describes a whole file. The five inline tags describe individual _claims_ inside
it, and they exist for one concrete reason: without them, retiring a plan means re-reading it and
judging every passage, and the thing that gets missed is unfinished work. Discovered by measuring
rather than by reasoning — auditing one real repo's five `landed` plans found **three** carrying
live unfinished work inside files the retirement procedure ends by deleting. `[DEFERRED:]` and
`[UNVERIFIED:]` turn that from a reading task into a gate that blocks.

`[NEEDS CLARIFICATION: ...]` came from GitHub Spec Kit and predates the rest. The other four extend
its shape rather than introducing a second one — Spec Kit has no other inline semantic marker, so
there was no upstream vocabulary to adopt wholesale.

**Naming.** `PITFALL` over `GOTCHA`, which is too informal for a doc that outlives the session, and
over `WARNING`/`CAUTION`, since GitHub markdown alerts already own `[!WARNING]`/`[!CAUTION]` and
would muddy both the semantics and the grep. `CAVEAT` was the runner-up, rejected because a caveat
_qualifies a claim_ whereas these entries are traps someone actually fell into. `FOOTGUN` was
considered and rejected as too casual.

**Why line-anchored.** Found by piloting: a bare `rg '\[DEFERRED:'` also matches prose _mentions_ of
a tag, so the document defining the convention reports the largest backlog in the repo. Requiring
tags to open their own line, and anchoring the pattern, took false positives to zero on the pilot
repo. This is the cost of choosing a bracketed marker over something syntactically rarer — worth
paying for consistency with the existing Spec Kit marker.

**Why not more tags.** Vocabulary size trades against consistency of use, and inconsistent tags are
strictly worse than no tags: the greps still return results, so they get trusted while being
incomplete. Related, `[VERIFIED:]` is deliberately absent — it is a landed plan's default state, so
it would tag nearly every paragraph. Its absence is the signal instead, which costs nothing to
check.

## Retirement, not archiving

Architecture Decision Records, Python PEPs, and Rust RFCs all use an explicit status field — and all
three keep every record forever, because their job is durable institutional memory: "can this
decision still be trusted?", asked years later, by people who weren't there when it was made. That
permanence is a deliberate, reasonable choice for those formats, and a deliberate **non-goal** here.
`plans/` is meant to be a working set that empties out over time, not an ever-growing archive that
has to be read cover-to-cover to know what's still true.

That doesn't mean discarding freely, though. A plan file itself is disposable once its content is
safely elsewhere — but anything that was genuinely costly to work out (debugging that took more than
a couple of tries, an investigation with a non-obvious conclusion, rejected alternatives and why) is
presumed to have future value until proven otherwise, never dropped just because the code shipped. A
plan's durable content has exactly three legitimate final homes:

1. **The executed code itself** — for changes that need no further explanation beyond what the code
   and its own comments already carry.
2. **Usage docs** — anything about how a person or agent uses the result. A `docs/` tree in repos
   that have one.
3. **Design rationale** — settled decisions, rejected alternatives and hard-won gotchas. Some repos
   have exactly this bucket as a `contributing/` tree (e.g. `contributing/verify.md`,
   `contributing/cli-allowlist.md` in the repo this skill was authored in — "every gotcha the first
   implementation pass hit," read before re-deriving or "simplifying" something that was already a
   deliberate tradeoff). Others put it in a package's own `references/`, a `docs/` section, or a
   code comment.

**`SKILL.md` names these three by role rather than by path, and that wording is load-bearing.** It
said `docs/` and `contributing/` literally until 2026-08-28, in eleven places including its own
`description` frontmatter — which meant the convention silently assumed one repo's layout. The
failure showed up the moment the skill was published from a repo that has neither directory, by a
deliberate decision to keep rationale in each skill's own `references/`: the retirement procedure
named two destinations that did not exist, and retiring anything there would have had to either
invent them or ignore the instruction. Naming roles costs nothing and travels; naming paths
described one family's directory names to every consumer.

Once a plan's content is genuinely in one of those three homes, the plan file has no remaining job.
Git history is the fallback permanent record for the _file_ itself, if anyone ever needs to dig up
exactly how it was worded — but that fallback exists for recovering an old plan file, not as a
substitute for actually migrating content someone would otherwise have to dig through git log to
rediscover. The retirement procedure in `SKILL.md` operationalizes this: preserve by default, name
the destination explicitly, fix any references that would otherwise dangle, and only delete once
that's genuinely done — asking first whenever there's real doubt, since deletion is a one-way door
that git history only partially undoes (it recovers the file, not the judgment call that nothing in
it still mattered).

### Why the sibling-repo check is a step and not a nicety

Confirmed 2026-08-26, retiring a scaffolding plan: its tuned basedpyright profile had since moved to
a sibling repo's own rationale page, which had **reversed two of the plan's conclusions** on better
evidence. Migrating the plan's version verbatim would have restated both as current, in a second
location, reading as authoritative. The general shape — a plan that designed something later
extracted elsewhere is describing a decision another repo now owns and keeps current — is why step 1
of the retirement procedure says to check the owning repo before writing anything.

### Why `## Migrated to` is committed before the deletion

Because git records it nowhere otherwise. A commit that both adds the section and deletes the file
shows, in its own diff, only the removal; the added text is never part of any tree that survives.
Anyone later asking "where did this plan's content go?" reads the deletion commit and finds nothing
— which is precisely the question the section exists to answer. Two commits, in order, and the
answer is permanently in history.

### Why the quality gate applies to markdown

Recurring CI failures in the repos using this convention were audited on 2026-08-23. After one-off
causes were fixed, **every remaining recurring failure was a doc-only commit that skipped the gate**
— a `plans/*.md`, `AGENTS.md` or `SKILL.md` line-wrap reflow a formatter would have fixed locally.
Agent sessions treat "just markdown" as exempt; formatters do not. The rule in `SKILL.md` is stated
as an imperative with no exception clause for that reason.

### Worked example: retiring this repo's own first three landed plans

The first real dogfood of this procedure (`power-user-linux-setup`, 2026-08-14) retired
`2026-08-08-devcontainer-pipeline.md`, `2026-08-10-corporate-proxy-daemon.md`, and
`2026-08-13-devcontainer-mounts.md`, plus the tracking plan that scheduled the work. Two things from
that pass are worth carrying forward as the procedure's own lessons, not just its outcome:

- **"Default: preserve" is a check, not a guarantee of new writing.** Two of the three plans needed
  **zero** new `contributing/*.md` content — their design rationale (a devcontainer.json-vs-baked-
  image tradeoff, a `stable`-tag pin/float decision, an SSH-agent-forwarding default) turned out to
  already be fully present in `docs/dev-container.md`'s prose, written at landing time. Only the
  third plan's content — rejected alternatives (`cntlm`, a hand-rolled NTLM/Kerberos
  implementation), the reasoning behind a three-task `check`/`fix`/`install` split, and one
  narrowly-scoped bugfix (a restart/verify race condition) — wasn't captured anywhere else, and got
  a genuinely new `contributing/corporate-proxy.md`. The lesson: always check whether `docs/*.md`
  already covers the rationale before writing something new — duplicating it wastes the retirement
  pass' effort and leaves two copies to drift apart later.
- **The "commit the `## Migrated to` addition before deleting" rule (`SKILL.md`, step 2) is not
  optional busywork — it's the only way the section is ever recorded at all.** If a plan file is
  edited to add the section and then deleted in the _same_ commit, `git log -p -- plans/<file>.md`
  never shows the addition: a deletion commit's diff is computed against its parent's last
  _committed_ state, and if the addition was never committed on its own, the parent's state never
  had it either — the file just vanishes as if the section had never been written. Two small commits
  (add the section; separately, delete the file plus fix dangling references) is what actually makes
  the destination discoverable later via `git log -p` on the dead path.
- **Dangling references aren't confined to `AGENTS.md`/`docs/`/`contributing/`.** This pass found
  citations to a plan's own path inside `tasks/proxy.py`'s module docstring and a function docstring
  — code commentary explaining _why_ a design choice was made will naturally cite the plan that made
  it, the same way narrative docs do. A scoped grep of only the "obvious" narrative locations misses
  these; grep the whole repo for the filename instead.

### Worked example: migrating a legacy `PLAN.md` (`freshful-polite-mcp`, 2026-08-14)

This repo predated the convention entirely: one `PLAN.md` accumulated remote-research notes, a
live-spike log, several fully-landed design decisions, and one genuinely still-open thread (whether
to build support for a second site, blocked on an unresolved ToS question), all in one file, cited
by name from ten other files (`AGENTS.md`, `README.md`, and docstrings/comments across most of the
package). Two follow-on lessons, beyond confirming "Migrating a legacy single plan file"
(`SKILL.md`) works as described:

- **A quoted section title is part of the reference, not decoration on it.** The mechanical part of
  this migration (`sed 's/PLAN\.md/contributing\/design-notes.md/g'`) was necessary but not
  sufficient — dozens of hits looked like `PLAN.md "Proposed architecture"`, and the new document
  didn't use that heading (it became "Why CDP-attach and real DOM interaction, not a hand-crafted
  API client" once organized under its own topic). Anyone following the reference would land in the
  right file but have to search for the claimed section and not find it. Fixing the path and leaving
  the stale quoted title is only a half-fix.
- **Not every citation should point at the new design-rationale doc.** A few references cited
  `PLAN.md "Setup: the dedicated Chrome instance"` — but that recipe was always usage-facing and had
  already been duplicated verbatim in `AGENTS.md`'s own "Operational dependency" section since it
  was written. Migrating that content into `contributing/design-notes.md` too would have created a
  third copy of the same paragraph. The fix was to repoint those specific references at the
  `AGENTS.md` section that already existed, not to migrate more content.

## Relationship to a repo's own `AGENTS.md`

`status:` frontmatter is a plan's own machine-greppable lifecycle marker, updated the moment its
state changes. A repo's `AGENTS.md` (or equivalent) typically stays a separate, curated narrative
index of what's currently true about the repo, written at landing time. The two are decoupled
day-to-day — don't strip "landed"-style language out of `AGENTS.md` just because a plan's
frontmatter also says so, since it serves a different reader (someone skimming for context, not
auditing plan state) — but retirement is the one moment they must be kept in sync: once a plan file
is actually deleted, any `AGENTS.md` prose citing that exact path needs to be repointed (to wherever
the content actually migrated) or have the dead reference dropped.

`AGENTS.md` also accumulates drift independent of any single plan's retirement, and periodically
deserves the same scrutiny on its own. Worked example: the same `freshful-polite-mcp` session above
continued with a second `/plan-docs` pass, this time auditing `AGENTS.md` itself per an explicit ask
to leave it clean of "any planning or ideation." That surfaced the two patterns "Keeping AGENTS.md
itself clean" (`SKILL.md`) now names concretely — a "Status: ... exercised live 2026-08-14" heading
that was pure changelog framing wrapped around otherwise-fine architecture facts, and a "Parsing"
section still describing three functions as raising `NotImplementedError`, a claim
`rg
NotImplementedError` showed was no longer true anywhere in the file: the functions had been
fully implemented in an earlier, unrelated session, and nobody had gone back to update the prose
that said otherwise. Neither was a `plans/*.md` retirement in the formal sense — no frontmatter, no
file to delete — but both are the same underlying failure mode as a stale plan reference: prose
asserting something about the repo's state that stopped being true, with nothing forcing a revisit.

## Where a plan lives: the repo, or the store outside it

The convention's original assumption — a plan can be committed to the repo it describes — holds for
repos you own and fails for everything else. Measured 2026-08-28 across one working machine: of
eight project roots, seven were employer or client work, and **no repo outside the personal root had
a `plans/` directory at all**. Those sessions still planned; the planning just evaporated, because
adding a `plans/` directory to a large repo under review pressure is not available.

The store (`$PLANS_HOME`, default `~/plans`) is the parallel path for exactly those repos. It is not
a migration: repos that can hold their own plans keep holding them, and nothing moves.

### Why the route is configuration, not a heuristic

The tempting rule — "if the repo already has `plans/`, write there; otherwise use the store" — is
wrong on the case that matters most: a **new** repo you own has no `plans/` yet and would route its
first plan out of the repo forever. Keying off a root prefix (`github.com-personal/*` → repo) is
right for the common case but has to be overridable per repo, in both directions: a personal repo
that shouldn't carry plans, a client repo that welcomes them. That is a config file, and the
resulting shape — exact repo entry, then longest root prefix, then a default — is the smallest thing
that expresses all four cases.

`both` exists because switching is a state, not an instant. A repo that stops storing plans inside
itself still has committed plans to read (`{ mode = "both", write = "store" }`), and one adopting
in-repo plans still has store-held ones (`{ mode = "both", write = "repo" }`). Without it, a switch
silently orphans half the corpus.

### Why an unmatched repo asks instead of defaulting

Decided with the user 2026-08-28: with no matching rule and no `default`, `plans.py where` exits 3
and the agent asks. Both silent answers are bad in a way the user cannot see — guessing `repo`
creates a directory inside someone else's repository (turning up in their `git status`, possibly in
a PR), and guessing `store` files the plan somewhere the user never named and will not think to
look. A one-question round trip on the first plan in a new repo is cheaper than either, and the
answer is written to config, so it is asked exactly once per repo.

### Why the store mirrors the clone path

`<store>/<repo's path under the projects root>`, at whatever depth the repo sits. The existing root
directory names already encode host and organisation, so there is nothing to invent: no slug
function, no origin-URL parsing, and no collision when two clients each have a repo called `api`.
Depth matters — three of the eight measured roots hold repos at depth 2 (Bitbucket's project/repo
hierarchy, a grouping directory), so any fixed `<root>/<repo>` rule is wrong for them. The path is
computed from `git rev-parse --show-toplevel`, never from the working directory, so working in a
subdirectory lands in the same place as working at the root.

A store-held plan additionally carries `repo:` frontmatter holding the **origin URL**, not the path:
the path is already the file's own location, so repeating it would be a second copy of the same
fact, while the origin URL is the identity that survives the clone being moved or renamed.

### Why the store is a local git repository with no remote

Local history is the entire benefit and carries no disclosure risk. A single personal remote
accumulating several employers' internal architecture, ticket references and code excerpts is the
specific outcome to design against, and it is what happens by default if a remote is ever added
casually — so `init-store` never adds one and warns if one exists. Pushing is a per-root decision
against that employer's actual policy. The store is also never symlinked into a work repo, for the
same reason `research-library` forbids it: that would put the content back inside the tree that
repo-scoped agent reads walk.

### Why the mechanics are a script rather than instructions

Everything routing touches is deterministic — a path computation, a frontmatter rewrite, an anchored
grep, two gates that are a grep returning empty. Written as prose for an agent to carry out, each
costs file reads and gets the anchoring subtly wrong; written as `scripts/plans.py`, each is one
command whose output is the answer. The gates in particular are worth having in code:
`set-status …
planned` refusing while a `[NEEDS CLARIFICATION:` remains is the convention enforcing
itself, rather than depending on the agent remembering to run the grep it was told about.

`beads` reached the same shape independently and is the closest precedent found:
`bd init
--contributor` routes planning issues to a store outside the repo (`~/.beads-planning`)
specifically so experimental work never appears in a PR to a repo you don't own, and `BEADS_DIR`
overrides repo discovery entirely. Its own guidance — issues belong in the project's git history
when the project is yours — is the argument for keeping this a parallel path rather than a
replacement.

### Why the confidentiality gate derives its terms instead of listing them

The rule is easy to state — a published repo must not name a client — and useless without a check,
because the agent writing the plan is the one that does not know it is doing something wrong.
Measured 2026-08-28: this skill's own plan file, written by an agent, tabulated six employer/client
root directory names and one client's internal `<project>/<repo>` path, and was committed and pushed
to a repo whose README advertises it as public.

A checked-in list of forbidden names cannot be the answer: the only places to put it are the public
repo being protected — where the list is itself the disclosure — or a file somewhere that nobody
updates when a new client arrives. Deriving the terms from the machine's directory layout solves
both. Every root, project and repo name under `projects_root` that is not under a `public_roots`
entry is a name that identifies work that is not the author's to disclose, a fresh clone is covered
the moment it lands, and there is nothing to maintain.

Two details are what make it usable rather than ignored:

- **The walk stops at the first `.git`.** The first implementation collected three levels of
  directory names blindly and swept up `src`, `tests`, `dist`, `.venv` from inside work repos —
  producing 81 hits on a clean tree, all noise. A repo's internal structure identifies nobody.
- **Generic repo names get an ignore list, not a wider `public_roots`.** A work repo called `tools`
  or `settings` matches ordinary English. Ignoring that one name costs almost nothing; adding its
  root to `public_roots` would silence every other name in that organisation at the same time.

`--mode history` exists because the working tree is the wrong place to look once something has been
pushed: a redaction commit fixes the file and changes nothing about what is published. The scanner
reports; whether to rewrite published history is a force-push and a support request, and that is the
user's decision, not an edit an agent should make quietly.

### Why repo-less plans live in the store, under one reserved directory

An idea that has not earned a repo is exactly the thing this convention used to lose: `plans/`
belongs to a repo, so an exploration with no repo had nowhere to go but a chat scratchpad. It goes
in the store, in `_unscoped/`. Underscore-prefixed because every other directory in the store is a
mirrored project root, and a reserved name that cannot collide with one is worth more than a
prettier one. `--unscoped` deliberately needs no git repo at all — the idea may well be had
somewhere that isn't a checkout.

`graduate` is the other half, and the reason the unscoped area does not become a graveyard: when the
repo finally exists, one command routes the file through that repo's own rule and stamps its
provenance. Without it, the plan stays in the repo-less pile while the work moves into a repo, and
nobody finds it again.

### Why repo descriptions are metadata, not a search

Deciding which repo a piece of content belongs to by grepping candidate repos is the expensive,
unreliable way: it costs a lot of reads and answers "where is this word mentioned", which is not the
question. One line per repo — its README's first real line, overridable by an `[about]` entry — is
enough to rank candidates, and cheap enough to compute for every repo on the machine at once.

The output is deliberately not a decision. It is the input to an `AskUserQuestion` with two or three
concrete options, so the user confirms an informed guess instead of answering an open question. The
listing itself names work repos, which makes it exactly the kind of content the confidentiality rule
above is about — for choosing a destination, never for pasting into a repo.

### Why `uninstall` will not delete the store

`install` and `uninstall` are asymmetric on purpose. The config is derived, cheap, and rewritable,
so `uninstall` removes it. The store holds the only copy of every plan for every repo that could not
keep its own — no remote, by design — so deleting it is not the inverse of creating it. It takes
`--purge-store`, and a store that still holds plan files takes `--force` on top of that. An
uninstall that silently emptied it would be the single most destructive thing this skill could do.

## Prior art

Checked how established communities solve "dated proposal document with a lifecycle" before settling
on this design — mechanics were borrowed where they were good and cheap, ceremony and permanence
were rejected where they didn't fit a personal/small-team, poly-repo, single-machine context:

- **MADR (Markdown Architectural Decision Records)** —
  [adr.github.io/madr](https://adr.github.io/madr/), the de facto standard ADR format. Its
  [template](https://raw.githubusercontent.com/adr/madr/main/template/adr-template.md) uses flat
  YAML frontmatter with
  `status: "{proposed | rejected | accepted | deprecated | … | superseded by
  ADR-0123}"` and
  `date: {when the decision was last updated}` — the direct source for this design's
  minimal-frontmatter approach, `date`/`updated` meaning _last touched_ rather than _created_, and
  folding a supersession pointer straight into the status string instead of a separate field. ADRs
  are immutable once `accepted` — "corrections to typos and link rot are fine, but conclusions are
  not edited; write a new ADR that supersedes this one" — which is exactly the permanence this
  design rejects for `landed`.
- **Python PEPs** — [peps.python.org/pep-0001](https://peps.python.org/pep-0001/) — a richer status
  vocabulary
  (`Draft, Active, Accepted, Provisional, Deferred, Rejected, Withdrawn, Final,
  Superseded`) for a
  much bigger, multi-year governance process. Confirms the general pattern (single closed-vocabulary
  status field on a dated proposal doc) but is overkill here — states like `Provisional`/`Deferred`
  weren't worth importing.
- **Rust RFCs** — [rust-lang.github.io/rfcs](https://rust-lang.github.io/rfcs/) —
  `draft → active
  (accepted, not yet implemented) → complete/inactive`, plus a `postponed` state
  for stalled RFCs. The same core progression this design lands on (idea/planned/landed, plus
  `blocked on ...` mirroring `postponed`), arrived at independently before the comparison was made.
- **GitHub Spec Kit** — [github.com/github/spec-kit](https://github.com/github/spec-kit),
  `spec-driven.md` — the most directly comparable AI-agent-era prior art. Uses `spec.md` → `plan.md`
  → `tasks.md` per feature, but deliberately carries **no status frontmatter at all**: these are
  living documents "edited in place... when requirements change, you update the specification," with
  freshness implicit rather than explicit. It also keeps a separate `memory/constitution.md` holding
  immutable, repo-wide governing principles checked against every spec — the same shape as a repo's
  own `AGENTS.md` staying a separate narrative/governance layer, independent validation of keeping
  plan frontmatter decoupled from it day-to-day. Spec Kit was also checked specifically for how it
  handles pre-spec ideation: it deliberately ships no `/brainstorm` command (community consensus: AI
  is capable enough without one, and a formal brainstorming step risks bloated, overengineered
  pre-specs), and real-world adopters keep ideation in a wholly separate system (a ticket tracker, a
  chat scratchpad) rather than inside Spec Kit's own tracked files at all — a gap this design closes
  by giving `idea` its own status and section template inside the same file, rather than punting
  ideation to a second system.
- **Conventional Comments** — [conventionalcomments.org](https://conventionalcomments.org/) — a
  closed label set plus free text (`<label> [decorations]: <subject>`) for code-review comments,
  with machine-parseability as an explicit goal. The direct precedent for this design's inline tag
  vocabulary: a small fixed set of labels, each signalling intent, prefixed so both a human skimming
  and a grep can pick them out. Its labels themselves (`praise`, `nitpick`, `suggestion`, `issue`,
  `question`, `thought`, `chore`) are review-flow concepts and don't transfer — a plan file needs
  lifecycle concepts instead — but the shape and the "seven, not twenty" restraint both do.
- **Claude Code's own plan mode** — no persistent status convention of its own; a plan is transient
  until approved, then the plan file's job is done. Confirms there's no existing
  Anthropic-sanctioned answer to "how do I track a plan after approval" — this convention fills a
  real gap rather than duplicating a built-in mechanism.

**Takeaway:** the decision-record camp (ADR/PEP/RFC) uses explicit status _and_ keeps every record
forever, because their job is permanent institutional memory. GitHub Spec Kit skips status entirely
because its documents are continuously rewritten and never really "finish," and punts pre-spec
ideation to a different, disconnected system. This design borrows the decision-record camp's cheap,
greppable status mechanics and the living-document camp's in-place-editing spirit, but rejects both
camps' actual endpoints: not permanent archiving, and not open-ended living documents either — every
plan is meant to terminate in a deliberate migrate-then-delete step.
