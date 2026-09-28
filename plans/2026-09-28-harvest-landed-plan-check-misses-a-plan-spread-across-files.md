---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: 81492b4f-e6bc-4577-8d01-412b3ff4e7a9.jsonl
source_moment: 2026-09-28
source_plan:
---

# The sweep's "did this session land an open plan" check misses a plan that names several files

## Context

`harvest.py sweep` lists this repo's open plans that name a file this session wrote "three times or
more". On a scaffoldapy harvest that threshold picked the wrong plan and missed the right one.

- **Listed:** `2026-08-30-generated-test-layout.md`, matched on `conftest.py`. That was only an
  incidental edit (a `UV_PYTHON` removal in the e2e fixture), and the plan was not landed.
- **Missed:** `2026-08-30-application-tier-ci-matrix.md`, which this session's work answered
  outright and which was retired in `97da68e` once the harvest noticed it by reading
  `plans.py list`. It names `template/.github/workflows/ci.yml` twice,
  `template/pyproject.toml.jinja` once and `copier.yml` once. The session edited all three, so it
  named three touched files, but none of them three times.

## Evidence

scaffoldapy session `81492b4f-e6bc-4577-8d01-412b3ff4e7a9`, harvest boundary
`2026-09-28T18:23:47+03:00`. The missed plan's text is recoverable with
`git show 97da68e~1:plans/2026-08-30-application-tier-ci-matrix.md`.

## Recommended direction

Count distinct touched files named, not mentions of one file. A plan naming three or more files this
session wrote is a stronger landing signal than one naming a single file three times, and it is the
shape of a design plan, which lists what it will change. Keep the per-file fold for central files.
Add both plans as fixtures: this one must list, and the conftest one should rank below it or drop.
