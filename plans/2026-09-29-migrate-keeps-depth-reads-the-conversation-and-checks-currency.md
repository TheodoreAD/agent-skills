---
status: in-progress
updated: 2026-09-29
---

# `migrate` should keep depth, carry the conversation, and check what is still current

Extends `plans/2026-09-22-deterministic-plan-commits-and-migration.md` §3, which designed `migrate`.
That plan's design is not wrong, but it answers a narrower problem than the one the user keeps
hitting, and this plan is about the gap.

## Context

The user reported on 2026-09-29, across Claude Code, Copilot and Devin, that consolidating a
session's work into a plan fails in three ways:

- **Agents summarise the existing files**, losing almost all the depth of content that took real
  effort to build.
- **Agents ignore the conversation** and work from a file alone, so the decisions, pitfalls, risks
  and rejected alternatives that were argued out in the session and never written down are lost.
- **Nothing checks whether what is being carried forward is still true** against the repo as it
  stands now.

What the user asked for: a migration that reads the conversation context — decisions, pitfalls,
risks, and the like — together with every file the conversation produced, and checks the repo for
how current each of those concerns still is.

## What `migrate` does today, and why each failure gets through

Read from `skills/plan-conveyor/scripts/plans.py` (`_migrate_start`, `check_migration`,
`migration_items`) and the SKILL.md section "Consolidating a session's plans and loose documents
into one", 2026-09-29.

1. **Only tagged and dated lines are gated. Prose is ungated by design** ("rewording is the job").
   So a five-paragraph argument compressed to one sentence passes, as long as the few `[TAG: …]` or
   `YYYY-MM-DD` lines in it keep 60% of their significant words in some paragraph. Most of the depth
   the user means is untagged prose — mechanism, reasoning, the measurement's context, the "why it
   beat the alternative" — and all of that is outside the gate.
2. **The instructions invite the summary.** `start` prints "Rewrite the sections above out of that
   block", and the skeleton it writes is the three-section `Context` / `Open questions` /
   `Recommended direction` form. An agent handed a 400-line carried block and three empty headings
   reads the task as "fit this into three sections", which is summarising. The carried block stops
   the agent losing content it never read. It does nothing about content the agent read and then
   decided to compress.
3. **The conversation is explicitly out of scope.** The SKILL.md says the session's own reasoning
   "is yours to write into the plan. `migrate` cannot see it and never claims to". That is one
   sentence, and nothing in the procedure makes the agent act on it: no step enumerates it, no file
   records it, no gate checks it. So the part of the work with no other copy anywhere gets the
   weakest treatment of all.
4. **Nothing checks currency.** `check` compares the plan against the sources. Whether a source's
   claim still holds against the code — a path that moved, a function that was renamed, a
   `[DEFERRED:]` item somebody has since shipped, a commit that never reached `main` — is never
   asked.
5. **The command is not being reached.** Measured 2026-09-29 over every Claude Code transcript on
   this machine: `plans.py migrate start` has **never been run on real work**. The only transcript
   that invoked it is the session that built it (`75b2bcd7-…`, its `storage-consolidation` test
   case); the other hit is this session loading the skill. So the user's failed attempts did not go
   through `migrate` at all. Copilot and the Devin CLI do load this skill from `~/.agents/skills/`
   (see "Which harnesses this reaches"), so the cause is the same on all three: the request's
   wording ("write this up", "put everything in a plan", "consolidate") does not route to the
   section, or the section comes too late in a long SKILL.md to be acted on. Their transcripts were
   not searched; a Copilot `events.jsonl` sweep would confirm it for Copilot.

Item 5 means the fix is not only in `plans.py`. A better gate on a command nobody runs changes
nothing.

## Design, rough

### 1. The conversation becomes a source file, written first

The agent is the only thing that can see its own context on every harness, and a local transcript
exists on only some of them (see "Which harnesses this reaches" below). So the portable design does
not depend on parsing transcripts. It makes the agent write its context down, into a file that then
goes through the same gate as every other source.

- New `migrate ledger <topic>`, run first. It writes a ledger skeleton with fixed headings, taken
  from the fields the best prior art requires (goose, crush, Roo-Code; see "Prior art"): **every
  user message, verbatim**; decisions, each as chosen / rejected / why; errors and their fixes;
  commands that failed; pitfalls and gotchas; assumptions; risks; open questions; measurements, each
  with the command that produced it; and the files the session created or changed. Every heading
  stays even when empty (opencode's rule), so an empty one reads as "nothing" rather than as
  "forgot".
- **The script pre-fills what it can read mechanically, and the agent fills the rest.** Where a
  transcript is readable, `migrate ledger --transcript <path>` writes the user messages in verbatim
  from it, the way codex puts real user messages back after compaction rather than trusting the
  summariser to keep them. It also lists the files the session edited, the way cline appends a
  `## Files` section from tracked edits when the model leaves it out. The agent writes decisions,
  alternatives and pitfalls, which only it can judge. `harvest.py turns` already extracts Claude
  Code user messages; a Copilot reader for `~/.copilot/session-state/<id>/events.jsonl` would be
  new. The hand-back bug in
  `plans/2026-09-29-harvest-turns-counts-subagent-handbacks-as-user-messages.md` has to be fixed
  first, or subagent reports get filed as user statements.
- `migrate start` takes the ledger as a source like any other (`--from <ledger> <file>…`). From
  there, every bullet in it is gated, not only tagged lines.
- **Capture as it happens, not only at the end.** By the end of a long session the early turns may
  already have been compacted, so a ledger written at migration time is reconstructed from a context
  that has already lost detail. BMAD's answer is an append-only `.memlog.md`, one line per decision,
  constraint, assumption, open question or piece of user direction, written through
  `memlog.py append --type …` at the moment each happens; the spec is re-derived from it and never
  hand-patched. The equivalent here is `plans.py note <type> "<text>"` appending to the session's
  ledger during the work, so that `migrate ledger` at the end starts from those notes.

[DECISION: the ledger is a file, not a prompt. A prompt telling the agent to "include the
conversation" is what exists now, and it is what fails. A file with required headings is a thing the
gate can read, and it makes "the session decided X" a line with the same standing as a line in a
source document.]

### 2. Move, don't rewrite: the default operation changes

- `start` stops writing the three-section skeleton over the sources. The target's sections come from
  the sources' own headings, with the carried paragraphs placed under them, so the agent's job is to
  **arrange and cut duplicates**, not to compose.
- The printed instruction changes from "rewrite" to "move each paragraph to where it belongs, edit
  only where two sources overlap or where the currency check below says a claim is no longer true".
- `check` gates **every source paragraph**, not only tagged and dated lines, at a lower
  per-paragraph ratio than tags (say 0.4, to be measured), so rewording passes and compression
  fails. A paragraph that is genuinely redundant goes under `## Deliberately dropped` with the
  paragraph it duplicates, which is one line of work for a real duplicate and a visible decision for
  a cut.
- `check` also prints a **depth ratio** per source: significant words carried against significant
  words in the source. Information, not a gate. A 10:1 compression is visible at a glance, and a
  reader can ask about it.

[PITFALL: gating prose was rejected in the 2026-09-22 design because "a verbatim-coverage metric
would forbid rewording". That holds for a verbatim metric. A per-paragraph token-coverage ratio is
not verbatim, and the existing `coverage()` function already implements it for tag lines. The
rejection was sound for what it rejected; it just does not cover this.]

### 3. A currency pass, as a worklist rather than a detector

New `migrate currency <plan>` (or a stage of `check`), run after the ledger and the sources are
carried in and before the rewrite. For each gated item, it extracts what can be checked mechanically
and checks it against the repo as it is now:

| reference in the item                         | checked by                                                                          |
| --------------------------------------------- | ----------------------------------------------------------------------------------- |
| a backticked path                             | exists at HEAD, or moved (`git log --follow`)                                       |
| a backticked identifier, flag or task name    | `rg` hit count in the repo, zero reported                                           |
| a commit SHA                                  | exists, and is an ancestor of `origin/<default>`                                    |
| a plan filename                               | live, retired (`archive`), or neither                                               |
| a `[DEFERRED:]` / `[UNVERIFIED:]` / "not yet" | listed for the agent to re-check, with the file's last commit after the item's date |
| a dated measurement                           | listed with its command if the item names one, flagged if it does not               |

The output is a worklist: each item current, changed since, or unverifiable. The agent then records
a verdict for every item the pass flagged, in a `## Currency` section: still true, resolved (with
the commit), or changed (and how). `finish` refuses while a flagged item has no verdict.

[DECISION: a worklist the agent resolves once, not a check that runs on every plan. The objection
recorded in `plans/2026-09-08-stale-claims-in-live-plans-have-no-prompt.md` is that a `plans.py`
symbol check has a 43% false-positive rate across 167 plans, which is the noise floor that gets a
check switched off. That was measured for a **standing** detector firing on every live plan. Here
the check runs once, at the moment someone is already rewriting the plan and has the context to
judge each hit, and a false positive costs one "still true" line. The same measurement is the reason
it must not become a standing check.]

**`finish` records the commit it verified against**, as `verified_at: <sha>` in the frontmatter,
taken from BMAD's `bmad-project-context`. That skill writes "Verified <date> against <sha>" into its
document, and on refresh runs `git log --diff-filter=DR --name-only` since that SHA against every
line, putting each proposed removal in a ledger the user approves
(`skills/bmad-project-context/SKILL.md:89`). With the SHA recorded, a later re-check is a diff since
a known point rather than a re-read from nothing, and it answers the stale-claims plan's first open
question for migrated plans at least: the trigger is commits since `verified_at` touching a path the
plan names.

**Two checks nobody in the prior art does, and this plan would.** Named symbols (a function, a flag,
a task name) are checked against the repo; BMAD and cline check paths only. And a rejected
alternative's reason gets a currency line too: "rejected because X was not available" goes stale
when X ships, and no tool surveyed asks.

### 4. Getting the command reached, on every harness

- **The trigger is not the problem — measured.**
  `skills/plan-conveyor/evals/consolidation-reachability.json`, run 2026-09-29 against the installed
  descriptions at 3 runs: **10/10**. Five consolidation phrasings loaded plan-conveyor every time,
  two harvest phrasings loaded session-harvest, and three look-alikes loaded nothing. So on Claude
  Code a cold request reaches the skill. That refutes the first half of item 5's hypothesis. What
  the suite cannot see is a request made late in a long session.
- **The placement is what is left, and it is done.** The migrate section starts at line 1,642 of a
  1,736-line SKILL.md, below retirement, archive and several pitfalls, so an agent that loads the
  skill and acts on its top never reaches it. Landed 2026-09-29: a row in the opening "Start here"
  table ("write up a session, its notes and docs, as one plan → `migrate start` — never a summary").
  Splitting migrate into `references/migrate.md` is the next step if that proves not enough.
- **A stopgap for the conversation, landed with it.** The migrate section now tells the agent to
  write the conversation into `<topic>-conversation.md` as **tagged and dated lines**, so today's
  gate already checks it, and to pass it with `--from`, then keep it with `attach --commit`. That
  gives the ledger's function with today's code. `start`'s printed instruction no longer says
  "nothing is lost by summarising badly", which read as permission to compress.

[UNVERIFIED: whether the "Start here" row and the stopgap change what an agent actually does. The
trigger suite measures which skill loads, not what happens after. The real test is the next
consolidation on each harness: does it run `migrate start`, and does it write the conversation
file?]

- **Other harnesses: they do load the skill.** See the next section. So the script-based design
  reaches Copilot and the Devin CLI, not only Claude Code.

### Which harnesses this reaches (researched 2026-09-29)

Each harness answers four questions: whether it reads skills from the repo's `.agents/skills/`,
whether it reads skills from `~/.agents/skills/`, whether it reads the instructions file
`~/.agents/AGENTS.md`, and whether it keeps a local transcript.

- **Copilot CLI** (clone):
  - repo skills: yes.
  - home skills: yes (`github/docs`
    `content/copilot/reference/copilot-cli-reference/cli-command-reference.md:1146,1150`).
  - `~/.agents/AGENTS.md`: **no**. It reads only `AGENTS.md` in the git root and cwd, plus
    `~/.copilot/`.
  - transcript: `~/.copilot/session-state/<id>/events.jsonl`.
- **Copilot in VS Code** (clone):
  - repo skills: yes.
  - home skills: yes (`vscode` `promptFileLocations.ts:172-179`).
  - `~/.agents/AGENTS.md`: **no**.
  - transcript: `events.jsonl` as above for Agent Host sessions, or `chatSessions/<id>.jsonl` in
    workspace storage for Local-agent sessions.
- **Copilot cloud agent** (clone):
  - repo skills: yes.
  - home skills: no; it runs on a hosted runner.
  - `~/.agents/AGENTS.md`: no; there is no home directory.
  - transcript: none locally.
- **Devin CLI** (fetched docs page, closed source):
  - repo skills: yes.
  - home skills: yes.
  - `~/.agents/AGENTS.md`: **no**. It reads `~/.config/devin/AGENTS.md` and `~/.claude/CLAUDE.md`.
  - transcript: undocumented. Third parties report `~/.local/share/devin/cli/transcripts/`.
- **Devin cloud** (fetched docs page):
  - repo skills: yes.
  - home skills: no.
  - `~/.agents/AGENTS.md`: no.
  - transcript: none locally.

Script execution from a skill is documented for Copilot and inferred for Devin. The script-based
design therefore reaches every local surface. The ledger's headings are the part that reaches every
surface, cloud included, because they need no transcript and no script. Copilot's `events.jsonl`
makes a Copilot transcript reader a real option, not a hypothetical one.

None of the four reads `~/.agents/AGENTS.md` natively. On this machine that is already covered, as
checked 2026-09-29:

- `~/.copilot/copilot-instructions.md` is a byte-identical copy, the same size and time as the
  original.
- The Devin CLI reads `~/.claude/CLAUDE.md`, which is also a copy.
- `~/.config/devin/AGENTS.md` does not exist and is not needed.

The cloud agents see only what is in the repo, so a rule meant to reach them has to be in the repo's
own `AGENTS.md` or in a skill.

### Prior art (researched 2026-09-29, all from clones in `$RESEARCH_HOME`)

What each tool requires when it turns a conversation into a persistent document, quoted from its
prompt or code:

- **Compaction prompts, least to most depth.**
  - aider: "_Briefly_ summarize", no code blocks.
  - codex: four bullets and "Be concise" (`codex-rs/prompts/templates/compact/prompt.md`). It
    re-inserts real user messages verbatim, up to 20k tokens (`core/src/compact.rs:55,662-704`).
  - cline: "Be concise". Its code keeps the latest typed user turn verbatim and appends `## Files`
    from tracked edits (`compaction-shared.ts:362-375,659-667`).
  - opencode: fixed sections, "keep every section, even when empty", and a merge rule for updating
    an earlier summary: "anything you do not carry into the new summary is lost … where they
    conflict, the conversation wins" (`packages/core/src/session/compaction.ts:16-55`).
  - Roo-Code: an analysis pass first, then nine sections including "All user messages" and verbatim
    quotes "to ensure there's no drift" (`src/shared/support-prompt.ts:54-157`).
  - goose: a required JSON schema with `problem_solving` ("what was chosen, what was rejected, and
    why") and `user_messages`, plus "quote liberally", "omit a field rather than inventing"
    (`crates/goose-context-management/src/prompts/compaction.md`).
  - crush: the only one that asks for alternatives, gotchas, failed commands and assumptions by
    name, and the only one that says "Length: No limit. Err on the side of too much detail"
    (`internal/agent/templates/summary.md`).
- **Capture conventions.**
  - BMAD's append-only memlog is the strongest (above).
  - spec-kit records each clarification as `Q: … → A: …` under a dated session heading, and requires
    Decision / Rationale / Alternatives considered.
  - superpowers' `writing-plans` has a Proportion self-check, since "a plan several times longer
    than the spec … is a transcript".
  - beads compacts closed issues lossily, but snapshots the original first so `bd restore` can undo
    it, and records the commit hash.
- **Currency.**
  - BMAD's provenance SHA plus a `git log` diff (above) is the only real check found.
  - claude-mem skips a file's stored observations when the file is newer than them, a coarse
    per-file check.
  - spec-kit's `analyze` checks drift between spec, plan and tasks, never against code.

**What nobody does**, which is where this plan is new rather than borrowed: measuring depth
(counting decisions, alternatives and user messages in the source against what the output kept),
checking named symbols against the code, re-checking a rejected alternative's reason, and comparing
a summary against the transcript it came from. episodic-memory keeps full transcripts beside 2–4
sentence summaries, but never compares the two.

## Open questions

[DECISION: **capture both during the session and at the end.** Decided by the user 2026-09-29.
`plans.py note` appends as things happen, which is what BMAD does and the only form that survives
compaction. `migrate ledger` at the end starts from those notes and fills the gaps, pre-filling the
user's verbatim messages from the transcript where one exists. Rejected: end only, because it reads
a context that may already be compacted. Rejected: during only, because it is another mid-work
instruction an agent has to remember, the same kind of instruction-following this plan starts from.]

[DECISION: **the ledger is kept as a committed attachment of the plan, not offered for deletion.**
Decided by the user 2026-09-29. `finish` runs `attach --commit` for it rather than listing it with
the sources it may delete. It is the only record of what the session argued out, including the
user's messages verbatim, and the plan is by design a rearrangement of it, never a replacement.
Rejected: treating it like any other source, which would delete the one file whose content has no
other copy once the transcript expires.]

[NEEDS CLARIFICATION: what did the failed attempts look like? A transcript, or the before and after
files, from one Copilot and one Devin attempt would say which of the three failures dominates on
each. On Claude Code the evidence above says the command was never used, which points at triggering
and placement first.]

[NEEDS CLARIFICATION: is a per-paragraph gate at about 0.4 strict enough to stop compression and
loose enough to allow restructuring? Measure it on real pairs before choosing a number: the
`storage-consolidation` sources from `75b2bcd7-…`, plus any before and after from the user's
attempts.]

## Recommended direction

Order by what the evidence says is failing first:

1. **Done 2026-09-29: reachability (section 4)**, with the trigger measured sound and the placement
   fixed. Add trigger evals and move migrate into the "Start here" table. Cheapest, and without it
   nothing below is ever run.
2. **The ledger (section 1)**, including its template and the transcript pre-fill of user messages.
   This is the whole of the "ignores the conversation" failure, and its headings are portable even
   to a cloud harness that has neither a transcript nor the script.
3. **Move-don't-rewrite and the paragraph gate (section 2)**, with the ratio measured first.
4. **The currency pass (section 3)**, as a worklist with a `## Currency` section that `finish` gates
   on, and `verified_at: <sha>` recorded so a later re-check is a diff.

The transcript cross-check in section 1 waits on the hand-back fix in `harvest.py turns`.
