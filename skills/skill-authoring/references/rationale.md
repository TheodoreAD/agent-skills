# Why this skill says what it says

## Why "self-update on friction" is a convention, not one skill's quirk

Surfaced while designing `session-harvest`: a routing decision it made mid-design was genuinely
ambiguous (should "new skills should default to self-update mechanics" be a personal preference, or
a documented convention?) — asked rather than guessed, and the answer was "a convention, stated
somewhere shared." That is itself an instance of the pattern.

The underlying reason it needs stating: a convention skill that never revises itself from what
actually happens when it is used goes stale the way any unmaintained doc does, except worse, because
nobody re-reads a `SKILL.md` the way they would re-read `AGENTS.md`. It is loaded, followed, and
never looked at again. Building the revision step into the skill is the only thing that closes that
loop.

## Why a skill about shipping skills must describe the portable mechanism

Until 2026-08-27 this content lived in a skill that said skills ship by declaring them in one
particular machine-setup repo's config file and running that repo's own task runner. That was
accurate, and it was the exact problem: the skill telling people how to ship a skill described a
mechanism only its author could run. A reader without that repo had a path they did not have and a
command they could not run.

The general form is worth keeping: **a skill about a workflow must describe the workflow's portable
mechanism, not the author's automation around it.** Automation is the right place for "and here is
how my machine does it"; the skill is not. Where a machine-specific example genuinely helps, label
it as one example rather than as the procedure.

## Why the split from `mcp-server-shipping` (2026-08-28)

One skill covered both "ship a personal MCP server" and "ship an Agent Skill", with a `description`
naming both. That violated the rule the skill itself stated: two responsibilities in one
description, so every prompt about editing a skill had to win against text half-about
`uv tool
install` and `claude mcp add`, and vice versa.

The trigger test settles it. "I want to register an MCP server for Claude Code" and "I edited a
SKILL.md, how do I deploy it" are different requests with no overlap in vocabulary; nothing about
one should have to compete with the other. After the split each description covers one request
shape, and both got shorter.

What stayed together deliberately: the MCP repo dev loop (`repo-tasks`, `inv dev-env.setup`,
`uv run inv` in automation) stayed with `mcp-server-shipping`, because those repos _are_ the MCP
servers — it is that skill's subject matter, not general authoring advice.

## Why a bundled script gets stdlib-or-PEP-723 and never a venv (2026-08-28)

Researched when a plan put a real script inside a skill for the first time and "does it need a
venv?" was raised as an open worry. It does not, and a venv per skill is not the convention — it is
the thing the convention exists to avoid.

[agentskills.io's "Using scripts in skills"](https://agentskills.io/skill-creation/using-scripts) is
the spec-level guidance and describes exactly two tiers, neither of which is a virtual environment:
a **one-off command** referenced straight from `SKILL.md` through a runner that resolves at
invocation (`uvx`, `pipx run`, `npx`, `bunx`, `deno run`, `go run`), pinned to a version and with no
`scripts/` directory at all; or a **self-contained script** in `scripts/` declaring its dependencies
**inline** — PEP 723 for Python, run with `uv run`, verbatim "no separate manifest file or install
step required". Every other language on the page gets the same treatment (Deno `npm:` specifiers,
Bun auto-install, Ruby's `bundler/inline`).

Where venv-per-skill does appear is
[anthropics/skills discussion #117](https://github.com/anthropics/skills/discussions/117), and the
problem there is not ours: **cloud skills from different vendors sharing one sandbox**, where skill
A needs `pandas==2.1` and skill B needs `2.2`. The debated answers are venv-per-skill,
container-per- skill for untrusted code, and — rejected as fragile — `sys.path` namespacing. The one
point of consensus worth carrying is that dependencies should be _declared_ even before isolation is
enforced, so a conflict is detectable rather than silent; PEP 723 is that declaration. A single
user's own skills on their own machine have no multi-tenant conflict to isolate.

Extracted 2026-09-01 from the now-retired `plans/2026-08-28-cross-repo-plan-store.md`, which
researched it while deciding where `plan-docs`' own script would live.

## Why "editing the installed copy" gets its own emphasis

It is the failure that produces no error. A copy under `~/.agents/skills/<name>/` is writable, the
edit appears to work, and the skill visibly behaves differently in the current session. Everything
after that is silent: the next install overwrites it, no other machine sees it, and there is no
commit to review. Compare with the alternative failures in this workflow — a missing push produces
"my change didn't take effect", which at least prompts investigation.

The same asymmetry is why the redeploy sequence spells out the push step rather than assuming it.
The installer clones from the remote, so "committed" and "deployed" are separated by a step that
produces no symptom when skipped except the change quietly not existing.
