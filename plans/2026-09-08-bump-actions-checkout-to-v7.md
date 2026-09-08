---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-08T00:00:00Z
---

# `actions/checkout@v4` here is the family's last Node 20 call site

## Context

GitHub deprecated Node 20 for Actions on 2025-09-19 and currently **forces** these steps onto Node
24 rather than failing them, so the whole thing is invisible from a pass/fail signal — every run
stays green while carrying an annotation nobody reads:

```
Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run
on Node.js 24: actions/checkout@v4.
```

The family-wide bump was tracked in `repo-tasks`' `plans/2026-08-28-node20-action-deprecation.md`.
Measured 2026-09-08, **this repo is the only one left**:

| repo                     | state                                                                 |
| ------------------------ | --------------------------------------------------------------------- |
| `repo-tasks`             | `@v7` throughout, plus two `publish.yml` SHA pins at `v7.0.1`         |
| `power-user-linux-setup` | `@v7` throughout, `setup-python@v7`                                   |
| `scaffoldapy`            | `@v7` in its own `ci.yml` and in `template/.github/workflows/`        |
| **`agent-skills`**       | **`@v4`** in `.github/workflows/ci.yml:19` and `tests-windows.yml:31` |

Filed from `repo-tasks` rather than performed, because writing into another repo's working tree is
out — parallel sessions share these checkouts.

**This repo was in that plan's scope by mistake, which is why nothing has reached it.** Its status
read "blocked on the batched consumer sweep reaching `scaffoldapy` and `agent-skills`" — but this
repo is not a `repo-tasks` consumer at all: no `from repo_tasks` in its tasks, no
`bootstrap-repo-tasks.sh`. It needs an action bump, not a sweep, and it has been waiting behind an
ordering that never applied to it. Corrected there 2026-09-08; this plan is the half that has to
happen here.

## Evidence

Session `e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-08. The
distinctive phrase to search that transcript for is "one repo left, and it is not the one the status
says".

The repro is one command:

```shell
rg -n --hidden 'actions/checkout@' .github
```

[PITFALL: `--hidden` is not optional there. `rg` skips dot-directories by default, so a bare
`rg 'actions/checkout@' .` over a repo root returns **nothing** while `.github/workflows/` sits
right there — and an empty result reads exactly like "already on v7". This is the same silent-empty
trap `~/AGENTS.md` documents for `fd`. It cost a wrong answer in the source session before being
caught.]

## What the three majors actually change

Read from upstream release notes in the originating plan rather than assumed, and none of it reaches
this repo — but the reasoning is worth having to hand rather than re-derived:

- **`v5.0.0`** (2025-08-11) — the Node 24 move itself. Declares a minimum runner version of
  `v2.327.1`: irrelevant on GitHub-hosted runners, load-bearing for self-hosted. Both jobs here are
  hosted.
- **`v6.0.0`** (2025-11-20) — persists credentials to a separate file. Relevant only where
  `persist-credentials` or zizmor's `artipacked` is in play.
- **`v7.0.0`** (2026-06-18) — blocks checking out a fork PR under `pull_request_target` and
  `workflow_run`, plus an ESM rewrite. This repo uses neither trigger, and the stricter default is
  the wanted one.

Current upstream is **`v7.0.1`** (2026-07-20), whose SHA was
`3d3c42e5aac5ba805825da76410c181273ba90b1` when resolved 2026-08-28 — worth re-resolving at the time
of the change rather than trusting that line.

## Open questions

[NEEDS CLARIFICATION: does `tests-windows.yml` need anything beyond the version bump? It is the one
workflow in the family running on a Windows runner, and the three majors' notes were all checked
against Linux-hosted jobs. Nothing in them is platform-specific — the runner-version floor is about
self-hosted, not about OS — but that is reasoning rather than a green run, and this is the only
place in the family where it would show.]

[NEEDS CLARIFICATION: plain tag or SHA pin? This repo uses plain tags today and `repo-tasks` pins
only in `publish.yml`, where the job holds `id-token: write` against PyPI. The recorded family
decision is that pinning everywhere without dependabot means pins that rot, and dependabot means a
standing PR stream on repos pushed to directly — so plain tags are the default and nothing here
argues for the exception. Confirm rather than assume, since this repo has no equivalent
credential-bearing job to weigh.]

## Recommended direction

Two one-line edits, `@v4` -> `@v7`, in `.github/workflows/ci.yml` and
`.github/workflows/tests-windows.yml`. Run this repo's own gate, push, and confirm the deprecation
annotation is gone from the next run — `gh run view <id>` shows annotations that a green badge
hides, which is how the whole issue was found in the first place.

That closes the family-wide item, and `repo-tasks`' `plans/2026-08-28-node20-action-deprecation.md`
can then drop its last blocker.
