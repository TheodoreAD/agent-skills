---
status: idea
updated: 2026-11-27
---

# Test suite runtime on Windows

## Context

On 2026-11-25, a session handing work over from the ataraxia repo reported this repo's test suite as
slow on the Windows machine. Nobody acted on it then. The measurements below were taken 2026-11-27
on that machine. Each is from a single run, all of them local:

- `uv run inv quality.precommit` takes 7.5–8.5 minutes, nearly all of it pytest: 1477 passed and 17
  skipped, in 453–506 s.
- `tests/unit/test_plan_store.py` and `tests/unit/test_compartments.py` together take 392 s for 415
  tests, so about 0.95 s per test. The store tests create real git repositories and run `git` in
  subprocesses for each test.
- Every commit runs the gate, and the global rules ask for small single-concern commits, so this
  cost is paid several times in one task. One retirement here paid it four times in a row.

## Open questions

[NEEDS CLARIFICATION: where the time goes. The candidates are process start-up on Windows (`git`
subprocesses per test), filesystem cost under `%TEMP%` (Defender scanning new files), and fixtures
rebuilding repositories that could be shared. Measure with `pytest --durations=30` before choosing a
fix.]

[NEEDS CLARIFICATION: whether CI's Windows leg shows the same per-test cost, and how this machine
compares with the Linux one for the same suite.]

## Recommended direction

Profile first (`--durations`, then one slow test under a profiler). The likely options, cheapest
first:

- build one git repository template per session and copy it per test, rather than `git init` and
  commit each time;
- `pytest-xdist` for the gate run;
- a Defender exclusion for the pytest temp root on this machine. That is machine configuration, so
  it belongs in win-configs rather than here.

Keep the default suite complete. Moving tests into a slower marked tier would hide exactly the store
behaviour the gate exists to check.
