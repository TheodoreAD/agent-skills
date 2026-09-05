#!/usr/bin/env python3
"""The mechanical half of a session harvest: the boundary, the transcript, and the live-state sweep.

`session-harvest`'s judgement — the significance test, the routing filters, the report's groups —
stays in `SKILL.md`. Everything here is a command the skill used to spell out in prose and every run
re-derived by hand, differently each time. Measured 2026-09-02 over one machine's whole transcript
store (24,429 Bash calls in 1,134 transcripts): 568 plans-store status/log calls, 498
`git log origin/<branch>..HEAD`, 378 `gh run` calls, 164 hand-written Python heredocs over a
transcript, 94 installed-vs-checkout diffs, 93 `ps -o` invocations. A lookup redone from scratch
every time drifts, and its answers stop being comparable across runs.

    harvest.py boundary                          # step 0's instant; pass it to everything after
    harvest.py transcript --expect '<a command this session ran>'
    harvest.py turns --json
    harvest.py skills-state --since <session start>
    harvest.py sweep --boundary <instant>
    harvest.py claims --until <instant>

The transcript resolves, in order, from `--session <id|path>`, a background job's `state.json`
(`$CLAUDE_JOB_DIR`), Claude Code's own `$CLAUDE_CODE_SESSION_ID` (exported into every Bash call, so
the bare forms above work there), and last `--expect '<a command this session ran>'` by content.
Pass `--session` on a harness that exports no id.

Stdlib only, so it runs by path with no install step. **Every subcommand is read-only**: nothing
here writes a file, commits, pushes, installs or deletes, and the one thing the skill genuinely
needs to run — the repo's own quality gate, re-run when `exit-masked` is above zero — is deliberately
absent, because the gate is the repo's command and hard-coding one would be wrong in every repo that
spells it differently.

Six corrections the skill accumulated as prose warnings are code here instead, each one having
recurred at least once *after* its warning existed:

- the upstream branch is read (`rev-parse --abbrev-ref @{u}`), never typed as `main`;
- external commands run without a shell, so no pipe can eat an exit code;
- `gh run view --json status,conclusion` rather than a watch whose exit a pipe discards;
- `depends_on` is matched at line start, inside the frontmatter block;
- a background job's transcript comes from its `state.json`, wherever that file actually sits;
- `AskUserQuestion` answers are found by tool-use id, not by matching a preamble string.

Exit codes: 0 ok, 1 error, 2 argparse usage.
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
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol

PROJECTS_DIR = Path.home() / ".claude" / "projects"
JOBS_DIR = Path.home() / ".claude" / "jobs"
INSTALLED_SKILLS = Path.home() / ".agents" / "skills"

# A module constant rather than an `os.name` test at the call site, so a test can pin the platform
# without patching `os` itself: `os.name` is what `pathlib` reads to decide whether `Path()` is a
# PosixPath or a WindowsPath, and patching it globally makes every path in the process unusable.
WINDOWS = os.name == "nt"

# The two commands the sweep's process and socket steps run, per platform. The POSIX pair is what
# every measurement in this skill was made with; the Windows pair is reasoned from documented output
# and exercised only against fixture text in the tests, since nothing here has run on Windows.
PS_ARGV = ("ps", "-eo", "pid=,ppid=,pgid=,stat=,etimes=,args=")
PS_WINDOWS_ARGV = (
    "powershell",
    "-NoProfile",
    "-NonInteractive",
    "-Command",
    # One tab-separated line per process: pid, parent pid, age in seconds, command line.
    "$now = Get-Date; Get-CimInstance Win32_Process | ForEach-Object { "
    "$age = if ($_.CreationDate) { [int]($now - $_.CreationDate).TotalSeconds } else { 0 }; "
    '"$($_.ProcessId)`t$($_.ParentProcessId)`t$age`t$($_.CommandLine)" }',
)
SS_ARGV = ("ss", "-ltnp")
NETSTAT_WINDOWS_ARGV = ("netstat", "-ano")

# Skills a harvest leans on by default, so `skills-state` with no arguments still answers step 0's
# question. Anything else this run used is added with --skill.
DEFAULT_SKILLS = ("session-harvest", "plan-docs", "session-bash-audit")

# A process worth reporting is one that outlives the turn that started it. These two say what kind
# of survivor it is, which is the difference between "still working" and "polling forever".
WATCHER_RE = re.compile(r"gh run watch|while true|until \[|watch -n|tail -f|sleep \d")
SERVER_RE = re.compile(
    r"http\.server|uvicorn|gunicorn|flask run|vite|webpack|next dev|npm run dev|yarn dev|"
    r"rails s|php -S|python -m http|serve -|ngrok|caddy|nginx"
)
LOOPBACK = ("127.0.0.1", "::1", "[::1]", "localhost")

# `$?` after a pipe is the filter's, not the command's. Same regex as session-bash-audit's
# `exit-masked` row, restated here rather than imported: the two scripts install into separate skill
# directories and an import across them breaks whenever one is installed and the other is not.
EXIT_MASKED_RE = re.compile(r"2>&1\s*\|\s*(tail|head|grep|rg)\b")

# Sentences that tell the user a gate passed. Deliberately broad: an over-count is a footnote the
# agent reads and discards, while a miss is the failure this whole check exists to prevent.
GREEN_CLAIM_RE = re.compile(
    r"gate[^.\n]{0,40}\b(green|clean|pass(?:es|ed)?)\b"
    r"|\b(precommit|pre-commit|quality\.(?:check|precommit)|pytest|test suite|suite)\b[^.\n]{0,40}"
    r"\b(green|clean|pass(?:es|ed)?|all good)\b"
    r"|\ball (?:tests|checks)\b[^.\n]{0,20}\bpass(?:es|ed)?\b"
    r"|\b(0 errors|exits? 0|exit code 0)\b",
    re.IGNORECASE,
)

# The two preambles an AskUserQuestion result can open with. Used only as a cross-check against the
# exact extraction below — see `answers()` for why matching these is not the extraction itself.
ANSWER_PREAMBLES = ("Your questions have been answered:", "The user answered:")


class HarvestError(Exception):
    """Anything the caller can fix by passing a different argument."""


# --------------------------------------------------------------------------------------------
# the one seam: every external command
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Ran:
    argv: tuple[str, ...]
    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def lines(self) -> list[str]:
        return [line for line in self.out.splitlines() if line.strip()]


class Runner(Protocol):
    """Every subprocess this script makes, behind one seam so the parsers can be tested with none."""

    def __call__(self, argv: Sequence[str], cwd: Path | None = None) -> Ran: ...


class LiveRunner:
    """Real commands, **never through a shell** — which is the structural version of a rule the
    skill had to keep restating in prose.

    No shell means no pipe, and no pipe means `Ran.code` is always the command's own exit status.
    Every documented failure in this area came from a filter reporting its own success: a `git log`
    against the wrong branch exits 128 and `| wc -l` turned that into a calm `0` for a store 32
    commits ahead; `gh run watch --exit-status` had its whole purpose discarded by a `| tail` three
    separate times, each on a run following the checklist that warns against it.
    """

    def __init__(self, timeout: float = 90.0) -> None:
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
# instants
# --------------------------------------------------------------------------------------------


def now_iso() -> str:
    """The boundary: local time with its offset, to the second."""
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def as_instant(stamp: str) -> datetime | None:
    """Parse an ISO timestamp from either side of the comparison the skill keeps getting wrong.

    A transcript stamps UTC with a trailing `Z`; git prints local time with an offset. Compared as
    strings they sort by the offset rather than by the moment, so both sides are parsed and made
    aware here, and every comparison in this file is between two `datetime`s.
    """
    text = stamp.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def before(stamp: str, cutoff: str | None) -> bool:
    """True when `stamp` is strictly before `cutoff` — and when either is unreadable.

    Unplaceable entries are kept rather than dropped, the same choice `audit.py` makes: silently
    discarding what cannot be placed biases the very count it is being used to judge.
    """
    if not cutoff:
        return True
    left, right = as_instant(stamp), as_instant(cutoff)
    if left is None or right is None:
        return True
    return left < right


# --------------------------------------------------------------------------------------------
# the transcript
# --------------------------------------------------------------------------------------------


@dataclass
class Transcript:
    path: Path
    how: str
    session_id: str
    started: str | None
    cwd: str | None
    entries: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "resolved_by": self.how,
            "session_id": self.session_id,
            "session_started": self.started,
            "cwd": self.cwd,
            "entries": len(self.entries),
            "notes": self.notes,
        }


def read_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                entries.append(obj)
    return entries


def job_state(job_id: str | None = None) -> tuple[Path, dict[str, Any]] | None:
    """A background job's `state.json`, found rather than assumed.

    The skill named `$CLAUDE_JOB_DIR/../state.json`, which resolves to the jobs *root* on a build
    that points the variable at the job directory itself — `FileNotFoundError`, confirmed 2026-09-02
    on CLI 2.1.252. Both spellings are real on some build, so all of them are tried and the one that
    answered is reported. A miss returns None; it never falls back to an inferred id, which is the
    failure this exists to prevent.
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("CLAUDE_JOB_DIR")
    if env_dir:
        base = Path(env_dir)
        candidates += [base / "state.json", base.parent / "state.json"]
    if job_id:
        candidates += [JOBS_DIR / job_id / "state.json", JOBS_DIR / job_id[:8] / "state.json"]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            record = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            return candidate, record
    return None


def _from_job(job_id: str | None, must_match: str | None = None) -> tuple[Path, str] | None:
    """The transcript a job's `state.json` names, or None.

    `must_match` guards the id case: an id is only treated as a job's when that job's own
    `state.json` claims it as its `sessionId`. Without the guard a session id that happens to name
    no job would silently pick up whichever job directory shares its first eight characters.
    """
    found = job_state(job_id)
    if found is None:
        return None
    state_path, record = found
    if must_match is not None and record.get("sessionId") != must_match:
        return None
    scan = record.get("linkScanPath")
    if not isinstance(scan, str):
        return None
    path = Path(scan).expanduser()
    if not path.is_file():
        return None
    session = str(record.get("sessionId", ""))[:8]
    return path, f"{state_path} (job {session}, linkScanPath)"


def project_slug(cwd: Path) -> str:
    """The transcript directory Claude Code writes for a project: every character that is not an
    ASCII letter or digit becomes `-`, read from the CLI binary 2026-09-05. Past 200 characters the
    harness cuts the slug and appends a hash this script cannot recompute, so a directory lookup for
    such a path falls back to the machine-wide search. Same three lines as `audit.py`, duplicated
    rather than imported, because skills install individually."""
    slug = re.sub(r"[^a-zA-Z0-9]", "-", str(cwd))
    return slug if len(slug) <= 200 else ""


def _search_projects(needle: str) -> list[Path]:
    return sorted(
        (p for p in PROJECTS_DIR.rglob("*.jsonl") if p.stem == needle or p.stem.startswith(needle)),
        key=lambda p: -p.stat().st_mtime,
    )


def _by_content(expect: str, cwd: Path) -> list[Path]:
    """Transcripts containing `expect`, newest first — the "grep it for something you know you ran"
    check, used here to *select* rather than only to confirm.

    Scoped to the project directory for `cwd` when one exists, because a marker distinctive enough
    to identify a session is rarely distinctive across every project on the machine.
    """
    slug = project_slug(cwd)
    scoped = PROJECTS_DIR / slug if slug else None
    pool = sorted(scoped.glob("*.jsonl")) if scoped and scoped.is_dir() else list(PROJECTS_DIR.rglob("*.jsonl"))
    hits = [p for p in pool if expect in p.read_text(encoding="utf-8", errors="replace")]
    return sorted(hits, key=lambda p: -p.stat().st_mtime)


def _from_session_argument(session: str) -> tuple[Path, str] | None:
    if Path(session).expanduser().is_file():
        return Path(session).expanduser(), "path given"
    redirected = _from_job(session, must_match=session)
    if redirected:
        return redirected[0], f"{session[:8]} is a job id, not a transcript id — {redirected[1]}"
    matches = _search_projects(session)
    return (matches[0], "session id, matched under ~/.claude/projects") if matches else None


def _explicit_session(session: str) -> tuple[Path, str]:
    """An explicit id that names nothing is an error, never a fall-through: the caller pinned a
    session, and quietly resolving the harness's own instead reports a well-formed answer about a
    different transcript. Found 2026-09-05 by passing a nonsense id inside a live session and
    getting that session's transcript back, labelled as resolved by the environment."""
    found = _from_session_argument(session)
    if found is None:
        raise HarvestError(
            f"--session {session!r} names no transcript, job or file under {PROJECTS_DIR}. Check the id "
            "rather than dropping the flag: a bare call resolves the harness's own session, which may "
            "not be the one you meant."
        )
    return found


def resolve_transcript(session: str | None, job: str | None, expect: str | None, cwd: Path) -> Transcript:
    """THIS session's transcript, with the route it was found by printed rather than assumed.

    In a background job the session id is not the transcript id: `sessionId` names the job *and*
    names a real transcript file in the same directory, so a guess resolves successfully to a
    stranger's session and reports a well-formed, entirely wrong answer. Confirmed 2026-09-01 — a
    harvest audited 386 calls, not one of them its own, with nothing in the output reading as wrong.
    """
    notes: list[str] = []
    found = _explicit_session(session) if session else None
    if found is None and (job or os.environ.get("CLAUDE_JOB_DIR")):
        found = _from_job(job)
    if found is None and os.environ.get("CLAUDE_CODE_SESSION_ID"):
        # Claude Code exports its own session id into every Bash call, so a bare `turns`/`sweep`/
        # `claims` resolves with no state carried between invocations and nothing typed. After the
        # job check on purpose: a background job's environment names the parent session, and its
        # `state.json` is the only thing that knows the job's own transcript.
        env_id = os.environ["CLAUDE_CODE_SESSION_ID"]
        matches = _search_projects(env_id)
        if matches:
            found = matches[0], f"$CLAUDE_CODE_SESSION_ID ({env_id[:8]}), matched under ~/.claude/projects"
    if found is None and expect:
        hits = _by_content(expect, cwd)
        if len(hits) > 1:
            notes.append(f"{len(hits)} transcripts contain {expect!r}; took the most recent — pass --session to pin it")
        if hits:
            found = hits[0], f"newest transcript containing {expect!r}"
    if found is None:
        raise HarvestError(
            "no transcript resolved. Pass --session <id|path>, or --expect '<a command this session "
            "definitely ran>' to select by content. Never guess an id: a wrong one names a real file."
        )

    path, how = found
    entries = read_entries(path)
    if expect and not how.startswith("newest transcript"):
        found = expect in path.read_text(encoding="utf-8", errors="replace")
        notes.append(f"self-check: {expect!r} {'found' if found else 'NOT FOUND'} in this transcript")
        if not found:
            notes.append("a transcript missing a command you know you ran is somebody else's session")
    started = next((str(e.get("timestamp")) for e in entries if e.get("timestamp")), None)
    cwd_field = next((str(e.get("cwd")) for e in entries if e.get("cwd")), None)
    session_id = next((str(e.get("sessionId")) for e in entries if e.get("sessionId")), path.stem)
    return Transcript(path, how, session_id, started, cwd_field, entries, notes)


# --------------------------------------------------------------------------------------------
# what the transcript says
# --------------------------------------------------------------------------------------------


def block_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def iter_blocks(entries: Iterable[dict[str, Any]]) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    for entry in entries:
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict):
                yield entry, block


SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
COMMAND_WRAPPER_RE = re.compile(r"<command-(name|message|args)>|<local-command-(caveat|stdout)>")
# Not the user speaking, whichever population it arrives in: the harness reporting a background
# task, and the marker left when a tool call is rejected. Both are real signal and neither is an
# instruction, so they are labelled rather than dropped — a run that says "six user turns" when
# three of them are these has miscounted the brief in the direction that matters.
TASK_NOTIFICATION_RE = re.compile(r"<task-notification>|<local-command-stdout>")
INTERRUPT_RE = re.compile(r"^\[Request interrupted by user")


@dataclass
class Turn:
    kind: str  # user | answer | command
    timestamp: str
    text: str


def user_turns(entries: Iterable[dict[str, Any]]) -> list[Turn]:
    """Real user text, with the harness's own wrappers labelled rather than dropped.

    A compacted session hands you someone else's précis, and the loose ends this recovers are
    exactly what a summary drops. Slash-command wrappers and local-command output are kept as
    `command` turns: they are not instructions, but a run that reports "ten user turns" without
    saying eight were wrappers has miscounted the brief.
    """
    turns: list[Turn] = []
    for entry in entries:
        if entry.get("type") != "user":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        text = content if isinstance(content, str) else ""
        if isinstance(content, list):
            text = "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("type") == "text")
        text = SYSTEM_REMINDER_RE.sub("", text).strip()
        if not text:
            continue
        turns.append(Turn(classify_turn(text, bool(entry.get("isMeta"))), str(entry.get("timestamp", "")), text))
    return turns


def classify_turn(text: str, meta: bool = False) -> str:
    if INTERRUPT_RE.match(text):
        return "interrupt"
    if TASK_NOTIFICATION_RE.search(text):
        return "notification"
    return "command" if COMMAND_WRAPPER_RE.search(text) or meta else "user"


def queued_messages(entries: Iterable[dict[str, Any]]) -> tuple[list[Turn], int]:
    """A message the user sends **while a turn is still running** — the third population.

    Claude Code surfaces those inside the running turn and records them as `queue-operation`
    entries, not as `type: "user"`, so a scan built on user turns plus answers finds neither.
    Filed 2026-09-02 by a session that measured it: `turns` reported six user turns and five
    answers, and the single richest instruction of the session — new scope, roughly its last
    third, two plan files and six commits — appeared in none of them.

    **The miss is invisible exactly where it costs most.** A mid-turn message is what a user sends
    when they think of something while the agent is working, so it is disproportionately new scope
    rather than a correction to what is already running — an instruction with no earlier trace in
    the transcript to recover it from. A session where the user waited their turn loses nothing.

    Each queued message is recorded twice, `operation: "enqueue"` then `operation: "remove"` when
    it is delivered, so only the enqueue is taken. The same message also appears as an
    `attachment` of type `queued_command`; that count is returned as the cross-check rather than
    as a second source, because `attachment` carries mostly harness noise (230 token reminders in
    the transcript this was measured on) and matching the type would be the over-broad half of the
    mistake this step has already made twice.
    """
    found: list[Turn] = []
    attachments = 0
    for entry in entries:
        if entry.get("type") == "attachment":
            payload = entry.get("attachment")
            if isinstance(payload, dict) and payload.get("type") == "queued_command":
                attachments += 1
            continue
        if entry.get("type") != "queue-operation" or entry.get("operation") != "enqueue":
            continue
        text = SYSTEM_REMINDER_RE.sub("", str(entry.get("content", ""))).strip()
        if not text:
            continue
        kind = classify_turn(text)
        found.append(Turn("mid-turn" if kind == "user" else kind, str(entry.get("timestamp", "")), text))
    return found, attachments


def answers(entries: Sequence[dict[str, Any]]) -> tuple[list[Turn], int]:
    """`AskUserQuestion` answers, found by tool-use id — and a preamble count as the cross-check.

    On a tool-driven session the answers carry the entire brief, and every string-matching version
    of this filter has been wrong. First a heuristic looking for "question" and "answers" anywhere in
    a tool result, which returned `Read` outputs alongside real answers. Then a narrowing to
    `Your questions have been answered:`, which missed every typed answer — those open
    `The user answered:` — on a session where three typed answers carried the whole second half of
    the brief. Then anchoring both preambles to the start of a block, which still counts the skill's
    own text, a harvest's extraction script, and that script's output.

    Linking `tool_result.tool_use_id` back to a `tool_use` block named `AskUserQuestion` has none of
    those failure modes: it asks the transcript what the tool *was* rather than what its output looks
    like. Measured 2026-09-02 on a `power-user-linux-setup` session: 7 by id, 8 by anchored preamble,
    the extra being a grep's output that began with the marker. The preamble count is returned
    alongside so a disagreement is reported rather than silently resolved in either direction.
    """
    ask_ids = {
        str(block.get("id"))
        for _, block in iter_blocks(entries)
        if block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion"
    }
    found: list[Turn] = []
    preamble_hits = 0
    for entry, block in iter_blocks(entries):
        if block.get("type") != "tool_result":
            continue
        text = block_text(block.get("content")).strip()
        if text.startswith(ANSWER_PREAMBLES):
            preamble_hits += 1
        if str(block.get("tool_use_id")) in ask_ids:
            found.append(Turn("answer", str(entry.get("timestamp", "")), text))
    return found, preamble_hits


TOOL_WRITE_INPUTS = ("file_path", "notebook_path")
CD_RE = re.compile(r"(?:^|&&|;|\n)\s*cd\s+(\S+)")
GIT_C_RE = re.compile(r"\bgit\s+-C\s+(\S+)")


def written_paths(entries: Iterable[dict[str, Any]]) -> list[Path]:
    """Files this session *wrote*, from the transcript's own tool inputs.

    Reads are deliberately excluded. A session that only read another repo has not touched it for
    the sweep's purposes, and counting reads is the difference between a sweep reporting six repos
    and reporting the two that matter.
    """
    seen: dict[str, None] = {}
    for _, block in iter_blocks(entries):
        if block.get("type") != "tool_use" or block.get("name") not in ("Edit", "Write", "NotebookEdit"):
            continue
        payload = block.get("input")
        if not isinstance(payload, dict):
            continue
        for key in TOOL_WRITE_INPUTS:
            value = payload.get(key)
            if isinstance(value, str) and value:
                seen[value] = None
    return [Path(p) for p in seen]


def shell_targets(entries: Iterable[dict[str, Any]]) -> list[Path]:
    """Directories the session pointed a command at: `cd <path>` and `git -C <path>`."""
    seen: dict[str, None] = {}
    for _, block in iter_blocks(entries):
        if block.get("type") != "tool_use" or block.get("name") != "Bash":
            continue
        payload = block.get("input")
        if not isinstance(payload, dict):
            continue
        command = str(payload.get("command", ""))
        for pattern in (CD_RE, GIT_C_RE):
            for match in pattern.finditer(command):
                target = match.group(1).strip("'\"")
                if target.startswith("-") or "$" in target:
                    continue
                seen[str(Path(target).expanduser())] = None
    return [Path(p) for p in seen]


def bash_calls(entries: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for entry, block in iter_blocks(entries):
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            payload = block.get("input")
            if isinstance(payload, dict):
                out.append((str(entry.get("timestamp", "")), str(payload.get("command", ""))))
    return out


def assistant_text(entries: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    """Everything the agent put in front of the user — including an `AskUserQuestion`'s own text.

    A question's wording is a sentence the user reads and decides on, so a claim made there is as
    live as one in a message. Scanning only `text` blocks missed it, and the miss is the same shape
    as the answer-filter's: a user-facing population that is not the obvious entry type. Confirmed
    2026-09-02, by this function's own session — `claims` reported **0** green-gate assertions while
    two of the three questions it asked opened "Gate green, scan clean" and "gate green (393
    tests)", both of them decision prompts the user answered on that basis.
    """
    out: list[tuple[str, str]] = []
    for entry, block in iter_blocks(entries):
        stamp = str(entry.get("timestamp", ""))
        if entry.get("type") == "assistant" and block.get("type") == "text":
            text = str(block.get("text", "")).strip()
            if text:
                out.append((stamp, text))
        elif block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
            payload = block.get("input")
            if isinstance(payload, dict):
                asked = " ".join(
                    str(q.get("question", "")) for q in payload.get("questions", []) if isinstance(q, dict)
                ).strip()
                if asked:
                    out.append((stamp, asked))
    return out


# --------------------------------------------------------------------------------------------
# git, always through the runner
# --------------------------------------------------------------------------------------------


def git_root(runner: Runner, path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    if not start.exists():
        return None
    ran = runner(["git", "-C", str(start), "rev-parse", "--show-toplevel"])
    return Path(ran.out.strip()) if ran.ok and ran.out.strip() else None


def upstream_of(runner: Runner, repo: Path) -> tuple[str | None, str]:
    """The ref that belongs on the left of `..`, read rather than typed.

    Measured 2026-08-30 across this machine's clones: 22 of 71 were on `main`, fewer than were on
    `master`, the rest on a feature branch — so the substitution a session reaches for is wrong more
    often than it is right, and wrong quietly, because `git log origin/main..HEAD` against a
    `master` repo exits 128 into whatever filter swallowed it.
    """
    ran = runner(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "@{u}"])
    if ran.ok and ran.out.strip():
        return ran.out.strip(), ""
    branch = runner(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"])
    return None, f"no upstream for {branch.out.strip() or 'HEAD'} — nothing to count against"


@dataclass
class RepoState:
    path: str
    branch: str
    upstream: str | None
    dirty: list[str]
    ahead: list[dict[str, str]]
    fetch: str
    ref_age: str
    overlap: list[str]
    notes: list[str]


def repo_state(
    runner: Runner, repo: Path, since: str | None, do_fetch: bool, written: Sequence[Path] = ()
) -> RepoState:
    """Dirty tree, unpushed commits, and whether an unpushed one corrects something already pushed."""
    notes: list[str] = []
    branch = runner(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"]).out.strip()
    dirty = runner(["git", "-C", str(repo), "status", "--porcelain"]).lines
    upstream, why = upstream_of(runner, repo)
    if why:
        notes.append(why)

    fetch_state = "not attempted"
    ref_age = ""
    if do_fetch and upstream:
        # Alone in its own call, with nothing after it, and its exit code read before anything
        # downstream is believed. A fetch that fails for want of an ssh agent leaves
        # `origin/<branch>` exactly where it was, so the ahead-count still prints a plausible number
        # computed against a stale ref — the wrong answer and the right one look identical.
        ran = runner(["git", "-C", str(repo), "fetch", upstream.split("/", 1)[0]])
        fetch_state = "ok" if ran.ok else f"FAILED ({ran.err.strip().splitlines()[-1:] or ran.code})"
        if not ran.ok:
            aged = runner(["git", "-C", str(repo), "log", "-1", "--format=%cr", upstream])
            ref_age = aged.out.strip()
            notes.append(f"ahead-count is against a ref last updated {ref_age or 'an unknown time ago'}")

    ahead: list[dict[str, str]] = []
    overlap: list[str] = []
    if upstream:
        log = runner(["git", "-C", str(repo), "log", f"{upstream}..HEAD", "--format=%h%x1f%an%x1f%cI%x1f%s"])
        if not log.ok:
            notes.append(f"git log {upstream}..HEAD exited {log.code}: {log.err.strip()}")
        for line in log.lines:
            parts = line.split("\x1f")
            if len(parts) == 4:
                ahead.append({"sha": parts[0], "author": parts[1], "when": parts[2], "subject": parts[3]})
        overlap = _correction_overlap(runner, repo, upstream, since, written)
    return RepoState(str(repo), branch, upstream, dirty, ahead, fetch_state, ref_age, overlap, notes)


def _correction_overlap(
    runner: Runner, repo: Path, upstream: str, since: str | None, written: Sequence[Path] = ()
) -> list[str]:
    """Paths that are both unpushed now and already published during this session.

    Not proof of a correction, but a short list to read and empty for most sessions. The case it
    catches: a session pushed a claim, learned it was false, committed the fix and never pushed — so
    the remote serves a justification known to be wrong while its correction sits in the ahead-count
    looking like ordinary tidying.

    **`written` is what keeps that from firing on other sessions' work, and without it the check is
    actively misleading on a shared repo.** `--since` on the upstream log means "authored recently",
    not "this session published it": in a store several sessions commit to, every one of their
    commits lands in `published`, so any later commit by anyone to the same file reads as this
    session correcting itself. Confirmed 2026-09-04 — a harvest pushed a 22-commit backlog it had
    not authored, and the next session's ordinary follow-up to one of those files was reported as a
    correction. A correction is only this session's if this session wrote the path, so intersect.
    """
    if not since:
        return []
    unpushed = set(runner(["git", "-C", str(repo), "log", f"{upstream}..HEAD", "--name-only", "--format="]).lines)
    published = set(
        runner(["git", "-C", str(repo), "log", upstream, f"--since={since}", "--name-only", "--format="]).lines
    )
    mine: set[str] = set()
    for path in written:
        try:
            mine.add(Path(path).resolve().relative_to(repo.resolve()).as_posix())
        except (ValueError, OSError):
            continue  # written outside this repo: another section's finding, not this one's
    return sorted(unpushed & published & mine)


# --------------------------------------------------------------------------------------------
# subcommand: boundary
# --------------------------------------------------------------------------------------------


def cmd_boundary(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    payload = {"boundary": now_iso()}
    if not args.json:
        print(payload["boundary"])
        print("# pass this to every later call as --boundary/--until: it separates the session's")
        print("# working commands from this harvest's own inspections, which are a different population")
    return payload


# --------------------------------------------------------------------------------------------
# subcommand: transcript
# --------------------------------------------------------------------------------------------


def cmd_transcript(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    transcript = resolve_transcript(args.session, args.job, args.expect, Path.cwd())
    payload = transcript.as_dict()
    if not args.json:
        print(f"transcript: {transcript.path}")
        print(f"resolved by: {transcript.how}")
        print(f"session id:  {transcript.session_id}")
        print(f"started:     {transcript.started}")
        print(f"cwd:         {transcript.cwd}")
        print(f"entries:     {len(transcript.entries)}")
        for note in transcript.notes:
            print(f"note: {note}")
    return payload


# --------------------------------------------------------------------------------------------
# subcommand: turns
# --------------------------------------------------------------------------------------------


def cmd_turns(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    transcript = resolve_transcript(args.session, args.job, args.expect, Path.cwd())
    turns = user_turns(transcript.entries)
    found, preamble_hits = answers(transcript.entries)
    queued, queued_attachments = queued_messages(transcript.entries)
    everything = sorted([*turns, *found, *queued], key=lambda t: t.timestamp)
    quiet = {"command", "notification"}
    real = [t for t in everything if t.kind not in quiet]

    payload = {
        "transcript": transcript.as_dict(),
        "turns": [{"kind": t.kind, "timestamp": t.timestamp, "text": t.text} for t in everything],
        "counts": {
            "user": sum(1 for t in turns if t.kind == "user"),
            "mid_turn": sum(1 for t in queued if t.kind == "mid-turn"),
            "command_wrappers": sum(1 for t in turns if t.kind == "command"),
            "notifications": sum(1 for t in everything if t.kind == "notification"),
            "interrupts": sum(1 for t in everything if t.kind == "interrupt"),
            "answers": len(found),
            "answers_by_preamble": preamble_hits,
            "queued_attachments": queued_attachments,
        },
    }
    if args.json:
        return payload

    print(f"# transcript: {transcript.path}  ({transcript.how})")
    counts = payload["counts"]
    print(
        f"# {counts['user']} user turns, {counts['mid_turn']} sent mid-turn, "
        f"{counts['answers']} AskUserQuestion answers"
    )
    print(
        f"# also {counts['command_wrappers']} slash-command wrappers, {counts['notifications']} task "
        f"notifications, {counts['interrupts']} interruptions — none of them an instruction"
    )
    if preamble_hits != len(found):
        print(
            f"# self-check: {preamble_hits} blocks open with an answer preamble against {len(found)} "
            "matched by tool-use id — the difference is text quoting the marker (this skill, a "
            "grep's output), not a missed answer. Read the samples if it is large."
        )
    # The same cross-check for the third population: a queued message is also recorded as a
    # `queued_command` attachment, so a disagreement means the entry shape has moved and the
    # mid-turn count is the one that would silently read as "the user sent nothing mid-turn".
    if queued_attachments and not queued:
        print(
            f"# self-check: {queued_attachments} queued_command attachment(s) but no queue-operation "
            "entries — the transcript shape has changed; read the raw entries before trusting this"
        )
    if not real:
        print("# no user text and no answers: this is somebody else's transcript, or the wrong one")
    for turn in everything:
        if turn.kind in quiet and not args.all:
            continue
        body = turn.text if args.chars <= 0 else turn.text[: args.chars]
        print(f"\n--- {turn.kind} {turn.timestamp} ---\n{body}")
    return payload


# --------------------------------------------------------------------------------------------
# subcommand: skills-state
# --------------------------------------------------------------------------------------------


def plan_docs_config() -> dict[str, Any]:
    """`plan-docs`' config, read as a contract rather than through `plans.py`.

    Two independently installed skills share a location by both reading the same configuration —
    the environment variables and `~/.config/plan-docs/config.toml` — never by one importing the
    other, which would hard-code the install hub and break whenever one is installed without the
    other. Resolution copies `plans.py`'s three lines: `$PLAN_DOCS_CONFIG`, then `$XDG_CONFIG_HOME`,
    then the platform default. An absent or unreadable file is an empty mapping, so every default
    below still applies.
    """
    override = os.environ.get("PLAN_DOCS_CONFIG")
    if override:
        path = Path(override).expanduser()
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            base = Path(xdg).expanduser()
        elif WINDOWS:
            roaming = os.environ.get("APPDATA")
            base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
        else:
            base = Path.home() / ".config"
        path = base / "plan-docs" / "config.toml"
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def projects_root() -> Path:
    """Where this machine keeps its repos, from `plan-docs`' config, else that skill's own default."""
    raw = plan_docs_config().get("projects_root")
    return Path(str(raw) if raw else "~/projects").expanduser()


def skills_checkouts(name: str, root: Path, depth: int = 3) -> list[Path]:
    """Every git checkout under the projects root that holds `skills/<name>/SKILL.md`.

    A walk rather than a path: the author keeps repos as `<root>/<host>/<repo>` on one machine and
    would keep them flat as `<root>/<repo>` on another, and a reader's layout is anybody's guess.
    Symlinks are never followed and the walk stops at each `.git`, the same shape `plans.py` uses.
    """
    found: list[Path] = []

    def walk(directory: Path, remaining: int) -> None:
        try:
            children = sorted(p for p in directory.iterdir() if p.is_dir() and not p.is_symlink())
        except OSError:
            return
        for child in children:
            if child.name.startswith("."):
                continue
            if (child / ".git").exists():
                if (child / "skills" / name / "SKILL.md").is_file():
                    found.append(child)
                continue
            if remaining > 1:
                walk(child, remaining - 1)

    if root.is_dir():
        walk(root, depth)
    return found


def find_checkout(explicit: str | None, start: Path | None = None, name: str = "session-harvest") -> Path:
    """The skills checkout: what was passed, else `$SESSION_HARVEST_CHECKOUT`, else this script's
    own repo, else the one checkout under the projects root that holds this skill's source.

    The last tier is detection, not a guess: it walks the projects root `plan-docs` is configured
    with, so it finds the source wherever the repos are laid out and names nothing about any one
    machine. Until 2026-09-03 this carried a hard-coded `~/projects/<owner>/<repo>` fallback — the
    author's own checkout path, in code shipped to strangers — and until 2026-09-05 it then had no
    third tier at all, so the installed copy could never answer step 0 without `--checkout`.

    Two checkouts holding the skill (a fork beside its upstream) is a question, not a pick: the
    error lists them and asks for `--checkout`. None is the reader's normal case — the installed
    copy has no repo above it — and the error says what that means for a skill fix: it goes in the
    report, and nothing is filed anywhere.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if not (path / "skills").is_dir():
            raise HarvestError(f"{path} has no skills/ directory")
        return path
    configured = os.environ.get("SESSION_HARVEST_CHECKOUT")
    if configured:
        return find_checkout(configured)
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        if (parent / "skills").is_dir() and (parent / ".git").exists():
            return parent
    root = projects_root()
    detected = skills_checkouts(name, root)
    if len(detected) == 1:
        return detected[0]
    if detected:
        listed = ", ".join(str(p) for p in detected)
        raise HarvestError(f"several checkouts hold skills/{name} under {root}: {listed} — pass --checkout <path>")
    raise HarvestError(
        f"no skills checkout found: not above this script, and none under {root} holds skills/{name} — "
        "pass --checkout <path> if one exists elsewhere. Otherwise this machine has no source to file "
        "a skill fix against: report skill friction in the harvest report and file nothing."
    )


def worktree_main(checkout: Path) -> Path | None:
    """The checkout this one is a linked worktree of, or None when it is an ordinary one.

    Worth the one small read because it changes the remedy this subcommand offers, and changes it
    silently. In a linked worktree `.git` is a plain file holding `gitdir: <main>/.git/worktrees/
    <name>`; `find_checkout` resolves to the worktree, which is right — the source being edited is
    the one to diff against. What is not right is the push-then-re-install remedy underneath it:
    `skills add <owner>/<repo>` installs the remote's **default branch**, so from a worktree on a
    feature branch the push succeeds and installs nothing, and the verify step then compares an
    installed copy against a checkout that was never published.

    A submodule's `.git` is a file too, naming `…/.git/modules/…`, so the `worktrees` segment is
    what decides.
    """
    marker = checkout / ".git"
    if not marker.is_file():
        return None
    try:
        content = marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not content.startswith("gitdir:"):
        return None
    gitdir = Path(content.removeprefix("gitdir:").strip())
    if not gitdir.is_absolute():
        gitdir = (checkout / gitdir).resolve()
    if gitdir.parent.name != "worktrees":
        return None
    common = gitdir.parent.parent
    return common.parent if common.name == ".git" else common


def _same_file(left: Path, right: Path) -> bool:
    if not left.is_file() or not right.is_file():
        return False
    return left.read_bytes() == right.read_bytes()


# What a difference in each subdirectory actually costs. Printed per differing subdirectory rather
# than as one sentence covering both: a references-only difference was reported with the `scripts/`
# consequence attached ("an earlier call may have run the other copy"), which is a warning about
# something that cannot happen for an inert file. Confirmed 2026-09-02 on this skill's own output.
SUBDIR_CONSEQUENCE = {
    "scripts": "shelled out to, so an *earlier* call in this session may have run the other copy",
    "references": "read on demand and inert — nothing in this session ran from it",
}


def _subdir_diffs(installed: Path, checkout: Path) -> list[str]:
    """Which of `scripts/` and `references/` differ, reported apart from `SKILL.md`.

    They fail differently and only one of them can go stale in a session's context. `SKILL.md` is
    held in context, so a change there means re-read. `scripts/` is shelled out to, so the next call
    already runs the new code — but a call made *earlier* in the session ran the old one. And
    `references/` is read on demand and inert. A directory-scoped comparison cannot tell them apart,
    and fired the most expensive branch in the procedure on a references-only commit (2026-08-30).
    """
    differing: list[str] = []
    for sub in ("scripts", "references"):
        left, right = installed / sub, checkout / sub
        if not left.exists() and not right.exists():
            continue
        left_files = _tracked_files(left)
        right_files = _tracked_files(right)
        if left_files.keys() != right_files.keys() or any(
            left_files[rel].read_bytes() != right_files[rel].read_bytes() for rel in left_files.keys() & right_files
        ):
            differing.append(sub)
    return differing


def _tracked_files(root: Path) -> dict[str, Path]:
    """Every real file under `root`, keyed by its path relative to it.

    `__pycache__` is excluded, and that is not tidiness: the checkout accumulates one the moment a
    script is imported, the installed copy does not, and comparing them raw reported every skill's
    `scripts/` as differing — a false "the install is behind" on three skills at once, which is the
    exact reading this comparison exists to produce truthfully.
    """
    if not root.is_dir():
        return {}
    return {
        str(p.relative_to(root)): p
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def skill_state(runner: Runner, name: str, checkout: Path, installed_root: Path, since: str | None) -> dict[str, Any]:
    source = checkout / "skills" / name
    installed = installed_root / name
    rel = f"skills/{name}"
    state: dict[str, Any] = {"skill": name, "installed": str(installed), "checkout": str(source)}

    if not source.is_dir():
        state["verdict"] = "no such skill in the checkout"
        return state
    if not installed.is_dir():
        state["verdict"] = "not installed — every path a rule names for other sessions is dead"
        return state

    same = _same_file(installed / "SKILL.md", source / "SKILL.md")
    dirty = runner(["git", "-C", str(checkout), "status", "--porcelain", "--", rel]).lines
    upstream, _ = upstream_of(runner, checkout)
    ahead = (
        runner(["git", "-C", str(checkout), "log", f"{upstream}..HEAD", "--oneline", "--", rel]).lines
        if upstream
        else []
    )
    last = runner(["git", "-C", str(checkout), "log", "-1", "--format=%cI", "--", f"{rel}/SKILL.md"]).out.strip()

    state |= {
        "skill_md_identical": same,
        "subdirs_differing": _subdir_diffs(installed, source),
        "checkout_dirty": dirty,
        "unpushed_commits": ahead,
        "skill_md_last_commit": last,
    }

    # The three causes of a difference, which the diff alone cannot tell apart. Confirmed both ways
    # a day apart in 2026-08-30/29: the same non-empty diff meant "re-install" on a clean, level
    # checkout and "another session is mid-restructure, touch nothing" on a dirty one.
    if same:
        state["verdict"] = "installed copy matches the checkout"
    elif dirty:
        touched = any(x.endswith("SKILL.md") for x in dirty)
        whose = "SKILL.md itself is uncommitted" if touched else "elsewhere in the skill"
        state["verdict"] = (
            f"checkout DIRTY ({whose}) — work in progress; a re-install cannot deliver it, so report and move on"
        )
    elif ahead:
        state["verdict"] = (
            f"unpushed skill work ({len(ahead)} commit(s)) — the installer clones from the remote, so "
            "a re-install reinstalls the same stale copy; the push belongs to whoever authored them"
        )
    else:
        state["verdict"] = "install is stale against a clean, pushed checkout — a re-install is the remedy"

    if since and last:
        moved = as_instant(last) is not None and as_instant(since) is not None and as_instant(last) > as_instant(since)
        state["moved_since_session_start"] = moved
        if moved:
            moves = runner(
                ["git", "-C", str(checkout), "log", f"--since={since}", "--format=%h %an %s", "--", rel]
            ).lines
            state["moves_since_session_start"] = moves
            # Re-reading exists for *another* session's commit landing under this one's feet. When
            # every move is this run's own, the context holding the newest text is not stale and the
            # expensive branch fires on the case it was never about (confirmed 2026-09-02, four
            # skills, all four moved by the session's own commits).
            state["verdict"] += (
                f"; SKILL.md moved after this session began ({len(moves)} commit(s)) — re-read it from "
                "whichever side is ahead, unless every one of those commits is this session's own"
            )
    return state


def cmd_skills_state(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    checkout = find_checkout(args.checkout)
    names = args.skill or list(DEFAULT_SKILLS)
    if args.all:
        names = sorted(p.name for p in (checkout / "skills").iterdir() if p.is_dir())
    installed_root = Path(args.installed).expanduser() if args.installed else INSTALLED_SKILLS
    states = [skill_state(runner, name, checkout, installed_root, args.since) for name in names]
    main = worktree_main(checkout)
    plans_py = find_plans_py(checkout)
    # The command step 6 runs to file a skill fix from any other repo. Printed here, with the
    # detected checkout in it, so no skill body has to name where the author keeps the source.
    filing = f"python3 {plans_py} new <topic> --for {main or checkout}" if plans_py else None
    payload = {
        "checkout": str(checkout),
        "worktree_of": str(main) if main else None,
        "installed_root": str(installed_root),
        "file_a_fix": filing,
        "skills": states,
    }
    if not args.json:
        _print_skills_state(payload, bool(args.since))
    return payload


def _print_skills_state(payload: dict[str, Any], since_given: bool) -> None:
    print(f"checkout: {payload['checkout']}\ninstalled: {payload['installed_root']}")
    if payload["worktree_of"]:
        print(f"worktree: a linked worktree of {payload['worktree_of']}")
        print("  the installer clones the remote's DEFAULT branch, so a push from here installs")
        print("  nothing until this branch is merged — offer that, not a re-install")
    if payload["file_a_fix"]:
        print(f"file a fix from another repo: {payload['file_a_fix']}")
    if not since_given:
        print("note: --since <session start> adds the moved-after-this-session-began check")
    for state in payload["skills"]:
        print(f"\n== {state['skill']} ==")
        print(f"  {state['verdict']}")
        for sub in state.get("subdirs_differing", []):
            print(f"  also differing: {sub}/ — {SUBDIR_CONSEQUENCE[sub]}")
        for line in state.get("checkout_dirty", [])[:10]:
            print(f"  dirty: {line}")
        for line in state.get("unpushed_commits", []):
            print(f"  unpushed: {line}")
        for line in state.get("moves_since_session_start", []):
            print(f"  moved since start: {line}")


# --------------------------------------------------------------------------------------------
# subcommand: sweep
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Process:
    ppid: int
    pgid: int
    stat: str
    etimes: int
    args: str


def process_table(runner: Runner) -> dict[int, Process]:
    return _windows_process_table(runner, os.getpid()) if WINDOWS else _posix_process_table(runner)


def _posix_process_table(runner: Runner) -> dict[int, Process]:
    ran = runner(list(PS_ARGV))
    table: dict[int, Process] = {}
    for line in ran.lines:
        parts = line.split(None, 5)
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        pid, ppid, pgid, stat, etimes, args = parts
        table[int(pid)] = Process(int(ppid), int(pgid), stat, int(etimes) if etimes.isdigit() else 0, args)
    return table


def _windows_process_table(runner: Runner, mine: int) -> dict[int, Process]:
    """The same table from `Get-CimInstance Win32_Process`, which has no process groups.

    `pgid` is what `processes()` uses to leave this sweep's own pipeline out of the survivors, so
    here every process is its own group except this script's direct children, which join its group
    — the PowerShell reading the table is one of them, and reporting it would be the sweep
    measuring itself. `stat` has no Windows equivalent and is left empty.
    """
    ran = runner(list(PS_WINDOWS_ARGV))
    table: dict[int, Process] = {}
    for line in ran.lines:
        parts = line.split("\t", 3)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        pid, ppid, age = int(parts[0]), int(parts[1]), parts[2]
        args = parts[3] if len(parts) == 4 else ""
        table[pid] = Process(ppid, mine if ppid == mine else pid, "", int(age) if age.isdigit() else 0, args)
    return table


def processes(runner: Runner, table: dict[int, Process] | None = None) -> dict[str, Any]:
    """Survivors of the turn that spawned them, plus everything holding a listening socket.

    Two populations, deliberately: descendants of this session's own harness process (the
    backgrounded poll nobody killed — confirmed 2026-08-28, four CI-poll loops 36 hours old whose
    exit condition could never be true), and anything machine-wide that looks like a watcher or a
    server. The second drops "this session started" on purpose: the harder case is a process this
    session *reused* because the port answered, whose own session ended without ever harvesting it.

    Matching is done on `ps` output rather than with `pgrep -f`, whose full-cmdline match hits the
    harness's own `zsh -c … eval` wrapper and reports it as a real process.
    """
    table = process_table(runner) if table is None else table
    # An empty table means the listing did not run — it cannot omit the process reading it.
    # Reporting zero survivors there would be the "clean bill of health from a tool that never ran"
    # this sweep exists to prevent.
    if not table:
        what = "Get-CimInstance Win32_Process" if WINDOWS else "`ps -eo`"
        return {"available": False, "why": f"no process listing — {what} produced nothing here"}
    mine = os.getpid()
    my_group = table[mine].pgid if mine in table else -1
    chain: list[int] = []
    cursor = mine
    while cursor in table and cursor > 1:
        chain.append(cursor)
        cursor = table[cursor].ppid
    harness = next((pid for pid in chain if "claude" in table[pid].args), None)

    def row(pid: int, proc: Process, **extra: Any) -> dict[str, Any]:
        return {"pid": pid, "stat": proc.stat, "etimes": proc.etimes, "args": proc.args[:200], **extra}

    # This call's own pipeline is not a survivor. Excluded by process group rather than by age: the
    # `ps` reading the table and whatever is filtering its output both show up as children of the
    # harness with an age of zero, and reporting them as "processes this session left running" is
    # the sweep measuring itself.
    descendants: list[dict[str, Any]] = []
    if harness is not None:
        for pid, proc in table.items():
            if pid in chain or pid == harness or proc.pgid == my_group:
                continue
            walker, depth = proc.ppid, 0
            while walker in table and depth < 12:
                if walker == harness:
                    descendants.append(row(pid, proc))
                    break
                walker, depth = table[walker].ppid, depth + 1

    interesting = [
        row(pid, proc, kind="server" if SERVER_RE.search(proc.args) else "watcher")
        for pid, proc in table.items()
        if (WATCHER_RE.search(proc.args) or SERVER_RE.search(proc.args)) and pid not in chain and proc.pgid != my_group
    ]
    return {
        "available": True,
        "harness_pid": harness,
        "session_children": sorted(descendants, key=lambda d: -int(d["etimes"])),
        "watchers_and_servers": sorted(interesting, key=lambda d: -int(d["etimes"])),
    }


DIRECTORY_ARG_RE = re.compile(r"--directory[= ]([^\s]+)")
SECRET_NAMES = (".env", ".env.local", ".envrc", "secrets.json", ".netrc", "credentials")


def _served_directory(pid: int, args: str) -> Path | None:
    """What a listening process actually serves: its `--directory`, else its working directory.

    Only asked of something that looks like a file server. Every process has a working directory,
    and reading one as "what it serves" turned a browser whose cwd happened to be a repository into
    a finding about that repository — a false positive in the report's most alarming section.
    """
    match = DIRECTORY_ARG_RE.search(args)
    if match:
        return Path(match.group(1).strip("'\"")).expanduser()
    if not SERVER_RE.search(args):
        return None
    try:
        return Path(f"/proc/{pid}/cwd").resolve(strict=True)
    except OSError:
        return None


def _ss_listeners(lines: list[str]) -> list[tuple[str, list[tuple[str, int]]]]:
    """`ss -ltnp` rows as (local address, [(process name, pid), ...]), header dropped."""
    out: list[tuple[str, list[tuple[str, int]]]] = []
    for line in lines[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        who = [(name, int(pid)) for name, pid in re.findall(r'\("([^"]+)",pid=(\d+)', line)]
        out.append((fields[3], who))
    return out


def _netstat_listeners(lines: list[str], table: dict[int, Process]) -> list[tuple[str, list[tuple[str, int]]]]:
    """`netstat -ano` rows in the same shape: only TCP rows in LISTENING state carry a listener,
    and the process name comes from the table since netstat prints the pid alone. Reasoned from
    the documented column layout (`Proto  Local Address  Foreign Address  State  PID`), not from a
    Windows run."""
    out: list[tuple[str, list[tuple[str, int]]]] = []
    for line in lines:
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[3].upper() != "LISTENING":
            continue
        if not fields[4].isdigit():
            continue
        pid = int(fields[4])
        proc = table.get(pid)
        # `PureWindowsPath` so the basename is right whatever platform the tests run the parser on.
        name = PureWindowsPath(proc.args.split()[0]).name if proc and proc.args.split() else f"pid {pid}"
        out.append((fields[1], [(name, pid)]))
    return out


def sockets(runner: Runner, table: dict[int, Process] | None = None) -> dict[str, Any]:
    """What the survivors *expose*, which `ps` cannot see and liveness never flags.

    A development server's default bind is usually every interface, and that default is invisible
    locally: bound to loopback or to the world, every local run behaves identically and only the
    reachable audience differs. Confirmed 2026-08-31: `python3 -m http.server --directory <repo>`,
    24 hours up, on `0.0.0.0`, serving that repository's `.env` and `.git` to the whole LAN.

    **Liveness and bind address are two of three questions, and the third is what it serves.** A
    loopback bind narrows the audience; it does not close the finding, and framing the whole check
    as reachability is what makes a run stop at the safe-looking branch. Confirmed 2026-09-02: an
    `http.server` deliberately bound to `127.0.0.1` by the repo's own task, three and a half hours
    old, orphaned by a one-shot command, serving a repository root whose gitignored `.env` answered
    200. Loopback is a boundary against the LAN and against nothing else running as this user, which
    on a machine with several agent sessions and a browser is not a small set. So the served
    directory is resolved here and reported whatever the bind, which turns "serves the repo root"
    from an inference into a measurement.
    """
    argv = list(NETSTAT_WINDOWS_ARGV if WINDOWS else SS_ARGV)
    ran = runner(argv)
    if not ran.ok:
        return {"available": False, "why": ran.err.strip() or f"{argv[0]} exited {ran.code}"}
    table = process_table(runner) if table is None else table
    listeners: list[dict[str, Any]] = []
    for local, who in _netstat_listeners(ran.lines, table) if WINDOWS else _ss_listeners(ran.lines):
        host = local.rsplit(":", 1)[0]
        served: list[dict[str, Any]] = []
        for name, pid in who:
            proc = table.get(pid)
            directory = _served_directory(pid, proc.args if proc else "")
            if directory is None:
                served.append({"name": name, "pid": pid})
                continue
            readable = [n for n in SECRET_NAMES if (directory / n).exists()]
            served.append(
                {
                    "name": name,
                    "pid": pid,
                    "serves": str(directory),
                    "is_repo_root": (directory / ".git").exists(),
                    "readable_secrets": readable,
                }
            )
        listeners.append({"local": local, "exposed": host not in LOOPBACK, "processes": served})
    return {
        "available": True,
        "listeners": listeners,
        "exposed": [x for x in listeners if x["exposed"]],
        "over_a_repo": [
            x for x in listeners if any(p.get("is_repo_root") or p.get("readable_secrets") for p in x["processes"])
        ],
    }


def _docker_instant(row: str) -> datetime | None:
    """`2026-09-01 12:33:44 +0300 EEST` — docker's own `CreatedAt`, which no ISO parser takes."""
    parts = row.rsplit("\t", maxsplit=1)[-1].split()
    if len(parts) < 3:
        return None
    return as_instant(f"{parts[0]}T{parts[1]}{parts[2]}")


def disk(runner: Runner, since: str | None) -> dict[str, Any]:
    """Container images, build caches and interpreters — gigabytes no repository can see.

    Reported with sizes so the user can approve a removal line; never removed here. The build cache
    is shared with every other project on the machine, and an image another session is about to
    reuse costs a rebuild.
    """
    out: dict[str, Any] = {}
    if shutil.which("docker"):
        df = runner(["docker", "system", "df"])
        out["docker_system_df"] = df.lines if df.ok else [f"docker system df exited {df.code}"]
        images = runner(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"])
        rows = images.lines if images.ok else []
        out["images"] = rows[:40]
        cutoff = as_instant(since) if since else None
        if cutoff:
            out["images_since_session_start"] = [
                row for row in rows if (created := _docker_instant(row)) is not None and created > cutoff
            ]
    else:
        out["docker"] = "not installed"
    if shutil.which("uv"):
        pythons = runner(["uv", "python", "list", "--only-installed"])
        out["uv_pythons"] = pythons.lines if pythons.ok else []
    return out


def store_state(runner: Runner, name: str, path: Path, since: str | None) -> dict[str, Any]:
    """A store outside every working tree. Two of them fail differently, so both are checked.

    The plans store is a git repository, so its failure is an *uncommitted* plan: not a commit, so
    no ahead-count anywhere sees it, and nothing walks to a directory outside every working tree.
    The research library is not version-controlled at all, so its failure is a half-finished entry —
    a clone without its metadata file, or one that failed partway.
    """
    if not path.is_dir():
        return {"store": name, "path": str(path), "present": False}
    state: dict[str, Any] = {"store": name, "path": str(path), "present": True}
    if (path / ".git").exists():
        state["dirty"] = runner(["git", "-C", str(path), "status", "--porcelain"]).lines
        upstream, why = upstream_of(runner, path)
        state["upstream"] = upstream
        if upstream:
            state["unpushed"] = runner(["git", "-C", str(path), "log", f"{upstream}..HEAD", "--format=%h %an %s"]).lines
        else:
            state["note"] = why + " (the sensitive tier deliberately has no remote)"
    else:
        cutoff = as_instant(since) if since else None
        entries = _library_entries(path)
        state["changed_since_session_start"] = [
            str(entry.relative_to(path))
            for entry in entries
            if cutoff is not None and datetime.fromtimestamp(entry.stat().st_mtime, UTC) > cutoff
        ]
        # A half-finished entry is this store's characteristic failure: a clone without its
        # provenance file, or one that failed partway. Nothing else on the machine can see it,
        # because the store is not version-controlled at all.
        state["entries_without_provenance"] = [
            entry.relative_to(path).as_posix() for entry in entries if not _has_provenance(entry)
        ][:20]
    return state


def _library_entries(root: Path) -> list[Path]:
    """One level below each bucket — `repos/<entry>`, `pages/<entry>`, `docs/<file>`.

    The buckets themselves are not entries, and treating them as such reported the whole library as
    three unprovenanced entries: true of nothing, and it buries the one entry that really is
    missing its `SOURCE.md`.
    """
    buckets = [d for d in (root / "repos", root / "pages", root / "docs") if d.is_dir()]
    return sorted(
        entry
        for bucket in (buckets or [root])
        for entry in bucket.iterdir()
        if not entry.name.startswith(".") and not entry.name.endswith(".source.md")
    )


def _has_provenance(entry: Path) -> bool:
    if entry.is_dir():
        return (entry / "SOURCE.md").is_file()
    return entry.with_suffix(entry.suffix + ".source.md").is_file()


def find_plans_py(checkout: Path | None) -> Path | None:
    candidates = [INSTALLED_SKILLS / "plan-docs" / "scripts" / "plans.py"]
    if checkout:
        candidates.append(checkout / "skills" / "plan-docs" / "scripts" / "plans.py")
    return next((c for c in candidates if c.is_file()), None)


def absorb_queue(runner: Runner, plans_py: Path | None, repo: Path) -> dict[str, Any]:
    """Plans filed *for* this repo that nobody has taken — read-only, never `--apply`.

    Run here even though `plan-docs` tells every session to run it first: the queue refills for as
    long as the session runs, because the sessions filing into it run concurrently. Measured
    2026-08-30 in a session that followed the first-call rule correctly — 4 plans at start, 4 more
    two hours in, and one at five hours that was a credential exposure.
    """
    if plans_py is None:
        return {"available": False, "why": "plans.py not found"}
    ran = runner([sys.executable, str(plans_py), "absorb", "--path", str(repo), "--json"])
    if not ran.ok:
        return {"available": True, "error": ran.err.strip() or f"exited {ran.code}"}
    try:
        return {"available": True, "queue": json.loads(ran.out or "{}")}
    except json.JSONDecodeError:
        return {"available": True, "raw": ran.lines}


DEPENDS_ON_RE = re.compile(r"^depends_on:\s*(.+)$")


def depends_on(repo: Path) -> list[dict[str, Any]]:
    """`depends_on` plans, matched at line start and inside the frontmatter block only.

    A bare search for the word also hits a plan whose body tabulates a data schema having a field of
    that name, and a false positive here reads exactly like a real queue entry. The tag carries two
    meanings and they take opposite answers — work parked because that repo was mid-restructure
    (readiness is a question about that repo) and "this plan cannot land until that repo changes"
    (readiness is a question about the plan). This lists them with their targets; the sort into the
    two kinds is a reading, and belongs to the agent.
    """
    plans_dir = repo / "plans"
    if not plans_dir.is_dir():
        return []
    found: list[dict[str, Any]] = []
    for path in sorted(plans_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        for line in lines[1:]:
            if line.strip() == "---":
                break
            match = DEPENDS_ON_RE.match(line)
            if match:
                raw = match.group(1).strip().strip("[]")
                found.append(
                    {
                        "plan": path.name,
                        "targets": [t.strip().strip("'\"") for t in raw.split(",") if t.strip()],
                    }
                )
    return found


def ci_runs(runner: Runner, repo: Path, branch: str, since: str | None) -> dict[str, Any]:
    """CI for what this session pushed, read as JSON rather than watched.

    `--json` has no exit code to lose, so there is nothing for a pipe to take away — which is the
    whole argument, after three separate harvests piped `gh run watch --exit-status` into `tail` and
    reported the filter's `0`.
    """
    if not shutil.which("gh"):
        return {"available": False, "why": "gh not installed"}
    ran = runner(
        [
            "gh",
            "run",
            "list",
            "--branch",
            branch,
            "--limit",
            "10",
            "--json",
            "databaseId,workflowName,status,conclusion,headSha,createdAt,event",
        ],
        cwd=repo,
    )
    if not ran.ok:
        return {"available": True, "error": ran.err.strip() or f"gh run list exited {ran.code}"}
    try:
        runs = json.loads(ran.out or "[]")
    except json.JSONDecodeError:
        return {"available": True, "error": "gh returned unparsable JSON"}
    if since:
        runs = [r for r in runs if not before(str(r.get("createdAt", "")), since)]
    unfinished = [r for r in runs if r.get("status") not in ("completed", None)]
    failed = [r for r in runs if r.get("conclusion") not in ("success", None, "")]
    return {"available": True, "runs": runs, "in_flight": unfinished, "not_green": failed}


HOME_PATH_RE = re.compile(r"(?:~|/home/[\w.-]+)/[\w./@-]+")
TEST_PATH_RE = re.compile(r"(^|/)(tests?|conftest)(/|\.py$)|(^|/)test_[\w-]+\.py$|_test\.py$")


def _is_test_path(path: str) -> bool:
    return bool(path) and bool(TEST_PATH_RE.search(path))


def promised_paths(entries: Iterable[dict[str, Any]]) -> list[str]:
    """Paths this session wrote *into a file* that do not exist on this machine.

    A rule written into an always-loaded instructions file, or a `SKILL.md` command block, names a
    path — usually an installed copy, not the checkout the session was editing. Confirmed
    2026-08-29: a session deployed a `~/AGENTS.md` rule pointing at
    `~/.agents/skills/<name>/scripts/<file>` while the installed skill had no `scripts/` directory,
    so a machine-wide rule instructed every future session to run a file that did not exist. The
    checkout worked perfectly throughout, which is why nothing surfaced it.
    """
    missing: dict[str, None] = {}
    for _, block in iter_blocks(entries):
        if block.get("type") != "tool_use" or block.get("name") not in ("Edit", "Write"):
            continue
        payload = block.get("input")
        if not isinstance(payload, dict):
            continue
        # A path written into a *test* is a fixture: it is supposed not to exist, and that is
        # frequently the whole point of the test. Confirmed 2026-09-02 by this check reporting
        # `~/.agents/skills/demo/scripts/gone.py` — the literal argument of the test that pins this
        # very function — as a machine-wide instruction pointing at a missing file.
        if _is_test_path(str(payload.get("file_path", ""))):
            continue
        body = " ".join(str(payload.get(key, "")) for key in ("new_string", "content"))
        for match in HOME_PATH_RE.finditer(body):
            candidate = match.group(0).rstrip(".,;:)`\"'")
            if "<" in candidate or "*" in candidate or "." not in Path(candidate).name:
                continue
            if not Path(candidate).expanduser().exists():
                missing[candidate] = None
    return sorted(missing)


def _touched_repos(runner: Runner, extra: Sequence[str], entries: Sequence[dict[str, Any]]) -> list[Path]:
    """The repos to sweep: every git root the session wrote into or pointed a command at, plus
    `--repo`, and the current one when the transcript shows nothing.

    **A reference clone under `$RESEARCH_HOME` is excluded**, and the exclusion is not tidiness. Those
    are disposable vendor checkouts: fetching one asks a stranger's remote (which failed outright on
    a shallow single-branch clone), and reading its CI reports a stranger's workflow runs as though
    this session had pushed them. Neither is a loose end this session can own — `research-update`
    refreshes them and `research-library`'s `library.py check` is their checker. Confirmed
    2026-09-02: one `cd` into a clone to read its refspec pulled `astral-sh/uv` into the sweep, which
    then reported eight of that project's own CI runs and an untracked `SOURCE.md` (which every
    conformant entry has) as findings.
    """
    library = Path(os.environ.get("RESEARCH_HOME", str(Path.home() / "research"))).expanduser()
    repos: dict[str, Path] = {}
    candidates = [*(Path(p).expanduser() for p in extra), *written_paths(entries), *shell_targets(entries)]
    for raw in candidates or [Path.cwd()]:
        root = git_root(runner, raw)
        if root is not None and not root.is_relative_to(library):
            repos[str(root)] = root
    if not repos:
        root = git_root(runner, Path.cwd())
        if root is not None:
            repos[str(root)] = root
    return sorted(repos.values())


def _stores() -> list[tuple[str, Path]]:
    """The two plans stores as `plan-docs` resolves them — variable, then its config, then its
    default — and the research library. Two readers of one source of truth, not two defaults."""
    cfg = plan_docs_config()
    store = Path(os.environ.get("PLANS_HOME") or str(cfg.get("store") or "~/plans")).expanduser()
    sensitive_default = store.parent / f"{store.name}-sensitive"
    sensitive = Path(os.environ.get("PLANS_SENSITIVE_HOME") or str(cfg.get("sensitive_store") or sensitive_default))
    return [
        ("plans", store),
        ("plans-sensitive", sensitive.expanduser()),
        ("research", Path(os.environ.get("RESEARCH_HOME", str(Path.home() / "research"))).expanduser()),
    ]


def cmd_sweep(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    transcript, transcript_note = _sweep_transcript(args)
    since = args.since or (transcript.started if transcript else None)
    entries = transcript.entries if transcript else []
    repos = _touched_repos(runner, args.repo, entries)
    written = written_paths(entries)
    sections = set(args.only or [])

    def wanted(*names: str) -> bool:
        return not sections or bool(sections.intersection(names))

    # The two expensive inputs, shared by the sections that need them: one `ps` for processes and
    # sockets, one git pass for the repo report and CI.
    table = process_table(runner) if wanted("processes", "sockets") else {}
    states = [repo_state(runner, p, since, not args.no_fetch, written) for p in repos] if wanted("repos", "ci") else []
    producers: dict[str, Callable[[], dict[str, Any]]] = {
        "processes": lambda: {"processes": processes(runner, table)},
        "sockets": lambda: {"sockets": sockets(runner, table)},
        "disk": lambda: {"disk": disk(runner, since)},
        "repos": lambda: {"repos": [asdict(state) for state in states]},
        "ci": lambda: {"ci": {s.path: ci_runs(runner, Path(s.path), s.branch, since) for s in states}},
        "stores": lambda: _sweep_stores(runner, args.checkout, repos, since),
        "plans": lambda: {"depends_on": {str(path): depends_on(path) for path in repos}},
        "paths": lambda: _sweep_loose_files(runner, entries) if entries else {},
    }

    payload: dict[str, Any] = {
        "boundary": args.boundary,
        "session_started": since,
        "transcript": transcript.as_dict() if transcript else {"note": transcript_note},
    }
    for name, produce in producers.items():
        if wanted(name):
            payload |= produce()

    if args.json:
        return payload
    _print_sweep(payload)
    return payload


def _sweep_stores(runner: Runner, checkout: str | None, repos: Sequence[Path], since: str | None) -> dict[str, Any]:
    plans_py = find_plans_py(_checkout_or_none(checkout))
    return {
        "stores": [store_state(runner, name, path, since) for name, path in _stores()],
        "absorb": {str(path): absorb_queue(runner, plans_py, path) for path in repos},
    }


def _sweep_loose_files(runner: Runner, entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "written_outside_any_repo": [
            str(p) for p in written_paths(entries) if git_root(runner, p) is None and p.exists()
        ],
        "paths_named_but_missing": promised_paths(entries),
    }


def _sweep_transcript(args: argparse.Namespace) -> tuple[Transcript | None, str]:
    """The sweep still runs without a transcript, but says so — most of it is machine state.

    An explicit `--session`/`--job`/`--expect` that fails to resolve is an error rather than a
    degraded run: the caller named a session, and quietly sweeping a different scope is how a report
    ends up describing somebody else's work.
    """
    try:
        return resolve_transcript(args.session, args.job, args.expect, Path.cwd()), ""
    except HarvestError as error:
        if args.session or args.job or args.expect:
            raise
        return None, str(error)


def _checkout_or_none(explicit: str | None) -> Path | None:
    try:
        return find_checkout(explicit)
    except HarvestError:
        return None


def _print_sweep(payload: dict[str, Any]) -> None:
    """The grouped report. One printer per section, because the sections are read separately."""
    print(f"# boundary: {payload.get('boundary') or '(none passed — pass --boundary)'}")
    print(f"# session started: {payload.get('session_started')}")
    transcript = payload.get("transcript", {})
    print(f"# transcript: {transcript.get('path', transcript.get('note'))}")
    _print_processes(payload.get("processes"))
    _print_sockets(payload.get("sockets"))
    _print_disk(payload.get("disk"))
    for state in payload.get("repos", []):
        _print_repo(state)
    for repo, result in (payload.get("ci") or {}).items():
        _print_ci(repo, result)
    for state in payload.get("stores", []):
        _print_store(state)
    for repo, result in (payload.get("absorb") or {}).items():
        _print_absorb(repo, result)
    for repo, tagged in (payload.get("depends_on") or {}).items():
        _print_depends_on(repo, tagged)
    _print_loose_files(payload)


def _print_processes(procs: dict[str, Any] | None) -> None:
    if procs is None:
        return
    print("\n== processes ==")
    if not procs.get("available"):
        print(f"  unavailable: {procs.get('why')}")
        return
    children = procs["session_children"]
    print(f"  this session's surviving children: {len(children)}")
    for row in children[:15]:
        print(f"    pid {row['pid']:>7} {row['stat']:<4} {row['etimes']:>7}s  {row['args']}")
    others = procs["watchers_and_servers"]
    print(f"  watchers and servers machine-wide: {len(others)}")
    for row in others[:15]:
        print(f"    pid {row['pid']:>7} {row['kind']:<8} {row['etimes']:>7}s  {row['args']}")


def _print_sockets(socks: dict[str, Any] | None) -> None:
    if socks is None:
        return
    print("\n== listening sockets ==")
    if not socks.get("available"):
        print(f"  unavailable: {socks.get('why')}")
        return
    for row in socks["listeners"]:
        flag = "EXPOSED beyond loopback" if row["exposed"] else "loopback"
        who = ", ".join(f"{p['name']}/{p['pid']}" for p in row["processes"])
        print(f"    {row['local']:<28} {flag:<24} {who}")
        for proc in row["processes"]:
            if proc.get("is_repo_root") or proc.get("readable_secrets"):
                secrets = ", ".join(proc.get("readable_secrets", [])) or "none by name"
                print(f"      serves {proc['serves']} — repo root, readable: {secrets}")
                print("      a loopback bind narrows the audience; it does not close this finding")


def _print_disk(disks: dict[str, Any] | None) -> None:
    if disks is None:
        return
    print("\n== disk artifacts outside any repo ==")
    for line in disks.get("docker_system_df", [disks.get("docker", "")]):
        print(f"    {line}")
    for line in disks.get("images_since_session_start", []):
        print(f"    new this session: {line}")


def _print_repo(state: dict[str, Any]) -> None:
    print(f"\n== repo {state['path']} ==")
    print(f"  branch {state['branch']} -> upstream {state['upstream']}  (fetch: {state['fetch']})")
    print(f"  dirty: {len(state['dirty'])} path(s)")
    for line in state["dirty"][:10]:
        print(f"    {line}")
    print(f"  unpushed: {len(state['ahead'])} commit(s)")
    for commit in state["ahead"]:
        print(f"    {commit['sha']} {commit['when']} {commit['author']}: {commit['subject']}")
    if state["ahead"]:
        print("    ^ check who authored these before recommending a push: on a machine running")
        print("      parallel sessions the ahead-count is not necessarily this session's work")
    for path in state["overlap"]:
        print(f"  CORRECTION? unpushed and already published this session: {path}")
    for note in state["notes"]:
        print(f"  note: {note}")


def _print_ci(repo: str, result: dict[str, Any]) -> None:
    if not result.get("available"):
        return
    print(f"\n== CI {repo} ==")
    if result.get("error"):
        print(f"  {result['error']}")
    runs = result.get("runs", [])
    if not runs:
        print("  no runs since this session began")
    for run in runs[:8]:
        print(
            f"    {run.get('createdAt')} {run.get('workflowName')} "
            f"{run.get('status')}/{run.get('conclusion')} {str(run.get('headSha'))[:8]}"
        )
    if result.get("in_flight"):
        print(f"  {len(result['in_flight'])} run(s) still in flight — perishable, name it in the report")


def _print_store(state: dict[str, Any]) -> None:
    print(f"\n== store {state['store']} {state['path']} ==")
    if not state.get("present"):
        print("  not present")
        return
    for key in ("dirty", "unpushed", "changed_since_session_start", "entries_without_provenance"):
        for line in state.get(key, []):
            print(f"  {key}: {line}")
    if state.get("note"):
        print(f"  note: {state['note']}")


def _print_absorb(repo: str, result: dict[str, Any]) -> None:
    queue = result.get("queue") or {}
    pending = queue.get("absorbable") or []
    owed = queue.get("retirements_owed") or []
    if not (pending or owed):
        return
    print(f"\n== plans store, for {repo} ==")
    for item in pending:
        print(f"    filed and not taken: {item.get('name', item)} [{item.get('status', '?')}]")
    for item in owed:
        print(f"    retirement owed: {item.get('name', item)}")


def _print_depends_on(repo: str, tagged: list[dict[str, Any]]) -> None:
    if not tagged:
        return
    print(f"\n== depends_on plans in {repo} ==")
    for row in tagged:
        print(f"    {row['plan']} -> {', '.join(row['targets'])}")
    print("    sort these into the tag's two meanings before reporting readiness for any of them")


def _print_loose_files(payload: dict[str, Any]) -> None:
    outside = payload.get("written_outside_any_repo")
    if outside:
        print("\n== files written outside every repository ==")
        for path in outside:
            print(f"    {path}   (no diff, no history — say what would recover it)")
    missing = payload.get("paths_named_but_missing")
    if missing:
        print("\n== paths this session wrote into files that do not exist ==")
        for path in missing:
            print(f"    {path}")


# --------------------------------------------------------------------------------------------
# subcommand: claims
# --------------------------------------------------------------------------------------------


def cmd_claims(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """Green-gate sentences said to the user, counted against the masked exits behind them.

    A re-run settles whether the greens were true. It does not touch the fact that they were
    asserted: a session with a non-zero `exit-masked` has usually told the user "gate green" several
    times, each time on evidence a filter had already discarded, and those sentences stand in the
    conversation whatever the re-run says. "Said the gate was green 15 times on masked calls; re-run
    exits 0, so the claims hold" is a footnote; the same sentence ending "re-run exits 1" is a live
    inaccuracy with a reader.
    """
    transcript = resolve_transcript(args.session, args.job, args.expect, Path.cwd())
    masked = [
        {"timestamp": stamp, "command": command}
        for stamp, command in bash_calls(transcript.entries)
        if EXIT_MASKED_RE.search(command) and before(stamp, args.until)
    ]
    # Every match, not the first per message: a message often makes the claim twice, and an
    # undercount here is the same failure the rule exists to prevent, one level up.
    seen: set[tuple[str, str]] = set()
    claims: list[dict[str, str]] = []
    for stamp, text in assistant_text(transcript.entries):
        if not before(stamp, args.until):
            continue
        for match in GREEN_CLAIM_RE.finditer(text):
            line = _claim_line(text, match.start())
            if (stamp, line) in seen:
                continue
            seen.add((stamp, line))
            claims.append({"timestamp": stamp, "text": match.group(0), "line": line})
    total_bash = len(bash_calls(transcript.entries))
    payload = {
        "transcript": transcript.as_dict(),
        "bash_calls": total_bash,
        "exit_masked": len(masked),
        "green_claims": claims,
        "masked_calls": masked[: args.samples],
    }
    if args.json:
        return payload
    print(f"# transcript: {transcript.path}")
    print(f"# {len(masked)} of {total_bash} Bash calls masked their exit code behind a filter")
    print(f"# {len(claims)} message(s) told the user a gate or suite was green")
    for claim in claims:
        print(f"    {claim['timestamp']}  {claim['line']}")
    for call in payload["masked_calls"]:
        print(f"    masked: {call['command'][:160]}")
    if masked and claims:
        print(
            "\nRe-run the repo's own gate unpiped before believing any of those greens, and report the\n"
            "count with the re-run's verdict attached — the claims are in the conversation either way,\n"
            "and the conversation is the one artefact a later commit cannot amend."
        )
    elif not masked:
        print("\nno masked exits: the session's own green results stand on unfiltered evidence")
    return payload


def _claim_line(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return text[start : end if end != -1 else len(text)].strip()[:200]


# --------------------------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------------------------


def _add_transcript_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session", help="session id or transcript path")
    parser.add_argument("--job", help="background job id, whose state.json names the real transcript")
    parser.add_argument(
        "--expect",
        help="a string this session definitely produced; selects the transcript when no id is given, "
        "and verifies it when one is",
    )


def build_parser() -> argparse.ArgumentParser:
    # The shared flags are on a parent parser rather than on the top-level one, so
    # `harvest.py turns --json` works. With them declared only above the subcommand, argparse
    # accepts them only *before* it — which reads as the flag having been ignored.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output instead of the report")
    common.add_argument("--boundary", help="the step 0 instant, echoed back so a report says which one is in force")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("boundary", parents=[common], help="print the step 0 instant — the harvest's first command")

    transcript = subparsers.add_parser(
        "transcript", parents=[common], help="resolve THIS session's transcript and say how"
    )
    _add_transcript_flags(transcript)

    turns = subparsers.add_parser("turns", parents=[common], help="user turns and AskUserQuestion answers, in order")
    _add_transcript_flags(turns)
    turns.add_argument("--chars", type=int, default=0, help="cap each turn's text (0 = whole text, the default)")
    turns.add_argument("--all", action="store_true", help="include slash-command wrappers and meta turns")

    skills = subparsers.add_parser(
        "skills-state", parents=[common], help="installed copy vs checkout, dirt, unpushed work, moves"
    )
    skills.add_argument("--skill", action="append", help="skill name; repeatable (default: the ones a harvest uses)")
    skills.add_argument("--all", action="store_true", help="every skill in the checkout")
    skills.add_argument("--checkout", help="path to the agent-skills checkout")
    skills.add_argument("--installed", help="installed skills root (default ~/.agents/skills)")
    skills.add_argument("--since", help="session start, for the moved-after-this-session-began check")

    sweep = subparsers.add_parser(
        "sweep", parents=[common], help="processes, sockets, disk, git, CI, stores — one report"
    )
    _add_transcript_flags(sweep)
    sweep.add_argument("--repo", action="append", default=[], help="add a repo the transcript cannot show")
    sweep.add_argument("--since", help="session start (default: the transcript's first timestamp)")
    sweep.add_argument("--no-fetch", action="store_true", help="skip git fetch (offline, or no ssh agent)")
    sweep.add_argument("--checkout", help="path to the agent-skills checkout, for plans.py")
    sweep.add_argument(
        "--only",
        action="append",
        choices=["processes", "sockets", "disk", "repos", "ci", "stores", "plans", "paths"],
        help="run only these sections; repeatable",
    )

    claims = subparsers.add_parser(
        "claims", parents=[common], help="green-gate assertions made to the user, and the masked exits"
    )
    _add_transcript_flags(claims)
    claims.add_argument("--until", help="ignore anything at or after this instant (the boundary)")
    claims.add_argument("--samples", type=int, default=8, help="masked commands to print (default 8)")
    return parser


COMMANDS = {
    "boundary": cmd_boundary,
    "transcript": cmd_transcript,
    "turns": cmd_turns,
    "skills-state": cmd_skills_state,
    "sweep": cmd_sweep,
    "claims": cmd_claims,
}


def main(argv: Sequence[str] | None = None, runner: Runner | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = COMMANDS[args.command](args, runner or LiveRunner())
    except HarvestError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
