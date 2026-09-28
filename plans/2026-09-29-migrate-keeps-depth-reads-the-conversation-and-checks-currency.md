---
status: idea
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
   through `migrate` at all. On Copilot and Devin that is expected, since there is no evidence yet
   that either loads this skill. On Claude Code it means the request's wording ("write this up",
   "put everything in a plan", "consolidate") does not route to the section, or the section comes
   too late in a long SKILL.md to be acted on.

Item 5 means the fix is not only in `plans.py`. A better gate on a command nobody runs changes
nothing.

## Design, rough

### 1. The conversation becomes a source file, written first

The agent is the only thing that can see its own context on every harness. Claude Code has a
transcript `session-harvest` can read, but Copilot and Devin may not (see
`plans/2026-09-07-session-harvest-across-harnesses.md`, whose first open question is exactly that).
So the portable design does not parse transcripts. It makes the agent write its context down
**before** anything else, into a file that then goes through the same gate as every other source.

- New `migrate ledger <topic>`, run first. It writes a ledger skeleton with fixed headings: user
  statements of intent or constraint (quoted verbatim, with the turn they came from), decisions
  (each with the alternatives rejected and why), pitfalls hit, risks raised, open questions,
  measurements (each with the command that produced it), and the files the session created or
  changed.
- The agent fills it from its context, and `migrate start` takes it as a source like any other
  (`--from <ledger> <file>…`). From there, every bullet in it is gated, not only tagged lines.
- Where a transcript **is** readable (Claude Code today), `migrate check --transcript <id>` adds a
  second gate: every user message in the session is either reflected in the ledger or named under
  `## Deliberately dropped`. The user's own words are the one content with the highest authority and
  no other copy. `harvest.py turns` already extracts them and already separates harness-injected
  text from typed text (with the hand-back bug in
  `plans/2026-09-29-harvest-turns-counts-subagent-handbacks-as-user-messages.md` to fix first).

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

### 4. Getting the command reached, on every harness

- **The trigger.** Measure whether the skill's `description` fires on the phrasings the user
  actually uses. `skill-fitness`'s `trigger.py` takes eval cases; the evals should include "write up
  everything we decided into a plan", "consolidate these notes and what we discussed", "migrate this
  doc into plans/", and should-not-trigger cases.
- **The placement.** The migrate section starts at line 1,642 of a 1,736-line SKILL.md (measured
  2026-09-29), below retirement, archive and several pitfalls. On an agent that reads the top and
  stops, it is never reached. A pointer in the opening "Start here" table is the smallest fix;
  splitting migrate into `references/migrate.md` with a hard pointer is the next one.
- **Other harnesses.** Whether Copilot and Devin load `.agents/skills/` at all, and whether they can
  run the script, is not known here. If they do not, the instruction that reaches them is the home
  `AGENTS.md`, which is `power-user-linux-setup`'s to write; that would be a filed plan, not an edit
  from here.

## Open questions

[NEEDS CLARIFICATION: do Copilot and Devin load skills from `.agents/skills/`, and can they run
`plans.py`? If neither, sections 1–3 help only Claude Code, and the portable part is the ledger
headings, which would then have to live as a rule in the home `AGENTS.md` rather than in a script.
Answer by checking each harness's own docs or source, per the research-library rule, before
designing further.]

[NEEDS CLARIFICATION: what did the failed attempts look like? A transcript, or the before and after
files, from one Copilot and one Devin attempt would say which of the three failures dominates on
each. On Claude Code the evidence above says the command was never used, which points at triggering
and placement first.]

[NEEDS CLARIFICATION: is a per-paragraph gate at about 0.4 strict enough to stop compression and
loose enough to allow restructuring? Measure it on real pairs before choosing a number: the
`storage-consolidation` sources from `75b2bcd7-…`, plus any before and after from the user's
attempts.]

[NEEDS CLARIFICATION: where does the ledger live after `finish`? It is a source, so `finish` would
offer to delete it once its content is carried. It is also the closest thing to a record of what the
session argued out, so keeping it as a committed attachment (`attach --commit`) may be the better
default.]

[NEEDS CLARIFICATION: prior art. The global rule for a new convention is a real web and GitHub
prior-art pass before finalising: how other agent-memory and handoff tools (Devin's own session
notes, Copilot's memory, Cline's memory bank, `claude-mem`-style tools) capture conversation context
into files, and whether any of them already gate depth. Not done yet; this plan is search-free
design from the code.]

## Recommended direction

Order by what the evidence says is failing first:

1. **Reachability (section 4).** Add trigger evals and move migrate into the "Start here" table.
   Cheapest, and without it nothing below is ever run.
2. **The ledger (section 1)**, including its template. This is the whole of the "ignores the
   conversation" failure, and its headings are portable even to a harness that cannot run the
   script.
3. **Move-don't-rewrite and the paragraph gate (section 2)**, with the ratio measured first.
4. **The currency pass (section 3)**, as a worklist with a `## Currency` section that `finish` gates
   on.

The transcript cross-check in section 1 waits on the hand-back fix in `harvest.py turns`.
