---
status: idea
updated: 2026-09-01
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

[NEEDS CLARIFICATION: whether this is a section in `invoke-task-conventions` or a short rule in
`~/AGENTS.md`. The miss is silent and expensive — a hang with no output, which is the shape that
argues for the always-loaded file — but the trigger is sharp and topic-bound ("a task that runs
something interactive"), a skill that owns the topic already exists, and that file stands at 38
rules / 598 lines against its own ≤15 / ≤200 reference points. Filed to the skill on that reasoning;
worth a second opinion, since the last comparable call (a non-terminating CI-poll loop) went the
other way on exactly the silent-and-expensive test.]

[NEEDS CLARIFICATION: whether the other family repos have the same call shape today. `rg 'pty=True'`
across `repo-tasks`, `scaffoldapy` and the `*-polite-mcp` repos would answer it in one command, and
was not run from here — reading another repo is fine, but the finding belongs to whoever works there
next.]

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
