---
name: research-library
description: "Use when working with, adding to, or updating the shared cross-project research library at $RESEARCH_HOME (vendor repo clones, reference PDFs/epubs, mirrored docs pages) — before fetching the same material from the web, when cloning a reference repo for a project, or when asked to update/refresh the library."
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
