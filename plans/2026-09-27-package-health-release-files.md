---
status: idea
updated: 2026-09-27
---

# Package health: report what a release actually ships

Scope: PyPI, npm and Rust (crates.io, plus the GitHub release assets Rust binaries actually ship
as). The user widened it from PyPI alone on 2026-09-27.

## Context

`research-library`'s `scripts/package_health.py` judges a PyPI package on maintenance, typing,
battle-testing and fit. It was written because sessions kept hand-rolling
`pypi.org/pypi/<name>/json` fetches: 61 across 12 sessions, measured 2026-08-30 (its own docstring).

It does not report **what a release ships**, meaning its file list. That is exactly the question the
machine-wide install rule asks. The home `AGENTS.md` section "Installing a tool on this machine"
tells an agent to look for a maintained PyPI wrapper first (`shellcheck-py`, `actionlint-py`…), and
to "judge the wrapper from its own PyPI file list (`curl -s https://pypi.org/pypi/<name>/json`),
never from a search summary". Those facts are:

- **platform-tagged wheels**, meaning the binary ships inside the wheel, versus **sdist-only**,
  meaning it fetches or builds at install time;
- **file sizes**, which are the adoption cost;
- **release count**;
- **whether the wrapper's version tracks the upstream release**, checked against the upstream
  changelog.

That rule cites two cases where this went wrong in both directions. A search summary claimed
`hadolint-py` downloads at install time, and it nearly got rejected for a false reason: it ships
real 12 MB wheels. `lychee-bin` turned out to be a 78 MB wheel with exactly one release, which
reversed a decision already made to adopt it.

So the one rule that most needs the file list is the one the script can't answer, and the rule
itself spells the answer as a hand-rolled `curl`.

It surfaced 2026-09-27 in a Google-stack CLI research session. A research subagent had been told to
`curl` PyPI for exactly this, and had to be redirected to `package_health.py` with the file-list gap
named.

### npm and Rust have the same question, and different answers to where the files are

The install rule's methods include npm-global, and CLI tools written in Rust are routinely offered
through three channels at once: `cargo install`, a GitHub release binary, and a PyPI or npm wrapper
(`ruff` and `uv` are maturin binary wheels, and `@biomejs/biome` is npm platform packages). So
"which channel, and what does it cost" is one question asked across registries. Nothing answers it
today without hand-rolled `curl` against each registry's JSON.

What each registry exposes. These are from memory and must be verified against the live APIs before
coding.

- **npm**: `registry.npmjs.org/<name>` returns the packument.
  - Version and date: `dist-tags.latest`, and the `time` map of release dates. The prerelease trap
    is the same as PyPI's, so read the stable line from `dist-tags`, not from the newest key in
    `versions`.
  - Per-version size: `dist.unpackedSize`, `dist.fileCount`, `dist.tarball`.
  - Commands: `bin`.
  - **Install-time scripts**: `scripts.preinstall`, `install` and `postinstall`. This is npm's
    "sdist-only": the package downloads or builds its binary at install time.
  - Platform packages: `os`/`cpu`, plus `optionalDependencies` naming per-platform packages
    (`@scope/cli-linux-x64`). This is npm's "platform wheels"; the real size is the platform
    package's `unpackedSize`, not the wrapper's.
  - `deprecated`.
  - Download counts come from a separate API (`api.npmjs.org/downloads/point/last-week/<name>`).
    Report them unscored, like stars.
- **crates.io**: `crates.io/api/v1/crates/<name>` returns the crate and its versions.
  - Crate: `max_stable_version`, `updated_at`, `recent_downloads`, `repository`.
  - Per version: `num`, `created_at`, `yanked`, `crate_size`, `license`, and possibly `rust_version`
    (MSRV) and `bin_names`.

  crates.io's crawler policy requires a descriptive `User-Agent`, and the transport already sends
  one.
- **Rust binaries don't live on crates.io.** `cargo install` compiles from source, which costs a
  toolchain plus minutes of build time. The prebuilt binaries are **GitHub release assets** per
  target triple (`x86_64-unknown-linux-gnu`, `-musl`), which `cargo-binstall` resolves. So for a
  Rust tool, "what ships" is the latest stable release's asset list, with names and sizes, read
  through `gh api repos/<owner>/<repo>/releases/latest`. That also answers the same question for Go
  tools (gmailctl, gws), which ship the same way.

[UNVERIFIED: which of the npm and crates.io fields above exist today, and their exact names,
especially crates.io's `bin_names` and `rust_version` per version, and npm's
`dist.unpackedSize`/`fileCount` on older packuments. Record a real payload for one package per
registry as a fixture before writing a parser.]

[UNVERIFIED: how often sessions still hand-roll the PyPI fetch after `package_health.py` landed. A
rough `rg` for `curl…pypi.org/pypi/` over `~/.claude/projects` matched around 170 transcripts on
2026-09-27. That count is contaminated, because the home `AGENTS.md` rule text contains the same
string and is loaded into sessions. Measure it with `session-bash-audit` or `skill-fitness`'s
repeated-script mode, counting Bash tool-use commands only.]

## Open questions

[NEEDS CLARIFICATION: extend `package_health.py`, or add a sibling script (`release_files.py`)? A
flag such as `--files`, or an always-on section, keeps one entry point for "judge this package". But
the wrapper question has a different second input: the **upstream** repo whose releases the wrapper
should track. That is not the same repo as the package's own, which `package_health.py` already
takes as `<owner/repo>`. For `shellcheck-py` the package repo is `shellcheck-py/shellcheck-py` and
upstream is `koalaman/shellcheck`.]

[NEEDS CLARIFICATION: how to compare wrapper and upstream versions. Wrappers often use the upstream
version with a suffix (`0.10.0.1`), and some are unrelated. A reasonable first cut reports both
latest versions and the lag in days between upstream's release and the wrapper's matching one. It
flags "no matching wrapper release" rather than trying to parse every scheme.]

[NEEDS CLARIFICATION: the CLI shape once three registries are in scope. Options:

- a registry prefix on the name (`pypi:ruff`, `npm:@biomejs/biome`, `crates:ripgrep`), with a bare
  name meaning PyPI, so existing calls keep working;
- `--registry`;
- a separate script per registry.

The prefix keeps one entry point, and it matches how package URLs are written (the `purl` spec uses
`pkg:pypi/…`, `pkg:npm/…`, `pkg:cargo/…`). Check whether a purl-style spelling is worth adopting
outright.]

[NEEDS CLARIFICATION: which of `package_health.py`'s existing axes carry over.

- Maintenance carries over whole: stable-line cadence, contributors and bus factor, push versus
  release.
- Fit mostly carries over: dependency count, licence.
- Typing is Python-specific. npm's analogue is "ships its own `types`, or needs `@types/…`". Rust
  has no analogue.
- Battle-tested (`--clone`) carries over as-is.

Decide whether npm and crates get the full four-axis report or only maintenance plus release files
at first.]

[NEEDS CLARIFICATION: does the release-file report belong in `research-library` at all, or in
`power-user-linux-setup`, which owns the install rule and `setup.toml`? It belongs here if judging
"what does installing this cost" counts as part of judging a dependency, which the skill's
description already claims ("whether a version cap it carries will hold you back"). And the skill is
what's installed on every machine.]

## Recommended direction

1. Extend `package_health.py`. For the latest **stable** release, and optionally the last N, list
   every file with:
   - its type (wheel or sdist);
   - its wheel tags (Python, ABI, platform);
   - its size;
   - its upload time.

   Then summarise:
   - whether a `manylinux`/`musllinux` x86_64 wheel exists for this machine;
   - the largest file;
   - pure-Python (`py3-none-any`) versus platform-specific;
   - sdist-only, which means install-time build or fetch.

   It reuses the transport it already has. The same PyPI JSON payload is already fetched, so there
   is no extra request.
2. `--upstream <owner/repo>` adds the wrapper-tracking check through `gh api` releases: upstream's
   latest release date and version, whether the wrapper has a matching version, and the lag.
3. **npm**: the same file-level summary from the packument.
   - Tarball size and file count.
   - `bin`.
   - Install-time scripts, flagged prominently as "fetches or builds at install".
   - Platform packages resolved to this machine's `linux-x64` entry, with that package's own size.
   - Deprecation.
4. **crates.io**: stable version and date, cadence, yanked releases, crate size, MSRV if exposed,
   and whether it has binaries. Then the GitHub release-asset check below, because that's where the
   binary is.
5. **GitHub release assets** (`--assets`, or on by default for crates): the latest stable release's
   assets filtered to this machine's target triple (x86_64 Linux gnu/musl), with sizes and whether a
   checksum or signature file sits alongside. This is shared with `--upstream`, which reads the same
   endpoint.
6. `--json` carries all of it, like the rest of the report.
7. Update the SKILL.md "Judging a candidate dependency" section: the new lines, the registry
   spelling, and one example per registry (`shellcheck-py` with upstream `koalaman/shellcheck`, an
   npm platform-package tool, a Rust CLI). Check the description still triggers for "is this npm
   package / crate maintained" without contending with another skill. Measure that with
   `skill-fitness`'s `trigger.py candidate`.
8. Tests in `tests/unit/`, using recorded payload fixtures in `tests/fixtures/`: one per registry,
   plus a release-assets payload. Never inside the skill.
9. Build it in stages that each pass the gate: PyPI file list first, then `--upstream` and assets,
   then npm, then crates.io. Each is its own commit.

[DEFERRED: repointing the home `AGENTS.md` install rule from
`curl -s https://pypi.org/pypi/<name>/json` to this script. That rule is a fragment in
`power-user-linux-setup` (`config/agents-md/`), so once this lands, file it with
`plans.py new … --for github.com-personal/power-user-linux-setup` rather than editing that repo from
here.]
