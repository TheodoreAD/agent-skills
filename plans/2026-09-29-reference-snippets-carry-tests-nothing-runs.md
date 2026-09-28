---
status: idea
updated: 2026-09-29
---

# Reference snippets carry tests nothing runs

## Context

22 files under `skills/*/references/snippets/` show a reader the recommended shape for a pattern,
and most end in `test_*` functions that prove it. Nothing runs them. `pytest.ini`'s `testpaths` is
`tests/unit`, no test imports a snippet, and the type checker leaves `skills/` out.

So a snippet can be wrong in the way that matters most, teaching a pattern that does not work, and
stay wrong indefinitely. Confirmed 2026-09-29: `python-conventions-taudelta`'s `async-fanout.py`
taught `async with semaphore, contextlib.suppress(...)`, which raises `TypeError` on every call,
since `suppress` is not an async context manager. Its own test would have failed on first run. It
was found by a type check of `skills/`, not by a test, and fixed in `d04fb64`.

The obstacle is dependencies: most snippets import the library they are about (sqlalchemy, duckdb,
huey, pydantic, httpx, tenacity, qdrant-client, fastmcp and more), none of which is in this repo's
dev group, and adding them all would make every contributor install a dozen databases' clients.

## Open questions

[NEEDS CLARIFICATION: where snippet tests run. One option is a separate, opt-in tier: a marker or a
second pytest invocation that installs each snippet's `pip install …` line into a throwaway
environment, the way the Windows job uses `uv run --no-project --with`. Counted 2026-09-29: 15 of
the 22 name a dependency that way, 14 on the docstring's first line and `full-text-search.py`
further down. Another option is only the other 7 in the default suite (`blob-storage`,
`in-process-state`, `relational-simple`, `async-fanout`, `exceptions`, `guard-clauses`, `testing`),
which name no dependency, though each still needs checking for an unnamed import, with the rest left
out and said so.]

[NEEDS CLARIFICATION: whether CI runs the dependency-carrying tier. It needs the network and a dozen
installs per run, which is the cost a scheduled or path-filtered job exists for.]

## Recommended direction

Start with the stdlib-only snippets in the default suite, since they cost nothing to run and the one
bug found was in one of them. Then decide the tier for the rest with its cost measured: time and
download size for one run that installs every snippet's line.
