---
status: idea
updated: 2026-09-07
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

| script              | stmts |   cover |
| ------------------- | ----: | ------: |
| `plans.py`          |  2024 | **93%** |
| `package_health.py` |   356 |     88% |
| `library.py`        |   270 |     81% |
| `audit.py`          |   468 |     71% |
| `harvest.py`        |  1216 |     71% |
| `prompts.py`        |   162 |     74% |
| `fitness.py`        |   881 | **62%** |
| `trigger.py`        |   256 | **20%** |

`trigger.py` is the outlier and the reason it is one is legible: it shells out to `claude -p`, so
the half that runs a request cannot be unit-tested cheaply. But 20% means the parsing and scoring
halves are not covered either, and those are pure functions — the same shape `prompts.py` turned out
to be.

[NEEDS CLARIFICATION: **how much of `trigger.py` is actually untestable?** The answer is a reading
of which statements are inside the subprocess path and which are not, and it decides whether 20% is
a gap or a ceiling. `--cov-report=term-missing` names the lines; nobody has looked.]

## Anonymous record shapes

`count_shapes.py` over the four large scripts:

| script       | tuple returns | tuple params | dict params | dict fields |
| ------------ | ------------: | -----------: | ----------: | ----------: |
| `harvest.py` |        **11** |            0 |          13 |          13 |
| `fitness.py` |             6 |            1 |          12 |          14 |
| `plans.py`   |             1 |            0 |          10 |          12 |
| `audit.py`   |             1 |            0 |           2 |           6 |

`harvest.py`'s eleven are the standout: `upstream_of -> tuple[str | None, str]`,
`_sweep_transcript -> tuple[Transcript | None, str]`, `queued_messages -> tuple[list[Turn], int]`,
`answers -> tuple[list[Turn], int]` and seven more. Its thirteen `dict[str, Any]` parameters are
almost all the `_print_*(payload)` renderers, which is a different thing — a printer taking the
payload it prints is not an anonymous record threaded through a call chain.

[NEEDS CLARIFICATION: **is a two-element return worth a name here?** The skill's own case for
counting them is a 47-signature module where state was threaded through tuples nobody could follow.
These are mostly `(value, why)` pairs returned to one caller and unpacked immediately, which is the
shape a `NamedTuple` improves least. The honest test is whether any of the eleven is unpacked in
more than one place, or passed on as a tuple — that is a grep, not a judgement.]

[NEEDS CLARIFICATION: **do the `_print_*` renderers want a typed payload?** Thirteen functions take
`dict[str, Any]` produced by one function each. A dataclass per section would type them, and would
also mean the `--json` output and the printer stop being the same object — which is currently a
feature, since the JSON is the payload verbatim.]

`find_mutations.py` is the reassuring half: 15 attribute assignments across all eight scripts, so
these are near-stateless by construction. Two are worth a look on their own — `fitness.py:1810` and
`1815` write `args.ref_label` and `args.root` back into the argparse `Namespace`, which makes the
parsed arguments a mutable carrier rather than a record of what was asked for.

## Recommended direction

Take the two `NEEDS CLARIFICATION` greps first — they are minutes and they decide whether the tuple
finding is real. The `trigger.py` coverage question is the one with a clear payoff: if most of the
uncovered half is pure, it is the same win `prompts.py` just was.
