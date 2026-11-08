---
name: release-herald
description: "Use when writing the release notes for your own repository's release — drafting the GitHub release for a tag from every pull request and commit since the previous release, working out what users must change (breaking, API and configuration changes, deprecations), listing what the release publishes (packages, images, charts, on any registry), or creating that GitHub release as a draft through gh, on github.com or GitHub Enterprise Server. Handles gitflow (squash-merged feature PRs, release and hotfix PRs into main) and trunk repos, and says when PR descriptions or commit messages are too thin to write from. Not for judging someone else's package or its release cadence, and never cuts, bumps, tags or pushes anything."
license: MIT
compatibility: "Python 3.11+ (stdlib only) and gh, authenticated for the repository's host — github.com or GitHub Enterprise Server. Reaches that host's REST and GraphQL APIs through gh only; never runs git. Writes under ~/.config, ~/.cache and ~/.local/state (release-herald/; the XDG variables are honoured) and creates a GitHub release only when asked, as a draft by default."
---

# A release users can act on

Release notes are for the people who **use** what a repository ships. They lead with what those
people must change, then what is new for them, then everything else. This skill collects the whole
change set between two releases through `gh`, without touching git. It grades how much the PR
descriptions and commit messages actually say, and hands you a digest to write from. Writing is the
part left to you.

Two rules hold throughout. **Draft from what the pull requests and commits say, and never invent a
change, a migration step or a version.** **Never tag, bump, push or publish on your own
initiative**: the default output is markdown, and creating the release is a separate step the user
asks for.

## What this skill reads, runs and writes

- **Reads**: through `gh`, the repository's tags, commits, compare ranges, pull requests (title,
  body, labels, files, commits, linked issues), file diffs for the files that count as user-facing
  surface, `.github/workflows/*`, Actions variables, runs, jobs and deployments, and its file tree.
  Locally, its own config, cache and drafts.
- **Runs**: `gh repo view`, `gh api` (REST and GraphQL, always with `--hostname`), and
  `gh release view|create|edit` (always with `-R HOST/OWNER/REPO`). Never `git`. With no `--repo`,
  `gh` itself reads the current directory's remote, once, to name the repository.
- **Writes**:
  - `setup --accept` writes the per-repository config at
    `~/.config/release-herald/repos/<host>/<owner>/<repo>.toml`.
  - `collect` writes the collected JSON and the digest to `~/.cache/release-herald/…`.
  - `setup` writes its proposal to `~/.local/state/release-herald/…`, where drafts also go.
  - `publish` creates a GitHub release: a **draft** unless `--live`; `--update` replaces an existing
    release's notes. Nothing else changes on the host.
  - Nothing is ever written into the repository's working tree.
- **Network**: the repository's own host only, through `gh`. Package registries are never contacted;
  where an artifact lives is read from the workflows and confirmed by the user.

The paths are the Linux layout **on every OS**, and `$XDG_CONFIG_HOME`, `$XDG_CACHE_HOME` and
`$XDG_STATE_HOME` override them. A repository's config is keyed by its **URL on its host**, never by
a working-tree path, so a worktree, a second clone, or a session outside any checkout all find the
same file.

## Run the script

[`scripts/herald.py`](scripts/herald.py) holds every deterministic step. `S` is this skill's
directory.

```shell
python3 $S/scripts/herald.py repo [--repo HOST/OWNER/REPO]       # host, flow, config path
python3 $S/scripts/herald.py setup                               # first time per repo: a proposal
python3 $S/scripts/herald.py setup --accept <proposal.toml>      # after the user confirms it
python3 $S/scripts/herald.py collect --tag v1.2.0                # change set, quality, digest
python3 $S/scripts/herald.py check <draft.md> --tag v1.2.0 [--dropped 12,15]
python3 $S/scripts/herald.py publish --tag v1.2.0 --notes-file <draft.md>   # a draft release
python3 $S/scripts/herald.py explain                             # how quality is graded
```

`--repo` takes `HOST/OWNER/REPO`, `OWNER/REPO` or any URL; without it, the current directory's
repository. **Pass it whenever the user names a repository or a host.** A corporate GHES repository
needs nothing else, because the host comes from the repository's URL and no host is written into the
script. Every subcommand takes `--json`.

## The procedure

1. **Resolve.** Run `repo` and check the host, the repository and the flow it reports. If any of
   them is wrong, stop and ask.
2. **First time for this repository, or `collect` says the workflows changed: set up.** `setup`
   proposes three things:
   - **the flow** — gitflow when a `develop` branch exists
   - **the surface** — which files count as API or configuration
   - **the artifacts** — read from the release workflows: a job's `environment.url`, registry
     logins, `pypi-publish`, `uv`/`twine`/`npm publish`, JFrog `jf rt upload`/`jf docker push`,
     `docker push`, `helm push`, `aws s3 cp`, release actions, task-runner publish steps — then
     checked against the previous release's runs and deployments

   **Show the proposal to the user and have them confirm or correct it.** A destination held in a
   secret, or published by a task runner such as `inv dist.publish`, cannot be read — ask for it.
   Then `setup --accept`. Do not spend effort reading registries to verify a destination; the user's
   answer is the source.
3. **Collect.** `collect --tag <tag>` picks the previous release by version: a final release
   compares against the previous final (release candidates in between are skipped), a pre-release
   against the previous tag of any kind. `--previous` overrides. Read its summary.
4. **Report the signal before drafting, every time.** Tell the user the quality counts — items, PR
   descriptions and commit messages, each graded empty / thin / adequate / rich. On a **low-signal
   warning** (half or more of the kept items thin or empty), say plainly that there is little to go
   on and list the weakest items with their links. Let the user choose: enrich those PRs first, or
   proceed, with those entries written from title and diff only.
5. **Draft** from the digest, into the path `collect` printed (`draft to:`), following the template
   below.
6. **Check.** `check <draft> --tag <tag> --dropped <items you left out on purpose>`. Fix every
   error; read every warning.
7. **Show the user the notes** together with:
   - the range and flow used
   - what was excluded, and why
   - which entries are thin
   - any deprecation without a removal version
   - any artifact without a confirmed destination
8. **Only when asked, create the release**: `publish --tag <tag> --notes-file <draft>` makes a
   **draft**. `--live` publishes, and needs the user's words saying so. `--update` replaces the
   notes of an existing release. `publish` refuses when the tag is not on the remote — it never
   creates a tag — and when a release already exists without `--update`. It re-runs `check` first.

## How the change set is found

**Trunk**: every commit between the two tags. Each is mapped to its merged pull request, and commits
with no PR are kept as **direct commits**.

**Gitflow**:

- A release is a merged pull request **into the production branch**. It is identified by its base,
  so a release branch named by hand, `rel-1.2` say, is found as surely as `release/1.2`. That PR is
  a container. Its changes are the PRs behind its commits, and its own description becomes
  release-level context for the overview.
- Two comparisons are tried: from the previous tag, and from the previous release PR's branch tip.
  The one with fewer commits is used. When release PRs are squash-merged into `main`, the previous
  tag reaches back to the start of history and the previous release's tip does not. For a hotfix it
  is the other way round. For merge-committed releases the two agree.
- Back-merges (`sync/*`), version bumps and merge commits are excluded and listed.

**Squash-merged PRs** contribute their description and their squash commit message.
**Merge-committed PRs** contribute their description **and** their individual commit messages. Read
both. In commits mode (`--source commits`, or automatic when most commits have no PR), every commit
is its own entry.

Per item, the digest marks **signals**, which are evidence, not verdicts:

- **BREAKING?** — a label, a `!:` title, or "BREAKING CHANGE" / "action required" in the text
- **surface** — a changed file matching the repository's surface globs, with that file's diff
  included
- **deprecation**, **security** (a CVE or GHSA id)
- **docs** — the files a "See …" link should point at

Read the surface diffs. A renamed key, a changed default or a removed parameter is a change the user
must act on, whether or not anyone labelled it.

## The notes

```markdown
<Overview: what users get, in their terms. Patch: one line at most. Minor: one to three sentences.
Major: one short paragraph.> <Always: "No action is required to upgrade." or "N changes require
action — see below.">

## ⚠ Action required

### Breaking changes

**<What changed>** ([#N](URL/pull/N)) Previously, <old>. Now, <new>. This affects <who>. To migrate,
<step or snippet>. <Opt-out, or none.>

### Configuration changes

- `old.key` → `new.key`; `x` now defaults to `Y` (was `Z`). ([#N](URL/pull/N))

### Deprecations

- `<thing>` is deprecated and will be removed in <version>. Use `<replacement>` instead.
  ([#N](URL/pull/N))

### Security

- <CVE/GHSA id>: <one line>. ([#N](URL/pull/N))

## Highlights

### <Feature>

<One to three sentences.> <Usage a reader can copy, e.g. "Pass `max_retries=` to `submit()` to stop
retrying after N attempts."> See [docs/retries.md](URL/blob/TAG/docs/retries.md).

## All changes

### Features

- Added <what> to <where> ([#N](URL/pull/N), @login)
  - <nested detail only where a reader needs it>

### Fixes / Performance / Documentation / Dependencies

- …

## Artifacts

- <kind>: <name> <version> — <destination>

**Full Changelog**: [PREV...TAG](URL/compare/PREV...TAG)
```

- **Omit every empty section.** A patch release has no Highlights.
- **Past tense, from the user's side.** Rewrite PR titles into what changed for a user. Never paste
  a title or a commit log.
- **Compact links.** The link text is `#N` and nothing more, followed by the author as a bare
  `@login`. A direct commit is linked by its short sha. Every link is built from the URL the digest
  names as its link base: never a bare `#N`, which links only inside a release body, and never a
  typed host.
- **Action-required items come first and are repeated in place**: each breaking or configuration
  entry also appears under "All changes" with a leading **Breaking:**.
- **Name the exact key, flag, function, parameter, endpoint or environment variable**, in backticks.
- A deprecation names its removal version. If none is given, write "in a future release" and tell
  the user.
- **Highlights** carry usage and a link to the documentation at the tag. That is where "how to use
  the new feature" lives: next to the feature, near the top, where a skimming reader still is.
- Group "All changes" by type. Collapse dependency-bot PRs into one line, unless a bump changes
  something users see.

Why this shape and not another is in [`references/research.md`](references/research.md): 21
projects' release notes, the published writing guides, and the `gh` and API behaviour every step
above relies on.

## Configuration

The proposal `setup` writes is the config, with comments. The keys are:

| key                                       | what it does                                                                                            |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `url`                                     | the repository it belongs to                                                                            |
| `flow`                                    | `gitflow` or `trunk`; delete the key to detect on every run                                             |
| `production_branch`, `integration_branch` | the branch names, when they are not the default branch and `develop`                                    |
| `source`                                  | `auto`, `prs` or `commits`                                                                              |
| `surface`                                 | globs for files whose change is user-facing                                                             |
| `[exclude]`                               | `labels`, `title_prefixes`, `head_patterns`, `internal_paths`, `dependency_authors`                     |
| `[[artifacts]]`                           | `kind`, `name`, `destination` (with `{version}` / `{tag}`), `workflow`, `job`, `evidence`, `confidence` |
| `workflow_digest`                         | what the artifact answer was derived from; a change makes `collect` say so                              |

Edit the file by hand whenever that is quicker than re-running `setup`.

## Without the skill

[`references/prompt.md`](references/prompt.md) is the whole procedure as one prompt: the `gh` and
GraphQL calls, the gitflow rule, the quality rubric and the template. Anyone can paste it into an
agent that has `gh`, without installing anything. Its GraphQL and thresholds are the script's own,
kept identical by a test.
