# session-harvest

End-of-session review that files what matters and finds what was left running.

A long session with a coding agent ends with its work in three states. Some of it is written down:
committed code, a plan, a doc. Some of it exists only in the conversation: a decision you made
together, a caveat the agent mentioned once, the thing you said you'd do next. And some of it is
still running, with nobody watching it. Compacting the context or closing the window loses the
second group without a sound, and nothing ever reports the third.

The usual reflex is to tell the agent "remember this". That puts the note in a memory store only one
tool can read, where no reviewer sees it and nothing ever cleans it up.

session-harvest is the review you run instead, before you compact or stop. Say "harvest this
session", "anything dangling before I stop?", or type `/session-harvest`.

It works with any agent that reads [Agent Skills](https://agentskills.io). The part that reads the
conversation history is specific to Claude Code; the rest works anywhere.

## What it does

- Rereads the actual conversation, not the agent's own summary of it. That includes your answers to
  the agent's questions and messages you sent while it was busy, which are exactly what a summary
  tends to drop.
- Asks of each candidate: if this were lost, would a future session go wrong? Anything that fails is
  dropped rather than saved just in case.
- Checks a rule before writing it down. "We always do X" inferred from one session is a guess until
  it has been checked against the tool's own documentation.
- Files what survives in a plain file where it belongs: a plan in `plans/` (through
  [plan-conveyor](../plan-conveyor/)), the repo's `AGENTS.md` or docs, or your personal
  `~/.agents/AGENTS.md`. Never a harness memory store.
- Sweeps what the conversation can't show. That means processes the session left running and what
  they serve, unpushed commits in every repo it touched, CI on what it pushed, and whether plans it
  filed for other repos arrived.
- Ends with a report, least urgent first, a one-line verdict ("safe to compact", or "not yet, needs
  a decision on X"), and a short prompt to paste into your next session.

## What it looks like

An abridged example of the report's shape. The two findings under "needs action" are real, and each
comes from a harvest described in the skill:

```
Where everything went
  To code             3 commits on main, pushed
  To a plan here      plans/2026-09-28-store-mirror-keyed-by-repository.md
  To another repo     1 plan filed for power-user-linux-setup
  Only in this chat   why the store is keyed by remote, not path: not yet written down

Settled
  CI green on the last pushed commit (checked, not assumed)

Needs action now
  4 CI-polling loops, 36 hours old, whose exit condition can never become true
  python3 -m http.server over the repo root, 24 hours up, bound to 0.0.0.0,
    serving the repo's .env and .git to the whole network

Verdict: not yet. Write down the keying decision and stop the two leftovers.
```

The next-session prompt that follows holds only what the next session can't discover for itself:
what to do first and why, anything with a short fuse, and a command to re-check each item before
acting on it.

## Why not something you already have

A harness memory store keeps the note where only that tool can see it, unreviewed and never retired.
A file in the repo is visible to every agent, every reviewer and `git log`.

Scrolling back through the chat stops working once it has been compacted, because the summary is
where loose ends disappear. And the risky leftovers, a server still up or a commit never pushed,
were never in the chat in the first place.

It is also deliberately on-demand. It installs no hooks and never runs on its own, because it writes
files, and a tool that writes files should run when you ask it to.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill session-harvest
```

It routes plans through plan-conveyor, so install both:

```shell
npx skills add TheodoreAD/agent-skills --global --skill plan-conveyor
```

Needs Python 3.11 or newer and git. It uses `gh` and `docker` when they are present.

## What it touches

Its script writes nothing. The agent following it writes in three places: the repo you are working
in, that repo's `plans/`, and the plans store. It never edits another repo's working tree or an
installed copy of anything. Stopping a leftover process is proposed to you, not done. The network is
used only for `git fetch` to each repo's own remote and `gh` for CI. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full procedure your agent follows.
- [`references/rationale.md`](references/rationale.md): the prior art considered, and why there is
  no memory tier at all.
