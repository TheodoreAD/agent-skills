---
status: in-progress
updated: 2026-09-26
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

[DECISION: **neither extend nor derive the list — change what a cross-repo match is.** Settled
2026-09-26 with the user. The reframing: most users never build a repo that propagates files into
their others, so protecting that rare case with a precise mechanism, while every harvest pays for
generic noise, had the costs backwards. A plan in another repo now counts only if **one paragraph
names both the file and the repo it lives in**, unless the plan lives in that repo's own checkout or
store mirror. `SUBJECTLESS_NAMES` is unchanged and still skips scaffolding. Rejected: a derived
count threshold (gets `setup.toml`, which exists once, exactly wrong), a machine-specific
shared-vocabulary list (cannot ship in a published skill), repo-relative path matching (machinery
for the rare case). What it gives up is a plan that refers to the repo only obliquely.]

[DECISION: **the cross-repo section earns its place under the new rule.** Re-run 2026-09-26 on this
plan's own 2026-09-20 session: **19 rows by basename, 9 with a whole-file repo test, 4 by
paragraph.** Each of the 4 is about the setup repo's own `setup.toml` or `ci.yml` — whether each is
_affected_ still needs reading, which is what "candidates" means. The whole-file step was too loose
because a long plan names a widely-used repo somewhere and its own `ci.yml` somewhere else. The
confirmed 2026-09-13 true positive still matches: that plan's title names `repo-tasks`.]

[NEEDS CLARIFICATION: **the own-repo section's `setup.toml` noise is untouched.** "This repo's open
plans naming a file this session changed" is a separate check with its own three-mention proxy, and
on the same re-run it still printed 15 rows, 13 of them `setup.toml`. There the repo test means
nothing, since every plan is about that repo. Options: a `limit:` line naming the shape, or raising
the proxy for a name the repo's plans mention constantly. Needs its own measurement first.

**Measured 2026-09-26: a share threshold cannot separate vocabulary from a central subject.** Share
of open plans naming a file three or more times: `setup.toml` 15 of 65 (23%) in the setup repo, with
real subjects there at 2–3%. But `plans.py` is 10 of 51 (20%) in this repo and **is** the subject of
those plans, the plan-docs ones. Other repos top out at 9–12% on one plan each. So 23% and 20% are
indistinguishable by count while being opposite cases: one is a declaration file edited for many
unrelated reasons, the other is code whose plans design it. Any threshold that hides `setup.toml`
hides `plans.py`. Remaining options: collapse a widely-shared name's rows into one counted line
(cheap to read, still visible, but it collapses `plans.py` too), or accept the rows and add a
`limit:` line. This is a trade-off for the user rather than a measurement question.]

## Recommended direction

1. ~~Add `ci.yml` and `util.py` to `SUBJECTLESS_NAMES`, which is the part that is unambiguous and
   costs two strings.~~ **Not unambiguous — checked 2026-09-26 while implementing it, and not
   done.** The list's own comment in `harvest.py` admits only names a tool fixes for every package
   and **deliberately excludes config one repo propagates to consumers**, because a consumer's plan
   naming such a file may be about the change. `ci.yml` is exactly that: `scaffoldapy` ships
   `template/.github/workflows/ci.yml` into every project it generates, so a session changing it is
   the case where a sibling plan naming `ci.yml` matters most. And `util.py` is not "in every repo":
   the family has one real one (`power-user-linux-setup/tasks/util.py`) plus a vendored `invoke`
   copy in a playground. It is a conventional name, not a tool-fixed one, so the list's criterion
   does not admit it either. **A name can match everywhere in prose without being scaffolding on
   disk**, and that needed a different filter from this list — the paragraph rule above.
2. ~~Decide the `setup.toml` shape.~~ Done for the cross-repo section by the paragraph rule, landed
   2026-09-26; the own-repo section is the open question above.
3. Re-measure on the next harvest that changes a widely-discussed file. The 2026-09-26 re-run is one
   before-and-after on a replayed session; a live harvest is the second data point.

## Verification

Reproduce the measurement with
`python3 <checkout>/skills/session-harvest/scripts/harvest.py sweep
--boundary <instant>` in a repo
whose session changed a file every sibling's plans discuss, and read the two plan-matching sections'
row counts against how many rows matched only a shared name.
