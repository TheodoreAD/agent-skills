---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/repo-tasks
source_session: 52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl
source_moment: 2026-09-07T16:10:00Z
---

# The audit skill can measure state but not ownership, and three counters would fix it

## Context

Two quality passes over `repo-tasks` on 2026-09-07, the second one asked for as "nice and clean and
**encapsulated**". `python-refactor-audit`'s counters answered the first pass and had nothing to say
in the second: they measure **state** — anonymous tuples, dict-shaped records, config threaded
through leading parameters — and the second pass's whole subject was **ownership**, which module a
name belongs to. Every finding in it came from a counter written on the spot.

That is the gap. The skill's table is the review, by its own account ("an agent can run them over a
module without reading it, which is the point"), and for the ownership question there was nothing to
run.

Filed rather than applied: a session in `repo-tasks` does not edit `agent-skills`.

## Evidence

The second pass's findings, each with the counter that produced it. Every one of them was invisible
to the existing table, and none was found by reading.

**Cross-module imports of a private name — 5, in a 26-module package.** An `ast` walk over
`ImportFrom` nodes with `level == 1` whose imported name starts with `_`. Two clusters:

- `gitflow._next_steps`, imported by `configs`, `deps` and `venv` with a `reportPrivateUsage`
  suppression each, while `trunkflow` and `release` hand-rolled the same two `print` calls rather
  than add a fourth. A block five modules produce belongs to none of them; it became its own module.
- `version._bump`, imported by `gitflow` and `trunkflow`. See the pitfall below — the interesting
  half.

**The same git question asked from more than one module — 1 of 47 distinct commands.** Collect every
string constant (and `JoinedStr`, with the interpolations blanked) starting with the tool's name,
grouped by module. `git rev-parse --abbrev-ref HEAD` was defined identically in both branching-model
modules. `git push origin …` also appeared in three, and is **not** the same finding: it is an act
those tasks exist to perform, where a helper would hide the thing the reader came for. The counter
finds candidates; question-versus-act is the judgement it hands back.

**Non-task functions with an unused parameter — 2.** Parameters never loaded in the body, excluding
functions carrying the framework's decorator (a task is handed a `Context` whether it uses one or
not). Both were discovery functions taking a `Context` for symmetry; one said so and one did not.
The outcome was a docstring, not a signature change — which is the counter working, since the
alternative was nobody noticing the asymmetry at all.

**Test files patching a module other than the one under test — 2, one of them wrong.** For each
`test_<module>.py`, the first argument of every `monkeypatch.setattr`. `test_version.py` patched
`subprocess` process-wide because the code under test called `subprocess.run` while holding a
`Context` it could have asked instead. The remaining one is legitimate (`test_interactive.py`
patches `subprocess` because that module's whole job is calling it). **A test reaching outside its
own module is usually the production code reaching outside its own seam** — the patch is the
symptom, and this counter finds it from the test side, which is where it is visible.

## Open questions

[NEEDS CLARIFICATION: one script or four? The existing two are one file per shape
(`count_shapes.py`, `find_mutations.py`), which argues for a third — `find_boundaries.py`, taking a
package directory rather than a file list, since every one of these counts is about a **set** of
modules and none of them means anything against a single file. The test-patching counter is the odd
one out: it reads the suite, not the package, and may belong to `python-testing-conventions` instead
— though the finding it produces is about production code, which argues for keeping it here.]

[NEEDS CLARIFICATION: does the table's "what it means when high" column survive for these? A high
private-import count is not automatically bad — a package with one genuinely internal helper used
twice is fine. What is bad is a private import **plus** a hand-rolled copy elsewhere, which is the
pair that says the facility is filed under the wrong module. The column may need to be "what to
check next" for these rows rather than "what it means".]

## Recommended direction

### 1. `python-refactor-audit`, "Measure the shape you are removing" — new rows and a script

The table at `skills/python-refactor-audit/SKILL.md:86` gets a second half, introduced as measuring
ownership rather than state:

| what to count                                             | what it means when high                                 |
| --------------------------------------------------------- | ------------------------------------------------------- |
| imports of another module's private name                  | a facility filed under whoever needed it first          |
| the same question asked from more than one module         | shared plumbing with no home — an act is not a question |
| non-decorated functions with an unused parameter          | a signature promising a dependency that is not there    |
| test files patching a module other than the one they test | production code reaching outside its own seam           |

Plus `scripts/find_boundaries.py`, stdlib-only, taking a package directory. The four walks above are
~60 lines together; the session that wrote them has them in its transcript rather than in a file,
which is exactly the "a number nobody can re-derive is an assertion" failure the skill already warns
about — so the script is the deliverable, not the table row.

### 2. `python-conventions`, the Encapsulation bullet (`SKILL.md:224`)

That bullet says Python has no real privacy and to reserve underscores for genuine package-public
surfaces. True, and it does not answer the question that actually came up. Add:

> **A name another module imports is not private, and the underscore then costs more than it buys.**
> It earns a suppression at each call site, and — worse — it records a boundary that is not there,
> so the next module needing the same call adds a fourth suppression rather than asking whether the
> name is in the right place. Two importers is the point to ask; three is the point to move it. The
> question is not "should this be public" but "which module owns this", and the suppressions are the
> evidence.

### 3. Both `python-conventions` and `invoke-task-conventions` — the pitfall worth its own paragraph

`version._bump` carried a comment, copied into two modules, saying the underscore kept it out of the
CLI namespace. It never did. `Collection.from_module` collects `Task` objects and nothing else —
probed against invoke 3.0.3 with a module holding one task and one public plain function, and only
the task was published. The general form belongs in `python-conventions`:

> **An underscore does not exclude a name from a framework's own registration.** Whatever collects
> your functions — a task collection, a plugin registry, a fixture scan, an autouse discovery — has
> a rule of its own, and the underscore is a convention between humans. Check what the framework
> actually collects before believing a comment that says the name is hidden; the mechanism is
> usually the framework's own explicit registration.

and the invoke-specific half in `invoke-task-conventions`: `from_module` publishes `Task` objects,
so an explicit `Collection(...)` listing is the only thing that keeps a task out of a namespace —
which is what several modules in `repo-tasks` already do, for exactly that reason.

### 4. `python-refactor-audit`, "The second oracle" — widen it by one sentence

The section is scoped to a field changing **type** under an unchanged name. The same reasoning
covers any change to output that no test asserts: moving five modules onto one printing helper
changed no behaviour the suite could see (two greps for the words "Next steps" in 6,000 lines of
tests), so the old prints and the new calls were run side by side and diffed. Worth one clause — "or
any change to output the suite does not assert on" — rather than a new section.

## Verification

Each edit lands with the `skill-authoring` sequence, and the script earns a test the way the other
two do. The honest check for the table rows is the one the skill already sets: run
`find_boundaries.py` against `repo-tasks` at the commit before this pass (`c133345`) and confirm it
reports 5 private imports, 1 duplicated question, 2 unused parameters and 2 cross-module patches —
then at `4c48f7d` and confirm 0, 0, 2-documented and 1-legitimate. A counter that cannot reproduce
the pass that motivated it is not worth shipping.
