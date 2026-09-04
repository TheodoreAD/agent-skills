---
status: idea
updated: 2026-09-04
---

# The corpus assumes a POSIX machine, and one check would cry wolf forever on Windows

## Context

Asked by the user 2026-09-04: make sure the skills work on Windows — not forcing file permissions
and similar things when they detect it — and work out where that functionality is best kept.

**This is not a new principle; it is the session's existing one meeting a new axis.** The rule
settled 2026-09-02 is that a skill's output must be actionable by whoever ran it, and a check that
fires on correct behaviour is the same defect seen from the other side — it gets trained away, and
is then useless on the day it is right. A POSIX-mode warning on Windows is exactly that: unfixable
by the reader, on every run, forever. The work-device remote warning
(`2026-09-03-work-device-store-is-not-sensitive.md`) is the same shape, and so was the install-hub
portability report.

So the question is not "add a Windows branch". It is **which assumptions are location questions,
which are capability questions, and which are scope questions** — because those three have different
right answers and only the first is a branch.

## What is actually assumed, read from the scripts 2026-09-04

| site                                              | on Windows                                                  | severity              |
| ------------------------------------------------- | ----------------------------------------------------------- | --------------------- |
| `plans.py` `store_mode_problems` — `st_mode & 7`  | **warns on every run, with an unrunnable `chmod` remedy**   | **cries wolf**        |
| `plans.py` `mkdir(mode=STORE_MODE)`               | silently ignored; the store is not protected                | silent non-protection |
| `audit.py` `state_dir()` — `$XDG_STATE_HOME`      | falls back to `~/.local/state`, which is not the convention | wrong location        |
| `plans.py` config — `$XDG_CONFIG_HOME`            | same, for `~/.config`                                       | wrong location        |
| `fitness.py` `materialize_ref` — `subprocess tar` | depends on `tar.exe` being present                          | avoidable             |
| `session-bash-audit` as a whole                   | audits Bash habits; premise is a POSIX shell                | **scope**             |

[PITFALL: **the permission check is the dangerous one, and it fails in the direction that looks
fine.** CPython synthesises `st_mode` on Windows from the file attributes rather than reading a
POSIX mode — a directory comes back around `0o777`, so `mode & 0o007` is non-zero and the warning
fires on a machine where the concept does not exist. The user is then told to run `chmod 700`, which
is not a command they have. Meanwhile `mkdir(mode=0o700)` on the same machine is accepted and
ignored, so the store genuinely is unprotected while the skill's own body says it is created `0700`.
**Reasoned from CPython's documented behaviour, not measured** — nothing here has ever run on
Windows, which is itself the finding below.]

## Where each kind of assumption belongs

**1. Location is a branch, and it lives in the script that needs it — duplicated.** Settled
2026-09-03: skills install individually, so one cannot import another; shared _code_ is copied, not
depended on. `audit.py` already carries a ten-line `state_dir()`; the Windows arm is three more
lines (`%LOCALAPPDATA%` for state and cache, `%APPDATA%` for config, honouring the `$XDG_*`
variables first because a user who sets one on any platform means it). Copying that into each script
that needs it stays "the cheapest copying available"; a full platform matrix would not, which is the
line between this and taking a dependency.

[DECISION: **do not take `platformdirs`.** It is the right library and its semantics are what to
copy — that was already settled for the XDG side on 2026-09-03 — but these scripts are stdlib-only
so they run under a bare `python3` with nothing installed, and a `--global` skill install runs no
install step at all. PEP 723 plus `uv run` is the documented escape hatch and is refused here for a
smaller reason: it changes the documented call shape from `python3 <path>` to something requiring
`uv`, in every skill body and every instruction that cites one.]

**2. Permission is a capability question, and the answer is to say it is unavailable — not to
emulate it.** There is no stdlib way to set an ACL, so the honest behaviour is: skip the
enforcement, skip the warning, and **report that the protection is not in force**. That last part is
the one that must not be dropped. It belongs in three places, for three different readers:

- in `store_mode_problems`, as an early return that produces a _statement_ rather than silence;
- in `doctor`'s output, so a Windows user sees "not enforced on this platform" where a Linux user
  sees a mode;
- in **`plan-docs`'s own body**, because the sensitive tier's design rests on that protection and a
  reader whose machine cannot provide it is entitled to know before they put client work there.

**3. Scope is a declaration, and it belongs in the README's Scope column.** `session-bash-audit`
audits Bash-tool habits against POSIX-shell idioms; that is not a portability defect to fix but a
premise to state. The corpus already has the column and the rule — "where a skill genuinely needs an
environment assumption, it must say so rather than failing mysteriously" — and an operating system
is such an assumption.

**4. The corpus-level rule goes in `skill-authoring`,** beside the destination table added
2026-09-04, which is Unix-only as written and needs a Windows column plus one sentence: a POSIX mode
is accepted and ignored there, so a skill that relies on one for confidentiality must say so rather
than assume it.

[DECISION: **test the capability where it is observable, the platform only where it is not.**
`chmod` has no observable success on Windows, so `os.name == "nt"` is the honest test there.
Anything with a detectable outcome — a symlink, a long path — is better tried than predicted,
because the platform name is a proxy and the capability is the thing.]

## Open questions

[NEEDS CLARIFICATION: **whether CI should run on Windows at all.** Everything above is reasoned from
documented behaviour, because this repo has never executed a line on Windows —
`.github/workflows/ci.yml` is `runs-on: ubuntu-latest` and nothing else. A second matrix leg would
turn every claim here into a measurement, which is this corpus's standing preference, and would have
caught the permission warning the day it was written. Against: it doubles CI time for a platform the
author does not use, and the suite would need the `HOME`-fixture work to pass there.]

[NEEDS CLARIFICATION: **whether `session-bash-audit` is Unix-only or Git-Bash-shaped.** A Windows
user running Claude Code through Git Bash or WSL generates transcripts whose commands are POSIX, so
the audit may be perfectly meaningful — while the same user in PowerShell generates commands none of
its patterns match, and the report would read as "no problems found" rather than "wrong tool". That
distinction decides whether the answer is a Scope note or an `unavailable` message, and it cannot be
settled without one real transcript.]

[NEEDS CLARIFICATION: **whether the project-slug normalisation holds.** `audit.py` maps a transcript
directory back to a repo by replacing `/` and `.` with `-`. What Claude Code writes for a Windows
path is unknown here; if it slugs backslashes differently, `--project` and the own-repo `cd`
detection both silently match nothing — a zero that reads as good news.]

## Recommended direction

Smallest first, and the first one is the only urgent one:

1. **Make the permission check platform-aware and honest** — no warning where the concept does not
   exist, a stated "not enforced" instead, in the script, in `doctor` and in the skill body.
2. **Give `materialize_ref` the stdlib `tarfile`** instead of shelling out to `tar`, which removes
   an external-binary assumption on every platform rather than branching on one.
3. **Add the Windows arm to the location helpers**, honouring `$XDG_*` first.
4. **Declare scope** — README column for anything shell-shaped, and the Windows row in
   `skill-authoring`'s destination table.
5. Then decide the CI question, which is what converts the rest of this from reasoning into
   measurement.
