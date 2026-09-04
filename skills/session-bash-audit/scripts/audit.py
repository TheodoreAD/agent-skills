#!/usr/bin/env python3
"""Audit recent Claude Code transcripts for Bash-tool habits that fight ~/AGENTS.md's Bash rules.

Reads every `~/.claude/projects/*/*.jsonl` (main sessions and their `subagents/` transcripts)
modified in the last N days, pulls out each Bash tool call with its result, tags it against the
PATTERNS table below, and prints per-model rates, per-session rates, samples per pattern, denied
calls, and truncation re-runs. Stdlib only; read-only; never touches the transcripts.

    python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --days 4
    python3 .../audit.py --days 7 --project repo-tasks --samples 5 --json /tmp/x/calls.json

Extending: add a row to PATTERNS (name, regex or predicate, one-line why). Keep the row's "why"
honest — the table is also the checklist SKILL.md tells the agent to reason from, so a pattern with
no stated cost teaches nothing. Record what a new pattern found in references/research.md.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# A module constant rather than an `os.name` test inside the function, so a test can pin the platform
# without patching `os` itself: `os.name` is what `pathlib` reads to decide whether `Path()` is a
# PosixPath or a WindowsPath, and patching it globally makes every path in the process unusable.
WINDOWS = os.name == "nt"


def state_dir(skill: str = "session-bash-audit") -> Path:
    """Where this skill keeps a baseline it wrote — `$XDG_STATE_HOME/<skill>/`.

    **State, not data**: the specification's own example for `$XDG_STATE_HOME` is history, and the
    test is whether losing the file costs anything (`share`) or only a re-measurement (`state`). A
    baseline is the second.

    It used to have no home at all, so the skill told readers to write it into
    `~/.agents/skills/session-bash-audit/references/baselines/` — the **installed copy**, which is
    the artefact a re-install replaces and which this corpus elsewhere calls drift to edit. The one
    piece of genuinely per-machine state here was being kept in the one place designed to be
    overwritten.

    Deliberately not a new environment variable: `$XDG_STATE_HOME` is one the user already controls,
    so using it *removes* a setting rather than adding one. Ten lines duplicated per skill rather
    than imported, because skills install individually and one cannot import another.

    `$XDG_STATE_HOME` wins on every platform, including Windows: a user who sets it means it. Only
    the *default* is per-platform, and on Windows it is `%LOCALAPPDATA%` — state is a record of what
    happened on this machine, so it is the half that must not roam. Copying three lines here is the
    same trade as the duplication above; `platformdirs` is the right library and cannot be taken,
    because these scripts run under a bare `python3` with nothing installed.
    """
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base).expanduser() / skill
    if WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / skill
    return Path.home() / ".local" / "state" / skill


HEREDOC_RE = re.compile(r"<<-?\s*['\"]?[A-Za-z_]+['\"]?")
SEPARATOR_RE = re.compile(r"&&|\|\||[;|\n]")


@dataclass
class Call:
    cmd: str
    model: str
    project: str
    session: str
    subagent: bool
    timestamp: str
    error: bool
    result: str
    tags: set[str] = field(default_factory=set)

    @property
    def denied(self) -> bool:
        low = self.result.lower()
        return self.error and ("denied" in low or "doesn't want to proceed" in low or "rejected" in low)


def strip_heredoc(cmd: str) -> str:
    """Drop heredoc bodies so their content can't look like chained commands."""
    m = HEREDOC_RE.search(cmd)
    return cmd[: m.start()] if m else cmd


QUOTED_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'[^\']*\'')


def strip_quoted(cmd: str) -> str:
    """Blank every quoted string, after the heredoc strip, so a `|` inside a regex alternation or a
    message cannot read as a shell pipe. A shell pipe is never inside quotes; a `rg -n "head|tail"`
    is a search for those words, not a truncation. Confirmed 2026-09-05: three of a session's four
    `head/tail` hits were `rg` patterns naming the tags they were being counted as."""
    return QUOTED_RE.sub('""', strip_heredoc(cmd))


def split_chain(cmd: str) -> list[str]:
    """Split on the separators Claude Code's permission engine recognizes (&&, ||, ;, |, newline),
    outside quotes. Crude on purpose — this is a habit audit, not a shell parser."""
    body = strip_heredoc(cmd)
    parts: list[str] = []
    buf = ""
    quote: str | None = None
    i = 0
    while i < len(body):
        c = body[i]
        if quote:
            buf += c
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
            buf += c
        elif body.startswith(("&&", "||"), i):
            parts.append(buf)
            buf = ""
            i += 1
        elif c in ";|\n":
            parts.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _chain_tags(cmd: str) -> set[str]:
    parts = split_chain(cmd)
    if len(parts) < 2:
        return set()
    if len(parts) == 2 and parts[0].startswith("cd ") and "&&" in strip_heredoc(cmd):
        return {"cd-and-cmd"}  # the one chain shape ~/AGENTS.md permits (cross-repo only)
    return {f"chain{min(len(parts), 5)}"}


def _cd_tag(cmd: str, project: str) -> set[str]:
    m = re.search(r"(?:^|&&|;|\n)\s*cd\s+(\S+)", strip_heredoc(cmd))
    if not m:
        return set()
    target = m.group(1).replace("~", str(Path.home())).replace("$HOME", str(Path.home())).rstrip("/")
    # Claude Code names a project directory by its absolute path with / and . turned into -.
    return {"cd-own-repo"} if target.replace("/", "-").replace(".", "-") == project else {"cd-other"}


def _git_c_tag(cmd: str, project: str) -> set[str]:
    """`git -C <path>` where <path> is the session's own repo — the directory it is already in.

    Same normalisation as _cd_tag: Claude Code slugs a project directory by its absolute path with
    `/` and `.` turned into `-`. Cross-repo `git -C` is the recommended shape and is not tagged.
    """
    m = re.search(r"\bgit\s+-C\s+(\S+)", strip_heredoc(cmd))
    if not m:
        return set()
    target = m.group(1).replace("~", str(Path.home())).replace("$HOME", str(Path.home())).rstrip("/")
    return {"git-C-own-repo"} if target.replace("/", "-").replace(".", "-") == project else set()


def short_project(project: str) -> str:
    """`-home-u-projects-github-com-personal-repo-tasks` -> `repo-tasks` (best effort)."""
    for marker in ("-github-com-personal-", "-projects-"):
        if marker in project:
            return project.split(marker, 1)[1]
    return project[-24:]


Predicate = Callable[[str], bool]


def _rx(pattern: str) -> Predicate:
    compiled = re.compile(pattern)
    return lambda cmd: bool(compiled.search(strip_heredoc(cmd)))


def _rx_pipe(pattern: str) -> Predicate:
    """A predicate about a shell pipe: matched with quoted strings blanked, see `strip_quoted`."""
    compiled = re.compile(pattern)
    return lambda cmd: bool(compiled.search(strip_quoted(cmd)))


# name -> (predicate, why it matters). Chain and cd tags are computed separately above.
PATTERNS: dict[str, tuple[Predicate, str]] = {
    "head/tail": (
        _rx_pipe(r"\|\s*(head|tail)\b"),
        "truncates tool output the harness would have kept whole; forces re-runs and hides failures",
    ),
    "exit-masked": (
        _rx_pipe(r"2>&1\s*\|\s*(tail|head|grep|rg)\b"),
        "$? after a pipe is the filter's, not the command's — a failing gate reads as clean",
    ),
    "redirect-then-filter": (
        _rx_pipe(r">\s*\S+\s+2>&1\s*;.*\|\s*(rg|grep|head|tail)\b"),
        "capture-to-log is fine; filtering the log in the same call is not — Grep/Read the log as a second call",
    ),
    "echo-exit": (
        _rx(r";\s*echo\s+[\"']?(EXIT|exit)[=: ]"),
        "reflexive `; echo EXIT=$?` — the Bash tool already reports a non-zero exit",
    ),
    "search|head": (
        _rx_pipe(r"\b(rg|grep|fd|find)\b[^|]*\|\s*head\b"),
        "turns a completeness search into a sample without saying so (count first: rg -c / wc -l)",
    ),
    "sed-n": (_rx(r"\bsed\s+-n\b"), "file view via Bash; Read(offset/limit) does it with no Bash gate"),
    "cat-view": (
        lambda cmd: bool(re.fullmatch(r"\s*(cat|head -\d+|tail -\d+)\s+[^|;&<>]+", strip_heredoc(cmd))),
        "whole-file view via Bash; Read does it with no Bash gate",
    ),
    # Three rows cover these commands and they answer three different questions. Keep them straight:
    # this one is about the *harness tool* (shelling out at all), the next two about *which CLI*.
    # Measured 2026-08-29 over 15,171 calls: aggregating them is what hid the finding, because a
    # compliant `rg` and a non-compliant `grep -r` both fired this row identically.
    "grep/find": (
        _rx(r"(?:^|&&|;|\||\n)\s*(grep|rg|find|fd)\b"),
        "searching via Bash at all; Grep/Glob have their own gate and keep the whole result",
    ),
    "grep-r-not-rg": (
        _rx(r"(?:^|&&|;|\||\n)\s*grep\s+(-\w*[rR]\w*|--recursive)\b"),
        "recursive text search with grep; rg is faster and .gitignore-aware (plain grep stays fine)",
    ),
    # `[\s\S]*` rather than `.*`: a find continued across lines with a trailing backslash is common,
    # and `.` stops at the newline, so `.*` made the negative lookahead succeed and tagged an exempt
    # command as a miss. Caught 2026-09-02 by testing the pattern before trusting its count.
    "find-not-fd": (
        _rx(r"(?:^|&&|;|\||\n)\s*find\b(?![\s\S]*\s-(exec|execdir|delete|print0|newer|mtime|size|perm|user|group)\b)"),
        "plain file lookup with find; fd is faster, .gitignore-aware, and needs no -not -path excludes",
    ),
    "find-exempt": (
        _rx(r"(?:^|&&|;|\||\n)\s*find\b(?=[\s\S]*\s-(exec|execdir|delete|print0|newer|mtime|size|perm|user|group)\b)"),
        "find doing what fd does not: acting on matches, or selecting by time/size/perm — not a miss",
    ),
    "env-prefix": (_rx(r"^\s*[A-Z_][A-Z0-9_]*=\S+\s+\S"), "leading VAR=x defeats allow-rule prefix matching"),
    "bash-c": (_rx(r"\b(bash|sh|zsh)\s+-l?c\b"), "outer bash is itself ask-gated; always prompts"),
    "heredoc": (lambda cmd: bool(HEREDOC_RE.search(cmd)), "file write via shell; Write/Edit have their own gate"),
    "sed-i": (_rx(r"\bsed\s+-i\b"), "in-place edit via shell; Edit has its own gate"),
    "python-c": (_rx(r"\bpython3?\s+-c\b"), "ad-hoc script instead of a test or a dedicated tool"),
    "label-echo": (_rx(r"echo\s+['\"]?(===|---)"), "batching several steps into one call for labelled output"),
    "git-mutating": (
        _rx(r"\bgit\s+(-C\s+\S+\s+|-c\s+\S+\s+)?(commit|push|add|reset|checkout|rebase|merge|stash|rm|mv)\b"),
        "ask-gated verb; inside a chain or behind -C/-c the prefix rule may not match",
    ),
    "git-C-mutating": (
        _rx(r"\bgit\s+(-C|-c|--git-dir\S*|--work-tree\S*)\s+\S+\s+(commit|push|add|reset|checkout|rebase|merge)\b"),
        "global option before the verb: Bash(git push:*) does not match `git -C x push`",
    ),
    "pgrep-f": (
        _rx(r"\b(pgrep|pkill)\s+(-\w*f\w*\s+)+"),
        "full-cmdline match hits the harness's own `zsh -c … eval '<cmd>'` wrapper: a false positive "
        "that reads as a real process, plus the env blob. Match the executable (pgrep -x, ps -C)",
    ),
    "shell-background": (
        _rx(r"\b(nohup|setsid|disown)\b|(?<![&|>])&\s*$"),
        "shell-level backgrounding can be killed before the command runs, and the next call then "
        "reads state as though it had: use the Bash tool's own run_in_background",
    ),
    "rg-replace": (
        _rx(r"\brg\b[^|;&\n]*?\s-[A-Za-z]*r[A-Za-z]*(?=[\s=])|\brg\b[^|;&\n]*?\s--replace\b"),
        "rg's -r is --replace, not --recursive (rg is recursive by default): `rg -rn pat path` "
        "prints every match with the matched text rewritten — plausible output that is not what the "
        "file says. Deliberate --replace exists, so read the sample before counting it a defect",
    ),
}


def classify(call: Call) -> None:
    call.tags |= _chain_tags(call.cmd)
    call.tags |= _cd_tag(call.cmd, call.project)
    call.tags |= _git_c_tag(call.cmd, call.project)
    for name, (pred, _) in PATTERNS.items():
        if pred(call.cmd):
            call.tags.add(name)
    if "git-mutating" in call.tags and any(t.startswith("chain") for t in call.tags):
        call.tags.add("git-mutating-in-chain")


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def _blocks(path: Path):
    """Yield (message, block) for every content block in a transcript, skipping unparsable lines."""
    with path.open() as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict):
                    yield obj, msg, block


def _parse_transcript(path: Path, project: str) -> list[Call]:
    subagent = "subagents" in path.parts
    pending: dict[str, Call] = {}
    results: dict[str, tuple[bool, str]] = {}
    for obj, msg, block in _blocks(path):
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            pending[block["id"]] = Call(
                cmd=block["input"].get("command", ""),
                model=msg.get("model") or "?",
                project=project,
                session=path.stem,
                subagent=subagent,
                timestamp=obj.get("timestamp") or "",
                error=False,
                result="",
            )
        elif block.get("type") == "tool_result":
            tid = block.get("tool_use_id", "")
            results[tid] = (bool(block.get("is_error")), _text(block.get("content"))[:300])
    for tid, call in pending.items():
        call.error, call.result = results.get(tid, (False, ""))
        classify(call)
    return list(pending.values())


def _job_transcript(session: str) -> Path | None:
    """The transcript a background job writes into, when `session` is that job's own id.

    A background job has two ids and they are not interchangeable: `sessionId` identifies the job,
    `resumeSessionId` / `linkScanPath` identify the transcript it appends to. Both are real, and
    `sessionId` **also names a transcript file in the same project directory** — so passing it here
    resolves successfully to a stranger's session and reports a well-formed, entirely wrong answer.

    Confirmed 2026-09-01: a harvest audited `c9a20dab-…` (the job id) instead of `9502c71c-…` (its
    transcript) and got 386 calls against the real 101, with `chain` 45% against 10% and
    `git-C-own-repo` 0% against 22% — the same headline verdict, and not one of the job's own
    commands in the file. A wrong id that names nothing errors out; one that names the wrong file
    cannot be told from a right one by reading the output, which is why this resolves it here rather
    than leaving it to the caller to remember.
    """
    state = Path.home() / ".claude" / "jobs" / session[:8] / "state.json"
    if not state.is_file():
        return None
    try:
        record = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if record.get("sessionId") != session:
        return None
    scan = record.get("linkScanPath")
    path = Path(scan).expanduser() if scan else None
    return path if path is not None and path.is_file() else None


def load_session(session: str) -> list[Call]:
    """Every Bash call from one transcript, named by session id or by path.

    The one measurement that arrives while the session can still act on it. Everything else in this
    script looks across sessions after the fact, which is right for a trend and wrong for "you are
    doing this right now" — and a session's own rule-adherence is invisible to it otherwise: not in
    the conversation's narrative, not in git, not in CI, and not in its own impression of how the
    run went.

    Confirmed 2026-08-30, which is why this exists: a session that had spent the day authoring the
    rule against piping a gate through `head`/`tail` then produced that shape in 33% of its own Bash
    calls — a worse rate than the session it had been measuring. It reported "went well, gate green
    throughout", which was true and beside the point. **Authoring a rule does not make an agent more
    likely to follow it**, so the number has to come from the transcript rather than from the
    session's self-assessment.
    """
    path = Path(session)
    if not path.is_file():
        redirected = _job_transcript(session)
        if redirected is not None:
            print(f"# {session[:8]} is a background job's id, not a transcript id — reading {redirected.name}")
            path = redirected
        else:
            matches = [p for p in PROJECTS_DIR.rglob("*.jsonl") if p.stem == session or p.stem.startswith(session)]
            if not matches:
                return []
            path = max(matches, key=lambda p: p.stat().st_mtime)
    print(f"# transcript: {path}")
    return _parse_transcript(path, path.relative_to(PROJECTS_DIR).parts[0] if PROJECTS_DIR in path.parents else "")


def load_calls(days: float, project_filter: str | None) -> list[Call]:
    cutoff = time.time() - days * 86400
    calls: list[Call] = []
    for path in PROJECTS_DIR.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        project = path.relative_to(PROJECTS_DIR).parts[0]
        if project_filter and project_filter not in project:
            continue
        calls.extend(_parse_transcript(path, project))
    return calls


RATE_COLUMNS = [
    "head/tail",
    "exit-masked",
    "redirect-then-filter",
    "sed-n",
    "cat-view",
    "heredoc",
    "cd-own-repo",
    "git-C-own-repo",
    "git-mutating-in-chain",
]

# What a re-measurement after the 2026-08-24 changes (acceptEdits default, rewritten ~/AGENTS.md
# Bash cluster) should show, per model, relative to the stored baseline. "down": lower share;
# "zero": at or near 0%. Anything else is reported but not judged.
EXPECTATIONS: dict[str, str] = {
    "chain": "down",
    "head/tail": "down",
    "redirect-then-filter": "zero",
    "echo-exit": "zero",
    "sed-n": "down",
    "cat-view": "down",
    "heredoc": "down",
    "cd-own-repo": "zero",
    "git-C-own-repo": "zero",
    "git-mutating-in-chain": "down",
    "git-C-mutating": "zero",
    "find-not-fd": "down",
    # `grep-r-not-rg` is deliberately absent, and `find-exempt` too. The first sat at 8% of its pair
    # when measured (2026-08-29) — adherence already good, so the useful direction is "not up",
    # which this table cannot express: "down" would demand improvement on a rule that is being
    # followed, and a verdict nobody can satisfy is one that gets ignored. The second is not a miss
    # at all; it is the share `find-not-fd` deliberately excludes, reported so the judgement baked
    # into that row's regex stays visible rather than hidden inside it.
}


def rates(calls: list[Call]) -> dict[str, float]:
    """Share of `calls` carrying each tag, plus the aggregate chain rate."""
    n = len(calls)
    counts = Counter(t for c in calls for t in c.tags)
    out = {"chain": sum(counts[f"chain{i}"] for i in range(2, 6)) / n, "chain5": counts["chain5"] / n}
    for col in [*RATE_COLUMNS, "git-C-mutating", "echo-exit"]:
        out[col] = counts[col] / n
    return out


def rates_by_model(calls: list[Call]) -> dict[str, dict[str, float | int]]:
    groups = _group(calls, lambda c: f"{c.model}{' [sub]' if c.subagent else ''}")
    return {label: {"n": len(rs), **rates(rs)} for label, rs in groups.items()}


def _rate_row(label: str, calls: list[Call], columns: list[str]) -> str:
    r = rates(calls)
    cells = [f"chain={r['chain']:.0%}", f"chain5={r['chain5']:.0%}"]
    cells += [f"{col}={r[col]:.0%}" for col in columns]
    return f"{label:44} n={len(calls):5}  " + "  ".join(cells)


def save_baseline(calls: list[Call], path: Path, days: float, note: str) -> None:
    payload = {
        "saved": time.strftime("%Y-%m-%d", time.gmtime()),
        "days": days,
        "note": note,
        "models": rates_by_model(calls),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"\nbaseline written to {path}")


def compare(calls: list[Call], baseline_path: Path) -> None:
    """Per model present in both runs: delta in percentage points against the baseline, with a
    verdict for every tag EXPECTATIONS names. A model with under 50 calls in either run is shown
    but not judged — the rates are too noisy to call."""
    baseline = json.loads(baseline_path.read_text())
    print(f"\n== vs baseline {baseline_path.name} ({baseline.get('saved')}, {baseline.get('note', '')}) ==")
    now = rates_by_model(calls)
    verdicts: list[bool] = []
    for label, cur in sorted(now.items(), key=lambda kv: -int(kv[1]["n"])):
        old = baseline["models"].get(label)
        if old is None:
            print(f"{label:44} n={cur['n']:5}  (not in baseline)")
            continue
        judge = min(int(cur["n"]), int(old["n"])) >= 50
        cells = []
        for tag, want in EXPECTATIONS.items():
            after = float(cur.get(tag, 0.0))
            if tag not in old and want != "zero":
                # A "down" expectation on a pattern added since this baseline was saved has nothing
                # to be judged against, and defaulting the missing side to 0.0 does not degrade
                # gracefully: the test becomes `0.0 < 0.0`, so a **clean** rate of 0% reports MISS
                # and drags the score down with it. Confirmed 2026-09-02 by `find-not-fd`, added
                # that day, reporting `0%(+0pp,MISS)` against a 2026-08-24 baseline — and by
                # `redirect-then-filter`, absent from the same baseline, collecting an equally
                # unearned OK. The bug manufactured both verdicts, not just the harsh one.
                #
                # A **"zero"** expectation is absolute — `after <= 0.02` needs no `before` — so it
                # is still judged here. Skipping those too was the over-correction, and it silently
                # dropped a real 23% `git-C-own-repo` rate out of the score.
                cells.append(f"{tag}={after:.0%}(new)")
                continue
            before = float(old.get(tag, 0.0))
            delta = (after - before) * 100
            ok = after <= 0.02 if want == "zero" else after < before
            mark = ("OK" if ok else "MISS") if judge else "?"
            if judge:
                verdicts.append(ok)
            cells.append(f"{tag}={after:.0%}({delta:+.0f}pp,{mark})")
        print(f"{label:44} n={cur['n']:5}  " + "  ".join(cells))
    if verdicts:
        print(f"\n{sum(verdicts)}/{len(verdicts)} expectations met (models with >=50 calls in both runs)")
    else:
        print("\nno model has >=50 calls in both runs — nothing judged yet; re-run with a wider --days")


PROBES = [
    (
        "mkdir -p <scratch>/probe-fs",
        "no prompt — <scratch> is in permissions.additionalDirectories and mkdir is a mode-granted fs command",
    ),
    (
        "mkdir -p ./.probe-fs && rmdir ./.probe-fs",
        "no prompt — inside the working directory; also proves the old Bash(mkdir:*) ask rule is gone",
    ),
    (
        "git -C <another personal repo> status",
        "no prompt — the Bash(git -C * status:*) allow rule from global_option_prefixes",
    ),
    (
        "git init -q --bare <scratch>/probe-remote.git",
        "PROMPT — not read-only, matches no rule; approve it (throwaway path)",
    ),
    (
        "git -C <scratch>/probe-remote.git push -q <scratch>/probe-remote.git HEAD:probe",
        "PROMPT — a mutating verb behind -C matches no ask rule and must fall through to the mode's prompt; "
        "under auto mode this is the call that ran unprompted. Fails harmlessly after approval "
        "(bare repo has no HEAD); the prompt is the data point",
    ),
    (
        "rm -rf <scratch>/probe-fs <scratch>/probe-remote.git",
        "no prompt — in-scope rm is mode-granted; the harness still hard-blocks rm on critical paths",
    ),
]


def print_probes() -> None:
    print(__doc__.split("\n\n")[0])
    print(
        "\nLive permission probes. Run each as its OWN Bash tool call (a subprocess would bypass the\n"
        "harness's permission check), in an acceptEdits session, with <scratch> = $CLAUDE_JOB_DIR/tmp\n"
        "or the session scratchpad. The agent cannot see prompts: after running them, tell the user\n"
        "which steps were expected to prompt and ask whether that is what they saw.\n"
    )
    for i, (cmd, expect) in enumerate(PROBES, 1):
        print(f"{i}. {cmd}\n   expect: {expect}")


def _print_rates(title: str, groups: dict[str, list[Call]], limit: int | None = None) -> None:
    print(f"\n== {title} ==")
    for label, rs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:limit]:
        print(_rate_row(label, rs, RATE_COLUMNS))


def _group(calls: list[Call], key: Callable[[Call], str]) -> dict[str, list[Call]]:
    groups: dict[str, list[Call]] = defaultdict(list)
    for c in calls:
        groups[key(c)].append(c)
    return groups


def report(calls: list[Call], samples: int, compare_with: Path | None = None) -> None:
    random.seed(1)
    print(f"Bash calls: {len(calls)}  (subagent: {sum(c.subagent for c in calls)})")

    _print_rates("per model", _group(calls, lambda c: f"{c.model}{' [sub]' if c.subagent else ''}"))
    main_calls = [c for c in calls if not c.subagent]
    by_session = _group(main_calls, lambda c: f"{short_project(c.project)}/{c.session[:8]} {c.model}")
    _print_rates("per session (main, largest first)", by_session, limit=25)

    # The verdict prints here, above the samples, because the samples are the bulk and the verdict is
    # the answer. See report_session's note: a run piped through `head -12` lost the comparison
    # entirely when it printed last, and reported the rates as though they were the finding.
    if compare_with:
        compare(calls, compare_with)

    print("\n== pattern totals ==")
    totals = Counter(t for c in calls for t in c.tags)
    for name, (_, why) in PATTERNS.items():
        print(f"{name:24} {totals[name]:5}   {why}")
    for name in CHAIN_TAGS:
        print(f"{name:24} {totals[name]:5}")

    reruns = _truncation_reruns(calls)
    print(f"\n== re-runs after a head/tail-truncated first run: {len(reruns)} ==")
    for base in reruns[:samples]:
        print("  " + base[:140].replace("\n", "\\n"))

    if samples:
        _print_samples(calls, samples)

    denied = [c for c in calls if c.denied]
    print(f"\n== denied ({len(denied)}) ==")
    for c in denied:
        print(f"[{c.model[:12]}] {c.cmd[:160]!r}\n    -> {c.result[:120]!r}")


CHAIN_TAGS = (
    "chain2",
    "chain3",
    "chain4",
    "chain5",
    "cd-and-cmd",
    "cd-own-repo",
    "cd-other",
    "git-C-own-repo",
    "git-mutating-in-chain",
)
SAMPLE_TAGS = (
    "git-C-mutating",
    "git-mutating-in-chain",
    "chain5",
    "head/tail",
    "exit-masked",
    "cd-own-repo",
    "git-C-own-repo",
    "sed-n",
    "cat-view",
)


def _print_samples(calls: list[Call], samples: int) -> None:
    for name in SAMPLE_TAGS:
        rs = [c for c in calls if name in c.tags]
        print(f"\n== {name} ({len(rs)}) samples ==")
        for c in random.sample(rs, min(samples, len(rs))):
            who = f"{c.model[:12]}|{'sub' if c.subagent else 'main'}|{short_project(c.project)[:18]}"
            print(f"[{who}] {c.cmd[:220].replace(chr(10), chr(92) + 'n')}")


def _truncation_reruns(calls: list[Call]) -> list[str]:
    """Same command issued again after a `| head/tail -N` run — the truncation lost something."""
    seen: dict[str, int] = {}
    reruns: list[str] = []
    for c in sorted(calls, key=lambda c: c.timestamp):
        m = re.match(r"(.*?)\|\s*(?:head|tail)\s+-(\d+)\s*$", c.cmd.strip(), re.DOTALL)
        base = m.group(1).strip() if m else c.cmd.strip()
        limit = int(m.group(2)) if m else 10**9
        if base in seen and seen[base] < limit:
            reruns.append(base)
        seen[base] = limit
    return reruns


def _before(calls: list[Call], until: str) -> list[Call]:
    """Calls made strictly before `until`, so a run measuring itself can exclude its own tail.

    A harvest's sweep is a different population from the session it reports on — inspections rather
    than working commands — and including it measures the sweep. Measured 2026-09-01 on two runs the
    same day: one rose 37% -> 40% on `head`/`tail`, the other fell 22% -> 17% on `git -C`, so the
    direction is not predictable and "it inflates the number" is the wrong claim. Excluding is.

    A call whose transcript entry carried no timestamp is kept rather than dropped: it cannot be
    placed on either side, and silently discarding it would bias the rate it is being used to judge.
    """
    cutoff = datetime.fromisoformat(until)
    if cutoff.tzinfo is None:
        cutoff = cutoff.astimezone()
    kept: list[Call] = []
    for call in calls:
        if not call.timestamp:
            kept.append(call)
            continue
        stamped = datetime.fromisoformat(call.timestamp)
        if stamped.tzinfo is None:
            stamped = stamped.astimezone()
        if stamped < cutoff:
            kept.append(call)
    return kept


def report_session(args: argparse.Namespace) -> None:
    """One session measured against the baseline — the shape a run checking itself uses."""
    calls = load_session(args.session)
    if not calls:
        print(f"no Bash calls found for session {args.session!r}")
        return
    whole = len(calls)
    if args.until:
        calls = _before(calls, args.until)
        if not calls:
            print(f"no Bash calls before {args.until} for session {args.session!r}")
            return
    print(f"# this session: {len(calls)} Bash calls")
    if args.until:
        print(f"#   excluding {whole - len(calls)} at or after {args.until} — the run's own sweep")
    print(_rate_row("this session", calls, RATE_COLUMNS))
    # Comparison first, samples after. The samples run to dozens of lines and the comparison is one
    # block, so printing the comparison last put the only judged output behind the bulk. Confirmed
    # 2026-09-02: a harvest ran this exact command as `… --compare … | head -12`, saw the rates line
    # and the first sample blocks, and concluded `--compare` had silently produced no comparison —
    # then filed a plan naming the script and the baseline as the two candidate causes. Neither was
    # it. The rule against piping is what should have prevented it and the ordering is what makes
    # the failure survivable, so both exist.
    if args.compare:
        compare(calls, args.compare)
    else:
        print("\nCompare against the baseline with --compare; a rate worse than it is the finding,")
        print("and authoring a rule is not evidence of following it.")
    if args.samples:
        _print_samples(calls, args.samples)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=float, default=4, help="look back this many days of transcript mtime (default 4)")
    ap.add_argument("--project", help="only projects whose slug contains this substring")
    ap.add_argument("--samples", type=int, default=8, help="samples to print per pattern (0 = none)")
    ap.add_argument("--json", type=Path, help="also dump every call with its tags to this JSON file")
    ap.add_argument("--compare", type=Path, help="baseline JSON to diff the per-model rates against, with verdicts")
    ap.add_argument(
        "--save-baseline",
        nargs="?",
        const=None,
        default=False,
        type=Path,
        help="write this run's per-model rates as a baseline. With no path, "
        "$XDG_STATE_HOME/session-bash-audit/<date>.json — never inside the installed skill, "
        "which a re-install replaces",
    )
    ap.add_argument("--note", default="", help="free-text label stored in the baseline (mode in force, why)")
    ap.add_argument("--probe", action="store_true", help="print the live permission probes and exit")
    ap.add_argument(
        "--session",
        help="measure ONE session by id or transcript path, for a run checking itself against the baseline",
    )
    ap.add_argument(
        "--until",
        help="ignore calls at or after this ISO timestamp, so a run measuring itself can exclude its own sweep",
    )
    args = ap.parse_args()

    if args.probe:
        print_probes()
        return

    if args.session:
        report_session(args)
        return

    calls = load_calls(args.days, args.project)
    if args.until:
        calls = _before(calls, args.until)
    if not calls:
        print("no Bash calls found — check --days / --project / --until")
        return
    report(calls, args.samples, args.compare)
    if args.save_baseline is not False:
        default = state_dir() / f"{time.strftime('%Y-%m-%d', time.gmtime())}.json"
        save_baseline(calls, args.save_baseline or default, args.days, args.note)
    if args.json:
        args.json.write_text(json.dumps([{**c.__dict__, "tags": sorted(c.tags)} for c in calls], indent=1, default=str))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
