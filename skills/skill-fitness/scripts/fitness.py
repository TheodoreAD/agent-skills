#!/usr/bin/env python3
"""Measure a set of installed skills: contention, listing budget, real usage, absorbable scripts.

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
    report      all of the above, in the order a reader wants them

Every subcommand takes --json.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import sys
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
            value = " ".join(p for p in parts if p).strip()
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
# The working answer to the same question is `trigger.py`: write a handful of cases in the words a
# request would actually use and see whether the skill fires. That costs tokens and takes judgement,
# which is precisely why it works where a free heuristic did not.


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
    return out


def collect(want: str, skills: list[Skill], args: argparse.Namespace) -> tuple[dict[str, Any], Usage]:
    """Everything the requested sections need, gathered before anything is printed."""
    out: dict[str, Any] = {
        "generated": datetime.now(tz=UTC).date().isoformat(),
        "roots": sorted({s.scope for s in skills}),
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

    if want in ("overlap", "report"):
        pairs, stats = overlap_pairs(skills)
        out["overlap"] = pairs[: args.top]
        out["overlap_corpus_stats"] = stats
        out["ubiquitous_terms"] = getattr(idf, "ubiquitous", [])

    if want in ("absorb", "report"):
        out["absorbable"] = scan_absorbable()[: args.top]

    return out, usage


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
        print(f"  demoted to name-only: {', '.join(sim['demoted'])}")
    print(f"  priority: {out['priority_source']} (usageCount, 7-day half-life, floor 0.1)")
    print("  ordered by who loses their description first when the listing overflows")
    columns = ["skill", "listing_chars", "priority", "over_spec_cap", "auto", "explicit", "last_seen"]
    _print_table(out["budget"], columns)
    _render_observed(out["observed"])


def _render_observed(obs: dict[str, Any]) -> None:
    """What was actually sent, which outranks the simulation above whenever the two disagree."""
    print(f"\n## listings actually sent — {obs['listings']} observed, {obs['from_real_sessions']} from real sessions")
    if not obs["listings"]:
        print("  none recorded; the transcript store keeps these only on recent CLI versions")
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


def _render_absorbable(out: dict[str, Any]) -> None:
    print("\n## absorbable one-liners — recurring ad-hoc python, candidates for skill code")
    for r in out["absorbable"]:
        print(
            f"\n  {r['calls']:4d} calls / {r['sessions']} sessions / "
            f"{r['projects']} projects   imports: {', '.join(r['imports'])}"
        )
        print(f"    {r['example'][:160]}")


def render(out: dict[str, Any], skills: list[Skill], usage: Usage, args: argparse.Namespace) -> None:
    print(f"# skill fitness — {out['generated']}")
    for r in out["roots"]:
        print(f"  scope: {r}")

    if "inventory" in out:
        print(f"\n## inventory ({len(skills)} skills)")
        _print_table(out["inventory"], ["skill", "desc_chars", "body_lines", "scripts", "refs", "evals"])
        if out["stale_copies"]:
            print("\n  same name, different content — one copy is stale, and only one is loaded:")
            for c in out["stale_copies"]:
                print(f"    {c['name']}: loaded from {c['read_from']}, differs in {c['differs_in']}")

    if "budget" in out:
        _render_budget(out, args)

    if "overlap" in out:
        _render_overlap(out, args.top)

    if "usage" in out and args.command == "usage":
        _render_usage(skills, usage)

    if "absorbable" in out:
        _render_absorbable(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["inventory", "budget", "overlap", "usage", "absorb", "report"])
    p.add_argument("--root", action="append", type=Path, help="a skills directory; repeatable")
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
    args = p.parse_args()

    roots = args.root or [r for r in DEFAULT_SCOPES if r.exists()]
    repo_skills = Path.cwd() / "skills"
    if not args.root and repo_skills.is_dir():
        roots.append(repo_skills)
    skills = load_skills(roots)

    if not skills:
        print(f"no skills found under: {', '.join(str(r) for r in roots)}", file=sys.stderr)
        return 2

    out, usage = collect(args.command, skills, args)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    render(out, skills, usage, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
