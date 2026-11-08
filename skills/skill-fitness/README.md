# skill-fitness

Numbers on whether your agent's skills actually fire, instead of a hunch.

You install a skill and assume your agent uses it. Often it doesn't, and nothing tells you. A skill
is only ever picked from a listing of names and one-line descriptions, and that listing fails
quietly in a few ways:

- It has a size budget. When the listing overflows, skills are shown by bare name with no
  description, so the agent has nothing to match a request against. A skill that is never matched
  never builds the usage that would keep its description next time.
- A request phrased in your words rather than the description's words fires nothing at all.
- A description written by a model and never tested is, on average, worse than no skill. SkillsBench
  measured model-authored skills at 1.3 points **below** having no skill, and human-curated ones at
  16.2 points above.

skill-fitness measures all of this, so that changing a skill is a decision made from numbers.

It works with any agent that reads [Agent Skills](https://agentskills.io). The parts that read what
actually happened in past sessions are specific to Claude Code; the rest works anywhere.

## What you get

- One read-only report, no tokens spent: what is installed and from where, what the listing costs
  and which skills lose their description first, and what has actually been invoked, split into the
  agent choosing a skill and a person typing `/name`.
- The listings your harness really sent, read back from its session records. A skill shown as a bare
  name is visible there, so truncation is observed rather than modelled.
- A ranking of which pairs of skills look likely to compete, used to pick which pair to test for
  real.
- A live trigger test. You write requests as JSON with the skill each should select, including some
  that should select nothing, and it runs your agent and records what fired. A candidate mode scores
  a reworded description against your real installed set before you adopt it.
- Where a skill should hold code instead of prose: one-off scripts agents keep rewriting across
  sessions, and command lines a skill makes the agent assemble by hand every time.
- A published four-part quality rubric to score a skill against, with the ecosystem average for
  comparison.

## What it looks like

Part of the report, run on the machine this repo is developed on:

```
## listing budget — 11954 chars for these skills
  plus 16740 chars the harness lists and this tool cannot see, charged first
  from a listing it really sent: 28737 chars over 44 entries, sent 2026-09-29
  budget at a 200000-token window: 8000 chars — priority
  demoted to name-only: db-defaults-taudelta, invoke-task-conventions-taudelta, …
```

The budget is a share of the model's context window. On a model with a 200,000-token window it is
8,000 characters, and the harness's own entries are charged first: 16,740 characters here, more than
the whole budget. So all fifteen skills in this repo would reach that model as bare names. A bigger
window gives a bigger budget, which is why the report takes the window size as an option.

## What the measurements turned up

The expected failure is two skills fighting over one request. Three times the static analysis
predicted exactly that, and three live tests refuted it: 59 runs and not one request taken by the
wrong skill. Every real failure was a request that fired nothing, because a person described the
situation in their own words ("this skill has grown to cover three different things") while the
description used the tool's ("over-scoped", "split").

A skill that is never invoked looks broken, and usually isn't. Two such skills here looked like the
worst in the set. A live test scored them 7 out of 7 with their descriptions unchanged. Nobody had
asked for them yet, and rewriting them would have damaged two descriptions that worked.

## Why not just reword the description

Rewording on a hunch is the unmeasured authoring the SkillsBench numbers warn about, and it can't
tell a skill nobody needed from one that lost. Similarity scores between descriptions don't settle
it either: on real descriptions a fixed threshold either never fires or fires on everything, and a
symmetric score can't express one skill quietly covering another. So the static tools here rank
candidates, and a live test decides.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill skill-fitness
```

Then ask: "is the skill listing getting truncated?", "which of my skills never fire?", "test this
new description before I ship it".

Needs Python 3.11 or newer. The live trigger test needs the `claude` CLI and spends tokens; nothing
else does.

## What it touches

The report reads skill directories, Claude Code's session records and its `~/.claude.json`, uses no
network, and writes nothing except a baseline file when you name one. The trigger test runs your
agent in a temporary directory and deletes it afterwards. It refuses a test suite that expects a
skill you don't have installed, rather than paying to measure a contest that can't happen on your
machine. The complete list is in [`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/measurements.md`](references/measurements.md): the trigger ledger, the listing budget
  as read from the harness itself, and five heuristics that failed.
- [`references/research.md`](references/research.md): SkillsBench, the rubric, and what other tools
  in this space do and don't detect.
