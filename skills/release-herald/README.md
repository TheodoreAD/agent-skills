# release-herald

Drafts release notes from every PR since the last release, action items first.

A release page usually ends up as one of two things. Either it's GitHub's generated list of PR
titles, or it's a compare link and nothing else. Neither answers the reader's first question: do I
have to change anything to upgrade? The material for a good answer is usually already there, in PR
descriptions and commit messages. Nobody has gathered it and turned it into something a user can act
on.

release-herald gives your agent a script that collects the whole change set through `gh` and grades
how much the descriptions actually say. The agent then writes the notes the way the best-run
projects do: what users must change first, then highlights with usage, then everything else.

## What you get

- **A change set collected without git.** Every merged PR and direct commit between two tags, read
  through `gh` on github.com or a GitHub Enterprise Server host. The host comes from the
  repository's URL, never from a default.
- **Gitflow handled properly.** A release is found as the merged PR into `main`, even when its
  branch is mis-named. The change set behind it is right whether release PRs are squash-merged or
  merge-committed, and after a hotfix. Trunk repos go through commits.
- **A signal report before any drafting.** PR descriptions and commit messages are graded empty,
  thin, adequate or rich. When half or more are thin, it warns and lists the PRs worth fixing first.
- **Breaking and configuration changes surfaced.** Labels, `!:` titles and "BREAKING CHANGE" text
  are flagged, and so is any change to a file that counts as user-facing surface. Those files' diffs
  are included, so a renamed key or a changed default gets noticed.
- **A notes template.** An overview ending in an upgrade verdict, then Action required (breaking,
  configuration, deprecations, security), Highlights with usage and a docs link, then all changes
  with compact `[#123](url), @user` links.
- **A lint for the draft.** It checks every PR is covered or deliberately dropped, every link uses
  the right host, and no section is left empty.
- **Artifacts from your release workflows.** Packages, images and charts, on any registry, JFrog and
  internal ones included. What the workflows cannot say is asked once and kept.
- **A draft GitHub release, only when you ask.** It is never published live unless you say so, and
  it never creates a tag.

## What it looks like

Real output, against a test repository whose PRs carry only boilerplate descriptions:

```
$ herald.py collect --repo github.com/TheodoreAD/repo-tasks-gitflow-twin --tag v0.11.0
range:     v0.10.2 → v0.11.0 (minor)
flow:      gitflow — branch 'develop' exists
base:      gitflow: previous tag (the smaller of 2 comparisons, 8 commits)
commits:   8, 75% mapped to PRs; source prs
items:     2 kept, 5 excluded, 0 dependency PRs
quality:   items empty 0, thin 2, adequate 0, rich 0
           PR descriptions empty 0, thin 2, adequate 0, rich 0
           commit messages empty 3, thin 5, adequate 0, rich 0
WARNING:   low signal — 100% of kept items have thin or empty descriptions.
           Tell the user before drafting; these are the ones to enrich first:
           #38 Feature: twin-511ce738 https://github.com/TheodoreAD/repo-tasks-gitflow-twin/pull/38
           #39 Feature: twin-511ce738 https://github.com/TheodoreAD/repo-tasks-gitflow-twin/pull/39
```

The 5 excluded are the back-merge PRs and version bumps. On a trunk repository that pushes straight
to `main` with full commit bodies, the same command reads very differently:

```
$ herald.py collect --repo https://github.com/TheodoreAD/repo-tasks --tag v0.6.0
range:     v0.5.0 → v0.6.0 (minor)
flow:      trunk — no 'develop' branch
commits:   42, 0% mapped to PRs; source commits
items:     15 kept, 27 excluded, 0 dependency PRs
quality:   items empty 0, thin 0, adequate 2, rich 13
review:    breaking or surface signals on 14c0ff9, 069f3d6
```

## Why it is shaped this way

The section order and the per-item rules come from a survey of 21 projects' release notes and their
writing guides: Kubernetes, Django, uv, ruff, Electron, Rust, Node, Go, Keep a Changelog 2.0 and
others.

- Every well-run project puts what the reader must act on first.
- uv's "Previously… Now… To migrate… You cannot opt out" is the model for a breaking-change entry.
- No surveyed project puts "how to use" at the end. They all attach usage to the feature, near the
  top, so Highlights is where it goes.

## What it can't do

- It drafts from what PRs and commits say. When those are thin, the notes are thin, and it says so
  rather than guessing.
- Whether a change is breaking is decided by reading the evidence, not by the script.
- It does not read package registries. An artifact's destination comes from the workflows and from
  you.
- It never cuts, bumps, tags or pushes anything. That stays with your release flow.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill release-herald
```

Then ask: "write the release notes for v2.1", "what changed since the last release that users need
to update in their config?", "create the v3.0.0 release on our GHES instance as a draft".

Needs Python 3.11 or newer and `gh`, logged in for the repository's host.

No install at all: [`references/prompt.md`](references/prompt.md) is the whole procedure as one
prompt you can paste into any agent that has `gh`.

## What it touches

- It reads the repository through `gh`: tags, compare ranges, PRs, the diffs of user-facing files,
  workflows, runs and deployments. It never runs `git`.
- It writes only its own config, cache and drafts, under `~/.config`, `~/.cache` and
  `~/.local/state` (`release-herald/`) on every OS.
- It creates a GitHub release only through `publish`, which you ask for, and as a draft by default.
- The complete list is in [`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/research.md`](references/research.md): the survey, the `gh` and API behaviour every
  step relies on, and the gitflow range argument.
- [`references/prompt.md`](references/prompt.md): the standalone prompt.
