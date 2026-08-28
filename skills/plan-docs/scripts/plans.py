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
    plans.py tags --tag DEFERRED        # the anchored greps, without the anchoring mistakes
    plans.py set-status <file> planned  # runs the promotion gate first
    plans.py move <file> --to store     # a repo switching where it keeps plans
    plans.py refs <file>                # inbound references, before a retirement
    plans.py init-store                 # create the store as a local git repo, no remote

Exit codes: 0 ok, 1 error, 2 argparse usage, 3 needs-decision — no rule matched the repo, so the
agent must ask the user rather than pick a side.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

NEEDS_DECISION = 3

MODES = ("repo", "store", "both")
TAG_NAMES = ("NEEDS CLARIFICATION", "DECISION", "PITFALL", "DEFERRED", "UNVERIFIED")
# Anchored exactly as SKILL.md specifies: a tag opens its own line, optionally after a list marker.
# An unanchored search matches every prose *mention* of a tag and reports a false backlog.
TAG_RE = re.compile(rf"^\s*[-*]?\s*\[({'|'.join(TAG_NAMES)}): ", re.MULTILINE)
TOPIC_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Grouping order for `list`: what needs attention first, terminal states last.
STATUS_ORDER = ("in-progress", "blocked", "planned", "idea", "landed", "abandoned", "superseded")

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

[roots]
# "github.com-personal" = "repo"

[repos]
# A repo that has stopped storing plans inside itself: writes go to the store, the plans already
# committed in the repo stay readable.
# "github.com-acme/legacy-api" = { mode = "both", write = "store" }
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
    )


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

    @property
    def group(self) -> str:
        for known in STATUS_ORDER:
            if self.status.startswith(known):
                return known
        return "unknown"


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


def read_plan(path: Path, where: str) -> PlanFile:
    text = path.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    return PlanFile(
        path=path,
        where=where,
        status=fields.get("status", "(no status)"),
        updated=fields.get("updated", ""),
        tags=Counter(match.group(1) for match in TAG_RE.finditer(text)),
    )


def plan_files(routing: Routing) -> list[PlanFile]:
    found: list[PlanFile] = []
    for where, directory in routing.read_dirs():
        if not directory.is_dir():
            continue
        found.extend(read_plan(path, where) for path in sorted(directory.glob("*.md")) if path.name != "README.md")
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
    routing = resolve(args.path, cfg)
    if args.to is None:
        require_ok(routing)
        target = routing.write_dir
        where = routing.rule.write if routing.rule else ""
    else:
        if args.to not in routing.dirs:
            raise PlanError(f"cannot write to {args.to!r} for this repo: {routing.reason or 'no such directory'}")
        target, where = routing.dirs[args.to], args.to

    path = target / f"{today()}-{args.topic}.md"
    if path.exists():
        raise PlanError(f"{path} already exists — update it in place rather than opening a second file")

    lines = ["---", f"status: {args.status}", f"updated: {today()}"]
    if where == "store":
        # The store's directory tree encodes the clone path; the origin URL is the identity that
        # survives the clone being moved or renamed, so that is what the file itself records.
        origin = git(["remote", "get-url", "origin"], routing.repo_root) if routing.repo_root else None
        lines.append(f"repo: {origin or routing.rel}")
    lines += ["---", "", "## Context", "", "## Open questions", "", "## Recommended direction", ""]

    target.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"created: {path}")
    print(f"where:   {where}")
    if where == "store" and not (cfg.store / ".git").is_dir():
        print(f"note:    {cfg.store} is not a git repository yet — plans.py init-store")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    cfg = load_config()
    routing = require_ok(resolve(args.path, cfg))
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

    for where, path in routing.read_dirs():
        print(f"read:    {where:<6} {path}{'' if path.is_dir() else ' (does not exist)'}")
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


def cmd_init_store(args: argparse.Namespace) -> int:
    cfg = load_config()
    _ = args
    cfg.store.mkdir(parents=True, exist_ok=True)
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
        print(f"WARNING:     this store has remote(s) configured: {remotes.split()}")
        print("             a single personal remote holding several clients' material is the")
        print("             outcome this store is designed to avoid — check that this was deliberate")
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
    new.set_defaults(func=cmd_new)

    listing = add("list", "status-grouped index of this repo's plans, with open-tag counts")
    listing.add_argument("--status", help="only plans whose status starts with this")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(func=cmd_list)

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

    config = add("config", "show, locate or create the routing config")
    config.add_argument("action", choices=("show", "path", "init"), nargs="?", default="show")
    config.set_defaults(func=cmd_config)

    store = add("init-store", "create the store as a local git repository with no remote")
    store.set_defaults(func=cmd_init_store)

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
