---
status: landed
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

[DECISION: **the permission question was deleted rather than ported, 2026-09-04.** The user's
simplification — assume the Linux machine is single-user — removed the reason for the check, and
Windows removed any way to make it honest. So the branch, the "not enforced on this platform"
message and the three places it would have had to be said all go away with it.

What survives is the free half, and separating the two is the whole of this decision.
`mkdir(mode=0o700)` costs nothing, needs no platform test, and is silently ignored on Windows — it
is not "forcing" anything, so it stays. **Checking** the mode is what cries wolf, and it is gone:
`store_mode_problems` and the `doctor` warning are deleted, and both skill bodies now say the mode
is a free default rather than a protection to rely on.

The general form, now in `skill-authoring`: a defensive default that no-ops on the platforms that
lack it needs no branch; a _check_ for that default needs one, which is the argument for not writing
the check.]

[DECISION: **each script gets a module-level `WINDOWS = os.name == "nt"`, and the branch reads that
rather than `os.name` directly, 2026-09-04.** Not style — it is the only seam a test can use.
`pathlib` reads `os.name` to decide whether `Path()` returns a `PosixPath` or a `WindowsPath`, so
monkeypatching it to fake a platform makes the interpreter refuse to instantiate any path at all
(`UnsupportedOperation: cannot instantiate 'WindowsPath' on your system`) — the Windows arm is never
reached, and the failure looks like a broken test rather than an untestable design. Found by writing
`tests/unit/test_locations.py` first. One line per script, and the branch becomes testable on the
Linux machine that is the only one this corpus has.]

[DECISION: **a step whose external tool is absent reports `available: False`, never zeros,
2026-09-04.** `harvest.py`'s sockets step already did; its processes step did not, and an empty `ps`
table there produced "0 surviving children" — a clean bill of health from a step that never ran, on
exactly the sweep whose purpose is catching what a session left behind. `ps` cannot omit the process
reading it, so an empty table is unambiguous. This is the same defect as the permission warning seen
from the other side: one fires where it cannot be true, the other stays silent where it cannot
know.]

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

## The three open questions, all answered 2026-09-04

[DECISION: **no Windows leg in CI, and the honest position is "declared, not measured".** The case
for one is real but thin: a runner would measure `tarfile` extraction, the location defaults against
a true `%USERPROFILE%`, and the `git` subprocess tests under `autocrlf`. That is the whole list.
Against it, three things. **It settles neither of the other two questions** — both need a real
Claude Code session on Windows, and a GitHub runner generates no transcript, so the coupling this
plan originally asserted between them does not exist. **The fixture work comes first and is the real
cost**: `tests/unit/test_harvest.py:584` and `tests/unit/test_plan_store.py:76` fake the home
directory with `monkeypatch.setenv("HOME", …)`, and Windows `expanduser` never reads `HOME` — read
from `ntpath` source 2026-09-04, it takes `USERPROFILE`, else `HOMEDRIVE` + `HOMEPATH`. So the first
red would be the fixture rather than a defect, and until it is fixed those tests write into the real
profile. **And the platform has no user here.**

So the corpus does what it did with the permission check: says what it assumes instead of pretending
to have verified it. Reopen when a real Windows user appears — which is the same event the two
questions below wait on, so all three move together or not at all.]

**Whether `session-bash-audit` is Unix-only or Git-Bash-shaped: declared rather than decided.** It
cannot be settled without one real transcript, so the skill's body now says so — a Git Bash or WSL
session produces POSIX commands and the audit applies unchanged, a PowerShell one produces commands
no pattern matches, and a suspiciously clean Windows run should be read as the second rather than
the first.

**Whether the project-slug normalisation holds: same answer, and it needed the louder warning.**
`cd-own-repo`, `git-C-own-repo` and `--project` all compare against a slug made by replacing `/` and
`.` with `-`, so if the harness writes Windows paths differently they match nothing and report zero
— which reads as perfect adherence rather than as a broken comparison. That is now stated in the
skill: a zero on those rows from a Windows transcript is unverified, not good news.

## Recommended direction

Smallest first, and the first one is the only urgent one:

1. ~~Make the permission check platform-aware~~ — **done 2026-09-04 by deleting it**, per the
   decision above. This was the urgent item and it turned out to be a removal.
2. ~~Give `materialize_ref` the stdlib `tarfile`~~ — **done 2026-09-04.** `git archive` still
   produces the stream; `tarfile` reads it from memory with the `data` filter (guarded by `hasattr`,
   since the argument only exists from 3.11.4 and these scripts run under a bare `python3`). One
   external-binary assumption gone on every platform rather than branched on one.
3. ~~Add the Windows arm to the location helpers~~ — **done 2026-09-04**, in `audit.py`'s
   `state_dir` and `plans.py`'s `config_path`, `$XDG_*` first in both.
   `tests/unit/test_locations.py` pins the whole order for both copies, which is what the
   duplication rule needs and did not have.
4. ~~Declare scope~~ — **done 2026-09-04.** A Platform paragraph in the README (which is where it
   reads better than a fourth Scope value), the POSIX-shell premise in `session-bash-audit`'s body,
   the `ps`/`ss` steps in `session-harvest`'s sweep section, and the Windows column in
   `skill-authoring`'s destination table.
5. ~~Then decide the CI question~~ — **decided 2026-09-04: no leg.** See the decision above; the
   reasoning that it would convert this plan from reasoning into measurement turned out to be true
   only of a three-item slice, and false of the two questions it was supposed to unblock.

## Migrated to

- `skills/skill-authoring/SKILL.md`, "Where a skill may put things" — the Windows column on the
  destination table, the "variable everywhere, default per-platform" rule with its roaming axis, and
  the `0700` bullet carrying the set-but-never-check reasoning. This is the corpus-level home for
  every rule here that generalises.
- `README.md`, the Platform paragraph — that the corpus is POSIX-written, never executed on Windows,
  Linux-only in CI by decision, and which two skills assume more than a path.
- `skills/session-bash-audit/SKILL.md` — the POSIX-shell premise, and the warning that a zero on
  `cd-own-repo` / `git-C-own-repo` from a Windows transcript is unverified rather than good news.
- `skills/session-harvest/SKILL.md` step 5 — that `ps` and `ss` are the two POSIX-assuming steps and
  what an unavailable one means.
- `tests/unit/test_locations.py` — the `WINDOWS`-constant seam and why `os.name` cannot be patched,
  which is a design constraint rather than a note, so it lives in the file it constrains.
- Code: `fitness.py` `materialize_ref` (stdlib `tarfile`), `audit.py` `state_dir` and `plans.py`
  `config_path` (the Windows arms), `harvest.py` `processes` (`available: False`).

Not migrated, deliberately: the "what is actually assumed" survey table, which described the state
before this work and is now wrong in four of its six rows; and the `platformdirs` rejection, which
the `skill-authoring` rule states as a conclusion without needing the argument rehearsed.
