#!/usr/bin/env python3
"""A repo's one-line pitch, checked against measured conventions rather than taste.

    pitch.py check "Command-line JSON processor"              # every rule, no surface budget
    pitch.py check "<text>" --name jq --surface github        # ...plus that surface's limit
    pitch.py check "<text>" --style trailing-period=required  # a house-style axis, per target
    pitch.py surfaces                                         # every length budget and its source
    pitch.py readme README.md                                 # the short description, extracted
    pitch.py drift --repo <owner>/<name> --readme README.md   # the one string, on all its surfaces

**Why a script and not a paragraph.** Every rule below is a threshold somebody measured, and a
prose version is re-derived (differently) on every run. More to the point, whether a rule may
*block* is itself a measurement: each one here carries the rate at which it fires against a corpus
that is already governed by written rules and machine-checked, and a rule that fires on that corpus
is a rule about taste rather than about defects.

**The corpora.** `GITHUB_RATE` is 856 developer-tool repos drawn from three star bands and filtered
to real tools. `DEBIAN_RATE` is 85,842 package synopses read from a machine's own apt lists —
governed by Debian's synopsis rules and checked by lintian, which is what makes it a control rather
than a second sample. A rule is allowed to gate only where the controlled corpus says it almost
never fires: the split is at 0.35%, and everything above it warns. Measured 2026-09-09.

**What it cannot tell you** (see `check --explain`): whether the category noun is the right one,
whether the pitch is true, whether it parses for somebody who is not the author. Nothing here scores
quality. Across the same 856 repos, the correlation between violations of these rules and stars is
+0.056 — so this checks that a pitch is *well formed*, never that it works.

Stdlib only, so it runs by path with no install step. `check`, `surfaces` and `readme` are offline
and read-only; `drift` shells out to `gh` and reads a package registry over the network. Every
subcommand takes `--json`.

Exit codes: 0 clean, 1 a gate-level finding (or any finding under `--strict`), 2 argparse usage.
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

GATE_MAX_FALSE_POSITIVE = 0.35
"""Above this rate on the controlled corpus, a rule may warn but must never block.

Not a round number chosen for tidiness: it is the gap in the measurements. Every rule sits either at
or below 0.35% or at or above 1.01%, with nothing in between, so the line falls in empty space and
moving it slightly changes nothing.
"""

Level = Literal["gate", "warn", "style"]

URL_RE = re.compile(r"https?://\S+|\bwww\.\S+")
LEADING_ARTICLE_RE = re.compile(r"^(a|an|the)\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(we|our|ours|us|my|mine)\b", re.IGNORECASE)
SHORTCODE_RE = re.compile(r":[a-z0-9_+-]+:")
WHITESPACE_RE = re.compile(r"^\s|\s$|\s\s|[\n\t\r]")

# Marketing register, not ordinary adjectives. `fast` and `modern` are deliberately absent: Homebrew
# bans them in prose and still carries them at 3.0% and 1.2%, which is the rate at which they are
# load-bearing rather than filler. A word earns a place here by being a claim no reader can check.
SUPERLATIVES = (
    "amazing",
    "awesome",
    "best-in-class",
    "blazing",
    "blazingly",
    "cutting-edge",
    "effortless",
    "effortlessly",
    "incredible",
    "next-generation",
    "powerful",
    "revolutionary",
    "seamless",
    "seamlessly",
    "state-of-the-art",
    "ultimate",
    "unparalleled",
    "world-class",
)
SUPERLATIVE_RE = re.compile(r"\b(" + "|".join(SUPERLATIVES) + r")\b", re.IGNORECASE)

# twitter-text v3 (`config/v3.json`): a weighted length, not a character count. Everything outside
# these ranges costs double, and a URL is a flat 23 whatever it actually says.
X_LIGHT_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
X_URL_WEIGHT = 23
X_MAX_WEIGHTED = 280


@dataclass(frozen=True)
class Rule:
    """One check, with the evidence that decides whether it may block."""

    name: str
    why: str
    debian_rate: float | None
    github_rate: float | None

    @property
    def level(self) -> Level:
        if self.debian_rate is None:
            return "style"
        return "gate" if self.debian_rate <= GATE_MAX_FALSE_POSITIVE else "warn"


RULES: dict[str, Rule] = {
    rule.name: rule
    for rule in (
        Rule("too_long", "over 100 characters reads as a paragraph in a one-line field", 0.19, 28.7),
        Rule("leading_article", "the field is a label, and a label does not open with an article", 0.35, 26.8),
        Rule("restates_name", "the name is rendered directly above, so repeating it spends the first words", 0.02, 7.8),
        Rule("contains_url", "a description is not a link field, and the surface rarely renders it", 0.01, 2.0),
        Rule("contains_emoji", "does not survive every surface that renders this string", 0.04, 16.2),
        Rule("superlative", "a claim the reader cannot check reads as marketing", 0.17, 5.3),
        Rule("first_person", "nobody is speaking in a metadata field", 0.20, 2.0),
        Rule("stray_whitespace", "renders wrong somewhere, and is invisible in review", 0.00, 2.0),
        Rule("over_80", "past the shortest surface that will carry it unabridged", 2.32, 38.3),
        Rule("repeats_name", "usually redundant, occasionally the clearest phrasing", 1.15, 27.8),
        Rule("feature_list", "two or more commas is a feature list wearing a pitch's clothes", 1.01, 27.0),
        Rule("trailing_period", "house style, and the registries disagree", None, 41.8),
        Rule("leading_capital", "house style, and the registries disagree", None, None),
    )
}


@dataclass(frozen=True)
class Surface:
    """Where a pitch is deployed, and what that place will actually store."""

    name: str
    limit: int
    source: str
    hard: bool = True
    note: str = ""


SURFACES: dict[str, Surface] = {
    surface.name: surface
    for surface in (
        Surface("github", 350, "API error string; 2 of 2,160 sampled repos exceed it, both legacy"),
        Surface("readme", 120, "standard-readme spec, Short Description (required)"),
        Surface(
            "hn",
            80,
            "news.arc `title-limit*`; the check is `len>`, so exactly 80 passes",
            note="`Show HN: ` costs 9, leaving 71",
        ),
        Surface("npm", 255, "registry API", note="truncated silently, mid-word, with no error"),
        Surface("pypi", 512, "warehouse `_LENGTH_LIMITS`; the only length-limited metadata field"),
        Surface("x", X_MAX_WEIGHTED, "twitter-text v3 config", note="weighted: non-Latin costs 2, any URL costs 23"),
        Surface("homebrew", 80, "`MAX_DESC_LENGTH` in the desc cop", note="0 violations in 8,595 formulae"),
        Surface(
            "producthunt",
            60,
            "Product Hunt launch guide",
            note="its help centre says 260 for the description; check the live form",
        ),
        Surface("appstream", 90, "`summary-too-long` validator tag", hard=False),
    )
}

STYLE_AXES = ("trailing-period", "leading-capital")
STYLE_CHOICES = ("required", "forbidden", "ignore")

# The README's short description, per standard-readme: the first line that is prose rather than
# furniture. These openers are furniture on every README that has them.
README_SKIP_PREFIXES = (
    "http",
    "license",
    "build",
    "coverage",
    "pypi",
    "installation",
    "install",
    "documentation",
    "docs",
    "status",
)
# An image is furniture and goes; a link is prose wearing markup, so it keeps its text. Deleting
# both is the obvious one-liner and it silently eats words: this repo's own README opens "Personal
# [Agent Skills](…) — plain SKILL.md directories", and dropping the link turns the pitch into
# "Personal — plain SKILL.md directories".
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Inline code markers are presentation, like the link syntax above, and the string the spec asks you
# to match is plain text. A README that names a file in backticks could otherwise never equal its own
# GitHub description, which is the check's whole purpose.
CODE_TICK_RE = re.compile(r"`+")
HTML_BLOCK_RE = re.compile(r"<picture>.*?</picture>|<img[^>]*>", re.DOTALL | re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
README_MIN_CHARS = 18


@dataclass
class Finding:
    rule: str
    level: Level
    message: str
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {"rule": self.rule, "level": self.level, "message": self.message, "detail": self.detail}


@dataclass
class Report:
    text: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def gated(self) -> bool:
        return any(finding.level == "gate" for finding in self.findings)

    def add(self, rule_name: str, message: str, detail: str = "", level: Level | None = None) -> None:
        rule = RULES[rule_name]
        self.findings.append(Finding(rule_name, level or rule.level, message, detail))


def has_emoji(text: str) -> bool:
    """Unicode symbol-other, which is what every registry's own emoji rule means in practice."""
    return any(unicodedata.category(char) == "So" for char in text) or bool(SHORTCODE_RE.search(text))


def weighted_length(text: str) -> int:
    """X's weighted length: a URL is a flat 23, anything outside the Latin ranges costs double."""
    without_urls, url_count = URL_RE.subn("", text)
    weight = 0
    for char in without_urls:
        point = ord(char)
        light = any(low <= point <= high for low, high in X_LIGHT_RANGES)
        weight += 1 if light else 2
    return weight + url_count * X_URL_WEIGHT


def surface_length(text: str, surface: Surface) -> int:
    return weighted_length(text) if surface.name == "x" else len(text)


def check_text(
    text: str,
    name: str | None = None,
    surface: Surface | None = None,
    style: dict[str, str] | None = None,
) -> Report:
    """Every rule, in the order a reader would notice them. Pure: no I/O, no network."""
    report = Report(text=text)
    style = style or {}

    stripped = text.strip()
    if not stripped:
        # One finding, not two: an empty pitch is already the whole answer, and adding a whitespace
        # complaint on top of it describes the same character twice.
        report.add("stray_whitespace", "empty")
        return report
    if WHITESPACE_RE.search(text):
        report.add("stray_whitespace", "leading, trailing, doubled or non-space whitespace")

    check_length(report, stripped)
    check_register(report, stripped)
    if name:
        report_name_rules(report, stripped, name)
    if surface is not None:
        check_surface(report, stripped, surface)
    apply_style(report, stripped, style)
    return report


def check_length(report: Report, text: str) -> None:
    """One finding, not two: over 100 is already over 80, and saying both twice is noise."""
    if len(text) > 100:
        report.add("too_long", f"{len(text)} characters", "the median developer-tool repo uses 68")
    elif len(text) > 80:
        report.add("over_80", f"{len(text)} characters", "under every hard limit, but past Homebrew and Show HN")


def check_register(report: Report, text: str) -> None:
    """The rules about how it reads, as opposed to how long it is or where it is going."""
    if LEADING_ARTICLE_RE.match(text):
        report.add("leading_article", f"opens with {text.split(maxsplit=1)[0]!r}")
    if URL_RE.search(text):
        report.add("contains_url", "contains a URL")
    if has_emoji(text):
        report.add("contains_emoji", "contains emoji")
    if match := SUPERLATIVE_RE.search(text):
        report.add("superlative", f"{match.group(0)!r} is a claim the reader cannot check")
    if match := FIRST_PERSON_RE.search(text):
        report.add("first_person", f"{match.group(0)!r}")
    if text.count(",") >= 2:
        report.add("feature_list", f"{text.count(',')} commas", "27.0% on GitHub, 1.0% on Debian")


def check_surface(report: Report, text: str, surface: Surface) -> None:
    used = surface_length(text, surface)
    if used <= surface.limit:
        return
    level: Level = "gate" if surface.hard else "warn"
    report.findings.append(
        Finding("surface_limit", level, f"{used} of {surface.limit} for {surface.name}", surface.note or surface.source)
    )


def report_name_rules(report: Report, text: str, name: str) -> None:
    """Two different findings, and conflating them is what makes the check feel wrong.

    Opening with the project's own name is nearly always waste — the surface renders the name
    immediately above. Mentioning it later can be the clearest phrasing available, which is why that
    one only ever warns.
    """
    escaped = re.escape(name)
    if re.match(rf"^{escaped}\b\s+(is|are)\b", text, re.IGNORECASE):
        report.add("restates_name", f"opens with {name!r} and a copula", "median cost, 12 characters")
    elif re.search(rf"\b{escaped}\b", text, re.IGNORECASE):
        report.add("repeats_name", "names itself", "the surface already shows the name")


def apply_style(report: Report, text: str, style: dict[str, str]) -> None:
    """Two axes on which real registries hold opposite positions, so neither has a default.

    Obsidian mandates a trailing period and 90.3% of its plugins comply; Homebrew forbids one;
    AppStream flags it; Debian omits it in 99.1% of synopses. Leading capital splits the same way.
    A checker that picks a side is wrong about half its targets, so it is told per target.
    """
    period = style.get("trailing-period", "ignore")
    if period == "required" and not text.endswith("."):
        report.add("trailing_period", "no trailing period, and this target requires one", level="gate")
    if period == "forbidden" and text.endswith(".") and not text.endswith("etc."):
        report.add("trailing_period", "trailing period, and this target forbids one", level="gate")

    capital = style.get("leading-capital", "ignore")
    first = text[0]
    if capital == "required" and not first.isupper():
        report.add("leading_capital", f"opens lowercase with {first!r}, and this target wants a capital", level="gate")
    if capital == "forbidden" and first.isupper():
        report.add("leading_capital", "opens with a capital, and this target's house style is lowercase", level="gate")


def readme_pitch(markdown: str) -> str | None:
    """The short description standard-readme requires, pulled out the way a reader finds it.

    Furniture first: the title, the badge row, the logo. The first line of actual prose is the
    pitch, and the spec says it must equal what GitHub and the package registry carry.
    """
    for block in re.split(r"\n\s*\n", markdown):
        # A heading is never the short description, and it has to be rejected before the leading
        # `#` is stripped — otherwise a title long enough to clear the minimum reads as prose.
        # `power-user-linux-setup` is exactly that case: its H1 is 30 characters.
        if block.lstrip().startswith("#"):
            continue
        text = HTML_BLOCK_RE.sub("", block)
        text = IMAGE_RE.sub("", text)
        text = LINK_RE.sub(r"\1", text)
        text = CODE_TICK_RE.sub("", text)
        text = HTML_TAG_RE.sub("", text)
        # A paragraph, not a line: every formatter here wraps prose, so the short description
        # arrives split across two or three lines and reading only the first truncates it.
        text = " ".join(text.split())
        text = text.lstrip("#*_> ").strip()
        if len(text) < README_MIN_CHARS:
            continue
        if text.lower().startswith(README_SKIP_PREFIXES):
            continue
        return text
    return None


def github_description(repo: str) -> str | None:
    """Whatever the About box currently holds. Shells out; returns None rather than raising."""
    try:
        done = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "description"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout).get("description") or None
    except json.JSONDecodeError:
        return None


def registry_summary(kind: str, package: str) -> str | None:
    """PyPI's `summary` or npm's `description`, read from the registry's own metadata."""
    urls = {
        "pypi": f"https://pypi.org/pypi/{package}/json",
        "npm": f"https://registry.npmjs.org/{package}",
    }
    if kind not in urls:
        return None
    try:
        with urllib.request.urlopen(urls[kind], timeout=15) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if kind == "pypi":
        return payload.get("info", {}).get("summary") or None
    return payload.get("description") or None


def normalise(text: str | None) -> str:
    return " ".join(text.split()).casefold() if text else ""


def cmd_check(args: argparse.Namespace) -> int:
    surface = SURFACES[args.surface] if args.surface else None
    style = parse_style(args.style)
    report = check_text(args.text, name=args.name, surface=surface, style=style)
    if args.json:
        print(json.dumps({"text": report.text, "findings": [f.as_dict() for f in report.findings]}, indent=2))
    else:
        render(report, explain=args.explain)
    if report.gated:
        return 1
    return 1 if args.strict and report.findings else 0


def parse_style(pairs: Sequence[str] | None) -> dict[str, str]:
    style: dict[str, str] = {}
    for pair in pairs or ():
        axis, _, value = pair.partition("=")
        if axis not in STYLE_AXES or value not in STYLE_CHOICES:
            raise SystemExit(f"--style takes <{'|'.join(STYLE_AXES)}>=<{'|'.join(STYLE_CHOICES)}>, not {pair!r}")
        style[axis] = value
    return style


def render(report: Report, explain: bool = False) -> None:
    print(f'  "{report.text}"  ({len(report.text.strip())} chars)')
    if not report.findings:
        print("  clean against every rule here — which is not the same as good; see --explain")
        return
    for finding in report.findings:
        marker = {"gate": "BLOCK", "warn": " warn", "style": "style"}[finding.level]
        print(f"  {marker}  {finding.rule}: {finding.message}")
        if finding.detail:
            print(f"         {finding.detail}")
    if explain:
        print()
        print("  Gate vs warn is a measurement, not a judgement: a rule may block only where it")
        print(f"  fires on at most {GATE_MAX_FALSE_POSITIVE}% of 85,842 rule-governed Debian synopses.")
        print("  Nothing here scores quality. Violations correlate with stars at +0.056 (n=856).")


def cmd_surfaces(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps([vars(surface) for surface in SURFACES.values()], indent=2))
        return 0
    width = max(len(name) for name in SURFACES)
    for surface in SURFACES.values():
        kind = "hard" if surface.hard else "warn"
        print(f"  {surface.name:<{width}}  {surface.limit:>4}  {kind}  {surface.source}")
        if surface.note:
            print(f"  {'':<{width}}        {surface.note}")
    return 0


def cmd_readme(args: argparse.Namespace) -> int:
    pitch = readme_pitch(args.path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps({"pitch": pitch}, indent=2))
        return 0
    if pitch is None:
        print("  no short description found — the README opens with furniture all the way down")
        return 1
    shown = pitch if len(pitch) <= 200 else pitch[:197] + "..."
    print(f'  "{shown}"  ({len(pitch)} chars)')
    if len(pitch) > 120:
        print("  over the 120 standard-readme allows — this README opens with a paragraph, not a pitch")
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    """standard-readme requires one string on three surfaces. Compliance measured at 25-38%."""
    surfaces: dict[str, str | None] = {}
    if args.readme:
        surfaces["readme"] = readme_pitch(args.readme.read_text(encoding="utf-8"))
    if args.repo:
        surfaces["github"] = github_description(args.repo)
    if args.pypi:
        surfaces["pypi"] = registry_summary("pypi", args.pypi)
    if args.npm:
        surfaces["npm"] = registry_summary("npm", args.npm)

    known = {name: value for name, value in surfaces.items() if value}
    distinct = {normalise(value) for value in known.values()}
    agreed = len(distinct) <= 1

    if args.json:
        print(json.dumps({"surfaces": surfaces, "agree": agreed}, indent=2))
        return 0 if agreed else 1

    for name, value in surfaces.items():
        print(f"  {name:<8} {value or '(unreadable or unset)'}")
    print()
    if len(known) < 2:
        print("  fewer than two surfaces readable — nothing to compare")
        return 0
    if agreed:
        print("  every readable surface carries the same string, as standard-readme requires")
        return 0
    print("  these disagree. The spec requires one string: the README's short description must")
    print("  match GitHub's description and the package manager's. Only 4 of 17 sampled projects")
    print("  matched README to GitHub, and 5 of 13 matched GitHub to their registry.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="every rule against one pitch")
    check.add_argument("text")
    check.add_argument("--name", help="the project's name, which enables the two self-reference rules")
    check.add_argument("--surface", choices=sorted(SURFACES), help="also apply that surface's length budget")
    check.add_argument("--style", action="append", metavar="AXIS=VALUE", help="trailing-period= or leading-capital=")
    check.add_argument("--strict", action="store_true", help="exit 1 on a warning too")
    check.add_argument("--explain", action="store_true", help="print what the levels mean and what this cannot see")
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=cmd_check)

    surfaces = sub.add_parser("surfaces", help="every length budget, with where the number came from")
    surfaces.add_argument("--json", action="store_true")
    surfaces.set_defaults(func=cmd_surfaces)

    readme = sub.add_parser("readme", help="extract the short description from a README")
    readme.add_argument("path", type=Path)
    readme.add_argument("--json", action="store_true")
    readme.set_defaults(func=cmd_readme)

    drift = sub.add_parser("drift", help="the same string across README, GitHub and a registry")
    drift.add_argument("--readme", type=Path)
    drift.add_argument("--repo", help="owner/name, read with gh")
    drift.add_argument("--pypi", help="package name on PyPI")
    drift.add_argument("--npm", help="package name on npm")
    drift.add_argument("--json", action="store_true")
    drift.set_defaults(func=cmd_drift)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # A cut pipe is the reader's decision, not this script's error: die on SIGPIPE (exit 141)
    # rather than raising BrokenPipeError through a traceback nobody asked for.
    if hasattr(signal, "SIGPIPE"):  # absent on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
