---
status: idea
updated: 2026-09-10
source_repo: github.com-personal/repo-tasks
source_session: db005386-041e-4f80-acbe-6e944677e6fa.jsonl
source_moment: 2026-09-09T21:08:26Z
source_plan: # reports a fact — nothing to check back with
---

## Context

Both workflows here pin `astral-sh/setup-uv@v9.0.0` while upstream is at `v10.0.1` — two majors
behind, at `.github/workflows/ci.yml:22` and `.github/workflows/tests-windows.yml:34`. Measured
read-only from a `repo-tasks` session on 2026-09-10; nothing in this repo was touched.

It is plain currency drift rather than a deprecation: GitHub annotates neither pin, and both runs
are green. It came to light as the last residue of the family-wide Node 20 sweep, which found that
every `actions/checkout` here is correctly on `@v7` (cleared 2026-09-08 in `450cf68`) and that
`setup-uv` was the thing nobody had looked at.

**This repo can answer the question itself.** Its `tasks.py` is `from repo_tasks import ns`, so
`inv ci.check-actions` is already available — it reports each `uses:` against the action's latest
release, comparing only at the precision the pin states, so `@v9.0.0` against `v10.0.1` is reported
as behind while a bare `@v7` against `v7.0.1` is correctly current.

## Evidence

The measuring session was working in `repo-tasks`, retiring
`plans/2026-08-28-node20-action-deprecation.md`; the sweep that found this is that plan's own
closing check. Command and result, from outside this repo:

```shell
rg -n --hidden -g '*.yml' 'uses:\s*astral-sh/setup-uv' <this repo>/.github
.github/workflows/ci.yml:22:      - uses: astral-sh/setup-uv@v9.0.0
.github/workflows/tests-windows.yml:34:      - uses: astral-sh/setup-uv@v9.0.0
```

No user correction is involved; this is a measurement, not a report of anything going wrong.

## Open questions

[NEEDS CLARIFICATION: does `setup-uv` v10's cache change reach these workflows? v10 disables the
cache under `enable-cache: auto` for `pull_request_target`, `workflow_run` and `release` events, as
cache-poisoning defence. Elsewhere in the family that reached nothing, because no workflow used
those triggers — check the two here rather than assuming it carries over, particularly the Windows
job.]

## Recommended direction

1. `inv ci.check-actions` first, rather than editing from this plan — it reports every action here,
   not only the one that prompted this, and its answer is current on the day it runs.
2. Read v10's release notes against these two workflows before bumping, per the open question. The
   reading is the expensive half of a bump; the edit is two lines.
3. Both sites move together, in one commit — they are the same pin in two files.
