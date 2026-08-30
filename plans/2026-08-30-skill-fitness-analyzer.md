---
status: idea
updated: 2026-08-30
---

# A skill that measures and improves skills: triggers, contention, and absorbed scripts

Merged 2026-08-30 from `2026-08-22-skill-trigger-quality-review.md`, which owned the per-skill
trigger question and the first prior-art pass. That plan is **merged away and deleted** —
`plans.py archive --show 2026-08-22-skill-trigger-quality-review.md` reads it back. Its evidence is
carried below; several of its conclusions were checked live this pass and did not survive, and those
are corrected in place rather than appended, so the wrong argument does not stand above the right
one.

## Context

The ask (2026-08-30): a skill that perfects skills. Three capabilities, one subject —

1. **Trigger fitness.** Does a description fire on the requests it is meant to cover, and does it
   steal a sibling's? `skill-authoring` would call this checker rather than owning the mechanics.
2. **Contention against a given set**, starting with whatever is installed globally, because
   selection happens among the installed set and never one description at a time.
3. **Reaching into past sessions for stats** — including how often a skill left the agent
   hand-rolling near-identical Python that should have been deterministic code inside the skill.

The third is the novel one and turned out to be the most measurable.

## What was measured this pass, 2026-08-30

All numbers from this machine, this date. Commands are named so each is re-runnable rather than
believed.

### The description corpus

Parsed continuation-aware, across every skill this machine can see (`~/.agents/skills` plus the
repo's `skills/`):

| skill                   | real     | what the repo's gate sees | over the 1024 spec cap |
| ----------------------- | -------- | ------------------------- | ---------------------- |
| `python-conventions`    | 1302     | 612                       | **+278**               |
| `plan-docs`             | 1020     | 1020                      | —                      |
| `session-harvest`       | 997      | 997                       | —                      |
| the other seven         | ≤769     | =real                     | —                      |
| **total listing bytes** | **7411** |                           |                        |

One skill over the cap, one hidden from the gate, and they are the same skill — the violation is
large enough to have needed wrapping, which is exactly what the gate's line-by-line parse discards.
Unchanged since 2026-08-29, and the bug is still live.

### Invocation reality, and the correction that matters most

437 transcripts, 19,791 Bash calls, **113 `Skill` tool invocations**. But the merged-away plan
counted only the `Skill` tool, and that is the wrong denominator:

| skill              | `Skill` tool calls | `<command-name>` markers (user typed `/name`) |
| ------------------ | ------------------ | --------------------------------------------- |
| `plan-docs`        | 69                 | 12                                            |
| `session-harvest`  | 11                 | **84**                                        |
| `research-library` | 12                 | 0                                             |

[PITFALL: **An explicit `/skill-name` invocation does not necessarily produce a `Skill` tool call.**
The harness can inject the skill body directly as a command message instead, which is what
`session-harvest`'s 84-vs-11 split is. So the `Skill` counter under-reports total usage and
over-reports the auto-trigger share for any skill the user mostly types by hand, while `plan-docs`'
69-vs-12 says the opposite — most of its invocations really were model-chosen. The merged-away
plan's `[DEFERRED: ...]` asked exactly this before quoting the numbers as trigger rates; it is now
answered, and the answer is that **two mechanisms must be counted separately and neither alone is
the rate**.]

[PITFALL: a trigger probe run during this session added its own synthetic skill to the corpus and it
appears in the counts above. Any miner that reads the transcript store must be able to exclude its
own probe traffic, or repeated measurement inflates what it measures.]

### Ad-hoc Python, and whether "absorb it into the skill" is a real signal

1,067 `python -c` payloads extracted, 1,039 parseable, across 112 sessions. The shell string is
useless as a signature — every one normalises to `python3 -c S` because the payload is quoted — so
the clustering has to run on the **parsed payload**. Two lenses, both cheap:

- **Exact AST shape**: 681 distinct, 39 recurring across more than one session.
- **Import set**, coarser and far more legible:

| import set    | calls | sessions | projects |
| ------------- | ----- | -------- | -------- |
| `json`, `sys` | 145   | 25       | 5        |
| `json`        | 144   | 23       | 7        |
| `re`          | 74    | 10       | 6        |
| `tomllib`     | 60    | 17       | 3        |
| `ast`         | 19    | 5        | 1        |

The archetypal finding, and the one that proves the concept: **7 ad-hoc readers of the transcript
store, across 6 sessions** — sessions hand-rolling in a one-liner what `session-bash-audit` already
ships as `scripts/audit.py`. That is precisely "a skill exists, the agent did not reach for its
script, and wrote a worse one inline". Two more of the same shape:

- `import copier; print(copier.__file__)` — 15 calls, 11 sessions, 6 projects. A "where is this
  package installed" probe with no home.
- `import tomllib; tomllib.load(open('<a repo>/setup.toml','rb')); print('ok')` — 19 calls, 7
  sessions. A validation one-liner that belongs in that repo's task runner.

[DECISION: cluster on the **import set** first, not on AST shape or edit distance. It is one
`ast.parse` per payload, it survives the renaming and reformatting that defeat textual similarity,
and it produced human-legible clusters on the first run where the AST shape produced 681 mostly-
singleton buckets. AST shape stays as the second pass **within** an import cluster, for deciding
whether several calls are really the same operation.]

[DECISION: only `.py` **payloads** are worth mining, not `.py` files. 3,268 `Write`/`Edit` calls
touched `.py` paths but 3,195 of them were inside a repo — real source, not throwaway. Only 66 went
to a scratchpad. The throwaway script mostly never becomes a file, which is why a file-based
detector would have found almost nothing.]

### The listing budget, which nothing in the family was accounting for

Claude Code loads a listing of every skill's name and description. That listing has a **character
budget scaling at 1% of the model's context window**, and when it overflows Claude Code **shortens
descriptions starting with the skills you invoke least**, so the most-used skills keep their full
text.

[PITFALL: that is a death spiral with a measurable first step. A skill that never triggers is first
in line to lose its description; without its description it cannot be matched; so it triggers even
less. Two of this repo's skills have never fired at all. The budget is also **shared with every
bundled skill** (`/code-review`, `/design`, `/dataviz`, the artifact skills, ...), so this repo's
7,411 bytes are not the denominator — the machine's whole listing is, and it is much larger.]

Levers, all Claude-Code-specific: `skillListingBudgetFraction` (e.g. `0.02`), the
`SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable, and `skillOverrides` entries of `"name-only"`
to free budget by listing a low-priority skill without its description. `/doctor` estimates the
listing's context cost and names the biggest contributors; the Skills row in `/context` reports the
post-budget size; an overflow also writes a warning to the debug log, visible with `--debug`.

## Corrections to the merged-away plan

Each of these was stated there as settled and is wrong or incomplete as of today.

- **The cap's provenance.** The repo's gate comments `MAX_DESCRIPTION_CHARS = 1024` as "Claude
  Code's documented cap". It is the **Agent Skills specification's** cap (`description` must be
  1–1024 characters, non-empty, and free of XML tags). Claude Code's own number is different — it
  truncates the combined `description` + `when_to_use` at **1,536** in the listing, configurable
  with `skillListingMaxDescChars`. Both are real; they answer different questions, and the plan's
  open question "does any agent actually truncate at 1,024, and where?" is answered: not Claude
  Code, which truncates later and budgets separately.
- **`when_to_use` is not a way out.** Claude Code offers a dedicated frontmatter field for trigger
  phrases, which would neatly separate "what it does" from "when to use it" and make trigger-only
  similarity measurable. It is **not in the vendor-neutral specification** — so adopting it in this
  repo is exactly the vendor coupling `AGENTS.md` rules out. Trigger vocabulary stays inside
  `description`, and the analyzer has to extract it rather than read it from its own field.
- **The AI-security vendor's scanner does not cover items 2.3 and 2.4.** Its `UNVERIFIED` tag said
  running it could delete them from the plan. Read from source rather than run: its
  `_check_description_overlap` is **Jaccard similarity over the whole description's stop-word-
  filtered token set, hard-coded threshold 0.7, symmetric only**. On prose descriptions two skills
  would have to share 70% of their vocabulary to fire, so on a real corpus it is close to a no-op;
  it detects no shadowing at all, because Jaccard cannot express subsumption. It is security-framed
  (`TRIGGER_OVERLAP_RISK`, severity MEDIUM, category social-engineering). **Both items survive.**
- **`claude plugin eval` is still gated**, on CLI 2.1.251 as of today. `--help` renders in full,
  which is misleading; `claude plugin eval .` still answers
  `` `plugin eval` is currently in early
  access `` and exits. Its `init` subcommand and
  `--ablation with-without` are as previously described, and the report still publishes to claude.ai
  by default. Nothing to build on yet.

## Prior art, checked live this pass

**`skill-creator` is public now** (`anthropics/skills`, cloned to the research library), and it is
the closest thing to what is being asked for. What it actually does, from its source rather than its
docs:

- `scripts/run_eval.py` writes a **synthetic command file** into
  `.claude/commands/<name>-skill-
  <uuid>.md` carrying only the candidate description, runs
  `claude -p <query>` with `--output-format stream-json --include-partial-messages`, and watches the
  stream for a `content_block_start` naming the `Skill` tool with that id in its input. It kills the
  run the moment it detects one, so a trigger test does not pay for the work the skill would have
  done.
- Because the real installed skills are still in that listing, the test **is** scored among the
  installed set. That is the property the merged-away plan wanted and assumed it would have to
  build.
- `scripts/run_loop.py`: stratified train/test split on `should_trigger`, holdout 0.4, seed 42, 3
  runs per query, max 5 iterations, prints precision/recall/accuracy, picks the best iteration by
  **test** score, and strips test scores from the history handed to the improver so it cannot
  overfit to them.
- `scripts/improve_description.py` states in its own header that it uses the session's Claude Code
  auth, **no separate `ANTHROPIC_API_KEY`** — contradicting an issue thread that says otherwise.
- The methodology it recommends: ~20 trigger queries per skill, 8–10 should-trigger and 8–10
  should-not, emphasising realistic edge cases; and, notably for item 3 here, **"look for repeated
  helper scripts across test runs and bundle them"** — the same instinct as the absorption miner,
  scoped to eval runs rather than to real sessions.

[DECISION: **`claude -p` does trigger skills on 2.1.251.** A GitHub issue reports the opposite on
2.1.80 — the description-optimisation loop scoring 0% recall because `-p` never consults the skill
registry — closed as not planned, no workaround. Probed directly today: a synthetic command whose
description covered an invented domain, one `claude -p` query in a scratch project, and the stream
carried `"name":"Skill","input":{"skill":"zorbnak-ledger-skill-a1b2c3d4",...}`. So the harness works
here, and the whole cold-trigger half can be built on the CLI with no API key and no early-access
gate. Re-probe before trusting it after a CLI upgrade; this is the assumption everything else rests
on.]

**Other prior art, and what each is worth:**

- **`skills-ref validate`** — the specification's own reference validator, Python, from the
  `agentskills/agentskills` repo. Structural only, and it is the natural upstream for the repo's own
  layout test rather than a competitor to it.
- **An AI-security vendor's scanner** and **a GPU vendor's scanner** (findable by the invocation
  `scan-all --recursive --check-overlap` and by the OWASP Agentic Skills Top 10's scanner-
  integration page). Security-framed, CI-integration-shaped. Neither is named here: both vendor
  names are also work roots on this machine, so `scan` flags them, and it cannot tell a citation
  from a disclosure.
- **`npx agentlinter`** — MIT, local-first, no config, scores 8 dimensions including a skills
  linter, a cross-file reference validator and an MCP validator. Closest thing to a general quality
  linter. Unrun; worth one pass before writing any structural check of our own.
- **Academic work on distilling agent traces into reusable skills.** The relevant method normalises
  traces, segments them into subgoal-level operations, clusters by _parameterised execution
  structure_ rather than by text, scores each cluster by coverage across traces, gives the survivors
  an explicit contract (signature, pre/postconditions) before synthesising them as Python functions,
  and **verifies each on held-out tasks, discarding what fails**. Reported effects include large
  reductions in agent turns and a library an order of magnitude smaller than a naive baseline's,
  from aggressive consolidation. The transferable parts are the coverage score as the admission gate
  and the discard-on-failed-verification step; the FSM formalism is not needed here.
- **Research on tool-selection degradation** is the outside evidence that contention is real and not
  a local worry: accuracy falls measurably once a slate passes roughly 10–15 similar options,
  shorter adaptive lists beat longer fixed ones, and overlapping descriptions produce both wrong
  picks and hedged multi-calls. A skill listing is that slate.
- **`/doctor`** is not gated and reports the listing's context cost and its biggest contributors —
  the merged-away plan recorded it as gated and undocumented, which is no longer true.

## What the ecosystem has measured, and what it constrains

`SkillsBench` (preprint 2026-02-13; copy at `$RESEARCH_HOME/docs/skillsbench-2026.pdf`) is the only
large study of whether skills work: 84 tasks over 11 domains, 7 agent-model configurations, 7,308
trajectories, with skills drawn from a deduplicated corpus of 47,150 public ones. Four findings bear
directly on this plan.

| finding                         | effect vs. no skills |
| ------------------------------- | -------------------- |
| curated skills, overall         | +16.2pp              |
| **self-generated skills**       | **−1.3pp**           |
| 1 skill provided                | +17.8pp              |
| **2–3 skills provided**         | **+18.6pp**          |
| 4+ skills provided              | +5.9pp               |
| detailed / compact skill bodies | +18.8 / +17.1pp      |
| **comprehensive skill bodies**  | **−2.9pp**           |

[DECISION: **the tool measures; it never authors unaided — but "unaided" is the operative word, not
"a model wrote it".** The −1.3pp result is a model asked to generate procedural knowledge for a task
from nothing, with no evidence loop and nothing to score it against; the paper's own reading is that
effective skills need curated domain expertise. It is _not_ evidence against an agent drafting a
description that a trigger harness then scores and a person accepts or rejects — which is what
`skill-creator`'s description tuning does, with improved triggering on 5 of 6 public skills. So the
loop is: agent drafts, harness measures against held-out cases, the user decides which version
ships. The thing to refuse is a generated skill nobody measured, not a generated sentence.]

[PITFALL: the skill-count rows measure skills **provided to the agent for one task**, not skills
installed. Claude Code lists every installed skill but loads only what it invokes, so those numbers
are suggestive for a ten-skill corpus and not conclusive about it. Quoting "2–3 is optimal, you have
ten" as though it were the same measurement would be exactly the inference this plan exists to
prevent.]

The rubric that corpus was scored on is worth adopting verbatim rather than inventing a private
scale: **Completeness, Clarity, Specificity, Examples, 0–3 each, 12 total**, ecosystem mean 6.2 (SD
2.8), top quartile ≥9. Reporting on that scale makes this repo's skills comparable to 47,150 others
instead of to nothing.

Two further results shape what the harness may conclude. **Harness behaviour is a variable, not a
constant**: Claude Code has the highest skills-utilisation rate of the three commercial CLIs
studied, while one competitor "frequently neglects provided Skills — agents acknowledge Skills
content but often implement solutions independently". And **skills partly substitute for model
scale** — a small model with skills beat a large one without. Both argue for reporting which harness
and model a measurement came from rather than stating a bare rate.

## The structure this suggests

The community has converged on a little, and diverged on the rest.

- **Flat `skills/<name>/SKILL.md` is universal.** One widely-copied community collection nests a
  `skills/meta/` category, but the `.agents/skills/` convention and the `skills` CLI are flat, so
  nesting risks discovery. [DECISION: group skills with the spec's own `metadata:` map (a
  string→string mapping, explicitly for client-defined properties) rather than by directory —
  vendor-neutral, spec-legal, and invisible to a flat installer.]
- **Two rival eval layouts exist.** `skill-creator` uses `evals/evals.json`; `claude plugin eval`
  uses `<eval dir>/**/case.yaml` with `graders/*.md`. [DECISION: author cases in the `case.yaml`
  shape. It is what the official runner will consume when its gate lifts, it is YAML rather than a
  bespoke JSON schema, and the harness we can run today reads either. Choosing the format that is
  gated is the cheap option precisely because the gate is the thing expected to change.]
- **`spec/` and `template/` at the repo root** are how the reference collection publishes its format
  and a starting skeleton. Worth copying: a `template/SKILL.md` is the concrete answer to "what does
  a new skill look like here", which `skill-authoring` currently answers only in prose.

## Recommended direction

Cheapest and most certain first. Each stage is independently useful, which matters because stage 3
is the only one that costs tokens.

1. **Make the structural gate honest.** Continuation-aware frontmatter parse, plus a regression case
   asserting a wrapped value is measured whole — test the parser, not just the corpus, so the case
   survives a corpus where nothing happens to be wrapped. Add the spec's other two constraints while
   there: non-empty, and no XML tags. Then deal with the breach it exposes, which is item 2's
   problem, not the gate's.

2. **A static analyzer: deterministic, stdlib, zero tokens, CI-gateable.** Roughly in order of
   worth:
   1. **Inventory across scopes** — user, each repo, and the bundled set where it can be seen.
      Everything else is a view over this.
   2. **Name collisions across scopes**, which are silent: one of the two is simply never seen.
   3. **Pairwise overlap**, ranked rather than gated, reporting the shared trigger terms alongside
      the score, since the terms are what gets rewritten.
   4. **Shadowing** — directional subsumption of one trigger set by another. The corpus exhibits
      this and no existing tool detects it.
   5. **Listing-budget accounting** — total bytes, per-skill contribution, and which skills are
      closest to losing their descriptions first.
   6. **`AGENTS.md` rule-heading ↔ skill-description matches**, each a demotion candidate or a
      two-sources-of-truth risk, not guessed between.
   7. **The 12-point rubric score per skill**, on the ecosystem's own dimensions, reported beside
      that corpus's mean of 6.2 and its top-quartile line of 9.

   [DECISION: **rank, never gate, for everything above the structural checks.** A similarity
   threshold either never fires or fires on everything — the AI-security vendor's hard-coded 0.7 is
   the worked example of the first — and one calibrated on ten skills will not survive twenty. A
   ranked pair list showing the shared terms needs no calibration and stays useful at any corpus
   size. Only stage 1's structural checks (cap, non-empty, no XML tags, name collisions) fail CI,
   because those have real answers rather than scores.]

3. **The cold-trigger harness**, built on `claude -p` in the shape `skill-creator` already proved:
   synthetic command file, stream-watched, killed on detection. Scored among the installed set,
   which comes free. Two departures from `skill-creator`: run cases for **a pair** the static pass
   flagged, not three per skill in isolation; and never invoke the real skill, only detect
   selection, so a `plan-docs` trigger test cannot reach the commands that enumerate client
   directories.

4. **The absorption miner**, which nothing else in the ecosystem does against _real sessions_:
   cluster `python -c` payloads by import set, then by AST shape within a cluster; rank by session
   count and project spread; and report each cluster beside the skills that were loaded in those
   sessions. Output is a candidate list — "these 7 sessions hand-rolled a transcript reader;
   `session-bash-audit` ships one" — proposed as a diff, never applied.

5. **`evals/` per skill, written only where stage 2 or 3 says one is needed.** Not 20 cases × 10
   skills as a matter of course: the static pass names the contending pairs and the never-fired
   skills, and those are where cases earn their cost. The layout is `case.yaml` + `graders/`, so the
   same files serve the official runner later.

### Where it lives

[DECISION: a **`skill-fitness`** skill owns measurement, separate from `skill-authoring`, which
keeps the authoring guidance. The merged-away plan's objection — that a contention detector would
contend with `skill-authoring`, the joke version of its own bug — is answered by the triggers being
genuinely different: "how do I write a skill / get one deployed" against "audit my skills, why isn't
this one firing, what should I split". The transcript-reading machinery is shared with
`session-bash-audit` as a module rather than copied, since that skill already reads the same store
and already declares the dependency.]

[DECISION: **accept the Claude-Code-specific signals and declare them.** Invocation stats and
listing-budget accounting are the two most valuable outputs and neither is portable.
`session-bash-audit` sets the precedent — it reads `~/.claude/projects/*.jsonl` and says so plainly
rather than failing mysteriously. The static analysis and the rubric score work anywhere; the
harness-specific sections report themselves unavailable rather than being silently absent, so a
consumer on another harness is told what they are not getting.]

## Settled by the user, 2026-08-30

- **The corpus is measured before it is restructured.** `python-conventions` stays over-cap for now;
  the split is a real authoring decision with its own contention risk, and the analyzer should be
  able to say whether the pieces would contend before anyone commits to one. Trimming to fit is
  still ruled out, because it deletes trigger vocabulary to satisfy a length check.
- **Cases are written for flagged pairs**, not twenty per skill as a matter of course.
- **Rank, don't gate**, except for the structural checks.
- **The user's working mode is the constraint on the whole design**: prompts, ideas, decisions and
  argument, not writing prose word by word. So every output of this tool has to be either a number,
  a ranked list, or a proposed diff to accept or reject — a report whose remedy is "now go write a
  better description yourself" is a report that does not land. This is what makes the
  evidence-in-the-loop decision above load-bearing rather than a nicety.

## Open questions

[NEEDS CLARIFICATION: **which similarity measure?** Ranking rather than gating removes the threshold
problem but not this one. Whole-description cosine or Jaccard mixes "what it does" prose with
trigger vocabulary; TF-IDF over the corpus itself is stdlib-implementable and weights the terms that
actually distinguish skills, but on a ten-document corpus the IDF is noisy. Whatever is chosen has
to be legible enough that the shared terms it reports are the ones worth rewriting.]

[NEEDS CLARIFICATION: **how is the trigger clause extracted, given `when_to_use` is off the table?**
Whole-description similarity mixes "what it does" prose with trigger vocabulary and only the second
should count. Candidates: the span after "Use when", the comma-separated topic list, quoted phrases.
All three are conventions this repo happens to follow and a consumer's skills may not.]

[NEEDS CLARIFICATION: **how are the bundled skills enumerated?** The listing budget is shared with
them and they are not on disk under `~/.agents/skills`. Without them the budget report is wrong in
the optimistic direction. `/doctor` knows, but it is interactive and Claude-Code-specific. Is there
a file-backed source, or does this become a number the user pastes in once?]

[NEEDS CLARIFICATION: **how much of this may depend on one harness?** The invocation stats and the
budget accounting are the two most valuable signals and both are Claude-Code-specific.
`session-bash-audit` already reads `~/.claude/projects/*.jsonl` and declares that assumption openly,
so precedent exists — but a skill whose best signals only work on one harness reports less on every
other, against this repo's stated premise.]

[NEEDS CLARIFICATION: **where do the trigger cases live, and who writes them?** `skill-creator`'s
answer is ~20 per skill in `evals/evals.json` inside the skill. Ours would be per _pair_ rather than
per skill, which has no obvious home. And the honest cadence question: 20 queries × 3 runs × 10
skills is 600 agent runs, so this cannot be on any automatic path.]

[UNVERIFIED: `npx agentlinter` has not been run against this corpus. Every statement above about it
comes from its own marketing page. Run it before writing any structural check it may already
perform.]

[UNVERIFIED: the listing budget's units. The documentation says the budget "scales at 1% of the
model's context window" and elsewhere describes it as a character budget, which are not the same
number. The total measured here (7,411 characters for ten skills) is only alarming under one of the
two readings. `/doctor`'s own estimate settles it and has not been read.]

[DEFERRED: the merged-away plan's question of whether the layout gate should also assert that an
install command in a `SKILL.md` carries `--global`. Still wanted, still mechanical, still the same
gate — and still carrying the same objection, that a bare `npx skills add ../my-skills` is
legitimate while drafting.]
