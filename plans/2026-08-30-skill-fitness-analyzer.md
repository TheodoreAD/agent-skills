---
status: in-progress
updated: 2026-08-31
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

Both paragraphs above are the documentation's account and both are **wrong in the details that
decide the outcome**. Read from the binary and measured on 2026-08-31; see "The listing budget,
measured rather than paraphrased" below.

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
- **`npx agentlinter`** — MIT, no config, scores 8 dimensions including a skills linter, a
  cross-file reference validator and an MCP validator. Described as local-first, which is not what
  it is. **Run 2026-08-31 and rejected**; the verdict and its reasons are in the open-questions
  section below.
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

## Built, and what it measured — 2026-08-31

Stages 1 to 5 are implemented. `skills/skill-fitness/` holds `scripts/fitness.py` (static, free) and
`scripts/trigger.py` (live, the only part that costs tokens), plus two eval suites.

**The static shadowing flag did not reproduce, and that is the headline.** `fitness.py overlap`
predicted `python-conventions` shadowing both `invoke-task-conventions` (coverage 0.176) and
`db-defaults` (0.139), against a corpus shadow cut of 0.089. Across 14 live cases at 3 runs each, it
stole **none of them** — including six written deliberately to sit inside the region its own
description claims ("writing, reviewing, or refactoring Python code", data modeling, settings).

[DECISION: this vindicates ranking over gating, and the plan should keep saying so. A CI gate on the
overlap score would have blocked on a hypothesis the live run refuted. The static pass is a
generator of questions worth paying to answer, and its output is never a verdict on its own.]

**The real failure is a miss, not a steal.** The one failing case was _"Our automation scripts have
grown messy and inconsistent. Where do I start cleaning them up?"_ — for which **nothing fired at
all**, three times out of three. A description written in the tool's vocabulary (`tasks.py`, `inv`,
"namespace") does not lose the request to a competitor; it loses it to silence. That is the
2026-08-22 observation this plan started from, now reproduced on demand and measurable, which it
never was before.

Then the loop closed: a candidate description adding request-side vocabulary ("automation scripts,
task runner or build commands have grown messy, inconsistent or hard to find") won that case 3/3
while taking nothing from the incumbent on the cases it already handled.

[PITFALL: **an easy suite cannot tell "no contention" from "cases too easy".** The first suite of
eight cases passed 24/24 — and every prompt in it named something only one skill claims. It was only
the second suite, phrased in the contested region, that produced a finding. This is the same warning
`skill-creator` gives about negative cases, and it applies just as hard to positives.]

[PITFALL: **a candidate description competes with its own installed twin.** Both names satisfy the
same case, so scoring them as separate skills reports a failure every time the incumbent wins. The
first candidate run reported two such failures while the case the candidate was written to fix
passed 3/3 — the proposal was working and the scoreboard said otherwise.]

**The split landed, and the whole corpus verifies.** `python-conventions` became three skills on
2026-08-31 — 411 lines of design and style, 109 of testing, 102 of MCP server internals, each with
its own rationale and snippets, all three under the 1024-char cap. `KNOWN_OVER_CAP` is empty for the
first time. Full regression against the installed set afterwards: **33 cases, 99 runs, all
passing**, across four suites. The new `mcp-python-conventions` takes nothing from
`mcp-server-shipping` (9/9) or `polite-mcp-conventions` (6/6), which were its two closest neighbours
and the real risk of adding it.

[PITFALL: **a candidate score is a lower bound, not a prediction of the shipped skill.** A proposal
is registered as a command file; a real skill is not, and selection differs. The
module-restructuring case scored 0/3 against the old wording, 1/3 as a candidate, and **3/3** once
the same wording shipped. So a candidate that clearly improves is worth adopting even below a clean
pass — and the number that settles it is a `run` against the installed set after the change lands,
never the candidate figure.]

**Both never-invoked skills are fine, and that corrects this plan's own framing.**
`mcp-server-shipping` and `polite-mcp-conventions` have zero invocations across 593 transcripts and
sit first in the listing-drop order, which this plan wrote up as a death spiral with them as the
worked example. A live suite scored them **7/7** with their existing descriptions. There had been no
demand. The budget mechanic is still real; these two were not evidence for it.

[PITFALL: **an invocation count of zero has two causes needing opposite responses** — the request
came up and the skill lost it, or the request never came up — and no usage table can separate them.
Read as a defect, a zero sends someone to rewrite a description that works. The only thing that
answers it is a trigger suite phrased in the words a request would actually use.]

[DECISION: **no automated demand proxy; it was built twice and removed.** Counting sessions whose
user turns contained three or more of a skill's distinctive terms gave 370–430 for all eleven skills
across 593 transcripts, including one written that day. Tightening it to per-turn matches on terms
claimed by at most two skills made the numbers larger rather than sharper. Skill descriptions share
too much ordinary technical English — "install", "command", "check", "repo" — for a bag-of-words
proxy to separate them. Both constructions are recorded in `fitness.py` where the function used to
be, so the next person does not rebuild them. This is the third check this session that could not
discriminate, after the vendor's Jaccard 0.7 and this tool's own first absolute shadow cut; the
pattern is free heuristics over prose, and the fix each time was either a corpus-relative measure or
paying for a real run.]

[DECISION: **cases are JSON, reversing this plan's earlier choice of `case.yaml`.** The reason for
`case.yaml` was forward-compatibility with the still-gated official runner, and that reason stands —
but this family's skills are stdlib-only, there is no YAML parser in the standard library, and
hand-rolling one for prompts full of colons is precisely the ad-hoc-script pattern `absorb` exists
to detect. Converting is mechanical once that runner is usable.]

## The listing budget, measured rather than paraphrased — 2026-08-31

The budget section had been written from the documentation and from `/doctor`'s description. Both
were read this pass out of the Claude Code 2.1.251 binary itself and confirmed against the CLI's own
overflow warning. The mechanism is materially different from the account above, in ways that change
who gets hurt.

| the question         | the answer, from the binary                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------- |
| what units           | **characters**: `context_window_tokens × 4 × skillListingBudgetFraction` (default 0.01)              |
| the number           | **8,000 characters on a 200k-token model**; the env var `SLASH_COMMAND_TOOL_CHAR_BUDGET` is absolute |
| what an entry costs  | `- <name>: <description>`, description capped at `skillListingMaxDescChars` (1536), plus 1 per gap   |
| who can be truncated | **only user and project skills** — a bundled skill is exempt                                         |
| what truncation does | drops the description **whole**; the entry becomes `- <name>`. Nothing is "shortened"                |
| the order            | descending `usageCount × max(0.5^(days_since_last_use / 7), 0.1)`, from `~/.claude.json`             |
| and it is greedy     | each entry keeps its description if the room left allows, so a long one is dropped past a short one  |

[DECISION: **the budget is model-dependent, and that is the headline.** The same corpus is
comfortable on a large-window model and truncated on a 200k one. Measured the same hour: this
machine's listing is **15,486 characters over 25 entries**, which drew the overflow warning under
`--model claude-haiku-4-5-20251001` (8,000 budget) and no warning at all on the session's own model.
So "is my listing over budget" has no machine-wide answer — every report has to name the window it
assumed, which is why `fitness.py budget` takes `--context-window` and defaults to the pessimistic
200,000.]

[PITFALL: **the bundled skills' cost is not shared pain — it is taken off the top.** They are
charged first and never demoted, so the 5,912 characters of bundled entries on this machine come
straight out of the 8,000 available to the user's own thirteen. The simulation says that on a 200k
model **eleven of thirteen are demoted to name-only**, leaving only `session-harvest` and
`research-library` with descriptions. Every claim this plan made about a death spiral was
directionally right and quantitatively far too mild.]

[PITFALL: **priority is decayed usage, not the invocation count this plan kept reasoning about.**
Recency dominates at a 7-day half-life, so a skill used thirty times two months ago scores 3 and
sits below one used four times yesterday. The 0.1 floor is the only thing keeping a long-unused
favourite ahead of a never-used skill. A ranking built from raw transcript counts would put the
wrong skills at the top of the at-risk table.]

[DECISION: **the listings the harness sent are in the transcript store, and reading them back beats
every model of the budget — including this plan's own.** Each `skill_listing` attachment carries the
rendered text, the entry count and the names, so a demoted entry is visible as a bare `- name`.
Free, exact, and retrospective. It immediately corrected two things stated above as settled: the
exempt set is **not** every bundled entry (`security-review` demoted in a real listing while
`code-review`, `run` and `init` kept their descriptions, so exemption is not derivable from origin),
and the interactive listing is **18,109 characters over 30 entries**, not the probe's 15,486
over 25. The simulation stays for forecasting a corpus or a model that has not run yet; where the
two disagree, the simulation is the one that is wrong.]

[PITFALL: **half the recorded listings are this tool measuring itself** — 541 of 1,086 come from
`trigger.py`'s scratch directories. Listings from a temporary working directory are counted
separately rather than dropped, because the same bucket also holds real headless pipeline runs. This
is the third form the probe-contamination problem has taken, after the synthetic skill in the usage
counts and the `zorbnak-ledger` entry in the harness's own `skillUsage` map.]

**And the bundled-enumeration question is answered without enumerating them.** The bundled skills
are compiled into the CLI binary, so no file-based inventory can price them — but subtracting the
installed set from a listing the harness really sent leaves exactly that remainder. Free,
reproducible, and it does not become a number the user pastes in.

[DECISION: **the live probe that first answered this was built and then removed the same day.** It
forced `SLASH_COMMAND_TOOL_CHAR_BUDGET=1` so the CLI would log
`Skill listing over budget: N skills, C chars > B budget`, read that from `--debug-file`, and killed
the run. It worked. It was still worse than reading a recorded listing on three counts at once: it
was the only part of `fitness.py` that spent tokens; it ran headless, where fewer entries are
listed, so it under-reported by ~2,600 characters and would have justified a `0.02` budget setting
that does not actually fit; and each run entered the transcript store as a truncated listing, so the
tool contaminated the corpus it reads. The removal is recorded in `exempt_from_observed`'s docstring
rather than only here, because the probe is an obvious thing to reinvent.]

**Acted on the same day, and it is not this repo's change to make.** `claude-opus-5`,
`claude-sonnet-5` and `claude-fable-5` all fit the listing; `claude-haiku-4-5` is the only model
that overflows. The remedy is a `skillListingBudgetFraction` of 0.03 declared in
`power-user-linux-setup`'s `setup.toml` and synced the way `claude_default_mode` already is, so it
reaches the next machine rather than one file on this one. Filed there as
`2026-08-31-skill-listing-budget-truncates-subagents.md`.

[PITFALL: **the urgency in the first version of that filing was manufactured by a sampling error,
and the error is the lesson.** It said the overflow hits "the whole subagent tier, 181 of 443
transcripts". The 181 figure was sessions whose dominant model is `haiku-4-5`; the largest few were
inspected, they were `agent-*` subagents doing real work, and the set was described from them. The
set is not like its largest members. Cross-tabulated properly: **168 of those 181 are headless runs
under a temporary directory** — this tool's own `trigger.py` probes and the allowlist pipeline's
`claude -p` calls — averaging four assistant messages. Real subagents run on `sonnet-5`, 71 sessions
against 13, and `sonnet-5` fits the listing. This is the "generalizing from a sample" failure with a
worked example: the sample was self-selected by size, the outliers were the whole finding, and a
recommendation was filed on it before anything cross-checked the set.]

The corrected exposure, now read from the listings the harness actually sent rather than from a
model of them: **truncation has occurred in real work exactly twice**, both `agent-*` sessions on
2026-08-22, CLI 2.1.237, when the corpus and the harness were both different. Nine further
truncations are recorded and every one of them is a probe or a pipeline run in a scratch directory —
six from `power-user-linux-setup`'s allowlist runs, three from this session's own budget probes. So
the mechanism is real, it has fired, and it currently fires on nothing: every model in use clears
the listing. It becomes live again if a 200k-window model returns to real use, or if the listing
grows past the larger windows' budget.

The counter-evidence stays worth keeping: across 84 `agent-*` transcripts there are **zero** `Skill`
calls, and the data cannot say whether that is truncation, the subagent types defined without the
`Skill` tool at all, or no demand.

The levers, now that the mechanism is known rather than guessed: `skillListingBudgetFraction` and
`skillListingMaxDescChars` raise the two caps; `disableBundledSkills` (or
`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS`) removes the exempt entries that are taking the top off the
budget; and `skillOverrides` takes four values per skill — `on`, `name-only` (listed without its
description, deliberately, to free budget for the rest), `user-invocable-only` (still typable as
`/name`, hidden from the model) and `off`. The last is the interesting one for this corpus: a skill
the user only ever types is paying full listing price for a description no model needs.

[PITFALL: **the debug log is the only place this is visible non-interactively, and only on
overflow.** A plain `claude -p ... --debug` printed nothing — the warning goes to the log file, not
to stderr — and it is not emitted at all when the listing fits, which is why the probe had to force
a budget of 1 rather than read the real one. The line also reports the count of _listed_ entries,
which is smaller than the count of _loaded_ skills: 13 user plus 42 bundled were loaded here and 25
were listed. That gap is why a headless measurement under-reports an interactive listing, and is
half the reason the probe was removed.]

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

[RESOLVED 2026-08-31: **which similarity measure?** It does not matter on a corpus this size, which
is a measured answer rather than a shrug. IDF-weighted and unweighted variants were ranked against
each other over all 78 pairs: **they agree on seven of the top eight**, by similarity and by
containment alike, and the disagreements are reorderings inside a near-tied band. So the measure is
not what limits the signal. The IDF weighting stays, because it also supplies the corpus-derived
stop list and because it costs nothing — not because it was shown to be better.]

[RESOLVED 2026-08-31: **how is the trigger clause extracted?** It is not, and the attempt was
deleted. `Skill.trigger_text` took the span from a `Use when` lead-in onward; measured against the
installed corpus it **stripped nothing from 12 of 13 descriptions and three characters from the
thirteenth**, because this repo's own convention puts the trigger clause first, so the lead-in
matches at position zero. The prose it was meant to exclude _trails_ the trigger clause, and
locating that boundary means guessing at sentence openers ("Covers", "Also", "For X see Y") — which
is the same repo-specific fragility that ruled out adopting a `when_to_use` field. Similarity now
runs on the whole description and says so.]

[PITFALL: **the audit those two answers came from is unflattering and belongs next to them.** Three
measurements on this corpus, same day: the trigger extraction stripped nothing; the corpus-derived
stop list dropped exactly one term (`instead`) because its cut needs a term in half the corpus and
prose spreads thinner than that; and the single static shadowing prediction ever tested live was
refuted, 0 steals in 14 cases. The visible symptom is that the shared-term lists are ordinary
English — `working`, `writing`, `rather`, `before`, `asking`. The ranking is still worth having as a
way to choose which pair to pay for a live run on. It is not evidence about that pair, and the skill
now says so in those words. What would actually raise the signal is a bigger corpus (the stop list
strengthens with it) or phrase-level terms rather than single words — untested, and testable only by
the live runs it would be trying to save.]

[RESOLVED 2026-08-31: **how are the bundled skills enumerated?** They are not, and they do not need
to be. `budget` subtracts the installed set from a listing the harness really sent and reports the
remainder; see "The listing budget, measured rather than paraphrased". Enumerating them _is_
possible — each bundled skill's description sits in the binary as a `var name` / `var description`
pair — but that is a scrape of a compiled artifact with no stable shape across versions, and the
subtraction needs neither it nor a probe.]

[NEEDS CLARIFICATION: **how much of this may depend on one harness?** The invocation stats and the
budget accounting are the two most valuable signals and both are Claude-Code-specific.
`session-bash-audit` already reads `~/.claude/projects/*.jsonl` and declares that assumption openly,
so precedent exists — but a skill whose best signals only work on one harness reports less on every
other, against this repo's stated premise.]

[NEEDS CLARIFICATION: **where do the trigger cases live, and who writes them?** `skill-creator`'s
answer is ~20 per skill in `evals/evals.json` inside the skill. Ours would be per _pair_ rather than
per skill, which has no obvious home. And the honest cadence question: 20 queries × 3 runs × 10
skills is 600 agent runs, so this cannot be on any automatic path.]

[RESOLVED 2026-08-31: `npx agentlinter` was run against this corpus (v0.3.3, MIT, no dependencies,
last published 2026-02-08 — seven months stale, so "actively maintained" was the marketing page's
claim and not a fact). **Nothing to adopt.** Score 80/100 over 26 files, and every finding is either
already gated here or actively wrong for this repo. Details below, because "we checked and it was
useless" is only worth recording with the reasons attached.]

- **It never looks at what a description triggers on.** No overlap, no contention, no listing
  budget, no invocation data — it scores prose hygiene over `CLAUDE.md`/`AGENTS.md` and skill
  frontmatter. It is not a competitor to any part of `fitness.py`, and there is no structural check
  in it that the repo's own layout test does not already do better.
- **Its 11 "duplicate instruction" warnings are an artefact of this machine's own convention.**
  `CLAUDE.md` is a symlink to `AGENTS.md`, so the linter read one file twice and reported every rule
  in it as duplicated across two files. Any tool that walks a file list without resolving symlinks
  will do this; worth knowing before trusting a cross-file check from anyone.
- **`clarity/escape-hatch-missing` is advice this repo must not take.** It fired 14 times, including
  on the heading `## This repo is published: never name a client in it`, and its proposed fix is to
  append "unless the user explicitly requests it". That would soften the one rule here whose whole
  value is being absolute, and it is the exact inverse of this repo's own instruction to
  _strengthen_ a rule that gets missed. It also fires on headings rather than rules, so it cannot
  tell a section title from an imperative.
- **Its completeness suggestions are vendor artefacts** — `SOUL.md`, `TOOLS.md`, and a
  `clawdbot.json` / `openclaw.json` runtime config. This repo admits only vendor-neutral formats, so
  three of its eight scored dimensions are unreachable here by design.
- **Its only skill-level check is an `author` frontmatter field**, which the Agent Skills
  specification does not define. All 12 "Skill Safety" issues were that one tip repeated.

[PITFALL: **its default mode uploads the report** — `npx agentlinter` is documented as "Lint & share
report (default)", with `--local` to opt out. It was run with `--local` pinned. A quality linter
that publishes a repo's instruction files unless told otherwise is worth naming as a hazard rather
than as a footnote, because the obvious invocation is the sharing one.]

[RESOLVED 2026-08-31: the listing budget's units. Both readings are right and they compose: the
budget is in **characters**, at 1% of the context window measured in **tokens**, converted at four
characters per token. 8,000 characters on a 200k model. The two readings were never in conflict; the
missing term was the conversion, and it is what makes the budget model-dependent.]

[DEFERRED: the merged-away plan's question of whether the layout gate should also assert that an
install command in a `SKILL.md` carries `--global`. Still wanted, still mechanical, still the same
gate — and still carrying the same objection, that a bare `npx skills add ../my-skills` is
legitimate while drafting.]
