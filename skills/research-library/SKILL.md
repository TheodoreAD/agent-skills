---
name: research-library
description: "Use when working with, adding to, or updating the shared cross-project research library at $RESEARCH_HOME (vendor repo clones, reference PDFs/epubs, mirrored docs pages) — before fetching the same material from the web, when cloning a reference repo for a project, or when asked to update/refresh the library. Also owns judging a named third-party package or repo before depending on it: whether it is still maintained, who is actually committing to it, how often it releases on its stable line, whether it ships py.typed, how much test suite is behind it, whether a version cap it carries will hold you back — read from PyPI, the GitHub API and the project's own source rather than from a search summary."
compatibility: Python 3.11+ (stdlib only), git, and network access - clones from the URL you give, and package health from PyPI's JSON API and the GitHub API through gh, so your own token and rate limit apply. Text-only clones need a git with `clone --filter=blob:none --sparse` and `sparse-checkout set --no-cone`, measured on git 2.43; `--all-files` needs none of that. A library directory ($RESEARCH_HOME, default ~/research) that you create.
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

## What this skill reads, runs and writes

- **Reads**: `$RESEARCH_HOME` and the entries in it; a repo's own `AGENTS.md` for pointers.
  `size --ungreppable` opens every file in the store and reads its first 8 KB.
- **Runs**: `git clone`/`fetch`/`reset`/`sparse-checkout`/`tag -d`/`reflog expire`/`gc` inside
  library clones only, and `gh api` for package health and for a repo's reported size before `add`
  clones it.
- **Writes**: only inside `$RESEARCH_HOME` — `add` clones and writes a provenance file, `provenance`
  writes that file, `update` and `deepen` and `reshallow` change clones and their `depth:` field.
  `name`, `check` and `size` write nothing, and `--dry-run` prints what would run. Never a symlink
  or a copy into a project repo, and nothing outside the store is ever touched.
- **Reads from the environment**: `RESEARCH_HOME` for the store, and `RESEARCH_TEXT_ONLY` for
  whether `add` clones text-only by default.
- **Network**: the clone URL you give; PyPI and GitHub for `package_health.py` and for the pre-clone
  size question, GitHub through your own `gh` login. Nothing is uploaded.

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

## Naming, adding, and checking entries

The convention is `<host>--<owner>--<repo>` for every repo on every host, with no exceptions and no
GitHub special case, and every entry carries a provenance file. **Do not derive either by hand** —
`scripts/library.py` is that derivation, and the reason it exists is that both failures are silent:
a name derived from the URL you were handed rather than from the clone's own `origin` looks
completely normal (self-hosted instances resemble the popular host, and a renamed repo redirects
without saying so), and a store nothing version-controls has nothing else that would notice.

```shell
python3 $S/scripts/library.py name <url>            # the entry name, from any spelling of a remote
python3 $S/scripts/library.py add <url>             # clone, canonical name, SOURCE.md written
python3 $S/scripts/library.py add <url> --dry-run   # the clone and the file it would write
python3 $S/scripts/library.py check                 # every entry against these conventions
```

`S=~/.agents/skills/research-library`. `add` re-derives the name from the clone's own remote after
cloning and renames the entry when they disagree; it records `ref` as the branch and short sha it
actually got, and it clones **text-only** unless told otherwise — see below for what that leaves out
and why it costs a search nothing. For an entry that is not a git clone — a downloaded PDF, a
mirrored docs site — fetch it however the material requires, then
`library.py provenance <path> --url <url> --kind <kind> --ref <ref>` writes the metadata half, which
is the deterministic part and the part that gets skipped. `--json` on everything; `name` and `check`
are read-only, `add` and `provenance` write only inside `$RESEARCH_HOME`.

The provenance file's shape, since `check` enforces it and a reader may need to fix one by hand:
`url`, `kind` (`repo-clone`, `llms-txt-mirror` or `site-mirror`), `ref` (branch/tag/commit for a
clone, fetch date for a mirror), `fetched`, `depth` when the history was deliberately deepened (see
below), `text-only` when the checkout is narrowed (see below), and `note` only when non-obvious —
e.g. docs publishing from a different branch or repo than the one cloned.

**`add` asks before cloning something the host calls large**, exiting 3 with the reported figure
rather than prompting — an interactive prompt inside an agent's Bash call hangs with nothing to type
into. `--yes` proceeds, `--min <MB>` moves the line (default 250 MB), `--depth N` or `--full` clones
more than one commit and records it. The check is GitHub's API, so a host it cannot ask is never a
host it refuses to clone from.

**The reported size is a trigger, never a prediction, and the warning deliberately quotes no
estimate.** Measured 2026-09-07 against five real entries at depth 1: on-disk cost ran from 0.23×
the reported size (`cpython`, 851 MB reported and 192 MB on disk) to 1.32× (`Roo-Code`, 359 reported
and 473 on disk). A 5.7× spread, and not even an upper bound — a warning naming a predicted figure
would have been wrong by 4× in the reassuring direction.

## Clones hold text, because that is all anyone searches

**`add` clones text-only by default**: images, video, audio, fonts, archives, compiled objects and
model weights are left on the server, and everything a text search can read is checked out.
`--all-files` opts one entry out; `RESEARCH_TEXT_ONLY=0` opts a whole machine out.

```shell
python3 $S/scripts/library.py add <url>               # text-only, the default
python3 $S/scripts/library.py add <url> --all-files   # every file, images and binaries included
python3 $S/scripts/library.py add <url> --dry-run     # the two commands and the file it would write
```

**The exclusion cannot cost a search a single hit, and that is the only reason it is a default.**
Every format it skips is one ripgrep and grep already refuse to search — both treat a file with a
NUL byte in its first block as binary and skip it — so those bytes buy a search nothing. This is
also why it is not the same decision as excluding a _directory_, which makes a grep silently blind
and stays unadopted here for exactly that reason.

Verified end to end 2026-09-08 on `intellectronica/ruler`, 97% binary, the same commit cloned both
ways: **257 searchable files in both trees, the identical set**, `grep -rIl ruler` returning 190
files in both, and one file absent from the text-only clone — a 69 MB `.gif`. On disk, 141 MB became
**3.0 MB**, and `.git` 70 MB became **644 KB**.

That last number is the part worth knowing, because it comes from combining two things that each do
nothing alone. `--filter=blob:none` defers nothing on a `--depth 1` clone, since the checkout
materialises every blob at HEAD anyway; the sparse set alone shrinks the working tree while `.git`
stays exactly as large. Together, blobs the sparse set never wants are never fetched. A clone
carrying one without the other saves a fraction of what it appears to.

**Documents are kept, and PDFs are the reason.** A PDF is binary to a grep and readable by an agent,
so the line is document-versus-demo-asset rather than greppable-versus-not. Nine PDFs sit inside
repo clones today — 6.6 MB, **0.5% of the excluded weight**, including a 4.6 MB
`flameshot-documentation.pdf`. Half a percent of the saving removes the only case where this could
lose something a reader wanted. Ebook and office formats are kept on the same judgement. `.svg`
needs no exemption at all: it is text, so the NUL rule keeps it regardless.

**An entry whose checkout is narrower than its HEAD has to say so**, or a later grep that finds
nothing reads as an answer rather than as a question about what was checked out. `add` records
`text-only: yes`, and `check` reports both directions of drift — an entry claiming it over a full
checkout, and a sparse checkout nothing records, which also catches a path-based `sparse-checkout`
someone applied by hand.

`update` needs no special case: a shallow fetch and hard reset leave `core.sparseCheckout` and the
pattern list intact, confirmed on a real refresh.

## What the library costs

```shell
python3 $S/scripts/library.py size                  # entries at or above 250 MB, biggest first
python3 $S/scripts/library.py size --min 0          # everything
python3 $S/scripts/library.py size --ungreppable    # and how much of it no text search can read
```

`--ungreppable` is what makes re-cloning an existing entry text-only a decision with a number
attached rather than a principle. It classifies by **content**, not by the exclusion list, so the
report can contradict the patterns — which is how the extensionless residue stays visible: 620 files
and 16 MB library-wide, 1.25% of the ungreppable weight and reachable by no extension pattern. Small
enough to be the answer rather than a reason for a second filter. It reads every file in the store
(184,279 files in 2.9s warm on a 3 GB library), which is why it is a flag.

Measured 2026-09-08 over 86 entries: **1,286 MB of 3,274 MB of working tree, 39%, is ungreppable**.
It concentrates — `block/goose` is 310 MB of 343, `RooCodeInc/Roo-Code` 276 of 293 — and the biggest
entry in the library is the counterexample that keeps path exclusion a separate question:
`nodejs/node` is 15 MB of 669, because its 669 MB working tree is vendored V8 and OpenSSL
**source**, greppable to the last byte.

Per entry it splits `.git` from the working tree, **because they have different remedies and the
ratio says which applies**: a large `.git` at one commit is big blobs, where the only lever is not
keeping the clone; a large working tree at one commit is vendored directories. Measured on the worst
entry in a real 4.8 GB library — 940 MB at **one commit**, of which a single vendored `deps/`
directory was 675 MB, while the `src`, `lib` and `doc` a reference clone exists for totalled 34 MB.
Depth was not the problem there and no amount of re-shallowing would have moved it.

## Updating, deepening, and getting the disk back

```shell
python3 $S/scripts/library.py update                      # every clone, each at its intended depth
python3 $S/scripts/library.py update <entry>              # just this one
python3 $S/scripts/library.py deepen <entry> --depth 500  # more history, recorded as deliberate
python3 $S/scripts/library.py reshallow <entry>           # back to a depth-1 footprint, disk included
```

`update` refreshes each clone to its remote's latest — a shallow fetch and hard reset, since these
are disposable reference clones, not working copies with local commits to preserve. It and
`library.py check` answer different questions and neither replaces the other: one moves every clone
forward, the other says whether moving it forward can possibly do anything.

**A clone deeper than one commit with nothing recorded is skipped, not truncated.** Nothing
distinguishes a deliberate deepening from an accident, and truncating is the answer that cannot be
undone by reading. Confirmed 2026-09-07 in a 71-entry library: exactly one entry was deep, it had
been deepened on purpose to read a dependency's constraint history, and a loop refreshing everything
with `fetch --depth 1` would have destroyed that in silence. Use `deepen` rather than a hand-typed
`git fetch`, so the intent lands in the entry's `depth:` field and `update` can see it.

**`reshallow` exists because re-shallowing by hand does not reclaim the disk.** Measured 2026-09-07
on `encode/httpx`, `.git` in KB: a fresh `--depth 1` clone is 2,492; deepened by 400 commits and
re-shallowed with `fetch --depth 1` and `reset --hard` it reports **one commit again while the disk
does not move at all**; adding `reflog expire`, `gc --prune=now`, `repack -a -d`, `prune` and
`gc --aggressive` reaches 4,852 and stops there. The cause is **tags** — deepening brings them, each
pins a commit deep in history, and every object below stays reachable. Delete them and the same
clone lands at 2,472, below where it started. The widely-published sequence omits that step, so run
verbatim it leaves a clone permanently 95% larger and reports success. That is five commands in
order, one of which appears in no reference material: exactly the shape that belongs in code.

It refuses on a detached HEAD, where the tags may be the thing the clone exists to read; `--force`
overrides.

**An entry that looks suspiciously stale after a refresh is usually pinned**, and `check` names it:
a clone made with an explicit `--branch <tag>` leaves `HEAD` detached and keeps tracking that one
ref forever, so `git fetch origin` re-fetches the same thing and the refresh reports "up to date" on
something years old. Confirmed 2026-09-02, the first run of `check` over a 52-entry library: one
such clone, and 51 entries that a cruder rule would have flagged as pinned when they were cloned
exactly as this skill says. `check --remote` adds the one question that needs the network — whether
the tracked branch is still the remote's default — and is off by default so the rest stays instant.

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
source says, not what the summary claims. **Judge a package from its own PyPI file list rather than
from a search summary** — this is what to look at once you are there.

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
