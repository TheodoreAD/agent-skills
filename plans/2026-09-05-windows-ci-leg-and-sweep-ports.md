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

**The CI leg ran three times on 2026-09-05 and went green on the third.** What the first two runs
named, none of it in the scripts except two small things:

- 136 red on the first run, four causes: a fake config written with a Windows path inside a TOML
  basic string (a backslash opens an escape, so `C:\Users` is an invalid `\U`), which took a hundred
  plan-store tests down with one helper line; tests reading files through the platform code page,
  which turned the skeleton's em dash into mojibake and put a description over the cap by four
  characters; harvest fixtures keying commands on POSIX separators while `Path` renders backslashes;
  and two suites reading the real platform constant where they meant the POSIX arm. Plus the
  workflow setting `autocrlf` _after_ the checkout, which is the only order in which it does
  nothing.
- 6 red on the second, the same four causes in the places the first round missed.
- The two script findings: three reads in `session-bash-audit` relied on the platform encoding, so a
  transcript with an em dash would have raised on Windows; and `doctor` joined a store path and a
  root name with a literal slash, printing a mixed-separator path there.

[DECISION: **the prediction was wrong in an instructive way.** The expected first red was a
path-string assertion; the actual one was TOML escaping, which no amount of reading the tests would
have predicted, and the encoding findings were in the scripts, not the tests. That is the argument
for the leg in one sentence: the failures a platform produces are not the ones a reviewer on the
other platform imagines.]

[UNVERIFIED: **the two Windows commands have never executed.** The parsers are pinned to the
documented column layouts by fixture text; the PowerShell script inside one `argv` element, the tab
separators surviving PowerShell's output encoding, and `netstat` needing no elevation for `-o` are
all reasoned, not seen. The workflow now pipes a live `sweep --only processes --only sockets --json`
into `tests/ci/assert_sweep_available.py` after the suite, so the next push is the measurement; this
tag comes off when that step is green.]

## Still declared, not measured, and what would settle each

- Whether Claude Code's Bash tool on Windows produces POSIX-shell transcripts (Git Bash) or
  PowerShell ones — needs one real Windows session's transcript. The slug question that used to sit
  beside it is settled from the binary.
- Whether `%APPDATA%` and `%LOCALAPPDATA%` are set in the shell the harness spawns — the fallback to
  `~/AppData/...` exists, and only a session would show which branch runs.

## Recommended direction

1. ~~Push, read the first Windows run, fix what it names~~ — done, three rounds, green.
2. ~~Add a smoke step~~ — added; its first run is what the remaining `UNVERIFIED` waits on.
3. Leave the two transcript questions open until a Windows user appears; they cannot move from here,
   and saying so is the honest state.
