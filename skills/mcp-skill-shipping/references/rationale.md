# Why this workflow is shaped the way it is

Design rationale for `SKILL.md` — the workflow for taking a personal MCP server or skill repo from a
working checkout to something an agent can actually load, on the dev machine and everywhere else.
What it _is_ and how to use it live in the skill; this page is the _why_, including the branches
that were tried and rejected.

## Why git+`uv` instead of PyPI

Each repo in this family is a personal, non-commercial, single-user (maybe a friend or two) tool. A
PyPI release process — version bumps, `uv publish`, API tokens — is ceremony with no real audience
at this scale. `uv tool install` already resolves straight from a git remote and drops a real `PATH`
shim:

```shell
uv tool install git+https://github.com/TheodoreAD/olx-polite-mcp
```

so the GitHub repo itself is the artifact store. This needs nothing beyond a `[project.scripts]`
entry point in `pyproject.toml` and a reachable (public, or deploy-key-accessible private) repo — no
packaging step, no publish step. Pin `@<tag>`/`@<sha>` once a repo reaches a point worth freezing;
tracking the default branch is fine while still iterating. Revisit PyPI only if a repo ever needs to
be pip-installable as a transitive dependency of something else, which doesn't apply to a standalone
MCP server.

An earlier draft used `uvx --from git+URL` / `uv run --directory <path>` directly in
`claude mcp add`'s command. Revised after cross-checking against `olx-polite-mcp/README.md` — the
first sibling repo to reach a real "Installation" section — which settled on `uv tool install`
instead: one stable `PATH` binary name that registration points at regardless of source, versus a
path/flag baked into the MCP registration itself that has to change by hand when switching source.
Recorded here as the reason the skill reads the way it does now, not the way it first did.

## Why `--scope user` for `claude mcp add`

Claude Code's MCP registration has three scopes: `local` (per-project, per-user, unshared — the
default), `project` (writes `.mcp.json` into the project, checked into git, shared with anyone who
clones it), and `user` (`~/.claude.json`, available in every project on the machine). These are
personal cross-project tools, not something a specific project's collaborators need pinned in its
own repo — `user` scope is the direct analogue of how skills install globally, so both mechanisms
end up with the same reach. `project` scope would make sense for a _consumer_ repo (e.g. one wanting
to pin exactly which site-MCP versions it was built against) — not ruled out, just not the default
case this skill covers.

## Same registered command, two install sources — why that matters

The whole point of adding a `[project.scripts]` entry before `server.py` even exists, plus
installing it via `uv tool install` rather than pointing `claude mcp add` at a `uv run`/`uvx`
invocation directly, is that switching between "I'm actively developing this" and "I just want to
use it" becomes `uv tool install -e <path>` vs. `uv tool install git+<url>` — the _registration_
itself (`claude mcp add --scope user <name> <name>`) never changes, since both installs land the
same binary name on `PATH`. Never two divergent MCP-registration setups to keep in sync, and never a
reason to publish a dev build somewhere just to test it end-to-end.

## Why "self-update on friction" is a convention, not one skill's quirk

Surfaced while designing `session-harvest`: a routing decision it made mid-design was genuinely
ambiguous (should "new skills should default to self-update mechanics" be a personal preference, or
a documented convention?) — asked rather than guessed, and the answer was "a convention, stated
here." That is itself an instance of the pattern: a convention skill that never revises itself from
what actually happens when it is used goes stale the way any unmaintained doc does, except worse,
since nobody re-reads a skill file the way they would re-read `AGENTS.md`. Worth generalizing to
every future convention skill rather than treating it as bespoke to `session-harvest` — hence the
short rule in the skill pointing back at that skill as the worked example instead of re-explaining
the mechanics twice.

## Why the skill no longer documents a single machine's install mechanism

Until 2026-08-27 this skill said skills ship by declaring them in one particular machine-setup
repo's `setup.toml` and running that repo's own invoke task. That was true, and it was the exact
problem: the skill telling people how to ship a skill described a mechanism only its author could
run. The `skills` CLI does the same job for anyone, on any agent, so the skill now describes that
instead. The machine-specific declaration still exists on that machine, but it is a consumer of the
published repo, not the way skills are distributed.

The general form of that lesson is worth keeping: **a skill about a workflow must describe the
workflow's portable mechanism, not the author's automation around it.** Automation is the right
place for "and here is how my machine does it"; the skill is not.
