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
— but nothing on disk says whose fork it came from, so it cannot be decided without asking.]

[NEEDS CLARIFICATION: **whether this belongs in `skill-authoring` as a rule, in `skill-fitness` as a
behaviour, or both.** Both, probably, and they are different statements: `skill-fitness` has to
change what it prints, while `skill-authoring` has to make the next skill ask the question. The risk
of writing it only as a rule is that it is exactly the kind of rule an author satisfies on their own
machine without noticing, per the PITFALL above.]

[NEEDS CLARIFICATION: **whether the corpus ships any other reader-facing report about the author's
own work.** One known instance: `skill-fitness/references/baselines/derivable-*.json` is this
corpus's own counts, shipped into every install. Harmless in size, but it is literally a report
about somebody else's skills sitting inside the reader's copy, and a `--compare` run against it
would measure their corpus against ours. Not audited beyond this one file.]

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
