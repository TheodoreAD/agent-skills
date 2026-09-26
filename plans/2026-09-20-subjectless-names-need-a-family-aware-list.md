---
status: idea
updated: 2026-09-20
source_repo: github.com-personal/power-user-linux-setup
source_session: 70f5fe13-9f1a-40f4-84ac-5ce4fd98a163.jsonl
source_moment: 2026-09-20T21:20:10+03:00
source_plan:
---

# `SUBJECTLESS_NAMES` is a Python-package list, and the noise it filters is family-wide

Filed from a `power-user-linux-setup` harvest, which may not edit `agent-skills`. Reports a
measurement rather than proposing a design, so `source_plan` is blank.

## Context

`session-harvest`'s step 5 has two sections that match this session's changed files against plan
prose — "plans in other repos naming a file this session changed" and this repo's own equivalent.
Both already know the failure: a name every package has its own copy of matches everywhere and names
no subject. `SUBJECTLESS_NAMES` is the fix, added after a 2026-09-13 run measured 24 rows of which
22 matched nothing but `__init__.py` or `pyproject.toml`.

The list as it stands is
`{__init__.py, __main__.py, conftest.py, pyproject.toml, setup.cfg, setup.py, tasks.py}` — every
entry a Python packaging artifact.

## Evidence

Measured 2026-09-20 on a harvest of a session that changed `setup.toml`, `ci.yml`, `util.py`,
`netdoctor.py`, `wsl.py`, `cli.py` and several test modules.

**The cross-repo section returned 12 rows and all 12 were subjectless-name matches** — 8 repos
searched, and every row matched on `setup.toml`, `ci.yml` or `util.py` and nothing else. Not one row
named a file whose identity made the match meaningful. This repo's own section did better: 15 rows,
of which the `netdoctor.py` and `wsl.py` matches were real and the other 13 were `setup.toml`.

The three names divide into two different reasons, which is why extending the list by three strings
is the smaller half of the fix:

- **`ci.yml` and `util.py` are the existing failure exactly.** Every repo in this family has both.
  They belong in `SUBJECTLESS_NAMES` as it is defined today, and were missed only because the list
  was assembled from one language's packaging conventions rather than from what this machine
  actually holds.
- **`setup.toml` is a different shape and the more interesting one.** Exactly one repo on this
  machine has a file by that name — so as a _file_ it is perfectly distinctive, and a path-based
  check would be right to keep it. What makes it subjectless is that it is the machine's own
  configuration, so plans in every sibling repo discuss it: seven of the eight repos searched had a
  plan mentioning it. The match is real and the inference is not. **A name can be unique on disk and
  still name no subject in prose.**

## Open questions

[NEEDS CLARIFICATION: **derive the list instead of extending it?** The obvious version — count how
many repos under `projects_root` contain a file of that name, and treat anything above a threshold
as subjectless — fixes `ci.yml` and `util.py` for free and on any machine, with no list to maintain.
It gets `setup.toml` exactly wrong, because that file exists once. The two failure modes are
genuinely different and one derivation cannot cover both; a derived list plus a small explicit one
for the machine's own shared vocabulary may be the honest shape.]

[NEEDS CLARIFICATION: **is the cross-repo section earning its place at all?** Two measured runs now,
2026-09-13 and this one, and between them 34 rows of which 2 were real — both in the _own-repo_
half. The section's stated purpose is the genuinely uncoverable case (a plan elsewhere describing a
mechanism this session replaced, with a measurement booked against it), which is worth having. But a
section that has been ~94% noise twice is one the next harvest skims, and the skill already says so
about a different all-false-positive section. Tightening the names may be enough; if it is not, the
question is whether prose-matching is the wrong instrument for that case rather than a badly-tuned
one.]

## Recommended direction

1. Add `ci.yml` and `util.py` to `SUBJECTLESS_NAMES`, which is the part that is unambiguous and
   costs two strings.
2. Decide the `setup.toml` shape — a second, machine-specific list of shared-vocabulary names, or
   accept it as a known noise source and say so in the section's own `limit:` line, which is where
   the skill puts its other honest gaps.
3. Re-measure the section on the next harvest that changes a widely-discussed file, and record the
   row count before and after. Two runs is enough to establish the noise and not enough to establish
   that the fix helped.

## Verification

Reproduce the measurement with
`python3 <checkout>/skills/session-harvest/scripts/harvest.py sweep
--boundary <instant>` in a repo
whose session changed a file every sibling's plans discuss, and read the two plan-matching sections'
row counts against how many rows matched only a shared name.
