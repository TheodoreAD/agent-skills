---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_moment: 2026-09-08
---

# `python-conventions`: two distributions in one repo import installed, never by path

**Routed here by a decision, not by default.** The rule below was drafted as a `~/AGENTS.md` block
by a `repo-tasks` session, filed to `power-user-linux-setup` because that repo owns `~/AGENTS.md`,
and its open question was whether it belonged there at all or only in `python-conventions`. Asked
and answered 2026-09-08: **`python-conventions` only.** So it comes here, and nothing goes into
`~/AGENTS.md`.

The original filing is in `power-user-linux-setup`'s history as
`plans/2026-09-07-packages-in-one-repo-import-installed-not-by-path.md` — that name is what
`plans.py archive --search` needs to read the full drafting context back, including the
`~/AGENTS.md` placement argument that was rejected.

## Context

Stated by the user 2026-09-07, verbatim: "distinct python packages with their own pyproject toml in
the same repo should not import by path manipulation without a very good reason, like a special
framework contract, which is very rare. all projects should import from the installed wheels or
editable installations".

## The rule, as drafted

Wording carried over unchanged from the filed plan, since only its destination was in question. It
was written as an `~/AGENTS.md` `###` block, so it will want re-cutting to `python-conventions`'
house shape — that skill states a default per question and says whether the entry overrides a
model's own instinct or merely confirms it, which this text does not yet do.

> **They import each other through the installed distribution — an editable install, a wheel — and
> never by putting a sibling's source directory on the path at runtime.** No `sys.path.insert`, no
> `site.addsitedir`, no `PYTHONPATH` assignment, and no `__path__` mutation, and no conftest doing
> it on the suite's behalf. A uv workspace already installs its members editable, so in the normal
> case there is nothing to arrange: declare the dependency and import it.
>
> The reason is that a path insert makes the import work while the dependency stays **undeclared**.
> It is absent from the lock, from `uv sync`, and from the built wheel — so the failure lands on
> whoever installs the artifact rather than on the machine that built it, which is the worst place
> for it and the furthest from the edit that caused it.
>
> The exception is a **framework doing it in its own code**, and it is rare enough to name the one
> that actually applies: pytest's default `prepend`/`append` import modes insert the rootdir into
> `sys.path` permanently (`_pytest/pathlib.py` says so in a comment beside the code). That is
> pytest's contract with itself. It is not licence for a conftest to add a sibling's `src/`.
>
> Detected rather than remembered, where the repo runs ruff: `TID251` with `"sys.path"` and
> `"site.addsitedir"` in `[lint.flake8-tidy-imports.banned-api]`. Measured against ruff 0.14 — it
> catches the attribute, the aliased module (`import sys as s`), and `from sys import path` at the
> import; `os.environ["PYTHONPATH"] = …` and `__path__` are not expressible there and stay a review
> matter.

## Evidence

The detector already ships. It is in `repo-tasks`' `ruff.toml` as of `1c91c2e`, so every consumer
that runs `configs.pull` inherits it. Coverage was probed with a file per spelling and real ruff
rather than assumed:

| spelling                            | flagged            |
| ----------------------------------- | ------------------ |
| `sys.path.insert(0, …)`             | yes                |
| `import sys as s; s.path.append(…)` | yes                |
| `from sys import path`              | yes, at the import |
| `site.addsitedir(…)`                | yes                |
| `os.environ["PYTHONPATH"] = …`      | no                 |
| `__path__.append(…)`                | no                 |

`repo-tasks` itself already satisfied the rule before any of this: no `sys.path` anywhere, and its
one workspace member is reached through `importlib.metadata.version("sample-service")` — an
installed distribution, not a path.

## Open questions

[NEEDS CLARIFICATION: whether `python-conventions` is the right skill or whether this belongs in
`python-refactor-audit`. It is a layout-and-packaging rule rather than a "what should this code look
like" rule, and the conventions skill's own description is about choosing between shapes. Filed
against `python-conventions` because that is what the routing decision named, but the skill's author
is better placed to judge the split than the routing was.]

[NEEDS CLARIFICATION: whether the entry should carry the `TID251` configuration at all, given the
detector ships from `repo-tasks` rather than from the skill. Naming it makes the rule enforceable
and tells a reader where the check comes from; restating a config another repo owns is how two
declarations drift apart. Possibly a pointer at `repo-tasks`' `ruff.toml` rather than the snippet.]

## Recommended direction

Re-cut the block to `python-conventions`' house shape — one default per question, with whether it
overrides or confirms the model's instinct — and add it there. Nothing is owed to `~/AGENTS.md`; the
placement question is closed. `power-user-linux-setup` needs no change either: it has one
`pyproject.toml`, so the rule is inert there and lands for the repos with several.
