---
name: python-refactor-audit
description: "Use when an existing Python module has grown and the question is how to restructure it safely, not what to write — auditing a file nobody has reviewed as a whole, planning the change as a sequence of small commits each verified on its own, deciding which tests may be edited to follow a rename and which must not change at a character, proving an edited test still fails when the production change is reverted, finding a second oracle when the suite cannot see the change (a field's type changing under a name every caller already uses), measuring the shape you are trying to remove before and after so a large diff that moves nothing is caught, and deciding when not to restructure at all. For what a given piece of Python should look like — data modeling, dates, settings, modularity and singleton defaults — see the Python conventions skill; for what a test should cover, the Python testing skill."
metadata:
  family: python
---

# Auditing and restructuring a Python module that grew

A procedure for the pass nothing else does: a module built incrementally, never reviewed as a whole,
where the problem is not any single line but a shape repeated across the file. Every diff-scoped
reviewer — a code-review command, a simplifier agent, a PR bot — is scoped to recent changes by
design, and whole-module state threading is precisely what no diff contains.

This skill is about **how the pass is run**, which matters more than the target shape. What the
resulting code should look like is `python-conventions`; what a test should cover is
`python-testing-conventions`. The loop, the oracle rules and the stopping rule below are
language-neutral; the examples are Python.

The worked example every rule here comes from is in [`references/pilot.md`](references/pilot.md) — a
3,476-line single-file script restructured in nine commits on 2026-09-01, with its before/after
counts, the two counts that did not reproduce, and the things that went wrong.
[`references/prior-art.md`](references/prior-art.md) is what was surveyed and what was deliberately
not taken.

## First decide whether to restructure at all

**Four stopping conditions. Any one of them and the answer is: don't.**

- The current structure is not impeding the work.
- The restructure serves a speculative future need.
- **The only justification is testability.**
- The code is good enough for the phase the project is in.

Take an adversarial stance toward your own plan: does each boundary you are proposing correspond to
a real seam, or is it structure for its own sake? A restructure has to be argued against before it
is argued for, because every argument for one is available for any of them.

The pass in `references/pilot.md` dropped two planned items under this rule — a property that would
have been a second door to an answer a pure function already gave, and caching a 1.9 ms call while
the 3.9 ms one repeated five times was the actual cost. **Dropping items mid-pass is the rule
working, not the plan failing.** Say why in the plan file; a dropped item with a reason is a
finding.

Size is not a stopping condition in either direction. A 3,000-line file of 20-line functions is
already decomposed; "it is long" is not the complaint, and a pass that moves lines around to shorten
it makes things worse. State the complaint as a shape you can count, or you have not found one yet.

## Measure the shape you are removing, before the first line moves

Write a script that counts the specific shape — an `ast` walk, not a grep, and not an impression —
and keep it, because the same script is what re-measures at the end. A large diff that moves no
count did not do the job.

Three rules about the counting, each learned by getting it wrong:

- **A count you cannot reproduce is not a baseline.** Two counts in the pilot's original table could
  not be reproduced by any reading of the AST — 69 config-taking functions measured 47 leading and
  55 anywhere — so the later before/after had to be judged against re-derived numbers. Take the
  baseline with the script, not by hand.
- **Count what you will attribute the win to, and nothing else.** 22 anonymous tuple returns were 16
  records and 6 homogeneous `tuple[str, ...]` collections; a collection has no positions to name, so
  naming it is not available as an improvement. Counting them together overstated the problem and
  would have understated the result.
- **Re-measure with the same script at the end, and do not assert the result.** The final number is
  a measurement or it is nothing.

## The loop

**BASELINE → CHECKPOINT → REFACTOR → VERIFY → CHECKPOINT, one property per commit.**

1. **BASELINE.** Full suite green, counts taken, the test suite classified (below), and the
   second-oracle capture taken if this step needs one.
2. **CHECKPOINT.** Commit, so the tree is clean before anything moves.
3. **REFACTOR.** One property, one shape, one commit. Not one class per commit.
4. **VERIFY.** Whole suite, re-run the counts, apply the oracle rules.
5. **CHECKPOINT.** Commit with a message saying what moved and what was verified.

**One property per commit is the load-bearing part of the sequencing, not a style preference.** The
diff will be enormous and almost entirely mechanical, which is exactly when a behaviour change
hides: 69 signature changes read as noise, and the one that also flipped an argument order reads as
noise too. Each commit's mechanical part has to stay small enough that its non-mechanical part is
visible. A single commit introducing the whole object and rewriting every signature cannot be
reviewed, so it will not be.

**Name the shapes first.** Anonymous returns and stringly-keyed lookups become named records before
any state gets encapsulated: it is what a reader gains most from, and every later step is then
easier to verify against a named thing than against a tuple position.

## The oracle rules

The test suite is the oracle. The rule has three parts, and an earlier draft of it that said flatly
"no test may be edited to make a refactor pass" was wrong — a test naming a renamed function has to
change, and changing it costs nothing. What must not change is **what** is tested.

1. **Classify the suite before the first line moves**, and write the classification down. Which
   tests drive only the public entry point (argv, the CLI, the package's public API) and which touch
   an internal name. In the pilot: 105 tests, 65 entry-point-only, 24 both, 16 internal-only.
2. **The entry-point-only tests are frozen — not one character.** They exercise behaviour through
   the public surface and assert on output and state, so nothing a behaviour-preserving pass does
   can legitimately touch them. **One of them changing is the definition of the refactor having
   leaked into behaviour.** Do not edit it; find what leaked.
3. **In the rest, only the call form may change.** `load_config()` becoming `Workspace(path).config`
   is mechanical substitution. No assertion edited, no case dropped, no parametrization thinned.
4. **The check that separates "renamed" from "weakened": revert the production change, and the
   edited test must still fail.** Reviewing the assertion diff misses the case where a test asserts
   the same thing but no longer reaches the code that could break it — this is what catches it. Run
   it on every test you touched, not on a sample.

Two supporting habits:

- **Grep the suite for the names you are about to change, before starting.** The churn is then
  bounded and predictable rather than discovered one failure at a time.
- **A suite that reaches for a module-level loader at 20 sites is an argument for the refactor, not
  a cost of it.** The tests reach for a global because there is no object to construct; after the
  pass they construct one against a fixture. Where a restructure improves the test surface, that is
  evidence the shape was wrong, not churn to be tolerated.

## The second oracle, for a change the suite cannot see

**A widely-used field changing its _type_ under a name every caller already uses has a silent
failure mode, and the suite is not sufficient for it.** Nothing is renamed, so a missed call site
does not raise — it interpolates a repr into output, and the suite only covers the lines it asserts
on. Any step of this shape needs a second oracle.

**Capture the output of every read-only command before and after, and diff it**, `--json` payloads
included. One shell script in a scratchpad, and it is the only evidence that reaches the output
lines no test reads. In the pilot: all 15 commands byte-identical.

[PITFALL: **that oracle reads live machine state, so the two captures must be taken back to back.**
Confirmed 2026-09-01: a diff taken against a baseline captured earlier in the session came back
showing changes to files the pass never touched — a parallel session had edited them in between, and
the command being captured reads every repo on the machine. Run the committed copy against the
working tree seconds apart (`git show HEAD:<path> > <tmp>`, then both) rather than reusing an
earlier capture.]

The same shape applies to any oracle built from a program's observable output: it is only valid if
everything else it observes is held still.

## Read the after-numbers honestly

**A count that moves less than hoped is often the right answer rather than unfinished work, and
saying so is part of the pass.** The pilot's config-taking count moved 47 → 38; what remained were
pure functions _of_ the config, and a function that takes the config because it derives something
from it has a signature that says exactly that. Handing it a whole context object instead would be
the same anonymity one level up.

- **State what the pass did not buy.** The pilot's performance win was ~16 ms; the value was
  structural — one answer computed in one place — and the write-up says so rather than letting the
  timing carry an argument it cannot.
- **The findings you did not predict are the strongest evidence for the pass.** Two commands turned
  out never to have needed the config at all, which only became visible when the prologue went and
  the linter flagged the variable as unused; another resolved the same path twice in one function.
  The old shape was hiding what those functions actually depended on. Record these; they are what a
  reader should take from the pass.

## Scope discipline while the pass is running

- **No behaviour change of any kind, including "obvious" improvements noticed in passing.** The
  whole value of the pass is that its diff is verifiable as behaviour-preserving. Noticed
  improvements become plan entries (`plan-docs`), each its own later commit.
- **Deferred items get their own commit before or after, never folded in.** Bundling an unrelated
  fix into a mechanical diff makes the mechanical diff unverifiable.
- **A file split is a separate decision, and usually not this one.** Encapsulation is the goal;
  files are not. For a script that ships inside a skill and runs as `python3 <path>` with no install
  step, single-file is load-bearing and a split is a regression.

## Editing this skill

This file is _copied_ into `~/.agents/skills/python-refactor-audit` at install time, never
symlinked. Edit the source in the [`agent-skills`](https://github.com/TheodoreAD/agent-skills) repo,
push, then re-run the install
(`npx skills add TheodoreAD/agent-skills --global --skill python-refactor-audit`) to refresh every
project's copy. Editing the deployed copy in place is local drift and reaches no other machine.
