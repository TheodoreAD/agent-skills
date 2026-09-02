---
name: research-library
description: "Use when working with, adding to, or updating the shared cross-project research library at $RESEARCH_HOME (vendor repo clones, reference PDFs/epubs, mirrored docs pages) — before fetching the same material from the web, when cloning a reference repo for a project, or when asked to update/refresh the library. Also owns judging a named third-party package or repo before depending on it: whether it is still maintained, who is actually committing to it, how often it releases on its stable line, whether it ships py.typed, how much test suite is behind it, whether a version cap it carries will hold you back — read from PyPI, the GitHub API and the project's own source rather than from a search summary."
---

# Research library

`$RESEARCH_HOME` (default `~/research`) is a shared, cross-project store for reference material that
shouldn't live inside any single git repo: vendor repo clones, PDFs/epubs, mirrored docs-site
snapshots. It exists to avoid two things: (1) agents reading unvetted third-party content ambiently
just because it happens to sit inside a repo's working tree, and (2) every project re-cloning the
same reference material into its own gitignored folder.

**This skill assumes a library exists.** It is a plain directory — nothing installs it and nothing
but the conventions below depends on the layout. If `$RESEARCH_HOME` is unset and `~/research` does
not exist, say so and offer to create it rather than silently falling back to fetching from the web;
setting `RESEARCH_HOME` in a shell profile is the only setup step.

## Before fetching anything from the web

Check `$RESEARCH_HOME/repos/`, `$RESEARCH_HOME/docs/`, and `$RESEARCH_HOME/pages/` for existing
material on the topic before reaching for WebFetch/WebSearch or cloning a fresh copy. A project's
own `AGENTS.md` may already point at the specific entry relevant to that project.

## Layout

```
$RESEARCH_HOME/
  repos/<host>--<owner>--<repo>/   # shallow git clones
  docs/<file>.pdf|.epub            # downloaded reference docs
  pages/<slug>/                    # mirrored/llms.txt-derived doc site snapshots
  README.md                        # full conventions + rationale
```

## Naming (repos)

Always `<host>--<owner>--<repo>` — every repo, every host, no exceptions, no GitHub special case.
Check the actual `origin` remote rather than assuming from the URL you were given; self-hosted
instances (e.g. `gitlab.gnome.org`) can look like they might be GitHub and aren't.

## Adding an entry

```
git clone --depth 1 <url> "$RESEARCH_HOME/repos/<host>--<owner>--<repo>"
```

Then write that entry's `SOURCE.md` (or a `<file>.source.md` sibling for a flat `docs/` file):

```
url: <repo or docs URL actually fetched from>
kind: repo-clone | llms-txt-mirror | site-mirror
ref: <branch/tag/commit for a repo-clone, or fetch date for a mirror>
fetched: <date>
note: <only when non-obvious — e.g. docs publish from a different branch/repo than what's cloned>
```

## Updating

Refresh every clone under `repos/` to its default branch's latest commit — a shallow fetch and hard
reset, since these are disposable reference clones, not working copies with local commits to
preserve. Where the machine provides a refresher on `PATH` for this, use it (on this author's
machine, `research-update`); otherwise loop the clones directly. If an entry looks suspiciously
stale after running it, check `git config --get-all remote.origin.fetch` in that clone: a repo
originally cloned with an explicit `--branch <tag>` keeps tracking only that pinned ref forever, not
the moving default branch, until the fetch refspec is corrected (find the real default branch via
`git ls-remote --symref origin HEAD`).

## Grep the real source, don't trust docs/README prose

Once a repo's cloned, prefer grepping its actual source for ground truth over trusting its README or
a docs site's prose — both can be stale or wrong relative to the installed version. This has caught
real bugs before: a docs page describing a GNOME keybinding schema that didn't actually exist in the
installed GNOME version (only found by reading `gnome-shell` source directly), and a docs-site build
tool whose real mount behavior only matched its actual minified JS bundle, not its rendered docs
page.

Both of those are staleness. There is a second, worse shape: a README advertising a feature that was
**never implemented at all**. Confirmed 2026-08-27 while surveying medication trackers for `ingesta`
— a Home Assistant integration's README listed NIH RxNorm ingredient lookup among its features, and
neither `rxnorm` nor `ingredient` appears anywhere in the repo outside that README. A feature-list
comparison scores it as present; one grep settles it. When the question is "does this project do X",
the cheap decisive check is whether X appears in the code at all, not whether the docs claim it.

This is also why source beats a hands-on trial for an open-source candidate, where both are
available: a trial exercises the path you happened to walk, source shows every path there is, and it
answers questions no UI exposes — whether a dose amount is a number or free text, whether a
permission is stripped from the manifest.

## Judging a candidate dependency

Picking a library is the same activity as the rule above, one step earlier: the question is what the
source says, not what the summary claims. `~/AGENTS.md` says to judge a package from its own PyPI
file list rather than a search summary; this is what to look at once you are there.

**Judge each candidate against an absolute bar, on its own, before any head-to-head.** Popularity is
a weak signal past a threshold and is never a tiebreaker — a less popular project that clears the
bar beats a more popular one that does not. Stated 2026-08-30 while choosing between two Telegram
libraries, and it is the reason the script prints stars under `not scored`.

```shell
python3 $S/scripts/package_health.py <pypi-name> <owner/repo>
python3 $S/scripts/package_health.py anyio agronholm/anyio --clone $RESEARCH_HOME/repos/github.com--agronholm--anyio
```

Stdlib only, `S=~/.agents/skills/research-library`. PyPI over HTTPS, GitHub through `gh api` so it
uses your own token and rate limit. `--clone` adds what no API answers — `py.typed`, the
test-to-source ratio, the CI inventory, the licence files actually present. `--generated <glob>` is
repeatable and marks a mechanical layer so the ratio is taken against hand-written code. `--json`
for the whole answer.

The four axes it reports, and what each is for:

- **Maintenance** — releases on the **stable** line and their median gap, last push against last
  release (which separates "actively developed, slow to release" from "stalled"), human contributor
  count and bus factor over the last year, time to close an issue, archived flag, licence, yanked
  releases.
- **Typing** — `py.typed`, the project's own type-checker config and its strictness, which predicts
  what leaks. Then measure: run **your** checker in **your** mode over a small real usage sample.
  Nothing else tells you what your gate will say.
- **Battle-tested** — test-to-source ratio against hand-written source, whether coverage is enforced
  in CI or only reported, and what the CI workflows actually cover.
- **Fit** — runtime dependency count and names (never the raw `requires_dist`, which is mostly
  extras), version ceilings and whether they bind the distributed artifact or only the dev lockfile,
  licence compatibility, and whether the thing can be exercised offline.

**Three of the report's lines are traps wearing the shape of an answer, so read them as written:**
`open issues+PRs` is GitHub's field and counts both; a `PRE-RELEASE ONLY` or `pre-releases` line
means a dev version is moving while the stable one may not be; a `shallow clone` line means any
history question needs `git fetch --deepen` first. Confirmed 2026-09-02 on `httpx`: read naively,
PyPI says 4 releases in the last year with the newest yesterday. On the stable line it is **zero in
the last year, the last one 634 days ago** — the opposite answer to "is this maintained for me".

Everything the numbers hide — the bot that dominates a bus factor, the dual-licensed project the API
reports as GPL, why a version cap is not a cost until its historical lag says so, and how to prove
offline-testability — is in [`references/dependency-health.md`](references/dependency-health.md).
Read it before writing a recommendation, not before running the script.

## No symlinks into project repos

Never symlink `$RESEARCH_HOME` or any entry in it into a project's working tree. That would put this
content back in the ambient read path of anything scoped to that repo — the entire reason it lives
outside every repo. Reach it by its `$RESEARCH_HOME` path directly, only when a task actually calls
for it.

## Per-project pointers

This skill can't know _which_ entries matter to a given project. Each project's own `AGENTS.md`
should name the specific paths relevant to it ("for GNOME Shell extension behaviour, check
`$RESEARCH_HOME/repos/gitlab.gnome.org--GNOME--gnome-shell` before reading anything online"), as a
standing rule rather than a suggestion. That is also what makes the library reachable by agents that
read `AGENTS.md` but have no skill-discovery mechanism.

## Full design rationale

[`references/rationale.md`](references/rationale.md) — why this exists rather than a per-repo
`reference/` directory, why naming has no special case for the popular host, the pinned-tag refresh
trap, the docs-site mirroring research (`llms.txt` and its fallbacks), and why RAG/embeddings were
researched and deliberately not adopted.
