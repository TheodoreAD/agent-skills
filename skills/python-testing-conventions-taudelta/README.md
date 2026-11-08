# python-testing-conventions-taudelta

Settled pytest defaults: fixtures first, and real dependencies over mocks.

Coding agents write a lot of tests, and left alone they write them the same way every time. The same
three lines of setup get pasted at the top of every test. A mock appears the moment a test would
touch a file or a socket, even when the real thing would run in milliseconds. And "make sure
everything is clean" becomes a formatter run inside a test, which quietly fixes the exact defect the
test was supposed to catch.

This skill gives the agent one default answer for each of those decisions. It covers what a fixture
should hold and at what scope, when to parametrize and when to write a separate test, when to run a
dependency for real, and how to keep a suite from writing into your real home directory.

These are one author's rulings, not a neutral survey. Each default is what this author settled on,
with the reasoning written down. Where you would rule differently, fork the skill and change it. The
`-taudelta` suffix on the name marks it as that kind of skill.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others.

## What you get

- Fixtures first. Any setup a test needs is a pytest fixture, moved to `conftest.py` once two files
  want it. That removes the duplication, and it also puts three versions of "make a fake repo" side
  by side, where someone notices and merges them.
- A plain rule for parametrizing. If adding a case means adding a value, parametrize. If it means
  changing the test's logic, write a new test.
- Real dependencies wherever the suite can start and stop them itself: a SQLite file, a temp
  directory, a local queue, your own program run as a subprocess. A stand-in is kept for things the
  suite can't own, like a third-party HTTP API.
- The traps of a fake home directory, including the three extra ones Windows adds.
- A note on each rule saying whether it overrides what a model would do on its own or just confirms
  it, so the agent knows which lines carry weight.

## What it looks like

The habit the skill replaces:

```python
def test_list_is_empty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "plans").mkdir()
    assert list_plans(repo) == []
```

The same three setup lines appear in the next test, and the one after. The default moves them into a
fixture once and lets each test read as the scenario it checks:

```python
@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "plans").mkdir(parents=True)
    return root


def test_list_is_empty(repo):
    assert list_plans(repo) == []
```

Setup mechanics stay in one place, and the scenario stays readable top to bottom in the test itself.

## Why not mock it

Patching is the shape most training data shows, and "tests shouldn't touch the disk" sounds
disciplined. But a mock of something the suite could run for real tests the mock. The deciding
question in this skill is whether the suite can own the dependency's whole lifetime, not a list of
technologies. That question answers new cases on its own, where a list goes stale.

Real is not the same as sandboxed, though. A test that reaches `Path.home()` writes into your real
home directory, and running real services makes that matter more, not less.

## Built from what went wrong

On 2026-09-05 a suite that had never run on Windows was run there for the first time: 136 of 557
tests failed. Every failure was one of five fake-home and path traps now listed in the skill, and
none was a bug in the code being tested.

On 2026-08-23 an end-to-end test in a project generator ran the repo's fix-then-check command
against a freshly generated project. The fix step reformatted a generated `README.md` before the
check ran, so the test passed while every generated project failed its own first CI run. The skill
now says to use the check-only form of a command in a test unless the fix itself is what's being
tested.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill python-testing-conventions-taudelta
```

It picks up on its own when the agent writes or restructures Python tests. You can also ask
directly: "should this be a fixture?", "parametrize or a new test?", "mock the database or use a
real one?".

Design and style questions outside tests are in the companion
[python-conventions-taudelta](../python-conventions-taudelta/) skill.

## What it touches

Nothing. It has no scripts and runs nothing. It only guides how your agent writes tests.

## Read more

- [`SKILL.md`](SKILL.md): every default, and whether it overrides a model's own habit.
- [`references/rationale.md`](references/rationale.md): the sources consulted, and the DAMP versus
  DRY debate as it actually stands.
- [`references/snippets/testing.py`](references/snippets/testing.py): a runnable sketch of the
  fixture and parametrize shapes.
