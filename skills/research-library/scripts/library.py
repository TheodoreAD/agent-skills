#!/usr/bin/env python3
"""The research library's own conventions, as code: entry names, provenance files, and a check.

Adding an entry used to be a paragraph of prose an agent re-derived every time — turn a URL into
`<host>--<owner>--<repo>` by a naming rule with a documented trap in it, clone into that directory,
then hand-write a `SOURCE.md` in a fixed shape. That is a deterministic transformation, and the
failure it produces is silent: an entry that does not match the store's own convention looks
completely normal, and the store is not version-controlled, so nothing else on the machine can see
it.

    library.py name https://github.com/encode/httpx        # github.com--encode--httpx
    library.py name --from-clone $RESEARCH_HOME/repos/github.com--encode--httpx
    library.py add https://github.com/encode/httpx         # clone + SOURCE.md, canonical name
    library.py add https://github.com/encode/httpx --dry-run
    library.py provenance docs/uv.pdf --url <url> --kind site-mirror --ref 2026-09-02
    library.py check --strict                              # every entry against the convention
    library.py size --min 250                              # what the library costs, biggest first
    library.py update                                      # refresh, each entry at its own depth
    library.py deepen <entry> --depth 500                  # more history, recorded as deliberate
    library.py reshallow <entry>                           # back to a depth-1 footprint, disk included

The four commands above `check` are the clone's whole lifecycle, and they are code rather than prose
for a measured reason: returning a deepened clone to its original footprint takes five git commands
in order, one of which (`git tag -d`) appears in no published guide and without which the other four
reclaim nothing while reporting success. See `reshallow` for the numbers.

Stdlib only, so it runs by path with no install step. `add`, `provenance`, `update`, `deepen` and
`reshallow` write, and only inside `$RESEARCH_HOME`; `name`, `check` and `size` are read-only. Every
subcommand takes `--json`.

Exit codes: 0 ok, 1 error (or a finding under `check --strict`), 2 argparse usage, 3 needs-decision
— `add` found a repo the host reports as large, so the user chooses rather than the script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

NEEDS_DECISION = 3

MB = 1024 * 1024

# Above this, an entry is worth a decision rather than a default — before it is cloned, and when a
# report is asked for. Measured 2026-09-07 over a real 71-entry, 4.8 GB library: three entries sit
# above 250 MB and hold 43% of the whole store, while a 100 MB line names fourteen and reads as a
# list of ordinary repos. A default, not a rule: `--min` moves it and `--min 0` prints everything.
PROBLEMATIC_MB = 250

BUCKETS = ("repos", "pages", "docs")
PROVENANCE = "SOURCE.md"
# The fields the store's own README requires. `note` is optional by that same README, and asking for
# it would make every conformant entry a finding. `depth` is optional for the same reason and carries
# *intent*: an entry whose history was deepened on purpose says so here, so `update` refreshes it
# without truncating it back. Absent means "nobody has said", which `update` treats as a question
# rather than as permission — see `refresh_plan`.
REQUIRED_FIELDS = ("url", "kind", "ref", "fetched")
DEPTH_FIELD = "depth"
FULL_DEPTH = "full"
KINDS = ("repo-clone", "llms-txt-mirror", "site-mirror")
# The branch a single-branch refspec tracks. `git clone --depth 1` implies `--single-branch`, so
# `+refs/heads/main:refs/remotes/origin/main` is what a *correct* entry looks like here — not a trap.
#
# Measured 2026-09-02 on the real library: a rule that flagged every non-wildcard refspec reported 49
# of 52 entries, including every one cloned exactly as the skill instructs. The documented trap is
# narrower — a clone made with an explicit `--branch <tag>`, which leaves HEAD detached and a refspec
# naming something that is not a moving branch, so `git fetch origin` re-fetches the same pinned ref
# forever and a refresh reports "up to date" on an entry years stale.
SINGLE_BRANCH_REFSPEC = re.compile(r"^\+?refs/heads/(?P<branch>[^:*]+):refs/remotes/origin/(?P=branch)$")
WILDCARD_REFSPEC = re.compile(r"^\+?refs/heads/\*:refs/remotes/origin/\*$")

# scp-style `git@host:owner/repo.git`. The host must carry a dot and the path must not start with
# a slash, or `ftp://host/owner/repo` parses as host `ftp` with a path of `//host/owner/repo` and
# yields a plausible, wrong entry name instead of an error.
SCP_URL = re.compile(r"^(?:(?P<user>[\w.-]+)@)?(?P<host>[\w-]+(?:\.[\w-]+)+):(?P<path>[\w.~-][\w./~-]*)$")
SCHEME_URL = re.compile(r"^(?:git\+)?(?P<scheme>https?|ssh|git)://(?:[\w.-]+(?::[^@]*)?@)?(?P<rest>.+)$")


class LibraryError(Exception):
    """Anything the caller can fix by passing a different argument."""


@dataclass(frozen=True)
class Ran:
    argv: tuple[str, ...]
    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0


class Runner(Protocol):
    """Every git call, behind one seam, so the naming and checking logic is testable with none."""

    def __call__(self, argv: Sequence[str], cwd: Path | None = None) -> Ran: ...


class LiveRunner:
    def __init__(self, timeout: float = 300.0) -> None:
        self.timeout = timeout

    def __call__(self, argv: Sequence[str], cwd: Path | None = None) -> Ran:
        args = [str(a) for a in argv]
        try:
            proc = subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            return Ran(tuple(args), 127, "", f"{args[0]}: not found")
        except subprocess.TimeoutExpired:
            return Ran(tuple(args), 124, "", f"timed out after {self.timeout:.0f}s")
        return Ran(tuple(args), proc.returncode, proc.stdout, proc.stderr)


# --------------------------------------------------------------------------------------------
# the store


def store_root(explicit: str | None = None) -> Path:
    """`$RESEARCH_HOME`, or the documented default — and never a guess beyond those two.

    The skill's own rule: if the library does not exist, say so and offer to create it rather than
    silently falling back to fetching from the web. So a missing store is an error here, not a
    directory this script creates on the way past.
    """
    raw = explicit or os.environ.get("RESEARCH_HOME") or str(Path.home() / "research")
    root = Path(raw).expanduser()
    if not root.is_dir():
        raise LibraryError(f"no research library at {root} — set RESEARCH_HOME, or create it deliberately")
    return root


# --------------------------------------------------------------------------------------------
# naming


def entry_name(url: str) -> str:
    """`<host>--<owner>--<repo>`, for every host, with no special case for the popular one.

    Handles the three spellings a remote actually arrives in — `https://host/owner/repo(.git)`,
    the scp-style `git@host:owner/repo.git`, and `ssh://git@host/owner/repo` — plus a `git+` prefix,
    because that is how a dependency URL is written and it is the form most likely to be pasted.

    A nested group (GitLab subgroups) keeps every segment: `gitlab.com/group/sub/proj` becomes
    `gitlab.com--group--sub--proj`. Dropping the middle segments would collide two projects whose
    names match under different subgroups, and a silent collision in a store nothing version-controls
    is the worst failure this convention has.

    Case is preserved below the host, because the store already holds `gitlab.gnome.org--GNOME--…`
    and a rename would orphan every `AGENTS.md` pointing at it. The host itself is lowercased, since
    DNS is case-insensitive and two spellings of one host are the same host.
    """
    raw = url.strip().rstrip("/")
    if not raw:
        raise LibraryError("empty URL")

    scheme = SCHEME_URL.match(raw)
    if scheme:
        rest = scheme.group("rest")
        host, _, path = rest.partition("/")
    else:
        scp = SCP_URL.match(raw)
        if not scp:
            raise LibraryError(f"cannot read a host and path out of {url!r}")
        host, path = scp.group("host"), scp.group("path")

    host = host.split("@")[-1].split(":")[0].lower()
    host = host.removeprefix("www.")
    path = path.strip("/")
    path = path.removesuffix(".git")
    segments = [s for s in path.split("/") if s and s != "~"]
    if not host or not segments:
        raise LibraryError(f"cannot read a host and path out of {url!r}")
    return "--".join([host, *segments])


def clone_origin(runner: Runner, path: Path) -> str | None:
    ran = runner(["git", "-C", str(path), "remote", "get-url", "origin"])
    return ran.out.strip() if ran.ok and ran.out.strip() else None


def canonical_name(runner: Runner, path: Path) -> str | None:
    """The name an existing clone *should* have, read from its own `origin` rather than from the URL
    somebody typed. Self-hosted instances look like the popular host and are not it, and a redirect
    can move a repo to a new owner without the URL you cloned from ever saying so."""
    origin = clone_origin(runner, path)
    return entry_name(origin) if origin else None


# --------------------------------------------------------------------------------------------
# provenance files


def provenance_path(entry: Path) -> Path:
    """`SOURCE.md` inside a directory entry, `<file>.source.md` beside a flat one."""
    return entry / PROVENANCE if entry.is_dir() else entry.with_name(entry.name + ".source.md")


def render_provenance(url: str, kind: str, ref: str, fetched: str, note: str = "", depth: str = "") -> str:
    lines = [f"url: {url}", f"kind: {kind}", f"ref: {ref}", f"fetched: {fetched}"]
    if depth:
        lines.append(f"{DEPTH_FIELD}: {depth}")
    if note:
        lines.append(f"note: {note}")
    return "\n".join(lines) + "\n"


def set_provenance_field(entry: Path, key: str, value: str) -> None:
    """Rewrite one field in an entry's provenance, leaving every other line where it was.

    A line edit rather than parse-and-re-render: the file is hand-editable by design and its `note`
    can be prose the author wrote, so round-tripping it through the renderer would quietly reflow or
    drop anything the parser does not model.
    """
    path = provenance_path(entry)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
    replacement = f"{key}: {value}"
    for index, line in enumerate(lines):
        name, sep, _ = line.partition(":")
        if sep and name.strip().lower() == key:
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def recorded_depth(entry: Path) -> str:
    """What the entry says its history is *meant* to be, or "" when nobody has said."""
    path = provenance_path(entry)
    if not path.is_file():
        return ""
    return parse_provenance(path.read_text(encoding="utf-8", errors="replace")).get(DEPTH_FIELD, "")


def parse_provenance(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith(" "):
            fields[key.strip().lower()] = value.strip()
    return fields


def today() -> str:
    return datetime.now(UTC).date().isoformat()


# --------------------------------------------------------------------------------------------
# add


def reported_size_mb(runner: Runner, url: str) -> int | None:
    """What the host says the repository weighs, in MB, or None when nothing can say.

    GitHub's API only, through `gh`, which this skill already depends on for package health. It
    reports the **packed** repository, so it is a trigger and never a number: measured 2026-09-07
    against five real entries at depth 1, on-disk cost ran from 0.23x the reported size (`cpython`,
    851 MB reported, 192 MB on disk) to 1.32x (`Roo-Code`, 359 reported, 473 on disk). A 5.7x spread,
    and not even an upper bound — so the warning below says a repo is large and refuses to predict by
    how much. Quoting a figure would have been wrong by 4x in the reassuring direction on `cpython`.
    """
    name = entry_name(url)
    host, _, rest = name.partition("--")
    owner, _, repo = rest.partition("--")
    if host != "github.com" or not owner or not repo or "--" in repo:
        return None
    ran = runner(["gh", "api", f"repos/{owner}/{repo}", "--jq", ".size"])
    return round(int(ran.out.strip()) / 1024) if ran.ok and ran.out.strip().isdigit() else None


def cmd_add(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    root = store_root(args.root)
    name = entry_name(args.url)
    target = root / "repos" / name
    depth = [] if args.full else ["--depth", str(args.depth)]
    clone = ["git", "clone", *depth, args.url, str(target)]
    payload: dict[str, Any] = {"url": args.url, "name": name, "path": str(target), "clone": clone}

    if target.exists():
        raise LibraryError(f"{target} already exists — refresh it instead of re-adding it")

    if args.dry_run:
        # Before the size probe, deliberately: a dry run runs nothing at all, which is a contract
        # this file's tests assert rather than assume.
        payload |= {"dry_run": True, "provenance": render_provenance(args.url, "repo-clone", "<ref>", today())}
        if not args.json:
            print(" ".join(clone))
            print(f"\n# {target / PROVENANCE}\n{payload['provenance']}")
        return payload

    reported = None if args.yes else reported_size_mb(runner, args.url)
    payload["reported_mb"] = reported
    if reported is not None and reported >= args.min:
        # Exit 3 rather than prompting: this runs inside an agent's Bash call, where an interactive
        # prompt hangs with nothing to type into. The decision goes back to the user with the number
        # that prompted it, which is the shape `plan-docs` uses for a repo no rule routes.
        print(
            f"{name}: the host reports {reported} MB packed, at or above the {args.min} MB line.\n"
            "On-disk cost has run between 0.2x and 1.3x of that figure across this library, so this\n"
            "may be large and the number is not a prediction. Clone it with --yes, or narrow the source.",
            file=sys.stderr,
        )
        payload["needs_decision"] = True
        return payload

    ran = runner(clone)
    if not ran.ok:
        raise LibraryError(f"clone failed ({ran.code}): {ran.err.strip() or ran.out.strip()}")

    # The name is re-derived from the clone's own remote, not from the URL that was passed. A
    # redirect (a repo renamed or transferred) resolves silently, and the entry would otherwise carry
    # a name nothing else on the machine agrees with.
    real = canonical_name(runner, target) or name
    if real != name:
        (root / "repos" / real).parent.mkdir(parents=True, exist_ok=True)
        target.rename(root / "repos" / real)
        target = root / "repos" / real
        payload |= {"renamed_from": name, "name": real, "path": str(target)}

    origin = clone_origin(runner, target) or args.url
    ref = args.ref or head_ref(runner, target)
    # Recorded at clone time when it is anything but the default, so `update` never has to guess
    # whether a deep entry was meant — the guess it would otherwise make is the one that truncates.
    kept = FULL_DEPTH if args.full else (str(args.depth) if args.depth != 1 else "")
    body = render_provenance(origin, args.kind, ref, today(), args.note or "", depth=kept)
    (target / PROVENANCE).write_text(body, encoding="utf-8")
    payload |= {"provenance": body, "ref": ref, "origin": origin}

    if not args.json:
        print(f"added {target}")
        if payload.get("renamed_from"):
            print(f"  renamed from {payload['renamed_from']} — the remote resolves to a different name")
        print(f"  {target / PROVENANCE}:")
        for line in body.splitlines():
            print(f"    {line}")
    return payload


def head_ref(runner: Runner, path: Path) -> str:
    """`<branch>@<sha>` for a clone — the `ref` field's documented content for a repo entry."""
    branch = runner(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"]).out.strip()
    sha = runner(["git", "-C", str(path), "rev-parse", "--short", "HEAD"]).out.strip()
    return f"{branch}@{sha}" if branch and sha else (branch or sha or "unknown")


def cmd_provenance(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """The metadata file for an entry that is not a git clone — a mirrored page, a downloaded PDF.

    Deliberately not a fetcher: mirroring a docs site is a judgement about what to fetch and how
    deep, and nothing about it is deterministic. Writing its provenance file *is* deterministic, and
    it is the half that gets skipped.
    """
    root = store_root(args.root)
    entry = Path(args.entry)
    if not entry.is_absolute():
        entry = root / entry
    if not entry.exists():
        raise LibraryError(f"{entry} does not exist — add the entry first, then record where it came from")
    if args.kind not in KINDS:
        raise LibraryError(f"kind must be one of {', '.join(KINDS)}")

    path = provenance_path(entry)
    body = render_provenance(args.url, args.kind, args.ref or today(), today(), args.note or "")
    if not args.dry_run:
        path.write_text(body, encoding="utf-8")
    if not args.json:
        print(f"{'would write' if args.dry_run else 'wrote'} {path}")
        for line in body.splitlines():
            print(f"    {line}")
    return {"path": str(path), "provenance": body, "dry_run": bool(args.dry_run)}


# --------------------------------------------------------------------------------------------
# size, and the clone lifecycle
#
# Every sequence below was measured on 2026-09-07 rather than reasoned about, and two of the
# measurements contradict what the obvious version of this code would have done. They are recorded
# at the function that depends on them.


def tree_size(path: Path) -> int:
    """Bytes under a directory, following no symlink.

    `du` is deliberately not shelled out to: it is absent on Windows and the runner seam in this file
    is for git. The difference is that this counts apparent size rather than allocated blocks, so it
    reads a little under `du` on a filesystem with large blocks — consistent across entries, which is
    all a ranking needs.
    """
    total = 0
    stack = [path]
    while stack:
        try:
            with os.scandir(stack.pop()) as items:
                for item in items:
                    if item.is_symlink():
                        continue
                    if item.is_dir(follow_symlinks=False):
                        stack.append(Path(item.path))
                    else:
                        total += item.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    return total


def commit_count(runner: Runner, entry: Path) -> int | None:
    """How many commits this clone actually holds. None when it is not a readable git repo."""
    ran = runner(["git", "-C", str(entry), "rev-list", "--count", "HEAD"])
    return int(ran.out.strip()) if ran.ok and ran.out.strip().isdigit() else None


@dataclass(frozen=True)
class EntrySize:
    """One entry's cost, split the way the remedies split.

    `git` and `worktree` are separate because they have different fixes and the ratio says which one
    applies: a big `.git` at one commit is large blobs (nothing to do but not clone it), while a big
    working tree at one commit is vendored directories (a sparse checkout, decided per entry).
    Measured on the worst entry in a real library: 940 MB total at ONE commit, of which 675 MB was a
    single vendored `deps/` directory. Depth was not the problem and re-shallowing would not have
    moved it.
    """

    entry: str
    total: int
    git: int
    commits: int | None
    depth: str

    @property
    def worktree(self) -> int:
        return max(self.total - self.git, 0)

    @property
    def deepened(self) -> bool:
        return self.commits is not None and self.commits > 1


def entry_size(runner: Runner, root: Path, entry: Path) -> EntrySize:
    git_dir = entry / ".git"
    return EntrySize(
        entry=entry.relative_to(root).as_posix(),
        total=tree_size(entry) if entry.is_dir() else entry.stat().st_size,
        git=tree_size(git_dir) if git_dir.is_dir() else 0,
        commits=commit_count(runner, entry) if git_dir.exists() else None,
        depth=recorded_depth(entry),
    )


def mb(value: int) -> int:
    return round(value / MB)


def cmd_size(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """What the library costs, biggest first, with a minimum worth reporting on."""
    root = store_root(args.root)
    rows = sorted((entry_size(runner, root, e) for e in iter_entries(root)), key=lambda r: -r.total)
    floor = args.min * MB
    over = [row for row in rows if row.total >= floor]
    total = sum(row.total for row in rows)
    payload = {
        "root": str(root),
        "entries": len(rows),
        "total_mb": mb(total),
        "min_mb": args.min,
        "over_min": [
            {
                "entry": row.entry,
                "total_mb": mb(row.total),
                "git_mb": mb(row.git),
                "worktree_mb": mb(row.worktree),
                "commits": row.commits,
                "depth": row.depth,
            }
            for row in over
        ],
        "over_min_mb": mb(sum(row.total for row in over)),
    }
    if args.json:
        return payload
    print(f"{root}: {len(rows)} entries, {mb(total)} MB")
    if not over:
        print(f"  nothing at or above {args.min} MB")
        return payload
    held = sum(row.total for row in over)
    share = round(100 * held / total) if total else 0
    print(f"  {len(over)} at or above {args.min} MB, holding {mb(held)} MB ({share}% of the store)")
    width = max(len(row.entry) for row in over)
    for row in over:
        note = f"  {row.commits} commits" if row.deepened else ""
        note += f"  depth: {row.depth}" if row.depth else ""
        print(f"  {row.entry.ljust(width)}  {mb(row.total):>5} MB  (.git {mb(row.git)}, tree {mb(row.worktree)}){note}")
    return payload


def repo_entry(root: Path, name: str) -> Path:
    """One entry under `repos/`, named or given as a path, checked to be a clone."""
    entry = Path(name).expanduser()
    if not entry.is_absolute():
        entry = root / "repos" / entry.name if entry.parent.name in ("", ".") else root / entry
    if not (entry / ".git").exists():
        raise LibraryError(f"{entry} is not a git clone")
    return entry


def head_branch(runner: Runner, entry: Path) -> str:
    ran = runner(["git", "-C", str(entry), "symbolic-ref", "-q", "--short", "HEAD"])
    return ran.out.strip() if ran.ok else ""


def reshallow(runner: Runner, entry: Path) -> list[list[str]]:
    """Return a clone to a depth-1 footprint, and actually reclaim the disk.

    **The tag deletion is the step that makes the other four worth running**, and it appears in no
    reference material. Measured 2026-09-07 on `encode/httpx`, `.git` in KB: a fresh `--depth 1`
    clone is 2,492; deepened by 400 commits and then re-shallowed with `fetch --depth 1` and
    `reset --hard` it reports one commit again while the disk does not move at all; adding
    `reflog expire`, `gc --prune=now`, `repack -a -d`, `prune` and `gc --aggressive` gets it to
    4,852 and no further. Deepening brings the repo's tags, each pinning a commit deep in history,
    so every object below stays reachable and no `gc` will ever drop it. Delete the tags and the
    same clone lands at 2,472 — below where it started.

    Run verbatim, the widely-published sequence leaves a clone permanently 95% larger than a fresh
    one and reports success, which is exactly the kind of silent, five-steps-in-order failure that
    belongs in code rather than in a paragraph somebody follows from memory.
    """
    branch = head_branch(runner, entry)
    tags = runner(["git", "-C", str(entry), "tag"]).out.split()
    steps: list[list[str]] = [
        ["git", "-C", str(entry), "fetch", "--depth", "1", "origin", *([branch] if branch else [])],
        ["git", "-C", str(entry), "reset", "--hard", "FETCH_HEAD"],
    ]
    if tags:
        steps.append(["git", "-C", str(entry), "tag", "-d", *tags])
    steps += [
        ["git", "-C", str(entry), "reflog", "expire", "--expire=now", "--all"],
        ["git", "-C", str(entry), "gc", "--prune=now", "-q"],
    ]
    return steps


def refresh_plan(runner: Runner, entry: Path) -> tuple[list[list[str]] | None, str]:
    """How to refresh one entry, or why it is being left alone.

    Three cases, and the third is the one that needs saying. A clone at one commit with no recorded
    intent is the ordinary entry: re-shallow it. A clone whose provenance records a `depth` was
    deepened deliberately: fetch without a depth flag, which keeps the graft point where it is and
    still moves the tip. **A clone deeper than one commit with nothing recorded is skipped**, because
    nothing distinguishes a deliberate deepening from an accident and truncating is the answer that
    cannot be undone by reading. Confirmed 2026-09-07 in a real library: exactly one of 71 entries
    was deep, it was deepened on purpose to read a dependency's constraint history, and the loop that
    refreshes every entry with `fetch --depth 1` would have destroyed that silently.
    """
    depth = recorded_depth(entry)
    commits = commit_count(runner, entry)
    if depth and depth != "1":
        # Any value but `1` counts as deliberate, including prose. The real library's one deep entry
        # records a whole sentence here — "deepened to ~436 commits …, not the usual --depth 1" —
        # because the store's convention asks for the divergence *and why*, and a field that only
        # accepted an integer would have read that as unrecorded and truncated it.
        return (
            [
                ["git", "-C", str(entry), "fetch", "origin"],
                ["git", "-C", str(entry), "reset", "--hard", "FETCH_HEAD"],
            ],
            f"depth recorded ({depth[:60]}{'…' if len(depth) > 60 else ''}) — refreshed, not re-shallowed",
        )
    if commits is not None and commits > 1 and not depth:
        return None, (
            f"{commits} commits but no depth recorded — skipped rather than truncated. "
            f"Record it (`deepen --record {depth or commits}`) or flatten it (`reshallow`)"
        )
    return reshallow(runner, entry), "re-shallowed to depth 1"


def repo_entries(root: Path) -> list[Path]:
    return [e for e in iter_entries(root) if e.parent.name == "repos" and (e / ".git").exists()]


def cmd_update(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """Refresh clones to their remote's latest, preserving whatever depth each one is meant to have."""
    root = store_root(args.root)
    chosen = [repo_entry(root, name) for name in args.entry] if args.entry else repo_entries(root)
    results = [update_one(runner, root, entry, dry_run=args.dry_run) for entry in chosen]

    payload = {"root": str(root), "updated": results}
    if args.json:
        return payload
    for record in results:
        _print_update(record)
    skipped = sum(1 for r in results if r.get("skipped"))
    print(f"{len(results)} entr(ies), {skipped} skipped")
    return payload


def update_one(runner: Runner, root: Path, entry: Path, *, dry_run: bool) -> dict[str, Any]:
    """One entry refreshed at whatever depth it is meant to have, with what it cost."""
    # Not measured under --dry-run: walking every entry costs a full pass over the store, and a run
    # that changes nothing has no delta to report anyway.
    before = 0 if dry_run else tree_size(entry)
    steps, why = refresh_plan(runner, entry)
    record: dict[str, Any] = {"entry": entry.relative_to(root).as_posix(), "action": why}
    if steps is None:
        record["skipped"] = True
        return record
    if dry_run:
        record["steps"] = [" ".join(step) for step in steps]
        return record
    for step in steps:
        ran = runner(step)
        if not ran.ok:
            record["error"] = f"{' '.join(step[3:])}: {ran.err.strip() or ran.code}"
            return record
    after = tree_size(entry)
    record |= {
        "mb_before": mb(before),
        "mb_after": mb(after),
        "mb_delta": mb(after - before),
        "ref": head_ref(runner, entry),
    }
    return record


def _print_update(record: dict[str, Any]) -> None:
    if record.get("skipped"):
        print(f"  SKIPPED {record['entry']}: {record['action']}")
    elif record.get("error"):
        print(f"  FAILED  {record['entry']}: {record['error']}")
    elif "steps" in record:
        print(f"  would   {record['entry']}: {record['action']}")
        for step in record["steps"]:
            print(f"            {step}")
    else:
        delta = record["mb_delta"]
        sign = f"{delta:+d} MB" if delta else "no change"
        print(f"  ok      {record['entry']}: {record['action']}, {record['mb_after']} MB ({sign})")


def cmd_deepen(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """Fetch more history for one entry, and record that it was meant.

    The recording is the point: without it the next `update` cannot tell this from an accident, and
    the safe reading of an accident is to leave it alone forever.
    """
    root = store_root(args.root)
    entry = repo_entry(root, args.entry)
    before = tree_size(entry)
    depth = FULL_DEPTH if args.full else str(args.depth)
    step = (
        ["git", "-C", str(entry), "fetch", "--unshallow"]
        if args.full
        else ["git", "-C", str(entry), "fetch", f"--deepen={args.depth}"]
    )
    payload: dict[str, Any] = {"entry": entry.relative_to(root).as_posix(), "depth": depth, "step": " ".join(step)}
    if args.dry_run:
        payload["dry_run"] = True
        if not args.json:
            print(payload["step"])
        return payload

    ran = runner(step)
    if not ran.ok:
        raise LibraryError(f"deepen failed ({ran.code}): {ran.err.strip() or ran.out.strip()}")
    set_provenance_field(entry, DEPTH_FIELD, depth)
    after = tree_size(entry)
    payload |= {
        "commits": commit_count(runner, entry),
        "mb_before": mb(before),
        "mb_after": mb(after),
        "mb_delta": mb(after - before),
    }
    if not args.json:
        print(f"{payload['entry']}: {payload['commits']} commits, {payload['mb_after']} MB (+{payload['mb_delta']})")
        print(f"  recorded {DEPTH_FIELD}: {depth} — `update` will now refresh it without re-shallowing")
    return payload


def cmd_reshallow(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """Return one entry to a depth-1 footprint, disk included. See `reshallow` for the measurements."""
    root = store_root(args.root)
    entry = repo_entry(root, args.entry)
    if not head_branch(runner, entry) and not args.force:
        raise LibraryError(
            f"{entry.name} has a detached HEAD — it was cloned at a tag or a commit, so its tags may be "
            "the thing being read and this deletes them. Pass --force if the history is genuinely disposable"
        )
    before = tree_size(entry)
    steps = reshallow(runner, entry)
    payload: dict[str, Any] = {"entry": entry.relative_to(root).as_posix(), "steps": [" ".join(s) for s in steps]}
    if args.dry_run:
        payload["dry_run"] = True
        if not args.json:
            for step in payload["steps"]:
                print(" ".join(step) if isinstance(step, list) else step)
        return payload

    for step in steps:
        ran = runner(step)
        if not ran.ok:
            raise LibraryError(f"{' '.join(step[3:])} failed ({ran.code}): {ran.err.strip() or ran.out.strip()}")
    set_provenance_field(entry, DEPTH_FIELD, "1")
    after = tree_size(entry)
    payload |= {"commits": commit_count(runner, entry), "mb_before": mb(before), "mb_after": mb(after)}
    if not args.json:
        print(f"{payload['entry']}: {payload['commits']} commit(s), {mb(before)} MB -> {mb(after)} MB")
    return payload


# --------------------------------------------------------------------------------------------
# check


def iter_entries(root: Path) -> list[Path]:
    """One level below each bucket. The buckets themselves are not entries, and a `README.md` at the
    store's own root is not one either."""
    entries: list[Path] = []
    for bucket in BUCKETS:
        directory = root / bucket
        if not directory.is_dir():
            continue
        entries.extend(
            sorted(p for p in directory.iterdir() if not p.name.startswith(".") and not p.name.endswith(".source.md"))
        )
    return entries


def check_entry(runner: Runner, root: Path, entry: Path, remote: bool = False) -> dict[str, Any]:
    """Every way an entry can silently stop matching the store's own convention."""
    findings: list[str] = []
    record: dict[str, Any] = {"entry": str(entry.relative_to(root)), "findings": findings}

    provenance = provenance_path(entry)
    if not provenance.is_file():
        findings.append(f"no provenance file ({provenance.name})")
    else:
        fields = parse_provenance(provenance.read_text(encoding="utf-8", errors="replace"))
        missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
        if missing:
            findings.append(f"provenance missing: {', '.join(missing)}")
        if fields.get("kind") and fields["kind"] not in KINDS:
            findings.append(f"provenance kind {fields['kind']!r} is not one of {', '.join(KINDS)}")

    if entry.parent.name != "repos":
        return record
    if not (entry / ".git").exists():
        findings.append("under repos/ but not a git clone — a clone that failed partway looks exactly like this")
        return record

    real = canonical_name(runner, entry)
    record["origin"] = clone_origin(runner, entry)
    if real and real != entry.name:
        findings.append(f"name does not match its own origin: is {entry.name}, should be {real}")

    findings.extend(_refresh_findings(runner, entry, remote=remote))
    return record


def _refresh_findings(runner: Runner, entry: Path, remote: bool) -> list[str]:
    """Whether a `git fetch origin` in this clone can ever bring anything new.

    Two answers are free, and the third needs the network and is opt-in:

    - **HEAD detached** — the clone was made at a tag or a commit, so nothing about it moves. This is
      the documented trap's real signature.
    - **the refspec names a branch that is not the one HEAD is on** — a refresh updates a
      remote-tracking ref the working tree never follows.
    - **the tracked branch is not the remote's default**, which only `git ls-remote --symref origin
      HEAD` can say. Off by default because `check` is otherwise local, offline and instant.
    """
    findings: list[str] = []
    refspecs = runner(["git", "-C", str(entry), "config", "--get-all", "remote.origin.fetch"]).out.split()
    head = runner(["git", "-C", str(entry), "symbolic-ref", "-q", "HEAD"])
    branch = head.out.strip().removeprefix("refs/heads/") if head.ok else ""

    if not branch:
        findings.append("HEAD is detached — cloned at a tag or a commit, so no refresh will ever move it")
    tracked = [m.group("branch") for r in refspecs if (m := SINGLE_BRANCH_REFSPEC.match(r))]
    if branch and tracked and branch not in tracked:
        findings.append(f"fetch refspec tracks {', '.join(tracked)} but HEAD is on {branch}")

    if remote and (tracked or branch):
        symref = runner(["git", "-C", str(entry), "ls-remote", "--symref", "origin", "HEAD"])
        match = re.search(r"ref:\s+refs/heads/(\S+)\s+HEAD", symref.out) if symref.ok else None
        default = match.group(1) if match else ""
        if default and default not in (tracked or [branch]):
            findings.append(f"tracks {', '.join(tracked or [branch])} but the remote's default branch is {default}")
        elif not symref.ok:
            findings.append(f"could not read the remote's default branch: {symref.err.strip() or symref.code}")
    if refspecs and not tracked and not any(WILDCARD_REFSPEC.match(r) for r in refspecs):
        findings.append(f"unusual fetch refspec ({' '.join(refspecs)}) — read it before trusting a refresh")
    return findings


def cmd_check(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    root = store_root(args.root)
    records = [check_entry(runner, root, entry, remote=args.remote) for entry in iter_entries(root)]
    flagged = [r for r in records if r["findings"]]
    payload = {"root": str(root), "entries": len(records), "flagged": len(flagged), "records": records}
    if args.json:
        return payload
    print(f"{root}: {len(records)} entries, {len(flagged)} with findings")
    for record in flagged:
        print(f"\n  {record['entry']}")
        for finding in record["findings"]:
            print(f"    - {finding}")
    if not flagged:
        print("  every entry carries its provenance, matches its own remote, and tracks a moving branch")
    return payload


def cmd_name(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    if args.from_clone:
        path = Path(args.from_clone).expanduser()
        name = canonical_name(runner, path)
        if name is None:
            raise LibraryError(f"{path} has no origin remote to read a name from")
        payload = {"name": name, "origin": clone_origin(runner, path), "path": str(path)}
    else:
        if not args.url:
            raise LibraryError("pass a URL, or --from-clone <path>")
        payload = {"name": entry_name(args.url), "url": args.url}
    if not args.json:
        print(payload["name"])
    return payload


# --------------------------------------------------------------------------------------------
# cli


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--root", help="the library root (default: $RESEARCH_HOME, else ~/research)")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    name = subparsers.add_parser("name", parents=[common], help="the entry name a URL maps to")
    name.add_argument("url", nargs="?", help="repo URL in any of the usual spellings")
    name.add_argument("--from-clone", help="read the name from an existing clone's own origin remote")

    add = subparsers.add_parser("add", parents=[common], help="clone a repo into the library and record it")
    add.add_argument("url")
    add.add_argument("--kind", default="repo-clone", choices=KINDS)
    add.add_argument("--ref", help="what to record as ref (default: the cloned branch and short sha)")
    add.add_argument("--note", help="only when non-obvious, per the store's README")
    add.add_argument("--depth", type=int, default=1, help="clone this many commits (default: 1)")
    add.add_argument("--full", action="store_true", help="clone the whole history; recorded as depth: full")
    add.add_argument(
        "--min", type=int, default=PROBLEMATIC_MB, metavar="MB", help="host-reported size that makes this a question"
    )
    add.add_argument("--yes", action="store_true", help="clone without asking the host how big it is")
    add.add_argument("--dry-run", action="store_true", help="print the clone and the provenance file, write nothing")

    size = subparsers.add_parser("size", parents=[common], help="what the library costs, biggest entry first")
    size.add_argument(
        "--min",
        type=int,
        default=PROBLEMATIC_MB,
        metavar="MB",
        help=f"report entries at or above this (default: {PROBLEMATIC_MB}; 0 for all)",
    )

    update = subparsers.add_parser("update", parents=[common], help="refresh clones at their intended depth")
    update.add_argument("entry", nargs="*", help="entry names (default: every clone under repos/)")
    update.add_argument("--dry-run", action="store_true", help="print what each entry would run")

    deepen = subparsers.add_parser("deepen", parents=[common], help="fetch more history for one entry, and record it")
    deepen.add_argument("entry")
    deepen.add_argument("--depth", type=int, default=100, help="commits to add (default: 100)")
    deepen.add_argument("--full", action="store_true", help="unshallow completely")
    deepen.add_argument("--dry-run", action="store_true")

    flatten = subparsers.add_parser("reshallow", parents=[common], help="return one entry to a depth-1 footprint")
    flatten.add_argument("entry")
    flatten.add_argument("--force", action="store_true", help="proceed on a detached HEAD, whose tags may be the point")
    flatten.add_argument("--dry-run", action="store_true")

    prov = subparsers.add_parser("provenance", parents=[common], help="write an entry's provenance file")
    prov.add_argument("entry", help="path to the entry, absolute or relative to the library root")
    prov.add_argument("--url", required=True)
    prov.add_argument("--kind", required=True, choices=KINDS)
    prov.add_argument("--ref", help="branch/tag/commit, or the fetch date for a mirror (default: today)")
    prov.add_argument("--note")
    prov.add_argument("--dry-run", action="store_true")

    check = subparsers.add_parser("check", parents=[common], help="every entry against the store's conventions")
    check.add_argument("--strict", action="store_true", help="exit 1 when any entry has a finding")
    check.add_argument(
        "--remote",
        action="store_true",
        help="also ask each remote for its default branch (network; the only complete refresh check)",
    )
    return parser


COMMANDS = {
    "name": cmd_name,
    "add": cmd_add,
    "provenance": cmd_provenance,
    "check": cmd_check,
    "size": cmd_size,
    "update": cmd_update,
    "deepen": cmd_deepen,
    "reshallow": cmd_reshallow,
}


def main(argv: Sequence[str] | None = None, runner: Runner | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = COMMANDS[args.command](args, runner or LiveRunner())
    except LibraryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=1, default=str))
    if payload.get("needs_decision"):
        return NEEDS_DECISION
    if args.command == "check" and args.strict and payload.get("flagged"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
