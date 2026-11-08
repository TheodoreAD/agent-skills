# python-conventions-taudelta

One settled answer per Python design question, so sessions stop drifting.

Ask a coding agent to add a record type to a Python project and it will pick one of six plausible
options: a dataclass, a Pydantic model, a `NamedTuple`, a `TypedDict`, `attrs` or `msgspec`. Ask
again next week, in a fresh session, and it may pick a different one. None of the choices is wrong
on its own. Together they leave a codebase with four idioms for the same job, and the next agent
copies whichever one it happened to read last.

The same drift shows up in dates and timezones, settings, error handling, CLIs, async code and HTTP
retries. This skill gives the agent one default for each, with the conditions under which to pick
something else, so the choice is made once instead of every session.

These are one author's rulings, not a neutral survey. Each answer is the one this author settled on,
with the reasoning written down. Where you would rule differently, fork the skill and change the
answer. The `-taudelta` suffix on the name marks it as that kind of skill.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others.

## What you get

- A default per topic: data modeling, dates and timezones, settings and secrets, guard clauses and
  exceptions, modularity and duplication, module-level singletons, immutability, CLIs, type hygiene,
  `src/` package layout, async and concurrency, and HTTP clients with retry.
- The escape routes for each default, named in advance. For example, the default record type moves
  to `msgspec` only once Pydantic's overhead is a measured bottleneck.
- A note on every topic saying whether it overrides what a model would do on its own or just
  confirms it. Early returns and EAFP are confirmations you can skim. The module-level singleton and
  `frozen=True` on data that crosses a boundary are overrides the agent would not reach for
  unprompted.
- Traps found by measuring, stated where they bite. Pydantic's `model_copy(update=...)` skips
  validation that `dataclasses.replace` performs. Two aware datetimes in the same non-UTC zone
  subtract on their wall clock and ignore a DST change between them.
- A folder of small, ruff-clean Python files for the main patterns, to copy rather than adapt.

## What it looks like

A two-field value type looks like a textbook `NamedTuple`:

```python
class Quantity(NamedTuple):
    amount: float
    unit: str


Quantity(5, "ml") < Quantity(300, "mg")  # True: compared as a tuple, across units
```

The skill's data-modeling section explains why this is a bug rather than a convenience. A
`NamedTuple` inherits tuple ordering, so a comparison that should be refused succeeds silently. Its
default for internal data is a frozen dataclass, where the same comparison raises a `TypeError`
unless you define an ordering yourself. A `NamedTuple` is still the right upgrade from a bare tuple,
because the positional surface already exists there. It is a downgrade from a frozen dataclass,
because it adds indexing, unpacking and equality with plain tuples that nobody designed.

## Why not let the agent decide

Left alone, the agent does decide, and it decides differently each time depending on what it last
saw. A consistent default is worth more than the best answer picked fresh per session, because the
agent learns the codebase's style by copying it.

A linter or type checker doesn't settle these questions either. They check how code is spelled, not
which of six record types to use or where a timestamp should become UTC. This skill leaves tool
configuration to the repo and covers only the design choices made while writing.

## Built from what went wrong

The timezone rule came from a real project, measured on 2026-08-27. A "24 hour" window spanned 23
real hours across a spring-forward change, and a six-hour minimum interval between two doses elapsed
an hour early. Neither failure was visible by reading the code, which is why the skill asks for
tests with hand-worked answers at real DST transitions.

The `NamedTuple` rule was applied on 2026-09-01 to a 3,200-line standard-library-only script: 16
anonymous tuple returns became `NamedTuple`s, and its 6 frozen dataclasses were deliberately left
alone.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill python-conventions-taudelta
```

It picks up on its own when the agent writes or reviews Python. You can also ask directly:
"dataclass or Pydantic here?", "how should this handle timezones?", "this module has grown a lot of
global state, how far should I break it up?".

Tests are covered by the separate
[python-testing-conventions-taudelta](../python-testing-conventions-taudelta/) skill, and the Python
inside an MCP server by [mcp-python-conventions-taudelta](../mcp-python-conventions-taudelta/).

## What it touches

Nothing. It has no scripts and runs nothing. It only guides how your agent writes code.

## Read more

- [`SKILL.md`](SKILL.md): every default, its escape routes, and whether it overrides a model's own
  habit.
- [`references/rationale.md`](references/rationale.md): the sources consulted and the options
  rejected, topic by topic.
- [`references/snippets/`](references/snippets/): one copy-pasteable file per pattern.
