# Why release-herald is shaped this way

Research done 2026-11-08 before any code was written. It ran as three passes:

- how well-run projects structure release notes
- how `gh` and the GitHub API behave on github.com and on Enterprise Server
- how a release's artifacts can be discovered without reading every registry

Evidence came from repository clones (`$RESEARCH_HOME/repos/…`) and from published release bodies
read with `gh release view`. No web page was the source of a claim below.

## The structure of the notes

21 projects were surveyed.

- **Clones**: Kubernetes (`sig-release` and the contributor guide), Django `docs/releases`, uv,
  ruff, pydantic, Electron, Rust (`RELEASES.md` and the blog), Node, Go `doc/next`, FastAPI, Keep a
  Changelog 2.0, changesets, towncrier, semantic-release, release-please, release-drafter, GitHub's
  docs.
- **Published release bodies, via `gh`**: gh, Helm, Next.js and Terraform.

**What users must act on comes first, everywhere it is done well.**

- Kubernetes heads it "Urgent Upgrade Notes — (No, really, you MUST read this before you upgrade)".
- uv, ruff and Electron open with breaking changes.
- release-please emits `⚠ BREAKING CHANGES` before features.
- GitHub's own `release.yml` example lists "Breaking Changes" first.
- Keep a Changelog 2.0 makes the order a rule: _"Ordering by urgency puts what a reader must act on
  above what is only good to know."_ It dissents in one respect: in a changelog file it marks breaks
  inline rather than collecting them. That is why the template does both — a section at the top, and
  a **Breaking:** marker repeated in place.

**uv's breaking-change entry is the best template found.** Each entry has a bold title and the PR
link, then _Previously … Now …_, who is affected, how to migrate, and whether you can opt out. From
uv 0.13.0:

> Previously, uv split values passed to `--constraint`… on spaces, even when quoted. Now, each value
> is treated as a single path… You cannot opt out of this behavior. Repeat the option to provide
> multiple files.

The same release opens with an upgrade verdict, _"We expect most users to be able to upgrade without
making changes."_ That is why the overview always ends with one.

**Deprecations always name a removal and a replacement.**

- Electron: _"…deprecated and will be removed in Electron 46… Use the asynchronous methods
  instead."_
- The Kubernetes guide: _"…deprecated since v1.14, will be removed in v1.18."_
- Node: DEP ids.
- Go: `GODEBUG` windows of at least two years.
- Django: a written timeline.

**No project has a trailing "how to use" section.** gh 2.103.0, Django, Rust, Node and pydantic all
put usage under a per-feature heading near the top: a sentence, a snippet, a docs link. The user's
first sketch had "how to use the new features" after the PR list. Moved into Highlights 2026-11-08,
with the user's agreement, because readers skim from the top and stop.

**Noise is dropped by the curated projects and kept by the generated ones.**

- uv ignores `internal*` labels.
- The Kubernetes guide excludes tests and build changes.
- Keep a Changelog 2.0 caps itself at six types and calls dependencies and internals usually not
  notable.
- GitHub's generated notes keep everything, which is what makes gh's own notes noisy.

**Size scales with the version delta.**

- Patch: no overview or one line, fixes only (uv 0.13.7, Rust 1.99.1, Django 6.1.3).
- Minor: one to three sentences.
- Major: a paragraph of themes.
- Keep a Changelog: _"a sentence or two… skip it otherwise."_

**The drafting brief already exists, written for machines.** Keep a Changelog 2.0:

> machines can draft, but humans curate… summarize notable, user-facing changes; do not paste a git
> log; sort each change into one of the six types; explain the reason in the text; mark breaking
> changes; and remove anything not worth reading.

ruff and uv's CONTRIBUTING files call the same step "editorialize". The Kubernetes guide's per-note
contents are the checklist behind "name the exact thing":

> An indicator if there is user Action required… The name of the affected API or configuration
> fields, CLI commands/flags… A link to relevant user documentation.

Its style rule is _"Write your release notes in the past tense."_ Past tense was chosen with the
user 2026-11-08, over uv and ruff's imperative.

## `gh` and the API, on any host

Read from `cli/cli`, `cli/go-gh` and `github/docs`, and checked live against public repositories.

**`gh api` does not follow the repository's host.** It uses the default host — `GH_HOST`, else the
only configured host, else `github.com` — unless `--hostname` is passed (`pkg/cmd/api/api.go`
417-421; `RepoHost` appears nowhere in that package). In a GHES checkout, on a machine logged in to
both hosts, `gh api repos/{owner}/{repo}` therefore talks to github.com. So every API call here
passes `--hostname`, and every repository command passes `-R HOST/OWNER/REPO`.

`-R` has a second effect. **With `-R`, `gh release create` skips every local git call**: tag
detection, previous-tag detection, the changelog range (`create.go` 295-356). That is the "never
touch git" path, made explicit.

`gh repo view` ignores `GH_REPO`, but its positional `HOST/OWNER/REPO` form works, and `--json url`
carries the host. That is the one call that resolves the repository, and with no argument `gh` reads
the remote itself.

**Changes without git.** release-drafter's algorithm (`packages/github-adapter/src/index.ts`
132-225):

1. A paginated REST compare. Unpaginated it is capped at 250 commits. The file list appears only on
   page 1, capped at 300.
2. GraphQL hydration of `associatedPullRequests`.
3. A dedupe by PR, keeping merged PRs into this repository.

Its own comment explains the REST step: _"GraphQL Ref.compare cannot resolve all comparisons that
use arbitrary SHAs, tags, or non-linear histories."_ Live on uv `0.13.6…0.13.7`, one query returned
52 commits with their PRs, labels, files and linked issues, at a cost of 1. Every field used exists
in the GHES 3.17–3.22 schemas.

**`#123` autolinks in release bodies, issues and PRs, but not in committed files.** github/docs,
`autolinked-references-and-urls.md`: _"Autolinked references are not created in wikis or files in a
repository."_ A `#123` that renders on the release page is plain text once copied into
`CHANGELOG.md`. So links are explicit, `[#123](url)`. Their text stays `#123`, compact as the user
asked. A bare `@login` in a release body adds that person to the release's Contributors avatar list.

**`generate-notes` was considered and is not used as the source.** It is one title-only line per PR,
categorised by labels, with an undocumented choice of previous tag. In a gitflow repository whose
release PRs are squash-merged, it lists the release PR and nothing behind it, because it follows tag
ancestry.

## The gitflow range

The primary target is gitflow with squash-merged feature PRs. `repo-tasks`' own model is: features
into `develop`; `release/*` and `hotfix/*` finished by a PR into `main`; the tag on `main`; a
`sync/<tag>` PR back into `develop`. Its twin repository exercised the release PR both squash-merged
and merge-committed.

When the release PR is squash-merged, `main` never contains `develop`'s commits, so
`compare/PREV_TAG...TAG` either shows one commit (the squash) or, from the release branch's tip,
everything since the beginning of history. Expanding the release PR's own commit list fails the same
way, because GitHub lists commits in the head that are not reachable from the base.

The comparison that is right from the previous release PR's branch tip is wrong for a hotfix, which
branches off `main`. Each candidate is a superset of the true set, so the script takes the smaller
`ahead_by`. The release PR is identified by its base, not its branch name — asked for explicitly
2026-11-08, so a release manager's mis-named branch is still found.

## Artifacts

**Artifacts are found from the workflows, not from the registries** — asked for explicitly
2026-11-08: _"they could be in jfrog artifactory or other corp artifact repositories. don't get hung
up if reading them outright deterministically is hard."_

The clues were read from each action's own `action.yml` and from real release workflows (uv, zizmor,
act, actionlint, git-cliff, helm, cli/cli). The best single clue is `jobs.<id>.environment.url`.
Runtime confirmation came from the previous tag's deployments: their statuses' `environment_url`
gave `https://pypi.org/p/zizmor` with a link to the exact job.

The limits are stated rather than worked around:

- Secrets are never readable. Helm's destination is entirely in secrets.
- A task runner's publish step names no destination.
- Matrix and dynamic tags cannot be resolved statically.
- Runs and logs expire after 90 days.

Each of those ends in a question to the user, asked once and kept.

## Where its files live

`~/.config`, `~/.cache` and `~/.local/state` on every OS, Windows included. Decided by the user
2026-11-08 so that one backup covers every machine; `skill-authoring-taudelta` carries the rule
corpus-wide since then.

The config is keyed by the repository's URL on its host, never by a working-tree path. A linked
worktree, a second clone and a session outside any checkout must all find the same answer.
