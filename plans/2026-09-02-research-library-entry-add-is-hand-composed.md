---
status: landed
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

[DECISION: **`add` clones, and `--dry-run` is the printing mode rather than the whole design.** The
objection was real — a script that writes outside the repo assumes a machine layout — and it is
answered by where it writes: only under `$RESEARCH_HOME`, which the script refuses to invent if it
does not exist, exactly as the skill's own rule says. Printing alone would have left the two halves
that actually get skipped (the canonical name and the provenance file) as manual steps, which is the
finding. `name` and `check` stay read-only, so the read path never has a write in it.]

[DECISION: **`check` lives in the skill, and it does not overlap `research-update`.** They answer
different questions: the machine-local refresher moves every clone forward, `check` says whether
moving a clone forward can do anything at all. A check that lived only in the machine's setup repo
could not travel with a published skill, and the convention it enforces is the skill's. Filed
separately for the machine's own repo: `research-update` could end by calling `library.py check` and
printing what it found, which is where the two do meet.]

## What landed, 2026-09-02

`skills/research-library/scripts/library.py`, stdlib only, four subcommands: `name`, `add`,
`provenance`, `check`. The `SKILL.md` now delegates the derivation instead of describing it, and the
`fitness.py derivable` count for this skill went **1 → 0**, with delegated rising 2 → 6.

**The first run of `check` over the real 52-entry library found four things, and one of them was a
bug in the check itself.** The rule as first written — flag any fetch refspec that is not the
`+refs/heads/*` wildcard — reported **49 of 52 entries**, every one of them cloned exactly as this
skill instructs. `git clone --depth 1` implies `--single-branch`, so a refspec naming one branch is
what a _correct_ entry looks like here.

[PITFALL: the documented trap is narrower than "a single-branch refspec", and reading the 49 is what
showed it. A clone made with an explicit `--branch <tag>` leaves **HEAD detached** and tracks a ref
that never moves; that is the signature, it is free to check, and it caught the one real instance
(`gitlab.gnome.org--GNOME--gnome-shell`). Whether a tracked branch is still the remote's _default_
cannot be answered offline at all, so it is `--remote` and off by default. An audit that flags 94%
of a conformant corpus is one nobody runs twice.]

The other three findings are the store's own, and are reported rather than fixed here — the entries
are outside every repo and the vocabulary belongs to the store's README, not to this parser:

- `docs/adv360-smartset-action-tokens-v3-31-23.pdf` and
  `docs/adv360-smartset-direct-programming-guide-v12-2-22.pdf` — no `ref`, and
  `kind: site-mirror (single PDF)`;
- `docs/skillsbench-2026.pdf` — `kind: reference-pdf`.

[DEFERRED: three real entries reached for a kind the store's three-value vocabulary does not have,
which is evidence the vocabulary is missing one for a flat downloaded document rather than evidence
that three people typed it wrong. Widening it is a change to `$RESEARCH_HOME/README.md` and to this
skill together, and it is the user's store to decide about — so `check` reports the mismatch and
changes nothing.]
