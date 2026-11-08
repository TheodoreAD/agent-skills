# Release notes prompt — standalone

This is the whole `release-herald` procedure as one prompt, for anyone who has not installed the
skill. Paste everything below the line into an agent that can run `gh` (authenticated against the
host the repository lives on), fill in the inputs, and it will draft the release notes the same way
the skill does. The skill's script does steps 1–8 deterministically; here the agent does them by
hand, so they are spelled out in full.

---

You are drafting the GitHub release notes for one release of one repository. The notes are for the
people who **use** what this repository ships, not for its contributors: lead with what they must
act on, then what is new for them, then the full list. Draft from what the pull requests and commits
actually say; never invent a change, a migration step or a version number.

## Inputs

- `REPO` — the repository, as `HOST/OWNER/REPO` or its web URL (`https://HOST/OWNER/REPO`). If
  omitted, use the repository of the current directory (step 1).
- `TAG` — the release's tag. It must already exist on the remote.
- `PREVIOUS_TAG` — optional; derive it if omitted (step 2).
- `FLOW` — `gitflow`, `trunk`, or omitted to detect (step 3).
- `MODE` — `markdown` (default): output the notes and stop. `draft-release`: also create the release
  as a **draft** (step 12). Never publish a release live unless told to in so many words.

## Hard rules

- **Never run `git`.** Everything goes through `gh`, which talks to the hosting platform's API.
- **Never assume `github.com`.** The repository may be on GitHub Enterprise Server. Resolve the host
  once in step 1, then pass `-R HOST/OWNER/REPO` to every `gh` repository command and
  `--hostname HOST` to every `gh api` call. `gh api` does **not** follow the repository's host on
  its own — it talks to `gh`'s default host, which is `github.com` for anyone logged in to both.
- Build every link from the repository's own URL (`https://HOST/OWNER/REPO/...`). Never type a host.
- Never create, move or delete a tag or a branch.

## 1. Resolve the repository

```shell
gh repo view HOST/OWNER/REPO --json url,nameWithOwner,defaultBranchRef
gh repo view --json url,nameWithOwner,defaultBranchRef        # REPO omitted: the current directory
```

`HOST` is the host part of `url`. Use `url` as the base of every link below.

## 2. The range

List the tags and pick the previous release by version, not by date:

```shell
gh api --hostname HOST --paginate "repos/OWNER/REPO/tags?per_page=100" --jq '.[].name'
```

- Consider only tags with the same prefix as `TAG` (`v`, `group-v`, …) that parse as versions.
- For a **final** `TAG` (`v1.2.0`), `PREVIOUS_TAG` is the highest **final** version below it —
  release candidates in between are skipped, so the notes cover the whole release.
- For a **pre-release** `TAG` (`v1.2.0rc2`, `v1.2.0-rc.2`), it is the highest version of any kind
  below it, so testers see what changed since the last candidate.
- The version delta (major, minor, patch, pre-release) sets the size of the notes in step 10.

Resolve both tags to commits:

```shell
gh api --hostname HOST repos/OWNER/REPO/commits/TAG --jq .sha
gh api --hostname HOST repos/OWNER/REPO/commits/PREVIOUS_TAG --jq .sha
```

## 3. The flow

If `FLOW` is given, use it. Otherwise the repository is **gitflow** when it has an integration
branch named `develop`, and **trunk** when it does not:

```shell
gh api --hostname HOST repos/OWNER/REPO/branches/develop --jq .name
```

In gitflow, the **production branch** is the default branch, unless the default branch is `develop`
itself — then it is `main` (or `master`, whichever exists).

## 4. The change set

Look up the pull requests associated with a commit with this query (used for the tag commits here
and for every commit in step 5):

```shell
gh api graphql --hostname HOST -f owner=OWNER -f name=REPO -f oid=SHA -f query='
query($owner: String!, $name: String!, $oid: GitObjectID!) {
  repository(owner: $owner, name: $name) {
    object(oid: $oid) {
      ... on Commit {
        associatedPullRequests(first: 10) {
          nodes {
            number
            merged
            baseRefName
            headRefName
            headRefOid
            mergeCommit { oid }
          }
        }
      }
    }
  }
}'
```

**Trunk:** the change set is every commit between the two tags:

```shell
gh api --hostname HOST "repos/OWNER/REPO/compare/PREVIOUS_TAG...TAG?per_page=100&page=1" \
  --jq '{ahead_by, total_commits, commits: [.commits[] | {sha, message: .commit.message, parents: (.parents | length), author: .author.login}]}'
```

Keep requesting `page=2`, `page=3`, … until you have `total_commits` commits.

**Gitflow:** a release is a pull request into the production branch — a _release PR_. Identify it by
its **base** (the production branch), never by its branch name: a release manager working by hand
can name the branch `release/1.2`, `rel-1.2` or anything else, and it is still the release PR.

1. Find the release PR for `TAG`: among the PRs associated with the tag commit, the merged one whose
   base is the production branch and whose `mergeCommit.oid` is the tag commit. Do the same for
   `PREVIOUS_TAG`. Note each one's `headRefOid` — the tip of its release branch.
2. The release PR is a container, not a change. The changes are the commits behind it, and there are
   two candidate starting points:
   - `PREVIOUS_TAG`
   - the previous release PR's `headRefOid`

   with the current release PR's `headRefOid` as the end (the tag commit, if no release PR was
   found). Compare each candidate start with that end and **use the one with the smaller
   `ahead_by`**. Each candidate covers at least everything in the release, so the smaller one is the
   closer fit. This matters when the release PR is squash-merged into the production branch: the
   production branch then never contains the integration branch's commits, so a comparison from the
   previous tag reaches back to the beginning of the repository. For a release PR that was
   merge-committed, the two agree. For a hotfix branched off the production branch, the previous tag
   is the closer one.
3. Paginate the chosen comparison as in the trunk case.

Keep the release PR's own description: it is release-level context for the overview.

## 5. Commits → pull requests

For every commit in the change set, run the associated-PR query from step 4 and keep the PRs that
are merged, into this repository, and are not the release PR itself.

- When several PRs qualify, prefer the one whose `mergeCommit.oid` equals the commit. That is the
  squash-merge case: the commit _is_ the PR.
- Several commits mapping to one PR is a merge-committed or rebased PR: it is one item.
- A commit with no PR is a **direct commit**, and it is an item of its own.

Then fetch each PR's details. Batch several PRs into one query with aliases (`pr1: pullRequest(…)`,
`pr2: …`):

```shell
gh api graphql --hostname HOST -f owner=OWNER -f name=REPO -F number=N -f query='
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      title
      body
      url
      merged
      mergedAt
      baseRefName
      headRefName
      headRefOid
      author { login }
      mergeCommit { oid }
      labels(first: 30) { nodes { name } }
      files(first: 100) { totalCount nodes { path additions deletions changeType } }
      closingIssuesReferences(first: 10) { nodes { number title url } }
      commits(first: 100) { totalCount nodes { commit { oid messageHeadline messageBody } } }
    }
  }
}'
```

For a PR that was merge-committed rather than squashed, its individual commit messages are part of
the record. Read them alongside the description, not instead of it.

## 6. What to leave out

Exclude, and list for the user what you excluded and why:

- back-merge PRs (`sync/*`, a production-into-integration merge)
- version-bump commits ("Bump version: …", "chore(release): …")
- merge commits with no PR of their own
- PRs or commits that change only CI, tests, build plumbing, or planning documents (for example a
  `plans:` title prefix)
- PRs labelled `internal`, `skip-changelog` or `no-release-note`
- the repository's `.github/release.yml` `exclude` labels and authors, if it has one

Bot dependency PRs (`dependabot[bot]`, `renovate[bot]`) collapse into one "Dependencies" line,
unless a bump changes something users see.

## 7. Signals per item

Mark each item with what you can see, then decide what it means:

- **Surface** — it changes files users depend on: configuration files and their schema, settings
  modules, public API modules, CLI definitions, OpenAPI/JSON schemas, database migrations, chart
  `values.yaml`, `.env.example`. For those files only, read the diff:

  ```shell
  gh api --hostname HOST --paginate "repos/OWNER/REPO/pulls/N/files?per_page=100" --jq '.[] | {filename, patch}'
  gh api --hostname HOST repos/OWNER/REPO/commits/SHA --jq '.files[] | {filename, patch}'    # a direct commit
  ```

  A removed or renamed key, a changed default, or a new required setting is a configuration change.
  A removed or renamed function, parameter or flag is an API change.
- **Breaking** — a `breaking`, `breaking-change` or `semver-major` label; `!:` in a conventional
  title; `BREAKING CHANGE` or "action required" in the description; or a surface change that makes
  existing usage fail.
- **Deprecation** — the description or diff deprecates something.
- **Security** — a CVE or GHSA id, or a `security` label.
- **Docs** — documentation files changed, or the description links to them. That link goes in the
  feature's "See …" line.

## 8. How much there is to go on — tell the user before drafting

For each item, take the text the notes depend on: the PR description, or the commit body for a
direct commit. For a squash-merged PR, also take its squash commit message. Strip HTML comments,
headings, checkbox lines, and lines that are only a link, then count the words:

| grade    | words      |
| -------- | ---------- |
| empty    | 0          |
| thin     | 1–14       |
| adequate | 15–59      |
| rich     | 60 or more |

Report the count per grade to the user. When **half or more** of the items you keep are thin or
empty, warn plainly that there is little to go on, and list those items with their links. The user
may then improve those PR descriptions first, or tell you to proceed. When a quarter or more are
thin, say so in one line.

For a thin item, write its entry from its title and diff only, and tell the user which entries those
are. Never pad a thin entry with guesses.

## 9. Artifacts

What the release produces: packages, images, charts, binaries. Look in `.github/workflows/*.yml` for
workflows triggered by tags, releases or a manual dispatch:

```shell
gh api --hostname HOST repos/OWNER/REPO/contents/.github/workflows --jq '.[].path'
gh api --hostname HOST repos/OWNER/REPO/contents/PATH -H 'Accept: application/vnd.github.raw'
```

Clues to a destination, which may be any registry (not only GitHub's):

- a job's `environment: url:`
- a login action's `registry:`
- a metadata action's `images:`
- `pypi-publish`'s `repository-url`
- `uv publish --publish-url` / `twine upload --repository-url`
- `setup-node`'s `registry-url` / `npm publish --registry`
- `JF_URL` with `jf rt upload` / `jf docker push`
- `docker push`
- `helm push oci://…`
- `mvn deploy`
- `aws s3 cp` / `gsutil cp` / `az storage`
- `gh release upload` and release actions' `files:`

To see what actually ran, check the previous tag's run and deployment:

```shell
gh api --hostname HOST "repos/OWNER/REPO/actions/runs?head_sha=SHA" --jq '.workflow_runs[] | {id, name, path, event, conclusion}'
gh api --hostname HOST "repos/OWNER/REPO/deployments?sha=SHA" --jq '.[] | {id, environment}'
```

A destination held in a secret cannot be read. Ask the user rather than guessing.

## 10. Draft the notes

Size by the version delta. Omit every section that would be empty.

```markdown
<Overview: what users get from this release, in user terms. Patch: one line at most. Minor: one to
three sentences. Major: one short paragraph of themes.> <Upgrade verdict, always: "No action is
required to upgrade." or "N changes require action — see below.">

## ⚠ Action required

### Breaking changes

**<What changed, in a few words>** ([#N](URL/pull/N)) Previously, <old behaviour>. Now,
<new behaviour>. This affects <who / which usage>. To migrate, <step, or a before/after snippet>.
<How to opt out, or "There is no opt-out.">

### Configuration changes

- `old.key` → `new.key`; `other.key` now defaults to `X` (was `Y`). ([#N](URL/pull/N))

### Deprecations

- `<thing>` is deprecated and will be removed in <version>. Use `<replacement>` instead.
  ([#N](URL/pull/N))

### Security

- <CVE/GHSA id>: <one line>. ([#N](URL/pull/N))

## Highlights

### <Feature name>

<One to three sentences on what it does for the user.> <Minimal usage, e.g. "Pass `max_retries=` to
`submit()` to stop retrying after a fixed number of attempts."> See
[docs/retries.md](URL/blob/TAG/docs/retries.md).

## All changes

### Features

- Added <what> to <where> ([#N](URL/pull/N), @login)
  - <nested detail only where a reader needs it>

### Fixes

- Fixed <what the user saw> ([#N](URL/pull/N), @login)

### Performance / Documentation / Dependencies

- …

## Artifacts

- <kind>: <name> <version> — <destination link>

**Full Changelog**: [PREVIOUS_TAG...TAG](URL/compare/PREVIOUS_TAG...TAG)
```

Writing rules:

- **Past tense, user's point of view.** Write "Added `max_retries` to `submit()`", not "Add retry
  param" or "Refactored the submit loop". Rewrite PR titles; never paste them, and never paste a
  commit log.
- **One entry per PR.** Link it compactly: the link text is `#N` and nothing else, with the author
  as a bare `@login` after it. `@login` renders as a link on the host and adds the author to the
  release's contributor list. A direct commit is linked by its short sha:
  `([abc1234](URL/commit/SHA))`.
- **Use explicit links, never bare `#N`.** A bare `#N` autolinks in a release body, but not in a
  `CHANGELOG.md` or anywhere the text is copied to.
- **Action required comes first, and it is repeated in place.** Every breaking or configuration item
  also appears in "All changes" with a leading **Breaking:** marker.
- **Name the exact thing**: the key, flag, function, parameter, endpoint or environment variable, in
  backticks.
- A deprecation names its removal version. If the PR does not say, write "in a future release" and
  tell the user it needs a version.
- **Highlights** are for minor and major releases only: one to three headline features, each with
  usage a reader can copy and a link to the documentation at `TAG`. A patch release has none.
- Group "All changes" by type: Features, Fixes, Performance, Documentation, Dependencies. Within a
  type, an area prefix (`**cli**:`) is fine when the project is large.
- Use the gitflow release PR's description and the overall diff for the overview. Never put
  contributor-facing detail there.

## 11. Check before handing over

- Every item you kept is referenced, and everything you dropped is in your list for the user.
- Every link uses the repository's own host and `OWNER/REPO`.
- No section is empty. The sections appear in the template's order.
- Every breaking or configuration item is under "Action required" and repeated in "All changes".
- The compare link is present.

## 12. Output

Output the notes as markdown, followed by a short report for the user:

- the range used and why
- the flow
- the quality counts and any low-signal warning
- the thin entries
- what was excluded
- any deprecation missing a version
- any artifact you could not place

In `MODE=draft-release` only, and only after the user has seen the notes, save them to a file and
create a **draft**. Stop if a release for `TAG` already exists.

```shell
gh release view TAG -R HOST/OWNER/REPO --json tagName          # must fail: no release yet
gh release create TAG -R HOST/OWNER/REPO --verify-tag --draft --title TAG -F notes.md
```

`--verify-tag` refuses when the tag is not on the remote, rather than letting `gh` create it.
Publishing the draft is the user's separate decision.
