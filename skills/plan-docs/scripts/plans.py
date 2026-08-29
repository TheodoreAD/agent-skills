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
    plans.py list                       # what is open here — scope, cap and filters below
    plans.py list --scope family        # the same, across every repo on the machine
    plans.py tags --tag DEFERRED        # the anchored greps, without the anchoring mistakes
    plans.py set-status <file> planned  # runs the promotion gate first
    plans.py move <file> --to store     # a repo switching where it keeps plans
    plans.py refs <file>                # inbound references, before a retirement
    plans.py archive --search <words>   # a retired plan, back out of git history
    plans.py scan                       # no client's identity in a repo you publish
    plans.py repos --search auth        # what each repo is for, to route a plan by
    plans.py new <topic> --unscoped     # an idea with no repo yet
    plans.py graduate <file> --to <repo>  # ... once it has one
    plans.py doctor                     # where plans live, what is enrolled, what is broken
    plans.py install --explain          # what setup would do, and what only the user can decide

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
from collections.abc import Iterator
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
# A plan filename as it appears cited inside another plan's prose. Used to find the pairs that a
# dirty-store harvest deliberately created instead of editing one file.
PLAN_NAME_RE = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md")

# Grouping order for `list`: what needs attention first, terminal states last.
STATUS_ORDER = ("in-progress", "blocked", "planned", "idea", "landed", "abandoned", "superseded")

# The statuses a plan is finished in. `backlog` hides these by default: the cross-repo question is
# "what is still open everywhere", and a retired-but-not-yet-deleted plan is noise against it.
TERMINAL_STATUSES = ("landed", "abandoned", "superseded")

# A well-formed status line: one of these exactly, or one of the two prefixes followed by a reason.
# The vocabulary is open-ended at the end, never at the start, which is what makes drift detectable.
STATUS_EXACT = ("in-progress", "planned", "idea", "landed", "abandoned")
STATUS_PREFIXES = ("blocked on ", "superseded by ")

# How much of a status line `list` prints as a group heading before eliding it.
HEADING_WIDTH = 72

# How many `idea` plans a listing shows before eliding the rest. Only that tier is capped — see
# `_print_rows`. Measured 2026-08-29 against this author's corpus: 10 keeps the whole-machine
# listing inside ~35 lines, which is the token cost this default exists to bound.
DEFAULT_IDEA_LIMIT = 10

SCOPES = ("auto", "repo", "family", "unscoped")

# Tables `config set` understands. A key's table is whatever precedes its first dot, but only when
# it is one of these — a [repos] key is a path full of dots and must not be split on every one.
CONFIG_TABLES = ("roots", "repos", "about", "private", "view")

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

# How many `idea` plans a listing shows before eliding the rest. Only that tier is capped: the live
# tiers are bounded by what can be in flight, while ideas accumulate forever. 0 disables the cap.
[view]
idea_limit = 10

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
    idea_limit: int

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
        idea_limit=_int_field(_table(raw, "view"), "idea_limit", DEFAULT_IDEA_LIMIT),
    )


def _int_field(raw: dict[str, object], key: str, fallback: int) -> int:
    value = raw.get(key)
    if value is None:
        return fallback
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PlanError(f"view.{key} must be a non-negative integer, got {value!r}")
    return value


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
# retired plans
#
# Retirement deletes the file, and git history is the archive. That is only a cheap trade if
# getting a retired plan back is one command rather than an archaeology session, which is what
# this section is: the deletion commits, a content search across them, and the `git show` that
# prints the file as it was the moment before it went.


# `git log --name-only` interleaves commit headers with the paths they touched, so the header's
# fields are joined by a separator no path can contain — which is also how the two line kinds are
# told apart. Not a leading record separator: Python counts \x1c-\x1f as whitespace, so `git()`'s
# own `.strip()` eats one off the front of the output and the first commit parses as a path.
UNIT = "\x1f"

# ERE metacharacters. A search phrase is escaped with these before it reaches git's pickaxe, which
# takes POSIX extended regex, not Python's.
ERE_SPECIAL = re.compile(r"([.^$*+?()\[\]{}|\\])")

MIGRATED_RE = re.compile(r"^#{2,}\s+migrated to\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s")
BULLET_RE = re.compile(r"^([-*]|\d+[.)])\s")

# How much of a `## Migrated to` entry a listing row shows before eliding it.
TARGET_WIDTH = 110


@dataclass(frozen=True)
class Source:
    """One git history that can hold retired plans: a repo's own `plans/`, or the store's mirror."""

    where: str
    root: Path
    prefix: str  # directory inside that root where plans live, trailing slash included


@dataclass
class Retired:
    """A plan file as of the commit that deleted it."""

    repo: str
    where: str
    root: Path
    path: str
    sha: str
    date: str
    subject: str
    status: str = ""
    migrated: tuple[str, ...] = ()
    live: str = ""  # set when a file of this name exists now: moved, not retired

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def restore(self) -> str:
        # `^` is the commit before the deletion, which is the last one that still had the file.
        return f"git -C {self.root} show {self.sha[:12]}^:{self.path}"


def is_git_repo(path: Path) -> bool:
    return path.is_dir() and git(["rev-parse", "--git-dir"], path) is not None


def archive_sources(cfg: Config, routing: Routing | None) -> list[Source]:
    """Which histories to search: this repo's route, or every repo on the machine plus the store."""
    if routing is None:
        found = [Source("repo", cfg.projects_root / rel, "plans/") for rel in repo_paths(cfg)]
        return [*found, Source("store", cfg.store, "")]
    found = []
    for where, _ in routing.read_dirs():
        if where == "repo" and routing.repo_root is not None:
            found.append(Source("repo", routing.repo_root, "plans/"))
        elif where == "store" and routing.rel is not None:
            found.append(Source("store", cfg.store, f"{routing.rel}/"))
    return found


def source_label(cfg: Config, source: Source, path: str) -> str:
    """Which repo a retired plan belonged to, whichever history it turned up in."""
    if source.where == "store":
        return path.rsplit("/", 1)[0] if "/" in path else UNSCOPED_DIR
    try:
        return source.root.resolve().relative_to(cfg.projects_root.resolve()).as_posix()
    except (ValueError, OSError):
        return source.root.name


def is_plan_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.endswith(".md") and name != "README.md"


def deleted_plans(cfg: Config, source: Source) -> list[Retired]:
    """Every plan file deleted from one history, newest deletion first, one entry per path.

    A path deleted, restored and deleted again keeps only the latest deletion — that is the commit
    whose parent holds the file's final state, and the earlier one is reachable from `--file`.
    """
    pathspec = source.prefix or "."
    out = git(
        ["log", "--diff-filter=D", "--name-only", f"--format=%H{UNIT}%as{UNIT}%s", "--", pathspec],
        source.root,
    )
    found: list[Retired] = []
    seen: set[str] = set()
    sha = date = subject = ""
    for line in (out or "").splitlines():
        if UNIT in line:
            sha, _, rest = line.partition(UNIT)
            date, _, subject = rest.partition(UNIT)
            continue
        path = line.strip()
        if not path or not sha or not is_plan_path(path) or path in seen:
            continue
        seen.add(path)
        found.append(
            Retired(
                repo=source_label(cfg, source, path),
                where=source.where,
                root=source.root,
                path=path,
                sha=sha,
                date=date,
                subject=subject,
            )
        )
    return found


def pickaxe_paths(source: Source, phrase: str) -> set[str]:
    """Paths whose content ever gained or lost `phrase`, as git's pickaxe reports them.

    The words are joined by a whitespace class rather than searched literally: plan prose is
    reflowed by the repo's formatter, so any phrase long enough to be worth searching for has
    probably been split across a line break somewhere in its history.
    """
    pattern = "[[:space:]]+".join(ERE_SPECIAL.sub(r"\\\1", word) for word in phrase.split())
    if not pattern:
        return set()
    out = git(
        ["log", "--pickaxe-regex", f"-S{pattern}", "--name-only", "--format=", "--", source.prefix or "."],
        source.root,
    )
    return {line.strip() for line in (out or "").splitlines() if line.strip()}


def migrated_targets(text: str) -> tuple[str, ...]:
    """The `## Migrated to` entries — where a retired plan's content actually went.

    Continuation lines are folded back into the entry above them: every plan in a repo with a
    formatter has its bullets wrapped, and a listing that prints each wrapped line as its own
    destination reads as though the content went to twice as many places as it did.
    """
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if MIGRATED_RE.match(line)), None)
    if start is None:
        return ()
    found: list[str] = []
    current = ""
    for line in lines[start + 1 :]:
        if HEADING_RE.match(line):
            break
        stripped = line.strip()
        if stripped and not BULLET_RE.match(stripped):
            current = f"{current} {stripped}".strip()
            continue
        if current:
            found.append(current)
        current = BULLET_RE.sub("", stripped, count=1) if stripped else ""
    if current:
        found.append(current)
    return tuple(found)


def fill_details(entry: Retired) -> Retired:
    """The plan's final state: its status, and what it says it was migrated to. One blob read."""
    text = git(["show", f"{entry.sha}^:{entry.path}"], entry.root)
    if text is None:
        return entry
    entry.status = parse_frontmatter(text).get("status", "")
    entry.migrated = migrated_targets(text)
    return entry


def plan_pathspec(source: Source, name: str) -> str:
    """Where one plan file sits in a history. The store searched whole has no prefix to anchor on,
    so the name is matched at any depth — git's own `*` spans `/` in a pathspec."""
    return f"{source.prefix}{name}" if source.prefix else f"*/{name}"


def plan_history(source: Source, name: str) -> list[tuple[str, str, str]]:
    """Every commit that touched one plan path, newest first: (sha, date, subject)."""
    out = git(["log", f"--format=%H{UNIT}%as{UNIT}%s", "--", plan_pathspec(source, name)], source.root)
    found: list[tuple[str, str, str]] = []
    for line in (out or "").splitlines():
        sha, _, rest = line.partition(UNIT)
        date, _, subject = rest.partition(UNIT)
        found.append((sha, date, subject))
    return found


def retired_plans(cfg: Config, sources: list[Source], search: str | None) -> list[Retired]:
    found: list[Retired] = []
    for source in sources:
        entries = deleted_plans(cfg, source)
        if search and entries:
            matched = pickaxe_paths(source, search)
            entries = [entry for entry in entries if entry.path in matched]
        found.extend(entries)
    found.sort(key=lambda entry: (entry.date, entry.name), reverse=True)
    return found


def live_plans(cfg: Config, routing: Routing | None) -> dict[str, Path]:
    """Plan files that exist right now, by filename — the same scope the archive is searched at."""
    if routing is None:
        return {plan.path.name: plan.path for _, plan in family_plans(cfg)}
    return {plan.path.name: plan.path for plan in plan_files(routing)}


def mark_live(cfg: Config, routing: Routing | None, entries: list[Retired]) -> None:
    """Flag entries whose filename exists now — a plan moved between repo and store, not retired."""
    live = live_plans(cfg, routing)
    for entry in entries:
        current = live.get(entry.name)
        if current is not None:
            entry.live = str(current)


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


def transcript_root() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(base).expanduser() if base else Path.home() / ".claude") / "projects"


def encode_project_dir(path: Path) -> str:
    """How Claude Code names a project's transcript directory: every non-alphanumeric becomes `-`.

    Verified against this machine's own directories 2026-08-29 — `/home/u/projects/github.com-x/y`
    becomes `-home-u-projects-github-com-x-y`, so dots collapse to dashes like separators do.
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def _candidate_repos(cfg: Config) -> Iterator[Path]:
    """cwd's repo first — the overwhelmingly common answer — then every repo under the root.

    A generator so the projects-root walk only happens when cwd is *not* the session's repo, which
    is exactly the drifted case and the only one worth paying for.
    """
    here = repo_root_of(Path.cwd())
    if here is not None:
        yield here
    for rel in repo_paths(cfg):
        yield cfg.projects_root / rel


def claude_session_repo(cfg: Config) -> Path | None:
    """The session's repo per Claude Code's own transcript layout, or None under anything else.

    Claude Code writes each session's transcript to `<config>/projects/<encoded project path>/`, so
    the directory holding this session's file names the repo the session belongs to — decided when
    the session began and unaffected by any later `cd`.

    The encoding is lossy (several characters all become `-`), so candidates are encoded and
    compared rather than the directory name being decoded, which would be ambiguous.
    """
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id):
        return None
    try:
        matches = list(transcript_root().glob(f"*/{session_id}.jsonl"))
    except OSError:
        return None
    if len(matches) != 1:
        return None
    encoded = matches[0].parent.name
    return next((repo for repo in _candidate_repos(cfg) if encode_project_dir(repo) == encoded), None)


def session_anchor(cfg: Config) -> tuple[Path | None, str]:
    """The repo this session belongs to, and which signal said so.

    Three tiers, most trustworthy first, because the guard that uses this is only as good as its
    weakest input and a caller deserves to know which one it got:

    1. `$PLAN_DOCS_SESSION_REPO` — the vendor-neutral escape hatch. Any harness can export it at
       session start, and it is the only tier available to one that is not Claude Code.
    2. Claude Code's session transcript, which is exact and needs no setup.
    3. cwd — the weak tier. It is what the guard used before an anchor existed, and it cannot detect
       a drifted directory, since the thing being checked and the thing checking it both moved.

    Never `--path`: that names what a command is *about*, not where the session lives.
    """
    override = os.environ.get("PLAN_DOCS_SESSION_REPO", "").strip()
    if override:
        root = repo_root_of(Path(override).expanduser())
        if root is None:
            raise PlanError(f"$PLAN_DOCS_SESSION_REPO is {override!r}, which is not inside a git repository")
        return root, "$PLAN_DOCS_SESSION_REPO"
    found = claude_session_repo(cfg)
    if found is not None:
        return found, "this session's transcript"
    return repo_root_of(Path.cwd()), "cwd (no session anchor — see doctor)"


def session_repo(cfg: Config) -> Path | None:
    return session_anchor(cfg)[0]


def session_is_anchored(cfg: Config) -> bool:
    """Whether the answer came from a real anchor rather than the drift-prone fallback."""
    return not session_anchor(cfg)[1].startswith("cwd")


def is_foreign(target: Path | None, cfg: Config) -> bool:
    here = session_repo(cfg)
    return target is not None and here is not None and here.resolve() != target.resolve()


def warn_cross_repo(target: Path, cfg: Config, action: str) -> None:
    """Say so when a command is about to touch a working tree that is not the session's.

    Not a refusal: these act on files that already exist, and there are legitimate reasons. But
    parallel sessions on one machine share a working tree, so a file appearing in someone else's is
    worth a line every single time rather than a surprise later.
    """
    if is_foreign(target, cfg):
        print(f"WARNING: {action} touches {target}, which is not the repo this session is in.")
        print("         Parallel sessions share a working tree. Prefer doing this from a session")
        print("         inside that repo; if you continue, tell the user what landed where.")


def resolve_repo_argument(value: str, cfg: Config) -> Path:
    """A repo named either by path or by its path relative to `projects_root`.

    Both spellings appear in practice — an agent that just ran `list --scope family` has the
    relative form in hand, and one that resolved a directory has the absolute.
    """
    direct = Path(value).expanduser()
    if direct.is_dir():
        return direct
    candidate = cfg.projects_root / value
    if candidate.is_dir():
        return candidate
    raise PlanError(f"no repo at {value!r}: tried {direct} and {candidate}")


def cmd_new(args: argparse.Namespace) -> int:
    if not TOPIC_RE.match(args.topic):
        raise PlanError(f"topic {args.topic!r} must be kebab-case: lowercase letters, digits and single hyphens")
    cfg = load_config()
    if args.unscoped:
        if args.to or args.for_repo:
            raise PlanError("--unscoped belongs to no repo, so it cannot be combined with --to or --for")
        return write_plan(cfg.unscoped, args.topic, args.status, "unscoped", None, cfg)
    if args.for_repo:
        return file_for_repo(args, cfg)
    routing = resolve(args.path, cfg)
    if routing.rule and routing.rule.write == "repo" and is_foreign(routing.repo_root, cfg):
        # Refused rather than warned: `--for` is the correct way to record something against
        # another repo, so writing a new file into its tree has no remaining legitimate use.
        anchored = session_is_anchored(cfg)
        source = "this session started in" if anchored else "cwd says this session is in"
        hint = (
            ""
            if anchored
            else "\n  If that IS the repo you are in:    cwd has drifted; cd back and re-run without --path."
        )
        raise PlanError(
            f"{source} {session_repo(cfg)}, but this would create a plan in {routing.repo_root} "
            f"— a tree a parallel session may be holding.\n"
            f"  If the plan belongs to that repo:  new {args.topic} --for {routing.rel or routing.repo_root}"
            f"{hint}"
        )
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
    belongs = routing.rel or (str(routing.repo_root) if routing.repo_root else None)
    return write_plan(target, args.topic, args.status, where, origin, cfg, belongs_to=belongs)


def file_for_repo(args: argparse.Namespace, cfg: Config) -> int:
    """File a plan against a repo this session is not working in, without touching its tree.

    Always the store mirror, never the repo's own `plans/`, whatever that repo's route says. That is
    the whole point: writing into another repo's working tree is the foreign commit this exists to
    stop, on a machine where parallel sessions share one tree. The owning repo picks it up later,
    from inside itself, committing only to itself.
    """
    if args.to:
        raise PlanError("--for already decides where the file goes (the target's store mirror); drop --to")
    target_root = resolve_repo_argument(args.for_repo, cfg)
    routing = resolve(target_root, cfg)
    if routing.repo_root is None:
        raise PlanError(f"{target_root} is not inside a git repository")

    here = resolve(args.path, cfg).repo_root
    if here is not None and here.resolve() == routing.repo_root.resolve():
        raise PlanError(f"--for names the repo this session is already in; use plain `new {args.topic}`")
    if "store" not in routing.dirs:
        raise PlanError(
            f"{routing.repo_root} is not under projects_root ({cfg.projects_root}), so it has no store "
            "mirror to file into; move the clone under it or plan in that repo directly"
        )

    origin = git(["remote", "get-url", "origin"], routing.repo_root) or routing.rel
    code = write_plan(routing.dirs["store"], args.topic, args.status, "store", origin, cfg)
    print(f"filed for: {routing.rel or routing.repo_root}")
    if routing.rule and routing.rule.write == "repo":
        print("note:      that repo keeps its own plans, so this is in transit — a session working")
        print("           there absorbs it with: plans.py move <file> --to repo")
    print("commit:    write the plan, then commit it in the store straight away —")
    print(f"           git -C {cfg.store} add <path> && git -C {cfg.store} commit")
    return code


def write_plan(
    target: Path, topic: str, status: str, where: str, repo: str | None, cfg: Config, belongs_to: str | None = None
) -> int:
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
    if belongs_to:
        # Named on every create, not only when something looks wrong. The cross-repo guard compares
        # against cwd, and cwd can drift — when it does, both sides of that comparison drift with it
        # and the guard cannot fire at all. Saying which repo the plan just became the property of
        # is the one check that survives drift, because it depends on nothing that drifted.
        print(f"repo:    {belongs_to}")
    if where in {"store", "unscoped"} and not (cfg.store / ".git").is_dir():
        print(f"note:    {cfg.store} is not a git repository yet — plans.py install")
    if where == "unscoped":
        print("note:    belongs to no repo yet — plans.py graduate <file> --to <repo> when it does")
    return 0


def is_within(path: Path, parent: Path) -> bool:
    try:
        return path.resolve().is_relative_to(parent.resolve())
    except OSError:
        return False


def auto_scope(cfg: Config, routing: Routing) -> str:
    """`repo` when the session sits in a routed repo, `family` otherwise.

    Inside the store the answer is `family`: the store is a git repository, so `resolve` finds a
    repo root there, but it is not a project and a session that has cd'd into it is asking about
    everything rather than about the store's own directory.
    """
    if routing.repo_root is not None and is_within(routing.repo_root, cfg.store):
        return "family"
    return "repo" if routing.verdict == "ok" else "family"


def repo_scope_plans(cfg: Config, routing: Routing) -> list[tuple[str, PlanFile]]:
    """Everything about the repo the session is in, plus the plans that belong to no repo yet.

    Deliberately not `routing.read_dirs()`. A route decides where a *write* lands; letting it decide
    what a *read* can see is what kept unscoped plans invisible from every repo on a machine whose
    roots are all `mode = "repo"` — the set with no other route back to attention was the one set
    nothing surfaced. Same argument `family_plans` already makes: discovery must not depend on the
    routing config being complete.
    """
    label = routing.rel or (routing.repo_root.name if routing.repo_root else "(repo)")
    found: list[tuple[str, PlanFile]] = []
    for where in ("repo", "store"):
        if where in routing.dirs:
            found.extend((label, plan) for plan in plans_in(routing.dirs[where], where))
    found.extend((UNSCOPED_DIR, plan) for plan in plans_in(cfg.unscoped, "unscoped"))
    return found


def cmd_list(args: argparse.Namespace) -> int:
    """What is open, at whichever breadth the question was asked at.

    One command rather than two: a per-repo index and a machine-wide one differ only in breadth, and
    `--scope` is that axis. Ownership stays per-repo either way — this is a view, nothing is written.
    """
    cfg = load_config()
    routing = resolve(args.path, cfg)
    scope = args.scope if args.scope != "auto" else auto_scope(cfg, routing)

    if scope == "repo":
        require_ok(routing)
        entries = repo_scope_plans(cfg, routing)
    elif scope == "unscoped":
        entries = [(UNSCOPED_DIR, plan) for plan in plans_in(cfg.unscoped, "unscoped")]
    else:
        entries = family_plans(cfg)

    all_entries = entries
    entries = _select(entries, args)
    if args.json:
        print(json.dumps([_plan_payload(rel, plan) for rel, plan in entries], indent=2))
        return 0

    print(f"scope:   {scope}{' (auto)' if args.scope == 'auto' else ''}")
    if scope == "repo":
        print(f"repo:    {routing.rel or routing.repo_root}")
    else:
        print(f"root:    {cfg.projects_root}")
    print(f"store:   {cfg.store}")
    if not entries:
        # Not necessarily an empty repo: a `plans/` holding nothing but landed plans is a
        # retirement backlog, and "(no plan files)" on its own would be a lie of omission.
        print("\n(no open plans)")
        _print_retirements_owed(all_entries, args)
        return 0

    elided = _print_rows(entries, show_repo=scope != "repo", limit=_idea_limit(args, cfg), stale=args.stale)
    if scope == "repo":
        _print_absorbable(routing)
        _print_inbound_dependencies(cfg, routing)
    elif scope == "family":
        _print_family_dependencies(entries)
        _print_status_drift(entries)
    _print_footer(cfg, entries, elided)
    _print_retirements_owed(all_entries, args)
    return 0


def _print_retirements_owed(entries: list[tuple[str, PlanFile]], args: argparse.Namespace) -> None:
    """Terminal-status plans are hidden from the rows but never silently.

    `plans/` is a working set that empties out, so a `landed` plan still sitting in one is a
    retirement owed — the single most useful thing this command can point at. Hiding it with no
    trace is what the pre-scope `list` avoided by showing terminal rows outright; the count says the
    same thing in one line instead of N.
    """
    if args.all or args.status:
        return
    owed = [pair for pair in entries if pair[1].group in TERMINAL_STATUSES]
    if owed:
        print(f"{len(owed)} plan(s) at a terminal status await retirement — --all to see them")


def _idea_limit(args: argparse.Namespace, cfg: Config) -> int:
    """`--limit` wins over the configured cap; 0 means no cap at either level."""
    return cfg.idea_limit if args.limit is None else args.limit


def _select(entries: list[tuple[str, PlanFile]], args: argparse.Namespace) -> list[tuple[str, PlanFile]]:
    """An explicit --status wins over the open-work default, so `--status landed` still works."""
    if args.status:
        entries = [pair for pair in entries if pair[1].status.startswith(args.status)]
    elif not args.all:
        entries = [pair for pair in entries if pair[1].group not in TERMINAL_STATUSES]
    if args.tag:
        entries = [pair for pair in entries if pair[1].tags.get(args.tag)]
    if args.stale is not None:
        entries = [pair for pair in entries if _is_stale(pair[1], args.stale)]
    if args.since is not None:
        entries = [pair for pair in entries if _moved_since(pair[1], args.since)]
    return entries


def _is_stale(plan: PlanFile, days: int) -> bool:
    age = age_in_days(plan.updated)
    return age is None or age >= days


def _moved_since(plan: PlanFile, since: str) -> bool:
    """Whether a plan was updated on or after a date.

    An unstamped plan is excluded here and *included* by `--stale`, which is not an inconsistency:
    the questions are opposites. "What has nobody touched" must surface a file with no evidence of
    being touched; "what moved this week" must not claim a file moved when nothing says it did.
    """
    return bool(plan.updated) and plan.updated >= since


def iso_date(value: str) -> str:
    """Validate a YYYY-MM-DD argument at parse time, so a typo fails before anything is listed."""
    try:
        datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a YYYY-MM-DD date") from None
    return value


def age_in_days(updated: str) -> int | None:
    """Days since a plan's `updated` stamp, or None when it has none or it does not parse.

    None is not zero: a plan with no stamp is drift, and treating it as fresh would hide exactly the
    file most likely to have been abandoned.
    """
    try:
        stamped = datetime.strptime(updated, "%Y-%m-%d").replace(tzinfo=UTC).date()
    except ValueError:
        return None
    return (datetime.now(UTC).astimezone().date() - stamped).days


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


def _print_rows(entries: list[tuple[str, PlanFile]], *, show_repo: bool, limit: int, stale: int | None) -> int:
    """Render the grouped index, capping the `idea` tier only. Returns how many rows were elided.

    Only `idea` is capped. The live tiers are bounded by how much work can actually be in flight —
    measured 2026-08-29 on this author's machine, 19 live against 49 ideas — while `idea` grows
    without bound, so it is the only group whose output cost is unbounded. A limit that can hide
    in-progress work would make the command unsafe to trust, and a truncated answer to "what is
    next" is worse than an untruncated long one.
    """
    order = {name: index for index, name in enumerate((*STATUS_ORDER, "unknown"))}
    grouped: dict[str, list[tuple[str, PlanFile]]] = {}
    for rel, plan in sorted(entries, key=lambda pair: (order[pair[1].group], pair[0], pair[1].path.name)):
        grouped.setdefault(plan.status, []).append((rel, plan))
    repo_width = max(len(rel) for rel, _ in entries) if show_repo else 0
    name_width = max(len(plan.path.name) for _, plan in entries)

    elided = 0
    for status, group in grouped.items():
        shown = group
        if status == "idea" and limit > 0 and len(group) > limit:
            # Newest first inside the capped tier: an idea nobody has touched in months is the one
            # row a cap may drop without costing anything.
            shown = sorted(group, key=lambda pair: pair[1].updated, reverse=True)[:limit]
            shown = sorted(shown, key=lambda pair: (pair[0], pair[1].path.name))
            elided += len(group) - limit
        # A free-form status can be a whole paragraph; the drift section prints it in full instead.
        heading = status if len(status) <= HEADING_WIDTH else status[: HEADING_WIDTH - 1] + "…"
        capped = f", showing {len(shown)}" if len(shown) != len(group) else ""
        print(f"\n{heading} ({len(group)}{capped})")
        for rel, plan in shown:
            tags = "  ".join(f"{count} {name}" for name, count in sorted(plan.tags.items()))
            prefix = f"  {rel.ljust(repo_width)}  " if show_repo else "  "
            line = f"{prefix}{plan.where:<8} {plan.path.name.ljust(name_width)}"
            age = age_in_days(plan.updated)
            stamp = f"updated {plan.updated or '?'}"
            if stale is not None:
                stamp += f" ({age}d)" if age is not None else " (no stamp)"
            print(f"{line}  {stamp}{'  ' + tags if tags else ''}")
    return elided


def _print_footer(cfg: Config, entries: list[tuple[str, PlanFile]], elided: int) -> None:
    totals = Counter(name for _, plan in entries for name in plan.tags.elements())
    open_tags = "  ".join(f"{totals[name]} {name}" for name in TAG_NAMES if totals[name])
    print(f"\n{len(entries)} plan(s) across {len({rel for rel, _ in entries})} location(s)")
    if elided:
        print(f"{elided} idea(s) not shown — --limit 0 for all of them")
    if open_tags:
        print(f"open tags: {open_tags}")

    public = set(cfg.public_root_names())
    if any(rel.split("/")[0] not in public and rel != UNSCOPED_DIR for rel, _ in entries):
        print("Rows outside a public root name repos that are not yours to disclose — this listing is")
        print("for deciding what to work on, never for pasting into a repo you publish.")


def _blocked_by(entries: list[tuple[str, PlanFile]]) -> dict[str, list[str]]:
    """`depends_on` as a blocked-by view, which is the only thing that ever made the field useful.

    A plan naming a sibling repo is waiting on work there; from that repo's own `plans/` directory
    the wait is invisible, which is the discovery gap this command exists to close. Keyed by the
    bare repo name the field carries, not by a path — `depends_on: [repo-tasks]` names a repo.
    """
    waiting: dict[str, list[str]] = {}
    for rel, plan in entries:
        for name in plan.depends_on:
            waiting.setdefault(name, []).append(f"{rel}/{plan.path.name}")
    return waiting


def _print_family_dependencies(entries: list[tuple[str, PlanFile]]) -> None:
    """Counts, not edges.

    Every edge printed here is one line, so the section grows with the corpus exactly the way the
    `idea` tier did — measured 2026-08-29, 22 of 81 lines in this author's family listing, the
    largest single section once the idea cap landed. Capping one tier only moves an unbounded cost
    unless the other unbounded section is bounded too. The edges themselves are actionable in one
    place, `--scope repo` inside the repo being waited on, so that is where they are printed.
    """
    waiting = _blocked_by(entries)
    if not waiting:
        return
    print("\nblocked by another repo (depends_on) — run --scope repo there for the plans")
    for name in sorted(waiting):
        print(f"  {name} <- {len(waiting[name])} plan(s)")


def _print_absorbable(routing: Routing) -> None:
    """A session that skipped the start-of-session proposal still sees the backlog here."""
    pending = absorbable(routing)
    if pending:
        print(f"\n{len(pending)} plan(s) filed for this repo await absorption — plans.py absorb")


def _print_inbound_dependencies(cfg: Config, routing: Routing) -> None:
    """What other repos are waiting on *this* one — the actionable half, and bounded by definition.

    Needs the family pass: a repo's own `plans/` cannot contain the plan that names it. Cheap, since
    `repo_paths` stops at each `.git` without walking any repo's contents.
    """
    name = (routing.rel or "").split("/")[-1] or (routing.repo_root.name if routing.repo_root else "")
    dependents = sorted(_blocked_by(family_plans(cfg)).get(name, []))
    if not dependents:
        return
    print(f"\nwaiting on this repo ({len(dependents)})")
    for dependent in dependents:
        print(f"  {dependent}")


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

    found = [
        {"path": str(plan.path), "tag": tag, "line": number, "text": line}
        for plan in targets
        for tag in wanted
        for number, line in open_tags(plan.path, tag)
    ]
    if args.json:
        print(json.dumps(found, indent=2))
        return 0

    for hit in found:
        print(f"{hit['path']}:{hit['line']}: {hit['text']}")
    print(f"\n{len(found)} tag(s) across {len(targets)} file(s): {', '.join(wanted)}")
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
    if args.json:
        payload = {"path": str(plan.path), "from": plan.status, "to": args.status, "updated": today()}
        print(json.dumps(payload, indent=2))
        return 0
    print(f"updated: {plan.path}")
    print(f"status:  {plan.status} -> {args.status}")
    return 0


def plan_references(text: str, exclude: str) -> list[str]:
    """Plan filenames a plan's own text names, other than itself.

    The dirty-store rule requires a plan written alongside an existing one to reference it, so the
    reference is the signal that two files cover one topic. Deterministic, unlike guessing from
    similar titles — and it costs the author nothing they were not already told to write.
    """
    return sorted({name for name in PLAN_NAME_RE.findall(text) if name != exclude})


def consolidation_pairs(routing: Routing, pending: list[PlanFile]) -> dict[str, list[str]]:
    """For each plan awaiting absorption, the plans it says it relates to that actually exist.

    Checked against both directories: a plan filed while the store was dirty may reference another
    filed plan, or one already committed in the repo.
    """
    known = {plan.path.name for plan in pending}
    known |= {path.name for path in routing.dirs["repo"].glob("*.md")} if routing.dirs["repo"].is_dir() else set()
    pairs: dict[str, list[str]] = {}
    for plan in pending:
        cited = plan_references(plan.path.read_text(encoding="utf-8"), plan.path.name)
        related = [name for name in cited if name in known]
        if related:
            pairs[plan.path.name] = related
    return pairs


def absorbable(routing: Routing) -> list[PlanFile]:
    """Plans filed for this repo that belong in its own tree.

    Only for a repo whose route writes to `repo`: for one routed to the store, the mirror *is* the
    permanent home and nothing is in transit. That is the whole distinction, read from route plus
    location rather than from a frontmatter field nobody would maintain.
    """
    if routing.rule is None or routing.rule.write != "repo" or "store" not in routing.dirs:
        return []
    return plans_in(routing.dirs["store"], "store")


def cmd_absorb(args: argparse.Namespace) -> int:
    """Take plans filed for this repo from the store into the repo's own `plans/`.

    Run from inside the repo that owns them, which is what keeps this from being a foreign commit:
    the session writes only to its own tree, and to the store only to remove what it just took.
    """
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
    pending = absorbable(routing)

    pairs = consolidation_pairs(routing, pending) if pending else {}

    if args.json:
        payload = [
            {
                "path": str(plan.path),
                "name": plan.path.name,
                "status": plan.status,
                "updated": plan.updated,
                "consolidate_with": pairs.get(plan.path.name, []),
            }
            for plan in pending
        ]
        print(json.dumps({"repo": routing.rel, "absorbable": payload}, indent=2))
        return 0

    if not pending:
        # Silence is the point: this runs at the top of a session, and a session with nothing
        # waiting should not be told so.
        if args.verbose:
            print(f"nothing filed for {routing.rel or routing.repo_root}")
        return 0

    if not args.apply:
        return _report_absorbable(routing, pending, pairs)

    target = routing.dirs["repo"]
    wanted = set(args.only) if args.only else None
    chosen = [plan for plan in pending if wanted is None or plan.path.name in wanted]
    moved, blocked = _take_plans(chosen, target)

    for plan, destination in moved:
        print(f"absorbed: {plan.path.name} -> {destination}")
    for plan in blocked:
        print(f"CONFLICT: {plan.path.name} already exists in {target}; resolve it by hand — the two")
        print(f"          cover the same topic, which is a merge, not a rename. Filed copy: {plan.path}")
    if moved:
        print(f"\n{len(moved)} absorbed. Run this repo's quality gate, then commit here and in {cfg.store}.")
    landed = {plan.path.name for plan, _ in moved}
    owed = {name: related for name, related in pairs.items() if name in landed}
    if owed:
        print()
        for name, related in owed.items():
            print(f"consolidate: {name} with {', '.join(related)} — now both in {target}")
        _print_consolidation_note()
    return 1 if blocked else 0


def _report_absorbable(routing: Routing, pending: list[PlanFile], pairs: dict[str, list[str]]) -> int:
    print(f"{len(pending)} plan(s) filed for {routing.rel or routing.repo_root}, awaiting absorption:")
    for plan in pending:
        related = pairs.get(plan.path.name)
        note = f"  -> consolidate with {', '.join(related)}" if related else ""
        print(f"  {plan.path.name:<52} {plan.status}  updated {plan.updated or '?'}{note}")
    if pairs:
        _print_consolidation_note()
    print("\nabsorb them with --apply; each moves into this repo's plans/ and leaves the store.")
    print("Commit both: this repo (the additions) and the store (the removals).")
    return 0


def _print_consolidation_note() -> None:
    """Why these exist, said once rather than per pair.

    They are not an accident: a harvest that found the store dirty was told to add a file rather
    than edit one another session might be holding. Absorption is where that debt is paid, because
    it is the first moment both halves are in one tree and one session owns them.
    """
    print("\nThese are two halves of one topic, split because the store was dirty when the second")
    print("was written. Merge them into one plan, keep the earlier filename, and delete the other")
    print("— the reference that paired them is prose, so nothing re-surfaces this once absorbed.")


def _take_plans(chosen: list[PlanFile], target: Path) -> tuple[list[tuple[PlanFile, Path]], list[PlanFile]]:
    """Move each plan into the target directory, skipping any whose name is already taken.

    A collision is never renamed around: two plans sharing a name is the moment a merge is wanted,
    and a silent rename hides exactly that.
    """
    moved: list[tuple[PlanFile, Path]] = []
    blocked: list[PlanFile] = []
    for plan in chosen:
        destination = target / plan.path.name
        if destination.exists():
            blocked.append(plan)
            continue
        target.mkdir(parents=True, exist_ok=True)
        destination.write_text(plan.path.read_text(encoding="utf-8"), encoding="utf-8")
        plan.path.unlink()
        moved.append((plan, destination))
    return moved, blocked


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
    found: list[dict[str, object]] = []
    if routing.repo_root:
        # `git grep` over tracked files: the same set a reviewer sees, without walking .venv or
        # build output. Matching the bare filename, since short-form references are the easy miss.
        output = git(["grep", "-n", "-F", "--", name], routing.repo_root)
        for line in (output or "").splitlines():
            path, _, rest = line.partition(":")
            number, _, text = rest.partition(":")
            found.append({"where": "repo", "path": path, "line": int(number) if number.isdigit() else 0, "text": text})
    store_dir = routing.dirs.get("store")
    if store_dir and store_dir.is_dir():
        for path in sorted(store_dir.rglob("*.md")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if name in line:
                    found.append({"where": "store", "path": str(path), "line": number, "text": line.strip()})

    if args.json:
        print(json.dumps({"file": name, "references": found}, indent=2))
        return 0
    for hit in found:
        print(f"{hit['where']:<6} {hit['path']}:{hit['line']}:{hit['text']}")
    print(f"\n{len(found)} reference(s) to {name}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Retired plans, read back out of git history.

    Retirement deletes the file everywhere, which is only a cheap rule because the file is still in
    the repository — this is the command that makes that true in practice rather than in principle.
    Nothing is written, and a plan is never restored to the working tree: what comes back is its
    content on stdout, which is what a session actually needs.
    """
    cfg = load_config()
    routing = None if args.all else require_ok(resolve(args.path, cfg))
    sources = archive_sources(cfg, routing)

    if args.show:
        return show_retired(cfg, routing, sources, args.show)
    if args.file:
        return show_lifecycle(cfg, sources, args.file)

    entries = retired_plans(cfg, sources, args.search)
    shown = [fill_details(entry) for entry in entries[: args.limit]]
    mark_live(cfg, routing, shown)
    if args.json:
        print(json.dumps([_retired_payload(entry) for entry in shown], indent=2))
        return 0

    _print_sources(cfg, sources, everywhere=routing is None)
    if not shown:
        scope = f" containing {args.search!r}" if args.search else ""
        print(f"\n(no retired plan{scope} in the histories above)")
        return 0

    _print_retired_rows(shown)
    counted = f"{len(shown)} of {len(entries)}" if len(shown) < len(entries) else str(len(entries))
    print(f"\n{counted} retired plan(s)")
    print("archive --show <file> prints one back; --file <file> its whole lifecycle")
    _warn_if_private(cfg, shown)
    return 0


def _print_sources(cfg: Config, sources: list[Source], *, everywhere: bool) -> None:
    """The histories being searched. `--all` is summarised rather than listed: one line per repo is
    dozens of lines of work-repo paths before the first result."""
    store = next((source for source in sources if source.where == "store"), None)
    if everywhere:
        print(f"scope:   every repo under {cfg.projects_root} ({len(sources) - (store is not None)})")
    else:
        for source in sources:
            if source.where == "repo":
                print(f"repo:    {source.root}/{source.prefix}")
    if store is not None:
        state = "" if is_git_repo(store.root) else "  (not a git repository — nothing here is recoverable)"
        print(f"store:   {store.root}/{store.prefix}{state}")


def _warn_if_private(cfg: Config, entries: list[Retired]) -> None:
    """Same caution `backlog` and `repos` carry: these rows name repos that are not yours to name."""
    public = set(cfg.public_root_names())
    if any(entry.repo.split("/")[0] not in public and entry.repo != UNSCOPED_DIR for entry in entries):
        print("Rows outside a public root name repos that are not yours to disclose — this listing is")
        print("for finding your own reasoning again, never for pasting into a repo you publish.")


def _print_retired_rows(entries: list[Retired]) -> None:
    name_width = max(len(entry.name) for entry in entries)
    status_width = max(len(entry.status or "?") for entry in entries)
    for entry in entries:
        print(
            f"\n{entry.date}  {entry.name.ljust(name_width)}  {(entry.status or '?').ljust(status_width)}"
            f"  {entry.repo} ({entry.where})"
        )
        for target in entry.migrated[:3]:
            elided = target if len(target) <= TARGET_WIDTH else target[: TARGET_WIDTH - 1] + "…"
            print(f"    migrated to: {elided}")
        if entry.live:
            print(f"    still live:  {entry.live} — moved, not retired")
        else:
            print(f"    {entry.restore}")


def _retired_payload(entry: Retired) -> dict[str, object]:
    return {
        "repo": entry.repo,
        "where": entry.where,
        "root": str(entry.root),
        "path": entry.path,
        "name": entry.name,
        "deleted": entry.date,
        "sha": entry.sha,
        "subject": entry.subject,
        "status": entry.status,
        "migrated_to": list(entry.migrated),
        "live": entry.live,
        "restore": entry.restore,
    }


def _match_retired(cfg: Config, sources: list[Source], name: str) -> list[Retired]:
    wanted = Path(name).name
    return [entry for entry in retired_plans(cfg, sources, None) if entry.name == wanted]


def show_retired(cfg: Config, routing: Routing | None, sources: list[Source], name: str) -> int:
    """Print a retired plan's final content — the state of the file the moment before it went."""
    wanted = Path(name).name
    matches = _match_retired(cfg, sources, wanted)
    # A plan moved from a repo to the store left a deletion commit behind exactly like a retired one.
    # Printing that old copy would hand back a stale version of a file that is live somewhere else.
    mark_live(cfg, routing, matches)
    matches = [entry for entry in matches if not entry.live]
    if not matches:
        current = live_plans(cfg, routing).get(wanted)
        if current is not None:
            raise PlanError(f"{wanted} is not retired — it is still on the working set at {current}")
        searched = ", ".join(f"{source.root}/{source.prefix}" for source in sources)
        raise PlanError(f"no retired plan named {wanted!r} in {searched}")
    if len(matches) > 1:
        listed = ", ".join(f"{entry.repo} ({entry.date})" for entry in matches)
        raise PlanError(f"{wanted!r} was retired in more than one place — run with --path there: {listed}")

    entry = fill_details(matches[0])
    text = git(["show", f"{entry.sha}^:{entry.path}"], entry.root)
    if text is None:
        raise PlanError(f"git could not read {entry.path} from {entry.sha}^ in {entry.root}")
    print(f"plan:    {entry.path}")
    print(f"repo:    {entry.repo} ({entry.where})")
    print(f"deleted: {entry.sha[:12]} {entry.date} {entry.subject}")
    print(f"restore: {entry.restore}")
    print(f"\n{text}")
    return 0


def show_lifecycle(cfg: Config, sources: list[Source], name: str) -> int:
    """Every commit that touched one plan, in each history that has it — drafting to retirement."""
    wanted = Path(name).name
    retired = _match_retired(cfg, sources, wanted)
    total = 0
    for source in sources:
        commits = plan_history(source, wanted)
        if not commits:
            continue
        print(f"\n{source.root}/{plan_pathspec(source, wanted)}")
        for sha, date, subject in commits:
            print(f"  {sha[:12]}  {date}  {subject}")
        total += len(commits)
        for entry in retired:
            if entry.root == source.root:
                print(f"  retired here — {entry.restore}")
    print(f"\n{total} commit(s) touching {wanted}")
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
    if routing.rule and routing.rule.write == "repo" and routing.repo_root:
        warn_cross_repo(routing.repo_root, cfg, f"graduate {plan.path.name}")
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


@dataclass(frozen=True)
class Decision:
    """One thing the user has to settle, printed as data for an agent to put to them."""

    key: str
    what: str
    current: str
    suggest: str
    cost: str


def install_decisions(cfg: Config) -> list[Decision]:
    """Everything `install` cannot decide on the user's behalf, with what it would guess and why.

    Printed rather than prompted. The script has to keep working when a human runs it by hand, and
    an interactive prompt inside an agent's Bash call hangs the session with nothing to type into —
    so the agent is the interactive surface and this is the data it asks from.
    """
    unset = "(unset — the default is in use)"
    decisions = [
        Decision(
            key="projects_root",
            what="the directory every repo path is measured from, and the shape the store mirrors",
            current=f"{cfg.projects_root}" + ("" if cfg.exists and cfg.path.is_file() else f" {unset}"),
            suggest=str(cfg.projects_root),
            cost="a wrong root matches no repo to any rule, so every plan asks where it goes",
        ),
        Decision(
            key="store",
            what="where plans live for repos that cannot hold their own",
            current=f"{cfg.store} (from {cfg.store_source})",
            suggest=str(cfg.store),
            cost="moving it later leaves the old copy behind; it is the only copy of those plans",
        ),
    ]

    decisions.append(
        Decision(
            key="default",
            what="the route for a repo no [roots] or [repos] rule matches",
            current=cfg.default.describe() if cfg.default else "(none — an unmatched repo exits 3 and asks)",
            suggest="store on a machine with client work; leave unset to be asked each time",
            cost="a default of `repo` silently adds plans/ to repos you do not own",
        )
    )

    # One question per unrouted root only when nothing else answers it. With a `default` set, every
    # one of them has the same answer already, and asking anyway turned a six-question walkthrough
    # into a twelve-question one on this author's machine — questions the user pays for and whose
    # answer was never in doubt.
    roots = sorted({rel.split("/")[0] for rel in repo_paths(cfg)})
    unrouted = [name for name in roots if name not in cfg.roots]
    if unrouted and cfg.default is None:
        decisions += [
            Decision(
                key=f"roots.{name}",
                what=f"where plans go for every repo under {name}/",
                current="(no rule, and no default — these repos cannot be planned in until this is set)",
                suggest="repo if these are yours to commit to, store if they are an employer's",
                cost='guessing "repo" writes a plans/ directory into someone else\'s repository',
            )
            for name in unrouted
        ]
    decisions.append(
        Decision(
            key="public_roots",
            what="roots whose names may appear in a repo you publish; everything else is scanned for",
            current=", ".join(cfg.public_roots) or "(unset — falls back to the roots routed `repo`)",
            suggest=", ".join(name for name in roots if cfg.roots.get(name, Rule((), "")).write == "repo") or "(none)",
            cost="too wide silences a whole organisation's names in `scan`, which is the gate that "
            "stops a client's identity reaching a published repo",
        )
    )
    decisions.append(
        Decision(
            key="private.extra",
            what="names that must never reach a published repo and are not directories here",
            current=", ".join(cfg.private_extra) or "(empty)",
            suggest="any employer with no clone on this machine, work email domains, ticket prefixes",
            cost="an employer with no directory to derive from is invisible to `scan` until listed",
        )
    )
    return decisions


def cmd_install(args: argparse.Namespace) -> int:
    if args.explain:
        return explain_install(load_config())
    return run_install(args)


def explain_install(cfg: Config) -> int:
    """What `install` will do, and what only the user can settle. Writes nothing."""
    print("install would:")
    for verb, target, note in (
        ("write" if not cfg.path.is_file() else "keep", cfg.path, ""),
        ("create" if not cfg.store.is_dir() else "keep", cfg.store, " (git repository, no remote)"),
        ("create" if not cfg.unscoped.is_dir() else "keep", cfg.unscoped, ""),
    ):
        print(f"  {verb:<7}{target}{note}")
    print("  nothing else — it never edits a value you have already set")

    decisions = install_decisions(cfg)
    print(f"\n{len(decisions)} decision(s) — put each to the user, then record it with `config set`:")
    for decision in decisions:
        print(f"\ndecision: {decision.key}")
        print(f"  what:    {decision.what}")
        print(f"  current: {decision.current}")
        print(f"  suggest: {decision.suggest}")
        print(f"  cost:    {decision.cost}")
    print("\nnothing was written. Run `install` once the decisions above are recorded.")
    if any(key.startswith("roots.") for key in (d.key for d in decisions)):
        print("Root names above that are not under a public root are not yours to disclose.")
    return 0


def run_install(args: argparse.Namespace) -> int:
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


def store_problems(cfg: Config) -> list[str]:
    """What is wrong with the store, checked every time rather than only at setup.

    `install` reported these once and never again, so a store that lost its git identity afterwards
    stayed broken silently until `archive` returned nothing and looked like an empty history.
    """
    found: list[str] = []
    if not cfg.path.is_file():
        found.append(f"no config at {cfg.path} — run: plans.py install")
    if not cfg.store.is_dir():
        found.append(f"the store {cfg.store} does not exist — run: plans.py install")
        return found
    if not is_git_repo(cfg.store):
        found.append("the store is not a git repository, so `archive` can retrieve nothing there — plans.py install")
    elif not git(["config", "user.email"], cfg.store):
        found.append("the store has no git identity and cannot commit — git -C <store> config user.name/user.email")
    remotes = git(["remote"], cfg.store)
    if remotes:
        found.append(f"the store has remote(s) {remotes.split()} — one personal remote holding several clients'")
    if not os.environ.get("PLANS_HOME"):
        found.append(f"PLANS_HOME is unset; {cfg.store} is in use by default. Export it so the machine agrees")
    if not session_is_anchored(cfg):
        found.append(
            "no session anchor: the cross-repo guard is falling back to cwd, which cannot detect a "
            "drifted directory. Export PLAN_DOCS_SESSION_REPO=<repo> at session start to fix it"
        )
    return found


def cmd_doctor(args: argparse.Namespace) -> int:
    """Where plans live, which repos are enrolled, how many there are, and what is broken.

    Deliberately not called `status`: `set-status` already exists and `status:` is a plan's own
    frontmatter field, so `plans.py status` would read as a question about one plan.
    """
    cfg = load_config()
    entries = family_plans(cfg)
    counts: dict[str, int] = {}
    for rel, _ in entries:
        counts[rel] = counts.get(rel, 0) + 1

    # Aggregated per root, not per repo. Routing is a per-root decision, so the root is the unit
    # that answers "what is enrolled" — and a per-repo listing on this author's machine was 71 rows
    # naming every employer and client repo on it, which is a listing this skill exists to keep from
    # being produced casually. A repo is named below only when it actually holds plans.
    roots: dict[str, list[str]] = {}
    for rel in repo_paths(cfg):
        roots.setdefault(rel.split("/")[0], []).append(rel)
    holding = sorted(((rel, counts[rel]) for rel in counts if rel != UNSCOPED_DIR and counts[rel]), key=lambda p: -p[1])
    unrouted = [rel for rel, _ in holding if _match_rule(cfg, rel)[1] == "no rule"]

    if args.json:
        payload = {
            "config": str(cfg.path),
            "exists": cfg.path.is_file(),
            "projects_root": str(cfg.projects_root),
            "store": str(cfg.store),
            "store_source": cfg.store_source,
            "unscoped": str(cfg.unscoped),
            "idea_limit": cfg.idea_limit,
            "roots": [
                {
                    "root": name,
                    "rule": (rule.describe() if (rule := _match_rule(cfg, f"{name}/x")[0]) else "(no rule — asks)"),
                    "source": _match_rule(cfg, f"{name}/x")[1],
                    "repos": len(members),
                }
                for name, members in sorted(roots.items())
            ],
            "holding_plans": [{"repo": rel, "plans": n} for rel, n in holding],
            "statuses": dict(Counter(plan.group for _, plan in entries)),
            "problems": store_problems(cfg) + [f"{rel} holds plans but no rule routes it" for rel in unrouted],
        }
        print(json.dumps(payload, indent=2))
        return 0

    _print_doctor(cfg, entries, roots, counts, holding, unrouted)
    return 0


def _print_doctor(
    cfg: Config,
    entries: list[tuple[str, PlanFile]],
    roots: dict[str, list[str]],
    counts: dict[str, int],
    holding: list[tuple[str, int]],
    unrouted: list[str],
) -> None:
    anchor, source = session_anchor(cfg)
    print(f"session repo:  {anchor or '(not in a git repository)'}  [{source}]")
    print(f"config:        {cfg.path}{'' if cfg.path.is_file() else ' (does not exist)'}")
    print(f"projects_root: {cfg.projects_root}")
    print(f"store:         {cfg.store} (from {cfg.store_source})")
    print(f"unscoped:      {cfg.unscoped}")
    print(f"idea_limit:    {cfg.idea_limit}")

    print(f"\nenrolled ({len(roots)} root(s), {sum(len(m) for m in roots.values())} repo(s))")
    width = max((len(name) for name in roots), default=0)
    for name, members in sorted(roots.items()):
        rule, source = _match_rule(cfg, f"{name}/x")
        described = rule.describe() if rule else "(no rule — asks)"
        with_plans = sum(1 for rel in members if counts.get(rel))
        print(f"  {name.ljust(width)}  {described:<24} {source:<22} {len(members):>3} repo(s), {with_plans} with plans")

    if holding:
        print(f"\nholding plans ({len(holding)})")
        width = max(len(rel) for rel, _ in holding)
        for rel, count in holding:
            print(f"  {rel.ljust(width)}  {count} plan(s)")

    statuses = Counter(plan.group for _, plan in entries)
    tally = "  ".join(f"{statuses[name]} {name}" for name in (*STATUS_ORDER, "unknown") if statuses[name])
    tags = Counter(name for _, plan in entries for name in plan.tags.elements())
    print(f"\ntally ({len(entries)} plan(s))")
    print(f"  {tally or '(none)'}")
    if tags:
        print("  " + "  ".join(f"{tags[name]} {name}" for name in TAG_NAMES if tags[name]))

    problems = store_problems(cfg) + [f"{rel} holds plans but no rule routes it" for rel in unrouted]
    print(f"\nproblems ({len(problems)})")
    for problem in problems:
        print(f"  - {problem}")
    if not problems:
        print("  (none)")

    public = set(cfg.public_root_names())
    if any(name not in public for name in roots):
        print("\nRoot and repo names above that are not under a public root are not yours to disclose —")
        print("this is for setting the machine up, never for pasting into a repo you publish.")


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


def split_config_key(key: str) -> tuple[str, str]:
    """`view.idea_limit` -> ("view", "idea_limit"); `roots.github.com-personal` -> ("roots", rest).

    Split on the first dot only, and only when what precedes it is a known table: a repo key is a
    path full of dots, and naively splitting on every dot turns one entry into a nested table.
    """
    table, _, rest = key.partition(".")
    if rest and table in CONFIG_TABLES:
        return table, rest
    return "", key


def render_toml_value(raw: str) -> str:
    """Encode a CLI string as a TOML value, letting TOML itself decide whether it already is one.

    `10` stays an integer, `["a", "b"]` an array, `{ mode = "both" }` an inline table — while a bare
    `store` or `~/plans`, which is not valid TOML on its own, becomes the string it obviously means.
    No serializer of our own, and no way for the two to disagree.
    """
    try:
        tomllib.loads(f"v = {raw}")
    except tomllib.TOMLDecodeError:
        return json.dumps(raw)
    return raw


def render_toml_key(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else json.dumps(name)


def table_span(lines: list[str], table: str) -> tuple[int, int] | None:
    """The line range a table's entries live in, exclusive of its header. None if it has none."""
    if not table:
        end = next((i for i, line in enumerate(lines) if line.lstrip().startswith("[")), len(lines))
        return 0, end
    header = f"[{table}]"
    start = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    return start + 1, end


def set_config_value(path: Path, key: str, value: str) -> str:
    """Write one key, preserving every comment in the file.

    Surgical line editing rather than a read-modify-serialize round trip, generalising what
    `describe` has always done. The skeleton's comments carry the reasoning for every key, and the
    rule that routing is configuration rather than a per-session judgement call rests on them being
    readable — a hand-rolled serializer would drop all of them, and `tomllib` cannot write at all.
    A commented-out example is replaced in place, which leaves the explanation above it attached to
    the value it explains.
    """
    table, name = split_config_key(key)
    entry = f"{render_toml_key(name)} = {render_toml_value(value)}"
    lines = path.read_text(encoding="utf-8").splitlines()

    span = table_span(lines, table)
    if span is None:
        lines += ["", f"[{table}]", entry]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "added"

    start, end = span
    pattern = re.compile(rf"^(\s*)(#\s*)?{re.escape(render_toml_key(name))}\s*=")
    live = [i for i in range(start, end) if pattern.match(lines[i]) and not lines[i].lstrip().startswith("#")]
    commented = [i for i in range(start, end) if pattern.match(lines[i])]
    if live:
        lines[live[0]] = entry
        action = "updated"
    elif commented:
        lines[commented[0]] = entry
        action = "set"
    else:
        insert = end
        while insert > start and not lines[insert - 1].strip():
            insert -= 1
        lines.insert(insert, entry)
        action = "added"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return action


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
    if args.action == "set":
        if args.key is None or args.value is None:
            raise PlanError("config set needs a key and a value, e.g. config set view.idea_limit 20")
        if not path.exists():
            raise PlanError(f"no config at {path} — run: plans.py install")
        original = path.read_text(encoding="utf-8")
        action = set_config_value(path, args.key, args.value)
        try:
            # Re-read so a value the config's own schema rejects fails here, next to the change,
            # rather than on some later command that has nothing to do with it. Restore first: a
            # rejected value left on disk breaks every subsequent command, which is a worse failure
            # than the one being reported.
            load_config()
        except PlanError:
            path.write_text(original, encoding="utf-8")
            raise
        print(f"{action}:  {args.key}")
        print(f"config:  {path}")
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
    new.add_argument(
        "--for",
        dest="for_repo",
        metavar="REPO",
        help="file against another repo (path, or path under projects_root) without touching its tree",
    )
    new.add_argument("--unscoped", action="store_true", help="an idea with no repo yet; needs no repo at all")
    new.set_defaults(func=cmd_new)

    listing = add("list", "what is open — this repo by default, every repo with --scope family")
    listing.add_argument("--scope", choices=SCOPES, default="auto", help="breadth (default: auto)")
    listing.add_argument("--status", help="only plans whose status starts with this")
    listing.add_argument("--tag", choices=TAG_NAMES, help="only plans carrying this open tag")
    listing.add_argument("--stale", type=int, metavar="DAYS", help="only plans not updated in this many days")
    listing.add_argument("--since", type=iso_date, metavar="YYYY-MM-DD", help="only plans updated on or after this")
    listing.add_argument("--limit", type=int, help="cap the idea tier (0 = no cap; default: config)")
    listing.add_argument("--all", action="store_true", help="include landed, abandoned and superseded")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_list)

    tags = add("tags", "anchored search for the five plan-docs tags")
    tags.add_argument("--tag", choices=TAG_NAMES, help="one tag (default: all five)")
    tags.add_argument("--file", help="one plan, by path or bare filename (default: all)")
    tags.add_argument("--json", action="store_true")
    tags.set_defaults(func=cmd_tags)

    status = add("set-status", "rewrite a plan's status and updated date, running the gate first")
    status.add_argument("file", help="plan path or bare filename")
    status.add_argument(
        "status", help="idea | planned | in-progress | blocked on … | landed | abandoned | superseded by …"
    )
    status.add_argument("--force", action="store_true", help="write the status even if its gate fails")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_set_status)

    absorb = add("absorb", "take plans filed for this repo out of the store into its own plans/")
    absorb.add_argument("--apply", action="store_true", help="actually move them (default: report only)")
    absorb.add_argument("--only", nargs="*", default=[], metavar="FILE", help="absorb just these filenames")
    absorb.add_argument("--verbose", action="store_true", help="say so when there is nothing to absorb")
    absorb.add_argument("--json", action="store_true")
    absorb.set_defaults(func=cmd_absorb)

    move = add("move", "move a plan between the repo and the store")
    move.add_argument("file", help="plan path or bare filename")
    move.add_argument("--to", choices=("repo", "store"), required=True)
    move.set_defaults(func=cmd_move)

    refs = add("refs", "inbound references to a plan, across the repo and the store")
    refs.add_argument("file", help="plan path or bare filename")
    refs.add_argument("--json", action="store_true")
    refs.set_defaults(func=cmd_refs)

    archive = add("archive", "retired plans, read back out of git history")
    archive.add_argument("--search", help="only plans whose content ever contained this phrase")
    archive.add_argument("--file", help="one plan's whole lifecycle: every commit that touched it")
    archive.add_argument("--show", metavar="FILE", help="print a retired plan's final content")
    archive.add_argument("--all", action="store_true", help="every repo on the machine, plus the whole store")
    archive.add_argument("--limit", type=int, default=40, help="how many to list (default: 40)")
    archive.add_argument("--json", action="store_true")
    archive.set_defaults(func=cmd_archive)

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
    install.add_argument(
        "--explain", action="store_true", help="what it would do and what you must decide; writes nothing"
    )
    install.set_defaults(func=cmd_install)

    doctor = add("doctor", "where plans live, which repos are enrolled, the tally, and what is broken")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    uninstall = add("uninstall", "undo install; never deletes plans without being told twice")
    uninstall.add_argument("--keep-config", action="store_true", help="leave the config file in place")
    uninstall.add_argument("--purge-store", action="store_true", help="also delete the store directory")
    uninstall.add_argument("--force", action="store_true", help="allow --purge-store to delete plan files")
    uninstall.set_defaults(func=cmd_uninstall)

    config = add("config", "show, locate, create or edit the routing config")
    config.add_argument("action", choices=("show", "path", "init", "set"), nargs="?", default="show")
    config.add_argument("key", nargs="?", help="set: e.g. default, view.idea_limit, roots.<root>")
    config.add_argument("value", nargs="?", help="set: a TOML literal, or a bare string")
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
