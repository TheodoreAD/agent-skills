---
name: skill-fitness
description: >-
  Use when asking whether installed skills are actually working — why a skill never fires or fires
  on the wrong requests, which two skills compete for the same request, what the skill listing is
  costing in context and which skill loses its description first, which skills have never been
  invoked at all, or which repeated one-off scripts an agent keeps writing should become code
  inside a skill. Also for scoring a skill against the published quality rubric before shipping it,
  and for deciding whether a skill that has grown too big, or covers several different things at
  once, should be broken up or split into separate skills. Measures an installed set from
  frontmatter and from the session transcript store; it does not teach how to write or deploy a
  skill.
---

# Skill fitness

Measures whether a set of skills works, so the fix is chosen from numbers rather than from a hunch.
Authoring guidance is `skill-authoring`'s job and this skill does not repeat it; Bash-usage auditing
is `session-bash-audit`'s.

Evidence behind the rules below, loaded only when you need it:
[`references/measurements.md`](references/measurements.md) for what was measured here — the 119-run
trigger ledger, the listing budget read from the binary, and the ledger of five heuristics that
failed; [`references/research.md`](references/research.md) for published work and other people's
tools — SkillsBench, the quality rubric, `skill-creator`, and what the scanners in this space do and
do not detect.

## The one rule that shapes everything here

**Never ship a skill, or a description, that nothing measured.** `SkillsBench` (84 tasks, 7,308
trajectories, across a deduplicated corpus of 47,150 public skills) found model-authored skills
scoring **−1.3pp against having no skill at all**, while human-curated ones scored **+16.2pp**. The
failure was authoring _unaided_ — generating procedural knowledge with nothing to score it against.

So drafting a candidate description is fine and often the right move; shipping it without running
the trigger check is not. The loop is: draft → measure → a person decides which version ships.

## Start here

```shell
python3 <this skill>/scripts/fitness.py report
```

Read-only, stdlib, deterministic, no tokens. Every sub-command takes `--json`.

**`report` runs the three sections whose remedy belongs to whoever ran it, and no others.** The
other four all end in "edit the skill" — which a reader who merely _installed_ it must not do, since
editing a deployed copy is drift that reaches nothing — so they have to be asked for by name.

| the question                                    | the command   | whose remedy     |
| ----------------------------------------------- | ------------- | ---------------- |
| what is installed, and from where               | `inventory`   | the runner's     |
| what is the listing costing, and who is at risk | `budget`      | the runner's     |
| what actually gets invoked                      | `usage`       | the runner's     |
| those three, in reading order                   | `report`      | the runner's     |
| which skills compete for the same request       | `overlap`     | **the author's** |
| what one-liners should be skill code            | `absorb`      | **the author's** |
| what a skill makes an agent compose by hand     | `derivable`   | **the author's** |
| what a skill assumes about its reader's machine | `portability` | **the author's** |

That split is a property of the **command**, never of the corpus in front of it. A rule that
inspected the roots instead would behave one way on the author's machine — where the hub and the
checkout hold the same names — and another way everywhere else, which is the exact class of bug it
exists to prevent.

**Every run names the corpus it measured, and you should read that line first.** A count is a
statement about a specific set of files, and this tool can be aimed at populations that routinely
disagree: measured on one machine 2026-09-03, with a clean working tree and nothing unusual
happening, the checkout, `origin` and the install differed from each other.

```text
corpus: working tree — /home/you/projects/agent-skills/skills
corpus: installed — /home/you/.agents/skills
        deployed copies — not yours to edit; a fix belongs to the skill's author
```

By default it reads `./skills` **first** when run from a skills repo, then `~/.agents/skills` and
`~/.claude/skills`. The order matters and is not cosmetic: resolution is first-occurrence-wins, so
before the repo was moved to the front, a bare run inside a checkout silently measured the installed
copies instead of the files being edited. `--root <dir>` (repeatable) replaces the whole set — use
it to score a corpus you do not have installed. `budget` also takes `--context-window <tokens>`,
explained below.

## Reading the output

**`budget` is ordered by who loses their description first, and that order is the finding.** Claude
Code loads a listing of every skill's name and description; when it does not fit, a user skill is
demoted to name-only, so it cannot be matched, so it stays at zero invocations and stays first in
line to be demoted again. A skill at the top of that table with a large `listing_chars` is the one
to act on.

Four properties of that mechanism decide the answer, and three of them are easy to guess wrong. Read
from the Claude Code 2.1.251 binary on 2026-08-31 and confirmed against the CLI's own overflow
warning; re-check after an upgrade, since none of it is documented behaviour.

- **The budget is model-dependent.** It is a _character_ budget, computed as 1% of the context
  window in tokens times four. A 200k-window model gets 8,000 characters. So the same corpus can be
  comfortable in the main session and truncated in a subagent on a smaller model — pass
  `--context-window` for the model you care about, and treat the default 200,000 as the pessimistic
  case rather than the wrong one.
- **Most of the harness's own entries are exempt.** They are charged against the budget first and
  never demoted, so their cost is not shared pain — it comes off the top of what is left for yours.
  Measured on this machine: **8,530 characters of them against a 200k-model budget of 8,000** — over
  the whole budget before any of the user's thirteen skills is priced. **The exempt set is narrower
  than "the harness shipped it", and is not derivable from a skill's origin**: in a real listing on
  2026-08-31, `security-review` was demoted while `code-review`, `run` and `init` kept their
  descriptions. Read an observed listing rather than reasoning about which entries qualify.
- **Demotion is a greedy fit, not a cut-off.** Entries are walked in descending priority and each
  keeps its description if the room left allows, so a long description is dropped while a shorter,
  _lower_-priority one survives. The demoted set is not the bottom of the table.
- **Priority is decayed usage, not the invocation count**: `usageCount × max(0.5^(days/7), 0.1)`,
  from the harness's own `skillUsage` map in `~/.claude.json`. Recency dominates — thirty uses two
  months ago scores 3, below four uses yesterday — and the floor is what keeps a long-unused
  favourite ahead of a never-used skill.

**`listings actually sent` outranks everything above it, and is free.** The transcript store keeps
each `skill_listing` attachment verbatim — the rendered text, the entry count, the names — so the
report reads back what the harness really sent rather than modelling it. A demoted entry is visible
as a bare `- name`, so the death spiral is observable rather than inferred. Where that section and
the simulation disagree, the simulation is what is wrong: it is how the exemption error above was
caught. The harness's own entries are priced the same way — subtract the installed skills from the
largest untruncated real listing and the remainder is what this tool cannot see, at no cost.

[A live probe did that job and was **removed on 2026-08-31**. It ran `claude -p` with the budget
forced to 1 so the CLI would log its listing size. It worked, and it was worse in three ways at
once: it was the only part of `fitness.py` that spent tokens; it ran headless, where fewer entries
are listed, so it under-reported the real listing by about 2,600 characters and would have talked
someone into a budget setting that does not fit; and its own runs entered the transcript store as
truncated listings, so the tool contaminated the corpus it reads every time it was used. Do not
reintroduce it.]

Read that section with two cautions:

- **Truncation being rare is not the mechanism being harmless**, and neither is the reverse. It
  fires only when a listing exceeds that session's model budget, so a corpus can sit one skill away
  from truncation for months and record nothing.
- **This tool's own probes dominate the raw count.** Measured here: 1,086 listings recorded, of
  which 541 came from `trigger.py`'s scratch directories. Listings captured under a temporary
  working directory are counted separately for that reason — a probe is not a session, and a report
  that mixes them measures the measuring.

**`usage` counts two mechanisms and neither alone is the rate.** `auto` is the model choosing the
skill through the `Skill` tool. `explicit` is a person typing `/name`, which often injects the body
directly and produces no tool call at all. Measured 2026-08-30: one skill showed 11 auto against 84
explicit, another 69 against 12 — opposite stories, and either column read alone gives the wrong
one.

**A high `explicit` count is a hypothesis, not a diagnosis**, and it failed its first test here.
"The person keeps having to ask for it by name" is the obvious reading, so the corpus's one inverted
skill — 13 auto against 87 explicit, where its neighbour ran 70 against 15 — got a suite built as a
controlled comparison: the description's own trigger phrasings as the control, the same needs in a
person's words as the test, two of those lifted from real transcripts. **10/10.** Controls and
paraphrases alike, precision 1.0, nothing stolen and nothing fired on the should-not-trigger cases.
The description opens "Use when invoked explicitly as `/name`" and every auto-trigger phrasing it
lists works; the split was the skill behaving as designed plus a person's habit. Read the column as
a reason to write a suite, never as the finding itself.

**A zero is not a verdict, and treating it as one wastes the effort it seems to demand.** It means
either the request came up and this skill lost it, or the request never came up — opposite problems,
and no invocation count can separate them. Confirmed 2026-08-31: this repo's two never-invoked
skills looked like the worst cases in the corpus, and a live trigger suite scored them **7/7** with
their existing descriptions. There had simply been no demand. Rewriting them would have damaged two
descriptions that work.

Resist the free heuristic here. Inferring demand from whether a skill's vocabulary appears in past
requests was built twice and measured nothing both times — skill descriptions share too much
ordinary technical English for a bag-of-words proxy to separate them, and the first version reported
comparable "demand" for all eleven skills including one written that day. The answer that works is
the one that costs something: write a few cases in the words a request would actually use, and run
them.

**`overlap` ranks, it never gates.** Similarity between prose descriptions is low in absolute terms,
so any fixed cutoff either never fires or fires on everything — an AI-security scanner in this space
uses Jaccard > 0.7, which on real descriptions is close to never, and this script's own first draft
used an absolute 0.5 and flagged nothing. Shadowing is therefore judged against the corpus's own
distribution and the numbers are always printed, because the judgement is the reader's.

**Treat it as a way to choose which pair to spend a live run on, never as a finding.** That is not
modesty; it is what the audit of 2026-08-31 measured on this corpus:

| the mechanism                                        | what it actually did           |
| ---------------------------------------------------- | ------------------------------ |
| isolating the trigger clause from the description    | stripped nothing from 12 of 13 |
| the corpus-derived stop list, on 13 skills           | dropped one term               |
| the one static shadowing prediction ever tested live | refuted, 0 steals in 14 cases  |

The consequence is visible in the output: the shared-term lists are full of ordinary English —
`working`, `writing`, `rather`, `before`, `asking` — because nothing in a small corpus removes it.
The ranking still orders pairs sensibly, and both an IDF-weighted and an unweighted measure pick the
same seven of the top eight pairs, so the choice of measure is not what is limiting it. Corpus size
is. Read the rank, then go and measure the pair.

Three distinct failures hide under "skills competing", and each has a different fix:

| term          | shape                                                 | what to do                         |
| ------------- | ----------------------------------------------------- | ---------------------------------- |
| **overlap**   | two descriptions share trigger vocabulary             | redraw the boundary, not the prose |
| **shadowing** | A's trigger set subsumes B's, so B rarely wins        | narrow A, or merge B into it       |
| **collision** | the same `name` in two scopes, with different content | `inventory` reports it; see below  |

`a_covers_b` is directional and is what detects shadowing — a symmetric measure cannot express
subsumption at all, which is why the vendor scanners miss it.

**`inventory` reports a collision only when the two copies differ**, and that is the useful case: it
means one of them is stale, which is usually an installed copy that has drifted behind its source
and behaves like an older version of itself. The same name appearing in a skills repo and in the
install it produced is a duplicate, not a finding, and a `~/.claude/skills` symlinked to
`~/.agents/skills` is one directory arriving twice. Reporting those made the first run emit twenty
findings carrying no information, which is how a check gets ignored.

**`absorb` finds work a skill should have owned.** It clusters ad-hoc `python -c` payloads from the
transcript store by import set, then by AST shape within a cluster. A cluster spanning many sessions
and several projects is the agent re-solving one problem inline instead of running a script.

**Read `shapes` before `calls`, and distrust the printed example until you have.** The clustering
key is the import set, which is deliberately coarse; the example shown is the shortest payload in
the cluster, not a description of it. A cluster whose shape count approaches its call count is one
import set, not one repeated script — the label says which. Confirmed 2026-09-01, and it nearly
produced a false finding in a review: the top two clusters read `148 calls / 26 sessions` and
`146 / 25`, and carried **106 and 119 distinct shapes** — 106 different one-liners that happen to
import `json` and `sys`. Chasing the example's actual shape through the store found **3 calls in 3
sessions**. The dense clusters are the findings; the big ones are the vocabulary. Confirmed
2026-08-30: eight sessions across three projects had each hand-rolled a regex to read a skill's
description length, all of them with the same single-line-parse bug that a real parser does not
have.

Propose the absorption as a diff. Do not apply it silently — where the code lands is an authoring
decision, and `skill-authoring` owns that.

**`derivable` asks the same question of the skill instead of the transcripts.** `absorb` needs a
transcript store and only sees what an agent already re-wrote by hand; `derivable` reads the
`SKILL.md` itself, so it works on a corpus nobody has run and catches a skill before anyone pays for
it. Each fenced command line lands in one of three buckets:

- **delegated** — it calls a `scripts/*.py`, its own or a sibling skill's. The shape being aimed at,
  and it stays delegated however many placeholders it carries.
- **derivable** — a placeholder, a pipeline, a chain, an HTTP call, a SQL query, a JSON traversal:
  something the agent assembles from context on every run, and not a script call.
- **fixed** — a literal with no variable parts. Cheap, and not a finding.

**Read the samples, not the count.** Legitimate residue exists and the report prints it alongside
everything else: an external CLI's own documented one-liner, a one-off emergency procedure, the
consuming repo's own gate command a portable script must not hard-code. What is not residue is a
composed pipeline, a query, a parse, or a multi-step sequence — see `skill-authoring`'s "Anything
the skill can derive deterministically goes in a script" for the authoring rule this measures.

**A single run cannot show drift, which is the question this exists for.** Save a baseline while a
corpus is in good shape and compare after a run of edits; a rise in a skill's derivable count is the
finding, and a fall is reported rather than celebrated (a skill can shed command lines by being
cut).

```shell
python3 <this skill>/scripts/fitness.py derivable --save-baseline <path>.json
python3 <this skill>/scripts/fitness.py derivable --compare <path>.json
```

[PITFALL: every early run of this measure was dominated by its own false positives, and reading the
residue line by line is what found them — a layout diagram in an untagged fence read as seven
commands, a wrapped invocation read as three, a skill abbreviating its own script path
(`python3 <path> list`) read as 48 derivable lines out of 49 when 46 of them are calls into that
script. Each is pinned by a test in `tests/unit/test_derivable.py`. If you extend the classifier,
extend those first: an audit whose output is mostly noise is one that gets switched off after its
first run.]

## Scoring a skill's quality

The script deliberately does not score writing quality: that is judgement, and a heuristic
pretending to be a rubric score is worse than no score. Read the skill and score it yourself on the
published rubric, which is what the 47,150-skill corpus was measured with, so the number is
comparable:

| dimension        | 0–3, what earns the points                         |
| ---------------- | -------------------------------------------------- |
| **Completeness** | are the required components present and sufficient |
| **Clarity**      | readability and organisation                       |
| **Specificity**  | actionable instructions rather than vague guidance |
| **Examples**     | are there examples, and are they good              |

Ecosystem mean is **6.2/12**; the top quartile begins at **9**. Report the four sub-scores, not just
the total, because the remedy differs per dimension.

Two further published findings worth applying when the score is low:

- **Comprehensive skills measure worse than no skill** (−2.9pp), while detailed and compact ones
  score +18.8 and +17.1pp. A skill whose description is over the 1024-character specification cap is
  usually over-scoped rather than over-described — **trimming the description deletes trigger
  vocabulary, which is backwards.** Consider a split, and run `overlap` on the proposed pieces first
  to check they will not shadow each other.
- **Two to three skills applied to one task beat four or more** (+18.6pp against +5.9pp). That is
  measured per task rather than per machine, so it is an argument for sharp boundaries, not for
  deleting skills.

## What this cannot see

Say so rather than reporting a smaller number as if it were the whole one.

- **`usage`, `listings actually sent`, and the invocation half of `budget` are Claude Code
  specific.** They read `~/.claude/projects/*.jsonl` and `~/.claude.json`. On another harness each
  says **unavailable** and drops its columns rather than printing zeros. That distinction is load-
  bearing and was not free: measured 2026-08-31 under a fake `HOME`, the report rendered thirteen
  skills as never invoked and forecast which of them would lose a description, on no data at all —
  in a tool whose own rule is that a zero is not a verdict. If you port this, keep the flag.
- **What survives anywhere**: `inventory`, the listing arithmetic, `overlap`, and the rubric. The
  budget still reports its total as a floor, because pricing the harness's own entries needs a
  listing it sent.
- **The harness's own skills are not on disk** and are not in `inventory`. `budget` prices them by
  subtracting the installed set from a real listing, so that number is only as fresh as the last
  session recorded; on a machine with no listings recorded, the total is a floor and says so.
- **A trigger probe contaminates its own corpus.** Any synthetic skill created to test triggering
  appears in later `usage` runs; exclude it with `--exclude <name>`.
- **`derivable` only reads fenced blocks.** A skill that describes a command in a sentence — "query
  the API for the run's conclusion and read `status`" — asks for exactly the same re-derivation and
  is invisible to it. So a zero is not a certificate; it means nothing is fenced. The fenced form is
  the common one and the one that grows, which is why the measure is worth having anyway.

## Trigger cases, when the static pass is not enough

`overlap` says which pairs are suspicious; only a live run says which one actually wins. That run is
`scripts/trigger.py`, and it is the only thing here that costs tokens.

```shell
python3 <this skill>/scripts/trigger.py run <cases>.json --dry-run   # count the runs, spend nothing
python3 <this skill>/scripts/trigger.py run <cases>.json --runs 3
```

Cases are JSON, in the skill's own `evals/`, with `expect` naming the skill that should fire and
`null` for should-not-trigger. Write them **for a flagged pair**, not a fixed number per skill — the
pair is the unit of the failure. Each run is killed the moment a skill is named, so a case never
proceeds into the skill's work; a case for a skill whose commands enumerate private directories
cannot print them.

**Write the hard cases, or the suite proves nothing.** Measured 2026-08-31 on this repo: a first
suite of eight cases passed 24/24 at three runs each — and every prompt in it named something only
one skill claims (`tasks.py`, `inv`, "full-text search"). A suite like that cannot tell "these
skills do not contend" apart from "these cases were too easy". A second suite, phrased in the region
a broad skill's description actually claims, is what produced a finding.

**Expect the failure to be a miss, not a steal.** This is now the strongest pattern in the data, and
it should change what you go looking for.

| static prediction, tested live                          | cases | steals | what actually failed                                                                 |
| ------------------------------------------------------- | ----- | ------ | ------------------------------------------------------------------------------------ |
| a broad skill shadowing two narrow ones                 | 14    | **0**  | one miss: "our automation scripts have grown messy, where do I start"                |
| a new skill taking its two nearest neighbours' requests | 15    | **0**  | nothing                                                                              |
| the corpus's top-ranked pair, split on purpose          | 30    | **0**  | one miss: "this skill has grown to cover three different things, worth breaking up?" |

**Three predictions of contention, three refutations, 59 runs, not one steal** — while every real
failure was a request that fired nothing. A description built from the tool's vocabulary rather than
the request's does not lose to a competitor; it loses to silence. Both misses above are the same
shape: the skill claimed the situation in its own words ("over-scoped", "split"; `tasks.py`, `inv`)
and the person described it in theirs ("grown to cover three things", "breaking up"; "messy
automation scripts").

So write the should-trigger cases in a stranger's vocabulary, and read a passing suite as weak
evidence: it says these skills do not fight, which they mostly do not, and says nothing about the
requests none of them answer.

## Testing a proposed description before adopting it

This is the "measure" in draft → measure → decide, and it is what makes drafting a description
legitimate rather than the unmeasured authoring that scores below having no skill at all.

```shell
python3 <this skill>/scripts/trigger.py candidate <cases>.json \
  --skill <name> --description @<file> --runs 3
```

The proposal joins the listing under a temporary name alongside every real skill, so it is scored in
the same competition it will actually face. Adopt it only if it wins cases the incumbent lost
without losing cases the incumbent won.

**A candidate score is an estimate with error in both directions — never report it as what the
shipped skill will do.** A proposal is registered as a command file and a real skill is not, and the
difference shows up in the result. Measured twice on 2026-08-31 in the optimistic direction: a
request scoring 0/3 against the old wording and 1/3 as a candidate scored **3/3** once shipped; a
second one scoring 0/3 and 2/3 as a candidate shipped at **2/3**, exactly its candidate figure. This
file called that a **lower bound** until 2026-09-01, when `python-refactor-audit` refuted it on
identical cases: the whole suite went 12/12 as a candidate and **11/12** installed, and its flagship
case went **3/3 → 1/3** — a two-run drop, outside the variance band below. Listing truncation was
ruled out with `budget`. So: adopt a candidate that clearly improves even below a clean pass, and
settle it with a `run` against the installed set after the change lands.

**Three runs is the floor, and a 2/3 is a pass that is not a clean one.** Across these suites a case
that scored 3/3 twice has come back 2/3 with no relevant change in between, the third run firing
nothing. Read a single dropped run as variance rather than as a finding, and do not compare a 3/3
against a 2/3 as though the difference were signal.

**The candidate competes against its own installed twin**, and reading that as failure is the trap.
Both names satisfy the same case, so the run scores them together and reports the split separately.
Confirmed 2026-08-31: the first candidate run reported two cases failed because the _incumbent_ won
them, while the case the candidate was written to fix passed 3/3 — the proposal was working and the
scoreboard said otherwise. A candidate that never wins any fire is simply not more attractive than
the wording already in place, which is also a result.
