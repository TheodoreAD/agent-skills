# research-library

Cloned source outside your repos, for your agent to grep instead of the web.

When a coding agent needs to know how a library behaves, it usually searches the web or fetches a
docs page. What comes back is a summary of a summary: rendered prose that may describe another
version, or a feature that was never built. The code, the tests and the changelog have the real
answer. And an agent reads a local tree far better than it pages through a website one fetch at a
time.

research-library gives your agent one directory, `~/research` by default, outside all your projects.
It holds shallow clones of the repos you keep referring to, plus PDFs and mirrored docs sites. The
agent checks there first, clones what's missing with one command, and searches it locally. Every
project on the machine shares the same copies.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others.

## What you get

- One command to add a repo. It clones shallow, names the entry `<host>--<owner>--<repo>` from the
  clone's real remote, and writes a small provenance file recording the URL, commit and date. You
  always know which version you are reading.
- Clones hold text only, by default. Images, video and compiled files stay on the server, since grep
  skips them anyway. On one real repo that took the clone from 141 MB to 3 MB, with the same 257
  searchable files in both.
- Updates that don't destroy anything. One command refreshes every clone, and it leaves alone a
  clone that someone deliberately deepened to read its history.
- A disk report that says which entries are big and why: history, vendored code, or binaries nobody
  can search.
- Third-party content kept out of your repos. Anything inside a project's working tree gets read as
  trusted project context by every repo-wide search, which is how a cloned README becomes a prompt
  injection. Outside the repo, it is read only when a task names it.

## Its second job: judging a dependency

Before you add a package, the agent can check it against the registry, GitHub and the project's own
source instead of a search summary. PyPI, npm, crates.io, apt and GitHub-release-only tools are all
covered. Real output, trimmed:

```
$ python3 package_health.py pypi httpx
httpx 0.28.1  —  The next generation HTTP client.

maintenance
  releases         67 stable releases, 0 in the last year
  first / last     2019-07-19 … 2024-12-06
  since last       662d
  pre-releases     9, latest 2026-08-31   — not counted above; a dev line moving is not the stable line moving
  last push        2026-03-29 (184d ago)
  not scored       15525 stars, 2643 forks
  humans/365d      4 over 5 commits
  bus factor       2

ships (0.28.1)
  linux x86_64     pure-Python wheel, installs anywhere
```

Over 15,000 stars, a pre-release last month, and no stable release in almost two years. Whether that
matters depends on what you need from it. The point is that you see it before choosing, and that
stars are listed as "not scored" on purpose.

It also reports what installing actually downloads (wheel or source build, npm platform packages,
install scripts that run code on your machine), each version floor compared with your machine, and
how far an apt package lags behind upstream.

## Why not just let the agent search

Search is fine for finding which project to look at. It is a poor way to learn what that project
does. Two cases from building this skill: a docs page described a GNOME keybinding schema that did
not exist in the installed version, and a project's README advertised a lookup feature whose name
appears nowhere in its code. One grep settled each. A summary would have repeated both.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill research-library
```

Then create the library directory (`mkdir ~/research`, or point `RESEARCH_HOME` somewhere else).
From then on, ask things like "how does uv resolve this? check the source", or "is this package
still maintained?".

Agents follow a standing rule more reliably than a skill they have to remember to load. For that
reason, add one line to your `AGENTS.md`, such as "check `$RESEARCH_HOME` and clone the source
before fetching docs from the web".

Needs Python 3.11 or newer and git. `gh`, logged in, for the GitHub half of the package report.

## What it touches

It writes only inside the library directory, never into a project. It uses the network for the clone
URLs you give it and for public, read-only registry and GitHub APIs, through your own `gh` login.
The complete list is in [`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/rationale.md`](references/rationale.md): why a shared library, the naming rule, and
  why embeddings and RAG were looked at and left out.
- [`references/dependency-health.md`](references/dependency-health.md): what each package-health
  number hides, and each registry's traps.
