---
status: in-progress
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

What each registry exposes, verified 2026-09-27 against live payloads fetched with the script's
`User-Agent`. Trimmed copies are fixtures in `tests/fixtures/package_health/`: `biome-npm.json`,
`biome-cli-linux-x64-npm.json`, `esbuild-npm.json` and `ripgrep-crates.json`.

- **npm**: `registry.npmjs.org/<name>` returns the full packument. For `@biomejs/biome` that is 377
  kB over 153 versions, and for `esbuild` 1.26 MB over 482.
  - Version and date: `dist-tags.latest`, and the `time` map, keyed by version plus `created` and
    `modified`. `dist-tags` also carries `beta` and `nightly` lines for biome, and `latest-4` for
    express, so the prerelease trap is real: read `dist-tags.latest`, never the newest key in
    `versions`.
  - Per-version size: `dist.unpackedSize`, `dist.fileCount` and `dist.tarball` all exist on current
    versions. **They are missing on old ones.** `express` lacks both on 258 of its 289 versions,
    everything up to 4.16.2 (2017-10-10), and has them from 4.16.3 (2018-03-12) on. `esbuild` lacks
    them only on its 0.0.0 placeholder. A parser must treat them as optional.
  - Provenance: `dist.attestations.provenance.predicateType` (SLSA v1) is present on biome and
    esbuild releases and absent on express. This is a supply-chain signal the plan did not list.
  - Commands: `bin`, an object, for example `{"biome": "bin/biome"}`.
  - **Install-time scripts**: `scripts` is present in the full packument, for example esbuild
    0.28.2's `{"postinstall": "node install.js"}`. It is absent from biome, which has none.
    `hasInstallScript: true` exists **only** in the abbreviated form
    (`Accept: application/vnd.npm.install-v1+json`). That form has no `time` map and no `scripts`,
    so the full packument is the one to read.
  - Platform packages: the wrapper names them in `optionalDependencies`, for example
    `@biomejs/cli-linux-x64` and `@biomejs/cli-linux-x64-musl`, all pinned to the wrapper's own
    version. Each platform package carries `os` (`["linux"]`), `cpu` (`["x64"]`) and, on 122 of its
    148 versions, **`libc`** (`["glibc"]`). The real size is the platform package's own
    `dist.unpackedSize`, which is 64.7 MB for cli-linux-x64 2.5.14 against 779 kB for the wrapper.
    Resolving it costs one more packument fetch. esbuild uses the same pattern, 26 platform
    packages, **and** a `postinstall` that verifies them, so the two signals co-occur and are
    reported separately.
  - `deprecated` is a per-version string. biome 2.0.1 to 2.0.3 carry one, and express has 173.
  - Typing: `types` on the version (esbuild has `lib/main.d.ts`). `typings` is the legacy spelling,
    and neither appeared on biome.
  - Download counts are a separate API (`api.npmjs.org/downloads/…`). Not fetched here.
- **crates.io**: `crates.io/api/v1/crates/<name>` returns
  `{crate, versions, keywords,
  categories}`, with every version inline (59 of 59 for ripgrep, 93
  kB).
  - Crate: `max_stable_version`, `max_version`, `newest_version`, `default_version`, `updated_at`,
    `created_at`, `num_versions`, `downloads`, `recent_downloads`, `repository`, `yanked` and
    `trustpub_only` all exist.
  - Per version: `num`, `created_at`, `yanked`, `yank_message`, `crate_size`, `license`,
    `rust_version`, `bin_names`, `has_lib`, `edition`, `downloads`, `checksum`, `trustpub_data` and
    `published_by` all exist.
    - **`bin_names`** is a list, `["rg"]`, and is populated even on ripgrep 0.1.0 from 2016. It
      answers "does this crate ship a binary" directly.
    - **`rust_version`** (the MSRV) is null unless the crate declares one. ripgrep has it on 9 of 59
      versions, from 14.0.0 (2023-11-26) on, so absent means undeclared, not unknown.
    - **`linecounts`** is also per version: code and comment lines per language, populated back to
      0.1.0. It is not a test-to-source split, so it does not replace `--clone`.
  - Dependencies are **not** inline. They take a second request per version, at
    `versions[].links.dependencies`.

  The descriptive `User-Agent` was sent and the request succeeded. What crates.io does without one
  was not tested.
- **Rust binaries don't live on crates.io.** `cargo install` compiles from source, which costs a
  toolchain plus minutes of build time. The prebuilt binaries are **GitHub release assets** per
  target triple (`x86_64-unknown-linux-gnu`, `-musl`), which `cargo-binstall` resolves. So for a
  Rust tool, "what ships" is the latest stable release's asset list, with names and sizes, read
  through `gh api repos/<owner>/<repo>/releases/latest`. That also answers the same question for Go
  tools (gmailctl, gws), which ship the same way.

[UNVERIFIED: how often sessions still hand-roll the PyPI fetch after `package_health.py` landed. A
rough `rg` for `curl…pypi.org/pypi/` over `~/.claude/projects` matched around 170 transcripts on
2026-09-27. That count is contaminated, because the home `AGENTS.md` rule text contains the same
string and is loaded into sessions. Measure it with `session-bash-audit` or `skill-fitness`'s
repeated-script mode, counting Bash tool-use commands only.]

## Open questions

[DECISION: extend `package_health.py` rather than add a sibling script. The `ships` section is
always on, and the upstream is its own flag, `--upstream <owner/repo>`, separate from the positional
package repo. For `shellcheck-py` the package repo is `shellcheck-py/shellcheck-py` and upstream is
`koalaman/shellcheck`. Taken 2026-09-27 as the recommended direction, when stages 1 and 2 were
implemented. It is reversible while nothing outside this repo calls the flag.]

[DECISION: wrapper and upstream versions match by spelling only: the upstream version exactly, or
followed by `.`, `+`, `_` or `-`, so `0.11.0` matches `0.11.0.1` and never `0.110`. The report
prints both versions and the lag in days, from upstream's `published_at` to the matching wrapper
version's earliest upload. On a miss it prints `NO MATCHING WRAPPER RELEASE` rather than guessing.
Implemented 2026-09-27, with the rationale in `references/dependency-health.md`.]

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

## Progress

- **Stage 1, the PyPI file list, landed 2026-09-27.** The always-on `ships` section is in the text
  report and in `--json` as `release_files`. The fixture is `shellcheck-py-pypi.json`, whose 0.9.0.3
  is a real sdist-only release.
- **Stage 2, `--upstream` with GitHub release assets, landed 2026-09-27.**
  - It reads `releases/latest` once, for the version, the date and the assets.
  - The asset filter takes Rust triples, Go's `linux_amd64`, shellcheck's `linux.x86_64` and
    `.deb`/`.rpm`/`.apk`, and reads libc from the name.
  - A checksum is a `.sha256`-style sidecar or a `checksums.txt`/`SHA256SUMS` manifest. A signature
    is a `.sig`/`.asc`/`.minisig` beside the asset or beside the manifest.
  - GitHub's per-asset `digest` field is reported separately, as GitHub's hash of the upload.
  - The fixtures are `shellcheck-release.json` (no checksum files at all) and `ripgrep-release.json`
    (a `.sha256` per asset, musl only for x86_64).
  - Item 5's `--assets` flag without `--upstream` is **not** built. Nothing needs it until crates.io
    lands, where the release repo is the crate's own `repository`.
- SKILL.md has the `Ships` and `Upstream` lines and the `shellcheck-py` example. The reasoning is in
  `references/dependency-health.md`.
- **npm and crates.io: fields verified, parsers not written.** That is blocked on the CLI-shape and
  axes questions above.

[DEFERRED: repointing the home `AGENTS.md` install rule from
`curl -s https://pypi.org/pypi/<name>/json` to this script. That rule is a fragment in
`power-user-linux-setup` (`config/agents-md/`), so once this lands, file it with
`plans.py new … --for github.com-personal/power-user-linux-setup` rather than editing that repo from
here.]
