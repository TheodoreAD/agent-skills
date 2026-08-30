---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Typer is the CLI default, and no skill says so

## Context

Stated by the user on 2026-08-30: **Typer is the default for a CLI whenever a project is not
constrained to the standard library.** It came up because a plan in another repo was weighing a
Typer command against a `python -m` entrypoint as though the framework itself were an open question.
It is not, and nothing written down said so.

Checked the same day: `python-conventions` names `click` twice and both times as _prior art for
exception hierarchies_, never as a recommendation. `db-defaults` covers storage only.
`invoke-task-conventions` covers `inv` tasks, which is a different surface — a task runner for
repo-local work, not the program a user installs. So an agent picking a CLI framework today picks by
habit, and the habit is `argparse`.

That gap is the same shape as the doubles one filed alongside it
([`2026-08-30-no-doubles-for-controllable-backends.md`](2026-08-30-no-doubles-for-controllable-backends.md)):
a default the user holds firmly, which the skills happen not to state, so it gets re-litigated per
project.

## Open questions

[NEEDS CLARIFICATION: Where the standard-library carve-out actually bites, so the rule can name it
rather than gesture at it. The obvious cases are a script that must run on a bare interpreter with
no install step, and code shipped somewhere dependencies cannot follow — a Pyodide payload, a
bootstrap script that runs before any environment exists. Worth listing two or three concretely, or
the exception swallows the rule.]

[NEEDS CLARIFICATION: Whether the rule should say anything about Typer's own relationship to Click.
Typer is built on Click, so "use Typer" and "Click is fine" are not opposites — but a project that
reaches for raw Click when Typer is available is choosing more boilerplate for the same result, and
the rule is worth nothing if it does not say which one an agent should write.]

## Recommended direction

Add it to `python-conventions` as a topic in its own right, in the same shape every other topic in
that skill takes: the default, the carve-out, and a line on whether it overrides a model's own
instinct or merely confirms it. This one **overrides** — left alone, a model writes `argparse`,
because that is what the standard library offers and what most training data shows.

What the entry should carry:

- **Typer for anything with subcommands, options, or a `[project.scripts]` entry.** Annotated types
  are the declaration, which matches the same skill's existing rule that metadata rides in the
  annotation rather than on the right-hand side of a default.
- **`argparse` only under a genuine standard-library-only constraint**, named rather than assumed.
- **Not a rule about task runners.** `inv` stays what it is for repo-local work; the two do not
  compete, and `invoke-task-conventions` should say so in a line rather than leaving a reader to
  wonder which one a new command belongs in.

Not `~/AGENTS.md`. It is a Python library default, which is exactly what `python-conventions` exists
to hold, and the global file is already long enough that adding per-language library picks to it
would start it down that road.
