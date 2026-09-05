---
status: in-progress
updated: 2026-09-05
---

# A Windows CI leg, and the sweep's Windows arms, reversing the 2026-09-04 decision

## Context

`2026-09-04-skills-on-windows.md` (retired; `archive --show` reads it back) landed the location
defaults, the `tarfile` extraction and the POSIX declarations, and closed with a decision against a
Windows CI leg: a runner would measure three things and settle neither of the two questions that
need a real Claude Code session on Windows, so "declared, not measured" was the honest position.

Reopened 2026-09-05 by the user — _"continue making sure all the skills work on windows, without
compromising the features they have today working for linux"_ — and reversed on this reasoning:
without any run on Windows, every claim in the corpus stays declared, and the unit suite is the only
instrument available for the location defaults, the extraction, the git subprocesses under
`autocrlf`, and now the sweep's parsers. Three items was the whole list a runner could measure; it
is still three more than zero. The user chose the deeper option: the CI leg **and** a port of the
sweep's `ps`/`ss` steps.

## What landed 2026-09-05, and how far each is verified

- **The project-slug bug, on every platform.** Claude Code slugs a project path as `[^a-zA-Z0-9]` →
  `-` with a 200-character cap and a hash suffix, read from the CLI binary. Three copies in
  `audit.py` and `harvest.py` replaced only `/` and `.`, so a repo path holding `_` never matched
  and the own-repo rows reported zero on Linux too. Fixed and pinned by tests; the
  session-bash-audit body stops calling the Windows slug unverified.
- **The suite can run on Windows.** Fake-home fixtures set `USERPROFILE` beside `HOME`; the
  store-mode test is skipped where a POSIX mode is ignored by design; the symlink test skips when
  the runner cannot create one; `trigger.py` reads its child through a thread instead of `select()`,
  which on Windows takes sockets only, and resolves the launcher with `which()`. One live run on
  Linux confirmed the thread refactor.
- **`tests-windows.yml`**, a separate workflow so `ci.yml` stays byte-identical to the family
  template: `uv run --no-project --with pytest pytest` on `windows-latest`, with `autocrlf` off and
  long paths on. Only pytest, because the quality gate's tools are pinned as Linux wheels.
- **The sweep's Windows arms.** Processes from `Get-CimInstance Win32_Process` through PowerShell,
  one tab-separated line per process; listeners from `netstat -ano` filtered to TCP rows in
  `LISTENING` state. `Win32_Process` has no process groups, so every process is its own group except
  this script's direct children, which join its group — that is how the sweep keeps its own
  PowerShell out of the survivors. The served-directory and readable-secrets findings apply through
  `--directory`, since there is no `/proc` to read a cwd from.

[UNVERIFIED: **the CI leg has never run.** It runs on the first push, and the first red is likely to
be a path-string assertion somewhere in `test_plan_store.py` comparing `str(path)` with `/` in it —
the suite was never written with backslashes in mind. Read that run before believing anything below
it; the fixture work of 2026-09-04 was the prerequisite, and whether it was the whole prerequisite
is exactly what the run answers.]

[UNVERIFIED: **the two Windows commands have never executed.** The parsers are pinned to the
documented column layouts by fixture text; the PowerShell script inside one `argv` element, the tab
separators surviving PowerShell's output encoding, and `netstat` needing no elevation for `-o` are
all reasoned, not seen. A Windows CI leg exercises the parsers only — the runner has a `ps`-less
PowerShell, so `sweep --only processes` there would be the first live measurement, and it is worth
adding as a smoke step once the suite is green there.]

## Still declared, not measured, and what would settle each

- Whether Claude Code's Bash tool on Windows produces POSIX-shell transcripts (Git Bash) or
  PowerShell ones — needs one real Windows session's transcript. The slug question that used to sit
  beside it is settled from the binary.
- Whether `%APPDATA%` and `%LOCALAPPDATA%` are set in the shell the harness spawns — the fallback to
  `~/AppData/...` exists, and only a session would show which branch runs.

## Recommended direction

1. Push, read the first Windows run, fix what it names as its own commit each, and re-run until
   green. Expect one or two rounds.
2. Add a smoke step to the Windows workflow that runs the sweep's processes and sockets sections
   from the checkout with `--json` and asserts `available: true` on both — the one live measurement
   a runner can make of the arms above.
3. Leave the two transcript questions open until a Windows user appears; they cannot move from here,
   and saying so is the honest state.
