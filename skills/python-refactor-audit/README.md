# python-refactor-audit

Restructuring a Python module that grew, one measured commit at a time.

Some modules are never reviewed as a whole. They grow a function at a time, each change reviewed on
its own, until the problem is no single line but a shape repeated across the file: the same config
object passed by hand through dozens of signatures, tuples returned where a named record belonged, a
dict used as a record with string keys. Every diff-scoped reviewer misses this by design, because no
one diff contains it.

Asking an agent to "clean this up" is how that goes badly. The result is a huge diff, mostly
mechanical, where one real behaviour change hides among a hundred renames. The tests pass, because
someone edited them to pass.

This skill is a procedure for doing the pass safely. It decides whether to restructure at all,
counts the shape before touching anything, and moves one property per commit. Each commit is checked
against a test suite whose rules say which tests may change and how.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others.

## What you get

- Four stopping conditions checked first. If the structure isn't slowing the work, if the need is
  speculative, if the only argument is testability, or if the code is good enough for the project's
  phase, the answer is not to restructure. Length alone is never the complaint.
- Two small scripts that count the shapes worth removing, so the review starts from numbers rather
  than an impression. The same scripts re-measure at the end, which is how a large diff that moved
  nothing gets caught.
- A loop: baseline, commit, change one property, verify, commit. Each commit stays small enough that
  anything in it other than mechanical renaming is visible.
- Rules for the test suite. Tests that only drive the public entry point are frozen, not one
  character changed. In the rest, only the call form may change. And every edited test must still
  fail when the production change is reverted.
- A second check for the change the suite can't see: a field keeping its name while its type
  changes. Capture every read-only command's output before and after, and diff it.

## What it looks like

`count_shapes.py` pointed at one of this repo's own scripts, `session-bash-audit`'s `audit.py`. Real
output, trimmed:

```
anonymous tuple RETURNS: 6
  load_session -> tuple[list[Call], Path | None]
  load_calls -> tuple[list[Call], int]
  drop_replayed -> tuple[list[Call], int]
  …

anonymous tuple PARAMETERS: 1
  save_baseline(window: tuple[str | None, str | None])

dict parameters: 3
  _print_compare_header(baseline: dict[str, Any])
  compare(expectations: dict[str, str])
  _print_rates(groups: dict[str, list[Call]])
```

Each line is a candidate, not a verdict. A tuple of two unrelated things returned from a function is
information that was thrown away, and naming it is usually the first commit of a pass. A dict built
to be handed to `json.dumps` is usually fine, and the skill says so. A companion script,
`find_mutations.py`, lists every attribute assignment in a module. That turns "should these records
be frozen?" from a matter of taste into a two-minute check.

## Why not just ask for a refactor

An unstructured refactor produces the diff nobody can review. Sixty signature changes read as noise,
and the one that also flips an argument order reads as noise too. The skill's answer is sequencing
and oracles, not caution. Name the shapes first, change one property per commit, and prove each
edited test would still catch a regression.

It also covers knowing when to stop. A count that moves less than hoped is often the right result.
What remains may be functions that genuinely depend on the thing being passed, and the write-up
should say so.

## Built from a real pass

Every rule comes from one worked example, recorded in the skill's references: a 3,476-line
single-file script restructured in nine commits on 2026-09-01. Its 105 tests were classified before
anything moved, 65 of them public-entry-point only and left untouched. For the step no test could
see, all 15 read-only commands produced byte-identical output before and after.

It also records what went wrong. Two counts in the original plan could not be reproduced by any
reading of the code, so the before and after had to be judged against re-derived numbers. That is
why the skill takes every count with a committed script and never by hand.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill python-refactor-audit
```

Then ask: "this module has grown, how should we restructure it?", or "audit this file and plan the
refactor as small commits".

Needs Python 3.11 or newer for the two scripts, with nothing to install. What the restructured code
should look like is the companion [python-conventions-taudelta](../python-conventions-taudelta/)
skill's job.

## What it touches

The two scripts read the Python files you point them at, write nothing, and use no network. The
commits the procedure produces are made by your agent in your repo, one at a time. The complete list
is in [`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full procedure your agent follows.
- [`references/pilot.md`](references/pilot.md): the worked example, with its before and after counts
  and what did not reproduce.
- [`references/prior-art.md`](references/prior-art.md): what was surveyed and deliberately not
  taken.
