#!/usr/bin/env python3
"""A skill's name is a primary key. This is the check nothing else runs.

    names.py check repo-pitch                 # is this name free, before adopting it
    names.py check a b c --json               # several candidates at once
    names.py audit                            # every installed skill: scope clashes, then the registry
    names.py audit --root skills --mine <you> # the names in a source checkout you are authoring
    names.py audit --offline                  # the scope-clash half only, no network

**Why this exists.** Nothing warns you. `vercel-labs/skills` skips a skill whose name it has already
seen — first-seen-wins by traversal order, silently — so installing somebody else's repo can make
one of yours disappear from the listing with no message anywhere. The lockfile is keyed by name too,
which is why a rename reads as a **delete** rather than a move, and why skills have neither the
`displayName` nor the `renames` map Anthropic shipped for plugins after exactly this problem.

Measured 2026-09-12 against the public registry: five of one fifteen-skill corpus were names other
repos had already published, `skill-authoring` among them, claimed by six others including two
vendor repos. None of that was visible from the authoring side.

**What it does not do.** It does not judge a name. There is no published naming convention to judge
against — the specification's authoring pages contain none, no eval anywhere varies skill names, and
the only community rule (prefer verbs and gerunds) is contradicted by the corpus roughly six to one.
So this checks identity, which is mechanical, and leaves style alone, which is not.

**The network half is a query of somebody else's live data, so it can be wrong in one direction
only.** An unreachable registry is reported as `unknown` and exits 3 — never as clean. A check that
silently passes when it could not run is worse than no check, because the answer is trusted.

Stdlib only. Read-only: it reads skill directories and queries a public search endpoint, and writes
nothing anywhere. `--offline` makes it network-free, and every command takes `--json`.

Exit codes: 0 clean, 1 a collision, 2 argparse usage, 3 indeterminate (the registry could not be
reached, so nothing is claimed).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

REGISTRY = "https://skills.sh/api/search"
TIMEOUT = 20
INDETERMINATE = 3

# The scopes a loader actually walks, and deliberately not a source checkout.
#
# Two rival skills cannot both occupy one hub — the second would overwrite the first — so a genuine
# local collision is always *across scopes*: the user hub against a project's own `.agents/skills`,
# where the spec says the project wins and a warning is expected. A source `skills/` directory is not
# a scope; including it flags every skill whose source is merely ahead of its install, which is
# routine authoring and fires constantly. Pass `--root skills` explicitly to audit names you are
# writing; that finds one copy each and reports no conflict, which is the truth.
DEFAULT_ROOTS = ("~/.agents/skills", ".agents/skills")

Fetcher = Callable[[str], list[dict[str, object]]]


@dataclass
class NameCheck:
    """One name, and everyone else who publishes it."""

    name: str
    owners: list[str] = field(default_factory=list)
    local: list[tuple[str, str]] = field(default_factory=list)
    reachable: bool = True

    @property
    def local_conflict(self) -> bool:
        """Two local copies that are not the same file. One skill in two places is not a clash."""
        return len({digest for _, digest in self.local}) > 1

    @property
    def collides(self) -> bool:
        return bool(self.owners) or self.local_conflict

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "owners": self.owners,
            "local_paths": [path for path, _ in self.local],
            "local_conflict": self.local_conflict,
            "registry": "read" if self.reachable else "unreachable",
            "collides": self.collides,
        }


def fetch_registry(name: str) -> list[dict[str, object]]:
    """Ask the public index who publishes this name. Raises on any failure, so callers can tell
    "nobody has it" from "nobody answered" — the whole point of the unknown state."""
    url = f"{REGISTRY}?q={urllib.parse.quote(name)}"
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise TypeError(f"registry returned {type(payload).__name__}, not an object")
    skills = payload.get("skills", [])
    return skills if isinstance(skills, list) else []


def owners_of(name: str, fetch: Fetcher, mine: str | None = None) -> tuple[list[str], bool]:
    """Every source publishing this exact name, excluding your own.

    The endpoint is a fuzzy search, so a query for `plan-docs` returns `plan-docs-lite` and friends.
    Only an exact `skillId` match is a collision — a near miss is a different skill with a different
    key, and reporting it would train the reader to ignore this.
    """
    try:
        hits = fetch(name)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, AttributeError):
        # Deliberately broad. The contract is "any failure to get a usable answer is unknown", and
        # an exception escaping here would end the run — strictly worse than either verdict. Note
        # `json.JSONDecodeError` subclasses `ValueError` but catching the subclass alone does not
        # catch a plain one, which is how a payload of the wrong shape got through in testing.
        return [], False
    owners: set[str] = set()
    for hit in hits:
        if not isinstance(hit, dict) or hit.get("skillId") != name:
            continue
        identifier = str(hit.get("id", ""))
        source = identifier.rsplit("/", 1)[0] if "/" in identifier else ""
        if source and (mine is None or not source.lower().startswith(mine.lower())):
            owners.add(source)
    return sorted(owners), True


def local_skills(roots: Iterable[Path]) -> dict[str, list[tuple[str, str]]]:
    """Every skill name visible locally, mapped to each path claiming it and that copy's digest.

    The digest is what separates a real clash from a reflection. A source checkout and the installed
    hub both hold `plan-docs`, and they are the same skill — reporting that as a collision would fire
    on every skill the author has installed, which is how a check gets switched off. Two paths with
    **different** content under one name is the silent-drop condition; two paths with identical
    content is just the thing you installed.
    """
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            manifest = child / "SKILL.md"
            if child.is_dir() and manifest.is_file():
                digest = hashlib.sha256(manifest.read_bytes()).hexdigest()[:12]
                found[child.name].append((str(child), digest))
    return dict(found)


def resolve_roots(given: Sequence[str] | None) -> list[Path]:
    candidates = given or DEFAULT_ROOTS
    return [Path(entry).expanduser() for entry in candidates]


def run_checks(
    names: Sequence[str],
    local: dict[str, list[tuple[str, str]]],
    fetch: Fetcher | None,
    mine: str | None,
) -> list[NameCheck]:
    results: list[NameCheck] = []
    for name in names:
        check = NameCheck(name=name, local=local.get(name, []))
        if fetch is not None:
            check.owners, check.reachable = owners_of(name, fetch, mine)
        results.append(check)
    return results


def verdict(results: Sequence[NameCheck], offline: bool) -> int:
    if any(result.collides for result in results):
        return 1
    if not offline and any(not result.reachable for result in results):
        return INDETERMINATE
    return 0


def render(results: Sequence[NameCheck], offline: bool) -> None:
    colliding = [result for result in results if result.collides]
    unknown = [result for result in results if not result.reachable]

    for result in colliding:
        if result.local_conflict:
            print(f"  {result.name}: {len(result.local)} local copies, and they differ")
            for path, digest in result.local:
                print(f"      {digest}  {path}")
            print("      one of these is already invisible — the loader keeps the first it walks")
        if result.owners:
            print(f"  {result.name}: also published by {', '.join(result.owners)}")

    if unknown:
        print(f"  registry unreachable for {len(unknown)} name(s) — reported as unknown, not clean")

    if not colliding and not unknown:
        scope = "locally" if offline else "locally or in the public registry"
        print(f"  no collisions {scope} for {len(results)} name(s)")
        return

    if colliding:
        print()
        print("  A duplicate name is dropped silently, first-seen-wins, and the lockfile is keyed by")
        print("  name — so a rename later reads as a delete. Pick a free name now; it is the only")
        print("  cheap moment.")


def cmd_check(args: argparse.Namespace) -> int:
    local = local_skills(resolve_roots(args.root))
    results = run_checks(args.name, local, None if args.offline else fetch_registry, args.mine)
    return emit(results, args)


def cmd_audit(args: argparse.Namespace) -> int:
    local = local_skills(resolve_roots(args.root))
    if not local:
        print("  no skills found — name a directory with --root", file=sys.stderr)
        return 1
    results = run_checks(sorted(local), local, None if args.offline else fetch_registry, args.mine)
    return emit(results, args)


def emit(results: Sequence[NameCheck], args: argparse.Namespace) -> int:
    code = verdict(results, args.offline)
    if args.json:
        print(json.dumps({"results": [r.as_dict() for r in results], "exit": code}, indent=2))
    else:
        render(results, args.offline)
    return code


def build_parser() -> argparse.ArgumentParser:
    # Shared options live on a parent parser rather than the top level, so they may be written
    # after the subcommand. Argparse only accepts a top-level option *before* it, which reads as a
    # typo to anybody who has used a CLI built any other way.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", action="append", help="a skills directory; repeatable")
    common.add_argument("--mine", help="your own registry source, excluded from collisions (e.g. yourname)")
    common.add_argument("--offline", action="store_true", help="skip the registry; report local duplicates only")
    common.add_argument("--json", action="store_true")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", parents=[common], help="one or more candidate names, before adopting them")
    check.add_argument("name", nargs="+")
    check.set_defaults(func=cmd_check)

    sub.add_parser("audit", parents=[common], help="every skill name found under the roots").set_defaults(
        func=cmd_audit
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # A cut pipe is the reader's decision, not this script's error: die on SIGPIPE (exit 141).
    if hasattr(signal, "SIGPIPE"):  # absent on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
