# Skill fitness — prior art and what the ecosystem has measured

Background behind `SKILL.md`. Everything here is **external**: published measurements, other
people's tools, and facts about the harness that a reader can check independently. Local
measurements taken on the author's machine live in [`measurements.md`](measurements.md) instead,
because the two age differently — this file goes stale when the ecosystem moves, that one when the
machine does.

Load this when deciding whether to build something, adopt someone else's tool, or argue about
whether skills work at all. `SKILL.md` carries the rules; this carries the reasons.

## Contents

- [SkillsBench: the only large study of whether skills help](#skillsbench-the-only-large-study-of-whether-skills-help)
- [The quality rubric worth reporting on](#the-quality-rubric-worth-reporting-on)
- [`skill-creator`, the closest prior art](#skill-creator-the-closest-prior-art)
- [Tools that look like this one and are not](#tools-that-look-like-this-one-and-are-not)
- [Academic work on distilling traces into skills](#academic-work-on-distilling-traces-into-skills)
- [Why tool-selection research makes contention worth measuring](#why-tool-selection-research-makes-contention-worth-measuring)
- [Two description caps, and which one to gate on](#two-description-caps-and-which-one-to-gate-on)
- [Why `when_to_use` is off the table](#why-when_to_use-is-off-the-table)

## SkillsBench: the only large study of whether skills help

Preprint 2026-02-13; copy at `$RESEARCH_HOME/docs/skillsbench-2026.pdf`. 84 tasks over 11 domains, 7
agent-model configurations, 7,308 trajectories, with skills drawn from a deduplicated corpus of
**47,150 public skills**.

| finding                         | effect vs. no skills |
| ------------------------------- | -------------------- |
| curated skills, overall         | +16.2pp              |
| **self-generated skills**       | **−1.3pp**           |
| 1 skill provided                | +17.8pp              |
| **2–3 skills provided**         | **+18.6pp**          |
| 4+ skills provided              | +5.9pp               |
| detailed / compact skill bodies | +18.8 / +17.1pp      |
| **comprehensive skill bodies**  | **−2.9pp**           |

**The −1.3pp result is about authoring _unaided_, not about a model writing a sentence.** It
measures a model asked to generate procedural knowledge for a task from nothing, with no evidence
loop and nothing to score against; the paper's own reading is that effective skills need curated
domain expertise. It is not evidence against an agent drafting a description that a harness then
scores and a person accepts or rejects. That distinction is what makes this skill's whole loop
legitimate: **agent drafts → harness measures against held-out cases → the user decides what
ships.** The thing to refuse is a generated skill nobody measured, never a generated sentence.

[PITFALL: **the skill-count rows measure skills provided for one task, not skills installed.**
Claude Code lists every installed skill but loads only what it invokes, so those numbers are
suggestive for a ten-skill corpus and not conclusive about it. Quoting "2–3 is optimal, you have
thirteen" as if it were the same measurement is exactly the inference this skill exists to prevent.
Read them as an argument for sharp boundaries, not for deleting skills.]

Two further results shape what any measurement here may claim:

- **Harness behaviour is a variable, not a constant.** Claude Code had the highest skills-
  utilisation rate of the three commercial CLIs studied, while one competitor "frequently neglects
  provided Skills — agents acknowledge Skills content but often implement solutions independently".
- **Skills partly substitute for model scale** — a small model with skills beat a large one without.

Both argue for reporting which harness and model a measurement came from rather than stating a bare
rate.

## The quality rubric worth reporting on

The 47,150-skill corpus was scored on **Completeness, Clarity, Specificity, Examples, 0–3 each, 12
total**. Ecosystem mean **6.2** (SD 2.8); top quartile begins at **9**.

Worth adopting verbatim rather than inventing a private scale, because reporting on it makes a skill
comparable to 47,150 others instead of to nothing. Report the four sub-scores, not just the total —
the remedy differs per dimension. `fitness.py` deliberately does not compute this: it is judgement,
and a heuristic pretending to be a rubric score is worse than no score.

## `skill-creator`, the closest prior art

Public at `anthropics/skills`, cloned to the research library. What it actually does, from source
rather than from its docs:

- **`scripts/run_eval.py`** writes a synthetic command file into
  `.claude/commands/<name>-skill-
  <uuid>.md` carrying only the candidate description, runs
  `claude -p <query>` with `--output-format stream-json --include-partial-messages`, and watches the
  stream for a `content_block_start` naming the `Skill` tool with that id. It kills the run the
  moment it detects one, so a trigger test never pays for the work the skill would have done.
- Because the real installed skills are still in that listing, **the test is scored among the
  installed set** — the property that matters most, and it comes free.
- **`scripts/run_loop.py`**: stratified train/test split on `should_trigger`, holdout 0.4, seed 42,
  3 runs per query, max 5 iterations. Picks the best iteration by **test** score and strips test
  scores from the history handed to the improver, so it cannot overfit to them.
- **`scripts/improve_description.py`** states in its own header that it uses the session's Claude
  Code auth, **no separate `ANTHROPIC_API_KEY`** — contradicting an issue thread that says
  otherwise.
- Its recommended methodology: ~20 trigger queries per skill, 8–10 should-trigger and 8–10
  should-not, emphasising realistic edge cases. And, notably for the absorption miner, **"look for
  repeated helper scripts across test runs and bundle them"** — the same instinct, scoped to eval
  runs rather than to real sessions.

`trigger.py` is built in this shape, with two deliberate departures: cases are written for **a
pair** the static pass flagged rather than three per skill in isolation, and the real skill is never
invoked, only selection is detected — so a trigger test for a skill whose commands enumerate private
directories cannot print them.

## Tools that look like this one and are not

- **`skills-ref validate`** — the specification's own reference validator, Python, from the
  `agentskills/agentskills` repo. Structural only, and the natural upstream for this repo's layout
  test rather than a competitor to it.
- **An AI-security vendor's scanner** and **a GPU vendor's scanner**, findable by the invocation
  `scan-all --recursive --check-overlap` and by the OWASP Agentic Skills Top 10's scanner-
  integration page. Neither is named here: both vendor names are also work roots on this machine, so
  `plans.py scan` flags them and cannot tell a citation from a disclosure.

  The first was read from source rather than run. Its `_check_description_overlap` is **Jaccard
  similarity over the whole description's stop-word-filtered token set, hard-coded threshold 0.7,
  symmetric only.** On prose descriptions two skills would have to share 70% of their vocabulary to
  fire, so on a real corpus it is close to a no-op — and it detects no shadowing at all, because
  Jaccard cannot express subsumption. It is security-framed (`TRIGGER_OVERLAP_RISK`, severity
  MEDIUM, category social-engineering). This is the worked example behind "rank, never gate".
- **`npx agentlinter`** — MIT, no dependencies. **Run 2026-08-31 against this corpus and rejected.**
  Score 80/100 over 26 files, and nothing worth adopting:
  - It never looks at what a description triggers on — no overlap, no contention, no listing budget.
    It scores prose hygiene over instruction files, so it is not a competitor to any part of
    `fitness.py`.
  - Its 11 "duplicate instruction" warnings were an artefact of `CLAUDE.md` being a symlink to
    `AGENTS.md`: it read one file twice and reported every rule as duplicated. Any tool that walks a
    file list without resolving symlinks does this.
  - `clarity/escape-hatch-missing` fired 14 times, including on the heading
    `## This repo is published: never name a client in it`, proposing to append "unless the user
    explicitly requests it". That is the inverse of this repo's own rule to _strengthen_ a rule that
    gets missed, and it fires on headings, so it cannot tell a section title from an imperative.
  - Three of its eight dimensions score vendor artefacts this repo does not admit — `SOUL.md`,
    `TOOLS.md`, a `clawdbot.json` / `openclaw.json` runtime config.
  - Its only skill-level check is an `author` frontmatter field the specification does not define.

  [PITFALL: **its default mode uploads the report.** `npx agentlinter` is documented as "Lint &
  share report (default)", with `--local` to opt out. A quality linter that publishes a repo's
  instruction files unless told otherwise is worth naming as a hazard, because the obvious
  invocation is the sharing one. Last published 2026-02-08, so "actively maintained" was its
  marketing page's claim and not a fact.]
- **`claude plugin eval`** — still early-access gated on CLI 2.1.251. `--help` renders in full,
  which is misleading; `claude plugin eval .` answers "`plugin eval` is currently in early access"
  and exits. Its report publishes to claude.ai by default. Nothing to build on yet.

## Academic work on distilling traces into skills

The relevant method normalises agent traces, segments them into subgoal-level operations, clusters
by _parameterised execution structure_ rather than by text, scores each cluster by coverage across
traces, gives the survivors an explicit contract (signature, pre/postconditions) before synthesising
them as Python functions, and **verifies each on held-out tasks, discarding what fails**. Reported
effects include large reductions in agent turns and a library an order of magnitude smaller than a
naive baseline's, from aggressive consolidation.

The transferable parts are **the coverage score as the admission gate** and **the discard-on-failed-
verification step**, both of which the absorption miner uses. The FSM formalism is not needed here.

## Why tool-selection research makes contention worth measuring

Outside evidence that contention is a real phenomenon and not a local worry: selection accuracy
falls measurably once a slate passes roughly 10–15 similar options, shorter adaptive lists beat
longer fixed ones, and overlapping descriptions produce both wrong picks and hedged multi-calls. A
skill listing is that slate.

Worth holding alongside this repo's own finding that contention, while real in principle, was
**not** what failed in 119 measured runs — see `measurements.md`. Both can be true: the research
says a crowded slate degrades selection, and this corpus is not yet crowded enough for that to be
its problem.

## Two description caps, and which one to gate on

Both are real and they answer different questions:

| cap      | whose                 | what it governs                                                                                                |
| -------- | --------------------- | -------------------------------------------------------------------------------------------------------------- |
| **1024** | the Agent Skills spec | validity: `description` must be 1–1024 chars, non-empty, no XML tags                                           |
| **1536** | Claude Code           | rendering: `description` + `when_to_use` truncated in the listing, configurable via `skillListingMaxDescChars` |

Gate on **1024** — it is the tighter one and the one that makes a skill valid everywhere. A repo
comment calling 1024 "Claude Code's documented cap" is wrong; Claude Code truncates later and
budgets separately.

## Why `when_to_use` is off the table

Claude Code offers a dedicated frontmatter field for trigger phrases. It would neatly separate "what
it does" from "when to use it" and make trigger-only similarity directly measurable — which is the
one thing that would have rescued the trigger-clause extraction described in `measurements.md`.

It is **not in the vendor-neutral specification**, so adopting it is exactly the vendor coupling
this repo's `AGENTS.md` rules out. Trigger vocabulary stays inside `description`, and any analyzer
has to work with the whole field.
