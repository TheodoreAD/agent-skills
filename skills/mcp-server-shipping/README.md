# mcp-server-shipping

Personal MCP servers installed from git and registered once, no PyPI release.

You wrote an MCP server for yourself, and it works in the repo you wrote it in. Now you want it in
every project, on this machine and the next one, without turning a personal tool into a package
release. The usual first attempt registers the server with a `uv run --directory <path>` or
`uvx --from git+<url>` command baked into the client's config. That works until you switch between
your working copy and a released version, and then the registration has to change by hand each time.

This skill gives your agent one workflow for that job: an entry point, `uv tool install` to put a
real binary on your `PATH`, and a registration that names only that binary. Switching between the
code you are editing and a pinned version from GitHub becomes one reinstall, and the registration
never changes.

The workflow was written for the author's own family of small MCP servers, and its examples use
their names. Substitute your own everywhere.

## What you get

- An entry point first. A `[project.scripts]` line in `pyproject.toml` added before the server code,
  not retrofitted, so the server has a stable command name from day one.
- Two install sources for the same name. `uv tool install -e <checkout>` while you are developing,
  which picks up local edits without reinstalling, and `uv tool install git+<url>` (pinned to a tag
  or commit once it is worth freezing) when you just want to use it.
- A registration that never has to change. Because both installs put the same binary name on your
  `PATH`, the client is pointed at that name once. Switching sources is `uv tool install` again, and
  uv replaces the old install.
- No PyPI. For a personal tool the GitHub repo is the artifact store, so there is no version bump,
  publish step or API token to manage.
- A scope decision for Claude Code: `--scope user` for a tool you want in every project, and
  `--scope project`, which writes the repo's `.mcp.json`, only for a repo that should offer the
  server to anyone who clones it.
- A rule for automation that holds whatever task runner you use. The runner is a per-project
  dependency, so CI and scripts call it through the project's environment
  (`uv run <runner>
  <task>`), never as a bare name that might resolve to another project's copy or
  to nothing.

## What it looks like

While you are developing, with local edits picked up live:

```shell
uv tool install -e <path-to-your-checkout>
```

Once you just want to use it:

```shell
uv tool install git+https://github.com/TheodoreAD/olx-polite-mcp
```

Either way, registration is the same line, run once:

```shell
claude mcp add --scope user olx-polite-mcp olx-polite-mcp
```

## Which parts are Claude Code specific

The entry point, `uv tool install` and skipping PyPI work for any MCP client: what they produce is a
command on your `PATH`, and any client that launches a stdio server by command name can use it. The
registration step is Claude Code's. `claude mcp add`, its `local`, `project` and `user` scopes, the
`.mcp.json` file, and the one-time approval a new session asks for before launching a project or
user server are all Claude Code behaviour. On another client, register the same binary name the way
that client registers servers.

## Why not the obvious alternatives

Publishing to PyPI is ceremony with no audience for a personal tool, and it makes testing a dev
build end to end mean releasing it somewhere first.

Putting `uvx` or `uv run` directly in the registration was this skill's own first draft. It was
revised after the first of the author's servers to get a real installation section settled on
`uv tool install` instead: one stable binary name that registration points at, rather than a path or
flag inside the registration that must be edited whenever the source changes.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill mcp-server-shipping
```

Then ask your agent to "make this MCP server installable everywhere" or "switch this server back to
my local checkout". For the Python inside the server rather than its packaging, see
[mcp-python-conventions-taudelta](../mcp-python-conventions-taudelta/).

Needs uv, and the `claude` CLI for the registration step.

## What it touches

The skill ships no scripts and runs nothing itself. The commands it tells your agent to run do
write: `uv tool install` creates a tool environment and a shim on your `PATH` (`~/.local/bin` by
default), and `claude mcp add` writes the registration into Claude Code's user config, or into the
repo's `.mcp.json` for project scope. Both are undone with the same tools' uninstall and remove. The
git install clones the repo you name. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the workflow your agent follows.
- [`references/rationale.md`](references/rationale.md): why git and uv beat PyPI, why user scope,
  and why one registered command covers both install sources.
