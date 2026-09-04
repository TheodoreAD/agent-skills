#!/usr/bin/env python3
"""Measure a set of installed skills: contention, listing budget, real usage, work that should be code.

Stdlib only, read-only, deterministic, zero tokens. Everything here is a *measurement*; nothing in
this file judges wording or rewrites a description. That split is deliberate and evidence-backed:
SkillsBench (84 tasks, 7,308 trajectories) found self-generated skills score -1.3pp against no
skills at all while curated ones score +16.2pp, so the model's place in this loop is drafting a
candidate that a trigger harness then scores — never authoring unmeasured.

Subcommands, cheapest first:

    inventory   every skill this machine can see, and which scope it came from
    budget      what the skill listing costs, and who loses their description first
    overlap     ranked pairs sharing trigger vocabulary, plus directional shadowing
    usage       real invocation counts from the transcript store (Claude Code only)
    absorb      ad-hoc python -c payloads that recur, i.e. candidates for skill code
    derivable   commands a SKILL.md asks an agent to compose that a script could carry
    portability what a SKILL.md assumes about its reader's machine, and whether it says so
    report      inventory + budget + usage, in the order a reader wants them

`report` is deliberately not "all of the above". The four sections it leaves out — overlap, absorb,
derivable, portability — all end in "edit the skill", which is work only a skill's author can do;
a reader who installed it must not edit the deployed copy. Name one to run it.

Every subcommand takes --json.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------------------------
# Where skills live, and where the transcripts are

DEFAULT_SCOPES = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]
TRANSCRIPTS = Path.home() / ".claude" / "projects"

# The spec's validity cap. Claude Code truncates the listing entry at 1536 and budgets the whole
# listing at ~1% of the context window; both numbers matter and they are not the same question.
SPEC_DESC_CAP = 1024

# Claude Code's listing arithmetic, read out of the 2.1.251 binary on 2026-08-31 rather than out of
# the documentation, because the documented behaviour ("descriptions are shortened to fit") is not
# what the code does — a description is kept whole or dropped whole. Every constant here is a
# default the user can override, named so it can be re-checked after a CLI upgrade.
LISTING_ENTRY_CAP = 1536  # skillListingMaxDescChars
BUDGET_FRACTION = 0.01  # skillListingBudgetFraction
BUDGET_CHARS_PER_TOKEN = 4  # the budget is in characters; this converts the window's tokens
DEFAULT_CONTEXT_TOKENS = 200_000  # the fallback when the model's window is unknown
BUDGET_ENV = "SLASH_COMMAND_TOOL_CHAR_BUDGET"  # an absolute char budget; overrides the fraction
# A listed entry is "- <name>: <description>"; a demoted one is "- <name>"; entries are newline
# separated, so n entries cost n-1 more.
ENTRY_OVERHEAD = 4
NAME_ONLY_OVERHEAD = 2
# The harness's own priority: usageCount decayed with a 7-day half-life, floored at a tenth.
USAGE_HALF_LIFE_DAYS = 7.0
USAGE_DECAY_FLOOR = 0.1
HARNESS_STATE = Path.home() / ".claude.json"
# YAML block-scalar indicators, which open a folded or literal value rather than being part of it.
BLOCK_SCALARS = frozenset({">", "|", ">-", "|-", ">+", "|+"})

# Words that carry no trigger signal. Deliberately short: an aggressive stop list is how a scanner
# starts silently discarding the domain terms that distinguish one skill from another.
STOP = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "that", "this", "these", "those",
    "of", "in", "on", "at", "to", "for", "with", "from", "by", "as", "is", "are", "was", "were",
    "be", "been", "being", "it", "its", "use", "used", "using", "when", "where", "which", "who",
    "whom", "what", "how", "why", "not", "no", "nor", "so", "such", "can", "could", "should",
    "would", "may", "might", "must", "will", "shall", "do", "does", "did", "done", "have", "has",
    "had", "you", "your", "yours", "we", "they", "them", "their", "there", "here", "also", "into",
    "over", "under", "about", "across", "per", "via", "each", "any", "all", "one", "two", "more",
    "most", "other", "others", "same", "own", "just", "only", "very", "both", "few", "some",
})  # fmt: skip

CODE_SPAN = re.compile(r"`([^`]+)`")
WORD = re.compile(r"[a-z][a-z0-9-]{2,}")
COMMAND_MARKER = re.compile(r"<command-name>/?([a-zA-Z0-9_-]+)</command-name>")
PY_DASH_C = re.compile(r"python3?$")


# --------------------------------------------------------------------------------------------
# Frontmatter


def parse_frontmatter(text: str) -> dict[str, str]:
    """Continuation-aware `key: value` scan.

    A line-by-line parse that skips indented lines silently truncates any wrapped value, which is
    precisely the long descriptions worth measuring. Confirmed 2026-08-30: that bug hid the only
    over-cap description in this repo's own corpus from its own gate.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    key: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if key is not None:
            # `description: >-` is a block scalar: the indicator is syntax, not the first word of
            # the value. Keeping it put ">- " on the front of every folded description, which
            # inflated the measured length by three and made a "Use when" lead-in look like it
            # matched at offset 3 rather than 0. Caught 2026-08-31, by two measurements disagreeing.
            body = parts[1:] if parts and parts[0] in BLOCK_SCALARS else parts
            value = " ".join(p for p in body if p).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key] = value

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            flush()
            key, first = m.group(1), m.group(2)
            parts = [first.strip()]
        elif key is not None:
            parts.append(line.strip())
    flush()
    return fields


@dataclass
class Skill:
    name: str
    scope: str
    path: Path
    description: str
    when_to_use: str = ""
    body_lines: int = 0
    has_scripts: bool = False
    has_references: bool = False
    has_evals: bool = False

    @property
    def listing_text(self) -> str:
        """What the harness puts after the colon: `description`, or `description - when_to_use`."""
        return f"{self.description} - {self.when_to_use}" if self.when_to_use else self.description

    @property
    def entry_chars(self) -> int:
        """`- <name>: <description>`, with the description capped at the per-entry limit."""
        return len(self.name) + ENTRY_OVERHEAD + min(len(self.listing_text), LISTING_ENTRY_CAP)

    @property
    def name_only_chars(self) -> int:
        """`- <name>` — what the entry costs once its description has been dropped."""
        return len(self.name) + NAME_ONLY_OVERHEAD

    def terms(self) -> set[str]:
        """Vocabulary for the overlap measure, taken from the **whole** description.

        An earlier version tried to isolate the trigger clause — the "when to use it" half, on the
        reasoning that only that half decides selection — by taking the span from a `Use when`
        lead-in onward. Measured 2026-08-31 against the installed corpus: **it stripped nothing from
        12 of 13 descriptions and three characters from the thirteenth**, because the convention it
        was written for puts the trigger clause *first*, so the lead-in matches at position zero.
        The prose it meant to exclude trails the trigger clause rather than preceding it, and
        finding *that* boundary means guessing at sentence openers ("Covers", "Also", "For X see
        Y") — repo-specific, and the objection that killed the idea of a `when_to_use` field.

        So the split is not attempted. What actually suppresses non-discriminating prose is the
        corpus-derived IDF below, and its limits are documented there rather than hidden behind an
        extraction step that does nothing.
        """
        text = self.description
        # A backticked term is high-signal: it names a command, flag or file the request will use.
        coded = {t.lower() for span in CODE_SPAN.findall(text) for t in WORD.findall(span.lower())}
        plain = set(WORD.findall(text.lower()))
        return (coded | plain) - STOP


def load_skills(roots: list[Path]) -> list[Skill]:
    """First occurrence of each name wins, and only a *differing* second copy is worth reporting.

    Two subtleties, both learned by the first run producing twenty findings and no information.
    `~/.claude/skills` is commonly a symlink to `~/.agents/skills`, so the same directory arrives
    twice under two names — resolving each root removes that entirely. And a skills repo checked
    out on the same machine as its own installed copy legitimately holds every one of those names;
    that is a duplicate, not a collision.

    What is left after both is the finding worth having: **the same name in two scopes with
    different content**, which means one copy is stale — usually an install that has drifted behind
    its source, which is otherwise invisible until a skill behaves like an older version of itself.
    """
    found: dict[str, Skill] = {}
    digests: dict[str, str] = {}
    stale: list[tuple[str, str, str]] = []
    seen_roots: set[Path] = set()

    for root in roots:
        resolved = root.resolve()
        if not resolved.exists() or resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        for md in sorted(resolved.glob("*/SKILL.md")):
            text = md.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(text)
            name = fm.get("name") or md.parent.name
            digest = sha256(text.encode("utf-8")).hexdigest()
            if name in found:
                if digests[name] != digest:
                    stale.append((name, found[name].scope, str(root)))
                continue
            digests[name] = digest
            found[name] = Skill(
                name=name,
                scope=str(root),
                path=md.parent,
                description=fm.get("description", ""),
                when_to_use=fm.get("when_to_use", ""),
                body_lines=len(text.splitlines()),
                has_scripts=(md.parent / "scripts").is_dir(),
                has_references=(md.parent / "references").is_dir(),
                has_evals=(md.parent / "evals").is_dir(),
            )
    load_skills.stale = stale  # type: ignore[attr-defined]
    return sorted(found.values(), key=lambda s: s.name)


# --------------------------------------------------------------------------------------------
# Overlap and shadowing


def idf(skills: list[Skill]) -> dict[str, float]:
    """Inverse document frequency over the corpus itself, with a corpus-derived stop list.

    A term appearing in half the corpus or more carries no signal about *which* skill a request
    belongs to, however meaningful it is in English — on this family "repo", "agent" and "project"
    are in nearly every description. Deriving that set from the corpus beats hand-listing words:
    a hand-written stop list is how a scanner starts silently discarding the domain vocabulary that
    distinguishes one skill from another, and it has to be re-tuned for every consumer's corpus.

    **Measured limit, 2026-08-31: on a 13-skill corpus this drops exactly one term.** The cut needs
    a term in half the corpus, and prose vocabulary is spread thinner than that — so the shared-term
    lists this feeds are dominated by ordinary English ("working", "writing", "rather", "before")
    rather than by anything a request would be phrased in. It is a real weighting, not a real
    filter, and it gets stronger as the corpus grows. Together with the noisy IDF on a corpus this
    small, it is why the output is a ranked list to spend a live run on and never a pass/fail
    threshold.
    """
    n = max(len(skills), 1)
    df: Counter[str] = Counter()
    for s in skills:
        df.update(s.terms())
    ubiquitous = {t for t, c in df.items() if n > 3 and c >= max(2, (n + 1) // 2)}
    idf.ubiquitous = sorted(ubiquitous)  # type: ignore[attr-defined]
    return {t: 1.0 + (n / (1 + c)) ** 0.5 for t, c in df.items() if t not in ubiquitous}


def weighted_jaccard(a: set[str], b: set[str], w: dict[str, float]) -> float:
    inter = sum(w.get(t, 1.0) for t in a & b)
    union = sum(w.get(t, 1.0) for t in a | b)
    return inter / union if union else 0.0


def containment(a: set[str], b: set[str], w: dict[str, float]) -> float:
    """How much of b's trigger vocabulary a already covers. Asymmetric, unlike Jaccard.

    This is what detects shadowing: a broad skill whose trigger set subsumes a narrow one's wins
    requests meant for the narrow one, and a symmetric measure cannot express that at all.
    """
    total = sum(w.get(t, 1.0) for t in b)
    return sum(w.get(t, 1.0) for t in a & b) / total if total else 0.0


def overlap_pairs(skills: list[Skill]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Ranked pairs, with shadowing judged against this corpus rather than a constant.

    An absolute cutoff is the mistake this tool exists to point at: the AI-security scanner it was
    compared against fires at Jaccard > 0.7, which on prose descriptions is close to never. The
    first draft of *this* function used an absolute 0.5 for containment and fired on nothing, for
    the same reason. So shadowing is flagged relative to the corpus's own distribution — a pair is
    a candidate when its directional coverage is a standard deviation above the mean and clearly
    one-sided — and the numbers are always printed so the judgement stays the reader's.
    """
    w = idf(skills)
    rows: list[dict[str, Any]] = []
    for a, b in combinations(skills, 2):
        ta, tb = {t for t in a.terms() if t in w}, {t for t in b.terms() if t in w}
        if not ta or not tb:
            continue
        shared = sorted(ta & tb, key=lambda t: -w.get(t, 1.0))
        rows.append(
            {
                "a": a.name,
                "b": b.name,
                "similarity": round(weighted_jaccard(ta, tb, w), 3),
                "a_covers_b": round(containment(ta, tb, w), 3),
                "b_covers_a": round(containment(tb, ta, w), 3),
                "shared_terms": shared[:12],
                "shared_count": len(shared),
            }
        )

    coverages = [float(r[k]) for r in rows for k in ("a_covers_b", "b_covers_a")]
    stats: dict[str, float] = {}
    if coverages:
        mean = sum(coverages) / len(coverages)
        sd = (sum((c - mean) ** 2 for c in coverages) / len(coverages)) ** 0.5
        cut = mean + sd
        stats = {"coverage_mean": round(mean, 3), "coverage_sd": round(sd, 3), "shadow_cut": round(cut, 3)}
        for r in rows:
            ab, ba = float(r["a_covers_b"]), float(r["b_covers_a"])
            r["shadows"] = ""
            if ab > cut and ab > ba * 1.5:
                r["shadows"] = f"{r['a']} may shadow {r['b']}"
            elif ba > cut and ba > ab * 1.5:
                r["shadows"] = f"{r['b']} may shadow {r['a']}"

    rows.sort(key=lambda r: -max(float(r["similarity"]), float(r["a_covers_b"]), float(r["b_covers_a"])))
    return rows, stats


# --------------------------------------------------------------------------------------------
# Transcript store: the listings actually sent


@dataclass
class Listing:
    """One `skill_listing` attachment: the exact text the harness sent the model that turn."""

    session: str
    project: str
    date: str
    chars: int
    count: int
    names: list[str]
    demoted: list[str]
    transient: bool  # from a temporary working directory, so possibly a probe rather than work


def _entries_in_order(content: str, names: list[str]) -> dict[str, bool]:
    """Map each listed name to whether it kept its description, walking the declared order.

    Descriptions may contain newlines, so a continuation line can look exactly like an entry —
    `- init` is a plausible thing to write inside prose, and `init` is also a real skill. Two
    cheap defences, because a miscount here reports a working skill as demoted:

    - **the walk is order-aware**, so a stray line only misleads if it names the *next* expected
      entry rather than any entry;
    - **an entry cannot be both demoted and described**, so a bare `- name` line is only read as a
      demotion when that name appears nowhere in the text with a description after it.

    Neither is a proof. A description whose text contains a bare line naming the next entry, where
    that entry is genuinely demoted, is still ambiguous — and is left counted as a demotion, which
    is the safe direction: it over-reports a problem rather than hiding one.
    """
    described = {n for n in names if re.search(rf"(?m)^- {re.escape(n)}: ", content)}
    kept: dict[str, bool] = {}
    i = 0
    for line in content.split("\n"):
        if i >= len(names):
            break
        want = names[i]
        if line.startswith(f"- {want}: "):
            kept[want] = True
            i += 1
        elif line == f"- {want}" and want not in described:
            kept[want] = False
            i += 1
    return kept


def scan_listings() -> list[Listing]:
    """Every listing the harness actually sent, read back out of the transcript store.

    This is ground truth and it outranks any model of the budget, including this file's own. The
    attachment carries the rendered text, the entry count and the names, so a demoted entry — one
    rendered as a bare `- name` — is directly observable rather than simulated. Two things it
    settled that the arithmetic got wrong:

    - **The exempt set is not "everything bundled".** Measured 2026-08-31 in a real listing:
      `security-review` was demoted while `code-review`, `run` and `init` kept their descriptions,
      so exemption tracks something narrower than "the harness shipped it" and cannot be inferred
      from a skill's origin. An observed listing is the only reliable split.
    - **The interactive listing is larger than any headless probe of it**: 18,109 characters over
      30 entries observed, against 15,486 over 25 from `probe_listing`.

    `transient` marks a listing captured under a temporary working directory. A trigger or budget
    probe lands there, and so does a tool run in a scratch checkout — worth separating from real
    sessions, worth reporting rather than dropping.
    """
    listings: list[Listing] = []
    if not TRANSCRIPTS.exists():
        return listings
    for path in TRANSCRIPTS.rglob("*.jsonl"):
        transient = path.parent.name.startswith("-tmp-")
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"skill_listing"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                att = obj.get("attachment")
                if not (isinstance(att, dict) and att.get("type") == "skill_listing"):
                    continue
                content = str(att.get("content") or "")
                names = [str(n) for n in (att.get("names") or [])]
                kept = _entries_in_order(content, names)
                listings.append(
                    Listing(
                        session=path.stem[:8],
                        project=path.parent.name,
                        date=str(obj.get("timestamp") or "")[:10],
                        chars=len(content),
                        count=int(att.get("skillCount") or len(names)),
                        names=names,
                        demoted=sorted(n for n, k in kept.items() if not k),
                        transient=transient,
                    )
                )
    listings.sort(key=lambda listing: listing.date)
    return listings


# --------------------------------------------------------------------------------------------
# Transcript store: real usage, and absorbable scripts


@dataclass
class Usage:
    tool_calls: Counter[str] = field(default_factory=Counter)
    explicit: Counter[str] = field(default_factory=Counter)
    last_seen: dict[str, str] = field(default_factory=dict)
    sessions: int = 0
    # Whether the transcript store was there to read at all. Without this the counters are zero on
    # a machine that has never run Claude Code and zero on a skill nobody invoked, and the report
    # cannot tell a reader which — while this skill's own rule is that a zero is not a verdict.
    available: bool = False


def _blocks(path: Path):
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        yield obj, b
            elif isinstance(content, str):
                yield obj, {"type": "text", "text": content}


def scan_usage(exclude: set[str] | None = None) -> Usage:
    """Count both invocation mechanisms, because neither alone is the rate.

    A `Skill` tool_use is the model choosing the skill. A `<command-name>` marker in a user turn is
    the person typing `/name`, which frequently does *not* produce a tool call — the body is
    injected directly instead. Measured 2026-08-30: session-harvest had 11 tool calls against 84
    typed invocations, plan-docs 69 against 12. Reporting either number alone misleads, in opposite
    directions for those two skills.
    """
    u = Usage()
    exclude = exclude or set()
    if not TRANSCRIPTS.exists():
        return u
    u.available = True

    def record(counter: Counter[str], name: str, stamp: str) -> None:
        if not name or name in exclude:
            return
        counter[name] += 1
        if stamp:
            u.last_seen[name] = max(u.last_seen.get(name, ""), stamp)

    for path in TRANSCRIPTS.rglob("*.jsonl"):
        u.sessions += 1
        for obj, b in _blocks(path):
            stamp = str(obj.get("timestamp") or "")[:10]
            if obj.get("type") == "user" and b.get("type") == "text":
                for m in COMMAND_MARKER.finditer(b.get("text") or ""):
                    record(u.explicit, m.group(1), stamp)
            elif b.get("type") == "tool_use" and b.get("name") == "Skill":
                inp = b.get("input") or {}
                record(u.tool_calls, str(inp.get("skill") or inp.get("command") or ""), stamp)
    return u


# A "demand" signal was built here and removed on 2026-08-31, and the removal is worth recording
# so it is not rebuilt the same way. The question is real: an invocation count of zero has two
# causes needing opposite responses — the request came up and the skill lost it, or the request
# never came up at all. Both of this repo's never-invoked skills turned out to be the second case,
# scoring 7/7 on a live trigger suite; reporting their zero as a defect would have sent someone to
# rewrite two working descriptions.
#
# What does not work is inferring demand from words. Two constructions were measured, both useless:
# counting sessions whose user turns contained 3+ of a skill's distinctive terms gave 370-430 for
# all eleven skills across 593 transcripts, including one written that day; tightening to per-turn
# matches on terms claimed by at most two skills made the numbers larger, not sharper. Skill
# descriptions share too much ordinary technical English — "install", "command", "check", "repo" —
# for a bag-of-words proxy to separate them, and a column that cannot discriminate is worse than no
# column, because it still gets read as a finding.
#
# **Gap detection was attempted here too, on 2026-08-31, and it does not work lexically either.**
# The live suites had shown that contention is not what fails — 89 runs, 0 steals — while every real
# failure was a request that fired nothing. That made "find the requests nothing answers" the tool's
# main open problem, and the transcript store looks like it holds the missing half. It does not, in
# any form a rule can read. Three constructions, all measured against 165 real opening requests:
#
#   1. Terms frequent in real requests but absent from every description. Top of the list: "look",
#      "need", "don", "let", "get", "now", "make". Ordinary English, exactly as before.
#   2. The discriminative version — terms over-represented in sessions where no skill fired versus
#      sessions where one did. Ratios rested on counts like 5-against-1, and the winners were
#      "previous", "latest", "either", "lot", "true".
#   3. The non-lexical one, and the closest to working: an explicitly typed `/name` means the model
#      did not route the request, so the user's own words just before it are a real gap example.
#      Of ~130 typed invocations, nearly every preceding turn was harness boilerplate — a compact
#      summary, an injected skill body. Two were genuine, and they were found by reading the output,
#      not by any rule in it.
#
# So there is no gap detector here, and building one is not the next step. What the tool does have
# is a *behavioural* pointer at which skill to go and test: the `auto` versus `explicit` split in
# `scan_usage`. A person typing `/name` is a person the description did not serve, and that signal
# needs no vocabulary matching at all.
#
# The working answer to every version of this question is `trigger.py`: write a handful of cases in
# the words a request would actually use and see whether the skill fires. That costs tokens and takes
# judgement, which is precisely why it works where five free heuristics over prose did not.


def _payload(cmd: str) -> str | None:
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return None
    for i, tok in enumerate(parts):
        if tok == "-c" and i and PY_DASH_C.search(parts[i - 1]) and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _imports(src: str) -> frozenset[str]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            tree = ast.parse(src)
        except (SyntaxError, ValueError):
            return frozenset()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return frozenset(mods)


def _shape(src: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            tree = ast.parse(src)
        except (SyntaxError, ValueError):
            return ""
    return " ".join(sorted(type(n).__name__ for n in ast.walk(tree)))


FENCE = re.compile(r"^\s*```(\S*)")
# Fences whose contents are commands. An untagged fence is included because the convention is
# widespread, and filtered afterwards by `_is_command` — an untagged block is just as likely to hold
# a directory tree, and counting one of those as commands is how this measure becomes noise.
COMMAND_LANGS = frozenset({"", "shell", "bash", "sh", "zsh", "console", "shell-session", "sql", "http"})
# A command starts with a bare program name, optionally behind `VAR=value` or a `$ ` prompt. A first
# token containing a slash is a path — the tell that separates `git -C <store> log` from
# `repos/<host>--<owner>--<repo>/`, which is a layout diagram and not a command at all.
ENV_PREFIX = re.compile(r"^(?:\$\s+)?(?:[A-Za-z_]\w*=\S*\s+)*")
COMMAND_HEAD = re.compile(r"^[A-Za-z][\w.+-]*$|^[~./][\w./+-]*[\w.+-]$|^\$\w+$")
SCRIPT_CALL = re.compile(r"scripts/[\w.-]+\.(py|sh)|\b[\w.-]+\.py\b")
# `python3 <path> list`, `python3 $H sweep` — a skill abbreviating its own script's path. Counting
# these as derivable put `plan-docs` at 48 of 49, when 45 of them are calls into `plans.py`: the
# measure would have reported the repo's best-delegated skill as its worst offender.
SCRIPT_INDIRECT = re.compile(r"\b(?:python3?|uv\s+run)\s+(?:<[^>]+>|\$\w+)")
PLACEHOLDER = re.compile(r"<[^>\s][^>]*>|\$[A-Z][A-Z0-9_]{2,}|\{\w+\}")
SQL_HEAD = re.compile(r"^\s*(select|insert|update|delete|create|alter|with)\b", re.IGNORECASE)
# SQL anywhere in the line, not only at its start: the shape that actually appears in a SKILL.md
# is a query quoted inside a CLI call (`psql -c "SELECT …"`, `sqlite3 db "…"`), and a head-only
# match sees none of those — the category the principle names most explicitly.
SQL_BODY = re.compile(
    r"\bselect\b[^\"']*\bfrom\b|\binsert\s+into\b|\bupdate\b[^\"']*\bset\b|"
    r"\bdelete\s+from\b|\bcreate\s+(table|index|view)\b|\balter\s+table\b",
    re.IGNORECASE,
)
# A request tool, not merely a URL: `uv tool install git+https://…` is a fixed install line with
# nothing to derive, and matching bare URLs reported it as an HTTP API call.
HTTP_CALL = re.compile(r"\bcurl\b|\bhttpie?\b|\bgh\s+api\b|\bwget\b|\bhttpx?\.(get|post)\b")
JSON_WORK = re.compile(r"\bjq\b|--json\b|json\.tool|\bpython3?\s+-c\b.*json")
FLAGGED = re.compile(r"(?:^|\s)--?[A-Za-z][\w-]*")


def command_lines(body: str) -> list[str]:
    """Every command line in a `SKILL.md`'s fenced blocks, continuations joined, comments dropped.

    Joining `\\`-continuations is not cosmetic: an `audit.py` invocation wrapped over three lines
    counted as three commands, two of which had lost the program name that made them delegation.
    Every early false positive in this measure came from reading a fragment as a command.
    """
    out: list[str] = []
    lang: str | None = None
    pending = ""
    for raw in body.splitlines():
        fence = FENCE.match(raw)
        if fence:
            lang, pending = (fence.group(1).lower() if lang is None else None), ""
            continue
        if lang is None or lang not in COMMAND_LANGS:
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            pending += line[:-1].strip() + " "
            continue
        command = (pending + line).strip()
        pending = ""
        if _is_command(command):
            out.append(command)
    return out


def _is_command(line: str) -> bool:
    if SQL_HEAD.match(line):
        return True
    head = ENV_PREFIX.sub("", line).split()
    return bool(head) and bool(COMMAND_HEAD.match(head[0]))


def classify_command(line: str, has_scripts: bool = False) -> set[str]:
    """What a command line asks of the reader. An empty set means a fixed literal — nothing to do.

    `script` wins over everything: a call to a `scripts/*.py` is the delegation this whole measure
    is trying to produce, and it is still delegation when it carries `<session-id>` and a pipe.
    """
    body = line.split("#", 1)[0] if " #" in line else line
    if SCRIPT_CALL.search(body) or (has_scripts and SCRIPT_INDIRECT.search(body)):
        return {"script"}
    kinds: set[str] = set()
    if PLACEHOLDER.search(body):
        kinds.add("placeholder")
    # Placeholders are stripped before the shell operators are looked for: `<path>` closes with a
    # `>`, so every placeholder line read as a redirect and the tag appeared on 48 lines that have
    # no redirect in them.
    shell = PLACEHOLDER.sub(" ", body)
    if "|" in shell:
        kinds.add("pipeline")
    if "&&" in shell or ";" in shell:
        kinds.add("chain")
    if re.search(r"\d?>>?\s*\S", shell):
        kinds.add("redirect")
    if HTTP_CALL.search(body):
        kinds.add("http")
    if SQL_HEAD.match(body) or SQL_BODY.search(body):
        kinds.add("sql")
    if JSON_WORK.search(body):
        kinds.add("json")
    if len(FLAGGED.findall(body)) >= 2:
        kinds.add("flags")
    return kinds


def scan_derivable(skills: list[Skill]) -> list[dict[str, Any]]:
    """Work a skill asks an agent to compose in prose that a script could do once.

    The static half of the question `absorb` answers dynamically. `absorb` needs a transcript store
    and only sees what an agent already re-wrote; this reads the `SKILL.md` itself, so it catches a
    skill that has drifted *before* anybody pays for it, and it works on a corpus nobody has run.

    The principle it measures, stated by the user 2026-09-02: anything non-trivial a skill can
    derive deterministically belongs in a script — a CLI's flag syntax, an HTTP request shape, a SQL
    query, a JSON traversal. Having a model re-derive those every run is wasteful and risky, and a
    rule that tells an agent *how to spell a command* has to be followed correctly every single
    time, while a script is followed once. Confirmed by `session-harvest`, which carried six such
    rules as prose warnings and had each of them missed at least once anyway.

    Three buckets per command line, and the middle one is the finding:

    - **delegated** — the line calls a `scripts/*.py`, its own or a sibling skill's. The target
      shape, and it stays delegated however many placeholders it carries.
    - **derivable** — a placeholder, a pipeline, a chain, an HTTP call, a query, a JSON traversal:
      something assembled from context on every run, and not a script call.
    - **fixed** — a literal with no variable parts. Cheap to read, cheap to run, not a finding.
    """
    rows: list[dict[str, Any]] = []
    for skill in skills:
        body = (skill.path / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        lines = command_lines(body)
        buckets: dict[str, list[dict[str, Any]]] = {"delegated": [], "derivable": [], "fixed": []}
        for line in lines:
            kinds = classify_command(line, skill.has_scripts)
            bucket = "delegated" if "script" in kinds else ("derivable" if kinds else "fixed")
            buckets[bucket].append({"command": line[:200], "kinds": sorted(kinds - {"script"})})
        tags = Counter(k for row in buckets["derivable"] for k in row["kinds"])
        rows.append({
            "skill": skill.name,
            "has_scripts": skill.has_scripts,
            "commands": len(lines),
            "delegated": len(buckets["delegated"]),
            "derivable": len(buckets["derivable"]),
            "fixed": len(buckets["fixed"]),
            "kinds": dict(tags.most_common()),
            "samples": buckets["derivable"],
        })  # fmt: skip
    rows.sort(key=lambda r: (-int(r["derivable"]), r["skill"]))
    return rows


# --------------------------------------------------------------------------------------------
# portability: what a skill assumes about the machine that is reading it

# `skills add` puts every install under the same hub on every machine, so a skill citing its own
# script by that path cites something the reader actually has. It is the one `~/` path that is not
# an assumption, and excluding it is what keeps the measure from reporting the correct idiom.
# The install hub, plus the XDG base directories and the user dirs beside them. None of these is an
# assumption about a *particular* machine: they are published defaults that mean the same thing on
# every one, so naming them is the opposite of the finding this measure looks for — a skill that
# says it keeps state in `~/.local/state/<name>/` has told its reader everything there is to know.
# Added 2026-09-04, when documenting the destinations in `skill-authoring` produced eleven findings
# for a section whose entire purpose is declaring where things go.
PORTABLE_HOME = (
    "~/.agents/skills",
    "~/.config",
    "~/.local/state",
    "~/.local/share",
    "~/.cache",
    "~/Documents",
)
# A path is followed by prose punctuation as often as not, and `~/AGENTS.md.` reported as a distinct
# token from `~/AGENTS.md` is one finding printed twice.
HOME_PATH = re.compile(r"~/[\w./*-]*[\w*]")
ABS_HOME = re.compile(r"/(?:home|Users)/[\w.-]+(?:/[\w./*-]*[\w*])?")
# Three characters and up, so a `$S=…` shorthand a fenced block defines on its own first line is
# not reported as something the reader has to have set before running anything.
ENV_VAR = re.compile(r"\$([A-Z][A-Z0-9_]{2,})")
# Shell basics, plus the XDG variables — those are the specification's own, already under the user's
# control, so a skill using one is *removing* a setting rather than asking for one. A skill-invented
# `$SOMETHING_HOME` is the finding; `$XDG_STATE_HOME` never is.
ENV_UNIVERSAL = frozenset({
    "HOME", "PATH", "PWD", "USER", "SHELL", "EDITOR", "TMPDIR", "LANG", "TERM",
    "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR",
})  # fmt: skip
# Runners whose *targets* come from a repo rather than from the tool. `inv quality.precommit` is a
# task that exists in the author's repos and nowhere else; `git status` is the same everywhere.
TASK_RUNNERS = frozenset({"inv", "invoke", "make", "just", "rake", "nox", "tox", "task", "mise"})
INSTALL_LINE = re.compile(r"skills\s+add\s+([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)")
GITHUB_LINK = re.compile(r"github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)")
CODE_INLINE = re.compile(r"`([^`]+)`")

# The corpus's own idiom for owning an assumption instead of stating it as fact. Deliberately
# narrow: a loose pattern marks everything declared and the measure reports nothing. "on this
# author's machine" is the phrase this corpus already uses in the places that got it right.
DECLARED = re.compile(
    r"on (?:this|the) author'?s machine|this author'?s own|on my machine|"
    r"the repo'?s (?:own )?equivalent|your own|substitute|if you have|if your|"
    r"where no such|where a repo has one|assumes|unavailable|not available|"
    r"only if|set (?:it|this|that) to|defaults? to|\(default|by default|overrides?\b|export |"
    r"points at|if (?:it|one) (?:is|exists)|where you keep|cannot know|if it exports",
    re.IGNORECASE,
)


def author_vocabulary(skills: list[Skill], extra: list[str] | None = None) -> tuple[str, list[str]]:
    """The author's repo names, derived from the corpus rather than from the machine running this.

    A machine-derived list (the way a private-name scanner reads the project roots) would make the
    answer depend on whose laptop the audit runs on, and the question here is about the *reader's*
    machine, not the author's. Two self-describing sources instead: the `skills add <owner>/<repo>`
    line the corpus carries for its own install names the owner, and every `github.com/<that
    owner>/…` link in the corpus names a repo that owner has. Both travel with the files.

    The vocabulary is seeded from every markdown file in a skill, not only its `SKILL.md`: a repo
    linked once from a `references/rationale.md` is still the repo whose name appears bare in three
    other skills' bodies, and reading `SKILL.md` alone missed exactly that case.

    The known gap: a sibling repo the corpus never links (one `*-mcp` of five is linked, the rest
    are named in prose) is invisible here. `--author-repo` adds one by hand.
    """
    texts = [
        path.read_text(encoding="utf-8", errors="replace") for s in skills for path in sorted(s.path.rglob("*.md"))
    ]
    owners: Counter[str] = Counter()
    repos: set[str] = set(extra or [])
    for text in texts:
        for owner, repo in INSTALL_LINE.findall(text):
            owners[owner] += 1
            repos.add(repo)
    if not owners:
        return "", sorted(repos)
    owner = owners.most_common(1)[0][0]
    for text in texts:
        repos.update(repo for linked, repo in GITHUB_LINK.findall(text) if linked == owner)
    return owner, sorted(repos)


def _blocks_by_line(lines: list[str]) -> list[int]:
    """Which blank-line-separated block each line belongs to. A bullet list with no blank lines
    between its items is one block, which is deliberate: a hedge in the lead-in sentence covers the
    bullets under it, and that is how the corpus's correct instances are actually written."""
    out: list[int] = []
    block = 0
    for line in lines:
        if not line.strip():
            block += 1
        out.append(block)
    return out


def _references(line: str, in_fence: bool, repos: re.Pattern[str] | None, own_name: str = "") -> list[tuple[str, str]]:
    """Every assumption one line makes about the reader's machine, as (kind, token) pairs.

    `own_name` exempts the runner a skill is *about*: `invoke-task-conventions` naming `inv` on
    every second line is its subject, not an assumption, and reporting it buries the skills where
    the same token is an instruction the reader cannot follow.
    """
    found: list[tuple[str, str]] = [
        ("home-path", path) for path in HOME_PATH.findall(line) if not path.startswith(PORTABLE_HOME)
    ]
    found.extend(("abs-path", path) for path in ABS_HOME.findall(line))
    found.extend(("env-var", f"${name}") for name in ENV_VAR.findall(line) if name not in ENV_UNIVERSAL)
    if repos is not None:
        found.extend(("author-repo", name) for name in repos.findall(line))
    code = line if in_fence else " ".join(CODE_INLINE.findall(line))
    heads = re.findall(r"(?:^|[`\s(])([a-z][\w-]*)\s+[\w.:-]+", code)
    found.extend(("task-runner", h) for h in heads if h in TASK_RUNNERS and h not in own_name)
    return found


def _declared_blocks(lines: list[str], blocks: list[int]) -> set[int]:
    """Which blocks own an assumption, matched against the block's **joined text**.

    Never per line. This corpus's markdown is reflowed by a formatter, so a multi-word idiom lands
    wherever the wrap falls — and a phrase split across two lines is invisible to a per-line search
    while reading perfectly to a human. Found on this measure's own author 2026-09-03: a sentence
    ending "(`~/.local/state/…` by" / "default)" declared the path in prose and was reported bare,
    and the same break could hit any of the phrases in `DECLARED` on any future reflow.
    """
    joined: dict[int, list[str]] = defaultdict(list)
    for line, block in zip(lines, blocks, strict=True):
        joined[block].append(line.strip())
    return {block for block, parts in joined.items() if DECLARED.search(" ".join(parts))}


def _is_owned(key: tuple[str, str], owned: set[tuple[str, str]]) -> bool:
    """Whether a reference is covered by a declaration — for a path, by one of its **prefixes** too.

    A skill that says what `~/.local/state` is has told its reader about
    `~/.local/state/<skill>/<file>.json`; requiring the declaration to name the leaf reports the
    same assumption once per filename. Found on this measure's own author 2026-09-03: declaring the
    state directory in one sentence left the very next line's fuller path counted as bare.

    Only for path kinds. An env var or a repo name has no prefix relation — `$PLANS_HOME` says
    nothing about `$PLANS_SENSITIVE_HOME`, and treating one as covering the other would hide exactly
    the pair a reader needs told apart.
    """
    kind, token = key
    if key in owned:
        return True
    if kind not in ("home-path", "abs-path"):
        return False
    return any(k == kind and token.startswith(f"{t}/") for k, t in owned)


def scan_portability(skills: list[Skill], extra_repos: list[str] | None = None) -> dict[str, Any]:
    """What a `SKILL.md` assumes its reader's machine already has, and whether it admits to it.

    A skill is installed by strangers. The reader has none of the author's repos, none of the
    author's dotfiles, and no task whose name the author invented — so every reference a skill makes
    outside itself is either something the reader can satisfy or a dead end that reads as an
    instruction. The repo rule this measures: where a skill genuinely needs an environment
    assumption, it must say so in the skill rather than failing mysteriously.

    So the finding is never "this skill names the author's repo". Evidence is supposed to name real
    things — "confirmed 2026-08-24 in <repo>" is honest and a stranger loses nothing by it. The
    finding is an assumption stated as **fact**: a pointer to a document only the author can open, a
    command whose task only the author's repos define, a `$VAR` nobody was told to set. Each
    reference is therefore `declared` or `bare`, decided by whether its own block owns the
    assumption in the corpus's existing idiom ("on this author's machine", "or the repo's
    equivalent", "if you have one"), and only the bare ones are findings.
    """
    owner, repos = author_vocabulary(skills, extra_repos)
    pattern = re.compile(r"(?<![\w/-])(" + "|".join(re.escape(r) for r in repos) + r")(?![\w-])") if repos else None
    rows: list[dict[str, Any]] = []
    for skill in skills:
        lines = (skill.path / "SKILL.md").read_text(encoding="utf-8", errors="replace").splitlines()
        blocks = _blocks_by_line(lines)
        declared_blocks = _declared_blocks(lines, blocks)
        hits: list[dict[str, Any]] = []
        in_fence = False
        for index, line in enumerate(lines):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            for kind, token in _references(line, in_fence, pattern, skill.name):
                hits.append({
                    "kind": kind,
                    "token": token,
                    "line": index + 1,
                    "where": "fence" if in_fence else "prose",
                    "declared": blocks[index] in declared_blocks,
                    "text": line.strip()[:160],
                })  # fmt: skip
        # The description is what the harness shows every session and has no block around it to
        # carry a declaration, so it can only ever inherit one from the body.
        hits.extend(
            {"kind": kind, "token": token, "line": 0, "where": "description", "declared": False, "text": "(desc)"}
            for kind, token in _references(skill.description, False, pattern, skill.name)
        )
        # Declaration is per *token*, file-wide, not per block. A skill that says once what
        # `$RESEARCH_HOME` is has told its reader; requiring the hedge beside every later mention
        # marked a correctly-written skill as six findings and is how a measure gets switched off.
        owned = {(h["kind"], h["token"]) for h in hits if h["declared"]}
        refs: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for hit in hits:
            key = (hit["kind"], hit["token"])
            if key in seen:
                continue
            seen.add(key)
            refs.append({**hit, "status": "declared" if _is_owned(key, owned) else "bare"})
        bare = [r for r in refs if r["status"] == "bare"]
        rows.append({
            "skill": skill.name,
            "refs": len(refs),
            "bare": len(bare),
            "in_fence": sum(1 for r in bare if r["where"] == "fence"),
            "declared": len(refs) - len(bare),
            "kinds": dict(Counter(r["kind"] for r in bare).most_common()),
            "samples": bare,
        })  # fmt: skip
    rows.sort(key=lambda r: (-int(r["bare"]), r["skill"]))
    return {"author": owner, "author_repos": repos, "skills": rows}


def scan_absorbable(min_sessions: int = 2) -> list[dict[str, Any]]:
    """Recurring throwaway Python: the agent solving the same problem again instead of reaching
    for a script.

    Clusters on the *import set* rather than on the command string or on edit distance. The command
    string is useless — every call normalises to `python3 -c S` because the payload is quoted — and
    exact AST shape over-splits, producing mostly singletons. The import set survives renaming and
    reformatting, and produced legible clusters on the first run.
    """
    clusters: dict[frozenset[str], list[tuple[str, str, str]]] = defaultdict(list)
    if not TRANSCRIPTS.exists():
        return []
    for path in TRANSCRIPTS.rglob("*.jsonl"):
        project = path.parent.name
        for _obj, b in _blocks(path):
            if b.get("type") != "tool_use" or b.get("name") != "Bash":
                continue
            src = _payload(str((b.get("input") or {}).get("command") or ""))
            if not src or len(src) < 20:
                continue
            mods = _imports(src)
            if mods:
                clusters[mods].append((project, path.stem, src))

    rows: list[dict[str, Any]] = []
    for mods, hits in clusters.items():
        sessions = {s for _, s, _ in hits}
        if len(sessions) < min_sessions:
            continue
        shapes = Counter(_shape(src) for _, _, src in hits)
        rows.append(
            {
                "imports": sorted(mods),
                "calls": len(hits),
                "sessions": len(sessions),
                "projects": len({p for p, _, _ in hits}),
                "distinct_shapes": len(shapes),
                "example": min((src for _, _, src in hits), key=len).strip()[:200],
            }
        )
    rows.sort(key=lambda r: (-int(r["sessions"]), -int(r["calls"])))
    return rows


# --------------------------------------------------------------------------------------------
# Reporting


def listing_budget(context_tokens: int) -> int:
    """Characters, not tokens: `context_window * 4 * fraction`, or an absolute env override.

    Both halves matter. The fraction is 1% *of the window in tokens*, converted at 4 characters
    per token — so the budget is model-dependent, and the same corpus can be over budget on one
    model and comfortable on another. Measured 2026-08-31 on CLI 2.1.251: a 15,486-character
    listing drew the overflow warning on a 200k-window model (budget 8,000) and no warning at all
    on the session's own larger-window model.
    """
    override = os.environ.get(BUDGET_ENV, "").strip()
    if override.isdigit() and int(override) > 0:
        return int(override)
    return max(1, int(context_tokens * BUDGET_CHARS_PER_TOKEN * BUDGET_FRACTION))


def harness_priority(state: Path = HARNESS_STATE, now: float | None = None) -> dict[str, float]:
    """The harness's own ranking, which is not the invocation count.

    Claude Code keeps a `skillUsage` map in `~/.claude.json` and scores each skill
    `usageCount * max(0.5 ** (days_since_last_use / 7), 0.1)`. So recency dominates: a skill used
    thirty times two months ago scores 3, below one used four times yesterday. This is the order
    descriptions are kept in when the listing overflows, so it is the order this table sorts by —
    the transcript counts answer a different question (which mechanism invoked it).

    Returns an empty map when the file is absent, which is the case on any other harness.
    """
    try:
        blob = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = blob.get("skillUsage")
    if not isinstance(entries, dict):
        return {}
    stamp = (now if now is not None else time.time()) * 1000
    scores: dict[str, float] = {}
    for name, rec in entries.items():
        if not isinstance(rec, dict):
            continue
        count = rec.get("usageCount") or 0
        last = rec.get("lastUsedAt") or 0
        days = max(0.0, (stamp - last) / 86_400_000)
        decay = max(USAGE_DECAY_FLOOR, 0.5 ** (days / USAGE_HALF_LIFE_DAYS))
        scores[name] = round(count * decay, 3)
    return scores


def simulate_listing(
    skills: list[Skill],
    priority: dict[str, float],
    budget: int,
    exempt_chars: int = 0,
    exempt_count: int = 0,
) -> dict[str, Any]:
    """Which of *these* skills lose their descriptions, replicating the harness's own greedy pass.

    Two properties of that pass are easy to get wrong and both change the answer:

    - **Bundled skills are exempt.** They are charged against the budget first and always keep
      their full descriptions; only user and project skills are candidates for demotion. So the
      cost of the harness's own skills is not shared pain — it is subtracted from what is left for
      yours.
    - **It is a greedy fit, not a cut-off.** Entries are walked in descending priority and each
      keeps its description if the remaining room allows, so a long description can be dropped
      while a shorter, *lower*-priority one is kept. The demoted set is not a suffix of the order.
    """
    n = exempt_count + len(skills)
    gaps = max(0, n - 1)
    total = exempt_chars + sum(s.entry_chars for s in skills) + gaps
    if total <= budget:
        return {"mode": "fits", "total_chars": total, "budget": budget, "demoted": []}

    floor = exempt_chars + sum(s.name_only_chars for s in skills) + gaps
    room = budget - floor
    demoted: list[str] = []
    for s in sorted(skills, key=lambda s: (-priority.get(s.name, 0.0), s.name)):
        extra = s.entry_chars - s.name_only_chars
        if extra <= room:
            room -= extra
        else:
            demoted.append(s.name)
    return {
        "mode": "priority",
        "total_chars": total,
        "budget": budget,
        "name_only_floor": floor,
        "demoted": sorted(demoted),
    }


def exempt_from_observed(listings: list[Listing], skills: list[Skill]) -> tuple[int, int, str]:
    """Price the entries this tool cannot see, from the largest listing the harness actually sent.

    The harness's own entries are compiled into the CLI binary rather than sitting on disk, so no
    file-based inventory can price them — and without them the budget total is wrong in the
    optimistic direction. Subtracting the installed skills' cost from a real listing leaves exactly
    that remainder, at no cost and with no probe.

    A **live probe used to do this job and was removed on 2026-08-31.** It ran `claude -p` with the
    budget forced to 1 so the CLI would log its real listing size. It worked, and it was worse than
    this in three ways at once: it was the only part of `fitness.py` that spent tokens; it ran
    headless, where fewer entries are listed, so it under-reported the interactive listing by about
    2,600 characters and would have talked someone into a budget setting that does not fit; and its
    own runs entered the transcript store as truncated listings, so the tool contaminated the corpus
    it reads every time it was used. Reading a listing a real session already produced has none of
    those properties. Do not reintroduce it.

    Reference is the largest **untruncated** listing from a real session: untruncated so every entry
    carries its full description, largest so conditional entries a smaller session lacked are
    included. Returns `(chars, count, source)`.
    """
    candidates = [x for x in listings if not x.transient and not x.demoted]
    if not candidates:
        return 0, 0, "no untruncated listing recorded"
    ref = max(candidates, key=lambda x: x.chars)
    listed = [s for s in skills if s.name in set(ref.names)]
    chars = ref.chars - sum(s.entry_chars for s in listed) - max(0, ref.count - 1)
    count = ref.count - len(listed)
    if chars < 0 or count < 0:
        # Descriptions have been edited since that listing was sent, so the subtraction is stale.
        return 0, 0, f"the listing of {ref.date} no longer matches the installed descriptions"
    return chars, count, f"{ref.chars} chars over {ref.count} entries, sent {ref.date}"


def budget_rows(skills: list[Skill], usage: Usage, priority: dict[str, float]) -> list[dict[str, Any]]:
    """Listing cost per skill, ordered by who loses their description first.

    When the listing overflows, Claude Code demotes user skills to name-only in ascending order of
    the decayed-usage priority above. That is self-reinforcing: no invocations, so the description
    goes, so the skill cannot be matched, so it stays at zero.
    """
    rows: list[dict[str, Any]] = []
    for s in skills:
        total = usage.tool_calls[s.name] + usage.explicit[s.name]
        rows.append(
            {
                "skill": s.name,
                "listing_chars": s.entry_chars,
                "priority": priority.get(s.name, 0.0),
                "over_spec_cap": max(0, len(s.description) - SPEC_DESC_CAP),
                "over_listing_cap": max(0, len(s.listing_text) - LISTING_ENTRY_CAP),
                "invocations": total,
                "auto": usage.tool_calls[s.name],
                "explicit": usage.explicit[s.name],
                "last_seen": usage.last_seen.get(s.name, "never"),
            }
        )
    rows.sort(key=lambda r: (float(r["priority"]), -int(r["listing_chars"])))
    return rows


def _print_table(rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        print("  (nothing)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    print("  " + "  ".join(c.ljust(widths[c]) for c in columns))
    print("  " + "  ".join("-" * widths[c] for c in columns))
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


def observed_summary(listings: list[Listing]) -> dict[str, Any]:
    """Roll up the listings the harness actually sent, keeping probe traffic countable."""
    truncated = [listing for listing in listings if listing.demoted]
    seen: Counter[str] = Counter()
    last: dict[str, str] = {}
    for listing in truncated:
        for name in listing.demoted:
            seen[name] += 1
            last[name] = max(last.get(name, ""), listing.date)
    return {
        "listings": len(listings),
        "from_real_sessions": sum(1 for listing in listings if not listing.transient),
        "largest_chars": max((listing.chars for listing in listings), default=0),
        "largest_count": max((listing.count for listing in listings), default=0),
        "truncated_listings": len(truncated),
        "truncated_real": sum(1 for listing in truncated if not listing.transient),
        "demoted": [{"skill": name, "listings": n, "last": last[name]} for name, n in seen.most_common()],
    }


def collect_budget(skills: list[Skill], usage: Usage, args: argparse.Namespace) -> dict[str, Any]:
    """The budget section: what the listing costs, who is forecast to lose a description, and
    what the harness has actually been sending."""
    priority = harness_priority()
    rows = budget_rows(skills, usage, priority)
    own_chars = sum(int(r["listing_chars"]) for r in rows)
    out: dict[str, Any] = {
        "budget": rows,
        "priority_source": "~/.claude.json skillUsage" if priority else "unavailable",
        "listing_own_chars": own_chars,
    }

    listings = scan_listings()
    exempt_chars, exempt_count, source = exempt_from_observed(listings, skills)
    out["listing_exempt_chars"] = exempt_chars
    out["listing_exempt_source"] = source
    out["simulation"] = simulate_listing(
        skills, priority, listing_budget(args.context_window), exempt_chars, exempt_count
    )
    out["observed"] = observed_summary(listings)
    out["observed"]["store_present"] = TRANSCRIPTS.exists()
    out["usage_available"] = usage.available
    return out


def materialize_ref(ref: str, cwd: Path, into: Path) -> tuple[Path, str]:
    """Extract a git ref's `skills/` into a directory, so a corpus nobody has installed can be read.

    This exists because `origin/main` is the **product** — `skills add <owner>/<repo>` clones the
    remote — and nothing here could measure it. Every count this tool has ever printed described the
    working tree or the install, so no number was ever a statement about what a reader has.

    It never fetches. Every script in this corpus is read-only, stdlib and network-free, and a
    silent fetch would trade that property for a convenience. Instead the sha and the age of the
    last fetch are returned for the header to print, and the reader decides whether that is fresh
    enough — the same shape as reporting a drift rather than gating on it. There is deliberately no
    staleness threshold: a threshold is a number nobody can defend, and it turns a plain fact into a
    policy argument.
    """
    sha = _git(["rev-parse", "--short", ref], cwd)
    if sha is None:
        raise SystemExit(
            f"no such ref: {ref}\n"
            "  --ref reads a local ref, and never fetches. If it is a remote-tracking ref you have\n"
            "  never fetched, run `git fetch` first — that is your call to make, not this script's."
        )
    into.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", ref, "skills"],
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        raise SystemExit(f"git archive {ref} skills failed: {archive.stderr.decode(errors='replace').strip()}")
    subprocess.run(["tar", "-x", "-C", str(into)], input=archive.stdout, check=True)
    return into / "skills", f"{ref} @ {sha}, {_fetch_age(cwd)}"


def _git(argv: list[str], cwd: Path) -> str | None:
    done = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def _fetch_age(cwd: Path) -> str:
    """How stale the remote-tracking refs are, in the words a reader can act on.

    `FETCH_HEAD`'s mtime is when the last fetch ran. A remote-tracking ref answers "what did I last
    fetch", never "what does the remote have" — so a run against `origin/main` describes the product
    only as of this moment.
    """
    common = _git(["rev-parse", "--git-common-dir"], cwd)
    if common is None:
        return "fetch age unknown"
    head = (cwd / common / "FETCH_HEAD").resolve()
    if not head.exists():
        return "never fetched in this clone"
    hours = (time.time() - head.stat().st_mtime) / 3600
    return f"fetched {hours:.0f}h ago" if hours >= 1 else "fetched under an hour ago"


def resolve_roots(explicit: list[Path] | None, cwd: Path) -> list[Path]:
    """Which directories to load skills from, in the order that decides which copy wins.

    Order is the whole of this function, because `load_skills` is first-occurrence-wins. A skills
    repo's own `skills/` goes **first**, not appended: appending made a bare run inside a checkout
    measure the *installed* copies and silently ignore the working tree. Measured 2026-09-03 in this
    repo — `plan-docs` reported at 1025 body lines from the hub while the tree held 1039, with only
    `inventory`'s stale-copy line hinting at it and every other subcommand showing nothing at all.

    Standing in a skills repo is an unambiguous statement about which corpus you mean.
    """
    if explicit:
        return list(explicit)
    roots = [r for r in DEFAULT_SCOPES if r.exists()]
    repo_skills = cwd / "skills"
    return [repo_skills, *roots] if repo_skills.is_dir() else roots


def describe_corpus(skills: list[Skill], args: argparse.Namespace) -> dict[str, str]:
    """Which population this run is measuring, so the number in the output means something.

    A count is a statement about a specific set of files, and this tool can be pointed at four that
    routinely disagree: the working tree, `origin`, the install hub, and an arbitrary `--root`.
    Measured on the author's machine 2026-09-03 with a clean tree and nothing unusual happening,
    three of them differed. A report that does not say which it read is a number whose meaning
    changes depending on whether its author had pushed.

    The `installed` case carries the extra sentence, because that is the one where the reader can
    act on nothing: a deployed copy is not theirs to edit.
    """
    roots = sorted({s.scope for s in skills})
    hub = {str(p.resolve()) for p in DEFAULT_SCOPES if p.exists()}
    if getattr(args, "ref_label", None):
        return {"kind": "git ref", "where": args.ref_label, "note": "what `skills add` would install"}
    if args.root:
        return {"kind": "explicit", "where": ", ".join(roots), "note": ""}
    if roots and set(roots) <= hub:
        return {
            "kind": "installed",
            "where": ", ".join(roots),
            "note": "deployed copies — not yours to edit; a fix belongs to the skill's author",
        }
    return {"kind": "working tree", "where": ", ".join(roots), "note": ""}


def collect(want: str, skills: list[Skill], args: argparse.Namespace) -> tuple[dict[str, Any], Usage]:
    """Everything the requested sections need, gathered before anything is printed.

    **`report` runs the installer-side sections only.** `inventory`, `budget` and `usage` have
    remedies belonging to whoever ran the command — refresh a stale copy, uninstall something,
    accept the listing cost. `overlap`, `absorb`, `derivable` and `portability` do not: every one of
    them ends in "edit the skill", which a reader who installed it must not do, since editing a
    deployed copy is drift that reaches nothing.

    So those four have to be named on the command line. The split is deliberately a property of the
    **command** rather than of whichever corpus is in front of it: a rule that inspected the roots
    would behave differently on the author's machine, where the hub and the checkout hold the same
    names, than on every other machine — and that is precisely the class of bug this rule exists to
    prevent, so it must not be implemented in a way that depends on it.
    """
    out: dict[str, Any] = {
        "generated": datetime.now(tz=UTC).date().isoformat(),
        "roots": sorted({s.scope for s in skills}),
        "corpus": describe_corpus(skills, args),
    }
    usage = Usage()

    if want in ("inventory", "report"):
        out["inventory"] = [
            {
                "skill": s.name,
                "desc_chars": len(s.description),
                "body_lines": s.body_lines,
                "scripts": s.has_scripts,
                "refs": s.has_references,
                "evals": s.has_evals,
                "scope": s.scope,
            }
            for s in skills
        ]
        out["stale_copies"] = [
            {"name": n, "read_from": a, "differs_in": b} for n, a, b in getattr(load_skills, "stale", [])
        ]

    if want in ("usage", "budget", "report"):
        usage = scan_usage(exclude=set(args.exclude))
        out["usage"] = {
            "transcripts": usage.sessions,
            "note": "auto = Skill tool_use; explicit = a typed /name, which often bypasses the tool",
        }

    if want in ("budget", "report"):
        out.update(collect_budget(skills, usage, args))

    if want == "overlap":
        pairs, stats = overlap_pairs(skills)
        out["overlap"] = pairs[: args.top]
        out["overlap_corpus_stats"] = stats
        out["ubiquitous_terms"] = getattr(idf, "ubiquitous", [])

    if want == "derivable":
        out["derivable"] = scan_derivable(skills)
        if args.compare:
            out["derivable_drift"] = compare_derivable(out["derivable"], Path(args.compare))

    if want == "portability":
        out["portability"] = scan_portability(skills, args.author_repo)

    if want == "absorb":
        out["absorbable"] = scan_absorbable()[: args.top]

    return out, usage


def save_derivable_baseline(rows: list[dict[str, Any]], path: Path) -> None:
    payload = {
        "saved": datetime.now(tz=UTC).date().isoformat(),
        "skills": {str(r["skill"]): {"derivable": r["derivable"], "delegated": r["delegated"]} for r in rows},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def compare_derivable(rows: list[dict[str, Any]], baseline_path: Path) -> dict[str, Any]:
    """Drift, which is the whole point of storing a baseline.

    A count is only evidence about one moment; the question the user asked is whether a skill drifts
    back toward prose *after a series of improvements*, and nothing answers that without a stored
    previous run. A rise is the finding. A fall is not automatically progress — a skill can shed
    command lines by being cut — so it is reported and not celebrated.
    """
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    before: dict[str, Any] = baseline.get("skills", {})
    deltas: list[dict[str, Any]] = []
    for row in rows:
        was = before.get(str(row["skill"]))
        if was is None:
            deltas.append({"skill": row["skill"], "derivable": row["derivable"], "verdict": "new"})
            continue
        delta = int(row["derivable"]) - int(was["derivable"])
        deltas.append({
            "skill": row["skill"],
            "was": was["derivable"],
            "derivable": row["derivable"],
            "delta": delta,
            "verdict": "DRIFTED" if delta > 0 else ("improved" if delta < 0 else "unchanged"),
        })  # fmt: skip
    gone = sorted(set(before) - {str(r["skill"]) for r in rows})
    return {"baseline": baseline.get("saved"), "skills": deltas, "no_longer_present": gone}


def _render_overlap(out: dict[str, Any], top: int) -> None:
    stats = out["overlap_corpus_stats"]
    print(f"\n## trigger overlap — top {min(top, len(out['overlap']))} pairs, ranked, not gated")
    if stats:
        print(
            f"  shadowing flagged above {stats['shadow_cut']} coverage "
            f"(corpus mean {stats['coverage_mean']}, sd {stats['coverage_sd']})"
        )
    if out["ubiquitous_terms"]:
        print(f"  dropped as corpus-ubiquitous: {', '.join(out['ubiquitous_terms'])}")
    for r in out["overlap"]:
        flag = f"  [{r['shadows']}]" if r.get("shadows") else ""
        print(
            f"\n  {r['a']} <-> {r['b']}   sim={r['similarity']}  "
            f"{r['a']}->{r['b']}={r['a_covers_b']}  {r['b']}->{r['a']}={r['b_covers_a']}{flag}"
        )
        print(f"    shared ({r['shared_count']}): {', '.join(r['shared_terms'])}")


def _render_usage(skills: list[Skill], usage: Usage) -> None:
    if not usage.available:
        print("\n## usage — unavailable, not zero")
        print(f"  no transcript store at {TRANSCRIPTS}. This section reads Claude Code's own")
        print("  transcripts; on another harness there is nothing to count, which is not the same")
        print("  finding as a corpus of skills nobody invoked.")
        return
    print(f"\n## usage across {usage.sessions} transcripts")
    rows = [
        {
            "skill": s.name,
            "auto": usage.tool_calls[s.name],
            "explicit": usage.explicit[s.name],
            "total": usage.tool_calls[s.name] + usage.explicit[s.name],
            "last_seen": usage.last_seen.get(s.name, "never"),
        }
        for s in skills
    ]
    rows.sort(key=lambda r: -int(r["total"]))
    _print_table(rows, ["skill", "auto", "explicit", "total", "last_seen"])
    print("\n  A zero is not a verdict. It means either the request came up and this skill lost it,")
    print("  or the request never came up — opposite problems, and this table cannot tell them")
    print("  apart. Write a few trigger cases in the words a request would use and run trigger.py.")


def _render_budget(out: dict[str, Any], args: argparse.Namespace) -> None:
    sim = out["simulation"]
    own, exempt = out["listing_own_chars"], out["listing_exempt_chars"]
    print(f"\n## listing budget — {own} chars for these skills")
    if exempt:
        print(f"  plus {exempt} chars the harness lists and this tool cannot see, charged first")
        print(f"  from a listing it really sent: {out['listing_exempt_source']}")
    else:
        print(f"  the harness's own entries are not counted here ({out['listing_exempt_source']}),")
        print("  so this total is a floor rather than the listing.")
    print(f"  budget at a {args.context_window}-token window: {sim['budget']} chars — {sim['mode']}")
    if sim["demoted"]:
        label = "would lose a description" if out["priority_source"] == "unavailable" else "demoted to name-only"
        print(f"  {label}: {', '.join(sim['demoted'])}")
    columns = ["skill", "listing_chars", "over_spec_cap"]
    if out["priority_source"] == "unavailable":
        # Without the harness's usage map every skill scores 0, so any demotion list is an artefact
        # of tie-breaking rather than a forecast. Say that instead of printing a confident order.
        print("  priority: unavailable — no ~/.claude.json, so every skill scores 0. The table")
        print("  below falls back to largest-first and the set named above to alphabetical")
        print("  tie-breaking; neither is a forecast of who actually loses a description.")
    else:
        print(f"  priority: {out['priority_source']} (usageCount, 7-day half-life, floor 0.1)")
        print("  ordered by who loses their description first when the listing overflows")
        columns.insert(2, "priority")
    if out["usage_available"]:
        columns += ["auto", "explicit", "last_seen"]
    else:
        print(f"  invocation columns omitted: no transcript store at {TRANSCRIPTS}")
    _print_table(out["budget"], columns)
    _render_observed(out["observed"])


def _render_observed(obs: dict[str, Any]) -> None:
    """What was actually sent, which outranks the simulation above whenever the two disagree."""
    if not obs.get("store_present"):
        print("\n## listings actually sent — unavailable, not zero")
        print(f"  no transcript store at {TRANSCRIPTS}; this is a Claude Code artefact")
        return
    print(f"\n## listings actually sent — {obs['listings']} observed, {obs['from_real_sessions']} from real sessions")
    if not obs["listings"]:
        print("  store present but nothing recorded; the harness keeps these only on recent CLI versions")
        return
    print(f"  largest: {obs['largest_chars']} chars over {obs['largest_count']} entries")
    if not obs["truncated_listings"]:
        print("  no listing was ever truncated here — the simulation above is a forecast, not a record")
        return
    print(
        f"  truncated: {obs['truncated_listings']} listing(s), "
        f"{obs['truncated_real']} of them from real sessions rather than a probe"
    )
    print("  skills observed listed as a bare name, with no description to be matched on:")
    _print_table(obs["demoted"], ["skill", "listings", "last"])


def _render_derivable(out: dict[str, Any], top: int) -> None:
    rows: list[dict[str, Any]] = out["derivable"]
    print("\n## derivable work — commands a skill asks an agent to compose, that code could carry")
    print("  delegated = calls the skill's own (or a sibling's) script. derivable = assembled per run.")
    print("  A fixed literal with no variable parts is neither, and is not a finding.")
    _print_table(rows, ["skill", "commands", "delegated", "derivable", "has_scripts"])
    for row in rows[:top]:
        if not row["derivable"]:
            continue
        kinds = ", ".join(f"{k}={v}" for k, v in row["kinds"].items())
        note = "no scripts/ at all" if not row["has_scripts"] else "has a script that does not carry these"
        print(f"\n  {row['skill']}: {row['derivable']} derivable ({kinds}) — {note}")
        for sample in row["samples"][:4]:
            print(f"    {sample['command'][:150]}")
    print("\n  Read the samples before acting on the count. Legitimate residue: an external CLI's own")
    print("  documented one-liner, a one-off emergency procedure, the repo command a script must not")
    print("  hard-code. Drift: a composed pipeline, a query, a parse, a multi-step sequence.")

    drift = out.get("derivable_drift")
    if not drift:
        print("\n  No baseline compared. --save-baseline <path> now, --compare <path> later: a single")
        print("  run says what is true today, and the question is whether a skill drifts back.")
        return
    print(f"\n## drift vs baseline {drift['baseline']}")
    for row in drift["skills"]:
        if row["verdict"] in ("unchanged", "new") and not row.get("derivable"):
            continue
        was = row.get("was", "-")
        print(f"  {row['skill']:28} {was} -> {row['derivable']:<4} {row['verdict']}")
    for name in drift["no_longer_present"]:
        print(f"  {name:28} in the baseline, not in this corpus")


def _render_portability(out: dict[str, Any], top: int) -> None:
    data = out["portability"]
    print("\n## portability — what a SKILL.md assumes about the machine reading it")
    print('  bare = stated as fact. declared = the block owns it ("on this author\'s machine", ...).')
    print("  Naming the author's repo as *evidence* is fine and portable; naming it as a place the")
    print("  reader should go and read something is a dead end. The status column is that difference.")
    if data["author_repos"]:
        print(f"\n  author repos, derived from the corpus's own links: {', '.join(data['author_repos'])}")
    else:
        print("\n  no `skills add <owner>/<repo>` line in this corpus — author-repo references unmeasured")
    _print_table(data["skills"], ["skill", "refs", "bare", "in_fence", "declared"])
    print("\n  in_fence is the sharper half: a bare assumption inside a fenced block is a command the")
    print("  reader is being told to run. The same token in prose may be a quotation of evidence.")
    for row in data["skills"][:top]:
        if not row["bare"]:
            continue
        kinds = ", ".join(f"{k}={v}" for k, v in row["kinds"].items())
        print(f"\n  {row['skill']}: {row['bare']} bare ({kinds})")
        for sample in row["samples"][:6]:
            print(f"    L{sample['line']:<4} {sample['where']:<11} {sample['kind']:<12} {sample['token']}")
            print(f"           {sample['text']}")


def _render_absorbable(out: dict[str, Any]) -> None:
    print("\n## absorbable one-liners — recurring ad-hoc python, candidates for skill code")
    print("  read `shapes` first: it is the count of distinct payloads, and a cluster whose shape")
    print("  count approaches its call count is one import set, not one repeated script.")
    for r in out["absorbable"]:
        shapes, calls = int(r["distinct_shapes"]), int(r["calls"])
        verdict = "one script" if shapes * 4 <= calls else ("mixed" if shapes * 2 <= calls else "NOT a repetition")
        print(
            f"\n  {calls:4d} calls / {r['sessions']} sessions / {r['projects']} projects / "
            f"{shapes} shapes  [{verdict}]   imports: {', '.join(r['imports'])}"
        )
        print(f"    {r['example'][:160]}")


def _render_inventory(out: dict[str, Any], count: int) -> None:
    print(f"\n## inventory ({count} skills)")
    _print_table(out["inventory"], ["skill", "desc_chars", "body_lines", "scripts", "refs", "evals"])
    if out["stale_copies"]:
        print("\n  same name, different content — one copy is stale, and only one is loaded:")
        for c in out["stale_copies"]:
            print(f"    {c['name']}: loaded from {c['read_from']}, differs in {c['differs_in']}")


def render(out: dict[str, Any], skills: list[Skill], usage: Usage, args: argparse.Namespace) -> None:
    """Sections print in reading order, and only the ones `collect` gathered."""
    print(f"# skill fitness — {out['generated']}")
    corpus = out["corpus"]
    print(f"  corpus: {corpus['kind']} — {corpus['where']}")
    if corpus["note"]:
        print(f"          {corpus['note']}")

    sections: list[tuple[str, Any]] = [
        ("inventory", lambda: _render_inventory(out, len(skills))),
        ("budget", lambda: _render_budget(out, args)),
        ("overlap", lambda: _render_overlap(out, args.top)),
        ("derivable", lambda: _render_derivable(out, args.top)),
        ("portability", lambda: _render_portability(out, args.top)),
        ("absorbable", lambda: _render_absorbable(out)),
    ]
    # `usage` is collected for `budget` too, where its own section would be noise; only the
    # subcommand that asked for it prints it.
    if "usage" in out and args.command == "usage":
        _render_usage(skills, usage)
    for key, draw in sections:
        if key in out:
            draw()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "command",
        choices=["inventory", "budget", "overlap", "usage", "absorb", "derivable", "portability", "report"],
    )
    p.add_argument(
        "--author-repo",
        action="append",
        default=[],
        help="a repo of the author's the corpus never links, so portability can see it named in prose",
    )
    p.add_argument("--root", action="append", type=Path, help="a skills directory; repeatable")
    p.add_argument(
        "--ref",
        help="measure a git ref's skills/ instead — e.g. origin/main, what `skills add` installs. "
        "Never fetches: the sha and the age of your last fetch are printed for you to judge",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=12, help="rows to show in ranked sections")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="skill name to ignore in usage counts, e.g. a synthetic probe this tool created",
    )
    p.add_argument(
        "--context-window",
        type=int,
        default=DEFAULT_CONTEXT_TOKENS,
        help="tokens in the model's context window; the listing budget is 1%% of it, times 4 chars",
    )
    p.add_argument(
        "--compare",
        type=Path,
        help="a derivable baseline JSON to diff against; a rise in a skill's derivable count is the finding",
    )
    p.add_argument(
        "--save-baseline",
        type=Path,
        help="write this run's per-skill derivable counts, so a later run can measure drift",
    )
    args = p.parse_args()
    args.ref_label = ""

    with tempfile.TemporaryDirectory(prefix="fitness-ref-") as scratch:
        if args.ref:
            root, args.ref_label = materialize_ref(args.ref, Path.cwd(), Path(scratch))
            args.root = [root]
        return _run(args)


def _run(args: argparse.Namespace) -> int:
    roots = resolve_roots(args.root, Path.cwd())
    skills = load_skills(roots)

    if not skills:
        print(f"no skills found under: {', '.join(str(r) for r in roots)}", file=sys.stderr)
        return 2

    out, usage = collect(args.command, skills, args)

    if args.save_baseline and "derivable" in out:
        save_derivable_baseline(out["derivable"], args.save_baseline)
        print(f"# derivable baseline written to {args.save_baseline}", file=sys.stderr)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    render(out, skills, usage, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
