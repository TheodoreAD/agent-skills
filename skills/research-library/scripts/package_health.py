#!/usr/bin/env python3
"""Judge one candidate dependency against an absolute maintenance bar, not against a rival.

Choosing a library is a recurring task that gets done from scratch every time. Measured over one
machine's transcripts on 2026-08-30: 61 hand-rolled `pypi.org/pypi/<name>/json` fetches across 12
sessions, and 96 `gh api repos/...` calls across 19, every one a fresh `curl` with a slightly
different field selection. The repo-stats shape is nearly identical each time and drifts anyway, so
answers that ought to be comparable across sessions are not. This is that lookup, written down once.

**Each candidate is judged on its own first, and popularity is never a tiebreaker.** Past a
threshold it is a weak signal, and the question that matters is whether this project independently
clears a maintenance bar. Star and fork counts are reported because they are free, and they are
deliberately not scored.

    package_health.py <pypi-name> <owner/repo>
    package_health.py httpx encode/httpx --clone ~/research/repos/github.com--encode--httpx
    package_health.py httpx encode/httpx --json
    package_health.py shellcheck-py shellcheck-py/shellcheck-py --upstream koalaman/shellcheck

Stdlib only, so it runs by path from any repo with no install step. PyPI is read over HTTPS; GitHub
is read through `gh api`, which uses the caller's own token and rate limit rather than needing one
configured here. `--clone <path>` adds everything that can only be answered from the source:
`py.typed`, the test-to-source ratio, the CI inventory, the licence files actually present.

Every report also lists what the latest stable release **ships** — its wheels and sdist, their tags
and sizes — from the same PyPI payload, so no extra request: whether a Linux x86_64 wheel exists,
whether it is pure Python or carries a binary, and whether it is sdist-only and so builds or fetches
at install time. `--upstream <owner/repo>` names the project a wrapper repackages, which is not the
wrapper's own repo: its latest stable GitHub release, the wrapper version matching it and the lag in
days, and that release's Linux x86_64 assets with the checksum and signature files beside them.

Exit codes: 0 ok, 1 error, 2 argparse usage.
"""

from __future__ import annotations

import sys

# Before any import below: `datetime.UTC` is 3.11+, and on 3.10 the failure would otherwise be an
# ImportError naming a stdlib module, with nothing pointing at the interpreter.
if sys.version_info[:2] < (3, 11):  # noqa: UP036 — runs exactly where requires-python is not enforced
    sys.exit(f"package_health.py needs Python 3.11 or newer; this is {sys.version.split()[0]} ({sys.executable})")

import argparse
import json
import re
import signal
import statistics
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any, Protocol

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
USER_AGENT = "package-health/1.0 (+https://github.com/TheodoreAD/agent-skills)"
TIMEOUT_SECONDS = 30

# A contributor login matching any of these is automation. Measured 2026-08-30: `renovate[bot]` was
# 70% of one project's commits over a year, which reads as a catastrophic bus factor and is actually
# dependency bumps. Excluding bots reversed the finding — that project had the *better* human
# distribution of the two candidates. Any contributor metric has to filter these or it is measuring
# the CI robots.
BOT_PATTERNS = (
    re.compile(r"\[bot\]$", re.IGNORECASE),
    re.compile(r"^(dependabot|renovate|pre-commit-ci|github-actions|greenkeeper|snyk-bot)\b", re.IGNORECASE),
    re.compile(r"-bot$", re.IGNORECASE),
)

# A `requires_dist` entry whose marker is gated on an extra is not installed by a plain
# `pip install <name>`. The extras dominate the raw list and are not what a consumer inherits.
EXTRA_MARKER_RE = re.compile(r";.*\bextra\s*==", re.IGNORECASE)

# PEP 440's pre-release and dev spellings, at the end of a version string: `1.0a1`, `1.0b2`,
# `1.0rc1`, `1.0.dev6`. `.post1` is deliberately absent — a post-release is a real release.
PRERELEASE_RE = re.compile(r"[._-]?(?:a|b|c|rc|alpha|beta|pre|preview|dev)[._-]?\d*$", re.IGNORECASE)
REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z0-9._-]+)")

# Files that answer "how much work does the consumer inherit", found by name rather than by parsing.
TYPE_CHECKER_CONFIGS = ("pyrightconfig.json", "mypy.ini", ".mypy.ini")
TYPE_CHECKER_TABLES = ("[tool.mypy]", "[tool.pyright]", "[tool.basedpyright]", "[tool.ty]")

# How many pages of commits the contributor window reads before it stops and says so. A bounded
# answer that names its own bound beats an unbounded walk of a large project's history.
COMMIT_PAGES = 5
COMMIT_PAGE_SIZE = 100
CONTRIBUTOR_WINDOW_DAYS = 365

# Closed issues sampled for the time-to-close median. Pull requests are excluded: they close on a
# different rhythm and would flatter a project that merges quickly and answers issues slowly.
ISSUE_SAMPLE = 50


class Transport(Protocol):
    """The two networks this reads, behind one seam so every computation below can be tested.

    Every input to this script is a network response, so the fetch layer is injectable and the tests
    drive it from captured fixtures. No test may reach the network, which is asserted rather than
    intended — see `tests/unit/test_package_health.py`.
    """

    def pypi(self, name: str) -> dict[str, Any]: ...

    def github(self, path: str) -> Any: ...


class LiveTransport:
    """PyPI over HTTPS, GitHub through `gh api` so the caller's own token and rate limit apply."""

    def pypi(self, name: str) -> dict[str, Any]:
        request = urllib.request.Request(PYPI_JSON.format(name=name), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise HealthError(f"PyPI returned {error.code} for {name!r} — check the distribution name") from error
        except urllib.error.URLError as error:
            raise HealthError(f"PyPI unreachable: {error.reason}") from error
        if not isinstance(payload, dict):
            raise HealthError(f"PyPI returned a non-object for {name!r}")
        return payload

    def github(self, path: str) -> Any:
        result = subprocess.run(
            ["gh", "api", path],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise HealthError(f"gh api {path} failed: {result.stderr.strip() or result.returncode}")
        return json.loads(result.stdout)


class HealthError(Exception):
    """Anything the caller can fix: a wrong name, an unreachable API, a path that is not a clone."""


# ------------------------------------------------------------------------------------------------
# PyPI: cadence and what a consumer actually installs


def release_dates(payload: dict[str, Any]) -> dict[str, datetime]:
    """One date per version: the **earliest** upload among that version's files.

    A version's wheels and sdist are uploaded at slightly different moments, sometimes minutes apart
    and occasionally on different days when a build is retried. Taking the max drifts the cadence;
    the first upload is when the release happened.
    """
    dates: dict[str, datetime] = {}
    for version, files in payload.get("releases", {}).items():
        stamps = [_parse_stamp(entry.get("upload_time_iso_8601")) for entry in files or []]
        present = [stamp for stamp in stamps if stamp is not None]
        if present:
            dates[version] = min(present)
    return dates


def yanked_versions(payload: dict[str, Any]) -> list[str]:
    """A version is yanked when every file for it is. A part-yanked release is still installable."""
    yanked: list[str] = []
    for version, files in payload.get("releases", {}).items():
        if files and all(entry.get("yanked") for entry in files):
            yanked.append(version)
    return sorted(yanked)


@dataclass(frozen=True)
class Cadence:
    releases: int
    in_last_year: int
    median_gap_days: float | None
    days_since_last: int | None
    first_release: str | None
    last_release: str | None
    prereleases: int = 0
    last_prerelease: str | None = None
    stable_only: bool = True
    yanked: list[str] = field(default_factory=list)


def is_prerelease(version: str) -> bool:
    """PEP 440's pre-release and dev markers, by their spelling. `.post` is a real release."""
    return bool(PRERELEASE_RE.search(version))


def cadence(dates: dict[str, datetime], yanked: list[str], *, now: datetime | None = None) -> Cadence:
    """Release rhythm over the **stable** line, with the pre-release line counted beside it.

    [PITFALL] PyPI's `releases` map holds pre-releases and dev builds alongside real ones, and a
    project pushing `1.0.devN` looks like it is shipping every few weeks while the version a
    consumer actually installs has not moved. Confirmed 2026-09-02 on `httpx`: the three most recent
    uploads are `1.0.dev4`, `1.0.dev5` and `1.0.dev6`, so counting them gave "4 releases in the last
    year, last one 1 day ago" for a project whose stable line is `0.28.1` from 2024. Both numbers
    are true and only one of them answers "is this maintained for me".

    Gaps are taken over the most recent ten releases rather than the whole history: a project's
    early rhythm says nothing about whether anyone is looking after it now, and a long-lived project
    with a slow first year has its median dragged by history nobody depends on.
    """
    now = now or datetime.now(UTC)
    pre = sorted(stamp for version, stamp in dates.items() if is_prerelease(version))
    stable = sorted(stamp for version, stamp in dates.items() if not is_prerelease(version))
    # A project that has only ever shipped pre-releases is measured on them, and says so — the
    # alternative is reporting zero releases for something that plainly has some.
    ordered = stable or pre
    if not ordered:
        return Cadence(
            releases=0,
            in_last_year=0,
            median_gap_days=None,
            days_since_last=None,
            first_release=None,
            last_release=None,
            yanked=yanked,
        )
    recent = ordered[-10:]
    gaps = [(later - earlier).days for earlier, later in pairwise(recent)]
    year_ago = now - timedelta(days=CONTRIBUTOR_WINDOW_DAYS)
    return Cadence(
        releases=len(ordered),
        in_last_year=sum(1 for stamp in ordered if stamp >= year_ago),
        median_gap_days=round(statistics.median(gaps), 1) if gaps else None,
        days_since_last=(now - ordered[-1]).days,
        first_release=ordered[0].date().isoformat(),
        last_release=ordered[-1].date().isoformat(),
        prereleases=len(pre),
        last_prerelease=pre[-1].date().isoformat() if pre else None,
        stable_only=bool(stable),
        yanked=yanked,
    )


# ------------------------------------------------------------------------------------------------
# PyPI: what a release actually ships


@dataclass(frozen=True)
class ReleaseFile:
    filename: str
    kind: str
    python_tag: str | None
    abi_tag: str | None
    platform_tag: str | None
    size: int | None
    uploaded: str | None
    yanked: bool


@dataclass(frozen=True)
class ReleaseFiles:
    """One release's file list, and the four answers an install decision actually needs from it.

    The target is fixed at x86_64 Linux, the machine this is judged for, rather than read from
    `platform.machine()`: a report whose answer moves with whoever ran it cannot be compared across
    sessions, and the tests would pin nothing.
    """

    version: str | None
    files: list[ReleaseFile]
    wheels: int
    sdists: int
    linux_x86_64_wheels: list[str]
    pure_python: bool
    platform_specific: bool
    sdist_only: bool
    largest: str | None
    largest_size: int | None


def latest_stable_version(payload: dict[str, Any]) -> str | None:
    """PyPI's own `info.version` when it is a stable release with files, else the newest stable by date.

    `info.version` is what `pip install <name>` resolves to, so it is the release worth judging.
    The fallback covers a payload whose `info.version` is a pre-release (a project that has only
    shipped those) or names a version whose files are gone.
    """
    releases = payload.get("releases", {})
    stated = payload.get("info", {}).get("version")
    if stated and not is_prerelease(stated) and releases.get(stated):
        return stated
    dated = release_dates(payload)
    stable = sorted((stamp, version) for version, stamp in dated.items() if not is_prerelease(version))
    ordered = stable or sorted((stamp, version) for version, stamp in dated.items())
    return ordered[-1][1] if ordered else stated


def wheel_tags(filename: str) -> tuple[str, str, str] | None:
    """The Python, ABI and platform tags of a wheel filename, each possibly a `.`-joined set.

    `name-version(-build)?-python-abi-platform.whl`: the last three dash-separated fields are the
    tags whatever the name and version hold, because both are normalised to contain no dashes.
    """
    if not filename.endswith(".whl"):
        return None
    parts = filename.removesuffix(".whl").split("-")
    if len(parts) < 5:
        return None
    return parts[-3], parts[-2], parts[-1]


def _is_linux_x86_64(platform_tag: str) -> bool:
    """`manylinux*_x86_64` or `musllinux*_x86_64`, in any member of a compressed tag set."""
    return any(
        tag.startswith(("manylinux", "musllinux")) and tag.endswith("_x86_64") for tag in platform_tag.split(".")
    )


def _file_kind(entry: dict[str, Any], filename: str) -> str:
    packagetype = entry.get("packagetype")
    if packagetype == "bdist_wheel" or filename.endswith(".whl"):
        return "wheel"
    if packagetype == "sdist" or filename.endswith((".tar.gz", ".zip", ".tar.bz2")):
        return "sdist"
    return str(packagetype or "unknown")


def release_files(payload: dict[str, Any], version: str | None = None) -> ReleaseFiles:
    """What installing `version` (default: the latest stable) actually downloads.

    [PITFALL] Whether a wrapper ships its binary or fetches it at install time is exactly what a
    search summary gets wrong, in both directions. Recorded before this existed: a summary claimed
    `hadolint-py` downloads at install and it ships real 12 MB wheels; `lychee-bin` turned out to be
    one 78 MB wheel with a single release ever. The file list answers both; the summary answered
    neither. An sdist-only release means pip builds it — or a build hook fetches a binary — on the
    consumer's machine, every time.
    """
    version = version or latest_stable_version(payload)
    entries = payload.get("releases", {}).get(version or "", []) or []
    files: list[ReleaseFile] = []
    for entry in entries:
        filename = str(entry.get("filename") or "")
        tags = wheel_tags(filename)
        size = entry.get("size")
        files.append(
            ReleaseFile(
                filename=filename,
                kind=_file_kind(entry, filename),
                python_tag=tags[0] if tags else None,
                abi_tag=tags[1] if tags else None,
                platform_tag=tags[2] if tags else None,
                size=int(size) if isinstance(size, int) else None,
                uploaded=_date_only(entry.get("upload_time_iso_8601")),
                yanked=bool(entry.get("yanked")),
            )
        )
    wheels = [entry for entry in files if entry.kind == "wheel"]
    sized = [entry for entry in files if entry.size is not None]
    largest = max(sized, key=lambda entry: entry.size or 0) if sized else None
    return ReleaseFiles(
        version=version,
        files=files,
        wheels=len(wheels),
        sdists=sum(1 for entry in files if entry.kind == "sdist"),
        linux_x86_64_wheels=[
            entry.filename for entry in wheels if entry.platform_tag and _is_linux_x86_64(entry.platform_tag)
        ],
        pure_python=any(entry.platform_tag == "any" for entry in wheels),
        platform_specific=any(entry.platform_tag not in (None, "any") for entry in wheels),
        sdist_only=bool(files) and not wheels,
        largest=largest.filename if largest else None,
        largest_size=largest.size if largest else None,
    )


def runtime_requirements(payload: dict[str, Any]) -> list[str]:
    """What a plain install pulls in: `requires_dist` minus everything gated on an extra.

    The extras dominate the raw list — a package with three runtime dependencies and six extras
    routinely shows thirty entries — and reporting the raw count overstates what the consumer
    inherits by an order of magnitude.
    """
    raw = payload.get("info", {}).get("requires_dist") or []
    return [entry for entry in raw if not EXTRA_MARKER_RE.search(entry)]


def requirement_names(requirements: list[str]) -> list[str]:
    """The distribution names alone, which is usually what a consumer is weighing, not the specs."""
    names: list[str] = []
    for entry in requirements:
        match = REQUIREMENT_NAME_RE.match(entry)
        if match:
            names.append(match.group(1))
    return sorted(set(names))


# ------------------------------------------------------------------------------------------------
# GitHub: who is looking after it


def is_bot(login: str) -> bool:
    return any(pattern.search(login) for pattern in BOT_PATTERNS)


@dataclass(frozen=True)
class Contributors:
    window_days: int
    commits_read: int
    truncated: bool
    humans: list[tuple[str, int]]
    bots: list[tuple[str, int]]

    @property
    def human_count(self) -> int:
        return len(self.humans)

    @property
    def bus_factor(self) -> int:
        """How many humans it takes to account for half the commits. One is the finding."""
        total = sum(count for _, count in self.humans)
        if not total:
            return 0
        seen = 0
        for index, (_, count) in enumerate(self.humans, start=1):
            seen += count
            if seen * 2 >= total:
                return index
        return len(self.humans)


def contributors(
    commits: list[dict[str, Any]], *, truncated: bool, window_days: int = CONTRIBUTOR_WINDOW_DAYS
) -> Contributors:
    """Split a commit listing into humans and automation, each ranked by commit count.

    A commit with no `author` object is attributed to its commit-author name: that is a commit whose
    email GitHub cannot match to an account, which is a real person, not a bot.
    """
    tally: Counter[str] = Counter()
    for entry in commits:
        author = entry.get("author") or {}
        login = author.get("login") or (entry.get("commit", {}).get("author", {}) or {}).get("name")
        if login:
            tally[login] += 1
    humans = [(login, count) for login, count in tally.most_common() if not is_bot(login)]
    bots = [(login, count) for login, count in tally.most_common() if is_bot(login)]
    return Contributors(
        window_days=window_days,
        commits_read=sum(tally.values()),
        truncated=truncated,
        humans=humans,
        bots=bots,
    )


@dataclass(frozen=True)
class IssueSample:
    """What a recent-closed sample actually contained, not just the median it yielded.

    The sample size is reported alongside the median because it is routinely **zero issues**, and a
    bare `None` there is indistinguishable from a project that closes nothing. See `issue_sample`.
    """

    sampled: int
    issues: int
    median_days: float | None


def issue_sample(items: list[dict[str, Any]]) -> IssueSample:
    """Median time to close over real issues only — anything carrying `pull_request` is a PR.

    [PITFALL] GitHub's issues endpoint returns pull requests too, and on an active project the
    recent closed items are overwhelmingly PRs. Confirmed 2026-09-02 against `encode/httpx`: 300
    closed items across three pages contained **zero** issues, so the median was `None` for a
    project that has closed thousands of them. Report what the sample held, so a missing median
    reads as "the sample was all PRs" rather than as a project that never closes anything.
    """
    spans: list[float] = []
    issues = 0
    for item in items:
        if "pull_request" in item:
            continue
        issues += 1
        opened = _parse_stamp(item.get("created_at"))
        closed = _parse_stamp(item.get("closed_at"))
        if opened and closed:
            spans.append((closed - opened).total_seconds() / 86400)
    return IssueSample(
        sampled=len(items),
        issues=issues,
        median_days=round(statistics.median(spans), 1) if spans else None,
    )


@dataclass(frozen=True)
class Repository:
    full_name: str
    archived: bool
    has_issues: bool
    license_field: str | None
    open_issues: int
    stars: int
    forks: int
    created: str | None
    pushed: str | None
    days_since_push: int | None
    default_branch: str | None


def repository(payload: dict[str, Any], *, now: datetime | None = None) -> Repository:
    """The repo's own stats. `license_field` is reported and never trusted — see `license_files`.

    [PITFALL] `open_issues_count` counts **pull requests as well as issues**, and it stays non-zero
    on a repo whose issue tracker is switched off entirely. Confirmed 2026-09-02: `encode/httpx`
    reports `has_issues: false` and `open_issues_count: 143`, every one of which is a PR. Scoring
    "open issues relative to project size" off that number compares a review backlog against a
    support backlog, so `has_issues` is carried alongside it and the report says which it is.
    """
    now = now or datetime.now(UTC)
    pushed = _parse_stamp(payload.get("pushed_at"))
    licence = (payload.get("license") or {}).get("spdx_id")
    return Repository(
        full_name=payload.get("full_name", "?"),
        archived=bool(payload.get("archived")),
        has_issues=bool(payload.get("has_issues", True)),
        license_field=None if licence in (None, "NOASSERTION") else licence,
        open_issues=int(payload.get("open_issues_count") or 0),
        stars=int(payload.get("stargazers_count") or 0),
        forks=int(payload.get("forks_count") or 0),
        created=_date_only(payload.get("created_at")),
        pushed=_date_only(payload.get("pushed_at")),
        days_since_push=(now - pushed).days if pushed else None,
        default_branch=payload.get("default_branch"),
    )


# ------------------------------------------------------------------------------------------------
# GitHub releases: the upstream a wrapper should track, and the binaries it publishes itself

# An asset for this machine names the architecture and either Linux or a Linux package format.
# Both spellings occur in the wild: Rust triples (`x86_64-unknown-linux-musl`), Go's
# `linux_amd64`, and shellcheck's own `linux.x86_64`. A `.deb` names no OS at all.
ASSET_ARCH_RE = re.compile(r"(?:x86[_-]64|amd64|x64)(?![0-9])", re.IGNORECASE)
ASSET_LINUX_RE = re.compile(r"linux|\.(?:deb|rpm|apk)$", re.IGNORECASE)
CHECKSUM_SUFFIXES = (".sha256", ".sha256sum", ".sha512", ".sha512sum", ".md5")
SIGNATURE_SUFFIXES = (".asc", ".sig", ".minisig", ".sigstore", ".sigstore.json", ".pem", ".cert")
# One file covering every asset: `SHA256SUMS`, `checksums.txt`, `gmailctl_0.10.0_checksums.txt`.
CHECKSUM_MANIFEST_RE = re.compile(r"(?:sha(?:256|512)sums|checksums?)(?:\.txt)?$", re.IGNORECASE)
TAG_PREFIX_RE = re.compile(r"^(?:[A-Za-z][\w.-]*?[-_/])?v?(?=\d)")


@dataclass(frozen=True)
class Asset:
    name: str
    size: int | None
    libc: str
    checksum: str | None
    signature: str | None
    github_digest: bool


@dataclass(frozen=True)
class Upstream:
    """The upstream's latest stable GitHub release, set against the wrapper that repackages it.

    `wrapper_match` is found by spelling only — the upstream version exactly, or followed by a
    separator (`0.11.0` matches the wrapper's `0.11.0.1`). Anything cleverer means parsing every
    project's scheme, and a wrong match reads as a false "tracks upstream"; "no matching wrapper
    release" is the honest answer when the spelling differs, and the reader compares the two
    versions printed beside it.
    """

    repo: str
    error: str | None = None
    tag: str | None = None
    version: str | None = None
    published: str | None = None
    days_since_release: int | None = None
    wrapper_match: str | None = None
    wrapper_match_date: str | None = None
    lag_days: int | None = None
    assets_total: int = 0
    linux_x86_64: list[Asset] = field(default_factory=list)
    checksum_manifests: list[str] = field(default_factory=list)


def tag_version(tag: str) -> str:
    """`v0.11.0` → `0.11.0`, `ripgrep-15.2.0` → `15.2.0`, `15.2.0` unchanged."""
    return TAG_PREFIX_RE.sub("", tag, count=1)


def wrapper_match(upstream_version: str, dates: dict[str, datetime]) -> str | None:
    """The wrapper's earliest version spelled as the upstream's, exactly or plus a suffix."""
    if upstream_version in dates:
        return upstream_version
    pattern = re.compile(rf"^{re.escape(upstream_version)}[.+_-]")
    matches = sorted((stamp, version) for version, stamp in dates.items() if pattern.match(version))
    return matches[0][1] if matches else None


def _is_sidecar(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(CHECKSUM_SUFFIXES + SIGNATURE_SUFFIXES) or bool(CHECKSUM_MANIFEST_RE.search(lowered))


def _beside(name: str, suffixes: tuple[str, ...], names: set[str]) -> str | None:
    """The first `<name><suffix>` the release also carries: a sidecar file for exactly this asset."""
    return next((f"{name}{suffix}" for suffix in suffixes if f"{name}{suffix}" in names), None)


def release_assets(release: dict[str, Any]) -> tuple[list[Asset], list[str], int]:
    """This machine's assets, each with the checksum and signature files that sit beside it.

    `github_digest` is GitHub's own sha256 of the upload, reported in the API since 2025. It proves
    the download matches what was uploaded and nothing about who uploaded it, so it is carried
    separately from a publisher's checksum or signature rather than counted as one.
    """
    raw = [asset for asset in release.get("assets") or [] if isinstance(asset, dict)]
    names = {str(asset.get("name") or "") for asset in raw}
    manifests = sorted(name for name in names if CHECKSUM_MANIFEST_RE.search(name.lower()))
    signed_manifest = next(
        (found for manifest in manifests if (found := _beside(manifest, SIGNATURE_SUFFIXES, names))), None
    )
    chosen: list[Asset] = []
    for asset in raw:
        name = str(asset.get("name") or "")
        if _is_sidecar(name) or not (ASSET_ARCH_RE.search(name) and ASSET_LINUX_RE.search(name)):
            continue
        lowered = name.lower()
        checksum = _beside(name, CHECKSUM_SUFFIXES, names)
        signature = _beside(name, SIGNATURE_SUFFIXES, names)
        size = asset.get("size")
        chosen.append(
            Asset(
                name=name,
                size=int(size) if isinstance(size, int) else None,
                libc="musl" if "musl" in lowered else "gnu" if "gnu" in lowered else "unspecified",
                checksum=checksum or (manifests[0] if manifests else None),
                signature=signature or signed_manifest,
                github_digest=bool(asset.get("digest")),
            )
        )
    return chosen, manifests, len(raw)


def upstream(
    transport: Transport, repo: str, wrapper_dates: dict[str, datetime], *, now: datetime | None = None
) -> Upstream:
    """Read `repos/<repo>/releases/latest`, which GitHub defines as the newest non-draft, non-prerelease.

    A repo that publishes tags and no releases answers 404 there. That is a finding about the
    upstream rather than a failure of the report, so it is carried as `error` and the rest of the
    report still prints.
    """
    now = now or datetime.now(UTC)
    try:
        release = transport.github(f"repos/{repo}/releases/latest")
    except HealthError as error:
        return Upstream(repo=repo, error=str(error))
    if not isinstance(release, dict):
        return Upstream(repo=repo, error="releases/latest returned a non-object")
    tag = str(release.get("tag_name") or "")
    version = tag_version(tag)
    published = _parse_stamp(release.get("published_at") or release.get("created_at"))
    match = wrapper_match(version, wrapper_dates) if version else None
    match_date = wrapper_dates.get(match) if match else None
    assets, manifests, total = release_assets(release)
    return Upstream(
        repo=repo,
        tag=tag,
        version=version,
        published=published.date().isoformat() if published else None,
        days_since_release=(now - published).days if published else None,
        wrapper_match=match,
        wrapper_match_date=match_date.date().isoformat() if match_date else None,
        lag_days=(match_date - published).days if match_date and published else None,
        assets_total=total,
        linux_x86_64=assets,
        checksum_manifests=manifests,
    )


# ------------------------------------------------------------------------------------------------
# The clone: everything the APIs cannot answer


@dataclass(frozen=True)
class Sources:
    source_files: int
    source_lines: int
    generated_files: int
    generated_lines: int
    test_files: int
    test_lines: int

    @property
    def raw_ratio(self) -> float | None:
        return round(self.test_lines / self.source_lines, 2) if self.source_lines else None

    @property
    def handwritten_ratio(self) -> float | None:
        """Tests against hand-written source, which is the number that means anything.

        Measured 2026-08-30: a candidate looked like 0.28 against a peer's 0.81 until 71% of its
        source turned out to be one-class-per-API-object binding modules. Against hand-written code
        the same project was 1.07 — better than the peer rather than a third as good. A raw ratio is
        meaningless wherever a project has a large mechanical layer, so segment before dividing.
        """
        hand = self.source_lines - self.generated_lines
        return round(self.test_lines / hand, 2) if hand > 0 else None


@dataclass(frozen=True)
class CloneFacts:
    path: str
    py_typed: bool
    sources: Sources
    workflows: list[str]
    license_files: list[str]
    type_checker_configs: list[str]
    shallow: bool


def line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _is_test(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & {"test", "tests", "testing"}) or path.name.startswith("test_") or path.name.endswith("_test.py")


def sources(root: Path, generated: list[str]) -> Sources:
    """Python line counts, split three ways: tests, generated source, hand-written source.

    `generated` is a list of glob patterns relative to the clone root, supplied by the caller,
    because no heuristic reliably finds a binding layer — the one that produced the measurement
    above had no generated-file header anywhere. Naming it is a judgement, so the flag makes it one
    the report states rather than one the script guesses.
    """
    marked = {resolved for pattern in generated for resolved in root.glob(pattern)}
    counts = Counter[str]()
    lines = Counter[str]()
    for path in sorted(root.rglob("*.py")):
        if any(part in {".git", ".venv", "node_modules", "build", "dist"} for part in path.parts):
            continue
        kind = "test" if _is_test(path.relative_to(root)) else "generated" if path in marked else "source"
        counts[kind] += 1
        lines[kind] += line_count(path)
    return Sources(
        source_files=counts["source"] + counts["generated"],
        source_lines=lines["source"] + lines["generated"],
        generated_files=counts["generated"],
        generated_lines=lines["generated"],
        test_files=counts["test"],
        test_lines=lines["test"],
    )


def license_files(root: Path) -> list[str]:
    """Every licence file present, because the API field reports one licence for a dual-licensed project.

    Confirmed 2026-08-30: the API said `GPL-3.0` for a project shipping `LICENSE`, `LICENSE.lesser`
    and a `LICENSE.dual` whose first line says either may be chosen. Taking the field at face value
    would have disqualified it on copyleft grounds that do not apply.
    """
    return [
        path.name
        for path in sorted(root.iterdir())
        if path.is_file() and path.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))
    ]


def clone_facts(root: Path, generated: list[str]) -> CloneFacts:
    if not root.is_dir():
        raise HealthError(f"--clone {root} is not a directory")
    workflows = sorted(path.name for path in (root / ".github" / "workflows").glob("*.y*ml"))
    configs = [name for name in TYPE_CHECKER_CONFIGS if (root / name).is_file()]
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        configs += [table for table in TYPE_CHECKER_TABLES if table in text]
    return CloneFacts(
        path=str(root),
        py_typed=any(root.rglob("py.typed")),
        sources=sources(root, generated),
        workflows=workflows,
        license_files=license_files(root),
        type_checker_configs=configs,
        shallow=(root / ".git" / "shallow").exists(),
    )


# ------------------------------------------------------------------------------------------------
# Assembling one candidate's answer


@dataclass(frozen=True)
class Health:
    name: str
    version: str | None
    summary: str | None
    requires_python: str | None
    cadence: Cadence
    runtime_requirements: list[str]
    release_files: ReleaseFiles
    repository: Repository | None
    contributors: Contributors | None
    issues: IssueSample | None
    clone: CloneFacts | None
    upstream: Upstream | None = None


def gather(
    transport: Transport,
    name: str,
    repo: str | None,
    *,
    clone: Path | None = None,
    generated: list[str] | None = None,
    upstream_repo: str | None = None,
    now: datetime | None = None,
) -> Health:
    now = now or datetime.now(UTC)
    payload = transport.pypi(name)
    info = payload.get("info", {})
    repo_facts, people, issues = None, None, None
    if repo:
        repo_facts = repository(transport.github(f"repos/{repo}"), now=now)
        people = _contributor_window(transport, repo, now=now)
        if repo_facts.has_issues:
            issues = issue_sample(transport.github(f"repos/{repo}/issues?state=closed&per_page={ISSUE_SAMPLE}"))
    return Health(
        name=info.get("name", name),
        version=info.get("version"),
        summary=info.get("summary"),
        requires_python=info.get("requires_python"),
        cadence=cadence(release_dates(payload), yanked_versions(payload), now=now),
        runtime_requirements=runtime_requirements(payload),
        release_files=release_files(payload),
        repository=repo_facts,
        contributors=people,
        issues=issues,
        clone=clone_facts(clone, generated or []) if clone else None,
        upstream=upstream(transport, upstream_repo, release_dates(payload), now=now) if upstream_repo else None,
    )


def _contributor_window(transport: Transport, repo: str, *, now: datetime) -> Contributors:
    since = (now - timedelta(days=CONTRIBUTOR_WINDOW_DAYS)).date().isoformat()
    collected: list[dict[str, Any]] = []
    truncated = False
    for page in range(1, COMMIT_PAGES + 1):
        batch = transport.github(f"repos/{repo}/commits?since={since}&per_page={COMMIT_PAGE_SIZE}&page={page}")
        if not isinstance(batch, list) or not batch:
            break
        collected.extend(batch)
        if len(batch) < COMMIT_PAGE_SIZE:
            break
        truncated = page == COMMIT_PAGES
    return contributors(collected, truncated=truncated)


# ------------------------------------------------------------------------------------------------
# Output


def render(health: Health) -> str:
    lines = [f"{health.name} {health.version or '?'}  —  {health.summary or 'no summary'}"]
    if health.requires_python:
        lines.append(f"requires-python: {health.requires_python}")

    pace = health.cadence
    lines.append("")
    kind = "stable" if pace.stable_only else "PRE-RELEASE ONLY — this project has shipped no stable"
    lines.append("maintenance")
    lines.append(f"  releases         {pace.releases} {kind}, {pace.in_last_year} in the last year")
    lines.append(f"  first / last     {pace.first_release or '?'} … {pace.last_release or '?'}")
    lines.append(f"  median gap       {_or_unknown(pace.median_gap_days, 'd (last 10 releases)')}")
    lines.append(f"  since last       {_or_unknown(pace.days_since_last, 'd')}")
    if pace.prereleases and pace.stable_only:
        lines.append(
            f"  pre-releases     {pace.prereleases}, latest {pace.last_prerelease}"
            "   — not counted above; a dev line moving is not the stable line moving"
        )
    if pace.yanked:
        lines.append(f"  yanked           {len(pace.yanked)}: {', '.join(pace.yanked[:6])}")

    if health.repository:
        repo = health.repository
        lines.append(f"  repo             {repo.full_name}{'  ARCHIVED' if repo.archived else ''}")
        lines.append(f"  last push        {repo.pushed or '?'} ({_or_unknown(repo.days_since_push, 'd ago')})")
        lines.append(f"  open issues+PRs  {repo.open_issues}   (GitHub counts both in this field)")
        lines.append(f"  issue tracker    {_issue_line(repo, health.issues)}")
        lines.append(f"  licence (field)  {repo.license_field or 'none reported'}   — verify against the files")
        lines.append(f"  not scored       {repo.stars} stars, {repo.forks} forks")

    if health.contributors:
        people = health.contributors
        top = ", ".join(f"{login} {count}" for login, count in people.humans[:5]) or "none"
        lines.append(
            f"  humans/{people.window_days}d      {people.human_count} over {people.commits_read} commits"
            f"{' (truncated)' if people.truncated else ''}"
        )
        lines.append(f"  bus factor       {people.bus_factor}   top: {top}")
        if people.bots:
            lines.append(f"  bots excluded    {', '.join(f'{login} {count}' for login, count in people.bots[:5])}")

    names = ", ".join(requirement_names(health.runtime_requirements)) or "none"
    lines.append("")
    lines.append("fit")
    lines.append(f"  runtime deps     {len(health.runtime_requirements)}: {names}")

    lines.append("")
    lines.extend(_release_file_lines(health.release_files))

    if health.upstream:
        lines.append("")
        lines.extend(_upstream_lines(health.upstream, health.release_files.version))

    if health.clone:
        clone = health.clone
        src = clone.sources
        lines.append("")
        lines.append(f"source ({clone.path})")
        lines.append(f"  py.typed         {'yes' if clone.py_typed else 'NO — the consumer inherits the typing work'}")
        lines.append(f"  type config      {', '.join(clone.type_checker_configs) or 'none found'}")
        raw, hand = _or_unknown(src.raw_ratio, ""), _or_unknown(src.handwritten_ratio, "")
        lines.append(f"  test/source      raw {raw}   hand-written {hand}")
        lines.append(
            f"  lines            {src.source_lines} source ({src.generated_lines} generated), {src.test_lines} test"
        )
        lines.append(f"  CI workflows     {', '.join(clone.workflows) or 'none'}")
        lines.append(f"  licence files    {', '.join(clone.license_files) or 'none'}")
        if clone.shallow:
            lines.append("  shallow clone    constraint archaeology needs `git fetch --deepen <n>` first")

    lines.append("")
    lines.append("Judge this against the bar before comparing it to anything. See the skill for the")
    lines.append("traps these numbers hide: a version cap is not a cost until its historical lag says so.")
    return "\n".join(lines)


# Past this many files the listing names the Linux x86_64 wheels and the sdist and counts the rest:
# a numpy-sized release has dozens of wheels, and `--json` carries every one.
FILE_LISTING_LIMIT = 12


def _release_file_lines(ships: ReleaseFiles) -> list[str]:
    lines = [f"ships ({ships.version or '?'})"]
    if not ships.files:
        lines.append("  files            none — this version has no files on PyPI")
        return lines
    lines.append(f"  files            {ships.wheels} wheel(s), {ships.sdists} sdist(s)")
    if ships.sdist_only:
        lines.append("  linux x86_64     SDIST ONLY — pip builds it, or a build hook fetches a binary, at install")
    elif ships.linux_x86_64_wheels:
        sizes = [_size(entry.size) for entry in ships.files if entry.filename in ships.linux_x86_64_wheels]
        lines.append(f"  linux x86_64     wheel present ({', '.join(sizes)}) — nothing built or fetched at install")
    elif ships.pure_python:
        lines.append("  linux x86_64     pure-Python wheel, installs anywhere")
    else:
        lines.append("  linux x86_64     NO WHEEL for this machine — pip falls back to the sdist and builds or fetches")
    kind = (
        "platform-specific and pure-Python wheels both"
        if ships.platform_specific and ships.pure_python
        else "platform-specific (a compiled or bundled binary per platform)"
        if ships.platform_specific
        else "pure Python (any)"
        if ships.pure_python
        else "no wheels"
    )
    lines.append(f"  wheel kind       {kind}")
    lines.append(f"  largest          {_size(ships.largest_size)}  {ships.largest or '?'}")
    shown = ships.files
    if len(shown) > FILE_LISTING_LIMIT:
        shown = [entry for entry in ships.files if entry.kind == "sdist" or entry.filename in ships.linux_x86_64_wheels]
        lines.append(f"  listing          {len(shown)} of {len(ships.files)}, other platforms omitted; --json has all")
    for entry in shown:
        yanked = "  YANKED" if entry.yanked else ""
        lines.append(f"    {_size(entry.size):>9}  {entry.uploaded or '?'}  {entry.filename}{yanked}")
    return lines


def _upstream_lines(up: Upstream, wrapper_version: str | None) -> list[str]:
    lines = [f"upstream ({up.repo})"]
    if up.error:
        lines.append(f"  latest release   none readable — {up.error}")
        lines.append("                   (a repo that publishes tags only has no releases/latest)")
        return lines
    lines.append(
        f"  latest release   {up.tag} ({up.version}), {up.published or '?'}"
        f" — {_or_unknown(up.days_since_release, 'd ago')}"
    )
    if up.wrapper_match:
        lines.append(
            f"  wrapper tracks   {up.wrapper_match} on {up.wrapper_match_date or '?'}, "
            f"{_or_unknown(up.lag_days, 'd')} after upstream"
        )
    else:
        lines.append(
            f"  wrapper tracks   NO MATCHING WRAPPER RELEASE for {up.version}; wrapper's latest stable is"
            f" {wrapper_version or '?'} — compare the two by hand"
        )
    lines.append(f"  linux x86_64     {len(up.linux_x86_64)} of {up.assets_total} assets")
    for asset in up.linux_x86_64:
        checks = ", ".join(
            part
            for part in (
                f"checksum {asset.checksum}" if asset.checksum else "NO checksum file",
                f"signature {asset.signature}" if asset.signature else "no signature",
                "GitHub digest" if asset.github_digest else "",
            )
            if part
        )
        lines.append(f"    {_size(asset.size):>9}  {asset.libc:<11}  {asset.name}")
        lines.append(f"               {checks}")
    return lines


def _size(size: int | None) -> str:
    """Decimal units, the way PyPI and GitHub print them, so the number matches what a reader sees there."""
    if size is None:
        return "?"
    for unit, scale in (("GB", 10**9), ("MB", 10**6), ("kB", 10**3)):
        if size >= scale:
            return f"{size / scale:.1f} {unit}"
    return f"{size} B"


def _issue_line(repo: Repository, sample: IssueSample | None) -> str:
    """Say which of the three things a missing median means, never leave it as a bare `?`."""
    if not repo.has_issues:
        return "DISABLED — every one of the open items above is a pull request"
    if sample is None:
        return "not sampled"
    if sample.median_days is None:
        return f"0 issues among the {sample.sampled} most recent closed items — all pull requests"
    return f"median close {sample.median_days}d over {sample.issues} of {sample.sampled} sampled"


def _or_unknown(value: object, suffix: str) -> str:
    return "?" if value is None else f"{value}{suffix}"


def _date_only(stamp: str | None) -> str | None:
    parsed = _parse_stamp(stamp)
    return parsed.date().isoformat() if parsed else None


def _parse_stamp(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        # `fromisoformat` takes the trailing `Z` from 3.11 on, which is this repo's floor. PyPI
        # stamps are offset-aware and GitHub's end in `Z`; a naive one is read as UTC rather than
        # dropped, since a missing offset is a formatting quirk and not a missing date.
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def payload_of(health: Health) -> dict[str, Any]:
    data = asdict(health)
    if health.contributors:
        data["contributors"]["human_count"] = health.contributors.human_count
        data["contributors"]["bus_factor"] = health.contributors.bus_factor
    if health.clone:
        data["clone"]["sources"]["raw_ratio"] = health.clone.sources.raw_ratio
        data["clone"]["sources"]["handwritten_ratio"] = health.clone.sources.handwritten_ratio
    return data


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="the distribution name on PyPI")
    parser.add_argument("repo", nargs="?", help="owner/repo on GitHub; omit to read PyPI only")
    parser.add_argument("--clone", type=Path, help="a local clone, for what the APIs cannot answer")
    parser.add_argument(
        "--generated",
        action="append",
        default=[],
        metavar="GLOB",
        help="source that is mechanical rather than hand-written, relative to the clone; repeatable",
    )
    parser.add_argument(
        "--upstream",
        metavar="OWNER/REPO",
        help="the project a wrapper repackages: its latest GitHub release, the wrapper's lag, its Linux assets",
    )
    parser.add_argument("--json", action="store_true", help="the whole answer as JSON")
    args = parser.parse_args(argv)

    try:
        health = gather(
            transport or LiveTransport(),
            args.name,
            args.repo,
            clone=args.clone,
            generated=args.generated,
            upstream_repo=args.upstream,
        )
    except HealthError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(payload_of(health), indent=2, default=str) if args.json else render(health))
    return 0


if __name__ == "__main__":
    # A cut pipe is the reader's decision, not this script's error: die on SIGPIPE (exit 141)
    # rather than print a BrokenPipeError traceback that reads as a crash. Inside the guard because
    # the disposition is process-wide and the tests load this module by path.
    if hasattr(signal, "SIGPIPE"):  # absent on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
