# db-defaults-taudelta

One default storage pick per need for local Python, testable in plain pytest.

Ask a coding agent to "add a cache" or "store these documents" in two different sessions and you can
get two different libraries. Neither choice is wrong, exactly. But a project collects them, each
with its own testing story, and some of them quietly need Docker or a cloud account before a single
test can run.

db-defaults-taudelta gives the agent one settled answer per storage need, so the pick stays the same
from session to session and project to project. It is one author's rulings, made for personal,
local-first Python projects. Where you would rule differently, fork it and change the table; the
point is that some table exists.

It works with any agent that reads [Agent Skills](https://agentskills.io).

## What you get

- A default for each of fourteen needs: in-process state, cache, simple and complex relational
  storage, analytics, documents, full-text search, vector search, job queues, scheduled tasks,
  pub/sub, graph data, blobs and time series.
- The same four criteria behind every pick. A permissive licence (MIT, Apache-2.0 or BSD), a project
  that is popular and actively maintained, a test suite that runs it for real inside plain `pytest`
  with no Docker or cloud account, and an API an agent can use correctly without much ceremony.
- An "escalate to" line for each need, naming what to move to once you outgrow the local default:
  Redis for a shared cache, Postgres for relational data, Qdrant Cloud for vectors.
- A starter file per need in `references/snippets/`: the install command and a working `test_*`
  function showing the pytest-local pattern.
- The traps found while choosing, written next to the pick they affect.

It is not a production recommendation. Security was deliberately left out of the criteria, and the
skill says so; the "escalate to" line is the answer for anything multi-tenant or internet-facing.

## What it looks like

Ask "this needs a job queue" and the agent reaches for the table rather than an evaluation. The
entry it finds, lightly condensed:

```
Background job / message queue
  Default:     huey (MIT)
  Why:         SqliteHuey(..., immediate=True) runs tasks synchronously in-process,
               so a plain pytest test just calls the function
  Escalate to: Celery, RQ or Dramatiq, once you need a real broker and several workers
```

The skill also tells the agent not to mock these stores in tests. The reason for choosing ones the
suite can start and stop is that the tests then run the real thing.

## What the research turned up

The complex-relational pick is SQLAlchemy with Alembic, tested against SQLite and escalated to
Postgres. Measured against SQLAlchemy 2.0.52, the SQLite side silently corrupts a `Decimal` and
drops a datetime's timezone, and neither problem exists on the Postgres you escalate to. A wide
decimal such as `1234567890123456789.000000001` comes back as `1234567890123456768.0000000000`, with
no warning. A ten-digit test value survives intact, which is how a project concludes the column type
is fine and ships. The skill names the fix: a column type that stores the exact string, and SQLite's
strict mode so the test database stops being laxer than the real one.

The graph pick changed with the ecosystem. Kuzu was archived in October 2025, and the community fork
`ladybug` continued the same engine three days later. The skill picks the fork and marks it as young
rather than as settled as SQLite.

## Why not let the agent choose each time

Choosing well takes research: licences, commit activity, release history, whether the thing can run
inside a test. An agent that re-does that research every session either spends the time or skips it
and picks what it remembers. This skill did the research once, in dated passes that are written up
with their GitHub and PyPI numbers, and asks the agent to reuse the answer. Nothing stops a
deviation. The aim is that a different pick is a decision someone made, not drift.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill db-defaults-taudelta
```

Then work normally. "Cache these API responses", "add full-text search over the notes" and "I need
somewhere to store embeddings" all land on the table. Ask explicitly for an evaluation if you want
one, and the skill steps aside.

## What it touches

Nothing. It ships no script, so it reads and writes nothing itself; it only guides the agent's
choice. The snippets are reference files the agent may copy from.

## Read more

- [`SKILL.md`](SKILL.md): the full table your agent follows.
- [`references/rationale.md`](references/rationale.md): the GitHub and PyPI evidence, and the
  options considered and rejected for each need.
- [`references/snippets/`](references/snippets/): one starter file per need.
