---
name: skill-fitness
description: >-
  Use when asking whether installed skills are actually working — why a skill never fires or fires
  on the wrong requests, which two skills compete for the same request, what the skill listing is
  costing in context and which skill loses its description first, which skills have never been
  invoked at all, or which repeated one-off scripts an agent keeps writing should become code
  inside a skill. Also for scoring a skill against the published quality rubric before shipping it,
  and for deciding whether an over-scoped skill should be split. Measures an installed set from
  frontmatter and from the session transcript store; it does not teach how to write or deploy a
  skill.
metadata:
  family: meta
---

# Skill fitness

Measures whether a set of skills works, so the fix is chosen from numbers rather than from a hunch.
Authoring guidance is `skill-authoring`'s job and this skill does not repeat it; Bash-usage auditing
is `session-bash-audit`'s.

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

Read-only, stdlib, deterministic, no tokens. Sub-commands when you want one section: `inventory`,
`budget`, `overlap`, `usage`, `absorb`. Every one takes `--json`.

| the question                                    | the command |
| ----------------------------------------------- | ----------- |
| what is installed, and from where               | `inventory` |
| what is the listing costing, and who is at risk | `budget`    |
| which skills compete for the same request       | `overlap`   |
| what actually gets invoked                      | `usage`     |
| what one-liners should be skill code            | `absorb`    |
| everything, in reading order                    | `report`    |

By default it reads `~/.agents/skills`, `~/.claude/skills`, and `./skills` when run from a skills
repo. `--root <dir>` (repeatable) replaces that set — use it to score a corpus you do not have
installed.

## Reading the output

**`budget` is ordered by who loses their description first, and that order is the finding.** Claude
Code loads a listing of every skill's name and description, budgeted at about 1% of the context
window and **shared with the harness's own bundled skills**. When it overflows, descriptions are
dropped starting with the least-invoked skill. That is self-reinforcing: no invocations, so the
description goes, so the skill cannot be matched, so it stays at zero. A skill at the top of that
table with a large `listing_chars` is the one to act on.

**`usage` counts two mechanisms and neither alone is the rate.** `auto` is the model choosing the
skill through the `Skill` tool. `explicit` is a person typing `/name`, which often injects the body
directly and produces no tool call at all. Measured 2026-08-30: one skill showed 11 auto against 84
explicit, another 69 against 12 — opposite stories, and either column read alone gives the wrong
one. A skill with high `explicit` and near-zero `auto` has a description problem; the person keeps
having to ask for it by name.

**`overlap` ranks, it never gates.** Similarity between prose descriptions is low in absolute terms,
so any fixed cutoff either never fires or fires on everything — an AI-security scanner in this space
uses Jaccard > 0.7, which on real descriptions is close to never, and this script's own first draft
used an absolute 0.5 and flagged nothing. Shadowing is therefore judged against the corpus's own
distribution and the numbers are always printed, because the judgement is the reader's.

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
Confirmed 2026-08-30: eight sessions across three projects had each hand-rolled a regex to read a
skill's description length, all of them with the same single-line-parse bug that a real parser does
not have.

Propose the absorption as a diff. Do not apply it silently — where the code lands is an authoring
decision, and `skill-authoring` owns that.

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

- **`usage` and the invocation half of `budget` are Claude Code specific.** They read
  `~/.claude/projects/*.jsonl`. On another harness those sections are unavailable, not zero.
- **Bundled skills are not on disk** and are not in `inventory`, yet they consume the same listing
  budget. The listing total is therefore a floor. `/doctor` estimates the real figure and names the
  biggest contributors; `/context`'s Skills row reports the size after the budget is applied.
- **A trigger probe contaminates its own corpus.** Any synthetic skill created to test triggering
  appears in later `usage` runs; exclude it with `--exclude <name>`.

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

**Expect the failure to be a miss, not a steal.** The static pass predicted that a broad skill was
shadowing two narrow ones. It was not: across both suites the narrow skills won every case they
should have, including the ones written to be ambiguous. The one real failure was a request phrased
the way a person phrases it — "our automation scripts have grown messy, where do I start" — for
which **nothing fired at all**. A description built from the tool's vocabulary rather than the
request's does not lose to a competitor; it loses to silence, and only a should-trigger case in
plain language finds it.

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

**The candidate competes against its own installed twin**, and reading that as failure is the trap.
Both names satisfy the same case, so the run scores them together and reports the split separately.
Confirmed 2026-08-31: the first candidate run reported two cases failed because the _incumbent_ won
them, while the case the candidate was written to fix passed 3/3 — the proposal was working and the
scoreboard said otherwise. A candidate that never wins any fire is simply not more attractive than
the wording already in place, which is also a result.
