# plan-conveyor

Design plans as plain files in the repo, from first idea to deletion.

Coding agents forget everything between sessions. The usual workarounds are a transcript nobody
rereads, a harness's private memory that no other tool or colleague can see, or a `PLAN.md` that
grows forever and is half wrong by the second week.

plan-conveyor gives your agent a small convention instead. Each idea or design gets its own markdown
file in `plans/`, with a status at the top, and a script does the bookkeeping. Plans are committed
with the code, reviewed like the code, and readable by any agent or any person. When a plan lands,
whatever is worth keeping moves to where it belongs (the code, a README, `AGENTS.md`) and the file
is deleted. So `plans/` stays a short list of what is actually still open.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others.

## What you get

- Every plan has a status: `idea`, `planned`, `in-progress`, `blocked on <reason>`, `landed` or
  `abandoned`. The agent changes it through a command that checks the plan is ready for it, not by
  editing the line.
- Decisions keep their reasons. Inline tags such as `[DECISION: …]`, `[PITFALL: …]` and
  `[NEEDS CLARIFICATION: …]` mark the claims that matter, and you can grep them across every plan. A
  plan with an open question or an unproven claim can't be marked `landed`, and anything marked
  `[DEFERRED: …]` is moved to an open plan before the file goes.
- "What should I work on next?" is one command, for this repo or for every repo on the machine.
- Plans for repos you can't write to. Client and employer repos rarely want a `plans/` directory
  added. Their plans go to a private store outside every working tree: a git repo of its own, with
  no remote unless you add one.
- Handing work to another repo without touching it. A session that notices something another repo
  needs files a plan for that repo. The next session working there is offered it. Nobody commits
  into someone else's working tree.
- A check against leaking client names. Before a commit to a public repo, `scan` looks for employer
  and client names, derived from your own project directories. There is no list of clients to
  maintain, which also means there is no such list to leak.
- Nothing is lost at deletion. A retired plan stays in git history, and `archive --search` brings it
  back.

## What it looks like

Ask your agent "what's open here?" and it runs `list`. This is this repository's own output,
trimmed:

```
in-progress (5)
  2026-09-07-research-library-clone-size.md       updated 2026-09-07  5 DECISION  2 NEEDS CLARIFICATION
  2026-09-28-store-mirror-keyed-by-repository.md  updated 2026-09-28  6 DECISION  1 UNVERIFIED
  …
blocked on repo-tasks adding a consumer pyright tier (1)
  2026-09-13-repo-tasks-consumer-sweep.md         updated 2026-09-29  3 DECISION  3 PITFALL

planned (2)
  2026-09-05-a-piped-gate-that-cannot-lie.md      updated 2026-09-05  5 DECISION  2 PITFALL  1 UNVERIFIED

idea (61, showing 10)
  …
waiting on this repo (4)
  github.com-personal/power-user-linux-setup/2026-08-29-harvest-blind-to-history-rewrite.md
  …
```

The last group is plans in other repos that are blocked on this one. A plan file itself is ordinary
markdown:

```markdown
---
status: in-progress
updated: 2026-09-28
---

# Store folders keyed by repository, not by clone path

[DECISION: link each repository to its store folder by its origin remote. Two clones of one repo
used to get two folders, and neither could see the other's plans.]

[NEEDS CLARIFICATION: what happens to a clone with no remote at all?]
```

## Why not something you already have

A harness's memory or plan mode keeps the plan where only that one tool can see it. A file in the
repo is visible to every agent, every reviewer and `git log`, and it survives switching tools.

An issue tracker is the right home for a team's backlog. These plans are the design notes one
developer and their agent work from, versioned next to the code they describe. The skill's
[prior-art notes](references/prior-art-task-trackers.md) compare it with markdown task trackers,
git-bug and beads.

A single `PLAN.md` grows without limit, and nobody can tell which parts are still true. One file per
topic, each with a status and a rule for when it is deleted, keeps the set small enough to trust.

## Built from what went wrong

Most rules in the skill exist because something failed while it was being used, and each carries the
date and the count. Two examples: of 101 pushes to a plans store, 32 had no confidentiality scan
before them, so publishing now goes through a `push` command that scans exactly what it is about to
send and refuses on a hit. And nine finished plans once sat unretired across five repos because
nothing ever asked anyone to clean them up, so the agent's first plan-conveyor command in a session
now asks.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill plan-conveyor
```

Then talk to your agent normally: "write this up as a plan", "what plans are open across my repos?",
"this one landed, retire it". On a machine that also holds client or employer work, ask the agent to
set plan-conveyor up. It walks you through each routing decision and explains what getting it wrong
would cost.

Needs Python 3.11 or newer and git. No packages to install.

## What it touches

It writes plan files in your repo's `plans/` and in its own stores (`~/plans` by default). It
commits through its own `commit` command, which takes only the plan files it names, so another
session's staged work never rides along. It uses the network for one command, `push`, and only to
the remote your store already has. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/design-rationale.md`](references/design-rationale.md): why the statuses, tags and
  retirement rule look the way they do.
- [`references/prior-art-task-trackers.md`](references/prior-art-task-trackers.md): the tools it was
  compared against.
