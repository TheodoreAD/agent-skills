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

[NEEDS CLARIFICATION: **whether "authorable" is still a question at all under the opt-in decision.**
It was the whole question while the plan was "scope the section to roots the reader can edit". With
author-side sections named explicitly instead, a reader who runs `portability` has asked for it, and
`--root` already lets them aim it. The residual case is narrow: whether an explicit run that finds
_only_ hub copies should still say so before printing. Cheap either way, and it no longer blocks
anything.

If it is answered, the cheap answer is by **root**: an explicit `--root`, or a `./skills` directory
in a git repo, is authorable; `~/.agents/skills` and `~/.claude/skills` are not. Per-skill would be
sharper — a reader who forked and installed from their own fork is editing the right thing when they
edit the hub copy — but nothing on disk says whose fork it came from, so it cannot be decided
without asking.

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

- **Two baselines, and they are not the same case** — corrected 2026-09-02 after checking what
  actually cites them, rather than reasoning from the fact that they ship.
  `skill-fitness/references/baselines/derivable-2026-09-02.json` is **never offered to a reader**:
  `skill-fitness`'s body shows `--save-baseline <path>` / `--compare <path>` with generic paths and
  names no shipped file. Its only consumer is this repo's own
  `test_derivable.py::test_this_repos_own_corpus_stays_within_its_baseline`. So it is a **test
  fixture that happens to live inside a published directory** — dead weight in a reader's install,
  not a trap laid for them. `session-bash-audit/references/baselines/2026-08-24-auto-mode.json` is
  the opposite: cited by path in its own skill twice, and there the skill **already gets it right**
  — "the measured numbers and baselines shipped here are one author's machine under one set of rules
  — treat them as a reference point to compare against, not as your own baseline; save your own on
  the first run." That sentence is the working precedent for this whole question.

  [PITFALL: **the caveat does not travel to the point of use, and the corpus already demonstrates
  it.** `session-harvest` cites that same directory —
  `audit.py --session … --compare ~/.agents/skills/session-bash-audit/references/baselines/<baseline>.json`
  — and repeats none of the caveat. `<baseline>` is a placeholder, and the only file in that
  directory is the author's, so a reader following the instruction literally compares their session
  against this machine's rates under this machine's rules. One skill declaring an assumption does
  not protect a reader who arrives through a different skill, which is the standing argument in this
  repo for putting a check in code rather than in prose.]
- **Eleven eval suites** under `skill-fitness/evals/` and `research-library/evals/`, each written
  for a contention between two skills of _this_ corpus and each expecting our skill names to win.
  This is the expensive one: `trigger.py` is the only thing in `skill-fitness` that costs tokens,
  and a reader who runs a shipped suite pays real money to measure whether our pair contends inside
  their installed set.

The line worth drawing is not "ship no measurements". A published finding is evidence and travels
fine — SkillsBench's numbers are quoted throughout and lose nothing by being someone else's. What
does not travel is a **machine-specific measurement offered as the reader's own comparison target**:
a baseline to diff against, a suite to run. Evidence is read; a baseline is executed.]

[DECISION: **author-side sections become an explicit opt-in.** Chosen by the user 2026-09-02 from
three shapes. `report` runs only the installer-side sections — `inventory`, `budget`, `usage` — and
`portability`, `derivable`, `overlap` and `absorb` have to be named on the command line. A reader
never meets an author-side section by accident, and the split is a property of the **command**
rather than of whichever corpus happens to be in front of it, so it holds on machines the author
cannot test. Rejected: scoping to authorable roots with a one-line skip, which leaves the section in
`report`'s path and makes behaviour depend on cwd; and printing two sections split by who acts,
which keeps a count of somebody else's defects in front of the reader on every run.]

[NEEDS CLARIFICATION: **whether a shipped baseline or suite should be renamed, relocated, or
refused.** The user asked for the implications rather than choosing them; they are worked through in
"What the shipped-data options actually cost" below. In short: the opt-in decision above already
removes most of the _baseline_ exposure and none of the _eval_ exposure, and options 1 and 3 turn
out to be complements rather than alternatives.]

## What the shipped-data options actually cost

**The opt-in decision moves this question before it is answered.** `derivable --compare` is
author-side, so under the decision above a reader cannot reach it without naming it — and the
derivable baseline was never cited to a reader anyway. What the decision does **not** cover is
`trigger.py`: it is a separate script with its own entry point, not a `fitness.py` section, so no
choice about `report`'s sections touches it. The eval suites are therefore the live half of this
question and the baselines are mostly the settled half.

**1. Leave in place, name whose they are.** Cost is one sentence per artefact, and the precedent is
already in the corpus and already works — `session-bash-audit` says its shipped numbers are one
author's machine under one set of rules and tells the reader to save their own on the first run. It
fixes misuse-by-default and costs no coupling: `test_derivable.py`'s path stays valid, the `evals/`
convention stays intact. What it does not do is stop the token spend — a caveat warns, it does not
prevent `trigger.py run <our suite>` from costing money. And its failure mode is already
demonstrated above: `session-harvest` cites the baselines directory without repeating the caveat, so
a reader arriving through a different skill never sees it. That is precisely the argument this repo
uses for putting a check in code instead of prose.

**2. Move them out of the installed artefact.** The most expensive, and it is a convention change
rather than a file move: `evals/` was deliberately admitted as one of the three directories a skill
may hold on 2026-08-31, and that is encoded in `CLAUDE.md` and enforced by
`tests/unit/test_skill_layout.py`. It fixes the problem completely for the reader — nothing to
misuse, no tokens to spend, a smaller install — at the cost of the reason the evals were put inside
a skill in the first place: they are worked examples of how to write trigger cases, and a fork loses
the suites that prove its descriptions work. **The two artefacts are not alike here**, and treating
them alike is the flaw in this option: a baseline is machine-specific data with no teaching value,
while an eval suite is data _and_ an example. Moving only the baselines is the coherent version, and
it costs almost nothing — one path in `test_derivable.py`.

**3. Refuse a foreign baseline or suite.** The only option that stops the token spend, and it works
whether or not the reader read a caveat or arrived through a skill that repeats one. It is also code
rather than prose, which is this repo's stated preference for exactly this kind of check, and the
data to do it already exists: the derivable baseline carries a skill-name map, the bash baseline
carries `saved`/`days`/`note`, and every eval case carries an `expect` naming a skill, so "is the
corpus in front of me the one this file was measured on" is computable without a fingerprint being
invented. Two costs. It is a **gate**, and this repo's standing position is that these measures rank
and never gate — so it needs an override flag, and a refusal that fires wrongly is worse than a
caveat that goes unread. And it is the only option here that cannot be done by editing markdown.

**Where that leaves it.** 1 and 3 are complements, not alternatives — a refusal that states its
reason _is_ the caveat, delivered at the moment it matters instead of three hundred lines away. 2 is
a separate decision that is cheap and clearly right for the baselines and expensive and arguable for
the evals.

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
