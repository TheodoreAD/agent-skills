---
status: idea
updated: 2026-09-18
source_repo: github.com-personal/repo-tasks
source_session: 14237e4b-3a66-4207-8a3a-882552c86680.jsonl
source_moment: 2026-09-18T09:40:00Z
source_plan: plans/2026-08-29-python-floor-in-the-shipped-configs.md
---

# The shipped scripts have no declared floor, and two of them already break below 3.11

## Context

The family's Python version tiers were settled 2026-09-18 and are written up as
`scaffoldapy/plans/2026-09-18-python-version-tier-rules.md` (in the store until that repo absorbs
it). **This repo is its own tier there**, and the rule naming it is:

> a repo whose shipped artifacts run on an interpreter it does not choose develops at those
> artifacts' floor.

That is this repo exactly. Its product is `skills/*/scripts/*.py`, run by a consumer's ambient
`python3` with no resolver anywhere in the path. The user's constraint, 2026-09-18:

> we need users to be able to use our skills without uv or any special system setup. we expect them
> to have at least python 3.11, that is the basic requirement, otherwise the toml configs fall
> apart, and 3.11 is pretty old as it is.

So the floor is **3.11**, it is a promise to strangers, and nothing in this repo currently states or
checks it.

## Evidence

Measured 2026-09-18 against the twelve scripts under `skills/*/scripts/`, by compiling each under
uv-managed 3.9 through 3.13 and then running two of them for real:

| script                               | compiles under | runtime floor        |
| ------------------------------------ | -------------- | -------------------- |
| `plan-docs/scripts/plans.py`         | 3.9            | **3.11** — `tomllib` |
| `session-harvest/scripts/harvest.py` | 3.9            | **3.11** — `tomllib` |
| the other ten                        | 3.9            | 3.9                  |

Both `tomllib` imports are top-level and unguarded. Run on 3.10:

```
ModuleNotFoundError: No module named 'tomllib'
```

Run, not inferred — `plans.py --help` under a stripped environment on 3.9, 3.10 and 3.11, failing on
the first two and succeeding on the third.

[PITFALL: **the traceback does not mention 3.11**, which is the whole cost. A consumer on Ubuntu
22.04 (`python3` is 3.10 there) gets a missing-module error naming a stdlib module, mid-task, with
nothing pointing at the interpreter. The repo's own README could say 3.11 in bold and that reader
would still be reading a traceback about `tomllib`.]

[PITFALL: **`python3` is not one interpreter and the variance is silent.** It resolves to the active
venv's interpreter ahead of the distro's, so a skill invoked from a session in one repo and the same
skill invoked from another run on different interpreters. Measured on one machine on one day:
3.11.15, 3.14.5 and 3.12.3 depending only on which directory the session was in. This repo cannot
control that and should not try; it can only make the floor low enough and say so.]

## Open questions

- **Does the version guard go in every script, or in one imported module?** Every script, almost
  certainly — a shared module is itself an import that has to succeed first, and these scripts are
  deliberately standalone so a consumer can run one by path. The cost is a repeated four lines,
  which is the kind of duplication the testing conventions say to accept when the alternative is a
  dependency.
- **Does anything stop a script acquiring a third-party import?** Nothing today. The stdlib-only
  rule is a real constraint on this repo and is the sort of thing a test can assert cheaply by
  walking each script's imports against `sys.stdlib_module_names`.
- **Is 3.9 worth keeping for the ten scripts that have it?** Probably not — one floor is easier to
  state and check than two, and the rule is 3.11 regardless. But it is worth knowing that only
  `tomllib` costs those ten their lower floor, in case the requirement is ever revisited.

## Recommended direction

1. **Recreate `.venv` on 3.11** and pin it: `requires-python = ">=3.11"` is already declared, so
   this is `inv venv.pin` and `inv venv.recreate`. The venv is 3.14.5 today. This is the step that
   makes the ordinary test run the floor check, and it is why this repo is not in the 3.14 tooling
   tier with `scaffoldapy`.
2. **Add the version guard** to every script, above the first 3.11-only import, naming the
   requirement in a sentence rather than an exception class.
3. **Assert the two rules in the suite** — every script imports cleanly on the floor, and imports
   nothing outside the standard library. Both are walks over `skills/*/scripts/*.py`, and both are
   the kind of check that only means anything while the dev venv is the floor.
4. **State the requirement in the repo's README and in each `SKILL.md`** that documents a script
   invocation, since the audience for it is someone who has not cloned anything.

[PITFALL: **none of this binds locally until `UV_PYTHON` is dealt with.** That variable is exported
machine-wide and outranks `.python-version`, so a bare `uv run` or `uv sync` in this tree rebuilds
the venv at 3.14 and step 1 silently comes undone. Filed for `power-user-linux-setup` as
`2026-09-13-uv-python-defeats-every-library-floor.md`; the replacement is `uv python pin --global`.
Do step 1 after that lands, or expect to redo it.]

## Attachments

- `skill-floor-probe.sh` — committed, 1 KB, attached 2026-09-18
