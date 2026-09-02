---
status: idea
updated: 2026-09-02
---

# `research-library` makes the agent derive an entry's name and write its metadata by hand

## Context

The first honest run of `fitness.py derivable` over this repo's own corpus, 2026-09-02, left seven
derivable command lines across 14 skills. Six are legitimate residue by the rule `skill-authoring`
states — three `npx skills add <owner>/<repo>` lines (an external CLI's own documented one-liner)
and three one-off git-surgery commands in `plan-docs`' history-purge procedure. **One is a real
finding**, and it is the reason to keep the audit rather than assume the repo is done:

```shell
git clone --depth 1 <url> "$RESEARCH_HOME/repos/<host>--<owner>--<repo>"
```

Adding an entry to the research library means: derive `<host>--<owner>--<repo>` from a URL by a
naming rule the skill spends a paragraph explaining (always that shape, every host, no GitHub
special case, read from the actual `origin` remote rather than assumed — self-hosted GitLab looks
like GitHub and is not), clone into it, then hand-write a `SOURCE.md` carrying `url`, `kind`, `ref`,
`fetched` and an optional `note`, in that shape, with `docs/` entries taking a `<file>.source.md`
sibling instead.

That is a deterministic transformation of a URL into a directory name plus a fixed metadata file —
the exact shape the principle says belongs in code, and it is written as prose for the agent to
re-derive every time. The skill already has `scripts/package_health.py`, so there is no "does this
skill get a script" question to settle.

## Why it matters more than one command line suggests

The failure it produces is silent and it is already recorded elsewhere in this repo: an entry that
does not match the store's own convention, which is invisible to every other check precisely because
that store is not version-controlled. `session-harvest`'s sweep now reports entries missing their
provenance file for that reason, which is the downstream half — this is the upstream half, and a
generator that always writes the file is a better fix than a sweep that reports its absence.

## Recommended direction

`scripts/library.py` (stdlib, read-only by default) with at least:

- `name <url>` — the entry name the convention produces, printed, so the derivation is one call and
  the same answer every time. It reads the real remote rather than the URL's host where they differ.
- `add <url> [--kind repo-clone|llms-txt-mirror|site-mirror] [--ref <ref>]` — clone or fetch, then
  write the provenance file. The one thing here that writes; everything else read-only.
- `check` — every entry against the convention: missing `SOURCE.md`, a name that does not match its
  own remote, a clone whose fetch refspec is pinned to one tag (the documented trap that makes
  `research-update` report "up to date" on something years stale).

[NEEDS CLARIFICATION: does `add` clone, or print the clone command? The skill is published and a
script that clones into `$RESEARCH_HOME` is a script that writes outside the repo on a machine whose
layout it assumes. Printing the exact command keeps it read-only and still removes the derivation,
which is the whole finding; cloning removes a step but adds an assumption. `check` is unambiguous
either way and is the half with no downside.]

[NEEDS CLARIFICATION: `research-update` already exists as a deployed script in the machine's own
setup repo, and refreshes every clone. Does `library.py check` belong beside it instead of in the
skill? Probably not — the convention is the skill's, and a check that lives on one machine cannot
travel with the published skill — but the overlap should be stated rather than discovered later.]

## Evidence

- `fitness.py derivable --root skills`, 2026-09-02: 105 fenced command lines, 93 delegated, 7
  derivable, and this is one of them. Baseline committed at
  `skills/skill-fitness/references/baselines/derivable-2026-09-02.json`.
- `$RESEARCH_HOME/README.md`'s own Naming, Provenance and Updating sections, which are the
  transformation this would carry.
