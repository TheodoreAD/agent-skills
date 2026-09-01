---
status: landed
updated: 2026-09-02
---

# `invoke-task-conventions` says nothing about a task that waits for typed input

## Context

An invoke task that runs a command needing something typed — a sudo password, an ssh key passphrase,
a debconf question — cannot do it through `c.run`, on any Python, for two independent reasons. The
skill that owns invoke task authoring across this family currently says nothing about it:
`rg 'pty|stdin|interactive|sudo'` over `skills/invoke-task-conventions/SKILL.md` returns nothing.

This was found the expensive way — a first `inv wsl.install` on a corporate WSL machine hung after
the sudo prompt, with the password echoed in plain text — and both causes were then reproduced in a
container.

**1. invoke echoes stdin, and races the child for it.** `Runner.should_echo_stdin()` is
`(not using_pty) and isatty(stdin)`, so for any non-pty `c.run` from a terminal invoke prints every
byte it reads back to stdout — it has put the terminal in cbreak, so otherwise the user would see
nothing. Meanwhile `sudo` reads `/dev/tty`, the same terminal. Whichever wins a given read gets the
bytes: when invoke wins, the password is printed _and_ the child never sees it, so it re-prompts and
the run looks stuck. Demonstrated with a task whose whole body is `c.run("head -n 1 > /dev/null")`:
typing `SUPERSECRET` prints it back.

**2. On Python 3.14 invoke cannot forward stdin at all.** `terminals.bytes_to_read()` calls
`fcntl.ioctl(stdin, FIONREAD, b"  ")` — a 2-byte buffer for a 4-byte result. Every Python before
3.14 overflowed it silently; 3.14 hardened `fcntl.ioctl` and raises `SystemError: buffer overflow`,
which kills invoke's stdin thread on the first keystroke. Nothing reaches the child, pty or not, and
it waits forever. Upstream: pyinvoke/invoke#1070, fixes open, **unreleased as of invoke 3.0.3**.

Measured in a container, same invoke 3.0.3 throughout:

| Python  | `c.run` needing forwarded stdin                    |
| ------- | -------------------------------------------------- |
| 3.10–13 | works, and echoes the typed text (cause 1)         |
| 3.14    | **hangs — nothing is ever forwarded to the child** |

Why it belongs in the skill rather than one repo's own instructions: **every repo in this family
runs invoke, and the interpreter is the family default.** `power-user-linux-setup` pins
`uv_python_default = "3.14"`, and `repo-tasks` is installed as a uv tool on the same default — so
any task in any consumer repo that shells out to something interactive hangs today, silently. The
repo where this was found had four such calls: a sudo pre-auth plus `ssh-keygen`, `ssh-copy-id` and
`ssh-add`, all written as `pty=True` in the belief that a pty was the fix for cause 1.

`pty=True` is the trap worth naming explicitly. It appears to fix cause 1 (the child controls echo
on its own pty) and does nothing for cause 2, so it reads as the correct pattern right up until the
interpreter moves under it.

## Open questions

[DECISION: **the skill, and the second opinion agrees — for a reason the original argument only
half-stated.** The silent-and-expensive test does pull toward `~/AGENTS.md`, and that is what makes
this a close call rather than an obvious one. What settles it is that the rule is **not
self-contained prose**: it needs the two causes, the interpreter matrix and the `pty=True` trap to
be actionable, and an always-loaded file cannot carry that at a size worth paying on every session —
`~/AGENTS.md` measured **636 lines on 2026-09-02**, up from the 598 this plan recorded a day earlier
and still growing. A one-line version there ("never run anything interactive from a task") would be
the part that is easy to remember and useless when it matters, because the failure looks like a hang
rather than like a rule being broken. The skill owns the topic and the reader arrives there with the
task open.]

[DECISION: **yes, the family is affected today — two live call sites in `repo-tasks`.** Measured
2026-09-02 with `rg 'pty=True'` across `repo-tasks`, `scaffoldapy`, the `*-polite-mcp` repos and
`product-research-pipeline`: `src/repo_tasks/docker.py:156` (`docker login`) and
`src/repo_tasks/helm.py:139` (`helm registry login`), both credential prompts, plus three unit tests
asserting that exact call shape. No other repo in the family has one. Filed for that repo as
`2026-09-02-interactive-logins-hang-on-python-314.md` rather than fixed from here.

The test detail is the part worth keeping: the three tests assert what is passed to a **mock**, so
they pass whatever the runtime does. That is why nothing caught this — the call shape is verified
and the behaviour is not.]

## Recommended direction

A section in `skills/invoke-task-conventions/SKILL.md` stating the invariant and the two shapes that
satisfy it:

> **A task may not run anything that waits for typed input.** Not through `c.run`, with or without
> `pty=True` — invoke echoes stdin itself on non-pty runs while the child reads `/dev/tty` (a race
> that prints passwords), and on Python 3.14 invoke's stdin thread dies on the first keystroke
> (pyinvoke/invoke#1070, unreleased), so the child waits forever. Run interactive children as a
> plain `subprocess` inheriting the real terminal, and make everything else non-interactive:
> authenticate sudo once up front and use `sudo -n` thereafter, and give apt
> `DEBIAN_FRONTEND=noninteractive` plus `--force-confold`.

The worked implementation is in `power-user-linux-setup`: `util.run_interactive()`,
`util.ensure_sudo()` (authenticate once outside invoke, rebind the prefix to `sudo -n`, keepalive
thread so the cache cannot lapse mid-run), `util.apt_command()`, and the reasoning in
`contributing/interactive-input.md`.

## Verification

- The two causes are reproduced by `tests/containers/` in `power-user-linux-setup` (a pty driver
  plus a password-protected-sudo-user image); the interpreter matrix above came from running the
  same probe under 3.10–3.14.
- Whether a consumer repo is affected is one `rg 'pty=True'` in that repo.

## Migrated to

- `skills/invoke-task-conventions/SKILL.md`, "A task may not run anything that waits for typed
  input" — both causes, the interpreter matrix, the `pty=True` trap, the two shapes that satisfy the
  rule, and `rg 'pty=True'` as the audit.
- The store, as `github.com-personal/repo-tasks/2026-09-02-interactive-logins-hang-on-python-314.md`
  — the two affected call sites, filed for the repo that owns them.

Deliberately not migrated: the `power-user-linux-setup` implementation details
(`util.run_interactive()`, `util.ensure_sudo()`, `util.apt_command()` and its
`contributing/interactive-input.md`). The skill points at the shape rather than shipping a second
copy of another repo's code, which would diverge from the one that is maintained.
