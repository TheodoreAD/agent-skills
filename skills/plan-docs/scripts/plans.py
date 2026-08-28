#!/usr/bin/env python3
"""Where a plan file goes, and the deterministic half of the plan-docs lifecycle.

`plan-docs` assumes a plan can be committed to the repo it describes. That holds for repos you own
and fails for employer and client repos, which is what the store is for: each repo's path mirrored
under `$PLANS_HOME`, outside every working tree. Which of the two a given repo uses is configuration,
never a guess — `~/.config/plan-docs/config.toml`, written by `plans.py config init`.

Every command is read-only unless it says otherwise, stdlib only, and prints `key: value` lines (most
also take `--json`) so an agent can act on the answer without opening a file.

    plans.py where                      # which directories this repo's plans live in
    plans.py new store-routing          # create today's plan file in the right one
    plans.py list                       # status-grouped index, with open-tag counts
    plans.py backlog                    # the same, across every repo on the machine
    plans.py tags --tag DEFERRED        # the anchored greps, without the anchoring mistakes
    plans.py set-status <file> planned  # runs the promotion gate first
    plans.py move <file> --to store     # a repo switching where it keeps plans
    plans.py refs <file>                # inbound references, before a retirement
    plans.py scan                       # no client's identity in a repo you publish
    plans.py repos --search auth        # what each repo is for, to route a plan by
    plans.py new <topic> --unscoped     # an idea with no repo yet
    plans.py graduate <file> --to <repo>  # ... once it has one
    plans.py install / uninstall        # set this machine up, or undo it

Exit codes: 0 ok, 1 error, 2 argparse usage, 3 needs-decision — no rule matched the repo, so the
agent must ask the user rather than pick a side.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

NEEDS_DECISION = 3

# Plans that belong to no repo yet live here, under the store. Underscore-prefixed so it can never
# collide with a mirrored root directory.
UNSCOPED_DIR = "_unscoped"

# Terms shorter than this are dropped from the confidentiality scan: a three-letter directory name
# matches half the English language and the resulting noise is what makes a gate get ignored.
MIN_PRIVATE_TERM = 4

# How deep under the projects root a git repo can sit. Measured on this author's machine: repos
# appear at depth 1 and 2 (a Bitbucket-style <project>/<repo> hierarchy); 3 leaves headroom.
MAX_REPO_DEPTH = 3

# Structural words in a root directory name — the hosting service and the domain suffix. They
# identify nobody, and gating on "github" or "com" would match everything.
HOSTING_WORDS = frozenset(
    {
        "com",
        "org",
        "net",
        "io",
        "co",
        "dev",
        "eu",
        "us",
        "github",
        "gitlab",
        "bitbucket",
        "visualstudio",
        "azure",
        "sourcehut",
        "codeberg",
        "git",
        "www",
        "corp",
        "inc",
        "group",
        "eng",
        "projects",
    }
)

MODES = ("repo", "store", "both")
TAG_NAMES = ("NEEDS CLARIFICATION", "DECISION", "PITFALL", "DEFERRED", "UNVERIFIED")
# Anchored exactly as SKILL.md specifies: a tag opens its own line, optionally after a list marker.
# An unanchored search matches every prose *mention* of a tag and reports a false backlog.
TAG_RE = re.compile(rf"^\s*[-*]?\s*\[({'|'.join(TAG_NAMES)}): ", re.MULTILINE)
TOPIC_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Grouping order for `list`: what needs attention first, terminal states last.
STATUS_ORDER = ("in-progress", "blocked", "planned", "idea", "landed", "abandoned", "superseded")

# The statuses a plan is finished in. `backlog` hides these by default: the cross-repo question is
# "what is still open everywhere", and a retired-but-not-yet-deleted plan is noise against it.
TERMINAL_STATUSES = ("landed", "abandoned", "superseded")

# A well-formed status line: one of these exactly, or one of the two prefixes followed by a reason.
# The vocabulary is open-ended at the end, never at the start, which is what makes drift detectable.
STATUS_EXACT = ("in-progress", "planned", "idea", "landed", "abandoned")
STATUS_PREFIXES = ("blocked on ", "superseded by ")

# How much of a status line `backlog` prints as a group heading before eliding it.
HEADING_WIDTH = 72

# The two gates SKILL.md states in prose, as data. Everything else is a free transition.
STATUS_GATES = {"planned": "NEEDS CLARIFICATION", "landed": "UNVERIFIED"}

CONFIG_SKELETON = """\
# plan-docs storage routing — read by skills/plan-docs/scripts/plans.py.
#
# A repo either keeps its plans in its own committed `plans/` directory ("repo"), or in the store
# outside every working tree ("store"), or is mid-switch and reads both ("both"). Keys under
# [roots] and [repos] are paths relative to `projects_root`; the most specific match wins
# ([repos] exact, then the longest [roots] prefix, then `default`).

projects_root = "~/projects"
store = "~/plans"

# No `default` on purpose: an unmatched repo makes `plans.py where` exit 3 so the agent asks,
# instead of silently writing a plans/ directory into somebody else's repo. Set one once the
# answer is boring — `default = "store"` is the usual choice on a machine with client work.
# default = "store"

# Roots whose contents may be NAMED in a repo you publish. Everything under every other root —
# the root, its projects, its repo names — is treated as confidential by `plans.py scan`.
# Defaults to the roots that keep their plans in-repo, which is usually the same set.
public_roots = ["github.com-personal"]

[roots]
# "github.com-personal" = "repo"

[repos]
# A repo that has stopped storing plans inside itself: writes go to the store, the plans already
# committed in the repo stay readable.
# "github.com-acme/legacy-api" = { mode = "both", write = "store" }

[private]
# Anything else that must never reach a published repo and is not a directory name: work email
# addresses, client product codenames, internal hostnames, ticket prefixes.
extra = []
# Names too generic to gate on — a work repo called "tools" would otherwise flag every mention of
# the word. Only add a name whose leaking would tell a reader nothing.
ignore = []

# What each repo is for — lets a plan be routed without grepping the repos. Only needed where a
# repo's README does not already say it in its first line. `plans.py describe <repo> "<text>"`.
[about]
"""

STORE_README = """\
# Plans store

Plan files (the `plan-docs` skill's `plans/YYYY-MM-DD-topic.md` convention) for repos that cannot
hold their own — employer and client work, where adding a `plans/` directory is not available.

Each repo's directory here mirrors its path under the projects root, so
`~/projects/<root>/<...>/<repo>` gets `<store>/<root>/<...>/<repo>`.

**This is a local git repository with no remote, deliberately.** Local history is the whole benefit
and carries no disclosure risk; a single personal remote accumulating several clients' internal
architecture is the outcome this design exists to avoid. Adding one is a per-root decision made
against that employer's actual policy, never a convenience.

Never symlink this store, or a subtree of it, into a work repo — that puts the content back inside
the tree repo-scoped agent reads walk.

Treat it as unbacked-up unless something was arranged deliberately.
"""


class PlanError(Exception):
    """Anything the user can fix: a malformed config, a missing file, a failed gate."""


class NeedsDecision(Exception):
    """No rule covers this repo. The agent has to ask the user, not pick a side for them."""


# --------------------------------------------------------------------------------------------
# configuration


@dataclass(frozen=True)
class Rule:
    """Where one repo's plans are read from, and which of those directories new files land in."""

    read: tuple[str, ...]
    write: str

    def describe(self) -> str:
        return f"read {'+'.join(self.read)}, write {self.write}"


@dataclass(frozen=True)
class Config:
    path: Path
    exists: bool
    projects_root: Path
    store: Path
    store_source: str
    default: Rule | None
    roots: dict[str, Rule]
    repos: dict[str, Rule]
    public_roots: tuple[str, ...]
    private_extra: tuple[str, ...]
    private_ignore: tuple[str, ...]
    about: dict[str, str]

    @property
    def unscoped(self) -> Path:
        """Plans that belong to no repo yet. Underscore-prefixed so it can't collide with a root."""
        return self.store / UNSCOPED_DIR

    def public_root_names(self) -> tuple[str, ...]:
        """Roots whose contents may be named in a published repo. Falls back to the roots configured
        to keep their plans in-repo, since a repo trusted to hold its own plans is one you own."""
        if self.public_roots:
            return self.public_roots
        return tuple(sorted(name for name, rule in self.roots.items() if rule.write == "repo"))


def config_path() -> Path:
    override = os.environ.get("PLAN_DOCS_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "plan-docs" / "config.toml"


def _rule_from_mode(mode: object, write: object, key: str) -> Rule:
    if mode not in MODES:
        raise PlanError(f"{key}: mode must be one of {', '.join(MODES)}, got {mode!r}")
    read = ("repo", "store") if mode == "both" else (str(mode),)
    # "both" writes to the repo unless told otherwise: a repo able to hold its own plans should.
    default_write = "repo" if mode == "both" else str(mode)
    target = default_write if write is None else str(write)
    if target not in read:
        raise PlanError(f"{key}: write = {target!r} is not one of the directories mode {mode!r} reads ({read})")
    return Rule(read=read, write=target)


def parse_rule(value: object, key: str) -> Rule:
    if isinstance(value, str):
        return _rule_from_mode(value, None, key)
    if isinstance(value, dict):
        unknown = sorted(k for k in value if k not in {"mode", "write"})
        if unknown:
            raise PlanError(f"{key}: unknown field(s) {unknown}; only mode and write are allowed")
        return _rule_from_mode(value.get("mode"), value.get("write"), key)
    raise PlanError(f"{key}: expected a mode string or a {{ mode, write }} table, got {type(value).__name__}")


def _rules(raw: dict[str, object], section: str) -> dict[str, Rule]:
    block = raw.get(section, {})
    if not isinstance(block, dict):
        raise PlanError(f"[{section}] must be a table of path = mode entries")
    out: dict[str, Rule] = {}
    for name, value in block.items():  # pyright: ignore[reportUnknownVariableType]
        out[str(name).strip("/")] = parse_rule(value, f"{section}.{name}")
    return out


def _path_field(raw: dict[str, object], key: str, fallback: Path) -> Path:
    value = raw.get(key)
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise PlanError(f"{key} must be a string path, got {type(value).__name__}")
    return Path(value).expanduser()


def load_config() -> Config:
    path = config_path()
    raw: dict[str, object] = {}
    if path.is_file():
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise PlanError(f"{path}: {exc}") from exc

    env_store = os.environ.get("PLANS_HOME")
    if env_store:
        store, store_source = Path(env_store).expanduser(), "$PLANS_HOME"
    elif "store" in raw:
        store, store_source = _path_field(raw, "store", Path.home() / "plans"), str(path)
    else:
        store, store_source = Path.home() / "plans", "default"

    default = raw.get("default")
    return Config(
        path=path,
        exists=path.is_file(),
        projects_root=_path_field(raw, "projects_root", Path.home() / "projects"),
        store=store,
        store_source=store_source,
        default=None if default is None else parse_rule(default, "default"),
        roots=_rules(raw, "roots"),
        repos=_rules(raw, "repos"),
        public_roots=_strings(raw.get("public_roots"), "public_roots"),
        private_extra=_strings(_table(raw, "private").get("extra"), "private.extra"),
        private_ignore=_strings(_table(raw, "private").get("ignore"), "private.ignore"),
        about={str(key): str(value) for key, value in _table(raw, "about").items()},
    )


def _table(raw: dict[str, object], key: str) -> dict[str, object]:
    block = raw.get(key, {})
    if not isinstance(block, dict):
        raise PlanError(f"[{key}] must be a table")
    return {str(name): value for name, value in block.items()}  # pyright: ignore[reportUnknownVariableType]


def _strings(value: object, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):  # pyright: ignore[reportUnknownVariableType]
        raise PlanError(f"{key} must be a list of strings")
    return tuple(str(item) for item in value)  # pyright: ignore[reportUnknownVariableType]


# --------------------------------------------------------------------------------------------
# routing


@dataclass(frozen=True)
class Routing:
    verdict: str  # ok | needs-decision
    reason: str
    repo_root: Path | None
    rel: str | None
    rule: Rule | None
    source: str
    dirs: dict[str, Path]

    @property
    def write_dir(self) -> Path:
        if self.rule is None or self.verdict != "ok":
            raise PlanError(self.reason)
        return self.dirs[self.rule.write]

    def read_dirs(self) -> list[tuple[str, Path]]:
        if self.rule is None:
            return []
        return [(where, self.dirs[where]) for where in self.rule.read if where in self.dirs]


def git(args: list[str], cwd: Path) -> str | None:
    """Run a git command, returning its stdout, or None if git failed or is unavailable."""
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def repo_root_of(start: Path) -> Path | None:
    top = git(["rev-parse", "--show-toplevel"], start)
    return Path(top) if top else None


def _match_rule(cfg: Config, rel: str | None) -> tuple[Rule | None, str]:
    """Most specific first: an exact [repos] entry, then the longest [roots] prefix, then default."""
    if rel is not None:
        if rel in cfg.repos:
            return cfg.repos[rel], f'repos entry "{rel}"'
        parts = rel.split("/")
        for depth in range(len(parts) - 1, 0, -1):
            prefix = "/".join(parts[:depth])
            if prefix in cfg.roots:
                return cfg.roots[prefix], f'roots entry "{prefix}"'
    if cfg.default is not None:
        return cfg.default, "default"
    return None, "no rule"


def resolve(start: Path, cfg: Config) -> Routing:
    root = repo_root_of(start)
    if root is None:
        return Routing("needs-decision", f"{start} is not inside a git repository", None, None, None, "no rule", {})

    try:
        rel = root.resolve().relative_to(cfg.projects_root.resolve()).as_posix()
    except (ValueError, OSError):
        rel = None

    rule, source = _match_rule(cfg, rel)
    dirs: dict[str, Path] = {"repo": root / "plans"}
    if rel is not None:
        dirs["store"] = cfg.store / rel

    if rule is None:
        reason = (
            f"no rule matches {rel or root} and no default is set in {cfg.path}"
            if cfg.exists
            else f"no config file at {cfg.path} (write one with: plans.py config init)"
        )
        return Routing("needs-decision", reason, root, rel, None, source, dirs)
    if "store" in rule.read and rel is None:
        reason = (
            f"{root} is not under projects_root ({cfg.projects_root}), so its store path cannot be "
            f'mirrored; move the clone under it or give this repo a mode = "repo" entry'
        )
        return Routing("needs-decision", reason, root, rel, rule, source, dirs)
    return Routing("ok", "", root, rel, rule, source, dirs)


def require_ok(routing: Routing) -> Routing:
    if routing.verdict != "ok":
        raise NeedsDecision(routing.reason)
    return routing


# --------------------------------------------------------------------------------------------
# plan files


@dataclass
class PlanFile:
    path: Path
    where: str
    status: str
    updated: str
    tags: Counter[str]
    depends_on: tuple[str, ...] = ()

    @property
    def group(self) -> str:
        for known in STATUS_ORDER:
            if self.status.startswith(known):
                return known
        return "unknown"


def status_is_known(status: str) -> bool:
    """Whether a status line is in the vocabulary at all. `blocked on …` and `superseded by …` carry
    a free-form reason; everything else has to match exactly, or it is drift."""
    return status in STATUS_EXACT or status.startswith(STATUS_PREFIXES)


def today() -> str:
    # tz-aware on purpose (ruff DTZ), then converted back to the machine's local calendar date,
    # which is the date a person reading the filename means.
    return datetime.now(UTC).astimezone().date().isoformat()


def parse_frontmatter(text: str) -> dict[str, str]:
    """The flat `key: value` block between the opening and closing `---`, values unquoted."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def parse_depends_on(value: str) -> tuple[str, ...]:
    """`depends_on: [repo-a, repo-b]` — the flat inline list the convention specifies, nothing more."""
    return tuple(part.strip().strip("\"'") for part in value.strip().strip("[]").split(",") if part.strip())


def read_plan(path: Path, where: str) -> PlanFile:
    text = path.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    return PlanFile(
        path=path,
        where=where,
        status=fields.get("status", "(no status)"),
        updated=fields.get("updated", ""),
        tags=Counter(match.group(1) for match in TAG_RE.finditer(text)),
        depends_on=parse_depends_on(fields.get("depends_on", "")),
    )


def plans_in(directory: Path, where: str) -> list[PlanFile]:
    if not directory.is_dir():
        return []
    return [read_plan(path, where) for path in sorted(directory.glob("*.md")) if path.name != "README.md"]


def plan_files(routing: Routing) -> list[PlanFile]:
    found: list[PlanFile] = []
    for where, directory in routing.read_dirs():
        found.extend(plans_in(directory, where))
    return found


def family_plans(cfg: Config) -> list[tuple[str, PlanFile]]:
    """Every plan on the machine, paired with the repo it belongs to, plus the unscoped area.

    Both possible directories are read for every repo, rather than only the ones its rule names:
    discovery must not depend on the routing config being complete, or the one repo nobody has
    routed yet is exactly the one whose backlog stays invisible. Cheap because `repo_paths` stops
    at each `.git` — no repo's own contents are walked.
    """
    found: list[tuple[str, PlanFile]] = []
    for rel in repo_paths(cfg):
        for where, directory in (("repo", cfg.projects_root / rel / "plans"), ("store", cfg.store / rel)):
            found.extend((rel, plan) for plan in plans_in(directory, where))
    found.extend((UNSCOPED_DIR, plan) for plan in plans_in(cfg.unscoped, "unscoped"))
    return found


def locate(routing: Routing, name: str) -> PlanFile:
    """Resolve a plan by path, or by bare filename across the repo's read directories."""
    candidate = Path(name)
    if candidate.is_file():
        resolved = candidate.resolve()
        for where, directory in routing.read_dirs():
            if resolved.parent == directory.resolve():
                return read_plan(resolved, where)
        return read_plan(resolved, "outside")

    matches = [plan for plan in plan_files(routing) if plan.path.name == Path(name).name]
    if not matches:
        searched = ", ".join(str(d) for _, d in routing.read_dirs()) or "(no readable directory)"
        raise PlanError(f"no plan named {name!r} in {searched}")
    if len(matches) > 1:
        joined = ", ".join(str(m.path) for m in matches)
        raise PlanError(f"{name!r} is ambiguous — pass a full path. Matches: {joined}")
    return matches[0]


def open_tags(path: Path, tag: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = TAG_RE.match(line)
        if match and match.group(1) == tag:
            hits.append((number, line.strip()))
    return hits


# --------------------------------------------------------------------------------------------
# confidentiality


def repo_paths(cfg: Config) -> list[str]:
    """Every git repo under the projects root, as a path relative to it.

    Stops descending the moment a `.git` is found, so a repo's own internal directory names never
    leak into the walk — collecting `src`, `tests` and `.venv` as if they identified a client is
    what makes a confidentiality gate noisy enough to be ignored.
    """
    if not cfg.projects_root.is_dir():
        return []
    found: list[str] = []

    def visit(path: Path, depth: int) -> None:
        if depth > MAX_REPO_DEPTH:
            return
        if (path / ".git").exists():
            found.append(path.relative_to(cfg.projects_root).as_posix())
            return
        for child in sorted(path.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                visit(child, depth + 1)

    visit(cfg.projects_root, 0)
    return found


def private_terms(cfg: Config) -> list[str]:
    """Every name that must not appear in a repo you publish, derived from the machine itself.

    A hard-coded list would have to live somewhere, and the only places available are a published
    repo (the thing being protected) or a file nobody updates. Deriving from the directory layout
    instead means a new client root is covered the moment it is cloned, with nothing to maintain:
    every path component under a non-public root — the root, its projects, its repo names — is a
    name that identifies work that is not yours to disclose.
    """
    public = set(cfg.public_root_names())
    terms: set[str] = set()
    if cfg.projects_root.is_dir():
        for path in cfg.projects_root.iterdir():
            if not path.is_dir() or path.name in public or path.name.startswith("."):
                continue
            terms.add(path.name)
            # An organisation appears in more forms than its directory name: a root called
            # `<org>.com-bitbucket-<something>` is the same client as an `@<org>.com` email address
            # in a doc. Splitting the root name on its separators catches both; the hosting words
            # are dropped because "github" and "com" identify nobody. Only ROOT names are split —
            # splitting repo names too would gate on ordinary words like "telemetry".
            terms.update(part for part in re.split(r"[.\-_]", path.name) if part.lower() not in HOSTING_WORDS)
    for rel in repo_paths(cfg):
        parts = rel.split("/")
        if parts[0] not in public:
            terms.update(parts)
    terms.update(cfg.private_extra)
    terms.difference_update(cfg.private_ignore)
    return sorted(term for term in terms if len(term) >= MIN_PRIVATE_TERM)


def scan_text(text: str, terms: list[str]) -> list[tuple[int, str, str]]:
    """(line number, term, line) for every private term appearing in the text, case-insensitively."""
    if not terms:
        return []
    pattern = re.compile("|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True)), re.IGNORECASE)
    hits: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = pattern.search(line)
        if match:
            hits.append((number, match.group(0), line.strip()))
    return hits


def scan_targets(root: Path, mode: str) -> list[tuple[str, str]]:
    """(label, text) pairs to scan: the tracked working tree, the staged diff, or all of history."""
    if mode == "staged":
        return [("(staged diff)", git(["diff", "--cached"], root) or "")]
    if mode == "history":
        return [("(history)", git(["log", "--all", "-p"], root) or "")]
    # Tracked *and* untracked-not-ignored: a plan file written a moment ago is exactly the thing
    # being scanned for, and it is not tracked yet.
    listed = git(["ls-files", "--cached", "--others", "--exclude-standard"], root) or ""
    pairs: list[tuple[str, str]] = []
    for name in listed.splitlines():
        path = root / name
        try:
            pairs.append((name, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: nothing greppable in it anyway
    return pairs


# --------------------------------------------------------------------------------------------
# repo knowledge


@dataclass
class RepoInfo:
    rel: str
    path: Path
    route: str
    about: str
    public: bool


def repo_summary(path: Path) -> str:
    """One line describing a repo, from its README's first real sentence — cheap and good enough.

    Deliberately not a grep of the repo: the point is to spend one small read per repo, not to
    search them. A repo whose README says nothing useful gets an [about] entry in the config.
    """
    for name in ("README.md", "readme.md", "AGENTS.md"):
        candidate = path / name
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "---", "<!--", "[!", "|", "```")):
                return stripped[:160]
    return ""


def known_repos(cfg: Config) -> list[RepoInfo]:
    """Every git repo under the projects root, with its route and a one-line description."""
    public = set(cfg.public_root_names())
    found: list[RepoInfo] = []
    for rel in repo_paths(cfg):
        path = cfg.projects_root / rel
        rule, _ = _match_rule(cfg, rel)
        found.append(
            RepoInfo(
                rel=rel,
                path=path,
                route=rule.write if rule else "unrouted",
                about=cfg.about.get(rel) or repo_summary(path),
                public=rel.split("/")[0] in public,
            )
        )
    return found


# --------------------------------------------------------------------------------------------
# commands


def cmd_where(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = resolve(args.path, cfg)
    if args.json:
        rule = routing.rule
        payload = {
            "verdict": routing.verdict,
            "reason": routing.reason,
            "repo_root": str(routing.repo_root) if routing.repo_root else None,
            "rel": routing.rel,
            "rule": None if rule is None else {"read": list(rule.read), "write": rule.write},
            "source": routing.source,
            "write_dir": str(routing.dirs[rule.write]) if rule and routing.verdict == "ok" else None,
            "read_dirs": {where: str(path) for where, path in routing.read_dirs()},
            "config": str(cfg.path),
        }
        print(json.dumps(payload, indent=2))
        return 0 if routing.verdict == "ok" else NEEDS_DECISION

    print(f"verdict: {routing.verdict}")
    if routing.verdict != "ok":
        print(f"reason:  {routing.reason}")
        print("choices: repo | store | both — ask the user, then record it in the config")
    print(f"repo:    {routing.repo_root or '(none)'}")
    print(f"rel:     {routing.rel or '(not under projects_root)'}")
    if routing.rule:
        print(f"rule:    {routing.rule.describe()}  ({routing.source})")
    if routing.verdict == "ok" and routing.rule:
        print(f"write:   {routing.dirs[routing.rule.write]}")
        for where, path in routing.read_dirs():
            print(f"read:    {where:<6} {path}")
    print(f"config:  {cfg.path}{'' if cfg.exists else ' (does not exist)'}")
    print(f"store:   {cfg.store} (from {cfg.store_source})")
    return 0 if routing.verdict == "ok" else NEEDS_DECISION


def cmd_new(args: argparse.Namespace) -> int:
    if not TOPIC_RE.match(args.topic):
        raise PlanError(f"topic {args.topic!r} must be kebab-case: lowercase letters, digits and single hyphens")
    cfg = load_config()
    if args.unscoped:
        return write_plan(cfg.unscoped, args.topic, args.status, "unscoped", None, cfg)
    routing = resolve(args.path, cfg)
    if args.to is None:
        require_ok(routing)
        target = routing.write_dir
        where = routing.rule.write if routing.rule else ""
    else:
        if args.to not in routing.dirs:
            raise PlanError(f"cannot write to {args.to!r} for this repo: {routing.reason or 'no such directory'}")
        target, where = routing.dirs[args.to], args.to

    origin = None
    if where == "store" and routing.repo_root:
        # The store's directory tree encodes the clone path; the origin URL is the identity that
        # survives the clone being moved or renamed, so that is what the file itself records.
        origin = git(["remote", "get-url", "origin"], routing.repo_root) or routing.rel
    return write_plan(target, args.topic, args.status, where, origin, cfg)


def write_plan(target: Path, topic: str, status: str, where: str, repo: str | None, cfg: Config) -> int:
    path = target / f"{today()}-{topic}.md"
    if path.exists():
        raise PlanError(f"{path} already exists — update it in place rather than opening a second file")

    lines = ["---", f"status: {status}", f"updated: {today()}"]
    if repo:
        lines.append(f"repo: {repo}")
    lines += ["---", "", "## Context", "", "## Open questions", "", "## Recommended direction", ""]

    target.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"created: {path}")
    print(f"where:   {where}")
    if where in {"store", "unscoped"} and not (cfg.store / ".git").is_dir():
        print(f"note:    {cfg.store} is not a git repository yet — plans.py install")
    if where == "unscoped":
        print("note:    belongs to no repo yet — plans.py graduate <file> --to <repo> when it does")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    cfg = load_config()
    if args.unscoped:
        sources = [("unscoped", cfg.unscoped)]
        plans = plans_in(cfg.unscoped, "unscoped")
    else:
        routing = require_ok(resolve(args.path, cfg))
        sources = routing.read_dirs()
        plans = plan_files(routing)
    if args.status:
        plans = [plan for plan in plans if plan.status.startswith(args.status)]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "path": str(plan.path),
                        "where": plan.where,
                        "status": plan.status,
                        "updated": plan.updated,
                        "tags": dict(plan.tags),
                    }
                    for plan in plans
                ],
                indent=2,
            )
        )
        return 0

    for where, path in sources:
        print(f"read:    {where:<8} {path}{'' if path.is_dir() else ' (does not exist)'}")
    if not plans:
        print("\n(no plan files)")
        return 0

    order = {name: index for index, name in enumerate((*STATUS_ORDER, "unknown"))}
    grouped: dict[str, list[PlanFile]] = {}
    for plan in sorted(plans, key=lambda p: (order[p.group], p.path.name)):
        grouped.setdefault(plan.status, []).append(plan)
    width = max(len(plan.path.name) for plan in plans)
    for status, group in grouped.items():
        print(f"\n{status} ({len(group)})")
        for plan in group:
            tags = "  ".join(f"{count} {name}" for name, count in sorted(plan.tags.items()))
            name = plan.path.name.ljust(width)
            print(f"  {plan.where:<6} {name}  updated {plan.updated or '?'}{'  ' + tags if tags else ''}")
    return 0


def cmd_backlog(args: argparse.Namespace) -> int:
    """What is open across every repo — the one question a per-repo `plans/` directory cannot answer.

    Ownership stays per-repo; this is a view over it, which is where every mature tool in this space
    landed. Nothing is moved, and nothing is written.
    """
    cfg = load_config()
    entries = _select_backlog(family_plans(cfg), args)

    if args.json:
        print(json.dumps([_plan_payload(rel, plan) for rel, plan in entries], indent=2))
        return 0

    print(f"root:    {cfg.projects_root}")
    print(f"store:   {cfg.store}")
    if not entries:
        print("\n(no plan files)")
        return 0

    _print_backlog_rows(entries)
    _print_dependencies(entries)
    _print_status_drift(entries)

    totals = Counter(name for _, plan in entries for name in plan.tags.elements())
    open_tags = "  ".join(f"{totals[name]} {name}" for name in TAG_NAMES if totals[name])
    print(f"\n{len(entries)} plan(s) across {len({rel for rel, _ in entries})} location(s)")
    if open_tags:
        print(f"open tags: {open_tags}")

    public = set(cfg.public_root_names())
    if any(rel.split("/")[0] not in public and rel != UNSCOPED_DIR for rel, _ in entries):
        print("Rows outside a public root name repos that are not yours to disclose — this listing is")
        print("for deciding what to work on, never for pasting into a repo you publish.")
    return 0


def _select_backlog(entries: list[tuple[str, PlanFile]], args: argparse.Namespace) -> list[tuple[str, PlanFile]]:
    """An explicit --status wins over the open-work default, so `--status landed` still works."""
    if args.status:
        entries = [pair for pair in entries if pair[1].status.startswith(args.status)]
    elif not args.all:
        entries = [pair for pair in entries if pair[1].group not in TERMINAL_STATUSES]
    if args.tag:
        entries = [pair for pair in entries if pair[1].tags.get(args.tag)]
    return entries


def _plan_payload(rel: str, plan: PlanFile) -> dict[str, object]:
    return {
        "repo": rel,
        "path": str(plan.path),
        "where": plan.where,
        "status": plan.status,
        "updated": plan.updated,
        "tags": dict(plan.tags),
        "depends_on": list(plan.depends_on),
    }


def _print_backlog_rows(entries: list[tuple[str, PlanFile]]) -> None:
    order = {name: index for index, name in enumerate((*STATUS_ORDER, "unknown"))}
    grouped: dict[str, list[tuple[str, PlanFile]]] = {}
    for rel, plan in sorted(entries, key=lambda pair: (order[pair[1].group], pair[0], pair[1].path.name)):
        grouped.setdefault(plan.status, []).append((rel, plan))
    repo_width = max(len(rel) for rel, _ in entries)
    name_width = max(len(plan.path.name) for _, plan in entries)
    for status, group in grouped.items():
        # A free-form status can be a whole paragraph; the drift section prints it in full instead.
        heading = status if len(status) <= HEADING_WIDTH else status[: HEADING_WIDTH - 1] + "…"
        print(f"\n{heading} ({len(group)})")
        for rel, plan in group:
            tags = "  ".join(f"{count} {name}" for name, count in sorted(plan.tags.items()))
            line = f"  {rel.ljust(repo_width)}  {plan.where:<6} {plan.path.name.ljust(name_width)}"
            print(f"{line}  updated {plan.updated or '?'}{'  ' + tags if tags else ''}")


def _print_dependencies(entries: list[tuple[str, PlanFile]]) -> None:
    """`depends_on` as a blocked-by view, which is the only thing that ever made the field useful.

    A plan naming a sibling repo is waiting on work there; from that repo's own `plans/` directory
    the wait is invisible, which is the discovery gap this whole command exists to close.
    """
    waiting: dict[str, list[str]] = {}
    for rel, plan in entries:
        for name in plan.depends_on:
            waiting.setdefault(name, []).append(f"{rel}/{plan.path.name}")
    if not waiting:
        return
    print("\nblocked by another repo (depends_on)")
    for name in sorted(waiting):
        for dependent in sorted(waiting[name]):
            print(f"  {name} <- {dependent}")


def _print_status_drift(entries: list[tuple[str, PlanFile]]) -> None:
    """Statuses outside the vocabulary. Only ever visible from here: each repo's own gate sees one
    repo, so a family-wide drift like `done` where `landed` is defined has nowhere else to surface."""
    drifted = sorted({plan.status for _, plan in entries if not status_is_known(plan.status)})
    if not drifted:
        return
    vocabulary = " | ".join((*STATUS_EXACT, "blocked on …", "superseded by …"))
    print(f"\nstatus drift ({len(drifted)}) — not in the vocabulary: {vocabulary}")
    for status in drifted:
        files = [f"{rel}/{plan.path.name}" for rel, plan in entries if plan.status == status]
        print(f"  {status!r}: {', '.join(sorted(files))}")


def cmd_tags(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
    targets = [locate(routing, args.file)] if args.file else plan_files(routing)
    wanted = [args.tag] if args.tag else list(TAG_NAMES)

    hits = 0
    for plan in targets:
        for tag in wanted:
            for number, line in open_tags(plan.path, tag):
                print(f"{plan.path}:{number}: {line}")
                hits += 1
    print(f"\n{hits} tag(s) across {len(targets)} file(s): {', '.join(wanted)}")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
    plan = locate(routing, args.file)

    gate = next((tag for prefix, tag in STATUS_GATES.items() if args.status.startswith(prefix)), None)
    if gate and not args.force:
        blocking = open_tags(plan.path, gate)
        if blocking:
            for number, line in blocking:
                print(f"{plan.path}:{number}: {line}")
            raise PlanError(
                f"{len(blocking)} open [{gate}: …] tag(s) block status {args.status!r}; "
                f"resolve them (or --force, which the convention does not) and re-run"
            )

    text = plan.path.read_text(encoding="utf-8")
    if not parse_frontmatter(text):
        raise PlanError(f"{plan.path} has no frontmatter block to update")
    lines = text.splitlines()
    end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    body = lines[1:end]
    kept = [line for line in body if not line.startswith(("status:", "updated:"))]
    front = [f"status: {args.status}", f"updated: {today()}", *kept]
    plan.path.write_text("\n".join(["---", *front, "---", *lines[end + 1 :], ""]), encoding="utf-8")
    print(f"updated: {plan.path}")
    print(f"status:  {plan.status} -> {args.status}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
    plan = locate(routing, args.file)
    if args.to not in routing.dirs:
        raise PlanError(f"this repo has no {args.to!r} directory: {routing.reason or 'not resolvable'}")
    target = routing.dirs[args.to]
    destination = target / plan.path.name
    if destination.exists():
        raise PlanError(f"{destination} already exists")
    if plan.path.parent.resolve() == target.resolve():
        print(f"unchanged: {plan.path} is already in {args.to}")
        return 0

    text = plan.path.read_text(encoding="utf-8")
    if args.to == "store" and "repo:" not in parse_frontmatter(text):
        origin = git(["remote", "get-url", "origin"], routing.repo_root) if routing.repo_root else None
        text = text.replace("\nupdated:", f"\nrepo: {origin or routing.rel}\nupdated:", 1)
    target.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    plan.path.unlink()
    print(f"moved:   {plan.path}")
    print(f"to:      {destination}")
    if plan.where == "repo":
        print("note:    stage the deletion in the repo (git rm / git add -u on that path) and commit it")
    return 0


def cmd_refs(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
    name = Path(args.file).name
    hits = 0
    if routing.repo_root:
        # `git grep` over tracked files: the same set a reviewer sees, without walking .venv or
        # build output. Matching the bare filename, since short-form references are the easy miss.
        output = git(["grep", "-n", "-F", "--", name], routing.repo_root)
        for line in (output or "").splitlines():
            print(f"repo   {line}")
            hits += 1
    store_dir = routing.dirs.get("store")
    if store_dir and store_dir.is_dir():
        for path in sorted(store_dir.rglob("*.md")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if name in line:
                    print(f"store  {path}:{number}:{line.strip()}")
                    hits += 1
    print(f"\n{hits} reference(s) to {name}")
    return 0


def list_terms(cfg: Config, terms: list[str]) -> int:
    for term in terms:
        print(term)
    print(f"\n{len(terms)} private term(s) derived from {cfg.projects_root}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """Refuse to let a client's identity reach a repo that gets published."""
    cfg = load_config()
    terms = private_terms(cfg)
    if args.list_terms:
        return list_terms(cfg, terms)
    root = repo_root_of(args.path)
    if root is None:
        raise PlanError(f"{args.path} is not inside a git repository")
    if not terms:
        print("terms:   none derived — set public_roots (and [private] extra) in the config first")
        print(f"config:  {cfg.path}")
        return 1

    tally: Counter[str] = Counter()
    hits = 0
    for label, text in scan_targets(root, args.mode):
        for number, term, line in scan_text(text, terms):
            if hits < args.samples:
                print(f"{label}:{number}: [{term}] {line[:160]}")
            tally[term.lower()] += 1
            hits += 1
    if hits > args.samples:
        print(f"... {hits - args.samples} more (raise --samples to see them)")
    print(f"\n{hits} hit(s) over {args.mode}, against {len(terms)} private term(s) from {cfg.projects_root}")
    for term, count in tally.most_common(10):
        print(f"  {count:>5}  {term}")
    if hits:
        print("\nEach names work that is not yours to disclose. Redact before committing. A term that")
        print("is a generic English word rather than an identity belongs in the config's")
        print("[private] ignore list — never widen public_roots to silence it.")
        print("A hit already in pushed history is a purge decision for the user, not an edit.")
    return 1 if hits else 0


def cmd_repos(args: argparse.Namespace) -> int:
    """What each repo is for, so a plan's destination is an informed question, not a grep."""
    cfg = load_config()
    repos = known_repos(cfg)
    if args.search:
        needles = [word.lower() for word in args.search.split()]
        scored = [(sum(word in f"{r.rel} {r.about}".lower() for word in needles), r) for r in repos]
        repos = [repo for score, repo in sorted(scored, key=lambda pair: -pair[0]) if score]
    if args.public_only:
        repos = [repo for repo in repos if repo.public]
    repos = repos[: args.limit]

    if args.json:
        print(
            json.dumps(
                [{"rel": r.rel, "route": r.route, "about": r.about, "public": r.public} for r in repos],
                indent=2,
            )
        )
        return 0
    if not repos:
        print("(no repos matched)")
        return 0
    width = max(len(repo.rel) for repo in repos)
    for repo in repos:
        flag = "public" if repo.public else "work"
        print(f"{repo.rel.ljust(width)}  {repo.route:<9} {flag:<6} {repo.about}")
    print(f"\n{len(repos)} repo(s). Offer the top few as AskUserQuestion options; never guess silently.")
    if any(not repo.public for repo in repos):
        print("Rows marked `work` name repos that are not yours to disclose — this listing is for")
        print("choosing a destination, never for pasting into a repo you publish.")
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    """Record what a repo is for, when its README does not say it well enough to route by."""
    cfg = load_config()
    if not cfg.exists:
        raise PlanError(f"no config at {cfg.path} — run: plans.py install")
    text = cfg.path.read_text(encoding="utf-8")
    entry = f'"{args.repo}" = {json.dumps(args.about)}'
    lines = text.splitlines()
    if "[about]" in lines:
        index = lines.index("[about]")
        lines = [line for line in lines if not line.startswith(f'"{args.repo}" =')]
        index = lines.index("[about]")
        lines.insert(index + 1, entry)
    else:
        lines += ["", "# What each repo is for — used to route a plan without grepping the repos.", "[about]", entry]
    cfg.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"described: {args.repo}")
    print(f"config:    {cfg.path}")
    return 0


def cmd_graduate(args: argparse.Namespace) -> int:
    """Move an unscoped plan into the repo that now exists for it."""
    cfg = load_config()
    plan = next((p for p in plans_in(cfg.unscoped, "unscoped") if p.path.name == Path(args.file).name), None)
    if plan is None:
        candidate = Path(args.file)
        if not candidate.is_file():
            raise PlanError(f"no plan named {args.file!r} in {cfg.unscoped}")
        plan = read_plan(candidate.resolve(), "unscoped")

    routing = require_ok(resolve(Path(args.to), cfg))
    target = routing.write_dir
    destination = target / plan.path.name
    if destination.exists():
        raise PlanError(f"{destination} already exists")

    text = plan.path.read_text(encoding="utf-8")
    if routing.rule and routing.rule.write == "store" and "repo" not in parse_frontmatter(text):
        origin = git(["remote", "get-url", "origin"], routing.repo_root) if routing.repo_root else None
        text = text.replace("\nupdated:", f"\nrepo: {origin or routing.rel}\nupdated:", 1)
    target.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    plan.path.unlink()
    print(f"graduated: {plan.path.name}")
    print(f"to:        {destination}")
    print(f"route:     {routing.rule.write if routing.rule else '?'} ({routing.source})")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Everything this skill needs on a machine, idempotently: config, store, unscoped area."""
    cfg = load_config()
    if not cfg.path.exists():
        cfg.path.parent.mkdir(parents=True, exist_ok=True)
        cfg.path.write_text(CONFIG_SKELETON, encoding="utf-8")
        print(f"created:     {cfg.path}")
    else:
        print(f"exists:      {cfg.path}")

    cfg.store.mkdir(parents=True, exist_ok=True)
    cfg.unscoped.mkdir(parents=True, exist_ok=True)
    if not (cfg.store / ".git").is_dir():
        if git(["init", "-q"], cfg.store) is None:
            raise PlanError(f"git init failed in {cfg.store}")
        print(f"initialized: {cfg.store} (git, no remote)")
    else:
        print(f"exists:      {cfg.store}")
    readme = cfg.store / "README.md"
    if not readme.exists():
        readme.write_text(STORE_README, encoding="utf-8")
        print(f"created:     {readme}")

    remotes = git(["remote"], cfg.store)
    if remotes:
        print(f"WARNING:     the store has remote(s) configured: {remotes.split()}")
        print("             one personal remote holding several clients' material is the outcome")
        print("             this store exists to avoid — check that this was deliberate")
    if not git(["config", "user.email"], cfg.store):
        print("todo:        the store has no git identity and cannot commit —")
        print("             git -C <store> config user.name/user.email")
    if not os.environ.get("PLANS_HOME"):
        print(f"todo:        PLANS_HOME is unset; the default {cfg.store} is in use. Export it from")
        print("             your shell profile so everything else on the machine agrees.")
    if not args.quiet:
        print("\nnext:        plans.py where   (in a repo)   /   plans.py new <topic> --unscoped")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Undo `install`. The store is never removed silently — it is the only copy of those plans."""
    cfg = load_config()
    if cfg.path.exists():
        if args.keep_config:
            print(f"kept:        {cfg.path}")
        else:
            cfg.path.unlink()
            print(f"removed:     {cfg.path}")
    else:
        print(f"absent:      {cfg.path}")

    held = [path for path in cfg.store.rglob("*.md") if path.name != "README.md"] if cfg.store.is_dir() else []
    if not args.purge_store:
        print(f"kept:        {cfg.store} ({len(held)} plan file(s)) — pass --purge-store to delete it")
        return 0
    if held and not args.force:
        raise PlanError(
            f"{cfg.store} still holds {len(held)} plan file(s); this is their only copy. "
            "Move what matters out first, or re-run with --force to delete them."
        )
    shutil.rmtree(cfg.store)
    print(f"removed:     {cfg.store} ({len(held)} plan file(s) deleted)")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    path = config_path()
    if args.action == "path":
        print(path)
        return 0
    if args.action == "init":
        if path.exists():
            print(f"exists:  {path} (left alone)")
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(CONFIG_SKELETON, encoding="utf-8")
        print(f"created: {path}")
        return 0

    cfg = load_config()
    print(f"config:        {cfg.path}{'' if cfg.exists else ' (does not exist)'}")
    print(f"projects_root: {cfg.projects_root}")
    print(f"store:         {cfg.store} (from {cfg.store_source})")
    print(f"default:       {cfg.default.describe() if cfg.default else '(none — unmatched repos exit 3)'}")
    for section, rules in (("roots", cfg.roots), ("repos", cfg.repos)):
        for key, rule in sorted(rules.items()):
            print(f"{section:<6} {key}: {rule.describe()}")
    return 0


# --------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plans.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name, help=help_text)
        child.add_argument("--path", type=Path, default=Path.cwd(), help="a path inside the repo (default: cwd)")
        return child

    where = add("where", "print the plan directories this repo reads and writes")
    where.add_argument("--json", action="store_true")
    where.set_defaults(func=cmd_where)

    new = add("new", "create today's plan file in the right directory")
    new.add_argument("topic", help="kebab-case topic, e.g. store-routing")
    new.add_argument("--status", default="idea", help="frontmatter status (default: idea)")
    new.add_argument("--to", choices=("repo", "store"), help="override the configured write target")
    new.add_argument("--unscoped", action="store_true", help="an idea with no repo yet; needs no repo at all")
    new.set_defaults(func=cmd_new)

    listing = add("list", "status-grouped index of this repo's plans, with open-tag counts")
    listing.add_argument("--status", help="only plans whose status starts with this")
    listing.add_argument("--json", action="store_true")
    listing.add_argument("--unscoped", action="store_true", help="the repo-less plans instead of this repo's")
    listing.set_defaults(func=cmd_list)

    backlog = add("backlog", "every open plan across every repo, in one index")
    backlog.add_argument("--status", help="only plans whose status starts with this")
    backlog.add_argument("--tag", choices=TAG_NAMES, help="only plans carrying this open tag")
    backlog.add_argument("--all", action="store_true", help="include landed, abandoned and superseded")
    backlog.add_argument("--json", action="store_true")
    backlog.set_defaults(func=cmd_backlog)

    tags = add("tags", "anchored search for the five plan-docs tags")
    tags.add_argument("--tag", choices=TAG_NAMES, help="one tag (default: all five)")
    tags.add_argument("--file", help="one plan, by path or bare filename (default: all)")
    tags.set_defaults(func=cmd_tags)

    status = add("set-status", "rewrite a plan's status and updated date, running the gate first")
    status.add_argument("file", help="plan path or bare filename")
    status.add_argument(
        "status", help="idea | planned | in-progress | blocked on … | landed | abandoned | superseded by …"
    )
    status.add_argument("--force", action="store_true", help="write the status even if its gate fails")
    status.set_defaults(func=cmd_set_status)

    move = add("move", "move a plan between the repo and the store")
    move.add_argument("file", help="plan path or bare filename")
    move.add_argument("--to", choices=("repo", "store"), required=True)
    move.set_defaults(func=cmd_move)

    refs = add("refs", "inbound references to a plan, across the repo and the store")
    refs.add_argument("file", help="plan path or bare filename")
    refs.set_defaults(func=cmd_refs)

    scan = add("scan", "fail if a private name reaches a repo you publish")
    scan.add_argument(
        "--mode", choices=("tree", "staged", "history"), default="tree", help="what to scan (default: tree)"
    )
    scan.add_argument("--samples", type=int, default=40, help="how many hit lines to print (default: 40)")
    scan.add_argument("--list-terms", action="store_true", help="print the derived terms and stop")
    scan.set_defaults(func=cmd_scan)

    repos = add("repos", "what each repo is for, to route a plan by")
    repos.add_argument("--search", help="rank by these words appearing in the path or description")
    repos.add_argument("--public-only", action="store_true", help="only repos under a public root")
    repos.add_argument("--limit", type=int, default=40)
    repos.add_argument("--json", action="store_true")
    repos.set_defaults(func=cmd_repos)

    describe = add("describe", "record what a repo is for, in the config")
    describe.add_argument("repo", help="path relative to projects_root, e.g. github.com-personal/agent-skills")
    describe.add_argument("about", help="one line: what belongs in that repo")
    describe.set_defaults(func=cmd_describe)

    graduate = add("graduate", "move an unscoped plan into the repo that now exists for it")
    graduate.add_argument("file", help="plan filename in the unscoped area, or a path")
    graduate.add_argument("--to", required=True, help="a path inside the destination repo")
    graduate.set_defaults(func=cmd_graduate)

    install = add("install", "set this machine up: config, store, unscoped area")
    install.add_argument("--quiet", action="store_true")
    install.set_defaults(func=cmd_install)

    uninstall = add("uninstall", "undo install; never deletes plans without being told twice")
    uninstall.add_argument("--keep-config", action="store_true", help="leave the config file in place")
    uninstall.add_argument("--purge-store", action="store_true", help="also delete the store directory")
    uninstall.add_argument("--force", action="store_true", help="allow --purge-store to delete plan files")
    uninstall.set_defaults(func=cmd_uninstall)

    config = add("config", "show, locate or create the routing config")
    config.add_argument("action", choices=("show", "path", "init"), nargs="?", default="show")
    config.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except NeedsDecision as exc:
        print("verdict: needs-decision", file=sys.stderr)
        print(f"reason:  {exc}", file=sys.stderr)
        print("choices: repo | store | both — ask the user, then record it in the config", file=sys.stderr)
        return NEEDS_DECISION
    except PlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
