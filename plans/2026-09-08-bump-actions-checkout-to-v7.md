---
status: landed
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

[DECISION: **`tests-windows.yml` needed nothing beyond the version bump.** The reasoning held and
now has a green run behind it — the Windows job passed on `@v7` in run `34238932918`, 2026-09-08.]

[DECISION: **plain tag.** Confirmed by reading the two workflows rather than by carrying the family
default across: neither declares `id-token`, neither is a publish job, and both checkouts already
set `persist-credentials: false`. There is no credential-bearing job here to weigh against the
recorded family decision that pinning without dependabot means pins that rot.]

## What happened

Done 2026-09-08 in `450cf68`, exactly the two one-line edits, pushed and green on both jobs.
`v7.0.1` was re-resolved at the time of the change and was still current.

The confirmation the plan asked for: `gh api .../annotations` on the CI job returns **0**, where the
same query on the previous run returned the Node 20 deprecation notice. That was the whole point —
the annotation is invisible from a pass/fail signal, so a green badge is not evidence either way.

## Migrated to

- **The three majors' analysis and why none of them reaches these jobs** -> the commit message of
  `450cf68`. Deliberately not copied into a docs file: it is two lines of YAML whose reasoning is
  about this repo's own jobs at this moment, and `git log`/`git blame` on the changed line is
  precisely the question a future reader arrives with. In this repo family `git log` is the channel
  rather than the convenient record, because parallel sessions share one working tree.
- **The scope-mistake finding** — that this repo was listed as blocked on a `repo-tasks` consumer
  sweep while not being a `repo-tasks` consumer at all, which is why nothing reached it for eleven
  days -> `github.com-personal/repo-tasks/2026-09-08-node20-blocker-cleared-by-agent-skills.md` in
  the store, committed `16e494e`. That is the plan that has to survive this one, because the wrong
  status line is still written down over there.
- **The `rg --hidden` pitfall** -> restated verbatim in that same filed plan, so it outlives this
  file. Not migrated into a skill or `~/AGENTS.md` from here: the fd/rg hidden-path question is
  being worked separately and elsewhere, and a second copy written from this side would read as
  authoritative while diverging.

Deliberately not migrated: the upstream SHA `3d3c42e5aac5ba805825da76410c181273ba90b1`, which is a
code contract this repo chose not to adopt, and the `@v4`/`@v7` per-repo state table, which was true
on 2026-09-08 and is a verification log rather than a decision.
