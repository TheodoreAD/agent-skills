---
status: landed
updated: 2026-09-02
---

# Derivable work belongs in a script, and skills should be audited for drift away from it

## Context

Requested by the user 2026-09-02, immediately after `session-harvest`'s mechanical half became
`harvest.py`:

> make sure we record the general principle that absolutely anything non-trivial a skill can derive
> deterministically should be in a python script, especially when dealing with command line
> interfaces, http rest apis, sql databases, and so on, you get the idea. having an llm re-derive
> complex commands or syntax every time is wasteful, risky, and has almost no benefit. we should be
> able to audit our skills for this to make sure that after a series of improvements the skill
> doesn't drift from this principle.

Two deliverables, and they have different homes: the **principle** (an authoring decision) and the
**audit** (a measurement over an installed set).

The evidence for the principle is already in this repo, three times over. `plan-docs` is 1025 lines
because `plans.py` carries its mechanics; `session-bash-audit` is 200 because `audit.py` does;
`session-harvest` was 967 lines of prose and every run re-derived the same dozen commands, measured
2026-09-02 at 24,429 Bash calls across 1,134 transcripts — 568 plans-store status/log calls, 498
`git log origin/<branch>..HEAD`, 164 hand-written Python heredocs over a transcript, no two alike.
Six of its corrections had been written as prose warnings and each recurred at least once anyway,
which is the argument in its sharpest form: **a rule telling an agent how to spell a command is a
rule that has to be followed correctly every single time, while a script is followed once.**

## Design

### 1. The principle goes in `skill-authoring`

[DECISION: `skill-authoring`, not `~/AGENTS.md` and not a new skill. It is an authoring decision —
"what goes in the body" is already one of that skill's sections, and this is the same question one
level up. `~/AGENTS.md`'s own admission test says a skill that owns the topic beats a new
always-loaded rule, and skill authoring happens in exactly one repo, so a machine-wide rule would be
loaded into every session in every repo to serve the few that write skills.]

The section states the principle, then the part that makes it usable — **what legitimately stays in
prose**, because a rule that reads as "no commands in a SKILL.md" would be wrong and would be
ignored on its first counter-example:

- a command with no variable parts that a reader runs once (`npx skills add <owner>/<repo>`);
- a single call to a script, which is delegation and is the shape being aimed for;
- a one-off emergency procedure nobody runs twice a year (a history purge);
- the command that names the repo's own tooling, which the script must not hard-code.

And what does not: anything assembled from context (flags derived per run), anything multi-step,
anything parsed afterwards, and every one of the categories the user named — a CLI's flag syntax, an
HTTP API's request shape, a SQL query, a JSON traversal.

### 2. The audit goes in `skill-fitness`, as `fitness.py derivable`

[DECISION: a sub-command of the existing analyzer, not a new skill and not a new script. The
description `skill-fitness` already ships says it covers "which repeated one-off scripts an agent
keeps writing should become code inside a skill", so this needs no description change — which
matters, because that skill's own first rule is never to reword a description without measuring it,
and a re-measure is a heavier cost than this addition is worth. It also already owns the _dynamic_
half of this exact question: `absorb` clusters recurring `python3 -c` payloads out of the transcript
store. `derivable` is the static half, and it needs no transcripts at all.]

A third skill covering "when should a skill have a script" would contend for requests with both
`skill-authoring` and `skill-fitness`, which this repo's `AGENTS.md` names as the failure mode to
design against.

**What it measures.** Per skill: the command lines in fenced blocks, split into

- **delegated** — the line invokes a `scripts/*.py` (its own or a sibling skill's). The good shape.
- **derivable** — the line carries a placeholder (`<session-id>`, `$PLANS_HOME`, `{name}`) or a
  composition (a pipe, a chain, a redirect) and is _not_ a script call. The agent assembles this
  from context on every run.
- **fixed** — a literal with no variable parts. Cheap, and not a finding.

Each derivable line is tagged with what kind of derivation it is — `pipeline`, `chain`, `http`,
`sql`, `json`, `flags` — so the report says what a skill is asking an agent to compose rather than
only how much.

**Drift is the point, so the number has to be comparable across runs.** Same mechanism as
`audit.py`: `--save-baseline` writes the per-skill counts, `--compare` prints the delta and fails
the expectation when a skill's derivable count has gone _up_. That is the "after a series of
improvements the skill doesn't drift" check, and without a stored baseline there is nothing to drift
against.

### 3. Prototype measurements, 2026-09-02

Run over this repo's 14 skills while designing the analyzer, and it changed the design twice:

| skill                | command lines | with placeholders | not delegated |
| -------------------- | ------------: | ----------------: | ------------: |
| `plan-docs`          |            49 |                48 |             3 |
| `research-library`   |            13 |                 9 |             7 |
| `session-harvest`    |             9 |                 7 |             3 |
| `skill-authoring`    |             7 |                 7 |             7 |
| `skill-fitness`      |             5 |                 5 |             1 |
| `session-bash-audit` |             7 |                 2 |             0 |
| the other 8          |             6 |                 0 |             0 |

[PITFALL: **the first two versions of the residue column were mostly false positives, and reading
the samples is what found it.** `research-library`'s seven were a directory-layout diagram in an
untagged fence — not commands at all. `skill-authoring`'s seven were `npx skills add <owner>/<repo>`
(an external CLI's own documented one-liner, whose placeholders are the reader's identity) and calls
to _another_ skill's script, which is delegation. `session-harvest`'s three were backslash
continuation lines of one `audit.py` invocation, counted separately. So the analyzer joins
continuations, requires a line to look like a command rather than a path, and treats any
`scripts/*.py` call as delegation whichever skill owns it. An audit whose residue is mostly noise is
one that gets switched off after its first run.]

The honest reading after those fixes: this repo is largely already compliant, and the value of the
audit is forward-looking. That is worth saying in the report rather than hiding — a green audit on
the corpus that motivated it is the expected outcome, not a sign the check is broken.

## Files touched

- `skills/skill-authoring/SKILL.md` — the principle, with the stays-in-prose test.
- `skills/skill-fitness/scripts/fitness.py` — `derivable` sub-command, in `report`, `--json`,
  baseline/compare.
- `skills/skill-fitness/SKILL.md` — how to read it, and what it cannot see.
- `tests/unit/test_derivable.py` — the classifier, one test per false positive above.
- `AGENTS.md` — one line under "Authoring a skill", where this repo's own admission criteria live.

## Verification

- The suite, including the new classifier tests.
- `fitness.py derivable` run over this repo's own skills, with the residue read line by line rather
  than counted — the check that the categories are real.

## What landed, 2026-09-02

Both halves, in the two homes the design argued for, plus one finding the audit made on its first
honest run.

- **`skill-authoring`** gains "Anything the skill can derive deterministically goes in a script, not
  in prose": the principle, why prose loses (it must be followed correctly every run and fails
  silently and plausibly when it is not), the four kinds of residue that legitimately stay, and the
  `session-harvest` measurement as the worked case.
- **`fitness.py derivable`** classifies every fenced command line in a corpus as delegated /
  derivable / fixed, tags the derivations (`placeholder`, `pipeline`, `chain`, `redirect`, `http`,
  `sql`, `json`, `flags`), and diffs against `--save-baseline` output. A baseline for this repo is
  committed at `skills/skill-fitness/references/baselines/derivable-2026-09-02.json`.
- **`tests/unit/test_derivable.py`**, 14 tests: one per false positive the early runs produced, plus
  `test_this_repos_own_corpus_stays_within_its_baseline`, which fails the gate when a skill's
  derivable count rises. That is what makes the drift check a gate rather than a report nobody runs.
- **`AGENTS.md`** carries the one-line rule with the pointer to both.

**The corpus as measured, after the false positives were fixed:** 14 skills, 105 fenced command
lines, 93 delegated, 7 derivable, 5 fixed. The seven: three `npx skills add <owner>/<repo>` lines in
`skill-authoring` (an external CLI's documented one-liner), three one-off git-surgery commands in
`plan-docs`' history-purge procedure, and one in `research-library`.

[DEFERRED: **that last one is a real finding and is not fixed here** — it is
`plans/2026-09-02-research-library-entry-add-is-hand-composed.md`. `research-library` tells the
reader to compose `git clone --depth 1 <url> "$RESEARCH_HOME/repos/<host>--<owner>--<repo>"` and
then write a `SOURCE.md` by hand — an entry name derived from a URL by a naming rule the skill
spends a paragraph explaining, which is the exact shape this principle says should be code. It
already has `scripts/package_health.py`, so the directory exists. Filed as its own plan rather than
bundled here: this plan is the principle and its audit, and fixing one skill under it is separate
work that the audit will now keep asking for.]

[DECISION: `skill-fitness`'s description is deliberately unchanged. It already claims "which
repeated one-off scripts an agent keeps writing should become code inside a skill", which covers
this mode, and that skill's own first rule is never to reword a description without measuring the
new wording against the installed set. A re-measure costs a trigger run and buys nothing here.]
