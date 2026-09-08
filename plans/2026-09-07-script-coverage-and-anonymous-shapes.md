---
status: idea
updated: 2026-09-08
---

# What the Python-code audit found in this repo's own scripts

## Context

Measured 2026-09-07, running `python-refactor-audit`'s two scripts and `pytest --cov` over the eight
shipped scripts — the first time this repo has audited its own code the way its skills tell other
repos to. The two findings that were cheap and unambiguous were fixed the same day and are not here:
`prompts.py` had **no tests at all** and did not appear in the coverage report (now 74%, 29 tests),
and both `python-refactor-audit` scripts crashed with a traceback on `--help`. What is left needs a
decision rather than a fix.

## Coverage, after the `prompts.py` gap was closed

Re-measured 2026-09-08, after the `harvest.py` rewrite. The 2026-09-07 column is kept because the
movement is the finding: two scripts grew by a third or more, and only one of them brought its
tests.

| script              | stmts 09-07 | stmts 09-08 | cover 09-07 | cover 09-08 |
| ------------------- | ----------: | ----------: | ----------: | ----------: |
| `plans.py`          |        2024 |        2216 |         93% |     **93%** |
| `package_health.py` |         356 |         359 |         88% |         87% |
| `library.py`        |         270 |         603 |         81% |         78% |
| `audit.py`          |         468 |         484 |         71% |         71% |
| `harvest.py`        |        1216 |        1588 |         71% |         75% |
| `prompts.py`        |         162 |         168 |         74% |         74% |
| `fitness.py`        |         881 |         884 |         62% |     **62%** |
| `trigger.py`        |         256 |         259 |         20% |     **20%** |

`harvest.py` took 372 more statements and its coverage went **up**, which is the shape to want and
the reason it is not on the list below. `library.py` more than doubled and lost three points, so its
new half is thinner than its old one — worth a look on its own terms, and not something the
2026-09-07 pass could have seen.

[DECISION: **`trigger.py`'s 20% is a gap, not a ceiling.** Measured 2026-09-08 with
`--cov-report=term-missing` plus a `coverage json` split of the missing lines against the two
subprocess-bound functions: of 207 uncovered statements, **66 are inside `run_query` or `execute`
and 141 are not**. The untestable half caps the file at roughly 75%, not at 20%. Everything else
missing is pure — `Result`'s methods, the whole `_StreamState` stream parser, `write_candidate`,
`write_proposal`, `load_cases`, `summarise`'s scoring, `_foreign_expectations`, `_refuse`,
`_dry_run` and `main`'s argparse. Same shape `prompts.py` turned out to be, and the same size of
win.]

## Anonymous record shapes

`count_shapes.py` over the four large scripts, both dates:

| script       | tuple returns 09-07 | tuple returns 09-08 | dict params 09-07 | dict params 09-08 |
| ------------ | ------------------: | ------------------: | ----------------: | ----------------: |
| `harvest.py` |              **11** |              **14** |                13 |                15 |
| `fitness.py` |                   6 |                   6 |                12 |                12 |
| `plans.py`   |                   1 |                   1 |                10 |                12 |
| `audit.py`   |                   1 |                   1 |                 2 |                 2 |

Tuple parameters are unchanged: one in `harvest.py` (`_named_before`), one in `fitness.py`
(`_is_owned`), none elsewhere.

The rewrite moved `harvest.py` in the wrong direction — three more anonymous returns
(`_explicit_session`, `_resolve_since`, `_green_claims`) and two more `dict[str, Any]` parameters.
That is worth stating plainly, because the same rewrite improved coverage: the two measurements
disagree about whether it went well, and only one of them was being watched.

Its `dict[str, Any]` parameters are still almost all the `_print_*(payload)` renderers, which is a
different thing — a printer taking the payload it prints is not an anonymous record threaded through
a call chain.

[DECISION: **the tuple finding is not real, by this plan's own test.** Ran 2026-09-08 over all
fourteen: every one is destructured at the call site, and **not one is passed on as a tuple**. Ten
have a single call site. The multi-site ones are `iter_blocks` (8), `bash_calls` (5) and `_stores`
(5) — all returning `Iterator`/`list` **of** pairs, unpacked in a `for` header, which is a
collection and not a record. `upstream_of` is the only genuine `(value, why)` shape with more than
one caller (3, one of which discards the `why`). Naming these buys nothing; the skill's own case for
counting them was a module where state was threaded through tuples nobody could follow, and this is
not that. **Leave them.**]

[NEEDS CLARIFICATION: **do the `_print_*` renderers want a typed payload?** Now fifteen functions
taking `dict[str, Any]` produced by one function each. A dataclass per section would type them, and
would also mean the `--json` output and the printer stop being the same object — which is currently
a feature, since the JSON is the payload verbatim.]

`find_mutations.py` is still the reassuring half: 16 attribute assignments across all eight scripts
(was 15), so these are near-stateless by construction. The two worth a look are unchanged in
substance and have moved by a line — `fitness.py:1811` and `1816` write `args.ref_label` and
`args.root` back into the argparse `Namespace`, which makes the parsed arguments a mutable carrier
rather than a record of what was asked for.

## Recommended direction

Both 2026-09-07 greps are now answered, and they split cleanly: the tuple half is closed, the
coverage half is open with a measured payoff. So there is one thing left worth doing and one thing
worth watching.

1. **`trigger.py`'s pure half.** 141 uncovered statements that are not subprocess-bound, in a file
   whose parsing and scoring are exactly the shape `prompts.py` was. Clear payoff, no design
   question in the way.
2. **`library.py` grew 270 -> 603 statements and lost coverage.** Not visible on 2026-09-07 and not
   investigated; find out what the new half is before deciding whether it matters.
3. **Watch the shape counts alongside coverage, not instead of it.** The `harvest.py` rewrite is the
   evidence: coverage said it went well, `count_shapes.py` said it drifted, and nothing was
   comparing the second one. Same argument `fitness.py derivable --compare <baseline>` already wins
   for a different metric — a baseline in `tests/fixtures/` is the shape, if this is worth gating.
