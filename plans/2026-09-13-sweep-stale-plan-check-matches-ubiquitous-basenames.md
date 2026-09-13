---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: 5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl
source_moment: 2026-09-13T14:56:10+03:00
source_plan:
---

# `sweep`'s made-stale-elsewhere check is 90% noise, and it is the section the skill already knows how to fix

## Context

`session-harvest`'s step 5 has a check for "what this session made stale somewhere else" — plans in
other repos and in the store naming a source file this session wrote. Run against a `repo-tasks`
session on 2026-09-13 it returned **20 rows, of which 18 matched on nothing but `__init__.py` or
`pyproject.toml`**.

Those two basenames are near-universal in a Python repo family. Matching them says only that the
session touched a Python package and that the other repo is also a Python package — which is true of
every session and every repo here, so the rows carry no information at all.

## Evidence

Session `5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-13, sweep
at boundary `2026-09-13T14:56:10+03:00`. The heading to search for is
`plans elsewhere naming a source file this session changed`.

| what the row matched on | rows  | signal                                |
| ----------------------- | ----- | ------------------------------------- |
| `__init__.py` only      | 9     | none                                  |
| `pyproject.toml` only   | 8     | none                                  |
| both, and nothing else  | 1     | none                                  |
| `selfinstall.py`        | **2** | **both genuinely about this session** |

The two real rows are `power-user-linux-setup/plans/2026-08-23-invoke-repo-tasks-tool-conflict.md`
and the store's own `2026-09-12-stamp-python-item-answered-in-repo-tasks.md` — and the session had
already found and acted on both by other means, hours earlier, which is worth noting because it
means the check's true positives were also its least useful ones on this run.

## The skill already contains the argument for fixing this

The `paths this session wrote into files that do not exist` check learned exactly this lesson and
carries it in its own text:

> The cost was never the noise: a section that has been all-false-positive once is one the next
> harvest skims, and the true positive above would have been the eleventh line.

That check was narrowed to three filenames for that reason. This one was not, and it is now the
section most likely to be skimmed — 18 rows deep before the reader reaches anything real.

[PITFALL: the check's stated limit, "candidates, not a verdict", reads as though it covers this. It
does not. That wording asks the reader to judge whether a plan naming `quality.py` is really about
`quality.py` — a judgement worth making. A row matching `__init__.py` is not a candidate needing
judgement; it is a match on a filename that carries no subject, and no amount of reading turns it
into a verdict either way.]

## Open questions, answered 2026-09-13

Landed as `0c249f9` and `4924cf0`, following the recommended direction below. The re-run against
this session returned exactly the two `selfinstall.py` rows, out of 24 the unchanged check printed
that day.

- **A fixed list, or a discriminating match?** A fixed list of package scaffolding, names a tool
  fixes for every package and whose content is always that package's own (`SUBJECTLESS_NAMES`),
  chosen after measuring both self-tuning shapes. Counting plan mentions would drop `plans.py`,
  named by 38 plans in five repos because it is one shared file. Counting checkouts that track a
  name separates `__init__.py` (36 of 71) from `selfinstall.py` (1) today, but a canonical file one
  repo propagates — `ruff.toml` at 6, `dprint.json` at 9 — gains a checkout with every consumer, so
  any fixed threshold eventually drops exactly the file whose consumers' plans may really be about
  the change. `README.md` was never searched, since `.md` is excluded.

[PITFALL: **tool config looks like scaffolding and is not.** `pytest.ini` has a name as fixed as
`conftest.py` and sits in 19 checkouts, so the first draft of the list carried it. `repo-tasks`
distributes a canonical `pytest.ini` to its consumers, together with `ruff.toml` and `dprint.json`,
so a change there is precisely what a consumer's plan naming it may be about. The list holds only
scaffolding, and a test pins `pytest.ini` as searched.]

- **Should the row say what it matched on?** It keeps its `names:` line, and the section now also
  prints the skipped names as `not searched`, so the filter is visible rather than silent.

## Recommended direction

1. Add the stop-list, matching what the sibling check does, and say in the skill text that this
   section learned the same lesson as that one — the two are a pair and should read like it.
2. Re-run the sweep against this same session afterwards. The expected result is 2 rows, both naming
   `selfinstall.py`, and that is a cheap falsifiable check on the change.
3. Leave the `candidates, not a verdict` limit exactly where it is. It is the right caveat for the
   rows that remain, and this change is not a substitute for it.
