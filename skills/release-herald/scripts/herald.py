#!/usr/bin/env python3
"""Everything deterministic about drafting a GitHub release, so the agent only writes prose.

    herald.py repo    [--repo HOST/OWNER/REPO]          # host, flow, config path — read-only
    herald.py setup   [--repo …]                         # first-time proposal: flow, surface, artifacts
    herald.py setup   --accept PROPOSAL.toml             # write the confirmed proposal as config
    herald.py collect --tag v1.2.0 [--previous v1.1.0]   # the change set, signals, quality, digest
    herald.py check   NOTES.md --tag v1.2.0              # lint a draft against what was collected
    herald.py publish --tag v1.2.0 --notes-file NOTES.md # a draft release; --live to publish
    herald.py explain                                    # how quality is graded (offline)

**Runs `gh` and nothing else — never `git`.** The repository is resolved once, from `--repo` or from
`gh repo view` in the current directory (where `gh` reads the remote itself), and every later call
names it explicitly: `-R HOST/OWNER/REPO` for repository commands and `--hostname HOST` for `gh api`,
which otherwise talks to `gh`'s default host whatever repository it is pointed at. No host is ever
written into this file, so a GitHub Enterprise Server repository works exactly like a github.com one.

**The gitflow change set is chosen by the smaller of two comparisons.** A release is the merged pull
request into the production branch (identified by its *base*, so a mis-named release branch is still
found). Its changes are the commits between a start and its branch tip, and there are two candidate
starts: the previous tag, and the previous release PR's branch tip. Each yields a superset of the
release — the first reaches back to the start of history when release PRs are squash-merged, the
second does the same for a hotfix cut from the production branch — so the one with the smaller
`ahead_by` is the closer fit. For merge-committed releases the two agree.

Config is keyed by the repository's URL on its host — never by a working-tree path — and lives at
`$XDG_CONFIG_HOME/release-herald/repos/<host>/<owner>/<repo>.toml`, `~/.config/…` on every OS.
Collected data is cache (`~/.cache/release-herald/…`); a draft goes to state
(`~/.local/state/release-herald/…`).

Stdlib only. Exit codes: 0 ok, 1 a blocking finding (`check`, a refused `publish`), 2 usage, a
failed `gh` call, or a refusal (a missing tag, an existing release).
"""

from __future__ import annotations

import sys

# A version guard before any 3.11-only import, so an older interpreter gets a sentence, not a
# ModuleNotFoundError naming a stdlib module.
if sys.version_info[:2] < (3, 11):  # noqa: UP036 — runs exactly where requires-python is not enforced
    sys.exit(f"herald.py needs Python 3.11 or newer; this is {sys.version.split()[0]} ({sys.executable})")

import argparse
import fnmatch
import hashlib
import itertools
import json
import os
import re
import subprocess
import tomllib
import urllib.parse
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL = "release-herald"

# --------------------------------------------------------------------------------------------
# Thresholds. Printed by `explain`; the standalone prompt states the same numbers, and a test keeps
# the two in step.
# --------------------------------------------------------------------------------------------

THIN_MIN_WORDS = 1
ADEQUATE_MIN_WORDS = 15
RICH_MIN_WORDS = 60
LOW_SIGNAL_SHARE = 0.5
"""Half or more of the kept items thin or empty: warn that there is little to go on."""
MIXED_SIGNAL_SHARE = 0.25
"""A quarter or more: say so in one line."""

GRADES = ("empty", "thin", "adequate", "rich")
COMPARE_PAGE = 100
GRAPHQL_COMMIT_BATCH = 40
GRAPHQL_PR_BATCH = 15
MAX_PATCH_LINES = 80
MAX_BODY_CHARS = 2500
MAX_SURFACE_ITEMS = 40
MAX_DIRECT_COMMIT_DETAILS = 300

# --------------------------------------------------------------------------------------------
# The two GraphQL selections. `references/prompt.md` quotes both verbatim, so a reader without the
# skill runs the same query; `tests/unit/test_herald.py` fails when they drift apart.
# --------------------------------------------------------------------------------------------

ASSOCIATED_PR_FIELDS = """
          nodes {
            number
            merged
            baseRefName
            headRefName
            headRefOid
            mergeCommit { oid }
          }
"""

PR_FIELDS = """
      number
      title
      body
      url
      merged
      mergedAt
      baseRefName
      headRefName
      headRefOid
      author { login }
      mergeCommit { oid }
      labels(first: 30) { nodes { name } }
      files(first: 100) { totalCount nodes { path additions deletions changeType } }
      closingIssuesReferences(first: 10) { nodes { number title url } }
      commits(first: 100) { totalCount nodes { commit { oid messageHeadline messageBody } } }
"""

# --------------------------------------------------------------------------------------------
# Defaults a repository's config can override. Each is a starting point the setup proposal shows,
# not a verdict: the agent and the user decide what is breaking or internal.
# --------------------------------------------------------------------------------------------

DEFAULT_SURFACE = (
    "*config*.toml",
    "*config*.yaml",
    "*config*.yml",
    "*config*.json",
    "*settings*.py",
    "*settings*.toml",
    "*schema*.json",
    "*openapi*.yaml",
    "*openapi*.yml",
    "*openapi*.json",
    "*.proto",
    "*.graphql",
    "*/cli.py",
    "*/cli/*",
    "*/__init__.py",
    "*/api/*",
    "*/migrations/*",
    "*values.yaml",
    "*.env.example",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "action.yml",
    "action.yaml",
)

DEFAULT_EXCLUDE: dict[str, tuple[str, ...]] = {
    "labels": ("internal", "skip-changelog", "no-changelog", "no-release-note", "ignore-for-release"),
    "title_prefixes": ("plans:", "Bump version", "chore(release)"),
    "head_patterns": ("sync/*",),
    "internal_paths": (
        ".github/*",
        "tests/*",
        "test/*",
        "plans/*",
        ".gitignore",
        ".editorconfig",
        ".pre-commit-config.yaml",
    ),
    "dependency_authors": ("dependabot[bot]", "renovate[bot]"),
}

DOC_PATTERNS = ("docs/*", "doc/*", "*.md", "*.rst")
DOC_IGNORE = ("CHANGELOG*", "*/CHANGELOG*", "HISTORY*", "NEWS*")
BREAKING_LABELS = frozenset({"breaking", "breaking-change", "breaking change", "semver-major", "major"})
BREAKING_TITLE_RE = re.compile(r"^\w+(\([^)]*\))?!:")
BREAKING_TEXT_RE = re.compile(r"BREAKING[ -]CHANGE|(?i:action required)")
DEPRECATION_RE = re.compile(r"\bdeprecat", re.IGNORECASE)
SECURITY_RE = re.compile(r"\bCVE-\d{4}-\d{4,}\b|\bGHSA(?:-[0-9a-z]{4}){3}\b", re.IGNORECASE)
BUMP_RE = re.compile(r"^(bump version|chore\(release\)|release v?\d|prepare (the )?release)", re.IGNORECASE)

VERSION_RE = re.compile(
    r"^(?P<prefix>.*?)(?P<nums>\d+(?:\.\d+){1,3})(?:[-.]?(?P<pre>dev|alpha|a|beta|b|pre|rc)\.?(?P<pren>\d+)?)?$",
    re.IGNORECASE,
)
PRE_RANK = {"dev": 0, "a": 1, "alpha": 1, "b": 2, "beta": 2, "pre": 3, "rc": 3}
FINAL_RANK = 9


class HeraldError(Exception):
    """A failure the user can act on; printed as one line, exit 2."""


# --------------------------------------------------------------------------------------------
# gh, behind one seam a test can replace.
# --------------------------------------------------------------------------------------------

Runner = Callable[[list[str]], tuple[int, str, str]]


def _subprocess_runner(argv: list[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    # A background harness exports FORCE_COLOR, and colour escapes break JSON parsing.
    env.pop("FORCE_COLOR", None)
    env.update({"NO_COLOR": "1", "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1", "CLICOLOR": "0"})
    try:
        ran = subprocess.run(argv, capture_output=True, text=True, env=env, check=False, timeout=300)
    except FileNotFoundError as exc:
        raise HeraldError("`gh` is not installed or not on PATH; this skill needs it") from exc
    return ran.returncode, ran.stdout, ran.stderr


@dataclass
class Gh:
    runner: Runner = _subprocess_runner
    calls: int = 0

    def run(self, args: Sequence[str]) -> tuple[int, str, str]:
        self.calls += 1
        return self.runner(["gh", *args])

    def api(self, host: str, path: str, *, raw: bool = False, missing_ok: bool = False) -> Any:
        args = ["api", "--hostname", host]
        if raw:
            args += ["-H", "Accept: application/vnd.github.raw"]
        args.append(path)
        code, out, err = self.run(args)
        if code != 0:
            if missing_ok and ("HTTP 404" in err or "Not Found" in err):
                return None
            raise HeraldError(f"gh api {path} failed on {host}: {err.strip() or out.strip()}")
        if raw:
            return out
        return json.loads(out) if out.strip() else None

    def graphql(self, host: str, query: str, variables: dict[str, str]) -> dict[str, Any]:
        args = ["api", "graphql", "--hostname", host, "-f", f"query={query}"]
        for key, value in variables.items():
            args += ["-f", f"{key}={value}"]
        code, out, err = self.run(args)
        if code != 0:
            raise HeraldError(f"GraphQL query failed on {host}: {err.strip() or out.strip()}")
        data = json.loads(out)
        if data.get("errors") and not data.get("data"):
            raise HeraldError(f"GraphQL errors on {host}: {data['errors']}")
        return data.get("data") or {}


# --------------------------------------------------------------------------------------------
# The repository, resolved once.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Repo:
    host: str
    owner: str
    name: str
    url: str
    default_branch: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def full(self) -> str:
        return f"{self.host}/{self.owner}/{self.name}"

    def link(self, path: str) -> str:
        return f"{self.url}/{path}"


SCP_RE = re.compile(r"^[\w.-]+@(?P<host>[^:/]+):(?P<path>.+)$")


def normalise_repo_spec(spec: str) -> str:
    """Any spelling of a repository → what `gh repo view` accepts: `HOST/OWNER/REPO` or `OWNER/REPO`."""
    spec = spec.strip()
    if m := SCP_RE.match(spec):
        host, path = m.group("host"), m.group("path")
    elif "://" in spec:
        parsed = urllib.parse.urlparse(spec)
        host, path = parsed.hostname or "", parsed.path
    else:
        return spec.removesuffix(".git").strip("/")
    parts = [p for p in path.removesuffix(".git").split("/") if p]
    if len(parts) < 2 or not host:
        raise HeraldError(f"cannot read a repository out of {spec!r}; pass HOST/OWNER/REPO")
    return f"{host}/{parts[0]}/{parts[1]}"


def resolve_repo(gh: Gh, spec: str | None) -> Repo:
    args = ["repo", "view"]
    if spec:
        args.append(normalise_repo_spec(spec))
    args += ["--json", "url,nameWithOwner,defaultBranchRef"]
    code, out, err = gh.run(args)
    if code != 0:
        where = spec or "the current directory"
        raise HeraldError(f"cannot resolve the repository for {where}: {err.strip()} — pass --repo HOST/OWNER/REPO")
    data = json.loads(out)
    url = str(data["url"]).rstrip("/")
    owner, name = str(data["nameWithOwner"]).split("/", 1)
    branch = (data.get("defaultBranchRef") or {}).get("name") or "main"
    return Repo(host=urllib.parse.urlparse(url).netloc, owner=owner, name=name, url=url, default_branch=branch)


# --------------------------------------------------------------------------------------------
# Locations: the Linux layout on every OS, so one backup covers every machine.
# --------------------------------------------------------------------------------------------


def _xdg(var: str, *default: str) -> Path:
    base = os.environ.get(var, "").strip()
    return (Path(base).expanduser() if base else Path.home().joinpath(*default)) / SKILL


def config_root() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def cache_root() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache")


def state_root() -> Path:
    return _xdg("XDG_STATE_HOME", ".local", "state")


def _safe(part: str) -> str:
    return re.sub(r"[^\w.@+-]", "_", part)


def _repo_parts(repo: Repo) -> tuple[str, str, str]:
    return _safe(repo.host), _safe(repo.owner), _safe(repo.name)


def config_path(repo: Repo) -> Path:
    host, owner, name = _repo_parts(repo)
    return config_root() / "repos" / host / owner / f"{name}.toml"


def repo_cache_dir(repo: Repo) -> Path:
    return cache_root().joinpath(*_repo_parts(repo))


def repo_state_dir(repo: Repo) -> Path:
    return state_root().joinpath(*_repo_parts(repo))


# --------------------------------------------------------------------------------------------
# Per-repository config.
# --------------------------------------------------------------------------------------------

CONFIG_KEYS = frozenset(
    {
        "url",
        "flow",
        "production_branch",
        "integration_branch",
        "source",
        "surface",
        "workflow_digest",
        "exclude",
        "artifacts",
    }
)
EXCLUDE_KEYS = frozenset(DEFAULT_EXCLUDE)
ARTIFACT_KEYS = frozenset({"kind", "name", "destination", "workflow", "job", "evidence", "confidence"})


@dataclass
class RepoConfig:
    path: Path
    exists: bool
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def flow(self) -> str | None:
        value = self.data.get("flow")
        return str(value) if value else None

    @property
    def source(self) -> str:
        return str(self.data.get("source") or "auto")

    @property
    def surface(self) -> tuple[str, ...]:
        value = self.data.get("surface")
        return tuple(str(v) for v in value) if isinstance(value, list) else DEFAULT_SURFACE

    def exclude(self, key: str) -> tuple[str, ...]:
        section = self.data.get("exclude") or {}
        value = section.get(key) if isinstance(section, dict) else None
        return tuple(str(v) for v in value) if isinstance(value, list) else DEFAULT_EXCLUDE[key]

    @property
    def artifacts(self) -> list[dict[str, Any]]:
        value = self.data.get("artifacts")
        return [a for a in value if isinstance(a, dict)] if isinstance(value, list) else []


def validate_config(data: dict[str, Any]) -> list[str]:
    problems = [f"unknown key {k!r}" for k in sorted(set(data) - CONFIG_KEYS)]
    if data.get("flow") not in (None, "gitflow", "trunk"):
        problems.append("flow must be 'gitflow' or 'trunk' (or absent, to detect)")
    if data.get("source") not in (None, "auto", "prs", "commits"):
        problems.append("source must be 'auto', 'prs' or 'commits'")
    exclude = data.get("exclude")
    if isinstance(exclude, dict):
        problems += [f"unknown exclude key {k!r}" for k in sorted(set(exclude) - EXCLUDE_KEYS)]
    for i, art in enumerate(data.get("artifacts") or []):
        if not isinstance(art, dict):
            problems.append(f"artifacts[{i}] is not a table")
            continue
        problems += [f"artifacts[{i}]: unknown key {k!r}" for k in sorted(set(art) - ARTIFACT_KEYS)]
        if not art.get("kind"):
            problems.append(f"artifacts[{i}] has no kind")
    return problems


def load_config(repo: Repo) -> RepoConfig:
    path = config_path(repo)
    if not path.is_file():
        return RepoConfig(path=path, exists=False)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise HeraldError(f"{path} is not valid TOML: {exc}") from exc
    problems = validate_config(data)
    if problems:
        raise HeraldError(f"{path}: " + "; ".join(problems))
    url = str(data.get("url") or "").rstrip("/")
    if url and url.lower() != repo.url.lower():
        raise HeraldError(f"{path} is for {url}, not {repo.url}; the file is keyed by URL, so it was copied by hand")
    return RepoConfig(path=path, exists=True, data=data)


def _toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_list(values: Iterable[str]) -> str:
    items = [_toml_str(v) for v in values]
    if sum(len(i) for i in items) < 70:
        return "[" + ", ".join(items) + "]"
    return "[\n" + "".join(f"  {i},\n" for i in items) + "]"


# --------------------------------------------------------------------------------------------
# Versions and the range.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Version:
    tag: str
    prefix: str
    nums: tuple[int, ...]
    pre_rank: int
    pre_num: int

    @property
    def is_pre(self) -> bool:
        return self.pre_rank != FINAL_RANK

    @property
    def padded(self) -> tuple[int, ...]:
        return self.nums + (0,) * (4 - len(self.nums))

    @property
    def key(self) -> tuple[tuple[int, ...], int, int]:
        return (self.padded, self.pre_rank, self.pre_num)

    @property
    def bare(self) -> str:
        return self.tag[len(self.prefix) :]


def parse_version(tag: str) -> Version | None:
    m = VERSION_RE.match(tag)
    if not m:
        return None
    pre = (m.group("pre") or "").lower()
    return Version(
        tag=tag,
        prefix=m.group("prefix"),
        nums=tuple(int(n) for n in m.group("nums").split(".")),
        pre_rank=PRE_RANK[pre] if pre else FINAL_RANK,
        pre_num=int(m.group("pren") or 0),
    )


def previous_version(current: Version, tags: Iterable[str]) -> Version | None:
    """Final → the previous final (rcs between are skipped); pre-release → the previous tag of any kind."""
    candidates = []
    for tag in tags:
        v = parse_version(tag)
        if v is None or v.prefix != current.prefix or v.key >= current.key:
            continue
        if not current.is_pre and v.is_pre:
            continue
        candidates.append(v)
    return max(candidates, key=lambda v: v.key) if candidates else None


def version_delta(current: Version, previous: Version | None) -> str:
    if previous is None:
        return "initial"
    for i, name in enumerate(("major", "minor", "patch", "patch")):
        if current.padded[i] != previous.padded[i]:
            return f"{name}-prerelease" if current.is_pre else name
    return "prerelease"


def list_tags(gh: Gh, repo: Repo, limit_pages: int = 20) -> list[str]:
    tags: list[str] = []
    for page in range(1, limit_pages + 1):
        batch = gh.api(repo.host, f"repos/{repo.slug}/tags?per_page=100&page={page}") or []
        tags += [str(t["name"]) for t in batch]
        if len(batch) < 100:
            break
    return tags


def commit_sha(gh: Gh, repo: Repo, ref: str) -> str:
    data = gh.api(repo.host, f"repos/{repo.slug}/commits/{urllib.parse.quote(ref, safe='')}", missing_ok=True)
    if not data:
        raise HeraldError(f"{ref!r} does not exist on {repo.url} — push the tag first; this skill never creates one")
    return str(data["sha"])


def branch_exists(gh: Gh, repo: Repo, branch: str) -> bool:
    path = f"repos/{repo.slug}/branches/{urllib.parse.quote(branch, safe='')}"
    return gh.api(repo.host, path, missing_ok=True) is not None


# --------------------------------------------------------------------------------------------
# Flow.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Flow:
    name: str
    production: str
    integration: str
    evidence: str


def detect_flow(gh: Gh, repo: Repo, config: RepoConfig) -> Flow:
    integration = str(config.data.get("integration_branch") or "develop")
    production = str(config.data.get("production_branch") or "")
    if not production:
        production = repo.default_branch
        if production == integration:
            production = next((b for b in ("main", "master") if branch_exists(gh, repo, b)), "main")
    if config.flow:
        return Flow(config.flow, production, integration, f"set in {config.path}")
    if branch_exists(gh, repo, integration):
        return Flow("gitflow", production, integration, f"branch {integration!r} exists")
    return Flow("trunk", production, integration, f"no {integration!r} branch")


# --------------------------------------------------------------------------------------------
# The change set.
# --------------------------------------------------------------------------------------------


def compare_page(gh: Gh, repo: Repo, base: str, head: str, page: int) -> dict[str, Any]:
    path = f"repos/{repo.slug}/compare/{base}...{head}?per_page={COMPARE_PAGE}&page={page}"
    return gh.api(repo.host, path) or {}


def compare_all(gh: Gh, repo: Repo, base: str, head: str, first: dict[str, Any]) -> list[dict[str, Any]]:
    total = int(first.get("total_commits") or 0)
    commits: list[dict[str, Any]] = list(first.get("commits") or [])
    page = 1
    while len(commits) < total:
        page += 1
        batch = list(compare_page(gh, repo, base, head, page).get("commits") or [])
        if not batch:
            break
        commits += batch
    return commits


def _repository_query(parts: Iterable[str]) -> str:
    head = "query($owner: String!, $name: String!) {\n  repository(owner: $owner, name: $name) {\n"
    return head + "\n".join(parts) + "\n  }\n}"


def associated_prs(gh: Gh, repo: Repo, oids: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
    """Each commit's merged pull requests into this repository."""
    found: dict[str, list[dict[str, Any]]] = {}
    for start in range(0, len(oids), GRAPHQL_COMMIT_BATCH):
        chunk = oids[start : start + GRAPHQL_COMMIT_BATCH]
        extra = "          nodes { baseRepository { nameWithOwner } }\n"
        parts = [
            f'    c{i}: object(oid: "{oid}") {{ ... on Commit {{ associatedPullRequests(first: 10) {{'
            f"{ASSOCIATED_PR_FIELDS}{extra}    }} }} }}"
            for i, oid in enumerate(chunk)
        ]
        data = gh.graphql(repo.host, _repository_query(parts), {"owner": repo.owner, "name": repo.name})
        repository = data.get("repository") or {}
        for i, oid in enumerate(chunk):
            nodes = ((repository.get(f"c{i}") or {}).get("associatedPullRequests") or {}).get("nodes") or []
            found[oid] = [n for n in nodes if n.get("merged") and _same_repo(n, repo)]
    return found


def _same_repo(node: dict[str, Any], repo: Repo) -> bool:
    name = (node.get("baseRepository") or {}).get("nameWithOwner") or repo.slug
    return str(name).lower() == repo.slug.lower()


def pr_details(gh: Gh, repo: Repo, numbers: Sequence[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for start in range(0, len(numbers), GRAPHQL_PR_BATCH):
        chunk = [int(n) for n in numbers[start : start + GRAPHQL_PR_BATCH]]
        parts = [f"    p{n}: pullRequest(number: {n}) {{{PR_FIELDS}    }}" for n in chunk]
        data = gh.graphql(repo.host, _repository_query(parts), {"owner": repo.owner, "name": repo.name})
        repository = data.get("repository") or {}
        out.update({n: pr for n in chunk if (pr := repository.get(f"p{n}"))})
    return out


def _merge_oid(node: dict[str, Any]) -> str | None:
    return (node.get("mergeCommit") or {}).get("oid")


def find_container(assoc: list[dict[str, Any]], sha: str, production: str) -> dict[str, Any] | None:
    """The release PR a tag commit came from: merged into the production branch, ideally as that commit."""
    into_production = [n for n in assoc if n.get("baseRefName") == production]
    exact = [n for n in into_production if _merge_oid(n) == sha]
    chosen = exact or into_production
    return min(chosen, key=lambda n: int(n["number"])) if chosen else None


def choose_pr(nodes: list[dict[str, Any]], oid: str, production: str, flow: str) -> dict[str, Any] | None:
    exact = [n for n in nodes if _merge_oid(n) == oid]
    if exact:
        return exact[0]
    if flow == "gitflow":
        not_release = [n for n in nodes if n.get("baseRefName") != production]
        if not_release:
            return min(not_release, key=lambda n: int(n["number"]))
    return min(nodes, key=lambda n: int(n["number"])) if nodes else None


@dataclass
class Range:
    tag: str
    previous: str
    tag_sha: str
    previous_sha: str
    base: str
    head: str
    base_reason: str
    delta: str
    prerelease: bool
    container: dict[str, Any] | None = None
    previous_container: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def container_numbers(self) -> set[int]:
        return {int(c["number"]) for c in (self.container, self.previous_container) if c}


def resolve_range(gh: Gh, repo: Repo, flow: Flow, tag: str, previous: str | None) -> tuple[Range, list[dict[str, Any]]]:
    current = parse_version(tag)
    tag_sha = commit_sha(gh, repo, tag)
    if previous is None and current is not None:
        found = previous_version(current, list_tags(gh, repo))
        previous = found.tag if found else None
    if previous is None:
        raise HeraldError(
            f"no previous release found before {tag}; pass --previous <tag> (a first release has no range)"
        )
    prev_v = parse_version(previous)
    delta = version_delta(current, prev_v) if current else "unknown"
    prerelease = bool(current and current.is_pre)
    prev_sha = commit_sha(gh, repo, previous)
    rng = Range(tag, previous, tag_sha, prev_sha, prev_sha, tag_sha, "trunk: previous tag", delta, prerelease)
    if flow.name != "gitflow":
        return rng, compare_all(gh, repo, prev_sha, tag_sha, compare_page(gh, repo, prev_sha, tag_sha, 1))
    return _gitflow_range(gh, repo, flow, rng)


def _gitflow_range(gh: Gh, repo: Repo, flow: Flow, rng: Range) -> tuple[Range, list[dict[str, Any]]]:
    assoc = associated_prs(gh, repo, [rng.tag_sha, rng.previous_sha])
    rng.container = find_container(assoc.get(rng.tag_sha, []), rng.tag_sha, flow.production)
    rng.previous_container = find_container(assoc.get(rng.previous_sha, []), rng.previous_sha, flow.production)
    if rng.container and rng.container.get("headRefOid"):
        rng.head = str(rng.container["headRefOid"])
    starts: list[tuple[str, str]] = [("previous tag", rng.previous_sha)]
    if rng.previous_container and rng.previous_container.get("headRefOid"):
        starts.append(("previous release PR's branch tip", str(rng.previous_container["headRefOid"])))
    tried = []
    for reason, start in starts:
        page = compare_page(gh, repo, start, rng.head, 1)
        tried.append((int(page.get("ahead_by") or 0), reason, start, page))
    ahead, reason, base, first = min(tried, key=lambda t: t[0])
    rng.base = base
    rng.base_reason = f"gitflow: {reason} (the smaller of {len(tried)} comparisons, {ahead} commits)"
    rng.candidates = [{"start": r, "sha": s, "ahead_by": a} for a, r, s, _ in tried]
    return rng, compare_all(gh, repo, base, rng.head, first)


# --------------------------------------------------------------------------------------------
# Items: exclusions, signals, quality.
# --------------------------------------------------------------------------------------------

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
LINK_ONLY_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:!?\[[^\]]*\]\([^)]*\)|<?https?://\S+>?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]")
WORD_RE = re.compile(r"[A-Za-z0-9][\w'`.-]*")


def informative_words(text: str | None) -> int:
    """Words left once a PR template's scaffolding is gone: comments, headings, checkboxes, bare links."""
    if not text:
        return 0
    kept = []
    for line in COMMENT_RE.sub("", text).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or set(stripped) <= set("-=*_|: "):
            continue
        if CHECKBOX_RE.match(line) or LINK_ONLY_RE.match(line):
            continue
        kept.append(stripped)
    return len(WORD_RE.findall(" ".join(kept)))


def grade(words: int) -> str:
    if words >= RICH_MIN_WORDS:
        return "rich"
    if words >= ADEQUATE_MIN_WORDS:
        return "adequate"
    if words >= THIN_MIN_WORDS:
        return "thin"
    return "empty"


def _match_any(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def signals_for(
    *, title: str, texts: Sequence[str], labels: Iterable[str], files: Sequence[str], surface: Sequence[str]
) -> dict[str, Any]:
    joined = "\n".join(t for t in texts if t)
    lower_labels = {lbl.lower() for lbl in labels}
    checks = (
        ("label", bool(lower_labels & BREAKING_LABELS)),
        ("title `!:`", bool(BREAKING_TITLE_RE.match(title))),
        ("text", bool(BREAKING_TEXT_RE.search(joined))),
    )
    security = sorted(set(SECURITY_RE.findall(title + "\n" + joined)))
    if not security and "security" in lower_labels:
        security = ["label"]
    return {
        "breaking": [reason for reason, hit in checks if hit],
        "surface": [f for f in files if _match_any(f, surface)],
        "deprecation": bool(DEPRECATION_RE.search(title + "\n" + joined)),
        "security": security,
        "docs": [f for f in files if _match_any(f, DOC_PATTERNS) and not _match_any(f, DOC_IGNORE)],
    }


def _split_message(message: str) -> tuple[str, str]:
    head, _, body = message.partition("\n")
    return head.strip(), body.strip()


def _trim(text: str | None, limit: int = MAX_BODY_CHARS) -> str:
    text = COMMENT_RE.sub("", text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …[truncated]"


def _trim_patch(patch: str | None) -> str:
    lines = (patch or "").splitlines()
    if len(lines) <= MAX_PATCH_LINES:
        return "\n".join(lines)
    return "\n".join(lines[:MAX_PATCH_LINES]) + f"\n… [{len(lines) - MAX_PATCH_LINES} more lines]"


@dataclass
class Rules:
    """The repository's exclusion and surface settings, read once."""

    surface: tuple[str, ...]
    labels: frozenset[str]
    title_prefixes: tuple[str, ...]
    head_patterns: tuple[str, ...]
    internal_paths: tuple[str, ...]
    dependency_authors: frozenset[str]

    @classmethod
    def from_config(cls, config: RepoConfig) -> Rules:
        return cls(
            surface=config.surface,
            labels=frozenset(lbl.lower() for lbl in config.exclude("labels")),
            title_prefixes=config.exclude("title_prefixes"),
            head_patterns=config.exclude("head_patterns"),
            internal_paths=config.exclude("internal_paths"),
            dependency_authors=frozenset(a.lower().removesuffix("[bot]") for a in config.exclude("dependency_authors")),
        )

    def internal_only(self, files: Sequence[str]) -> bool:
        return bool(files) and all(_match_any(f, self.internal_paths) for f in files)

    def pr_exclusion(self, title: str, head: str, labels: Sequence[str]) -> str | None:
        if _match_any(head, self.head_patterns):
            return f"back-merge branch {head!r}"
        hit = sorted({lbl for lbl in labels if lbl.lower() in self.labels})
        if hit:
            return f"label {', '.join(hit)}"
        return self._prefix(title)

    def commit_exclusion(self, headline: str, parents: int, has_pr: bool) -> str | None:
        if parents > 1 and not has_pr:
            return "merge commit"
        if BUMP_RE.match(headline):
            return "version bump"
        return self._prefix(headline)

    def _prefix(self, title: str) -> str | None:
        hit = next((p for p in self.title_prefixes if title.startswith(p)), None)
        return f"title prefix {hit!r}" if hit else None

    def is_dependency_bot(self, login: str) -> bool:
        return login.lower().removesuffix("[bot]") in self.dependency_authors


def _nodes(conn: dict[str, Any] | None) -> list[dict[str, Any]]:
    return list((conn or {}).get("nodes") or [])


def make_pr_item(pr: dict[str, Any], range_commits: list[dict[str, Any]], rules: Rules) -> dict[str, Any]:
    title = str(pr.get("title") or "")
    labels = [str(n["name"]) for n in _nodes(pr.get("labels"))]
    files = [str(n["path"]) for n in _nodes(pr.get("files"))]
    pr_commits = [
        {"oid": n["commit"]["oid"], "headline": n["commit"]["messageHeadline"], "body": n["commit"]["messageBody"]}
        for n in _nodes(pr.get("commits"))
    ]
    squashed = len(range_commits) == 1 and _merge_oid(pr) == str(range_commits[0]["sha"])
    squash_body = _split_message(str(range_commits[0]["commit"]["message"]))[1] if squashed else ""
    body = str(pr.get("body") or "")
    body_words = informative_words(body)
    commit_words = informative_words(squash_body) if squashed else sum(informative_words(c["body"]) for c in pr_commits)
    issues = [
        {"number": n["number"], "title": n["title"], "url": n["url"]} for n in _nodes(pr.get("closingIssuesReferences"))
    ]
    return {
        "kind": "pr",
        "number": int(pr["number"]),
        "url": pr.get("url"),
        "title": title,
        "author": str((pr.get("author") or {}).get("login") or "ghost"),
        "labels": labels,
        "base": pr.get("baseRefName"),
        "head": str(pr.get("headRefName") or ""),
        "merged_at": pr.get("mergedAt"),
        "merge": "squash" if squashed else "merge-or-rebase",
        "body": _trim(body),
        "squash_message_body": _trim(squash_body, 1200),
        "commits": [] if squashed else pr_commits,
        "commits_total": (pr.get("commits") or {}).get("totalCount", len(pr_commits)),
        "files": files,
        "files_total": (pr.get("files") or {}).get("totalCount", len(files)),
        "issues": issues,
        "signals": signals_for(
            title=title,
            texts=[body, squash_body, *(c["body"] for c in pr_commits)],
            labels=labels,
            files=files,
            surface=rules.surface,
        ),
        "quality": {
            "description_words": body_words,
            "description": grade(body_words),
            "commit_words": commit_words,
            "commits": grade(commit_words),
            "overall": grade(body_words + commit_words),
        },
    }


def make_commit_item(
    repo: Repo, c: dict[str, Any], pr_number: int | None, detail: dict[str, Any], rules: Rules
) -> dict[str, Any]:
    sha = str(c["sha"])
    headline, body = _split_message(str(c["commit"]["message"]))
    files_raw = list(detail.get("files") or [])
    files = [str(f["filename"]) for f in files_raw]
    words = informative_words(body)
    author = (c.get("author") or {}).get("login") or (c["commit"].get("author") or {}).get("name") or "unknown"
    return {
        "kind": "commit",
        "sha": sha,
        "url": repo.link(f"commit/{sha}"),
        "title": headline,
        "author": str(author),
        "pr": pr_number,
        "body": _trim(body),
        "files": files,
        "signals": signals_for(title=headline, texts=[body], labels=(), files=files, surface=rules.surface),
        "quality": {"commit_words": words, "commits": grade(words), "overall": grade(words)},
        "_files_raw": files_raw,
    }


def _item_ref(item: dict[str, Any]) -> str:
    return f"#{item['number']}" if item["kind"] == "pr" else str(item["sha"])[:7]


def _ref(item: dict[str, Any]) -> dict[str, Any]:
    return {"ref": _item_ref(item), "url": item["url"], "title": item["title"]}


@dataclass
class Collected:
    items: list[dict[str, Any]] = field(default_factory=list)
    excluded: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)


def map_commits(
    assoc: dict[str, list[dict[str, Any]]], commits: list[dict[str, Any]], rng: Range, flow: Flow
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    by_pr: dict[int, list[dict[str, Any]]] = {}
    unmapped: list[dict[str, Any]] = []
    for c in commits:
        nodes = [n for n in assoc.get(str(c["sha"]), []) if int(n["number"]) not in rng.container_numbers]
        chosen = choose_pr(nodes, str(c["sha"]), flow.production, flow.name)
        if chosen:
            by_pr.setdefault(int(chosen["number"]), []).append(c)
        else:
            unmapped.append(c)
    return by_pr, unmapped


def _add_pr_items(
    out: Collected, details: dict[int, dict[str, Any]], by_pr: dict[int, list[dict[str, Any]]], rules: Rules
) -> list[dict[str, Any]]:
    """PR items in merge order; returns commits whose PR could not be read, to be treated as direct."""
    orphans: list[dict[str, Any]] = []
    for number in sorted(by_pr, key=lambda n: str((details.get(n) or {}).get("mergedAt") or "")):
        pr = details.get(number)
        if pr is None:
            orphans += by_pr[number]
            continue
        item = make_pr_item(pr, by_pr[number], rules)
        reason = rules.pr_exclusion(item["title"], item["head"], item["labels"])
        if reason:
            out.excluded.append({**_ref(item), "reason": reason})
        elif rules.is_dependency_bot(item["author"]):
            out.dependencies.append({**_ref(item), "author": item["author"]})
        elif item["files_total"] == len(item["files"]) and rules.internal_only(item["files"]):
            out.excluded.append({**_ref(item), "reason": "touches only internal paths"})
        else:
            out.items.append(item)
    return orphans


def _add_commit_items(
    gh: Gh, repo: Repo, out: Collected, candidates: list[tuple[dict[str, Any], int | None]], rules: Rules
) -> None:
    detailed = 0
    for c, pr_number in candidates:
        headline = _split_message(str(c["commit"]["message"]))[0]
        reason = rules.commit_exclusion(headline, len(c.get("parents") or []), pr_number is not None)
        if reason:
            sha = str(c["sha"])
            out.excluded.append(
                {"ref": sha[:7], "url": repo.link(f"commit/{sha}"), "title": headline, "reason": reason}
            )
            continue
        detail: dict[str, Any] = {}
        if detailed < MAX_DIRECT_COMMIT_DETAILS:
            detail = gh.api(repo.host, f"repos/{repo.slug}/commits/{c['sha']}") or {}
            detailed += 1
        item = make_commit_item(repo, c, pr_number, detail, rules)
        if rules.internal_only(item["files"]):
            out.excluded.append({**_ref(item), "reason": "touches only internal paths"})
        else:
            out.items.append(item)


def surface_patches(gh: Gh, repo: Repo, item: dict[str, Any], surface: Sequence[str]) -> dict[str, str]:
    files: list[dict[str, Any]] = list(item.get("_files_raw") or [])
    if item["kind"] == "pr":
        for page in range(1, 4):
            batch = gh.api(repo.host, f"repos/{repo.slug}/pulls/{item['number']}/files?per_page=100&page={page}") or []
            files += batch
            if len(batch) < 100:
                break
    return {
        str(f["filename"]): _trim_patch(f.get("patch"))
        for f in files
        if f.get("patch") and _match_any(str(f.get("filename", "")), surface)
    }


def build_items(
    gh: Gh, repo: Repo, flow: Flow, config: RepoConfig, rng: Range, commits: list[dict[str, Any]], source: str
) -> dict[str, Any]:
    rules = Rules.from_config(config)
    assoc = associated_prs(gh, repo, [str(c["sha"]) for c in commits]) if commits else {}
    by_pr, unmapped = map_commits(assoc, commits, rng, flow)
    mapped_share = (len(commits) - len(unmapped)) / len(commits) if commits else 0.0
    effective = source if source != "auto" else ("prs" if mapped_share >= 0.5 else "commits")
    out = Collected()
    candidates: list[tuple[dict[str, Any], int | None]]
    if effective == "prs":
        details = pr_details(gh, repo, sorted(by_pr)) if by_pr else {}
        orphans = _add_pr_items(out, details, by_pr, rules)
        candidates = [(c, None) for c in unmapped + orphans]
    else:
        pr_of = {str(c["sha"]): n for n, cs in by_pr.items() for c in cs}
        candidates = [(c, pr_of.get(str(c["sha"]))) for c in commits]
    _add_commit_items(gh, repo, out, candidates, rules)
    for item in [i for i in out.items if i["signals"]["surface"]][:MAX_SURFACE_ITEMS]:
        item["surface_patches"] = surface_patches(gh, repo, item, rules.surface)
    for item in out.items:
        item.pop("_files_raw", None)
    return {
        "source": effective,
        "mapped_share": round(mapped_share, 2),
        "items": out.items,
        "excluded": out.excluded,
        "dependencies": out.dependencies,
    }


def quality_report(items: list[dict[str, Any]], commits: list[dict[str, Any]]) -> dict[str, Any]:
    overall = dict.fromkeys(GRADES, 0)
    descriptions = dict.fromkeys(GRADES, 0)
    messages = dict.fromkeys(GRADES, 0)
    for item in items:
        overall[item["quality"]["overall"]] += 1
        if item["kind"] == "pr":
            descriptions[item["quality"]["description"]] += 1
    for c in commits:
        messages[grade(informative_words(_split_message(str(c["commit"]["message"]))[1]))] += 1
    share = (overall["empty"] + overall["thin"]) / len(items) if items else 0.0
    level = "low" if share >= LOW_SIGNAL_SHARE else "mixed" if share >= MIXED_SIGNAL_SHARE else "ok"
    weakest = sorted(
        (i for i in items if i["quality"]["overall"] in ("empty", "thin")),
        key=lambda i: (i["quality"]["overall"] != "empty", _item_ref(i)),
    )
    return {
        "items": overall,
        "pr_descriptions": descriptions,
        "commit_messages": messages,
        "thin_share": round(share, 2),
        "level": level,
        "weakest": [_ref(i) for i in weakest],
    }


# --------------------------------------------------------------------------------------------
# Rendering: the digest the agent reads, and the summary the user sees.
# --------------------------------------------------------------------------------------------


def _quote(text: str, prefix: str = "> ") -> list[str]:
    return [f"{prefix}{line}" for line in text.splitlines()]


def _digest_flags(sig: dict[str, Any]) -> list[str]:
    pairs = (
        ("BREAKING?", sig["breaking"]),
        ("surface", sig["surface"]),
        ("deprecation", sig["deprecation"]),
        ("security", sig["security"]),
        ("docs", sig["docs"]),
    )
    return [name for name, on in pairs if on]


def _digest_item(item: dict[str, Any]) -> list[str]:
    sig = item["signals"]
    meta = f"{item['kind']}, @{item['author']}, quality {item['quality']['overall']}"
    if item["kind"] == "pr":
        meta += f", {item['merge']}" + (f", labels: {', '.join(item['labels'])}" if item["labels"] else "")
    out = [f"### {_item_ref(item)} {item['title']}", "", f"- {meta}", f"- url: {item['url']}"]
    if flags := _digest_flags(sig):
        out.append(f"- signals: {', '.join(flags)}")
    details = (("breaking evidence", sig["breaking"]), ("surface files", sig["surface"]), ("docs files", sig["docs"]))
    out += [f"- {label}: {', '.join(values)}" for label, values in details if values]
    out += [f"- closes #{i['number']}: {i['title']}" for i in item.get("issues") or []]
    if item.get("body"):
        out += ["", "Description:", "", *_quote(item["body"]), ""]
    if item.get("squash_message_body"):
        out += ["Squash commit message body:", "", *_quote(item["squash_message_body"]), ""]
    if item.get("commits"):
        out += [f"Commits ({item.get('commits_total', len(item['commits']))}):", ""]
        for c in item["commits"]:
            out += [f"- {c['headline']}", *_quote((c.get("body") or "").strip(), "  > ")[:12]]
        out.append("")
    for path, patch in (item.get("surface_patches") or {}).items():
        out += [f"Diff of {path}:", "", "```diff", patch, "```", ""]
    return [*out, ""]


def _digest_tail(collected: dict[str, Any]) -> list[str]:
    deps = [f"- {d['ref']} {d['title']} ({d['url']})" for d in collected["dependencies"]]
    excluded = [f"- {e['ref']} {e['title']} — {e['reason']}" for e in collected["excluded"]]
    artifacts = [
        f"- {a.get('kind')}: {a.get('name', '')} → {a.get('destination') or 'unknown'}" for a in collected["artifacts"]
    ]
    out: list[str] = []
    for title, lines in (
        ("Dependency PRs (collapse to one line)", deps),
        ("Excluded (tell the user)", excluded),
        ("Artifacts (from the confirmed setup)", artifacts),
    ):
        if lines:
            out += [f"## {title}", "", *lines, ""]
    return out


def render_digest(collected: dict[str, Any]) -> str:
    rng = collected["range"]
    pre = ", pre-release" if rng["prerelease"] else ""
    out = [
        f"# Release digest: {collected['repo']['url']} {rng['tag']}",
        "",
        f"- range: {rng['previous']} → {rng['tag']} ({rng['delta']}{pre})",
        f"- flow: {collected['flow']['name']} ({collected['flow']['evidence']}); {rng['base_reason']}",
        f"- source: {collected['source']} ({int(collected['mapped_share'] * 100)}% of commits map to a PR)",
        f"- compare: {collected['compare_url']}",
        f"- link base: {collected['repo']['url']}",
        *(
            f"- release PR: #{c['number']} {c.get('headRefName')} → {c.get('baseRefName')}"
            for c in rng.get("containers") or []
        ),
    ]
    if ctx := collected.get("release_context"):
        out += ["", "## Release PR description (release-level context)", "", ctx]
    out += ["", "## Items", ""]
    for item in collected["items"]:
        out += _digest_item(item)
    return "\n".join(out + _digest_tail(collected))


def _counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in counts.items())


def _quality_lines(q: dict[str, Any]) -> list[str]:
    thin = int(q["thin_share"] * 100)
    if q["level"] == "low":
        return [
            f"WARNING:   low signal — {thin}% of kept items have thin or empty descriptions.",
            "           Tell the user before drafting; these are the ones to enrich first:",
            *(f"           {w['ref']} {w['title']} {w['url']}" for w in q["weakest"][:15]),
        ]
    if q["level"] == "mixed":
        return [f"note:      {thin}% of kept items are thin or empty; those entries rest on title and diff"]
    return []


def render_summary(collected: dict[str, Any]) -> str:
    rng = collected["range"]
    q = collected["quality"]
    pre = ", pre-release" if rng["prerelease"] else ""
    share = int(collected["mapped_share"] * 100)
    lines = [
        f"repo:      {collected['repo']['url']}",
        f"range:     {rng['previous']} → {rng['tag']} ({rng['delta']}{pre})",
        f"flow:      {collected['flow']['name']} — {collected['flow']['evidence']}",
        f"base:      {rng['base_reason']}",
        f"commits:   {collected['commit_count']}, {share}% mapped to PRs; source {collected['source']}",
        f"items:     {len(collected['items'])} kept, {len(collected['excluded'])} excluded, "
        f"{len(collected['dependencies'])} dependency PRs",
        "quality:   items " + _counts(q["items"]),
        "           PR descriptions " + _counts(q["pr_descriptions"]),
        "           commit messages " + _counts(q["commit_messages"]),
    ]
    flagged = [_item_ref(i) for i in collected["items"] if i["signals"]["breaking"] or i["signals"]["surface"]]
    if flagged:
        lines.append(f"review:    breaking or surface signals on {', '.join(flagged)}")
    lines += _quality_lines(q)
    if not collected["artifacts"]:
        lines.append("artifacts: none confirmed — run `setup` to propose them")
    if collected["config"].get("stale"):
        lines.append("setup:     the workflows changed since setup was confirmed — re-run `setup` and compare")
    lines += [
        f"digest:    {collected['paths']['digest']}",
        f"draft to:  {collected['paths']['draft']}",
        f"gh calls:  {collected['gh_calls']}",
    ]
    return "\n".join(lines)


EXPLAIN = f"""How quality is graded.

Each kept item's text — the PR description, plus its squash commit message or its own commits'
messages; a direct commit's body — has HTML comments, headings, checkbox lines and link-only lines
removed, and the remaining words are counted:

  empty     0 words
  thin      {THIN_MIN_WORDS}-{ADEQUATE_MIN_WORDS - 1} words
  adequate  {ADEQUATE_MIN_WORDS}-{RICH_MIN_WORDS - 1} words
  rich      {RICH_MIN_WORDS} or more words

When {int(LOW_SIGNAL_SHARE * 100)}% or more of the kept items are thin or empty, `collect` warns that there
is little to go on; from {int(MIXED_SIGNAL_SHARE * 100)}% it notes it. PR descriptions and commit messages are
also counted separately, so the user sees which of the two the repository actually relies on.

Signals are evidence, never verdicts: `BREAKING?` means a label, a `!:` title, or "BREAKING CHANGE" /
"action required" text was found; `surface` means a changed file matches the repo's surface globs
(diffs of those files are in the digest). Whether a change needs user action is decided by reading.
"""


# --------------------------------------------------------------------------------------------
# collect
# --------------------------------------------------------------------------------------------


def substitute(template: str, version: Version | None, tag: str) -> str:
    return template.replace("{tag}", tag).replace("{version}", version.bare if version else tag)


def _release_context(gh: Gh, repo: Repo, rng: Range) -> str:
    if not rng.container or _merge_oid(rng.container) != rng.tag_sha:
        return ""
    number = int(rng.container["number"])
    return _trim(str((pr_details(gh, repo, [number]).get(number) or {}).get("body") or ""))


def _range_dict(rng: Range) -> dict[str, Any]:
    keys = ("number", "headRefName", "baseRefName", "headRefOid")
    return {
        "tag": rng.tag,
        "previous": rng.previous,
        "tag_sha": rng.tag_sha,
        "previous_sha": rng.previous_sha,
        "base": rng.base,
        "head": rng.head,
        "base_reason": rng.base_reason,
        "delta": rng.delta,
        "prerelease": rng.prerelease,
        "containers": [{k: c.get(k) for k in keys} for c in (rng.container, rng.previous_container) if c],
        "candidates": rng.candidates,
    }


def _setup_is_stale(gh: Gh, repo: Repo, config: RepoConfig) -> bool:
    """The workflows changed since the artifact answer was confirmed, so it may no longer be true."""
    recorded = config.data.get("workflow_digest")
    return bool(config.exists and recorded and recorded != _workflow_listing(gh, repo)[1])


def collect(gh: Gh, repo: Repo, tag: str, previous: str | None, source: str | None) -> dict[str, Any]:
    config = load_config(repo)
    flow = detect_flow(gh, repo, config)
    rng, commits = resolve_range(gh, repo, flow, tag, previous)
    built = build_items(gh, repo, flow, config, rng, commits, source or config.source)
    version = parse_version(tag)
    cache = repo_cache_dir(repo)
    paths = {
        "json": str(cache / f"{_safe(tag)}.json"),
        "digest": str(cache / f"{_safe(tag)}.digest.md"),
        "draft": str(repo_state_dir(repo) / f"{_safe(tag)}.md"),
    }
    collected: dict[str, Any] = {
        "schema": 1,
        "repo": {"host": repo.host, "owner": repo.owner, "name": repo.name, "url": repo.url},
        "flow": flow.__dict__,
        "range": _range_dict(rng),
        "compare_url": repo.link(f"compare/{rng.previous}...{rng.tag}"),
        "commit_count": len(commits),
        "release_context": _release_context(gh, repo, rng),
        **built,
        "quality": quality_report(built["items"], commits),
        "artifacts": [
            {**a, "destination": substitute(str(a.get("destination") or ""), version, tag) or None}
            for a in config.artifacts
        ],
        "config": {"path": str(config.path), "exists": config.exists, "stale": _setup_is_stale(gh, repo, config)},
        "paths": paths,
        "gh_calls": gh.calls,
    }
    cache.mkdir(parents=True, exist_ok=True)
    Path(paths["json"]).write_text(json.dumps(collected, indent=2), encoding="utf-8")
    Path(paths["digest"]).write_text(render_digest(collected), encoding="utf-8")
    Path(paths["draft"]).parent.mkdir(parents=True, exist_ok=True)
    return collected


# --------------------------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
BARE_REF_RE = re.compile(r"(?<![\w/\[#&])#(\d+)\b")
FENCE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
SECTION_ORDER = ("action required", "highlights", "all changes", "artifacts")
FORGE_PATH_RE = re.compile(
    r"^/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?P<kind>pull|issues|commit|compare|blob|tree)/(?P<rest>.+)$"
)


@dataclass
class Finding:
    level: str
    message: str


@dataclass
class Links:
    prs: set[int] = field(default_factory=set)
    shas: list[str] = field(default_factory=list)


def _check_links(prose: str, repo: dict[str, Any], findings: list[Finding]) -> Links:
    host = str(repo["host"]).lower()
    slug = f"{repo['owner']}/{repo['name']}".lower()
    links = Links()
    for label, url in MD_LINK_RE.findall(prose):
        parsed = urllib.parse.urlparse(url)
        m = FORGE_PATH_RE.match(parsed.path)
        if not parsed.netloc or not m:
            continue
        same_slug = f"{m['owner']}/{m['repo']}".lower() == slug
        if parsed.netloc.lower() != host:
            if same_slug:
                findings.append(
                    Finding("error", f"link to {parsed.netloc} where the repository lives on {host}: {url}")
                )
            continue
        if not same_slug:
            continue
        if m["kind"] == "pull":
            number = int(re.split(r"[/#?]", m["rest"])[0])
            links.prs.add(number)
            if label.strip() != f"#{number}":
                findings.append(Finding("warning", f"PR link text should be just `#{number}`, got `{label}`"))
        elif m["kind"] == "commit":
            links.shas.append(m["rest"].split("/")[0].lower())
    bare = sorted({int(n) for n in BARE_REF_RE.findall(MD_LINK_RE.sub("", prose))})
    findings.extend(Finding("warning", f"bare `#{n}` autolinks only in a release body; use [#{n}](url)") for n in bare)
    return links


def _is_covered(item: dict[str, Any], links: Links, dropped: set[str]) -> bool:
    if item["kind"] == "pr":
        return item["number"] in links.prs or str(item["number"]) in dropped
    if item.get("pr") and item["pr"] in links.prs:
        return True
    sha = str(item["sha"]).lower()
    return any(sha.startswith(s) for s in links.shas) or any(sha.startswith(d) for d in dropped if len(d) >= 7)


def _check_coverage(collected: dict[str, Any], links: Links, dropped: set[str], findings: list[Finding]) -> None:
    findings.extend(
        Finding("error", f"{_item_ref(i)} ({i['title']}) is neither in the notes nor in --dropped")
        for i in collected["items"]
        if not _is_covered(i, links, dropped)
    )
    known = {int(i["number"]) for i in collected["items"] if i["kind"] == "pr"}
    known |= {int(str(d["ref"]).lstrip("#")) for d in collected["dependencies"]}
    findings.extend(
        Finding("warning", f"#{n} is linked but is not one of this release's items") for n in sorted(links.prs - known)
    )


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    return [(i, len(m.group(1)), m.group(2)) for i, line in enumerate(lines) if (m := HEADING_RE.match(line))]


def _check_sections(text: str, delta: str, findings: list[Finding]) -> None:
    lines = text.splitlines()
    heads = _headings(lines)
    for pos, (idx, level, title) in enumerate(heads):
        nxt = heads[pos + 1] if pos + 1 < len(heads) else None
        body = "\n".join(lines[idx + 1 : nxt[0] if nxt else len(lines)]).strip()
        if not body and (nxt is None or nxt[1] <= level):
            findings.append(Finding("error", f"section `{title}` is empty; omit it"))
    seen = [(i, t) for _, _, t in heads for i, name in enumerate(SECTION_ORDER) if name in t.lower()]
    findings.extend(
        Finding("warning", f"section `{tb}` comes after `{ta}`; the order is {', '.join(SECTION_ORDER)}")
        for (a, ta), (b, tb) in itertools.pairwise(seen)
        if b < a
    )
    if delta.startswith("patch") and any("highlights" in t.lower() for _, _, t in heads):
        findings.append(Finding("warning", "a patch release has a Highlights section; patch notes skip it"))


def _section_text(text: str, name: str) -> str:
    out: list[str] = []
    level: int | None = None
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m and level is not None and len(m.group(1)) <= level:
            break
        if m and level is None and name in m.group(2).lower():
            level = len(m.group(1))
        elif level is not None:
            out.append(line)
    return "\n".join(out)


def check_notes(text: str, collected: dict[str, Any], dropped: Iterable[str] = ()) -> list[Finding]:
    findings: list[Finding] = []
    prose = CODE_SPAN_RE.sub("", FENCE_RE.sub("", text))
    links = _check_links(prose, collected["repo"], findings)
    dropped_set = {d.strip().lstrip("#").lower() for d in dropped if d.strip()}
    _check_coverage(collected, links, dropped_set, findings)
    _check_sections(text, str(collected["range"]["delta"]), findings)
    action = _section_text(text, "action required")
    findings.extend(
        Finding("warning", f"#{i['number']} carries a breaking signal but is not under Action required")
        for i in collected["items"]
        if i["kind"] == "pr" and i["signals"]["breaking"] and f"/pull/{i['number']})" not in action
    )
    if "/compare/" not in prose:
        findings.append(
            Finding("warning", "no compare link; end with **Full Changelog**: [PREV...TAG](…/compare/PREV...TAG)")
        )
    return findings


def load_collected(repo: Repo, tag: str, explicit: str | None) -> dict[str, Any]:
    path = Path(explicit) if explicit else repo_cache_dir(repo) / f"{_safe(tag)}.json"
    if not path.is_file():
        raise HeraldError(f"nothing collected for {tag} at {path}; run `collect --tag {tag}` first")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------
# publish
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PublishRequest:
    tag: str
    notes_file: Path
    title: str | None = None
    live: bool = False
    update: bool = False
    prerelease: bool | None = None


def publish(gh: Gh, repo: Repo, req: PublishRequest) -> str:
    if not req.notes_file.is_file():
        raise HeraldError(f"no notes file at {req.notes_file}")
    exists = gh.run(["release", "view", req.tag, "-R", repo.full, "--json", "tagName"])[0] == 0
    if exists and not req.update:
        raise HeraldError(f"a release for {req.tag} already exists on {repo.url}; pass --update to replace its notes")
    if req.update and not exists:
        raise HeraldError(f"no release for {req.tag} on {repo.url} to update")
    if req.update:
        args = ["release", "edit", req.tag, "-R", repo.full, "--notes-file", str(req.notes_file)]
        args += ["--title", req.title] if req.title else []
    else:
        commit_sha(gh, repo, req.tag)  # refuses with a sentence when the tag is not on the remote
        args = ["release", "create", req.tag, "-R", repo.full, "--verify-tag", "--notes-file", str(req.notes_file)]
        args += ["--title", req.title or req.tag]
        args += [] if req.live else ["--draft"]
        version = parse_version(req.tag)
        if req.prerelease if req.prerelease is not None else bool(version and version.is_pre):
            args.append("--prerelease")
    code, out, err = gh.run(args)
    if code != 0:
        raise HeraldError(f"gh {' '.join(args[:2])} failed: {err.strip() or out.strip()}")
    return out.strip()


# --------------------------------------------------------------------------------------------
# setup: flow, surface and artifacts, proposed once and confirmed by the user.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Clue:
    kind: str
    destination: str | None
    workflow: str
    job: str | None
    line: int
    evidence: str


DEST = r"((?:\$\{\{[^}]*\}\}|[^'\"\s])+)"
"""A destination token: no quotes or spaces, except inside a `${{ … }}` expression it may contain."""


def _q(body: str) -> re.Pattern[str]:
    return re.compile(body.replace(r"([^'\"\s]+)", DEST))


CLUE_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("npm", _q(r"\bregistry-url:\s*['\"]?([^'\"\s]+)"), "setup-node registry-url"),
    ("docker", _q(r"^\s*registry:\s*['\"]?([^'\"\s]+)"), "login registry"),
    ("docker", _q(r"^\s*images:\s*['\"]?([^'\"\s|>]+)"), "metadata images"),
    ("pypi", _q(r"\brepository-url:\s*['\"]?([^'\"\s]+)"), "pypi-publish repository-url"),
    ("pypi", _q(r"pypa/gh-action-pypi-publish()"), "pypi-publish action (default upload.pypi.org)"),
    ("pypi", _q(r"\buv publish\b.*?--publish-url[= ]['\"]?([^'\"\s]+)|\buv publish\b()"), "uv publish"),
    ("pypi", _q(r"\bUV_PUBLISH_URL:\s*['\"]?([^'\"\s]+)"), "UV_PUBLISH_URL"),
    ("pypi", _q(r"\btwine upload\b.*?--repository-url[= ]['\"]?([^'\"\s]+)|\btwine upload\b()"), "twine upload"),
    ("pypi", _q(r"\bTWINE_REPOSITORY_URL:\s*['\"]?([^'\"\s]+)"), "TWINE_REPOSITORY_URL"),
    ("npm", _q(r"\bnpm publish\b.*?--registry[= ]['\"]?([^'\"\s]+)|\bnpm publish\b()"), "npm publish"),
    ("artifactory", _q(r"\bJF_URL:\s*['\"]?([^'\"\s]+)"), "JF_URL"),
    ("artifactory", _q(r"\bjf rt (?:upload|u)\s+\S+\s+['\"]?([^'\"\s]+)"), "jf rt upload"),
    ("docker", _q(r"\bjf docker push\s+['\"]?([^'\"\s]+)"), "jf docker push"),
    ("docker", _q(r"\bdocker (?:image )?push\s+['\"]?([^'\"\s]+)"), "docker push"),
    ("helm", _q(r"\bhelm push\s+\S+\s+['\"]?(oci://[^'\"\s]+)"), "helm push"),
    ("helm", _q(r"helm/chart-releaser-action()"), "chart-releaser"),
    ("maven", _q(r"\bmvn\b.*\bdeploy\b()|\bgradlew?\b.*\bpublish\w*()"), "maven/gradle publish"),
    ("crates", _q(r"\bcargo publish\b()"), "cargo publish"),
    ("s3", _q(r"\baws s3 (?:cp|sync)\b.*?(s3://[^'\"\s]+)"), "aws s3"),
    ("gcs", _q(r"\bgsutil\b.*?\bcp\b.*?(gs://[^'\"\s]+)"), "gsutil cp"),
    ("azure", _q(r"\baz storage blob upload\b()"), "az storage"),
    ("github-release-asset", _q(r"\bgh release upload\b()"), "gh release upload"),
    (
        "github-release-asset",
        _q(r"(?:softprops/action-gh-release|ncipollo/release-action|goreleaser/goreleaser-action)()"),
        "release action",
    ),
    (
        "task",
        _q(
            r"^\s*(?:-\s*)?run:\s*((?:inv|invoke|make|just|task|npm run|nox|tox)\b"
            r"[^\n]*\b(?:publish|release|deploy|push|upload)\b[^\n]*)"
        ),
        "task runner step",
    ),
)
ENV_HINT_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*(?:REGISTRY|_URL|_REPOSITORY|_REPO)[A-Z0-9_]*):\s*['\"]?([^'\"\s#]+)")
IMAGES_BLOCK_RE = re.compile(r"^(\s*)images:\s*[|>][-+]?\s*$")
ENV_URL_RE = re.compile(r"^\s*url:\s*['\"]?([^'\"\s]+)")
TRIGGER_NAMES = ("push", "release", "workflow_dispatch", "workflow_call", "create", "schedule", "pull_request")
CALL_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?:\./|\$/)(\.github/workflows/[\w./-]+\.ya?ml)")
RELEASE_TRIGGERS = frozenset({"push-tags", "release", "create", "workflow_dispatch", "workflow_call"})


def workflow_triggers(text: str) -> list[str]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^(?:on|\"on\"|'on'|true):", line)), None)
    if start is None:
        return []
    inline = lines[start].split(":", 1)[1]
    found = {t for t in TRIGGER_NAMES if re.search(rf"\b{t}\b", inline)}
    for line in lines[start + 1 :]:
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        key = re.match(r"^\s{1,4}([\w-]+):", line)
        if key and key.group(1) in TRIGGER_NAMES:
            found.add(key.group(1))
        if re.match(r"^\s+tags:", line):
            found.add("push-tags")
    return sorted(found)


def _line_clue(line: str) -> tuple[str, str | None, str] | None:
    for kind, pattern, evidence in CLUE_PATTERNS:
        if m := pattern.search(line):
            return kind, next((g for g in m.groups() if g), None), f"{evidence}: {line.strip()[:120]}"
    if m := ENV_HINT_RE.match(line):
        return "hint", m.group(2), f"env {m.group(1)}"
    return None


@dataclass
class _ScanState:
    job: str | None = None
    in_jobs: bool = False
    env_until: int = -1
    images_indent: int | None = None


def _images_line(st: _ScanState, line: str) -> str | None:
    """An entry of a multi-line `images: |` block, or None once the block has ended."""
    if st.images_indent is None or not line.strip():
        return None
    if len(line) - len(line.lstrip()) <= st.images_indent:
        st.images_indent = None
        return None
    return line.strip().removeprefix("- ").split(",")[0].removeprefix("name=").strip("'\"")


def _structural(st: _ScanState, line: str, no: int) -> tuple[bool, str | None]:
    """Track jobs, `images:` blocks and `environment:` blocks; (consumed, an environment url)."""
    if m := IMAGES_BLOCK_RE.match(line):
        st.images_indent = len(m.group(1))
        return True, None
    st.in_jobs = st.in_jobs or bool(re.match(r"^jobs:\s*$", line))
    if st.in_jobs and (m := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)):
        st.job = m.group(1)
    if re.match(r"^\s*environment:", line):
        st.env_until = no + 4
        inline = re.search(r"url:\s*['\"]?([^'\"\s,}]+)", line)
        return True, inline.group(1) if inline else None
    if no <= st.env_until and (m := ENV_URL_RE.match(line)):
        return True, m.group(1)
    return False, None


def scan_workflow(path: str, text: str) -> list[Clue]:
    clues: list[Clue] = []
    st = _ScanState()
    for no, line in enumerate(text.splitlines(), start=1):
        if (image := _images_line(st, line)) is not None:
            clues.append(Clue("docker", image, path, st.job, no, f"metadata images: {image}"))
            continue
        consumed, env_url = _structural(st, line, no)
        if env_url:
            clues.append(Clue("deployment", env_url, path, st.job, no, "environment url"))
        if consumed:
            continue
        if found := _line_clue(line):
            clues.append(Clue(found[0], found[1], path, st.job, no, found[2]))
    return clues


VAR_RE = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")


def resolve_expression(value: str, repo: Repo, variables: dict[str, str], previous: Version | None) -> str:
    def repl(m: re.Match[str]) -> str:
        expr = m.group(1)
        if expr == "github.repository":
            return repo.slug
        if expr == "github.repository_owner":
            return repo.owner
        if expr in ("github.ref_name", "github.event.release.tag_name") or re.search(r"inputs\.\w*(tag|version)", expr):
            return "{tag}"
        if expr.startswith("vars.") and expr[5:] in variables:
            return variables[expr[5:]]
        return m.group(0)

    out = VAR_RE.sub(repl, value)
    if previous:
        out = out.replace(previous.tag, "{tag}")
        if previous.bare != previous.tag:
            out = out.replace(previous.bare, "{version}")
    return out


def _workflow_listing(gh: Gh, repo: Repo) -> tuple[list[dict[str, Any]], str]:
    """The default branch's workflow files, and a digest of their blob SHAs — one API call."""
    ref = urllib.parse.quote(repo.default_branch, safe="")
    listing = gh.api(repo.host, f"repos/{repo.slug}/contents/.github/workflows?ref={ref}", missing_ok=True) or []
    files = [f for f in listing if str(f.get("name", "")).endswith((".yml", ".yaml"))]
    digest = hashlib.sha256("\n".join(f"{f['path']}:{f.get('sha')}" for f in files).encode()).hexdigest()[:16]
    return files, digest


def _fetch_workflows(gh: Gh, repo: Repo) -> tuple[dict[str, str], str]:
    files, digest = _workflow_listing(gh, repo)
    ref = urllib.parse.quote(repo.default_branch, safe="")
    texts = {
        str(f["path"]): str(gh.api(repo.host, f"repos/{repo.slug}/contents/{f['path']}?ref={ref}", raw=True))
        for f in files
    }
    return texts, digest


def _repo_variables(gh: Gh, repo: Repo) -> dict[str, str]:
    """`${{ vars.X }}` values, when the user may read them; reading needs collaborator access."""
    try:
        listing = gh.api(repo.host, f"repos/{repo.slug}/actions/variables?per_page=100", missing_ok=True) or {}
    except HeraldError:
        return {}
    return {str(v["name"]): str(v["value"]) for v in listing.get("variables", [])}


def _run_evidence(gh: Gh, repo: Repo, sha: str) -> tuple[list[str], dict[str, str]]:
    """Publishing jobs that ran on the previous release's commit, and the URLs its deployments reported."""
    runs = gh.api(repo.host, f"repos/{repo.slug}/actions/runs?head_sha={sha}&per_page=50", missing_ok=True) or {}
    jobs_seen: list[str] = []
    for run in runs.get("workflow_runs", [])[:10]:
        jobs = gh.api(repo.host, f"repos/{repo.slug}/actions/runs/{run['id']}/jobs?per_page=100", missing_ok=True) or {}
        jobs_seen += [
            f"{run.get('path')} / {job.get('name')} ({job.get('conclusion')})"
            for job in jobs.get("jobs", [])
            if re.search(r"publish|upload|push|deploy|release", str(job.get("name", "")), re.IGNORECASE)
        ]
    urls: dict[str, str] = {}
    for dep in gh.api(repo.host, f"repos/{repo.slug}/deployments?sha={sha}&per_page=30", missing_ok=True) or []:
        path = f"repos/{repo.slug}/deployments/{dep['id']}/statuses?per_page=5"
        statuses = gh.api(repo.host, path, missing_ok=True) or []
        url = next((s.get("environment_url") for s in statuses if s.get("environment_url")), None)
        if url:
            urls[str(url)] = str(dep.get("environment"))
    return jobs_seen, urls


@dataclass
class SetupContext:
    repo: Repo
    variables: dict[str, str]
    previous: Version | None
    triggers: dict[str, list[str]]
    called: set[str]
    deployments: dict[str, str]

    def resolve(self, value: str) -> str:
        return resolve_expression(value, self.repo, self.variables, self.previous)

    def is_release_workflow(self, path: str) -> bool:
        return bool(set(self.triggers.get(path, [])) & RELEASE_TRIGGERS) or path in self.called

    @property
    def previous_tag(self) -> str:
        return self.previous.tag if self.previous else "?"


def _artifact_from(clue: Clue, ctx: SetupContext) -> dict[str, Any]:
    # A task runner's step names a command, not a place; the command is evidence, the place is a question.
    dest = ctx.resolve(clue.destination) if clue.destination and clue.kind != "task" else ""
    evidence = [f"{clue.workflow}:{clue.line} {clue.evidence}"]
    if "${{" in dest:
        evidence.append("destination comes from an expression this script cannot read (a secret or an input)")
    if not dest:
        evidence.append("the workflow does not say where this publishes: ask the user")
    seen = [
        f"deployment {env} of {ctx.previous_tag} reported {url}"
        for url, env in ctx.deployments.items()
        if dest and ctx.resolve(url) == dest
    ]
    return {
        "kind": clue.kind,
        "name": ctx.repo.name,
        "destination": dest,
        "workflow": clue.workflow,
        "job": clue.job or "",
        "evidence": evidence + seen,
        "confidence": "seen-in-run" if seen else "inferred",
    }


def propose_artifacts(clues: list[Clue], ctx: SetupContext) -> tuple[list[dict[str, Any]], list[str]]:
    artifacts: list[dict[str, Any]] = []
    hints: list[str] = []
    seen: set[tuple[str, str]] = set()
    for clue in (c for c in clues if ctx.is_release_workflow(c.workflow)):
        if clue.kind == "hint":
            hints.append(f"{clue.workflow}:{clue.line} {clue.evidence} = {ctx.resolve(clue.destination or '')}")
            continue
        art = _artifact_from(clue, ctx)
        key = (art["kind"], art["destination"] or clue.evidence)
        if key not in seen:
            seen.add(key)
            artifacts.append(art)
    known = {a["destination"] for a in artifacts}
    artifacts += [
        {
            "kind": "deployment",
            "name": env,
            "destination": ctx.resolve(url),
            "workflow": "",
            "job": "",
            "evidence": [f"deployment {env} of {ctx.previous_tag}"],
            "confidence": "seen-in-run",
        }
        for url, env in ctx.deployments.items()
        if ctx.resolve(url) not in known
    ]
    return artifacts, hints


def propose_surface(gh: Gh, repo: Repo) -> tuple[list[str], dict[str, list[str]]]:
    ref = urllib.parse.quote(repo.default_branch, safe="")
    tree = gh.api(repo.host, f"repos/{repo.slug}/git/trees/{ref}?recursive=1", missing_ok=True) or {}
    paths = [str(t["path"]) for t in tree.get("tree", []) if t.get("type") == "blob"]
    hits = {p: [x for x in paths if fnmatch.fnmatch(x, p)] for p in DEFAULT_SURFACE}
    used = [p for p, h in hits.items() if h]
    return used or list(DEFAULT_SURFACE), {p: h[:5] for p, h in hits.items() if h}


def setup_proposal(gh: Gh, repo: Repo) -> tuple[str, dict[str, Any]]:
    flow = detect_flow(gh, repo, load_config(repo))
    texts, digest = _fetch_workflows(gh, repo)
    finals = sorted(
        (v for t in list_tags(gh, repo, 3) if (v := parse_version(t)) and not v.is_pre), key=lambda v: v.key
    )
    previous = finals[-1] if finals else None
    runs, deployments = _run_evidence(gh, repo, commit_sha(gh, repo, previous.tag)) if previous else ([], {})
    ctx = SetupContext(
        repo=repo,
        variables=_repo_variables(gh, repo),
        previous=previous,
        triggers={path: workflow_triggers(text) for path, text in texts.items()},
        called={m.group(1) for text in texts.values() for line in text.splitlines() if (m := CALL_RE.match(line))},
        deployments=deployments,
    )
    clues = [c for path, text in texts.items() for c in scan_workflow(path, text)]
    artifacts, hints = propose_artifacts(clues, ctx)
    surface, surface_hits = propose_surface(gh, repo)
    report = {
        "flow": flow.__dict__,
        "workflows": ctx.triggers,
        "called_workflows": sorted(ctx.called),
        "run_evidence": runs,
        "hints": hints,
        "surface_hits": surface_hits,
        "artifacts": artifacts,
        "previous_release": previous.tag if previous else None,
        "workflow_digest": digest,
    }
    return render_proposal(repo, flow, surface, artifacts, hints, runs, digest), report


def render_proposal(
    repo: Repo,
    flow: Flow,
    surface: Sequence[str],
    artifacts: list[dict[str, Any]],
    hints: list[str],
    runs: list[str],
    digest: str,
) -> str:
    out = [
        f"# release-herald setup for {repo.url}",
        "# Proposed by `herald.py setup`. Edit anything wrong, then `herald.py setup --accept <this file>`.",
        "# Destinations may use {version} and {tag}; they are filled in per release.",
        "",
        f"url = {_toml_str(repo.url)}",
        f"flow = {_toml_str(flow.name)}  # {flow.evidence}; delete the line to detect on every run",
        f"production_branch = {_toml_str(flow.production)}",
        f"integration_branch = {_toml_str(flow.integration)}",
        'source = "auto"  # auto | prs | commits',
        f"workflow_digest = {_toml_str(digest)}  # the workflows this answer was derived from",
        "",
        "# Files whose change is a user-facing API or configuration change.",
        f"surface = {_toml_list(surface)}",
        "",
        "[exclude]",
        *(f"{key} = {_toml_list(values)}" for key, values in DEFAULT_EXCLUDE.items()),
    ]
    if runs:
        out += ["", "# Publishing jobs that ran for the previous release:", *(f"#   {r}" for r in runs)]
    if hints:
        out += ["", "# Environment values that may name a destination:", *(f"#   {h}" for h in hints)]
    if not artifacts:
        out += ["", "# No artifacts found. Add [[artifacts]] tables by hand, for example:", "# [[artifacts]]"]
        out += ['# kind = "docker"', '# name = "app"', '# destination = "registry.example/app:{version}"']
    for art in artifacts:
        out += ["", "[[artifacts]]"]
        out += [f"{key} = {_toml_str(str(art[key]))}" for key in ("kind", "name", "destination", "workflow", "job")]
        out.append(f"evidence = {_toml_list(art['evidence'])}")
        out.append(f'confidence = {_toml_str(art["confidence"])}  # set to "confirmed" once checked')
    return "\n".join(out) + "\n"


def accept_proposal(repo: Repo, proposal: Path) -> Path:
    text = proposal.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise HeraldError(f"{proposal} is not valid TOML: {exc}") from exc
    problems = validate_config(data)
    if str(data.get("url") or "").rstrip("/").lower() != repo.url.lower():
        problems.append(f"url must be {repo.url}")
    if problems:
        raise HeraldError(f"{proposal}: " + "; ".join(problems))
    target = config_path(repo)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="herald.py",
        description="Draft a GitHub release from its pull requests and commits, through gh only.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 2)[1] if __doc__ else None,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--repo", help="HOST/OWNER/REPO, OWNER/REPO or a URL; default: the current directory's")
        p.add_argument("--json", action="store_true", help="print JSON instead of text")
        return p

    add("repo", "the resolved repository, its flow and its config path (read-only)")

    p = add("setup", "propose the per-repository setup, or write a confirmed one")
    p.add_argument("--accept", type=Path, help="write this confirmed proposal as the repository's config")

    p = add("collect", "the release's change set, signals, quality report and digest")
    p.add_argument("--tag", required=True, help="the release tag; must exist on the remote")
    p.add_argument("--previous", help="the previous release tag; default: derived by version")
    p.add_argument("--source", choices=("auto", "prs", "commits"), help="override the configured source")

    p = add("check", "lint a drafted notes file against what was collected")
    p.add_argument("notes", type=Path)
    p.add_argument("--tag", required=True)
    p.add_argument("--collected", help="the collected JSON; default: the cache entry for --tag")
    p.add_argument("--dropped", default="", help="comma-separated items deliberately left out: 12,15,abc1234")

    p = add("publish", "create the release as a draft (or --live), or --update its notes")
    p.add_argument("--tag", required=True)
    p.add_argument("--notes-file", type=Path, required=True)
    p.add_argument("--title")
    p.add_argument("--live", action="store_true", help="publish immediately instead of creating a draft")
    p.add_argument("--update", action="store_true", help="replace the notes of an existing release")
    p.add_argument("--prerelease", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--dropped", default="", help="as for check")
    p.add_argument("--no-check", action="store_true", help="skip the lint that publish runs first")

    sub.add_parser("explain", help="how quality is graded and what the signals mean (offline)")
    return parser


def cmd_repo(args: argparse.Namespace, gh: Gh, repo: Repo) -> int:
    config = load_config(repo)
    data = {
        **repo.__dict__,
        "config": str(config.path),
        "configured": config.exists,
        "flow": detect_flow(gh, repo, config).__dict__,
        "cache": str(repo_cache_dir(repo)),
        "state": str(repo_state_dir(repo)),
    }
    print(json.dumps(data, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in data.items()))
    return 0


def cmd_setup(args: argparse.Namespace, gh: Gh, repo: Repo) -> int:
    if args.accept:
        print(f"wrote {accept_proposal(repo, args.accept)}")
        return 0
    text, report = setup_proposal(gh, repo)
    target = repo_state_dir(repo) / "setup-proposal.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    if args.json:
        print(json.dumps({**report, "proposal": str(target)}, indent=2))
    else:
        print(text)
        print(f"# proposal saved to {target}")
        print(f"# confirm or edit it with the user, then: herald.py setup --accept {target}")
    return 0


def cmd_collect(args: argparse.Namespace, gh: Gh, repo: Repo) -> int:
    collected = collect(gh, repo, args.tag, args.previous, args.source)
    print(json.dumps(collected, indent=2) if args.json else render_summary(collected))
    return 0


def _lint(args: argparse.Namespace, repo: Repo, notes: Path) -> list[Finding]:
    collected = load_collected(repo, args.tag, getattr(args, "collected", None))
    dropped = [d for d in args.dropped.split(",") if d.strip()]
    return check_notes(notes.read_text(encoding="utf-8"), collected, dropped)


def cmd_check(args: argparse.Namespace, gh: Gh, repo: Repo) -> int:
    findings = _lint(args, repo, args.notes)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        print("\n".join(f"{f.level}: {f.message}" for f in findings) or "clean")
    return 1 if any(f.level == "error" for f in findings) else 0


def cmd_publish(args: argparse.Namespace, gh: Gh, repo: Repo) -> int:
    if not args.no_check:
        findings = _lint(args, repo, args.notes_file)
        for f in findings:
            print(f"{f.level}: {f.message}", file=sys.stderr)
        errors = sum(f.level == "error" for f in findings)
        if errors:
            print(f"refusing to publish: {errors} error(s) above (fix them, or pass --no-check)", file=sys.stderr)
            return 1
    req = PublishRequest(args.tag, args.notes_file, args.title, args.live, args.update, args.prerelease)
    url = publish(gh, repo, req)
    print(f"{'updated' if args.update else 'published' if args.live else 'created as a draft'}: {url}")
    return 0


COMMANDS: dict[str, Callable[[argparse.Namespace, Gh, Repo], int]] = {
    "repo": cmd_repo,
    "setup": cmd_setup,
    "collect": cmd_collect,
    "check": cmd_check,
    "publish": cmd_publish,
}


def main(argv: Sequence[str] | None = None, gh: Gh | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "explain":
        print(EXPLAIN)
        return 0
    gh = gh or Gh()
    try:
        return COMMANDS[args.command](args, gh, resolve_repo(gh, args.repo))
    except HeraldError as exc:
        print(f"herald.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
