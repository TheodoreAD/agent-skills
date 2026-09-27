---
status: in-progress
updated: 2026-09-27
---

# Package health: report what a release actually ships

Scope: PyPI, npm, Rust (crates.io, plus the GitHub release assets Rust binaries actually ship as),
**apt**, and **GitHub repositories on their own**. The user widened it from PyPI alone on
2026-09-27, in two steps.

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

[DECISION: **the source is a required subcommand, with no default** (user, 2026-09-27: "we should
avoid having a default … the index/source platform should be a subcommand so the agent can't miss
it"):

```
package_health.py pypi   <name>          [--repo owner/repo] [--upstream owner/repo] [--clone …]
package_health.py npm    <name>          [--repo …] [--upstream …]
package_health.py crates <name>          [--repo …]
package_health.py apt    <name>
package_health.py github <owner/repo>
```

It beat a registry prefix with a bare name meaning PyPI, and a `--registry` flag, because a default
is exactly what an agent carries over from the previous call without noticing. A subcommand shows up
in `--help` as the first choice to make.

The package's own GitHub repo moves from a second positional to `--repo`. Every source can fill it
from its own metadata, but the lookup can be wrong or missing: npm `repository`, crates
`repository`, PyPI `project_urls`. An explicit `--repo` stays the override, and the report says
which one it used.]

[DECISION, with the user's push-back invitation answered: the break is loud, not silent. The old
form `package_health.py httpx encode/httpx` exits 2 with one line naming the new form
(`package_health.py
pypi httpx --repo encode/httpx`), rather than quietly still meaning PyPI. A
silent fallback would be a default by another name.

The callers were counted on 2026-09-27. In this repo: `SKILL.md`, `references/dependency-health.md`,
`evals/dependency-health.json`, `tests/unit/test_package_health.py`, and two older plans that cite
it in prose. Outside it: one store plan. All of them are updated in the same change.

The cost is anyone who installed the skill before the change and runs an old example from memory.
They get a one-line correction, not a wrong answer.]

[DECISION: a **`github <owner/repo>`** subcommand for tools that have no registry at all: Go and
Rust binaries shipped only as release assets, such as gog, gmailctl and helm. The user asked for
this on 2026-09-27 ("make sure we can get github releases/stars/contributors/etc").

It is the maintenance axis the script already computes from `gh api` (commits, contributors, bus
factor, issue close time, push versus release, archived flag, licence, and stars unscored), plus the
release view: the stable-release cadence from the GitHub releases list, and the latest release's
Linux assets with checksums and signatures, which stage 2 already built for `--upstream`. The
registry subcommands reuse the same code for their `--repo`. Item 5's standalone `--assets` becomes
this subcommand.]

[DECISION: **apt** as a source (user, 2026-09-27). What it answers is different from the others, and
the report says so. An apt package's maintenance is the **distro's**, not upstream's, so the key
question is how far behind upstream the packaged version is, and whether this machine's suite gets
security updates for it. That means:

- candidate version and origin (`archive.ubuntu.com noble/universe`, or a third-party repo), from
  `apt-cache policy`;
- installed size and dependencies, from `apt-cache show`;
- main (Canonical-supported) versus universe (community);
- with `--upstream owner/repo`, the lag behind upstream's latest release.

`apt-cache` is local and describes **this machine's** sources, which is the right answer for an
install decision. Checked on Ubuntu 24.04.5 LTS.]

[DECISION: apt also reports a **cross-release view** (user, 2026-09-27): which Ubuntu and Debian
releases carry which version. It's for choosing between apt and a release binary, and for knowing
what the next LTS brings. Candidate sources are Debian's madison API
(`api.ftp-master.debian.org/madison`) and Launchpad's published-sources API for Ubuntu. Verify both
against live responses and record them as fixtures before writing a parser, as was done for npm and
crates.io.]

[DECISION: **typing applies only to dynamically typed ecosystems.** Settled with the user
2026-09-27: statically typed languages are typed by construction, so a typing line for crates, or
for a Go or Rust binary, would carry no information.

- **PyPI**: `py.typed`, as today.
- **npm**: the package ships its own `types`/`typings`, or is written in TypeScript, versus needing
  a separate `@types/<name>`, versus neither.
- **crates, apt, github**: no typing section.]

[DECISION: **a floors line for every source**, replacing the idea of "MSRV for crates". The user
pointed out on 2026-09-27 that a minimum-version requirement applies across all languages and OSes.
Each source reports every floor its metadata states, read from the metadata and never inferred:

| source | floors                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pypi   | `requires_python` (already reported), and the **glibc floor from the manylinux tag** (`manylinux_2_17` means glibc ≥ 2.17; musllinux means musl)                |
| npm    | `engines.node` (and `engines.npm`), and a platform package's `os`/`cpu`/`libc`                                                                                  |
| crates | `rust_version` (MSRV), and "undeclared" when null                                                                                                               |
| apt    | the suite it is packaged for, and versioned `Depends` such as `libc6 (>= 2.34)`                                                                                 |
| github | libc family from the asset name (gnu or musl); a numeric glibc floor would need downloading the binary and reading its ELF version needs, which is out of scope |

Each floor is compared with this machine where the machine's value is cheap to read (Python version,
glibc from `ldd --version`, node if present), and a floor above this machine is flagged.]

[DECISION: stays in `research-library` (user, 2026-09-27). Judging what installing something costs
is part of judging a dependency, and the skill is installed on every machine. power-user-linux-setup
only repoints its install rule; see the DEFERRED item below.]

[DECISION: **npm platform packages are resolved by default** (user, 2026-09-27), at one extra
request, because otherwise the reported size is wrong by about 80 times (Biome: 64.7 MB against 779
kB).]

### What building it fully entails

The user asked, 2026-09-27. For scale, the script is 1,115 lines with 716 lines of tests after
stages 1–2. Each stage below is one or more commits, each passing the gate, each with recorded
fixtures and no network in tests.

1. **The subcommand refactor.** The CLI moves to subparsers, the old form gets its loud error, and
   `pypi` becomes the first subcommand. SKILL.md, the references, evals, tests and the plans that
   cite the old form are updated. No new data, so it's mostly moving code and rewriting examples.
2. **`github`.** A new entry point over code that already exists (maintenance, plus stage 2's
   assets), plus the stable-release cadence from the releases list. Small.
3. **Floors.** A cross-cutting section: the glibc floor from manylinux tags for PyPI and a
   comparison against this machine. The other sources add their rows as they land. Small.
4. **npm.** Packument parsing (optional size fields, `dist-tags`, deprecation, provenance), install
   scripts, platform-package resolution, typing, `engines`, and `repository` → `--repo`. The largest
   new parser, about the size of the PyPI one.
5. **crates.** The crate API (stable version, cadence, yanked, size, `bin_names`, MSRV), and
   `repository` → the `github` release view for binaries. Medium; the fixture exists.
6. **apt.** `apt-cache policy` and `show` parsing, main versus universe, and upstream lag. Medium,
   and the first source read from a local command rather than HTTP, so tests fake the command output
   instead of a payload.
7. **SKILL.md and trigger check.** The description must now say npm, crates, apt and GitHub without
   stealing triggers. Measure with `skill-fitness`'s `trigger.py candidate`.

Stages 1–3 are mechanical and low-risk. Stages 4–6 are each a session's worth of focused work.

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
- **npm and crates.io: fields verified, parsers not written.** The CLI-shape and axes questions that
  blocked them were settled 2026-09-27 (see the decisions above). Next up is the subcommand
  refactor, stage 1 of "What building it fully entails".
- Stages 1–2 were pushed 2026-09-27 (`c800f05`) and the skills re-installed.

Against "What building it fully entails":

- **Build stage 1, the subcommand refactor, landed 2026-09-27** (`54f609d`). `pypi` is the only
  subcommand so far; each source adds its own as it lands. `--repo` is filled from `project_urls`
  (source-like keys first, then `home_page`) and the report's `repo from` line names the field. The
  retired form exits 2 with the new spelling. The caller count was smaller than recorded: the two
  older plans (`2026-09-05-a-piped-gate-that-cannot-lie`, `2026-09-07-script-coverage-…`) name the
  script only, and `evals/dependency-health.json` names no command line, so none needed editing. The
  store plan outside this repo (`_unscoped/2026-09-26-google-api-access-foundation.md`) was read,
  not edited: it too names only `package_health.py`, never a command line.
- **Build stage 2, `github <owner/repo>`, landed 2026-09-27** (`06aa9d3`). The maintenance axis, the
  stable cadence from one page of the releases list (pre-release by GitHub's flag or by tag
  spelling, drafts skipped), and the latest release's Linux assets through a `LatestRelease` that
  `Upstream` now extends. Fixtures `ripgrep-releases.json` (75 releases) and `ripgrep-repo.json`.
  Monorepo tags such as `@biomejs/biome@2.5.14` read as their version. [UNVERIFIED: a monorepo's
  releases list mixes packages — `biomejs/biome` interleaves `@biomejs/js-api@6.0.0` with the CLI's
  — so its cadence counts all of them. Not handled; a filter by tag prefix is the obvious fix if it
  misleads in practice.]
- **Build stage 3, floors, landed 2026-09-27** (`9ef0a2d`). One `floors` section, the machine read
  through the transport seam (`python3`, glibc via `os.confstr`, `node --version` when on PATH) so
  tests pin it. PyPI: `requires_python` and the lowest manylinux glibc floor, a musllinux-only
  release flagged on glibc. GitHub: the libc family per asset name. A small PEP 440 and npm-range
  evaluator answers `not compared` rather than guess on a spelling it does not parse.
- **Build stage 4, npm, landed 2026-09-27** (`c35eb28`). Every field in the verified list above is
  read. Platform packages: the `optionalDependencies` **named** Linux x64 are fetched (two for
  biome, one for esbuild, never all 26), and each one's own `os`/`cpu`/`libc` picks the one this
  machine installs; `install size` is wrapper plus that. A pin naming no published version (biome
  2.0.3's `workspace:*`) prints `UNRESOLVED`. Typing: `types`/`typings`, a `types` condition in
  `exports`, else one request for `@types/<name>`, a 404 meaning none. New fixtures: `express-npm`
  (latest-4 newer than latest, sizes missing before 4.16.3), `types-express-npm`,
  `biome-cli-linux-x64-musl-npm`, `esbuild-linux-x64-npm`. Floor verdict wording changed from
  `ABOVE THIS MACHINE` to `NOT MET HERE`, because a libc mismatch is not "above".
- **Build stage 5, crates, landed 2026-09-27** (`31118d8`). `max_stable_version`, cadence, yanked,
  `crate_size`, `bin_names`, MSRV floor (`undeclared` when null). `repository` feeds the maintenance
  axis and, when `bin_names` is non-empty, a `prebuilt binary` section from the latest GitHub
  release. [UNVERIFIED: what crates.io does without a `User-Agent`; the script always sends one.]
- **Build stage 6, apt, landed 2026-09-27.** Fixtures first (`5f056f8`), then the parser
  (`471b08b`). Both cross-release endpoints were verified live before any parser existed:
  - Debian madison (`?package=<binary>&f=json`) is keyed by suite name and carries `-debug` and
    `buildd-` suites, skipped; the `amd64` build wins where a suite holds two versions.
  - Launchpad `getPublishedSources` wants the **source** name (`rust-ripgrep`), taken from
    `apt-cache show`'s `Source:`. It keeps end-of-life series `Published`, so `ubuntu/series` is
    read too and its `status` drops obsolete series; `Proposed` is skipped. That is one request more
    than the decision named.
  - `apt-cache` runs under `LC_ALL=C`; an unknown package makes `policy` print nothing and `show`
    exit 100.
  - Upstream comes from `--upstream` or, when it is GitHub, the package's `Homepage` — the same
    auto-fill-and-say-so rule as `--repo`. The lag counts upstream stable releases newer than the
    packaged version (noble's ripgrep: 4 behind, 920 days).
  - No GitHub maintenance axis for apt, per the decision that its maintenance is the distro's.
- **Build stage 7, SKILL.md and trigger check, landed 2026-09-27** (`698a92c`). The description
  names all five sources; the body is regrouped into shared axes and per-source additions;
  `compatibility:` names every endpoint and `apt-cache`, and the disclosure section lists
  `apt-cache` and `node --version` as run and madison and Launchpad as reached. Measured with
  `trigger.py candidate`, 3 runs: 12/13, each new-source positive 3/3 to the new wording, all
  negatives silent; the failure is the py.typed boundary case the suite keeps on purpose.
- All seven build stages are committed, not pushed, and the installed skill is not refreshed. Live
  runs of all five subcommands against real packages matched the fixture-driven tests.

[DEFERRED: repointing the home `AGENTS.md` install rule from
`curl -s https://pypi.org/pypi/<name>/json` to this script. That rule is a fragment in
`power-user-linux-setup` (`config/agents-md/`), so once this lands, file it with
`plans.py new … --for github.com-personal/power-user-linux-setup` rather than editing that repo from
here.]
