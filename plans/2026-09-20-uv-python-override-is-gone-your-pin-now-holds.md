---
status: idea
updated: 2026-09-20
source_repo: github.com-personal/power-user-linux-setup
source_session: 70f5fe13-9f1a-40f4-84ac-5ce4fd98a163.jsonl
source_moment: 2026-09-20T10:21:25Z
source_plan:
---

# The machine-wide UV_PYTHON override is gone, so this repo's pin now holds

**This reports a fact rather than proposing a design**, which is why `source_plan` is blank: there
is nobody to check with. The blocker named in
[`2026-09-18-python-floor-for-shipped-skill-scripts.md`](2026-09-18-python-floor-for-shipped-skill-scripts.md)
has been removed, and the work that plan describes can proceed.

## Context

Until 2026-09-19 this machine exported `UV_PYTHON="3.14"` into every shell, from
`power-user-linux-setup`'s `[packages.uv-env]`. uv reads that variable as an **explicit interpreter
request** — its own source documents it as "equivalent to the `--python` command-line argument" — so
it ranked above everything a project declared about itself. A `.python-version` in this repo was not
a weak defence against it; it was no defence at all, and neither was `requires-python`.

That is why every repo in the family developed above its own declared floor while looking fine: the
suite passed and the type checker agreed, because both were describing an interpreter neither had
been asked to check.

## Evidence

`power-user-linux-setup` commit `240721b`, pushed 2026-09-19: the export is deleted and
`inv python.pin-default` writes `~/.config/uv/.python-version` instead, from the same
`settings.uv_python_default`. Applied to this machine in the same session.

Measured on uv 0.11.19, before and after, on the machine itself:

| what is being resolved                                | exported `UV_PYTHON` | uv global pin |
| ----------------------------------------------------- | -------------------- | ------------- |
| PEP 723 script, `requires-python = ">=3.9"`           | 3.14.5               | 3.14.5        |
| PEP 723 script, `requires-python = "==3.11.*"`        | **3.14.5**           | 3.11.15       |
| project, `requires-python = ">=3.11,<3.12"`           | 3.14.5               | 3.11.15       |
| `uv tool install`, `requires-python = ">=3.11,<3.12"` | **3.14.5**           | 3.11.15       |

The 3.14 default survives wherever nothing declares otherwise and yields wherever something does.
The `uv tool install` row is the one that cost something in practice: it printed no warning at all,
so a tool was simply built against an interpreter it had excluded and failed later at import,
nowhere near the setting responsible.

The full reasoning is `power-user-linux-setup`'s
`plans/2026-09-18-replace-uv-python-with-a-uv-managed-default.md`.

[PITFALL: **a shell session started before 2026-09-19 still has the old value, and no dotfile edit
reaches it.** `~/.zshenv` lost the export immediately, and a session opened before that still
reported `UV_PYTHON=3.14` afterwards — it was inherited from the environment of the terminal the
session was launched in. So a check run from an old session measures the state before the change and
reads as "it did not work". Verify with `env -u UV_PYTHON uv run …`, or open a new terminal.]

## Open questions

[NEEDS CLARIFICATION: whether this repo wants a `.python-version` now that one would actually be
honoured. It was worth nothing while the variable outranked it, which is why most of the family
never added one. The file only becomes load-bearing in the state this change creates, and it is only
worth adding if something re-checks it later — `repo-tasks` has `inv venv.pin`/`venv.check` for
exactly that.]

## Recommended direction

1. **Recreate the venv at the declared floor** and confirm it took — `inv venv.recreate` where the
   repo-tasks task exists, else this repo's own equivalent. It passed `--python` explicitly all
   along, which is the one thing that outranked the variable, so this is the step that was always
   available and never stuck.
2. **Expect the gate to find things, and read that as the point rather than as breakage.** Nothing
   here has ever run at the real floor, so this is where the `typing.override`-class findings live —
   syntax and APIs newer than the declaration, invisible until something actually runs below them.
   `repo-tasks` recorded three such consumers in `plans/2026-08-25-consumer-transitions.md`, two of
   them in code that shipped in a wheel.
3. **Nothing about this repo's own declaration changes.** The tier rules are unaffected: libraries
   and anything another project installs stay at 3.11, and only applications start at 3.14.
