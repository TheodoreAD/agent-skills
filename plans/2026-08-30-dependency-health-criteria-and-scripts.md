---
status: landed
updated: 2026-09-02
---

# Dependency health: the criteria, and a script that stops re-deriving them

## Context

Choosing a library is a recurring task and it is currently done from scratch every time. Two
problems, and the second is the expensive one.

**The criteria are re-invented per session.** `~/AGENTS.md` says to judge a package from its own
PyPI file list rather than a search summary, and to go deeper than a single-pass summary for a real
selection decision. It does not say _what to look at_, so each session picks its own axes and the
comparisons are not commensurable. Stated 2026-08-30 while choosing a Telegram library: popularity
is a weak signal past a threshold and should not disqualify the less popular project; what matters
is whether **each candidate independently clears a maintenance bar**, with the head-to-head second.

**The lookups are hand-rolled every time.** Measured over this machine's own transcripts on
2026-08-30, across all sessions ever recorded:

| pattern                                | invocations | distinct sessions |
| -------------------------------------- | ----------: | ----------------: |
| `pypi.org/pypi/<name>/json` fetches    |          61 |                12 |
| `gh api repos/...`                     |          96 |                19 |
| `gh api` for stars/pushed/archived etc |          34 |                 7 |

Every one a fresh `curl … \| python3 -c "…"` with a slightly different field selection. The
repo-stats shape is nearly identical each time and drifts anyway — `forks_count` present in some,
absent in others; `default_branch` sometimes; `license.spdx_id` usually. Answers that should be
comparable across sessions are not.

[DECISION: This belongs in the `research-library` skill rather than a new one. That skill already
owns "before fetching anything from the web, check the library" and "grep the real source, don't
trust docs/README prose" — judging a candidate dependency is the same activity one step earlier, and
a second skill would compete with it for the same trigger.]

## Recommended direction

### 1. The criteria, as an absolute bar

Each candidate is judged on its own first. Only then is there a comparison, and popularity is
explicitly not a tiebreaker.

**Maintenance** — is someone still looking after this?

- release cadence: releases in the last year, median gap between recent releases, days since the
  last
- age and total release count, and whether any release has been yanked
- last push versus last release, which separates "actively developed, slow to release" from
  "stalled"
- **human** contributor count and bus factor over the last year
- median time to close an issue, from a recent sample
- archived flag, licence, open issue count relative to project size

**Typing** — how much work does the consumer inherit?

- ships `py.typed`
- the project's own type-checker configuration and its strictness, which predicts what leaks
- whether type checking runs as part of its test suite
- measured: run the consumer's own checker, in the consumer's own mode, over a small real usage
  sample — nothing else tells you what the gate will actually say

**Battle-tested** — is there a suite, and does it hold anything?

- test-to-source line ratio, computed against **hand-written** source
- coverage policy: is a target actually enforced in CI, or only reported
- CI workflow count and what they cover (tests, security audit, release, docs)

**Fit** — the axes that are about this consumer rather than the project:

- runtime dependency count and what they are
- version ceilings on anything the consumer already depends on, and whether the ceiling binds the
  distributed artifact or only the development lockfile
- licence compatibility with how the consumer ships
- whether the thing can be exercised offline, and what scaffolding that costs

### 2. The traps, all of them confirmed by hitting them

[PITFALL: **A bot dominates the bus factor.** `renovate[bot]` was 70% of one project's commits over
a year, which read as a catastrophic bus factor and is actually just dependency bumps. Excluding
`[bot]`, `dependabot`, `renovate` and `pre-commit-ci` reversed the finding — that project turned out
to have the _better_ human distribution of the two. Any contributor metric has to filter bots.]

[PITFALL: **GitHub's licence field reports one licence for a dual-licensed project.** The API said
`GPL-3.0` for a project shipping `LICENSE`, `LICENSE.lesser` and a `LICENSE.dual` whose first line
says either may be chosen. Taking the API at face value would have wrongly disqualified it on
copyleft grounds. Check the licence files in the clone, not the field.]

[PITFALL: **A raw test-to-source ratio is meaningless where a project has a large mechanical binding
layer.** One candidate looked like 0.28 against a peer's 0.81 — until 71% of its source turned out
to be one-class-per-API-object modules. Against hand-written code the same project was 1.07, i.e.
better than the peer rather than a third as good. Segment the source before dividing.]

[PITFALL: **A `pyrightconfig.json` `include` is ignored when the checker is pointed at a shared
scratch directory**, so a per-candidate measurement silently becomes the sum of every file sitting
beside it. Caught 2026-08-30 when a 25-line file reported 208 warnings. Put each sample in its own
directory with its own config, and assert `filesAnalyzed` is what you expected before reading any
count.]

[PITFALL: **A search summary will assert implementation details that the source does not support.**
One candidate is widely described, including by its own marketing, as having autogenerated API
bindings. There is no generator in the repository and no generated-file header. It may well be
generated by a tool kept elsewhere, but the claim could not be confirmed from the source, and a
comparison resting on it would have been resting on nothing. This is the `research-library` skill's
existing "grep the real source" rule earning itself again.]

### 2b. Methodology, as opposed to metrics

The traps above are things that produce a wrong number. These are things that produce a wrong
_judgement_ from correct numbers, and each one nearly did.

[DECISION: **A version cap is not a cost until its historical lag says it is.** A dependency that
pins `foo<2.14` looks like it will hold the consumer back, and the way to find out is archaeology
rather than argument: trace the constraint through that project's own git history and line each
widening up against the capped project's release dates.

Measured 2026-08-30 on a candidate capping pydantic:

| capped release | published  | cap widened | lag     |
| -------------- | ---------- | ----------- | ------- |
| 2.7.0          | 2024-04-11 | 2024-04-22  | 11 days |
| 2.8.0          | 2024-07-01 | 2024-07-06  | 5 days  |
| 2.9.0          | 2024-09-05 | 2024-09-09  | 4 days  |
| 2.10.0         | 2024-11-20 | 2024-11-23  | 3 days  |
| 2.11.0         | 2025-03-27 | 2025-03-29  | 2 days  |
| 2.12.0         | 2025-10-07 | 2025-10-08  | 1 day   |
| 2.13.0         | 2026-04-13 | 2026-05-03  | 20 days |

Median five days. That is a rolling ceiling maintained deliberately, not a wall — and the one time
the cap was held on purpose, the commit says why (an upstream release breaking a Python version they
still supported), which is a project doing its job rather than neglecting it. Without this table the
cap reads as a disqualifier; with it, it reads as a maintenance signal in the candidate's favour.]

[DECISION: **Say where a cap binds.** A constraint reached only through an optional extra or a dev
group binds the development lockfile; it never reaches the distributed artifact, whose own
`[project.dependencies]` stay as written. Those are different costs and conflating them overstates
the second one. Establish which it is before weighing it at all.]

[DECISION: **Measure whether a typing gap is _coverable_, not just that it exists.** A candidate
produced nine `reportUnknown*` diagnostics under the consumer's own checker because its central
class is generic over six parameters and is normally written bare. Writing the six arguments once,
as a `TypeAlias`, took the same sample to zero errors and zero warnings. The gap was real and the
cost was four lines — and it had already been written into a recommendation as though it were
structural. Always try the fix and re-measure before scoring the gap.]

[PITFALL: **Prove offline-testability by removing the network, not by reading about it.** One
candidate's documentation describes dispatching updates without network access; its application
object nonetheless calls the API during startup, so a fake token raises before any handler runs. The
decisive test was replacing `socket.socket` with a function that raises and dispatching anyway — one
candidate passed untouched, the other needed a request-layer subclass. Neither library's docs said
this.]

[PITFALL: **Install size and dependency count can disagree, and neither alone is the footprint.**
Measured in two isolated virtualenvs: 14 MB across 12 packages versus 15 MB across 18. A conclusion
drawn from size alone said "equivalent"; from count alone, "half again as much". Report both, and
resolve them against what actually matters for the consumer — usually the transitive names, not the
bytes.]

[PITFALL: **The library's shallow clones cannot answer a history question.** `--depth 1` is the
convention there and it is right for reading current source, but constraint archaeology needs
`git fetch --deepen <n>` first. `git log -p -- pyproject.toml` on a depth-1 clone returns one commit
and looks like a project that has never changed its pins.]

### 3. The script

`scripts/package_health.py`, stdlib only, reading PyPI's JSON API and the GitHub API through `gh`
(so it uses the user's own token and rate limit rather than needing one configured):

```
python3 package_health.py <pypi-name> <owner/repo> [--clone <path>] [--json]
```

A working prototype exists and produced every number in this plan; it lives in a session scratchpad
and will not survive, so it is a starting point to rewrite rather than a thing to move.

What it must compute, beyond the obvious field reads:

- release cadence from `releases[*][*].upload_time_iso_8601`, taking the **minimum** upload time per
  version — a version's files are uploaded at slightly different moments and the max drifts
- human-only contributor counts, per the bot trap above
- runtime dependencies as `requires_dist` entries **without** `extra ==`, since the extras dominate
  the raw list and are not what a consumer installs
- with `--clone`, the source/test line split, `py.typed`, CI workflow inventory, and the licence
  files actually present

[DECISION: **`--clone` never clones.** It reads a path the caller already has and refuses one that
is not a directory. The convenient behaviour would put entries in `$RESEARCH_HOME` as a side effect
of an unrelated question, which is how a library fills with material nobody chose to keep — and the
library's own conventions require a `SOURCE.md` beside every entry, which a side-effect clone would
not write. Settled 2026-09-02 with the implementation.]

[DECISION: **no download-count metric.** PyPI's stats come from BigQuery or pypistats.org rather
than the JSON API, so it is a second network dependency for a signal close to popularity — which
this plan's whole premise says is weak. "Is anybody using this at all" is a legitimate and different
question; when it needs answering, the dependents graph and the tracker's traffic answer it better
than a download count that CI mirrors inflate.]

### 4. Tests

The user's requirement is "efficient, effective and fully tested", and the hard part is that every
input is a network response. So:

- fixture JSON captured from real PyPI and GitHub responses, checked in, with the fetch layer taking
  an injectable transport — the same shape as the rest of these repos
- the cadence, bus-factor and dependency-filtering computations tested directly against fixtures,
  including the bot-filter and the multi-file-upload-time cases above, which are the parts with
  actual logic in them
- one test per trap in section 2, so a regression reintroduces a wrong answer loudly
- the clone-inspection half tested against a tiny synthetic tree rather than a real clone
- **no test may reach the network**, and that is worth asserting rather than intending

[DEFERRED: A `--compare` mode taking two or more candidates and emitting the table directly. Obvious
and desirable, and deliberately after the single-candidate path is right — the absolute bar is the
part this plan argues matters, and a comparison mode built first would quietly make the head-to-head
the primary output again.]

[DEFERRED: Generalising beyond PyPI. The same questions apply to npm, crates.io and Go modules, and
the metric definitions would transfer with a different fetch layer. Not now; there is one ecosystem
in play and a premature abstraction over registries would be shaped by exactly one of them anyway.]

## What landed, 2026-09-02

All four sections, in `research-library`:

- **`scripts/package_health.py`** — stdlib only, PyPI over HTTPS and GitHub through `gh api` so it
  uses the caller's own token. The fetch layer is a `Transport` protocol, which is what makes the
  computations testable. `--clone` for what no API answers, `--generated <glob>` for the binding
  layer, `--json` for the whole answer.
- **`SKILL.md`, "Judging a candidate dependency"** — the absolute bar, the four axes, and the three
  report lines that are traps wearing the shape of an answer.
- **`references/dependency-health.md`** — every trap and every methodology decision, loaded when a
  recommendation is being written rather than when the script is being run.
- **`tests/unit/test_package_health.py`** — 53 tests, one per trap, driven from fixtures captured
  from the real PyPI and GitHub APIs and trimmed to the fields the script reads. An autouse fixture
  replaces `urllib.request.urlopen` and `subprocess.run` with functions that fail the test, so "no
  test may reach the network" is asserted rather than intended.

### Three traps this plan did not know about, found by running the thing

Each was found the way the plan's own methodology says to find them — by measuring a real candidate
rather than reasoning about the metric — and each would have produced a confident wrong answer.

**PyPI's release map holds pre-releases, and counting them inverts the maintenance verdict.** On
`httpx`, the three most recent uploads are `1.0.dev4/5/6`, so the naive reading is "4 releases in
the last year, the newest yesterday". On the stable line it is **zero in the last year and the last
one 634 days ago** — the opposite answer to "is this maintained for me". `cadence` now splits the
two and reports the pre-release line beside the stable one; `.post` stays a real release.

**`open_issues_count` counts pull requests and survives a repo with no issue tracker.** `httpx`
reports `has_issues: false` and `open_issues_count: 143`, every one a PR. The plan's own criterion —
"open issue count relative to project size" — would have compared a review backlog against a support
backlog. `has_issues` is now carried beside the count and the report says which it is.

**A recent-closed sample can hold zero issues.** 300 closed items across three pages of `httpx`'s
issues endpoint, not one an issue, so the median was `None` for a project that has closed thousands.
A bare `None` is indistinguishable from a project that closes nothing, so the sample composition
travels with the median. `pallets/click`, which does use its tracker, yielded 4 issues in 50 — the
metric is obtainable and thin, which is itself worth printing.

### The description was widened, and measured before adoption

The old wording named only the library at `$RESEARCH_HOME`, so none of the new requests could have
selected the skill. Candidate mode, `evals/dependency-health.json`, 7 cases at 3 runs: **6/7, with
the candidate winning 9 of 12 fires**, the three new positives at 3/3 each, the clone case correctly
staying with the incumbent, and `db-defaults` keeping its "what kind of datastore" case cleanly —
that pair being the boundary the widening was written around. Full table in
`skills/skill-fitness/references/measurements.md`.

The one failing case is kept rather than reworded: "does this package ship py.typed" names no
package and no repo, and the description is deliberately scoped to a named candidate.
