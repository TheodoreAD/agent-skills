---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/repo-tasks
source_session: 52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl
source_moment: 2026-09-07T11:15:05Z
---

## Context

This repo's `uv.lock` pins `invoke-stubs` at `c2a1a7c` — still 0.1.0 content, two stubbed modules.
0.2.0 (`13bcc9e`, on `main`) declares every module `invoke/__init__.py` re-exports from plus `util`
— 16 in all — and fixes three annotations invoke has wrong rather than missing.

`repo-tasks` took it 2026-09-07 with a green gate, which was the verification `invoke-stubs`' own
plan listed as owed before any consumer bumped. Filed from that session; nothing here was touched.

## Evidence

Session transcript `52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-07, from
"we just finished upgrading the invoke stubs".

The one cost that session paid, worth knowing before running the gate here: `collection.pyi`
declares `collections: Lexicon` and `util.pyi` declares `Lexicon(dict[str, Any])`, so
`Collection.collections["x"]` is now honestly `Any`. Under 0.1.0 it fell through to invoke's untyped
vendored `Lexicon` and was `Unknown | None`, which the tests tier silences while `reportAny` stays
an error — 37 errors in one file, fixed with `cast(Collection, ...)` at each site.

Measured for this repo before filing: **no file here indexes `.collections[`**, and 9 lines carry a
`pyright: ignore`, so both the cost and the win look small. The bump is currency rather than a fix.

## Open questions

[NEEDS CLARIFICATION: does anything here type-check invoke at all, or is the `invoke-stubs` entry
inherited from the `repo-tasks-quality` manifest and never exercised? If it is the latter, the bump
is a lock line and nothing else, and this plan can be retired the moment the gate is green.]

## Recommended direction

`inv deps.lock --package invoke-stubs`, `inv venv.sync`, `inv quality.precommit`, commit the lock
bump alone if nothing else moves.
