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

Stdlib only, so it runs by path with no install step. `add` and `provenance` are the only
subcommands that write, and they write only inside `$RESEARCH_HOME`; `name` and `check` are
read-only. Every subcommand takes `--json`.

Exit codes: 0 ok, 1 error (or a finding under `check --strict`), 2 argparse usage.
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

BUCKETS = ("repos", "pages", "docs")
PROVENANCE = "SOURCE.md"
# The fields the store's own README requires. `note` is optional by that same README, and asking for
# it would make every conformant entry a finding.
REQUIRED_FIELDS = ("url", "kind", "ref", "fetched")
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


def render_provenance(url: str, kind: str, ref: str, fetched: str, note: str = "") -> str:
    lines = [f"url: {url}", f"kind: {kind}", f"ref: {ref}", f"fetched: {fetched}"]
    if note:
        lines.append(f"note: {note}")
    return "\n".join(lines) + "\n"


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


def cmd_add(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    root = store_root(args.root)
    name = entry_name(args.url)
    target = root / "repos" / name
    clone = ["git", "clone", "--depth", "1", args.url, str(target)]
    payload: dict[str, Any] = {"url": args.url, "name": name, "path": str(target), "clone": clone}

    if target.exists():
        raise LibraryError(f"{target} already exists — refresh it instead of re-adding it")

    if args.dry_run:
        payload |= {"dry_run": True, "provenance": render_provenance(args.url, "repo-clone", "<ref>", today())}
        if not args.json:
            print(" ".join(clone))
            print(f"\n# {target / PROVENANCE}\n{payload['provenance']}")
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
    body = render_provenance(origin, args.kind, ref, today(), args.note or "")
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
    add.add_argument("--dry-run", action="store_true", help="print the clone and the provenance file, write nothing")

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


COMMANDS = {"name": cmd_name, "add": cmd_add, "provenance": cmd_provenance, "check": cmd_check}


def main(argv: Sequence[str] | None = None, runner: Runner | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = COMMANDS[args.command](args, runner or LiveRunner())
    except LibraryError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=1, default=str))
    if args.command == "check" and args.strict and payload.get("flagged"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
