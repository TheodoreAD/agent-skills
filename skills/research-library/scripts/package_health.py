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

    package_health.py pypi httpx
    package_health.py pypi httpx --repo encode/httpx --clone ~/research/repos/github.com--encode--httpx
    package_health.py pypi httpx --json
    package_health.py pypi shellcheck-py --upstream koalaman/shellcheck

**The source is a required subcommand, with no default**, so the registry is the first choice an
agent makes rather than one it carries over from the previous call without noticing. The package's
own GitHub repo is `--repo`; left out, it is read from the source's own metadata (PyPI's
`project_urls`), and the report says which of the two it used, because that lookup can be wrong.

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

Exit codes: 0 ok, 1 error, 2 usage — including the retired `package_health.py <name> <owner/repo>`
form, which names its replacement rather than quietly still meaning PyPI.
"""

from __future__ import annotations

import sys

# Before any import below: `datetime.UTC` is 3.11+, and on 3.10 the failure would otherwise be an
# ImportError naming a stdlib module, with nothing pointing at the interpreter.
if sys.version_info[:2] < (3, 11):  # noqa: UP036 — runs exactly where requires-python is not enforced
    sys.exit(f"package_health.py needs Python 3.11 or newer; this is {sys.version.split()[0]} ({sys.executable})")

import argparse
import json
import os
import platform
import re
import shutil
import signal
import statistics
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any, Protocol

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
NPM_PACKUMENT = "https://registry.npmjs.org/{name}"
CRATES_API = "https://crates.io/api/v1/crates/{name}"
DEBIAN_MADISON = "https://api.ftp-master.debian.org/madison?package={name}&f=json"
LAUNCHPAD_API = "https://api.launchpad.net/1.0/{path}"
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
    """Everything outside this process, behind one seam so every computation below can be tested.

    Every input to this script is a network response, a local command's output or a fact about this
    machine, so all of them are injectable and the tests drive them from captured fixtures. No test
    may reach the network or run a command, which is asserted rather than intended — see
    `tests/unit/test_package_health.py`.
    """

    def pypi(self, name: str) -> dict[str, Any]: ...

    def github(self, path: str) -> Any: ...

    def npm(self, name: str) -> dict[str, Any]: ...

    def crates(self, name: str) -> dict[str, Any]: ...

    def apt_cache(self, *args: str) -> str: ...

    def madison(self, name: str) -> Any: ...

    def launchpad(self, path: str) -> Any: ...

    def machine(self) -> Machine: ...


@dataclass(frozen=True)
class Machine:
    """What a floor is compared against: this machine's values, where they are cheap to read.

    `python` is the interpreter running this script, which is the one `python3` resolves to and not
    necessarily a project's venv; the report says "this python3" for that reason.
    """

    python: str | None
    glibc: str | None
    node: str | None


class LiveTransport:
    """PyPI over HTTPS, GitHub through `gh api` so the caller's own token and rate limit apply."""

    def pypi(self, name: str) -> dict[str, Any]:
        payload = self._get_json(PYPI_JSON.format(name=name), "PyPI", name)
        if not isinstance(payload, dict):
            raise HealthError(f"PyPI returned a non-object for {name!r}")
        return payload

    def npm(self, name: str) -> dict[str, Any]:
        """The **full** packument. The abbreviated form lacks `time` and `scripts`, both read here."""
        # A scoped name keeps its `@` and encodes its `/`: `@biomejs%2Fbiome`.
        payload = self._get_json(NPM_PACKUMENT.format(name=urllib.parse.quote(name, safe="@")), "npm", name)
        if not isinstance(payload, dict):
            raise HealthError(f"npm returned a non-object for {name!r}")
        return payload

    def crates(self, name: str) -> dict[str, Any]:
        """The crate and every version inline. crates.io's policy asks for a descriptive User-Agent."""
        payload = self._get_json(CRATES_API.format(name=urllib.parse.quote(name, safe="")), "crates.io", name)
        if not isinstance(payload, dict):
            raise HealthError(f"crates.io returned a non-object for {name!r}")
        return payload

    def apt_cache(self, *args: str) -> str:
        """`apt-cache` under the C locale, because its labels (`Candidate:`) are translated otherwise."""
        tool = shutil.which("apt-cache")
        if not tool:
            raise HealthError("apt-cache is not on PATH — the apt source needs a Debian or Ubuntu machine")
        env = {**os.environ, "LC_ALL": "C", "LANG": "C"}
        result = subprocess.run([tool, *args], capture_output=True, text=True, check=False, timeout=60, env=env)
        if result.returncode != 0:
            message = next((line for line in result.stderr.splitlines() if line.startswith("E:")), result.stderr)
            kind = NotFound if "No packages found" in result.stderr else HealthError
            raise kind(f"apt-cache {' '.join(args)} failed: {message.strip() or result.returncode}")
        return result.stdout

    def madison(self, name: str) -> Any:
        return self._get_json(DEBIAN_MADISON.format(name=urllib.parse.quote(name, safe="")), "Debian madison", name)

    def launchpad(self, path: str) -> Any:
        return self._get_json(LAUNCHPAD_API.format(path=path), "Launchpad", path)

    def machine(self) -> Machine:
        return Machine(python=platform.python_version(), glibc=_glibc_version(), node=_node_version())

    @staticmethod
    def _get_json(url: str, registry: str, name: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            kind = NotFound if error.code == 404 else HealthError
            raise kind(f"{registry} returned {error.code} for {name!r} — check the name") from error
        except urllib.error.URLError as error:
            raise HealthError(f"{registry} unreachable: {error.reason}") from error

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


class NotFound(HealthError):
    """A registry's 404, which is an answer where a lookup is optional (`@types/<name>`)."""


def _glibc_version() -> str | None:
    """`os.confstr` answers without a subprocess (`glibc 2.39`), and is absent off glibc."""
    try:
        found = os.confstr("CS_GNU_LIBC_VERSION")
    except (AttributeError, ValueError, OSError):
        return None
    if not found or not found.startswith("glibc "):
        return None
    return found.removeprefix("glibc ").strip()


def _node_version() -> str | None:
    """`node --version` when node is on PATH; `None` rather than an error when it is not."""
    node = shutil.which("node")
    if not node:
        return None
    try:
        result = subprocess.run([node, "--version"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip().removeprefix("v") or None


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


def cadence(
    dates: dict[str, datetime],
    yanked: list[str],
    *,
    now: datetime | None = None,
    prerelease: Callable[[str], bool] = is_prerelease,
) -> Cadence:
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

    `prerelease` decides which line a version is on. PyPI's is PEP 440 spelling; a registry or a
    GitHub release list that flags pre-releases itself passes its own flag in.
    """
    now = now or datetime.now(UTC)
    pre = sorted(stamp for version, stamp in dates.items() if prerelease(version))
    stable = sorted(stamp for version, stamp in dates.items() if not prerelease(version))
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


# `https://github.com/o/r`, `git+https://github.com/o/r.git`, `git@github.com:o/r.git`,
# `https://github.com/o/r/blob/main/CHANGELOG.md` — the first two path segments are the repo.
GITHUB_URL_RE = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE)
# npm's shorthand spellings: `github:o/r` and a bare `o/r`.
GITHUB_SHORTHAND_RE = re.compile(r"^(?:github:)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
# A `project_urls` key that names the source, tried before a homepage that merely happens to be one.
SOURCE_KEY_RE = re.compile(r"source|repo|code|github", re.IGNORECASE)
# GitHub paths whose first segment is not an owner: a `Funding` URL is `github.com/sponsors/<who>`.
GITHUB_NON_OWNERS = frozenset({"sponsors", "orgs", "apps", "marketplace", "features", "topics"})


def repo_from_url(url: str | None) -> str | None:
    """`owner/repo` from any common spelling of a GitHub URL, or `None` for anything else."""
    if not url:
        return None
    text = url.strip()
    match = GITHUB_URL_RE.search(text) or GITHUB_SHORTHAND_RE.match(text)
    if not match:
        return None
    owner, name = match.group(1), match.group(2).removesuffix(".git")
    if owner.lower() in GITHUB_NON_OWNERS:
        return None
    return f"{owner}/{name}" if owner and name else None


@dataclass(frozen=True)
class RepoChoice:
    """Which GitHub repo the maintenance axis read, and where that name came from.

    [PITFALL] The metadata lookup can be wrong as well as missing: a homepage can point at an
    organisation's docs repo, and a renamed repo still resolves through GitHub's redirect under its
    old name. So the report always says which of the two it used, and `--repo` stays the override.
    """

    repo: str | None
    origin: str


def pypi_repo(info: dict[str, Any]) -> RepoChoice:
    """The first GitHub URL among `project_urls`, source-like keys first, then `home_page`."""
    urls = info.get("project_urls") or {}
    ordered = sorted(urls.items(), key=lambda item: 0 if SOURCE_KEY_RE.search(item[0]) else 1)
    for key, url in ordered:
        if found := repo_from_url(str(url)):
            return RepoChoice(found, f'PyPI project_urls "{key}"')
    if found := repo_from_url(info.get("home_page")):
        return RepoChoice(found, "PyPI home_page")
    return RepoChoice(None, "PyPI metadata names no GitHub repo")


def choose_repo(explicit: str | None, from_metadata: RepoChoice) -> RepoChoice:
    return RepoChoice(explicit, "--repo") if explicit else from_metadata


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
    description: str | None = None


def repository(payload: dict[str, Any], *, now: datetime | None = None) -> Repository:
    """The repo's own stats. `license_field` is reported and never trusted — see `license_files`.

    [PITFALL] `open_issues_count` counts **pull requests as well as issues**, and it stays non-zero
    on a repo whose issue tracker is switched off entirely. Confirmed 2026-09-02: `encode/httpx`
    reports `has_issues: false` and `open_issues_count: 143`, every one of which is a PR. Scoring
    "open issues relative to project size" off that number compares a review backlog against a
    support backlog, so `has_issues` is carried alongside it and the report says which it is.
    """
    now = now or datetime.now(UTC)
    payload = payload if isinstance(payload, dict) else {}
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
        description=payload.get("description"),
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
class LatestRelease:
    """A repo's latest stable GitHub release: its version, its date and this machine's assets."""

    repo: str
    error: str | None = None
    tag: str | None = None
    version: str | None = None
    published: str | None = None
    published_at: str | None = None
    days_since_release: int | None = None
    assets_total: int = 0
    linux_x86_64: list[Asset] = field(default_factory=list)
    checksum_manifests: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Upstream(LatestRelease):
    """The upstream's latest stable GitHub release, set against the wrapper that repackages it.

    `wrapper_match` is found by spelling only — the upstream version exactly, or followed by a
    separator (`0.11.0` matches the wrapper's `0.11.0.1`). Anything cleverer means parsing every
    project's scheme, and a wrong match reads as a false "tracks upstream"; "no matching wrapper
    release" is the honest answer when the spelling differs, and the reader compares the two
    versions printed beside it.
    """

    wrapper_match: str | None = None
    wrapper_match_date: str | None = None
    lag_days: int | None = None


def tag_version(tag: str) -> str:
    """`v0.11.0` → `0.11.0`, `ripgrep-15.2.0` → `15.2.0`, `@biomejs/biome@2.5.14` → `2.5.14`.

    The last spelling is a monorepo's per-package tag, the form changesets writes; everything up to
    the last `@` is the package name.
    """
    if "@" in tag:
        tag = tag.rsplit("@", 1)[1]
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

    `github_digest` is GitHub's own sha256 of the upload, the asset's `digest` field. It proves
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


def latest_release(transport: Transport, repo: str, *, now: datetime | None = None) -> LatestRelease:
    """Read `repos/<repo>/releases/latest`, which GitHub defines as the newest non-draft, non-prerelease.

    A repo that publishes tags and no releases answers 404 there. That is a finding about the
    repo rather than a failure of the report, so it is carried as `error` and the rest of the
    report still prints.
    """
    now = now or datetime.now(UTC)
    try:
        release = transport.github(f"repos/{repo}/releases/latest")
    except HealthError as error:
        return LatestRelease(repo=repo, error=str(error))
    if not isinstance(release, dict):
        return LatestRelease(repo=repo, error="releases/latest returned a non-object")
    tag = str(release.get("tag_name") or "")
    published = _parse_stamp(release.get("published_at") or release.get("created_at"))
    assets, manifests, total = release_assets(release)
    return LatestRelease(
        repo=repo,
        tag=tag,
        version=tag_version(tag),
        published=published.date().isoformat() if published else None,
        published_at=published.isoformat() if published else None,
        days_since_release=(now - published).days if published else None,
        assets_total=total,
        linux_x86_64=assets,
        checksum_manifests=manifests,
    )


def upstream(
    transport: Transport, repo: str, wrapper_dates: dict[str, datetime], *, now: datetime | None = None
) -> Upstream:
    """The upstream's latest release, plus the wrapper version spelled to match it and the lag."""
    base = latest_release(transport, repo, now=now)
    carried = {spec.name: getattr(base, spec.name) for spec in fields(base)}
    if base.error or not base.version:
        return Upstream(**carried)
    match = wrapper_match(base.version, wrapper_dates)
    match_date = wrapper_dates.get(match) if match else None
    # `published` is cut to a date for the report; the lag is measured from the full stamp.
    published = _parse_stamp(base.published_at)
    return Upstream(
        **carried,
        wrapper_match=match,
        wrapper_match_date=match_date.date().isoformat() if match_date else None,
        lag_days=(match_date - published).days if match_date and published else None,
    )


RELEASE_PAGE_SIZE = 100


@dataclass(frozen=True)
class ReleaseList:
    """The GitHub releases list, read as a cadence: what a registry's version history is elsewhere."""

    cadence: Cadence
    read: int
    drafts: int
    truncated: bool


def github_release_dates(releases: list[dict[str, Any]]) -> tuple[dict[str, datetime], set[str]]:
    """One date per published release, and the tags GitHub itself flags as pre-releases.

    Drafts are skipped: they are unpublished, and GitHub returns them only to a caller who can push.
    """
    dates: dict[str, datetime] = {}
    flagged: set[str] = set()
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "")
        stamp = _parse_stamp(release.get("published_at") or release.get("created_at"))
        if tag and stamp:
            dates[tag] = stamp
            if release.get("prerelease"):
                flagged.add(tag)
    return dates, flagged


def release_list(transport: Transport, repo: str, *, now: datetime | None = None) -> ReleaseList:
    """The stable-release cadence over the newest `RELEASE_PAGE_SIZE` releases, one request.

    A release is a pre-release when GitHub flags it **or** its tag is spelled as one: projects that
    publish `v2.0.0-rc.1` without ticking the box are common, and the flag alone would count them.
    """
    releases = transport.github(f"repos/{repo}/releases?per_page={RELEASE_PAGE_SIZE}")
    releases = releases if isinstance(releases, list) else []
    dates, flagged = github_release_dates(releases)
    return ReleaseList(
        cadence=cadence(dates, [], now=now, prerelease=lambda tag: tag in flagged or is_prerelease(tag_version(tag))),
        read=len(releases),
        drafts=sum(1 for release in releases if isinstance(release, dict) and release.get("draft")),
        truncated=len(releases) >= RELEASE_PAGE_SIZE,
    )


# ------------------------------------------------------------------------------------------------
# Floors: every minimum version the metadata states, set against this machine


@dataclass(frozen=True)
class Floor:
    """One stated minimum: what it constrains, the requirement as written, and where it was read.

    Read from the metadata and never inferred. `met` is `None` when the comparison was not made —
    this machine's value is not cheaply readable, or the requirement is spelled in a form this does
    not parse — and the report says which, rather than guessing either way.
    """

    what: str
    required: str
    source: str
    machine: str | None = None
    met: bool | None = None
    note: str | None = None


VERSION_PREFIX_RE = re.compile(r"^v?(\d+(?:\.\d+)*)")
PEP440_CLAUSE_RE = re.compile(r"^(~=|===|==|!=|<=|>=|<|>)\s*(\S+)$")
# `manylinux_2_17_x86_64` is PEP 600's spelling; the three legacy aliases are fixed glibc versions.
MANYLINUX_RE = re.compile(r"^manylinux_(\d+)_(\d+)_x86_64$")
MUSLLINUX_RE = re.compile(r"^musllinux_(\d+)_(\d+)_x86_64$")
MANYLINUX_LEGACY = {"manylinux1_x86_64": (2, 5), "manylinux2010_x86_64": (2, 12), "manylinux2014_x86_64": (2, 17)}


def version_tuple(text: str | None) -> tuple[int, ...] | None:
    """The leading numeric part of a version: `3.12.3` → (3, 12, 3), `18.0.0-rc1` → (18, 0, 0)."""
    match = VERSION_PREFIX_RE.match((text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def _padded(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)), right + (0,) * (width - len(right))


def _compare(op: str, have: tuple[int, ...], want: tuple[int, ...]) -> bool:
    have, want = _padded(have, want)
    return {
        ">=": have >= want,
        ">": have > want,
        "<=": have <= want,
        "<": have < want,
        "==": have == want,
        "===": have == want,
        "!=": have != want,
    }[op]


def python_spec_met(spec: str, version: str | None) -> bool | None:
    """Whether `version` satisfies a PEP 440 specifier set such as `>=3.9,<4`; `None` if unparsed."""
    have = version_tuple(version)
    clauses = [clause.strip() for clause in spec.split(",") if clause.strip()]
    if have is None or not clauses:
        return None
    verdicts = [_pep440_clause_met(clause, have) for clause in clauses]
    if any(verdict is None for verdict in verdicts):
        return None
    return all(verdicts)


def _pep440_clause_met(clause: str, have: tuple[int, ...]) -> bool | None:
    match = PEP440_CLAUSE_RE.match(clause)
    if not match:
        return None
    op, target = match.groups()
    if target.endswith(".*"):
        prefix = version_tuple(target.removesuffix(".*"))
        if prefix is None or op not in ("==", "!="):
            return None
        return (have[: len(prefix)] == prefix) == (op == "==")
    want = version_tuple(target)
    if want is None:
        return None
    if op == "~=":
        return len(want) >= 2 and _compare(">=", have, want) and have[: len(want) - 1] == want[:-1]
    return _compare(op, have, want)


NODE_COMPARATOR_RE = re.compile(r"^(\^|~|>=|<=|>|<|=)?v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?(?:[-+]\S*)?$")


def _node_comparator(token: str, have: tuple[int, ...]) -> bool | None:
    """One npm semver comparator: `>=18`, `^14.21.3`, `~1.2`, `18.x`, `*`."""
    match = NODE_COMPARATOR_RE.match(token)
    if not match:
        return None
    op, *raw = match.groups()
    given = [part for part in raw if part is not None]
    wild = next((index for index, part in enumerate(given) if not part.isdigit()), len(given))
    parts = tuple(int(part) for part in given[:wild])
    if op in (None, "="):
        if not parts:
            return True
        # An X-range or a partial version means every version under that prefix.
        return have[: len(parts)] == parts if wild < 3 or len(given) < 3 else _compare("==", have, parts)
    if op in (">=", ">", "<=", "<"):
        return _compare(op, have, parts or (0,))
    if op == "^":
        # Caret: the leftmost non-zero component is fixed.
        pivot = next((index for index, part in enumerate(parts) if part != 0), len(parts) - 1)
        return _compare(">=", have, parts) and have[: pivot + 1] == parts[: pivot + 1]
    # Tilde: the minor is fixed when given, else the major.
    keep = 2 if len(parts) >= 2 else 1
    return _compare(">=", have, parts) and have[:keep] == parts[:keep]


def node_range_met(spec: str, version: str | None) -> bool | None:
    """Whether `version` satisfies an npm `engines` range (`||` of space-joined comparators)."""
    have = version_tuple(version)
    if have is None:
        return None
    verdicts: list[bool | None] = []
    for alternative in spec.split("||"):
        text = re.sub(r"(>=|<=|>|<|=|\^|~)\s+", r"\1", alternative.strip())
        if " - " in text:
            low, _, high = text.partition(" - ")
            low_met, high_met = _node_comparator(f">={low.strip()}", have), _node_comparator(f"<={high.strip()}", have)
            verdicts.append(None if low_met is None or high_met is None else low_met and high_met)
            continue
        tokens = text.split() or ["*"]
        results = [_node_comparator(token, have) for token in tokens]
        verdicts.append(None if any(result is None for result in results) else all(results))
    if any(verdict is True for verdict in verdicts):
        return True
    return None if any(verdict is None for verdict in verdicts) else False


def wheel_libc_floor(platform_tag: str) -> tuple[str, tuple[int, ...]] | None:
    """The lowest libc a Linux x86_64 wheel accepts: `("glibc", (2, 17))`, or musl for musllinux.

    A compressed tag set installs wherever any member does, so the lowest member is the floor.
    """
    glibc: list[tuple[int, ...]] = []
    musl: list[tuple[int, ...]] = []
    for tag in platform_tag.split("."):
        if tag in MANYLINUX_LEGACY:
            glibc.append(MANYLINUX_LEGACY[tag])
        elif match := MANYLINUX_RE.match(tag):
            glibc.append((int(match.group(1)), int(match.group(2))))
        elif match := MUSLLINUX_RE.match(tag):
            musl.append((int(match.group(1)), int(match.group(2))))
    if glibc:
        return "glibc", min(glibc)
    if musl:
        return "musl", min(musl)
    return None


def _dotted(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def pypi_floors(requires_python: str | None, ships: ReleaseFiles, machine: Machine | None) -> list[Floor]:
    """`requires_python`, and the glibc floor the manylinux tags of this machine's wheels state."""
    here_python = machine.python if machine else None
    here_glibc = machine.glibc if machine else None
    shown_python = f"python3 {here_python}" if here_python else None
    floors = [
        Floor("python", requires_python, "requires_python", shown_python, python_spec_met(requires_python, here_python))
        if requires_python
        else Floor("python", "undeclared", "requires_python", shown_python, note="no floor stated")
    ]
    tagged = [
        found
        for entry in ships.files
        if entry.filename in ships.linux_x86_64_wheels
        and entry.platform_tag
        and (found := wheel_libc_floor(entry.platform_tag))
    ]
    glibc = sorted(version for family, version in tagged if family == "glibc")
    if glibc:
        spread = f", highest {_dotted(glibc[-1])}" if glibc[-1] != glibc[0] else ""
        have = version_tuple(here_glibc)
        floors.append(
            Floor(
                "glibc",
                f">={_dotted(glibc[0])}",
                f"manylinux tag, lowest of {len(glibc)} wheel(s){spread}",
                f"glibc {here_glibc}" if here_glibc else None,
                _compare(">=", have, glibc[0]) if have else None,
            )
        )
    elif tagged:
        floors.append(
            Floor(
                "libc",
                "musl",
                "musllinux tag — no manylinux wheel",
                f"glibc {here_glibc}" if here_glibc else None,
                False if here_glibc else None,
                note="pip on a glibc machine skips a musllinux wheel and falls back to the sdist",
            )
        )
    return floors


def asset_floors(release: LatestRelease, machine: Machine | None) -> list[Floor]:
    """The libc family each Linux asset names. A numeric glibc floor is not in a name.

    [DECISION] Reading it would mean downloading the binary and reading its ELF version needs,
    which is out of scope; the family is what the name states, and the note says what it does not.
    """
    here = f"glibc {machine.glibc}" if machine and machine.glibc else None
    notes = {
        "gnu": "the numeric glibc floor is not in the name; it is in the binary's ELF version needs",
        "musl": "a musl build runs on a glibc machine when statically linked, which the name does not say",
        "unspecified": "the name states no libc",
    }
    families = sorted({asset.libc for asset in release.linux_x86_64})
    return [Floor("libc", family, "asset name", here, None, notes.get(family)) for family in families]


# ------------------------------------------------------------------------------------------------
# npm: the packument, and the platform package that actually carries the binary

# The lifecycle scripts npm runs when a package is installed from the registry. `prepare` is
# absent on purpose: npm runs it for a git or local install, not for a registry tarball.
NPM_INSTALL_HOOKS = ("preinstall", "install", "postinstall")
NPM_TIME_META = frozenset({"created", "modified"})


def npm_is_prerelease(version: str) -> bool:
    """Semver: anything with a `-` before any `+build` is a pre-release (`2.0.0-beta.6`, nightlies)."""
    return "-" in version.split("+", 1)[0]


def npm_release_dates(doc: dict[str, Any]) -> dict[str, datetime]:
    """One date per published version from the `time` map, which also carries `created`/`modified`.

    Versions no longer in `versions` were unpublished; their `time` entries remain and are skipped.
    """
    published = doc.get("versions") or {}
    dates: dict[str, datetime] = {}
    for version, stamp in (doc.get("time") or {}).items():
        if version in NPM_TIME_META or version not in published:
            continue
        if parsed := _parse_stamp(stamp):
            dates[version] = parsed
    return dates


def npm_latest(doc: dict[str, Any]) -> str | None:
    """`dist-tags.latest` — never the newest key in `versions`, which is any line's newest publish.

    [PITFALL] Confirmed 2026-09-27: express's `latest-4` line (4.22.3) was published after its
    `latest` (5.2.1), and biome's `nightly` and `beta` tags sit beside `latest`. Sorting `versions`
    by date answers "what was published last", which is not what `npm install` resolves to.
    """
    tags = doc.get("dist-tags") or {}
    return tags.get("latest") if isinstance(tags, dict) else None


@dataclass(frozen=True)
class PlatformPackage:
    """One `optionalDependencies` entry that carries a binary for a platform, read from its own packument."""

    name: str
    spec: str
    version: str | None = None
    os: list[str] = field(default_factory=list)
    cpu: list[str] = field(default_factory=list)
    libc: list[str] = field(default_factory=list)
    unpacked_size: int | None = None
    file_count: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class NpmShips:
    version: str | None
    unpacked_size: int | None
    file_count: int | None
    tarball: str | None
    provenance: str | None
    bin: dict[str, str]
    install_scripts: dict[str, str]
    optional_dependencies: int
    platform_packages: list[PlatformPackage]
    chosen: str | None

    @property
    def install_size(self) -> int | None:
        """The wrapper plus this machine's platform package: what `npm install` actually writes."""
        chosen = next((pkg for pkg in self.platform_packages if pkg.name == self.chosen), None)
        extra = chosen.unpacked_size if chosen else 0
        if self.unpacked_size is None or extra is None:
            return None
        return self.unpacked_size + extra


@dataclass(frozen=True)
class NpmTyping:
    """Only dynamically typed ecosystems get a typing line; see the floors and typing decisions."""

    verdict: str
    detail: str


def _platform_candidates(optional: dict[str, str]) -> list[tuple[str, str]]:
    """The optional dependencies **named** for Linux x86_64, which decides only what to fetch.

    The name is not the verdict. Each candidate's own `os`/`cpu`/`libc` fields are read once it is
    fetched; the name only keeps the fetch count to one or two instead of esbuild's twenty-six.
    """
    return [
        (name, str(spec)) for name, spec in optional.items() if "linux" in name.lower() and ASSET_ARCH_RE.search(name)
    ]


def resolve_platform_package(transport: Transport, name: str, spec: str) -> PlatformPackage:
    """Read the platform package's own entry for the version the wrapper pins.

    [PITFALL] The pin is normally the wrapper's exact version, and a pin that names no published
    version is itself the finding. Confirmed on the real capture: biome 2.0.3 pinned every
    platform package to `workspace:*`, a monorepo spelling that leaked into a published manifest,
    and 2.0.1 to 2.0.3 all carry a deprecation for exactly that.
    """
    try:
        doc = transport.npm(name)
    except HealthError as error:
        return PlatformPackage(name=name, spec=spec, error=str(error))
    versions = doc.get("versions") or {}
    if spec not in versions:
        return PlatformPackage(name=name, spec=spec, error=f"pinned to {spec!r}, which names no published version")
    entry = versions[spec]
    dist = entry.get("dist") or {}
    return PlatformPackage(
        name=name,
        spec=spec,
        version=spec,
        os=list(entry.get("os") or []),
        cpu=list(entry.get("cpu") or []),
        libc=list(entry.get("libc") or []),
        unpacked_size=_int_or_none(dist.get("unpackedSize")),
        file_count=_int_or_none(dist.get("fileCount")),
    )


def _choose_platform(packages: list[PlatformPackage], machine: Machine | None) -> str | None:
    """The package npm would install here: a glibc machine takes `glibc` or an unstated libc."""
    usable = [pkg for pkg in packages if pkg.error is None]
    if machine is None or machine.glibc is None:
        return usable[0].name if len(usable) == 1 else None
    for pkg in usable:
        if not pkg.libc or "glibc" in pkg.libc:
            return pkg.name
    return None


def npm_ships(
    transport: Transport, entry: dict[str, Any], *, machine: Machine | None, resolve: bool = True
) -> NpmShips:
    dist = entry.get("dist") or {}
    provenance = ((dist.get("attestations") or {}).get("provenance") or {}).get("predicateType")
    scripts = entry.get("scripts") or {}
    optional = entry.get("optionalDependencies") or {}
    packages = (
        [resolve_platform_package(transport, name, spec) for name, spec in _platform_candidates(optional)]
        if resolve
        else []
    )
    raw_bin = entry.get("bin") or {}
    # `bin` may be a bare string, meaning one command named after the package.
    bins = {str(entry.get("name", "")).split("/")[-1]: raw_bin} if isinstance(raw_bin, str) else dict(raw_bin)
    return NpmShips(
        version=entry.get("version"),
        unpacked_size=_int_or_none(dist.get("unpackedSize")),
        file_count=_int_or_none(dist.get("fileCount")),
        tarball=dist.get("tarball"),
        provenance=provenance,
        bin={str(key): str(value) for key, value in bins.items()},
        install_scripts={hook: str(scripts[hook]) for hook in NPM_INSTALL_HOOKS if hook in scripts},
        optional_dependencies=len(optional),
        platform_packages=packages,
        chosen=_choose_platform(packages, machine),
    )


def _exports_declare_types(exports: Any) -> bool:
    """Modern packages state their types only as an `exports` condition, never as `types`."""
    if isinstance(exports, dict):
        return "types" in exports or any(_exports_declare_types(value) for value in exports.values())
    if isinstance(exports, list):
        return any(_exports_declare_types(value) for value in exports)
    return False


def types_package_name(name: str) -> str:
    """DefinitelyTyped's spelling: `express` → `@types/express`, `@scope/pkg` → `@types/scope__pkg`."""
    return "@types/" + (name[1:].replace("/", "__") if name.startswith("@") else name)


def npm_typing(transport: Transport, name: str, entry: dict[str, Any]) -> NpmTyping:
    """Own types, a separate `@types` package, or neither — one extra request only for the last two."""
    for key in ("types", "typings"):
        if entry.get(key):
            return NpmTyping("own", f"ships its own ({key}: {entry[key]})")
    if _exports_declare_types(entry.get("exports")):
        return NpmTyping("own", "ships its own (a types condition in exports)")
    if name.startswith("@types/"):
        return NpmTyping("own", "this is a DefinitelyTyped package")
    hint = "; typescript is a devDependency" if "typescript" in (entry.get("devDependencies") or {}) else ""
    if entry.get("bin"):
        hint += "; it ships a command, so this matters only if you import it"
    separate = types_package_name(name)
    try:
        doc = transport.npm(separate)
    except NotFound:
        return NpmTyping("none", f"NONE — no types field and no {separate}{hint}")
    except HealthError as error:
        return NpmTyping("unknown", f"{separate} not checked: {error}")
    latest = npm_latest(doc) or "?"
    return NpmTyping("@types", f"separate {separate} {latest} — maintained apart from the package{hint}")


def npm_repo(doc: dict[str, Any]) -> RepoChoice:
    repository = doc.get("repository")
    url = repository.get("url") if isinstance(repository, dict) else repository
    if found := repo_from_url(str(url) if url else None):
        return RepoChoice(found, 'npm "repository"')
    return RepoChoice(None, 'npm "repository" names no GitHub repo')


def npm_floors(entry: dict[str, Any], ships: NpmShips, machine: Machine | None) -> list[Floor]:
    """`engines`, and the chosen platform package's `os`/`cpu`/`libc`."""
    engines = entry.get("engines") or {}
    engines = engines if isinstance(engines, dict) else {}
    here_node = machine.node if machine else None
    floors: list[Floor] = []
    if node := engines.get("node"):
        floors.append(
            Floor(
                "node",
                str(node),
                "engines.node",
                f"node {here_node}" if here_node else None,
                node_range_met(str(node), here_node),
            )
        )
    else:
        floors.append(Floor("node", "undeclared", "engines.node", note="no floor stated"))
    if npm := engines.get("npm"):
        floors.append(Floor("npm", str(npm), "engines.npm", note="npm's own version is not read here"))
    candidates = [pkg for pkg in ships.platform_packages if pkg.error is None]
    chosen = next((pkg for pkg in candidates if pkg.name == ships.chosen), None)
    here_libc = f"glibc {machine.glibc}" if machine and machine.glibc else None
    if chosen:
        stated = "/".join(",".join(part) or "any" for part in (chosen.os, chosen.cpu, chosen.libc))
        floors.append(Floor("platform", stated, f"{chosen.name} os/cpu/libc", here_libc, True if here_libc else None))
    elif candidates:
        stated = ", ".join(f"{pkg.name} ({','.join(pkg.libc) or 'libc unstated'})" for pkg in candidates)
        floors.append(
            Floor(
                "platform",
                "none for this libc",
                stated,
                here_libc,
                False if here_libc else None,
                note="no Linux x64 platform package states this machine's libc",
            )
        )
    return floors


@dataclass(frozen=True)
class NpmHealth:
    name: str
    version: str | None
    description: str | None
    license: str | None
    dist_tags: dict[str, str]
    cadence: Cadence
    deprecated: list[str]
    latest_deprecated: str | None
    runtime_dependencies: list[str]
    typing: NpmTyping
    ships: NpmShips
    repo_choice: RepoChoice
    repository: Repository | None
    contributors: Contributors | None
    issues: IssueSample | None
    upstream: Upstream | None
    floors: list[Floor]


def gather_npm(
    transport: Transport,
    name: str,
    repo: str | None,
    *,
    upstream_repo: str | None = None,
    now: datetime | None = None,
    machine: Machine | None = None,
) -> NpmHealth:
    """npm's answer from the full packument, plus one fetch per Linux x64 platform package."""
    now = now or datetime.now(UTC)
    doc = transport.npm(name)
    versions = doc.get("versions") or {}
    latest = npm_latest(doc)
    entry = versions.get(latest or "") or {}
    dates = npm_release_dates(doc)
    ships = npm_ships(transport, entry, machine=machine)
    choice = choose_repo(repo, npm_repo(doc))
    repo_facts, people, issues = maintenance(transport, choice.repo, now=now)
    tags = doc.get("dist-tags") or {}
    return NpmHealth(
        name=str(doc.get("name") or name),
        version=latest,
        description=doc.get("description") or entry.get("description"),
        license=entry.get("license") or doc.get("license"),
        dist_tags={str(key): str(value) for key, value in tags.items()} if isinstance(tags, dict) else {},
        cadence=cadence(dates, [], now=now, prerelease=npm_is_prerelease),
        deprecated=sorted(version for version, item in versions.items() if (item or {}).get("deprecated")),
        latest_deprecated=entry.get("deprecated"),
        runtime_dependencies=sorted(entry.get("dependencies") or {}),
        typing=npm_typing(transport, str(doc.get("name") or name), entry),
        ships=ships,
        repo_choice=choice,
        repository=repo_facts,
        contributors=people,
        issues=issues,
        upstream=upstream(transport, upstream_repo, dates, now=now) if upstream_repo else None,
        floors=npm_floors(entry, ships, machine),
    )


# ------------------------------------------------------------------------------------------------
# crates.io: the crate API, and the GitHub release that holds the binary


@dataclass(frozen=True)
class CrateShips:
    """What `cargo install` builds, and whether a prebuilt binary exists instead.

    [PITFALL] A crate is source. `cargo install` compiles it, which costs a toolchain at least as
    new as the MSRV plus minutes of build time; the prebuilt binaries a Rust CLI ships are GitHub
    release assets, which `cargo-binstall` resolves. So the release view is read whenever the crate
    has binaries and a repo, and never counted as the crate itself.
    """

    version: str | None
    crate_size: int | None
    bin_names: list[str]
    has_lib: bool | None
    edition: str | None
    checksum: str | None


@dataclass(frozen=True)
class CratesHealth:
    name: str
    version: str | None
    description: str | None
    license: str | None
    downloads: int | None
    recent_downloads: int | None
    cadence: Cadence
    ships: CrateShips
    repo_choice: RepoChoice
    repository: Repository | None
    contributors: Contributors | None
    issues: IssueSample | None
    release: LatestRelease | None
    floors: list[Floor]


def crate_stable_version(crate: dict[str, Any], versions: list[dict[str, Any]]) -> str | None:
    """`max_stable_version`, crates.io's own answer; else the newest non-yanked, non-pre-release."""
    if stated := crate.get("max_stable_version"):
        return str(stated)
    candidates = [
        (stamp, str(item.get("num")))
        for item in versions
        if item.get("num") and not item.get("yanked") and not npm_is_prerelease(str(item.get("num")))
        if (stamp := _parse_stamp(item.get("created_at")))
    ]
    return max(candidates)[1] if candidates else crate.get("max_version")


def crates_repo(crate: dict[str, Any]) -> RepoChoice:
    if found := repo_from_url(crate.get("repository")):
        return RepoChoice(found, 'crates.io "repository"')
    if found := repo_from_url(crate.get("homepage")):
        return RepoChoice(found, 'crates.io "homepage"')
    return RepoChoice(None, 'crates.io "repository" names no GitHub repo')


def crate_floors(entry: dict[str, Any], release: LatestRelease | None, machine: Machine | None) -> list[Floor]:
    """`rust_version` (the MSRV), which is null unless the crate declares one — so null is undeclared."""
    msrv = entry.get("rust_version")
    floors = [
        Floor("rust", f">={msrv}", "rust_version (MSRV)", note="needed only to build it; rustc is not read here")
        if msrv
        else Floor("rust", "undeclared", "rust_version (MSRV)", note="null means the crate states none, not unknown")
    ]
    if release is not None:
        floors.extend(asset_floors(release, machine))
    return floors


def gather_crates(
    transport: Transport,
    name: str,
    repo: str | None,
    *,
    now: datetime | None = None,
    machine: Machine | None = None,
) -> CratesHealth:
    """crates.io's answer, and the GitHub release view when the crate ships binaries."""
    now = now or datetime.now(UTC)
    payload = transport.crates(name)
    crate = payload.get("crate") or {}
    versions = [item for item in payload.get("versions") or [] if isinstance(item, dict)]
    stable = crate_stable_version(crate, versions)
    entry = next((item for item in versions if item.get("num") == stable), {})
    stamps = {str(item["num"]): _parse_stamp(item.get("created_at")) for item in versions if item.get("num")}
    dates = {version: stamp for version, stamp in stamps.items() if stamp}
    yanked = sorted(str(item["num"]) for item in versions if item.get("num") and item.get("yanked"))
    choice = choose_repo(repo, crates_repo(crate))
    repo_facts, people, issues = maintenance(transport, choice.repo, now=now)
    bins = [str(found) for found in entry.get("bin_names") or []]
    release = latest_release(transport, choice.repo, now=now) if bins and choice.repo else None
    return CratesHealth(
        name=str(crate.get("name") or name),
        version=stable,
        description=(crate.get("description") or "").strip() or None,
        license=entry.get("license"),
        downloads=_int_or_none(crate.get("downloads")),
        recent_downloads=_int_or_none(crate.get("recent_downloads")),
        cadence=cadence(dates, yanked, now=now, prerelease=npm_is_prerelease),
        ships=CrateShips(
            version=stable,
            crate_size=_int_or_none(entry.get("crate_size")),
            bin_names=bins,
            has_lib=entry.get("has_lib") if isinstance(entry.get("has_lib"), bool) else None,
            edition=entry.get("edition"),
            checksum=entry.get("checksum"),
        ),
        repo_choice=choice,
        repository=repo_facts,
        contributors=people,
        issues=issues,
        release=release,
        floors=crate_floors(entry, release, machine),
    )


# ------------------------------------------------------------------------------------------------
# apt: this machine's sources, and which distro releases carry which version

# ` *** 14.1.0-1 500` — the `***` marks the installed version.
APT_VERSION_LINE_RE = re.compile(r"^\s*(\*\*\*)?\s+(\S+)\s+(-?\d+)\s*$")
# `        500 http://archive.ubuntu.com/ubuntu noble/universe amd64 Packages`, and a flat repo's
# `500 https://example.org/repo ./ Packages`, which has no component.
APT_SOURCE_LINE_RE = re.compile(r"^\s+(-?\d+)\s+(\S+)\s+(\S+?)(?:/(\S+))?(?:\s+(\S+))?\s+Packages\s*$")
APT_POCKET_RE = re.compile(r"-(updates|security|backports|proposed)$")
DEPENDS_RE = re.compile(r"^\s*([a-z0-9][a-z0-9.+-]*)(?::\S+)?\s*\(\s*(>=|<=|>>|<<|=)\s*([^)\s]+)\s*\)")
UBUNTU_HOSTS = ("archive.ubuntu.com", "security.ubuntu.com", "ports.ubuntu.com")
DEBIAN_HOSTS = ("deb.debian.org", "security.debian.org", "ftp.debian.org")
# Ubuntu's documented policy: an LTS is the April release of an even year.
UBUNTU_LTS_RE = re.compile(r"^\d*[02468]\.04$")
LAUNCHPAD_PAGE = 300


@dataclass(frozen=True)
class AptSource:
    priority: int
    url: str
    suite: str | None
    component: str | None


@dataclass(frozen=True)
class AptPolicy:
    installed: str | None
    candidate: str | None
    versions: dict[str, list[AptSource]]


def parse_apt_policy(text: str) -> AptPolicy | None:
    """`apt-cache policy <name>`; `None` when apt printed nothing, which is how it says "unknown"."""
    installed = candidate = None
    versions: dict[str, list[AptSource]] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Installed:"):
            installed = _apt_none(stripped.removeprefix("Installed:"))
        elif stripped.startswith("Candidate:"):
            candidate = _apt_none(stripped.removeprefix("Candidate:"))
        elif (source := APT_SOURCE_LINE_RE.match(line)) and current:
            priority, url, suite, component, _ = source.groups()
            versions[current].append(AptSource(int(priority), url, suite, component))
        elif line.strip().endswith("/var/lib/dpkg/status") and current:
            continue
        elif (version := APT_VERSION_LINE_RE.match(line)) and not stripped.endswith(":"):
            current = version.group(2)
            versions.setdefault(current, [])
    if installed is None and candidate is None and not versions:
        return None
    return AptPolicy(installed, candidate, versions)


def _apt_none(value: str) -> str | None:
    value = value.strip()
    return None if value in ("", "(none)") else value


def parse_apt_show(text: str, version: str | None) -> dict[str, str]:
    """The `apt-cache show` stanza for `version` (the first when it is absent), as a field map."""
    stanzas: list[dict[str, str]] = []
    fields_: dict[str, str] = {}
    key: str | None = None
    for line in [*text.splitlines(), ""]:
        if not line.strip():
            if fields_:
                stanzas.append(fields_)
            fields_, key = {}, None
        elif line[0] in " \t" and key:
            fields_[key] += "\n" + line.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            fields_[key] = value.strip()
    return next((stanza for stanza in stanzas if stanza.get("Version") == version), stanzas[0] if stanzas else {})


def debian_upstream_version(version: str) -> str:
    """`1:8.5.0-2ubuntu10.15` → `8.5.0`: drop the epoch, the Debian revision and any `+dfsg`/`~` suffix."""
    bare = re.sub(r"^\d+:", "", version)
    if "-" in bare:
        bare = bare.rsplit("-", 1)[0]
    match = re.match(r"\d+(?:\.\d+)*", bare)
    return match.group(0) if match else bare


@dataclass(frozen=True)
class AptOrigin:
    """Where the candidate comes from, which decides who maintains it."""

    host: str | None
    suite: str | None
    component: str | None
    pockets: list[str]
    distro: str | None

    @property
    def release(self) -> str | None:
        """`noble-security` → `noble`: the release the pocket belongs to."""
        return APT_POCKET_RE.sub("", self.suite) if self.suite else None


def apt_origin(policy: AptPolicy) -> AptOrigin:
    sources = [source for source in policy.versions.get(policy.candidate or "", []) if "://" in source.url]
    if not sources:
        return AptOrigin(None, None, None, [], None)
    best = max(sources, key=lambda source: source.priority)
    host = urllib.parse.urlparse(best.url).hostname
    distro = "ubuntu" if host in UBUNTU_HOSTS else "debian" if host in DEBIAN_HOSTS else None
    # The release pocket first, then updates and security, so the base suite is what is reported.
    named = {source.suite for source in sources if source.suite}
    suites = sorted(named, key=lambda suite: (bool(APT_POCKET_RE.search(suite)), suite))
    return AptOrigin(host, suites[0] if suites else best.suite, best.component, suites, distro)


def support_line(origin: AptOrigin) -> str:
    """Who fixes it. Canonical's own statement: `main` is supported for the release's life, and
    `universe` gets Canonical security fixes only through Ubuntu Pro (ESM); a third-party repo is its
    publisher's responsibility, not the distro's."""
    if origin.distro is None:
        return f"THIRD-PARTY REPO ({origin.host or 'unknown'}) — maintained by its publisher, not the distro"
    if origin.distro == "debian":
        return f"Debian {origin.component or '?'} — security support from the Debian security team for main"
    if origin.component in ("main", "restricted"):
        return f"Ubuntu {origin.component} — Canonical-supported, security updates for the life of the release"
    component = origin.component or "?"
    return f"Ubuntu {component} — community-maintained; Canonical security fixes only with Ubuntu Pro (ESM)"


@dataclass(frozen=True)
class AptUpstream:
    repo: str
    origin: str
    packaged: str
    error: str | None = None
    packaged_released: str | None = None
    latest: str | None = None
    latest_released: str | None = None
    newer_releases: int | None = None
    lag_days: int | None = None


def apt_upstream(transport: Transport, repo: str, origin: str, packaged: str) -> AptUpstream:
    """How far the packaged version is behind upstream's stable GitHub releases.

    `lag_days` runs from the packaged upstream version's release to upstream's newest: how old the
    distro's copy is relative to what upstream would give you today. The version match is by
    spelling, as for wrappers, so a miss leaves the packaged date unknown rather than guessed.
    """
    try:
        releases = transport.github(f"repos/{repo}/releases?per_page={RELEASE_PAGE_SIZE}")
    except HealthError as error:
        return AptUpstream(repo, origin, packaged, error=str(error))
    dates, flagged = github_release_dates(releases if isinstance(releases, list) else [])
    stable = {
        tag_version(tag): stamp
        for tag, stamp in dates.items()
        if tag not in flagged and not is_prerelease(tag_version(tag))
    }
    if not stable:
        return AptUpstream(repo, origin, packaged, error="no stable GitHub releases to compare with")
    latest = max(stable, key=lambda version: stable[version])
    match = wrapper_match(packaged, stable)
    packaged_stamp = stable.get(match) if match else None
    have = version_tuple(packaged) or (0,)
    newer = sum(1 for version in stable if (version_tuple(version) or (0,)) > have)
    return AptUpstream(
        repo,
        origin,
        packaged,
        packaged_released=packaged_stamp.date().isoformat() if packaged_stamp else None,
        latest=latest,
        latest_released=stable[latest].date().isoformat(),
        newer_releases=newer,
        lag_days=(stable[latest] - packaged_stamp).days if packaged_stamp else None,
    )


@dataclass(frozen=True)
class DistroRow:
    distro: str
    release: str
    label: str
    versions: list[str]
    pocket: str | None = None
    component: str | None = None
    this_machine: bool = False


@dataclass(frozen=True)
class CrossRelease:
    rows: list[DistroRow]
    error: str | None = None
    omitted: int = 0


def debian_cross_release(payload: Any) -> CrossRelease:
    """Madison's JSON, one row per suite. `-debug` and `buildd-` suites are archive plumbing."""
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return CrossRelease([], error="not in Debian")
    rows: list[DistroRow] = []
    for suites in payload[0].values():
        for suite, versions in (suites or {}).items():
            if suite.endswith("-debug") or suite.startswith("buildd-"):
                continue
            binaries = [
                version
                for version, detail in versions.items()
                if {"amd64", "all"} & set((detail or {}).get("architectures") or [])
            ]
            rows.append(
                DistroRow(
                    "debian",
                    suite,
                    "",
                    binaries or list(versions),
                    component=next(iter(versions.values()), {}).get("component"),
                )
            )
    return CrossRelease(rows)


def ubuntu_cross_release(sources: Any, series: Any, this_release: str | None) -> CrossRelease:
    """Launchpad's published sources per series, newest first; Proposed and obsolete series are left out.

    [PITFALL] Launchpad keeps an end-of-life series' publications as `Published`: rust-ripgrep's
    list still carries mantic and lunar. So the series list's own `status` decides what is shown,
    and the count left out is printed, rather than presenting a dead release as an option.
    """
    entries = [entry for entry in (sources or {}).get("entries", []) if entry.get("pocket") != "Proposed"]
    known = [entry for entry in (series or {}).get("entries", []) if isinstance(entry, dict)]
    rows: list[DistroRow] = []
    omitted = 0
    for item in sorted(known, key=lambda entry: version_tuple(entry.get("version")) or (0,), reverse=True):
        name = str(item.get("name") or "")
        published = [entry for entry in entries if str(entry.get("distro_series_link", "")).endswith(f"/{name}")]
        is_here = name == this_release
        if item.get("status") == "Obsolete" and not is_here:
            omitted += 1 if published else 0
            continue
        if not published and not is_here:
            continue
        lts = " LTS" if UBUNTU_LTS_RE.match(str(item.get("version") or "")) else ""
        label = f"{item.get('version')}{lts}, {item.get('status')}"
        newest = max(published, key=lambda entry: str(entry.get("date_published") or ""), default=None)
        rows.append(
            DistroRow(
                "ubuntu",
                name,
                label,
                [str(newest["source_package_version"])] if newest else [],
                pocket=newest.get("pocket") if newest else None,
                component=newest.get("component_name") if newest else None,
                this_machine=is_here,
            )
        )
    return CrossRelease(rows, omitted=omitted)


@dataclass(frozen=True)
class AptHealth:
    name: str
    summary: str | None
    installed: str | None
    candidate: str | None
    source_package: str
    section: str | None
    homepage: str | None
    installed_size: int | None
    download_size: int | None
    origin: AptOrigin
    support: str
    upstream: AptUpstream | None
    upstream_choice: RepoChoice
    ubuntu: CrossRelease
    debian: CrossRelease
    floors: list[Floor]


def apt_floors(stanza: dict[str, str], origin: AptOrigin, machine: Machine | None) -> list[Floor]:
    """The suite, and every versioned `Depends`; `libc6` is compared with this machine's glibc."""
    floors = [
        Floor(
            "suite",
            origin.release or "?",
            f"apt source of the candidate ({', '.join(origin.pockets) or '?'})",
            note="packaged for this machine's own sources",
        )
    ]
    here = machine.glibc if machine else None
    for clause in (stanza.get("Depends") or "").split(","):
        match = DEPENDS_RE.match(clause.split("|")[0])
        if not match:
            continue
        package, op, version = match.groups()
        if package == "libc6":
            want, have = version_tuple(version), version_tuple(here)
            met = _compare(op.replace(">>", ">").replace("<<", "<"), have, want) if want and have else None
            floors.append(Floor("glibc", f"{op}{version}", "Depends: libc6", f"glibc {here}" if here else None, met))
        else:
            floors.append(Floor(package, f"{op}{version}", "Depends", note="apt resolves it from the same sources"))
    return floors


def gather_apt(
    transport: Transport,
    name: str,
    *,
    upstream_repo: str | None = None,
    machine: Machine | None = None,
) -> AptHealth:
    """This machine's apt answer, the lag behind upstream, and which releases carry which version."""
    policy = parse_apt_policy(transport.apt_cache("policy", name))
    if policy is None:
        raise HealthError(f"apt knows no package {name!r} in this machine's sources")
    try:
        stanza = parse_apt_show(transport.apt_cache("show", name), policy.candidate)
    except NotFound:
        stanza = {}
    origin = apt_origin(policy)
    source_package = (stanza.get("Source") or name).split()[0]
    homepage = stanza.get("Homepage")
    choice = (
        RepoChoice(upstream_repo, "--upstream")
        if upstream_repo
        else RepoChoice(repo_from_url(homepage), "apt Homepage")
        if repo_from_url(homepage)
        else RepoChoice(None, "apt Homepage names no GitHub repo")
    )
    packaged = debian_upstream_version(policy.candidate) if policy.candidate else None
    size = stanza.get("Installed-Size")
    download = stanza.get("Size")
    return AptHealth(
        name=name,
        summary=(stanza.get("Description") or stanza.get("Description-en") or "").split("\n")[0] or None,
        installed=policy.installed,
        candidate=policy.candidate,
        source_package=source_package,
        section=stanza.get("Section"),
        homepage=homepage,
        # Installed-Size is KiB; Size is bytes.
        installed_size=int(size) * 1024 if size and size.isdigit() else None,
        download_size=int(download) if download and download.isdigit() else None,
        origin=origin,
        support=support_line(origin),
        upstream=apt_upstream(transport, choice.repo, choice.origin, packaged) if choice.repo and packaged else None,
        upstream_choice=choice,
        ubuntu=_cross_release(
            lambda: ubuntu_cross_release(
                transport.launchpad(
                    "ubuntu/+archive/primary?ws.op=getPublishedSources"
                    f"&source_name={urllib.parse.quote(source_package)}&exact_match=true&status=Published"
                    f"&ws.size={LAUNCHPAD_PAGE}"
                ),
                transport.launchpad("ubuntu/series"),
                origin.release if origin.distro == "ubuntu" else None,
            )
        ),
        debian=_cross_release(lambda: debian_cross_release(transport.madison(name))),
        floors=apt_floors(stanza, origin, machine),
    )


def _cross_release(read: Callable[[], CrossRelease]) -> CrossRelease:
    """A distro API that fails costs its own rows, never the rest of the report."""
    try:
        return read()
    except HealthError as error:
        return CrossRelease([], error=str(error))


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


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
    repo_choice: RepoChoice | None = None
    floors: list[Floor] = field(default_factory=list)


def gather(
    transport: Transport,
    name: str,
    repo: str | None,
    *,
    clone: Path | None = None,
    generated: list[str] | None = None,
    upstream_repo: str | None = None,
    now: datetime | None = None,
    machine: Machine | None = None,
) -> Health:
    """PyPI's answer. `repo` is `--repo`; when it is `None` the repo is read from `project_urls`."""
    now = now or datetime.now(UTC)
    payload = transport.pypi(name)
    info = payload.get("info", {})
    choice = choose_repo(repo, pypi_repo(info))
    repo_facts, people, issues = maintenance(transport, choice.repo, now=now)
    ships = release_files(payload)
    return Health(
        name=info.get("name", name),
        version=info.get("version"),
        summary=info.get("summary"),
        requires_python=info.get("requires_python"),
        cadence=cadence(release_dates(payload), yanked_versions(payload), now=now),
        runtime_requirements=runtime_requirements(payload),
        release_files=ships,
        repository=repo_facts,
        contributors=people,
        issues=issues,
        clone=clone_facts(clone, generated or []) if clone else None,
        upstream=upstream(transport, upstream_repo, release_dates(payload), now=now) if upstream_repo else None,
        repo_choice=choice,
        floors=pypi_floors(info.get("requires_python"), ships, machine),
    )


@dataclass(frozen=True)
class GithubHealth:
    """A repo judged on its own, for tools with no registry: Go and Rust binaries shipped as assets."""

    repo: str
    repository: Repository | None
    contributors: Contributors | None
    issues: IssueSample | None
    releases: ReleaseList
    latest: LatestRelease
    floors: list[Floor] = field(default_factory=list)


def gather_github(
    transport: Transport, repo: str, *, now: datetime | None = None, machine: Machine | None = None
) -> GithubHealth:
    """The maintenance axis, the stable-release cadence, and the latest release's Linux assets."""
    now = now or datetime.now(UTC)
    repo_facts, people, issues = maintenance(transport, repo, now=now)
    latest = latest_release(transport, repo, now=now)
    return GithubHealth(
        repo=repo,
        repository=repo_facts,
        contributors=people,
        issues=issues,
        releases=release_list(transport, repo, now=now),
        latest=latest,
        floors=asset_floors(latest, machine),
    )


def maintenance(
    transport: Transport, repo: str | None, *, now: datetime
) -> tuple[Repository | None, Contributors | None, IssueSample | None]:
    """The GitHub half of the maintenance axis, shared by every source that names a repo."""
    if not repo:
        return None, None, None
    repo_facts = repository(transport.github(f"repos/{repo}"), now=now)
    people = _contributor_window(transport, repo, now=now)
    issues = None
    if repo_facts.has_issues:
        issues = issue_sample(transport.github(f"repos/{repo}/issues?state=closed&per_page={ISSUE_SAMPLE}"))
    return repo_facts, people, issues


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

    lines.append("")
    lines.append("maintenance")
    lines.extend(_cadence_lines(health.cadence))
    lines.extend(_github_lines(health.repo_choice, health.repository, health.contributors, health.issues))

    names = ", ".join(requirement_names(health.runtime_requirements)) or "none"
    lines.append("")
    lines.append("fit")
    lines.append(f"  runtime deps     {len(health.runtime_requirements)}: {names}")

    lines.append("")
    lines.extend(_release_file_lines(health.release_files))
    lines.extend(_floor_lines(health.floors))

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

    lines.extend(CLOSING)
    return "\n".join(lines)


CLOSING = (
    "",
    "Judge this against the bar before comparing it to anything. See the skill for the",
    "traps these numbers hide: a version cap is not a cost until its historical lag says so.",
)


def render_github(health: GithubHealth) -> str:
    repo = health.repository
    lines = [f"{health.repo}  —  {(repo.description if repo else None) or 'no description'}"]
    lines.append("")
    lines.append("maintenance")
    lines.extend(_cadence_lines(health.releases.cadence, noun="GitHub releases"))
    listing = health.releases
    if listing.truncated:
        lines.append(f"  releases read    the newest {listing.read} only; older history is not counted")
    if listing.read == 0:
        lines.append("  releases read    none — a repo that publishes tags only has no release list")
    lines.extend(_github_lines(None, health.repository, health.contributors, health.issues))
    lines.append("")
    lines.extend(_latest_release_lines(health.latest, f"ships ({health.latest.repo}, latest stable release)"))
    lines.extend(_floor_lines(health.floors))
    lines.extend(CLOSING)
    return "\n".join(lines)


def render_npm(health: NpmHealth) -> str:
    lines = [f"{health.name} {health.version or '?'}  —  {health.description or 'no description'}"]
    others = ", ".join(f"{tag} {version}" for tag, version in health.dist_tags.items() if tag != "latest")
    if others:
        lines.append(f"dist-tags: latest {health.version}; also {others} — judged on latest only")
    if health.latest_deprecated:
        lines.append(f"LATEST IS DEPRECATED: {health.latest_deprecated}")
    lines.append("")
    lines.append("maintenance")
    lines.extend(_cadence_lines(health.cadence))
    if health.deprecated:
        shown = ", ".join(health.deprecated[:6]) + (" …" if len(health.deprecated) > 6 else "")
        lines.append(f"  deprecated       {len(health.deprecated)} version(s): {shown}")
    lines.extend(_github_lines(health.repo_choice, health.repository, health.contributors, health.issues))

    deps = health.runtime_dependencies
    lines.append("")
    lines.append("fit")
    lines.append(f"  runtime deps     {len(deps)}: {', '.join(deps[:12]) or 'none'}{' …' if len(deps) > 12 else ''}")
    lines.append(f"  licence          {health.license or 'none stated'}")
    lines.append(f"  typing           {health.typing.detail}")

    lines.append("")
    lines.extend(_npm_ship_lines(health.ships))
    lines.extend(_floor_lines(health.floors))
    if health.upstream:
        lines.append("")
        lines.extend(_upstream_lines(health.upstream, health.version))
    lines.extend(CLOSING)
    return "\n".join(lines)


def render_crates(health: CratesHealth) -> str:
    lines = [f"{health.name} {health.version or '?'}  —  {' '.join((health.description or 'no description').split())}"]
    lines.append("")
    lines.append("maintenance")
    lines.extend(_cadence_lines(health.cadence))
    lines.extend(_github_lines(health.repo_choice, health.repository, health.contributors, health.issues))
    if health.downloads is not None:
        recent = health.recent_downloads or 0
        lines.append(f"  not scored       {health.downloads} downloads, {recent} in the last 90 days")

    lines.append("")
    lines.append("fit")
    lines.append(f"  licence          {health.license or 'none stated'}")

    ships = health.ships
    lines.append("")
    lines.append(f"ships ({ships.version or '?'})")
    lines.append(f"  crate            {_size(ships.crate_size)} of source — cargo install compiles it here")
    kinds = ", ".join(kind for kind, present in (("library", ships.has_lib), ("binary", ships.bin_names)) if present)
    lines.append(f"  kind             {kinds or 'unknown'}; edition {ships.edition or '?'}")
    if ships.bin_names:
        lines.append(f"  commands         {', '.join(ships.bin_names)}")
    if health.release is not None:
        lines.append("")
        heading = f"prebuilt binary ({health.release.repo}, latest stable release)"
        lines.extend(_latest_release_lines(health.release, heading))
        if health.release.version and health.release.version != ships.version:
            lines.append(f"  version skew     GitHub release {health.release.version} against crate {ships.version}")
    elif ships.bin_names:
        lines.append("  prebuilt         not looked for — no GitHub repo; pass --repo owner/repo")
    lines.extend(_floor_lines(health.floors))
    lines.extend(CLOSING)
    return "\n".join(lines)


def render_apt(health: AptHealth) -> str:
    lines = [f"{health.name} {health.candidate or '(no candidate)'}  —  {health.summary or 'no summary'}"]
    lines.append("An apt package is maintained by the distro, not by upstream: judge the packaging and its lag.")
    origin = health.origin
    lines.append("")
    lines.append("this machine's apt")
    lines.append(f"  candidate        {health.candidate or 'NONE — known to apt, nothing installable'}")
    lines.append(f"  installed        {health.installed or 'no'}")
    lines.append(f"  from             {origin.host or '?'} {origin.suite or '?'}/{origin.component or '?'}")
    if len(origin.pockets) > 1:
        lines.append(f"  published in     {', '.join(origin.pockets)}")
    lines.append(f"  support          {health.support}")
    lines.append(f"  source package   {health.source_package}   section {health.section or '?'}")
    lines.append(f"  size             {_size(health.download_size)} download, {_size(health.installed_size)} installed")
    lines.append(f"  homepage         {health.homepage or 'none stated'}")

    lines.append("")
    choice = health.upstream_choice
    up = health.upstream
    if up is None:
        lines.append(f"upstream          not compared — {choice.origin}; pass --upstream owner/repo")
    else:
        override = "" if choice.origin == "--upstream" else "; --upstream overrides"
        lines.append(f"upstream ({up.repo}, from {up.origin}{override})")
        if up.error:
            lines.append(f"  releases         none readable — {up.error}")
        else:
            released = f", released {up.packaged_released}" if up.packaged_released else ", no matching GitHub release"
            lines.append(f"  packaged         {up.packaged}{released}")
            lines.append(f"  upstream latest  {up.latest}, released {up.latest_released}")
            behind = "UP TO DATE" if up.newer_releases == 0 else f"{up.newer_releases} stable release(s) BEHIND"
            lag = f", {up.lag_days}d older than upstream's latest" if up.lag_days else ""
            lines.append(f"  lag              {behind}{lag}")

    lines.append("")
    lines.append("cross-release (Ubuntu from Launchpad, Debian from madison)")
    for view in (health.ubuntu, health.debian):
        if view.error:
            lines.append(f"  {'?':<8} {view.error}")
        for row in view.rows:
            mark = "  <- this machine" if row.this_machine else ""
            where = f" ({row.pocket})" if row.pocket and row.pocket != "Release" else ""
            version = ", ".join(row.versions) or "not packaged"
            label = f"{row.release} {row.label}".strip()
            lines.append(f"  {row.distro:<7} {label:<36} {version}{where}{mark}")
        if view.omitted:
            lines.append(f"  {'':<7} ({view.omitted} obsolete series with this package not shown)")
    lines.extend(_floor_lines(health.floors))
    lines.extend(CLOSING)
    return "\n".join(lines)


def _npm_ship_lines(ships: NpmShips) -> list[str]:
    lines = [f"ships ({ships.version or '?'})"]
    count = f", {ships.file_count} files" if ships.file_count is not None else ""
    if ships.unpacked_size is None:
        lines.append("  tarball          size not recorded — npm stored no unpackedSize for this version")
    else:
        lines.append(f"  tarball          {_size(ships.unpacked_size)} unpacked{count}")
    commands = ", ".join(f"{name} → {path}" for name, path in ships.bin.items())
    lines.append(f"  bin              {commands or 'none — a library, no commands'}")
    if ships.install_scripts:
        hooks = "; ".join(f"{hook}: {command}" for hook, command in ships.install_scripts.items())
        lines.append(f"  install scripts  RUNS AT INSTALL — {hooks}")
    else:
        lines.append("  install scripts  none — nothing runs or fetches at install")
    lines.append(f"  provenance       {ships.provenance or 'none — no registry attestation for this version'}")
    if ships.optional_dependencies and not ships.platform_packages:
        lines.append(f"  platform pkgs    {ships.optional_dependencies} optionalDependencies, none named for Linux x64")
    elif ships.platform_packages:
        found = len(ships.platform_packages)
        lines.append(f"  platform pkgs    {found} of {ships.optional_dependencies} are Linux x64:")
        for pkg in ships.platform_packages:
            mark = "  <- this machine" if pkg.name == ships.chosen else ""
            if pkg.error:
                lines.append(f"    {'?':>9}  {pkg.name}  UNRESOLVED — {pkg.error}")
                continue
            libc = ",".join(pkg.libc) or "libc unstated"
            lines.append(f"    {_size(pkg.unpacked_size):>9}  {libc:<13} {pkg.name}@{pkg.version}{mark}")
        if ships.chosen:
            lines.append(f"  install size     {_size(ships.install_size)} here — the wrapper plus {ships.chosen}")
    return lines


def _floor_lines(floors: list[Floor]) -> list[str]:
    """Every floor, and whether this machine meets it; `NOT MET HERE` is the finding."""
    if not floors:
        return []
    lines = ["", "floors (stated by the metadata, compared with this machine where cheap to read)"]
    for floor in floors:
        if floor.met is True:
            verdict = f"met here ({floor.machine})"
        elif floor.met is False:
            verdict = f"NOT MET HERE ({floor.machine})"
        elif floor.machine is None:
            # A floor with a note says itself why it is not compared; one without is missing a value.
            verdict = "not compared" if floor.note else "not compared — this machine's value is not readable here"
        else:
            verdict = f"not compared (this machine: {floor.machine})"
        lines.append(f"  {floor.what:<8} {floor.required:<18} {verdict}")
        lines.append(f"  {'':<8} from {floor.source}{f' — {floor.note}' if floor.note else ''}")
    return lines


def _cadence_lines(pace: Cadence, noun: str = "releases") -> list[str]:
    kind = "stable" if pace.stable_only else "PRE-RELEASE ONLY — this project has shipped no stable"
    lines = [
        f"  releases         {pace.releases} {kind} {noun}, {pace.in_last_year} in the last year",
        f"  first / last     {pace.first_release or '?'} … {pace.last_release or '?'}",
        f"  median gap       {_or_unknown(pace.median_gap_days, 'd (last 10 releases)')}",
        f"  since last       {_or_unknown(pace.days_since_last, 'd')}",
    ]
    if pace.prereleases and pace.stable_only:
        lines.append(
            f"  pre-releases     {pace.prereleases}, latest {pace.last_prerelease}"
            "   — not counted above; a dev line moving is not the stable line moving"
        )
    if pace.yanked:
        lines.append(f"  yanked           {len(pace.yanked)}: {', '.join(pace.yanked[:6])}")
    return lines


def _github_lines(
    choice: RepoChoice | None,
    repo: Repository | None,
    people: Contributors | None,
    issues: IssueSample | None,
) -> list[str]:
    """The repo half of the maintenance section, whichever source named the repo."""
    lines: list[str] = []
    if choice is not None:
        if choice.repo:
            override = "" if choice.origin == "--repo" else "; --repo overrides"
            lines.append(f"  repo from        {choice.origin}{override}")
        else:
            lines.append(f"  repo             none read — {choice.origin}; pass --repo owner/repo")
    if repo:
        lines.append(f"  repo             {repo.full_name}{'  ARCHIVED' if repo.archived else ''}")
        lines.append(f"  last push        {repo.pushed or '?'} ({_or_unknown(repo.days_since_push, 'd ago')})")
        lines.append(f"  open issues+PRs  {repo.open_issues}   (GitHub counts both in this field)")
        lines.append(f"  issue tracker    {_issue_line(repo, issues)}")
        lines.append(f"  licence (field)  {repo.license_field or 'none reported'}   — verify against the files")
        lines.append(f"  not scored       {repo.stars} stars, {repo.forks} forks")
    if people:
        top = ", ".join(f"{login} {count}" for login, count in people.humans[:5]) or "none"
        lines.append(
            f"  humans/{people.window_days}d      {people.human_count} over {people.commits_read} commits"
            f"{' (truncated)' if people.truncated else ''}"
        )
        lines.append(f"  bus factor       {people.bus_factor}   top: {top}")
        if people.bots:
            lines.append(f"  bots excluded    {', '.join(f'{login} {count}' for login, count in people.bots[:5])}")
    return lines


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
    lines = _latest_release_lines(up, f"upstream ({up.repo})")
    if up.error:
        return lines
    if up.wrapper_match:
        tracks = (
            f"  wrapper tracks   {up.wrapper_match} on {up.wrapper_match_date or '?'}, "
            f"{_or_unknown(up.lag_days, 'd')} after upstream"
        )
    else:
        tracks = (
            f"  wrapper tracks   NO MATCHING WRAPPER RELEASE for {up.version}; wrapper's latest stable is"
            f" {wrapper_version or '?'} — compare the two by hand"
        )
    lines.insert(2, tracks)
    return lines


def _latest_release_lines(release: LatestRelease, heading: str) -> list[str]:
    lines = [heading]
    if release.error:
        lines.append(f"  latest release   none readable — {release.error}")
        lines.append("                   (a repo that publishes tags only has no releases/latest)")
        return lines
    lines.append(
        f"  latest release   {release.tag} ({release.version}), {release.published or '?'}"
        f" — {_or_unknown(release.days_since_release, 'd ago')}"
    )
    lines.append(f"  linux x86_64     {len(release.linux_x86_64)} of {release.assets_total} assets")
    for asset in release.linux_x86_64:
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


def payload_of(health: Any) -> dict[str, Any]:
    """Any source's answer as a dict, with the numbers `render` derives carried alongside the fields."""
    data = asdict(health)
    people = getattr(health, "contributors", None)
    if people:
        data["contributors"]["human_count"] = people.human_count
        data["contributors"]["bus_factor"] = people.bus_factor
    ships = getattr(health, "ships", None)
    if isinstance(ships, NpmShips):
        data["ships"]["install_size"] = ships.install_size
    clone = getattr(health, "clone", None)
    if clone:
        data["clone"]["sources"]["raw_ratio"] = clone.sources.raw_ratio
        data["clone"]["sources"]["handwritten_ratio"] = clone.sources.handwritten_ratio
    return data


SOURCES = ("pypi", "npm", "crates", "apt", "github")


def retired_form(argv: list[str]) -> str | None:
    """The one-line correction for `package_health.py <name> [<owner/repo>] …`, or `None`.

    [DECISION] The old form fails loudly rather than quietly still meaning PyPI: a silent fallback
    would be a default by another name, which is exactly what the subcommand exists to remove.
    """
    if not argv or argv[0].startswith("-") or argv[0] in SOURCES:
        return None
    # The retired form's second positional, when present, came straight after the name.
    if len(argv) > 1 and not argv[1].startswith("-"):
        spelled = ["pypi", argv[0], "--repo", argv[1], *argv[2:]]
    else:
        spelled = ["pypi", *argv]
    return (
        f"the source is a required subcommand now ({', '.join(SOURCES)}); "
        f"for PyPI: package_health.py {' '.join(spelled)}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sources = parser.add_subparsers(dest="source", required=True, metavar="{" + ",".join(SOURCES) + "}")

    pypi = sources.add_parser("pypi", help="a distribution on PyPI", description="Judge a PyPI distribution.")
    pypi.add_argument("name", help="the distribution name on PyPI")
    _add_repo_flag(pypi, "PyPI's project_urls")
    pypi.add_argument("--clone", type=Path, help="a local clone, for what the APIs cannot answer")
    pypi.add_argument(
        "--generated",
        action="append",
        default=[],
        metavar="GLOB",
        help="source that is mechanical rather than hand-written, relative to the clone; repeatable",
    )
    _add_upstream_flag(pypi)
    _add_json_flag(pypi)

    npm = sources.add_parser("npm", help="a package on npm", description="Judge an npm package.")
    npm.add_argument("name", help="the package name on npm, scoped or not (@biomejs/biome)")
    _add_repo_flag(npm, 'npm\'s "repository" field')
    _add_upstream_flag(npm)
    _add_json_flag(npm)

    crates = sources.add_parser("crates", help="a crate on crates.io", description="Judge a crate on crates.io.")
    crates.add_argument("name", help="the crate name on crates.io")
    _add_repo_flag(crates, 'crates.io\'s "repository" field')
    _add_json_flag(crates)

    apt = sources.add_parser(
        "apt",
        help="a package in this machine's apt sources",
        description="Judge an apt package: this machine's candidate, its lag behind upstream, and other releases.",
    )
    apt.add_argument("name", help="the binary package name, as apt-cache knows it")
    apt.add_argument(
        "--upstream",
        metavar="OWNER/REPO",
        help="the packaged project's GitHub repo, for the lag; default: read from the package's Homepage",
    )
    _add_json_flag(apt)

    github = sources.add_parser(
        "github",
        help="a GitHub repo on its own, for tools with no registry",
        description="Judge a GitHub repo: maintenance, stable-release cadence, the latest release's Linux assets.",
    )
    github.add_argument("repo", metavar="OWNER/REPO", help="the repository on GitHub")
    _add_json_flag(github)
    return parser


def _add_repo_flag(parser: argparse.ArgumentParser, where: str) -> None:
    parser.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help=f"the package's own GitHub repo, for the maintenance axis; default: read from {where}",
    )


def _add_upstream_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--upstream",
        metavar="OWNER/REPO",
        help="the project a wrapper repackages: its latest GitHub release, the wrapper's lag, its Linux assets",
    )


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="the whole answer as JSON")


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if correction := retired_form(argv):
        print(f"error: {correction}", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    transport = transport or LiveTransport()

    try:
        health, text = _run(args, transport, transport.machine())
    except HealthError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(payload_of(health), indent=2, default=str) if args.json else text)
    return 0


def _run(args: argparse.Namespace, transport: Transport, machine: Machine) -> tuple[Any, str]:
    """The source's answer and its rendering, one branch per subcommand."""
    if args.source == "github":
        if not GITHUB_SHORTHAND_RE.match(args.repo) or args.repo.startswith("github:"):
            raise HealthError(f"{args.repo!r} is not owner/repo")
        found = gather_github(transport, args.repo, machine=machine)
        return found, render_github(found)
    if args.source == "apt":
        packaged = gather_apt(transport, args.name, upstream_repo=args.upstream, machine=machine)
        return packaged, render_apt(packaged)
    if args.source == "crates":
        crate = gather_crates(transport, args.name, args.repo, machine=machine)
        return crate, render_crates(crate)
    if args.source == "npm":
        npm = gather_npm(transport, args.name, args.repo, upstream_repo=args.upstream, machine=machine)
        return npm, render_npm(npm)
    health = gather(
        transport,
        args.name,
        args.repo,
        clone=args.clone,
        generated=args.generated,
        upstream_repo=args.upstream,
        machine=machine,
    )
    return health, render(health)


if __name__ == "__main__":
    # A cut pipe is the reader's decision, not this script's error: die on SIGPIPE (exit 141)
    # rather than print a BrokenPipeError traceback that reads as a crash. Inside the guard because
    # the disposition is process-wide and the tests load this module by path.
    if hasattr(signal, "SIGPIPE"):  # absent on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
