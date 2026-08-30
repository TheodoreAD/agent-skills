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
import re
import shlex
import sys
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
LISTING_ENTRY_CAP = 1536

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

TRIGGER_LEAD = re.compile(r"\buse (?:this skill )?when\b", re.IGNORECASE)
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
        """What the harness puts in the listing: description plus when_to_use, if present."""
        return " ".join(x for x in (self.description, self.when_to_use) if x)

    @property
    def trigger_text(self) -> str:
        """The 'when to use it' half, which is the only half that decides selection.

        Falls back to the whole description when no lead-in is present, because that is what a
        consumer's skill will often look like, and reporting nothing would be worse than reporting
        a noisier set.
        """
        m = TRIGGER_LEAD.search(self.description)
        return self.description[m.start() :] if m else self.description

    def terms(self) -> set[str]:
        text = self.trigger_text
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

    On a ten-document corpus the IDF is still noisy, which is one reason the output is a ranked
    list and never a pass/fail threshold.
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


def budget_rows(skills: list[Skill], usage: Usage) -> list[dict[str, Any]]:
    """Listing cost per skill, ordered by who loses their description first.

    Claude Code shortens descriptions starting with the least-invoked skill when the listing
    overflows its budget. That makes a never-triggered skill self-reinforcing: no invocations, so
    its description is dropped first, so it cannot be matched, so it stays at zero.
    """
    rows: list[dict[str, Any]] = []
    for s in skills:
        total = usage.tool_calls[s.name] + usage.explicit[s.name]
        rows.append(
            {
                "skill": s.name,
                "listing_chars": len(s.listing_text) + len(s.name),
                "over_spec_cap": max(0, len(s.description) - SPEC_DESC_CAP),
                "over_listing_cap": max(0, len(s.listing_text) - LISTING_ENTRY_CAP),
                "invocations": total,
                "auto": usage.tool_calls[s.name],
                "explicit": usage.explicit[s.name],
                "last_seen": usage.last_seen.get(s.name, "never"),
            }
        )
    rows.sort(key=lambda r: (int(r["invocations"]), -int(r["listing_chars"])))
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
        rows = budget_rows(skills, usage)
        out["budget"] = rows
        out["listing_total_chars"] = sum(int(r["listing_chars"]) for r in rows)

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
        print(f"\n## listing budget — {out['listing_total_chars']} chars total")
        print("  ordered by who loses their description first when the listing overflows")
        columns = ["skill", "listing_chars", "over_spec_cap", "invocations", "auto", "explicit", "last_seen"]
        _print_table(out["budget"], columns)

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
