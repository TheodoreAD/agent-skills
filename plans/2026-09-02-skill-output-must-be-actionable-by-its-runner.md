---
status: idea
updated: 2026-09-02
---

# A skill's output must be actionable by whoever ran it

## Context

Stated by the user 2026-09-02, on being shown a portability audit of this corpus: _"I don't want the
skills to force users into looking at reports of stuff they can't fix, or plans they can't work on
because it's not their repos."_

The corpus is installed by strangers through `skills add`. A stranger runs the same commands the
author does, against a machine where most of what those commands find belongs to somebody else — so
a report that is useful here is a tax there, paid on every run, and the thing it trains is not
reading the output.

**This is one principle with three faces, and two of them are already written down without ever
having been generalised:**

- `~/AGENTS.md` bans writing into another repo outright and routes the work to a filed plan instead
  — the same asymmetry, one level up, solved by moving the finding rather than by printing it.
- `2026-09-02-status-drift-invisible-at-repo-scope.md` (landed today) is the same bug inside
  `plan-docs`: the session that could _see_ a drifted status was in a repo that could not fix it,
  and the session that could fix it was never shown it. The fix was to compute the finding where it
  can be acted on.
- The third face is the one with no rule yet: a **published** skill reporting on things the reader
  cannot author. Nothing in `skill-authoring` says an audit has to ask who can act before it prints.

## Evidence

**`skill-fitness` is the concentration of the problem, and `portability` is the sharpest instance.**
Measured 2026-09-02, `fitness.py portability` with no `--root` — the default, and what a stranger
would type:

- It reads `~/.agents/skills`, the install hub. Every skill there is a **deployed copy**, and this
  corpus's own `skill-authoring` rule says editing a deployed copy is drift that reaches nothing.
- The run produced **34 findings across 14 skills, of which a reader who installed them can act on
  zero.** Their only routes are forking the source repo or filing an issue against it, and the
  report names neither.

**Half of `fitness.py` has the same shape.** Sorting its sections by who the remedy belongs to:

| section       | remedy belongs to                                          | fine for a stranger? |
| ------------- | ---------------------------------------------------------- | -------------------- |
| `inventory`   | the installer (a stale copy is theirs to refresh)          | yes                  |
| `budget`      | the installer (uninstall, or accept the cost)              | yes                  |
| `usage`       | the installer (what to keep)                               | yes                  |
| `overlap`     | the author ("redraw the boundary, not the prose")          | **no**               |
| `absorb`      | the author (where the code lands is an authoring decision) | **no**               |
| `derivable`   | the author (fix the skill)                                 | **no**               |
| `portability` | the author                                                 | **no**               |
| rubric score  | the author                                                 | **no**               |

`report` runs all of them, so the default entry point hands a stranger four sections of work they
cannot do — and does it under a heading that reads as a defect list.

**There is no provenance on disk to lean on.** A `--global` install leaves no `skills-lock.json`
anywhere (checked 2026-09-02: none under `~`, `~/.agents` or `~/.claude`), so nothing records who
authored an installed skill. The discriminator has to be structural instead, and there is a good one
already in the data: `Skill.scope` is the root a skill was loaded from, and the install hub is
categorically different from a skills **repo checkout**. The rule needs no lock file and no network.

[PITFALL: **the author's own machine cannot show this bug**, which is why it survived being written
today. Here the hub and the source repo hold the same fourteen names, so every finding in the hub is
also a finding in a checkout the author can edit, and the report looks correct. It is only wrong on
a machine where the two differ — that is, every machine but this one. Any check for this class has
to be reasoned about, or run under a fake `HOME`, rather than read off a normal run.]

**Reproduced as a reader, under a fake `HOME`** (2026-09-02), which is the only way to see it from
here at all:

- A reader who installed **two** of the fourteen skills gets **four findings in `session-harvest`**,
  a file they must not edit, with neither of their real routes named.
- In the same run `plan-docs` fell from 1 bare to **0** — not because anything changed in it, but
  because `repo-tasks` left the derived author vocabulary when the skill that links it was not
  installed. **The verdict on a skill therefore depends on what else the reader happens to have.**
  That is tolerable in an author's audit of a whole corpus and indefensible in a reader-facing
  report, and it is a second, independent argument that this measure is not one.

**What is already safe, checked rather than assumed.** On an empty machine `audit.py` prints "no
Bash calls found" and `fitness.py` prints "no skills found" — neither invents a zero. And the plans
half of the user's sentence does not reproduce: a first-time reader running `plans.py list` in a
fresh repo gets `(no open plans)`, and `absorb` returns `needs-decision` asking them to choose their
own routing. `plan-docs` shows a reader nothing but their own files, at every scope.

**The skills that already get it right, and why.** `plan-docs` routes rather than prints — `absorb`
shows only plans filed **for the repo the session is in**, "waiting on this repo" is the actionable
half of a dependency edge, and `new --for <repo>` is the mechanism for a finding whose home is
elsewhere. `session-harvest`, `session-bash-audit` and `research-library` report exclusively on the
runner's own machine, repos and transcripts. None of that was derived from a stated rule; it came
out right because each was written for the person running it.

## Open questions

[NEEDS CLARIFICATION: **what an author-side section should do when the corpus holds nothing
authorable** — print one line and stop, or print the findings behind an explicit
`--include-installed`. One line is the honest default; a flag keeps the information reachable for
the case that actually matters, which is a reader who _has_ forked. Leaning: default to the
authorable roots, and when there are none, say so in a sentence that names the two real routes (fork
it, or open an issue upstream) rather than printing a table.]

[NEEDS CLARIFICATION: **whether "authorable" is a property of the root or of the skill.** Root is
cheap and needs nothing: an explicit `--root`, or a `./skills` directory in a git repo, is
authorable; `~/.agents/skills` and `~/.claude/skills` are not. Per-skill would be sharper — a reader
who forked and installed from their own fork is editing the right thing when they edit the hub copy
— but nothing on disk says whose fork it came from, so it cannot be decided without asking.

Checked before assuming: the `skills` CLI is **not** in `$RESEARCH_HOME/repos` (only
`anthropics/skills` is, which is a different project), so "does a `--global` install record its
source anywhere the CLI could be asked" is unanswered rather than answered no. The absence of a lock
file under `~`, `~/.agents` and `~/.claude` is the observation; the CLI's own intent is not. Cloning
it into the library is the next concrete step for this question.]

[NEEDS CLARIFICATION: **whether this belongs in `skill-authoring` as a rule, in `skill-fitness` as a
behaviour, or both.** Both, probably, and they are different statements: `skill-fitness` has to
change what it prints, while `skill-authoring` has to make the next skill ask the question. The risk
of writing it only as a rule is that it is exactly the kind of rule an author satisfies on their own
machine without noticing, per the PITFALL above.]

[DECISION: **the corpus ships three kinds of reader-facing artefact about the author's own work, and
one of them spends the reader's money.** Audited 2026-09-02 against a real install
(`~/.agents/skills`), so this is what a reader actually receives, not what the repo intends to send:

- **Two baselines**, both measured on this machine and both offered as a `--compare` target.
  `skill-fitness/references/baselines/derivable-2026-09-02.json` names this corpus's fourteen skills
  and their counts — compared against a reader's own set it reports `new` for everything they have
  and `no_longer_present` for everything of ours they do not, which is noise dressed as drift.
  `session-bash-audit/references/baselines/2026-08-24-auto-mode.json` holds this author's own
  per-model Bash rates under a named `~/AGENTS.md` revision.
- **Eleven eval suites** under `skill-fitness/evals/` and `research-library/evals/`, each written
  for a contention between two skills of _this_ corpus and each expecting our skill names to win.
  This is the expensive one: `trigger.py` is the only thing in `skill-fitness` that costs tokens,
  and a reader who runs a shipped suite pays real money to measure whether our pair contends inside
  their installed set.

The line worth drawing is not "ship no measurements". A published finding is evidence and travels
fine — SkillsBench's numbers are quoted throughout and lose nothing by being someone else's. What
does not travel is a **machine-specific measurement offered as the reader's own comparison target**:
a baseline to diff against, a suite to run. Evidence is read; a baseline is executed.]

[NEEDS CLARIFICATION: **whether a shipped baseline should be renamed, relocated, or refused.** Three
shapes, unresolved: name it for whose machine it came from and leave `--compare` as is; move
baselines and evals out of the skill and into the repo (they are the author's test data, not part of
the installed artefact — but `evals/` is one of the three directories a skill is allowed to have,
added deliberately on 2026-08-31); or have `--compare` and `trigger.py run` refuse a baseline or
suite whose corpus does not match the one in front of them, and say why.]

[DEFERRED: **the "editing this skill" footer** carried by five skills tells the reader to edit the
source in the author's repo and push. That is the same principle in miniature — an instruction to do
work in a repo the reader does not own — and it was already on the fix list as a dead pointer. It
now has a better reason, but the wording is downstream of the questions above, so it waits.]

## Recommended direction

Not yet — the questions above are the work. What is settled enough to write down:

**The rule, in the form it would take in `skill-authoring`:** before a skill prints a finding, ask
who can act on it. If the answer is somebody other than the person who ran the command — another
repo's session, the skill's author, a machine the runner does not own — the skill routes the finding
to where it can be acted on, or it does not print it by default. A report of things the reader
cannot change is not information; it is a cost they pay per run, and it teaches them to stop
reading.

**And the sequencing:** nothing in the corpus gets reworded for portability until this is settled,
because the fix for a finding depends on which side of the line it falls. The portability audit
itself is committed and unpushed at `fd51e53`, carrying the flaw it describes.
