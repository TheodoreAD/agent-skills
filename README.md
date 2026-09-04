# agent-skills

Personal [Agent Skills](https://github.com/agentskills/agentskills) — plain `SKILL.md` directories,
readable by any agent that speaks the format, with no vendor bundle wrapped around them.

Everything here is authored against the vendor-neutral stack only: `AGENTS.md` for instructions,
Agent Skills for procedural knowledge, MCP for tools. No Claude Code plugin manifest, no
marketplace, no `.claude-plugin/` — a skill in this repo works the same in Codex, Cursor, Copilot,
Gemini CLI, Zed and the rest.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global          # every skill, user-level
npx skills add TheodoreAD/agent-skills --global --skill plan-docs # just one
```

The [`skills` CLI](https://github.com/vercel-labs/skills) copies the skill into the canonical
`~/.agents/skills/` hub (or the agent-specific directory for the agents that need one) and links
each detected agent at it. Nothing else is required — no manifest to register, no repo to clone.

Or, without installing anything, point your agent at [`skills/<name>/SKILL.md`](skills/) and let it
read the file directly.

## Skills

| Skill                                                              | Use it when                                                                                                                                                                                                       | Scope                   |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| [`db-defaults`](skills/db-defaults/)                               | Adding local persistence to a Python project — cache, relational, OLAP, documents, full-text or vector search, job queue, pub/sub, blobs, time series — and you want the default pick rather than an evaluation   | Opinionated but general |
| [`invoke-task-conventions`](skills/invoke-task-conventions/)       | Adding, renaming or reviewing an `inv <namespace>.<task>`, and weighing what a rename actually costs across docs, CI and other repos                                                                              | Opinionated but general |
| [`mcp-python-conventions`](skills/mcp-python-conventions/)         | The Python inside a stdio MCP server — where logs may go when stdout carries the protocol, what an exception at a tool boundary becomes, and the tool docstring as an LLM-facing contract                         | Opinionated but general |
| [`mcp-server-shipping`](skills/mcp-server-shipping/)               | Building, installing or registering a personal MCP server — entry point, `uv tool install` from git instead of PyPI, `claude mcp add` scope                                                                       | Opinionated but general |
| [`plan-docs`](skills/plan-docs/)                                   | Capturing an idea, drafting a design, or tracking work-in-progress in a repo's `plans/` directory — or, for a work repo that can't hold one, in the store outside it — and retiring a plan once it lands          | Opinionated but general |
| [`polite-mcp-conventions`](skills/polite-mcp-conventions/)         | Working in the `*-polite-mcp` repos — confirming before a first live mutating action against a real account, batching per-item decisions                                                                          | Personal                |
| [`python-conventions`](skills/python-conventions/)                 | Writing or reviewing Python and wanting one settled answer per design question — data modeling, dates/times, settings, guard clauses, restructuring, exceptions, async, HTTP                                      | Opinionated but general |
| [`python-refactor-audit`](skills/python-refactor-audit/)           | Restructuring a Python module that grew and nobody has reviewed as a whole — the commit-by-commit loop, which tests may change, a second oracle when the suite can't see the change, and when not to do it at all | Opinionated but general |
| [`python-testing-conventions`](skills/python-testing-conventions/) | Writing or restructuring Python tests — fixture scope, when to parametrize, DAMP vs DRY, and whether a dependency should be doubled or run for real                                                               | Opinionated but general |
| [`research-library`](skills/research-library/)                     | Reaching for reference material — before fetching from the web, when cloning a vendor repo, when refreshing the shared `$RESEARCH_HOME` library, or when judging whether a named package is fit to depend on      | Opinionated but general |
| [`session-bash-audit`](skills/session-bash-audit/)                 | Measuring how agent sessions actually use the Bash tool from real transcripts, and routing each finding to the mechanism that owns it                                                                             | Opinionated but general |
| [`session-harvest`](skills/session-harvest/)                       | Deciding what from a session is worth persisting, and where it goes — a plan, a repo's `AGENTS.md`, a global preference, or nowhere                                                                               | Opinionated but general |
| [`skill-authoring`](skills/skill-authoring/)                       | Writing a new skill, editing an existing `SKILL.md`, or getting a skill change actually deployed — and when it should be an `AGENTS.md` rule instead                                                              | General                 |
| [`skill-fitness`](skills/skill-fitness/)                           | Measuring whether installed skills work — why one never fires, which two compete for a request, what the listing costs, and which repeated one-liners should become skill code                                    | Opinionated but general |

**Scope** says how much of the skill is a convention anyone can adopt versus a personal preference:
_general_ is portable as written, _opinionated but general_ picks one defensible convention out of
several and commits to it, and _personal_ depends on how one particular machine or repo family is
set up. No skill here sends anything off the machine on its own. Four do read or write outside the
repo you are working in, and each declares it: `research-library` (`$RESEARCH_HOME`), `plan-docs`
(`$PLANS_HOME` and `$PLANS_SENSITIVE_HOME`, for work repos that can't hold their own plans),
`session-bash-audit` (Claude Code's own transcripts) and `session-harvest`, whose sweep reads those
transcripts plus the machine's processes, listening sockets, container images and both stores —
read-only, and it writes nothing itself. `plan-docs` also describes pushing the shareable half of
its store to a remote you configure — behind a content scan, and never the half holding employer or
client work.

**Platform.** Everything here is written for a POSIX machine and none of it has been run on Windows
— CI is Linux-only by decision, so the Windows behaviour below is declared rather than measured. The
scripts are stdlib-only Python and resolve their locations from `$XDG_*` first, falling back to
`%APPDATA%` / `%LOCALAPPDATA%` there — but two skills assume more than a path. `session-bash-audit`
measures POSIX-shell idioms (`&&`, `;`, `|`, `cd`, `sed -n`), so it describes a Git Bash or WSL
session and says nothing useful about a PowerShell one; `session-harvest`'s sweep shells out to
POSIX tools to read processes, sockets and images. Both say so in their own bodies. A `0700` mode
set at creation is accepted and ignored on Windows, so no skill here treats one as protection.

## Layout

```
skills/<name>/
├── SKILL.md          # the skill itself — YAML frontmatter (name, description) + the instructions
├── references/       # rationale, prior art, evidence — read on demand, not loaded up front
└── scripts/          # anything the skill runs, when it has one
```

Each skill's `references/` is where its reasoning lives — why this convention and not the obvious
alternative, what went wrong the last time, which sources it was checked against. That is
deliberately inside the skill rather than in a repo-level `contributing/` tree, so a skill stays a
self-contained unit that can be read, copied or vendored on its own.

## License

MIT — see [LICENSE](LICENSE).
