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
    harvest.py filed --until <instant>       # a second harvest: what the first one already filed

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
import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
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

# Sentences that tell the user a gate passed. Broad by design — a miss is the failure this check
# exists to prevent — but broad *within a subject*, which is the correction measured 2026-09-08 over
# 1,201 transcripts.
#
# The fourth alternation used to be a bare exit-code phrase with no subject term in it at all, so it
# matched any sentence containing the words: 303 hits corpus-wide, of which a gate-shaped subject
# beside them keeps 158 and drops 145 — a `git fetch` that exited 0, a dry-run that exited 0, and an
# explanation of `gh run list` returning an empty array and exiting 0. Deleting the alternation was
# the cheaper fix and is wrong: the kept half contains real claims no other alternation reaches
# ("Gate re-run unpiped at harvest time: exit 0, 402 tests"). `re-run` earns its place in the subject
# list on the same evidence, and plain `run` is excluded because it readmits the `git fetch` line.
EXIT_CODE = r"(0 errors|exits? 0|exit code 0)"
GATE_SUBJECT = r"(gate|suite|pytest|precommit|pre-commit|quality\.\w+|re-run|tests?|checks?|workflow)"
GREEN_CLAIM_RE = re.compile(
    r"gate[^.\n]{0,40}\b(green|clean|pass(?:es|ed)?)\b"
    r"|\b(precommit|pre-commit|quality\.(?:check|precommit)|pytest|test suite|suite)\b[^.\n]{0,40}"
    r"\b(green|clean|pass(?:es|ed)?|all good)\b"
    r"|\ball (?:tests|checks)\b[^.\n]{0,20}\bpass(?:es|ed)?\b"
    rf"|\b{GATE_SUBJECT}\b[^.\n]{{0,40}}\b{EXIT_CODE}\b"
    rf"|\b{EXIT_CODE}\b[^.\n]{{0,40}}\b{GATE_SUBJECT}\b",
    re.IGNORECASE,
)

# Green claims about **CI**, counted separately rather than folded in. The pattern above has no term
# for CI at all, so "Both CI legs green" matched nothing — 329 sentences corpus-wide, more than the
# whole bare-exit-code alternation, and the phrasing this skill's own step 5 leads a harvest to write.
#
# Separate because the two fail differently and only one pairs with the masked-exit count. A masked
# local gate means the session could not see the result it reported; a CI conclusion is read from
# `gh run list --json`, which has no exit code for a pipe to eat, so a CI green is not usually
# resting on filtered evidence even in a session with a high `exit-masked`. Folding 329 into the
# paired number would have inflated it by half and weakened the one sentence the check exists to
# produce.
GREEN_CI_RE = re.compile(
    r"\b(ci|workflow|check run|actions?)\b[^.\n]{0,40}\b(green|clean|pass(?:es|ed)?|success(?:ful)?)\b"
    r"|\b(green|clean|pass(?:es|ed)?)\b[^.\n]{0,25}\b(ci|workflow|check run)\b",
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


def _contains(expect: str, text: str) -> bool:
    """`expect` as the caller typed it, searched for in raw JSONL.

    A transcript stores a Bash command as a JSON *string*, so its double quotes and backslashes are
    escaped on disk: the file holds `git tag -l \\"X\\"` where the caller typed `git tag -l "X"`. A
    raw substring search therefore misses exactly the specific quoted command a caller is most
    likely to paste, while the vaguer unquoted prefix matches — and the failure surfaces as
    `no transcript resolved`, which reads as "wrong command" rather than "the matcher cannot see
    this shape". Confirmed 2026-09-05: `--expect 'git tag -l "SINGLE-LINE-TEST"'` resolved nothing
    in a session whose transcript held that command three times, while `--expect 'git tag -l'`
    resolved it. Single quotes are not escaped inside a JSON string, so some quoted commands
    matched and some did not, with nothing saying which.

    Comparing escaped forms rather than decoding every line keeps this a substring scan over files
    that run to megabytes each. Both encoders are tried because this script does not write the file:
    `JSON.stringify` leaves non-ASCII alone, `json.dumps` escapes it to `\\uXXXX`, and they agree on
    everything else.
    """
    forms = (expect, json.dumps(expect, ensure_ascii=False)[1:-1], json.dumps(expect)[1:-1])
    return any(form in text for form in dict.fromkeys(forms))


def _by_content(expect: str, cwd: Path) -> list[Path]:
    """Transcripts containing `expect`, newest first — the "grep it for something you know you ran"
    check, used here to *select* rather than only to confirm.

    Scoped to the project directory for `cwd` when one exists, because a marker distinctive enough
    to identify a session is rarely distinctive across every project on the machine.
    """
    slug = project_slug(cwd)
    scoped = PROJECTS_DIR / slug if slug else None
    pool = sorted(scoped.glob("*.jsonl")) if scoped and scoped.is_dir() else list(PROJECTS_DIR.rglob("*.jsonl"))
    hits = [p for p in pool if _contains(expect, p.read_text(encoding="utf-8", errors="replace"))]
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
        found = _contains(expect, path.read_text(encoding="utf-8", errors="replace"))
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


def last_activity(entries: Iterable[dict[str, Any]]) -> str | None:
    """The transcript's own last stamped entry — the moment a process's age is compared against.

    Parsed rather than string-compared: the corpus's standing trap is that a transcript stamps UTC
    with a trailing `Z` while everything else carries an offset, and comparing those as text sorts
    by the offset instead of by the moment.
    """
    instants = [moment for entry in entries if (moment := as_instant(str(entry.get("timestamp", "")))) is not None]
    return max(instants).isoformat() if instants else None


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


def checkouts(root: Path, depth: int = 3) -> list[Path]:
    """Every git checkout under a root, stopping at each `.git`.

    A walk rather than a path: the author keeps repos as `<root>/<host>/<repo>` on one machine and
    would keep them flat as `<root>/<repo>` on another, and a reader's layout is anybody's guess.
    Symlinks are never followed, the same shape `plans.py` uses.
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
                found.append(child)
                continue
            if remaining > 1:
                walk(child, remaining - 1)

    if root.is_dir():
        walk(root, depth)
    return found


def skills_checkouts(name: str, root: Path, depth: int = 3) -> list[Path]:
    """Every git checkout under the projects root that holds `skills/<name>/SKILL.md`."""
    return [repo for repo in checkouts(root, depth) if (repo / "skills" / name / "SKILL.md").is_file()]


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


PRE_CHECK_COMMANDS = ("boundary", "transcript", "skills-state")


def _module_definitions(text: str) -> dict[str, str] | None:
    """Every module-level name and the source that defines it. None when the file will not parse.

    Assignments are included alongside functions because a pattern this script branches on is
    usually a module constant — a changed `GREEN_CLAIM_RE` changes what `claims` reports while every
    function around it is byte-identical.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    lines = text.splitlines()
    out: dict[str, str] = {}
    for node in tree.body:
        source = "\n".join(lines[node.lineno - 1 : node.end_lineno])
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            out[node.name] = source
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = source
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out[node.target.id] = source
    return out


def _reachable(name: str, defs: dict[str, str], seen: set[str] | None = None) -> set[str]:
    """`name` plus every module-level definition reachable from it, by name reference."""
    seen = set() if seen is None else seen
    if name in seen or name not in defs:
        return seen
    seen.add(name)
    try:
        tree = ast.parse(defs[name])
    except SyntaxError:
        return seen
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in defs:
            _reachable(node.id, defs, seen)
    return seen


def entry_points_differing(installed_script: Path, checkout_script: Path) -> list[str] | None:
    """Which subcommands of this script differ between the two copies. None when it cannot tell.

    `skills-state` answers the staleness question from inside the copy under test: on a stale
    install the three subcommands a harvest has already run — `boundary`, `transcript` and
    `skills-state` itself — came from the old code, and no ordering fixes that, because resolving
    the checkout is `skills-state`'s own job. So the exposure is reported rather than removed:
    naming the subcommands whose code actually differs turns "some of what you have already read may
    be stale" into a list, usually an empty one.

    Comparison is per definition rather than per file, because a `harvest.py` diff is nearly always
    somewhere else — observed 2026-09-07, six commits stale, every one of them in `sweep`, so all
    three pre-check answers were current and the run had no way to know it.

    None means the question was not answered — a file that would not parse or a subcommand that
    exists on neither side — and must never be read as "nothing differs".
    """
    try:
        left, right = installed_script.read_text("utf-8"), checkout_script.read_text("utf-8")
    except OSError:
        return None
    old, new = _module_definitions(left), _module_definitions(right)
    if old is None or new is None:
        return None
    differing: list[str] = []
    for command in sorted({n[4:].replace("_", "-") for n in {*old, *new} if n.startswith("cmd_")}):
        entry = f"cmd_{command.replace('-', '_')}"
        names = _reachable(entry, old) | _reachable(entry, new)
        if not names:
            return None
        if any(old.get(n) != new.get(n) for n in names):
            differing.append(command)
    return differing


def skill_state(
    runner: Runner,
    name: str,
    checkout: Path,
    installed_root: Path,
    since: str | None,
    *,
    baseline: str = "this session began",
) -> dict[str, Any]:
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

    subdirs = _subdir_diffs(installed, source)
    state |= {
        "skill_md_identical": same,
        "subdirs_differing": subdirs,
        "checkout_dirty": dirty,
        "unpushed_commits": ahead,
        "skill_md_last_commit": last,
    }

    # What the verdict is about: the parts of the installed copy that decide what a run does.
    # `SKILL.md` is held in context and `scripts/` is executed; `references/` is read on demand and
    # inert, so a difference there changes no run and must not read as a stale install.
    #
    # Until 2026-09-05 this branched on `same` alone, so a skill whose script had changed while its
    # SKILL.md had not reported "installed copy matches the checkout" — with `subdirs_differing`
    # naming `scripts` in the same payload, computed one line above and never read. Found by running
    # this check right after fixing two bugs in THIS script: the installed copy did not contain the
    # function committed an hour earlier and the verdict said it matched. `scripts/` is the likelier
    # half to be stale, too, since SKILL.md changes when the procedure does while a script changes on
    # every fix — and this repo's convention pushes anything derivable out of the body and into a
    # script, so the share this check has to see keeps growing.
    stale_script = "scripts" in subdirs
    if same and not stale_script:
        state["verdict"] = (
            "installed copy matches the checkout"
            if not subdirs
            else "installed copy matches, except references/ — read on demand and inert, so nothing to do"
        )
        return _with_move_check(state, runner, checkout, rel, since, last, baseline)

    # The three causes of a difference, which the diff alone cannot tell apart. Confirmed both ways
    # a day apart in 2026-08-30/29: the same non-empty diff meant "re-install" on a clean, level
    # checkout and "another session is mid-restructure, touch nothing" on a dirty one.
    what = "SKILL.md and scripts/" if stale_script and not same else "scripts/" if stale_script else "SKILL.md"
    if dirty:
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
        state["verdict"] = f"install is stale ({what}) against a clean, pushed checkout — a re-install is the remedy"
    if stale_script:
        # Said separately because the remedy differs: a stale SKILL.md can be re-read from whichever
        # side is ahead, and a stale script cannot — the run executes it.
        state["verdict"] += "; the stale part includes scripts/, which this session EXECUTES rather than reads"
        _note_own_staleness(state, installed, source)
    return _with_move_check(state, runner, checkout, rel, since, last, baseline)


def _note_own_staleness(state: dict[str, Any], installed: Path, source: Path) -> None:
    """When the stale script is the one running, say which of its subcommands that actually affects.

    Only fires when this process was launched from the installed copy being judged: a harvest that
    already runs `harvest.py` from the checkout is using current code and has nothing to re-run.
    """
    running = Path(__file__).resolve()
    if not running.is_relative_to(installed.resolve()):
        return
    differing = entry_points_differing(running, source / "scripts" / running.name)
    state["entry_points_differing"] = differing
    if differing is None:
        state["verdict"] += (
            "; this script IS the stale copy and the two could not be compared — re-run "
            f"{', '.join(PRE_CHECK_COMMANDS)} from the checkout before trusting their answers"
        )
        return
    already_run = [c for c in PRE_CHECK_COMMANDS if c in differing]
    if already_run:
        state["verdict"] += (
            f"; this script IS the stale copy and {', '.join(already_run)} differ — those answers came "
            "from the old code, so re-run them from the checkout"
        )
    else:
        state["verdict"] += (
            f"; this script IS the stale copy, but none of {', '.join(PRE_CHECK_COMMANDS)} differ, so the "
            "answers already collected match what the checkout would have given"
        )
    if differing:
        state["verdict"] += f" (differing: {', '.join(differing)})"


def _with_move_check(
    state: dict[str, Any],
    runner: Runner,
    checkout: Path,
    rel: str,
    since: str | None,
    last: str,
    baseline: str = "this session began",
) -> dict[str, Any]:
    """The moved-after-the-baseline note, appended to whatever verdict was reached.

    Split out when the verdict grew an early return, so the note cannot be reached by one branch and
    missed by another — which is the shape of the defect the early return exists to fix.

    **`baseline` is per skill, because session start is the wrong instant for the skill doing the
    asking.** Confirmed 2026-09-07, session `9164dacd`: the harvest was invoked in the session's last
    minutes, so `session-harvest`'s own body entered context *after* the three commits the check
    reported, and the warning said the held copy might be superseded when it was the newest text on
    the machine. Session start is right for a skill the session leaned on throughout and wrong for
    the one loaded last by construction — which is every harvest, on itself, in the step whose whole
    purpose is deciding whether to trust its own instructions.
    """
    if since and last:
        moved = as_instant(last) is not None and as_instant(since) is not None and as_instant(last) > as_instant(since)
        state["moved_since_session_start"] = moved
        state["move_baseline"] = {"instant": since, "is": baseline}
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
                f"; SKILL.md moved after {baseline} ({len(moves)} commit(s)) — re-read it from "
                "whichever side is ahead, unless every one of those commits is this session's own"
            )
    return state


def cmd_skills_state(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    checkout = find_checkout(args.checkout)
    # `--skill` ADDS to the defaults rather than replacing them, because the skill whose staleness
    # matters most is this one, and naming any other must not be what drops it. Confirmed
    # 2026-09-05: a harvest passed `--skill plan-docs --skill invoke-task-conventions`, got two
    # clean rows, and only a second call naming session-harvest found that its SKILL.md had moved
    # after session start with two unpushed commits — the finding step 0 exists for. `--all` is the
    # replace-everything case and stays one.
    names = list(DEFAULT_SKILLS) + [s for s in (args.skill or []) if s not in DEFAULT_SKILLS]
    source = checkout / "skills"
    held = sorted(p.name for p in source.iterdir() if p.is_dir()) if source.is_dir() else []
    # `DEFAULT_SKILLS` is this skill's own family, and in a checkout that holds none of them the
    # default is three "no such skill in the checkout" rows and no measurement — which is what a
    # reader running this against their own skills repo sees on their first call. The defaults exist
    # so naming another skill cannot drop this one (see above); where this one is not there to drop,
    # there is nothing for them to protect, so the checkout's own skills are the answer. Said out
    # loud rather than swapped silently: a scope that changes without a line is the shape this
    # script's own step 0 is about.
    note = ""
    if not args.all and held and not any(name in held for name in DEFAULT_SKILLS):
        names, note = held, f"none of {', '.join(DEFAULT_SKILLS)} are in this checkout — reporting its own {len(held)}"
    if args.all:
        names = held
    installed_root = Path(args.installed).expanduser() if args.installed else INSTALLED_SKILLS
    since, since_from = _resolve_since(args)
    loads = _skill_load_instants(args)
    states = [
        skill_state(
            runner,
            name,
            checkout,
            installed_root,
            loads.get(name, since),
            baseline=("this skill entered context" if name in loads else "this session began"),
        )
        for name in names
    ]
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
        "scope_note": note,
        "since": since,
        "since_from": since_from,
        "skills": states,
    }
    if not args.json:
        _print_skills_state(payload, bool(since))
    return payload


def _resolve_since(args: argparse.Namespace) -> tuple[str | None, str]:
    """The instant this session began, resolved the way every other subcommand resolves its session.

    **`--since` was a placeholder with no stated source, and that is what made guessing it the
    natural move.** The value exists — `transcript` prints it as `started:` — but step 0's command
    block never said to take it from there, and the two commands are independent, so a session
    batching its tool calls has to supply `--since` before `transcript` has answered.

    Six instances by 2026-09-08, and they err in both directions. Too early widens the window, so
    commits predating the session are reported as having moved under it and the verdict prescribes a
    re-read the evidence does not support — the most expensive step in the procedure, fired on the
    case the skill warns it should not fire on. Too late narrows it and a genuinely superseding
    commit lands outside, which is the failure the whole branch exists to catch, failing closed
    behind a clean report. One harvest guessed ninety minutes early and got the right verdict
    anyway, which is how a placeholder survives: the wrong input produced the right answer.

    The flag stays as an override for a harness that exports no id, and for auditing a window that
    is not this session's — the same shape `--session` already has.

    **A supplied value earlier than the resolved session start is reported, never rejected.** The
    plan that asked this called such a value always a mistake, since no session began before it
    began — but that premise contradicts the flag's own second purpose: auditing a wider window is
    exactly what an earlier instant is for, and refusing it would remove the capability to fix a
    typo. What the note catches is the case the six instances actually were: a guess, which is
    silently indistinguishable from a deliberate audit until the value and the real start are
    printed side by side.
    """
    if args.since:
        return args.since, _supplied_note(args)
    try:
        transcript = resolve_transcript(args.session, args.job, args.expect, Path.cwd())
    except HarvestError:
        # No transcript is the reader's ordinary case, not an error here: the comparison still runs
        # and only the moved-since-start half goes unanswered. Saying so beats reporting nothing
        # moved, which is what a silent `None` would have looked like.
        return None, "no session resolved — 'moved since start' unavailable"
    return transcript.started, f"transcript start ({transcript.path.stem[:8]})"


def _skill_load_instants(args: argparse.Namespace) -> dict[str, str]:
    """When each skill's body entered context, from this session's own `Skill` tool calls.

    The instant that matters for "did this move under me" is when the text was **read**, not when
    the session began, and for a skill invoked late those differ by hours. A harvest is loaded last
    by construction, so session start gives it a false positive on itself every time — in the step
    whose whole purpose is deciding whether to trust its own instructions.

    An explicit `--since` still wins: it is the override, and overriding the baseline for every row
    is a legitimate thing to want. A skill with no load entry — never invoked this session, or a
    harness that records invocations differently — falls back to session start and the report says
    which of the two each row used, because a baseline that changes silently is the defect one level
    up from the one this fixes.
    """
    if args.since:
        return {}
    try:
        entries = resolve_transcript(args.session, args.job, args.expect, Path.cwd()).entries
    except HarvestError:
        return {}
    loads: dict[str, str] = {}

    def record(name: str, stamp: str) -> None:
        # The earliest load is the one to keep: a skill re-invoked later was already in context.
        if name and stamp and name not in loads:
            loads[name] = stamp

    for entry, block in iter_blocks(entries):
        if block.get("type") == "tool_use" and block.get("name") == "Skill":
            payload = block.get("input")
            name = str(payload.get("skill", "")) if isinstance(payload, dict) else ""
            record(name, str(entry.get("timestamp", "")))
    for entry in entries:
        # A user-typed `/<skill>` is not a `Skill` tool call — the harness records it as a
        # `<command-name>` inside a *user* message — so reading tool calls alone misses the
        # invocation path this skill's own description calls the one to rely on. Confirmed
        # 2026-09-08 on the first real `/session-harvest` run after the load-instant check landed:
        # it fell back to session start and produced exactly the eleven-commit false positive the
        # check exists to remove.
        content = entry.get("message", {}).get("content") if isinstance(entry.get("message"), dict) else None
        if entry.get("type") == "user" and isinstance(content, str):
            for match in COMMAND_NAME_RE.finditer(content):
                record(match.group(1), str(entry.get("timestamp", "")))
    return loads


def _supplied_note(args: argparse.Namespace) -> str:
    """`supplied`, plus how it sits against this session's real start when one can be resolved."""
    try:
        started = resolve_transcript(args.session, args.job, args.expect, Path.cwd()).started
    except HarvestError:
        return "supplied — no session to compare it against"
    given, real = as_instant(args.since), as_instant(started or "")
    if given is None or real is None:
        return "supplied"
    minutes = round((given - real).total_seconds() / 60)
    if minutes == 0:
        return f"supplied — this session's own start, {started}"
    where = "before" if minutes < 0 else "after"
    wider = "wider" if minutes < 0 else "narrower"
    return f"supplied — {abs(minutes)} min {where} this session's start of {started}, so the window is {wider}"


def _print_skills_state(payload: dict[str, Any], since_given: bool) -> None:
    print(f"checkout: {payload['checkout']}\ninstalled: {payload['installed_root']}")
    if payload["worktree_of"]:
        print(f"worktree: a linked worktree of {payload['worktree_of']}")
        print("  the installer clones the remote's DEFAULT branch, so a push from here installs")
        print("  nothing until this branch is merged — offer that, not a re-install")
    if payload["file_a_fix"]:
        print(f"file a fix from another repo: {payload['file_a_fix']}")
    if payload.get("scope_note"):
        print(f"scope: {payload['scope_note']}")
    # The value used, always — the specific harm was never the wrong window but that a wrong one was
    # indistinguishable from a right one in the output, so nothing prompted a second look. An
    # operator overriding the default can still override it wrongly.
    if since_given:
        print(f"since: {payload.get('since')}  ({payload.get('since_from')})")
    else:
        print(f"since: unresolved — {payload.get('since_from')}")
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


REPARENTED_RE = re.compile(r"\b(systemd|init|launchd)\b")


def parentage(table: dict[int, Process], proc: Process) -> dict[str, Any]:
    """Who holds this process — the fact the orphan rule turns on, reported rather than fetched.

    `SKILL.md`'s step 5 tells the reader that an orphan reparented to `systemd --user` is a
    different finding from a process a live session still holds, and until 2026-09-06 the sweep
    printed neither the parent nor its command, so every run that reached that rule paid for it in
    two more `ps -o pid,ppid` calls. Confirmed 2026-09-05: a harvest did exactly that, and without
    the second call "orphaned" would have been an assumption — which is how the rule came to exist.

    `orphaned` is deliberately three-valued. A parent missing from the listing is not evidence of
    an orphan, and reporting one as orphaned would be the sweep inventing the fact it exists to
    supply.
    """
    parent = table.get(proc.ppid)
    if proc.ppid <= 1:
        orphaned: bool | None = True
    elif parent is None:
        orphaned = None
    else:
        orphaned = bool(REPARENTED_RE.search(parent.args.split(maxsplit=1)[0] if parent.args else ""))
    return {"ppid": proc.ppid, "parent": parent.args[:80] if parent else "", "orphaned": orphaned}


def started_after(etimes: int, cutoff: str | None) -> bool | None:
    """Whether a process began after a moment. Its age is the only start time the table carries.

    The comparison that separates "my leftover" from "somebody else's process": a listener that
    started after the harvested session's last transcript entry cannot be that session's, whatever
    else it looks like. Confirmed 2026-09-05 — an `http.server` whose start was 36 minutes after the
    session's last activity was nearly reported as that session's own litter.
    """
    moment = as_instant(cutoff) if cutoff else None
    if moment is None:
        return None
    return datetime.now(UTC) - timedelta(seconds=etimes) > moment


def processes(
    runner: Runner, table: dict[int, Process] | None = None, last_activity: str | None = None
) -> dict[str, Any]:
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
        return {
            "pid": pid,
            "stat": proc.stat,
            "etimes": proc.etimes,
            "args": proc.args[:200],
            **parentage(table, proc),
            "started_after_last_activity": started_after(proc.etimes, last_activity),
            **extra,
        }

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


def sockets(
    runner: Runner, table: dict[int, Process] | None = None, last_activity: str | None = None
) -> dict[str, Any]:
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
            # Who holds it and whether it predates the session are what the report reasons about,
            # so they travel with every listener rather than only with the ones serving a directory.
            held: dict[str, Any] = {"name": name, "pid": pid}
            if proc is not None:
                held |= parentage(table, proc)
                held["started_after_last_activity"] = started_after(proc.etimes, last_activity)
            directory = _served_directory(pid, proc.args if proc else "")
            if directory is None:
                served.append(held)
                continue
            readable = [n for n in SECRET_NAMES if (directory / n).exists()]
            served.append(
                held
                | {
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


DOCKER_CALL_RE = re.compile(r"(?:^|[|;&]|\bsudo(?:\s+-A)?\s+)\s*docker\b", re.MULTILINE)
QUOTED_SPAN_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def bare_commands(entries: Iterable[dict[str, Any]]) -> list[str]:
    """This session's Bash commands with quoted spans blanked — the input every attribution reads.

    **A quoted span is where a name appears without being used**, and blanking it is not a detail:
    `rg "docker"` searches for the word, `git commit -m "absorbed <file>"` names a file in a
    sentence, `--expect "library.py add"` quotes a command it is looking for. Skipping this was a
    false positive on the very first live run of the docker check, 2026-09-06 — `rg -n "def
    sweep|docker|listener" harvest.py` matched, because an alternation inside a quoted search
    pattern is a pipe followed by the word, which is command position by every rule a regex knows.

    Searching for a name is the single most likely way it appears in a session that never ran it,
    which is exactly the session these checks exist to protect. Shared rather than repeated so the
    next check cannot be written without it.
    """
    return [QUOTED_SPAN_RE.sub(" ", command) for _, command in bash_calls(entries)]


def invoked_docker(entries: Iterable[dict[str, Any]]) -> bool:
    """Whether the session ran `docker` at all — the cross-check that turns a timestamp into an
    attribution.

    Matched at command position, so a `rg docker` or a sentence naming it is not an invocation.
    A form this misses (an env-assignment prefix, a wrapper script) costs an image reported as
    unattributed, which is the direction that cannot make a false claim.
    """
    return any(DOCKER_CALL_RE.search(command) for command in bare_commands(entries))


def entry_needles(name: str) -> tuple[str, ...]:
    """The spellings a transcript would name one research-library entry by.

    `github.com--seddonym--import-linter` is reached two ways in practice, and only one of them is
    the directory name. A session that *reads* an entry names the directory — an `rg` over the
    clone, `library.py update <entry>`. A session that *adds* one names a URL, and the entry's own
    name is derived from it afterwards, so `<owner>/<repo>` is what sits in argv and the directory
    name appears nowhere.

    Matching the directory name alone therefore attributes every entry a session read and none it
    added, which is exactly backwards: an add is the event worth attributing, and a read leaves the
    mtime alone anyway.
    """
    parts = name.split("--")
    return (name, "/".join(parts[1:])) if len(parts) >= 3 else (name,)


def attributable_entries(changed: Sequence[str], entries: Sequence[dict[str, Any]]) -> list[str]:
    """Which of the changed library entries this session can be *shown* to have touched.

    An mtime inside the session window is not an attribution. The library is refreshed wholesale by
    `library.py update` and cloned into by any parallel session, so the window catches the machine's
    work and the report presents it as this session's.

    Confirmed 2026-09-07: a sweep reported **30 entries** as changed — `cpython`, `node`, `ansible`,
    `git`, and a whole dotfile-manager cluster that was visibly another session's research topic.
    **Five were this session's**, and its own transcript said which: it ran `library.py add` exactly
    five times, for a coupling-tool survey. A harvest reading that output would have reported
    touching thirty reference clones, which is specific, plausible, and wrong in the direction
    nobody re-checks.

    **It under-attributes when a script does the work, and the session that wrote this check is the
    example.** 2026-09-08: a retrofit re-cloned seven entries from a `retrofit.py` holding the names
    in a list, so argv named two of the seven and the other five came back unattributed — this
    session's own work, filed under "something else". That is the conservative direction and it is
    the intended one, since the alternative is claiming a refresher's work; but it is the same blind
    spot the outside-any-repo check has, one door along, and the report has to say so rather than
    let a low count read as a small session. The seam is `SUBPROCESS_SEAM`, shared with the checks
    that print it; the three instances that made it a convention rather than a footnote are in
    `references/rationale.md`, "What the step-5 checks owed a reader".
    """
    haystack = [*bare_commands(entries), *(str(path) for path in written_paths(entries))]
    return [
        item
        for item in changed
        if any(needle in text for needle in entry_needles(Path(item).name) for text in haystack)
    ]


def disk(runner: Runner, since: str | None, ran_docker: bool | None = None) -> dict[str, Any]:
    """Container images, build caches and interpreters — gigabytes no repository can see.

    Reported with sizes so the user can approve a removal line; never removed here. The build cache
    is shared with every other project on the machine, and an image another session is about to
    reuse costs a rebuild.

    **A timestamp inside the session window is not an attribution on a machine running parallel
    sessions.** Confirmed 2026-09-06: a sweep called twenty images — 2.4 GB — "new this session" for
    a session whose 183 Bash calls contained no `docker` at all; they were a parallel session's
    container-testing work. The report then proposes removing them, and the reason it gives for not
    deleting unasked is precisely that another session may be about to reuse one. So `ran_docker`
    decides which heading the rows land under, and rows that cannot be attributed are still
    reported: the sizes are worth seeing whoever made them.
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
            out["images_in_window"] = [
                row for row in rows if (created := _docker_instant(row)) is not None and created > cutoff
            ]
            out["images_attribution"] = (
                "this session ran docker"
                if ran_docker
                else "no docker command in this session's transcript"
                if ran_docker is False
                else "no transcript to check this session's commands against"
            )
    else:
        out["docker"] = "not installed"
    if shutil.which("uv"):
        pythons = runner(["uv", "python", "list", "--only-installed"])
        out["uv_pythons"] = pythons.lines if pythons.ok else []
    return out


def store_state(
    runner: Runner, name: str, path: Path, since: str | None, entries: Sequence[dict[str, Any]] = ()
) -> dict[str, Any]:
    """A store outside every working tree. Two of them fail differently, so both are checked.

    The plans store is a git repository, so its failure is an *uncommitted* plan: not a commit, so
    no ahead-count anywhere sees it, and nothing walks to a directory outside every working tree.
    The research library is not version-controlled at all, so its failure is a half-finished entry —
    a clone without its metadata file, or one that failed partway.

    `entries` is this session's transcript, and it is what keeps the library half from reading a
    time window as an attribution — the same defect the disk section's image rows had, fixed the
    same way. Without a transcript the rows are still reported and no claim is made about whose
    they are.
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
        library = _library_entries(path)
        # `as_posix()`, matching `entries_without_provenance` below rather than the `str()` this line
        # used to carry. On Windows `str()` yields `repos\github.com--a--b`, so the two lists in one
        # payload disagreed about their own separator — and no test covered this key until the
        # attribution split added one, which is how a Windows CI leg caught it on the first push.
        changed = [
            item.relative_to(path).as_posix()
            for item in library
            if cutoff is not None and datetime.fromtimestamp(item.stat().st_mtime, UTC) > cutoff
        ]
        attributed = attributable_entries(changed, entries) if entries else []
        state["changed_by_this_session"] = attributed
        # Kept as a list in the payload and printed as a bare count: a refresher moving every mtime
        # is the store working as designed, so twenty-five names are noise, while a reader who wants
        # to check the split should not have to re-derive it.
        state["changed_by_something_else"] = [item for item in changed if item not in set(attributed)]
        state["changed_attribution"] = (
            f"{len(attributed)} of {len(changed)} named in this session's own commands"
            if entries
            else "no transcript to check this session's commands against"
        )
        # A half-finished entry is this store's characteristic failure: a clone without its
        # provenance file, or one that failed partway. Nothing else on the machine can see it,
        # because the store is not version-controlled at all. Deliberately *not* attributed — it is
        # a per-entry fact that does not depend on who made it, and it is the check this section is
        # actually for.
        state["entries_without_provenance"] = [
            item.relative_to(path).as_posix() for item in library if not _has_provenance(item)
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


# Files whose basename is specific enough to be worth searching for, and which a plan would name
# because it describes a mechanism rather than because it cites a document. `.md` is deliberately
# absent: a plan naming another plan is a citation, which `plan-docs`' own `refs` already answers.
SOURCE_SUFFIXES = (".py", ".sh", ".toml", ".yml", ".yaml", ".json", ".cfg", ".ini", ".ts", ".js", ".rs", ".go")


def changed_source_names(entries: Sequence[dict[str, Any]]) -> list[str]:
    """Basenames of the source files this session wrote — what another repo's plan would name."""
    return sorted({p.name for p in written_paths(entries) if p.suffix in SOURCE_SUFFIXES})


def plans_directories(root: Path, exclude: Path | None, depth: int = 3) -> list[Path]:
    """Every checkout under the projects root that keeps a `plans/`, except the session's own."""
    return [
        repo / "plans"
        for repo in checkouts(root, depth)
        if (repo / "plans").is_dir() and (exclude is None or repo.resolve() != exclude)
    ]


def superseded_candidates(entries: Sequence[dict[str, Any]], session_repo: Path | None) -> dict[str, Any]:
    """Plans in *other* repos that name a source file this session changed.

    **Every other check in the sweep asks what is dangling _for_ this session; this one asks the
    inverse.** A plan describing a mechanism this session just replaced is not dangling state, not a
    process, not git state and not an unkept promise — no check reaches it, and the plan cannot
    notice on its own because the session that wrote it is gone.

    Confirmed 2026-09-05: a session replaced a repo's gate-output mechanism, and a plan in a
    different repo recorded that mechanism as its landed layer 2. **The cost was not the stale
    prose** — it was that the plan's `## Verification` scheduled a comparison a week later against a
    baseline saved to isolate exactly that layer, so the run would have measured a week of sessions
    in neither mode and reported a null result as "the change did nothing". A human reading stale
    prose notices; a scheduled measurement whose subject moved emits a confident wrong number.

    **Candidates, never a verdict** — the same shape as the `depends_on` bullet, and for the same
    reason: whether a plan is actually stale needs reading it, since one naming `quality.py` may be
    about something else entirely.

    **The session's own repo is not searched.** The blind spot is elsewhere by construction — a
    session is already reading its own `plans/`, and including them turns every edit to a
    well-discussed file into a page of true-but-useless rows, which is how a section teaches its
    reader to skim.
    """
    names = changed_source_names(entries)
    found: list[dict[str, Any]] = []
    searched: list[str] = []
    if not names:
        return {"names": [], "searched": searched, "candidates": found}
    # The shareable store only. A session has no business reading another party's plans to answer a
    # question about its own source file, and the confirmed instance sits in the shareable tier.
    store = next((path for label, path in _stores() if label == "plans"), None)
    directories = plans_directories(projects_root(), session_repo.resolve() if session_repo else None)
    for directory in [*directories, *([store] if store and store.is_dir() else [])]:
        searched.append(str(directory))
        for plan in sorted(directory.rglob("*.md")):
            try:
                text = plan.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            named = [name for name in names if name in text]
            if named:
                found.append({"plan": str(plan), "names": named})
    return {"names": names, "searched": searched, "candidates": found}


# Where a checkout records what it installs. A repo naming another repo in one of these is a
# consumer of it, whether or not either repo documents the relationship.
# `setup.toml` and `skills-lock.json` are not universal names; they are what the two installers in
# play here actually write, and a list that omitted them would have answered "no consumers" for the
# repo whose consumers prompted the check. A reader with neither file loses nothing by their being
# listed.
CONSUMER_MANIFESTS = ("pyproject.toml", "uv.lock", "requirements.txt", "package.json", "setup.toml", "skills-lock.json")
CONSUMER_MANIFEST_GLOBS = ("bootstrap-*.sh",)
# What a repo writes down for the people who install it, if it writes anything down at all.
CONSUMER_DOCS = ("contributing/consumer-sweep.md", "CONSUMERS.md", "docs/consumers.md")


def consumer_candidates(root: Path, repos: Sequence[Path], depth: int = 3) -> list[dict[str, Any]]:
    """Repos on this machine that install a repo this session changed.

    **Every other check in step 5 is about this machine's own state; this one is about what a push
    obliges elsewhere, and it is the only category a push _creates_ rather than leaves behind.**
    Confirmed 2026-09-05: a session changed the module every gate step in a repo now calls, pushed
    it, and the sweep reported dirty 0, unpushed 0, CI green, nothing owed. By every check the skill
    ran, that session was finished. It was not — that repo's bootstrap is unpinned until a version
    tag exists, so every consumer's next CI run installs whatever `main` is at that moment, with no
    consumer-side action and no notice. Two consumers, plus every repo one of them generates, were
    running new code in their gate path that nothing had exercised there.

    The gap was never that a documented procedure was ignored. **Nothing asked**, and the harvest is
    the step whose whole job is asking; the trigger existed only in a file nobody had reason to open.
    The skill already recognised this shape for exactly one repo — a skill edit reaching nothing
    until pushed *and* re-installed — written as a special case rather than as the mechanism it is.

    Consumers are derived from the machine rather than from documentation, the same move `scan`
    makes for private terms: a manifest naming the repo is evidence whether or not either side
    documents the relationship, and it works for a repo that documents none. A consumer-facing doc,
    where one exists, is reported beside it because it is the precise answer where the derived list
    is only a candidate.

    **Reporting is the whole action.** Sweeping a consumer means running its tasks and touching its
    tree, which a session that does not belong to it must not do — so the finding's home is the
    report and the next-session prompt.
    """
    found: list[dict[str, Any]] = []
    others = checkouts(root, depth)
    stores = {path.resolve() for _, path in _stores()}
    for repo in repos:
        # A plans store is written to by every session and installed by nobody — it is a store, not
        # a distributable, so asking who consumes it can only produce noise.
        if repo.resolve() in stores:
            continue
        name = repo.name
        consumers = [str(other) for other in others if other.resolve() != repo.resolve() and _installs(other, name)]
        docs = [doc for doc in CONSUMER_DOCS if (repo / doc).is_file()]
        if consumers or docs:
            found.append({"repo": str(repo), "consumers": consumers, "docs": docs})
    return found


COMMAND_NAME_RE = re.compile(r"<command-name>/([\w-]+)</command-name>")

OPEN_PLAN_STATUSES = ("idea", "planned", "in-progress", "blocked")


def plans_this_session_may_have_landed(
    entries: Sequence[dict[str, Any]], session_repo: Path | None, since: str | None
) -> dict[str, Any]:
    """This repo's own open plans naming a source file this session wrote.

    **The case is a session that builds everything a plan designed, documents it, and never touches
    the plan.** The plan keeps saying `idea` with open questions the code has answered, `absorb`
    never raises it because nothing is terminal, and the next session reading `list` sees live design
    work. Confirmed 2026-09-05: two plans in one repo were answered by six commits the same evening
    and the landing session ended without a status bump on either, so the next harvest nearly
    proposed building what already existed.

    **A prompt, never a gate, and the measurement is why.** Across 8 repos and 167 open plans,
    2026-09-08: 43% name a source file that moved after the plan was last touched, which is noise —
    a plan citing `plans.py` as context is not stale when `plans.py` changes. Requiring the name to
    look like the plan's *subject* (three or more mentions) puts it at 14%, and the residue is
    structural rather than fixable: a session that edits a file makes every plan about that file
    look stale, and no cheap signal separates a design that landed from a subject that merely moved.
    So this lists candidates and asks; `set-status` remains the only thing that changes a status.

    The sibling check for *other* repos' plans deliberately excludes this repo. This one is its
    complement and only reads this repo, because the failure is the opposite: there, a session
    cannot see plans it never opens; here, it does not think to open its own.
    """
    names = changed_source_names(entries)
    if not names or session_repo is None:
        return {"names": names, "candidates": []}
    found: list[dict[str, Any]] = []
    for plan in sorted((session_repo / "plans").glob("*.md")):
        try:
            text = plan.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        status, updated = _plan_frontmatter(text)
        if not any(status.startswith(open_status) for open_status in OPEN_PLAN_STATUSES):
            continue
        # Only a plan that predates this session can have been landed *by* it and left behind.
        if since and updated and updated > since[:10]:
            continue
        subjects = sorted({name for name in names if text.count(name) >= 3})
        if subjects:
            found.append({"plan": plan.name, "status": status, "updated": updated, "names": subjects})
    return {"names": names, "candidates": found}


def _plan_frontmatter(text: str) -> tuple[str, str]:
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", ""
    fields = {}
    for line in parts[1].splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields.get("status", ""), fields.get("updated", "")


def _installs(candidate: Path, name: str) -> bool:
    """Whether this checkout's manifests declare `name` — reading declarations, not commentary.

    **Comment lines are stripped, and that is not tidiness.** A manifest comment citing the repo's
    own `plans/` directory matched the plans store by its basename, so a sweep reported the store as
    "installed by" three repos that merely mention the word. Confirmed 2026-09-08 by this check's
    own first real run. A consumer relationship is declared in configuration; a repo that only talks
    about something in a comment is not installing it.
    """
    manifests = [candidate / manifest for manifest in CONSUMER_MANIFESTS]
    manifests += [path for pattern in CONSUMER_MANIFEST_GLOBS for path in candidate.glob(pattern)]
    for manifest in manifests:
        try:
            text = manifest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        declared = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
        if name in declared:
            return True
    return False


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


# Anchored at the temp *root*, not at any `tmp` segment: a repo's own `tmp/` directory is part of
# that repo and a file in it instructs its readers like any other.
SCRATCH_PATH_RE = re.compile(r"^/(tmp|var/tmp)/|(^|/)(scratchpad|scratch)(/|$)", re.IGNORECASE)


def _is_test_path(path: str) -> bool:
    """A file whose contents are fixtures rather than instructions to anybody.

    Two kinds, one rule: a test, and a file under a scratch or temp directory. The second was added
    2026-09-07 after this check reported two invented `~/work/ops/...` paths as machine-wide
    instructions pointing at missing files — they were inside a throwaway `SKILL.md` written into
    the session's scratchpad to audit a portability tool against a synthetic corpus. Nothing will
    ever read that file, which is the same reason a test fixture is exempt: the finding is a path a
    *future session* is told to run, and a scratch file tells nobody anything.

    The paths are named in shortened form here on purpose. Spelled in full, this docstring is itself
    a non-test file naming a path that does not exist, and the check reports its own explanation —
    which it did, on the first run after the fix landed.
    """
    return bool(path) and bool(TEST_PATH_RE.search(path) or SCRATCH_PATH_RE.search(path))


def promised_paths(entries: Iterable[dict[str, Any]]) -> list[str]:
    """Paths this session wrote *into a file* that do not exist on this machine.

    A rule written into an always-loaded instructions file, or a `SKILL.md` command block, names a
    path — usually an installed copy, not the checkout the session was editing. Confirmed
    2026-08-29: a session deployed a `~/AGENTS.md` rule pointing at
    `~/.agents/skills/<name>/scripts/<file>` while the installed skill had no `scripts/` directory,
    so a machine-wide rule instructed every future session to run a file that did not exist. The
    checkout worked perfectly throughout, which is why nothing surfaced it.

    **Only files an agent loads unconditionally are read**, because "does this path exist" cannot
    tell a path the session *instructed* someone to run from one it *documented* as belonging to
    somebody else — and the second is correct content, not a defect. Confirmed 2026-09-04: a harvest
    of a session whose whole subject was where each coding agent reads its instructions reported ten
    paths, **all ten false positives** — vendor directories for agents not installed here, and a
    docs table recording where three other agents look, which will never exist on this machine and
    is right anyway. The check's own first paragraph already scoped it this way; the code did not,
    and the gap between them is the whole finding.

    The cost of that noise is not the noise. **A section that has been all-false-positive once is
    one the next harvest skims**, and the true positive it exists for looks identical in the list to
    a docs table entry — the 2026-08-29 instance would have been the eleventh line.
    """
    missing: dict[str, tuple[str, str]] = {}
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
        target = str(payload.get("file_path", ""))
        # A block naming no target at all is not evidence that the write was harmless, so it is
        # kept — the same rule `_still_written` applies to a file it cannot read. The filter is
        # there to drop paths written into something demonstrably descriptive, and an unknown
        # destination demonstrates nothing.
        if _is_test_path(target) or (target and not _is_always_loaded(target)):
            continue
        body = " ".join(str(payload.get(key, "")) for key in ("new_string", "content"))
        for match in HOME_PATH_RE.finditer(body):
            candidate = match.group(0).rstrip(".,;:)`\"'")
            if "<" in candidate or "*" in candidate or "." not in Path(candidate).name:
                continue
            # Keyed by the expanded path, so `~/.codex`, `~/.codex/` and the absolute spelling are
            # one row rather than three. The literal spelling is kept for display and for
            # `_still_written`, which greps the file for the text that was actually written.
            resolved = Path(candidate).expanduser()
            if not resolved.exists() and str(resolved) not in missing:
                missing[str(resolved)] = (candidate, target)
    return sorted(shown for shown, target in missing.values() if _still_written(shown, target))


# The files an agent reads without being asked. A path named in one of these is an instruction to
# every future session; the same path in a docs page, a plan or a reference is a description, and
# describing where another vendor's agent looks is correct content on a machine that does not run it.
ALWAYS_LOADED_FILES = ("AGENTS.md", "CLAUDE.md", "SKILL.md")


def _is_always_loaded(target: str) -> bool:
    return bool(target) and Path(target).name in ALWAYS_LOADED_FILES


def _still_written(candidate: str, target: str) -> bool:
    """Whether the path is still in the file the session wrote it into.

    The check reads the session's **writes**, so a line edited away later is still in the transcript
    and still reported — and the finding is "a future session is told to run this", which a revised
    file no longer says. Confirmed 2026-09-07 in the run that added the scratch exemption above: the
    first version of that docstring spelled a missing path in full, the second did not, and the
    check went on reporting the first. A target that cannot be read is kept rather than dropped, on
    the same rule as everywhere else here — an unreadable file is not evidence of absence.
    """
    if not target:
        return True
    try:
        return candidate in Path(target).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True


def _is_library_entry(root: Path) -> bool:
    """A research-library clone, recognised by the store's own convention rather than by its path.

    Both halves are needed. `SOURCE.md` alone would exclude any project that happens to ship one;
    a `repos/` parent alone would exclude a legitimate checkout in a directory of that name. Together
    they are the entry shape `library.py` creates and `check` enforces.
    """
    return root.parent.name == "repos" and (root / "SOURCE.md").is_file()


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

    **That exclusion keyed on `$RESEARCH_HOME`, and the identical failure recurred one path away.**
    Confirmed 2026-09-08: a session probing text-only clones built a second library under its own
    scratchpad, and the sweep fetched that clone's remote, read its CI, and reported the untracked
    `SOURCE.md` as dirt — the same two symptoms, in a tree the location test could not see. A
    library is recognisable by its **shape**, so that is what is matched now: an entry directory
    holding a `SOURCE.md`, sitting directly under a `repos/` bucket. Both halves are the store's own
    convention rather than a path, so a library anywhere is excluded and an ordinary project that
    happens to carry a `SOURCE.md` is not.
    """
    library = Path(os.environ.get("RESEARCH_HOME", str(Path.home() / "research"))).expanduser()
    repos: dict[str, Path] = {}
    candidates = [*(Path(p).expanduser() for p in extra), *written_paths(entries), *shell_targets(entries)]
    for raw in candidates or [Path.cwd()]:
        root = git_root(runner, raw)
        if root is not None and not root.is_relative_to(library) and not _is_library_entry(root):
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
    # Both are the same question asked of two sections: can this artifact be this session's at all?
    # A transcript is what answers it, so without one neither claim is made.
    last = last_activity(entries) if transcript else None
    ran_docker = invoked_docker(entries) if transcript else None
    producers: dict[str, Callable[[], dict[str, Any]]] = {
        "processes": lambda: {"processes": processes(runner, table, last)},
        "sockets": lambda: {"sockets": sockets(runner, table, last)},
        "disk": lambda: {"disk": disk(runner, since, ran_docker)},
        "repos": lambda: {"repos": [asdict(state) for state in states]},
        "ci": lambda: {"ci": {s.path: ci_runs(runner, Path(s.path), s.branch, since) for s in states}},
        "stores": lambda: _sweep_stores(runner, args.checkout, repos, since, entries),
        "plans": lambda: {
            "depends_on": {str(path): depends_on(path) for path in repos},
            "superseded": superseded_candidates(entries, git_root(runner, Path.cwd())),
            "consumers": consumer_candidates(projects_root(), repos),
            "may_have_landed": plans_this_session_may_have_landed(entries, git_root(runner, Path.cwd()), since),
        },
        "paths": lambda: _sweep_loose_files(runner, entries, transcript is not None),
    }

    payload: dict[str, Any] = {
        "boundary": args.boundary,
        "session_started": since,
        "transcript": transcript.as_dict() if transcript else {"note": transcript_note},
    }
    if transcript is None:
        # The repo set comes from the transcript's own write paths and shell targets, so without one
        # it collapses to the working directory — which is a narrower sweep wearing a complete
        # report's clothes. Measured 2026-09-03: one repo where the resolved run covered three.
        payload["repo_scope"] = "the working directory only — with no transcript the session's repo set is unknown"
    for name, produce in producers.items():
        if wanted(name):
            payload |= produce()

    if args.json:
        return payload
    _print_sweep(payload)
    return payload


def _sweep_stores(
    runner: Runner,
    checkout: str | None,
    repos: Sequence[Path],
    since: str | None,
    entries: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    plans_py = find_plans_py(_checkout_or_none(checkout))
    return {
        "stores": [store_state(runner, name, path, since, entries) for name, path in _stores()],
        "absorb": {str(path): absorb_queue(runner, plans_py, path) for path in repos},
    }


# The seam every transcript-derived count shares: the tool call is the unit of evidence, so whatever
# a script does *inside* one is out of scope. Three independent instances by 2026-09-08 — a config
# rewritten by `inv catalogue.example --replace` rather than by `Edit`, a retrofit that re-cloned
# seven library entries from a list inside `retrofit.py` where argv named two, and a truncation
# counter that could not see the SIGPIPE its own verification script produced. None is reachable by
# fixing the others, so the count says its own limit rather than each reader learning it once per row.
SUBPROCESS_SEAM = "reads this session's own edit-tool writes; a file a subprocess wrote is out of scope"


def _sweep_loose_files(runner: Runner, entries: Sequence[dict[str, Any]], have_transcript: bool) -> dict[str, Any]:
    """The two checks that read nothing but this session's own writes — and say when they could not.

    Both are named in step 5 as findings no other check reaches, and both used to vanish from the
    report when no transcript resolved: not empty, **absent**. A reader scanning a full-looking
    report has no gap to notice, because every other section prints normally and the sections that
    did not run leave no heading behind. Confirmed twice, 2026-09-03 and 2026-09-04, the second time
    by a harvest that read the whole sweep, moved on, and found the hole only when re-reading the
    skill for a later step.

    So availability is reported rather than implied, and it is reported the same way whether the
    answer is a finding, none, or "this did not run" — the distinction a clean-looking report
    otherwise destroys.
    """
    if not have_transcript:
        why = "no transcript — both checks read this session's own writes"
        return {"loose_files": {"available": False, "why": why}}
    return {
        "loose_files": {"available": True, "limit": SUBPROCESS_SEAM},
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
    if payload.get("repo_scope"):
        print(f"# repos swept: {payload['repo_scope']}")
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
    _print_superseded(payload.get("superseded"))
    _print_consumers(payload.get("consumers"))
    _print_may_have_landed(payload.get("may_have_landed"))
    _print_loose_files(payload)


def _print_may_have_landed(state: dict[str, Any] | None) -> None:
    if state is None:
        return
    print("\n== this repo's open plans naming a file this session changed ==")
    rows = state.get("candidates") or []
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"    {row['plan']}  [{row['status']}, updated {row['updated']}]")
        print(f"      names: {', '.join(row['names'])}")
    print("  did this session land what any of these designed? if so, bump it with set-status")
    print("  limit: a prompt, not a verdict — measured 2026-09-08 at 14% of open plans family-wide")


def _print_consumers(rows: list[dict[str, Any]] | None) -> None:
    if rows is None:
        return
    print("\n== repos on this machine that install a repo this session changed ==")
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"    {row['repo']}")
        for consumer in row["consumers"]:
            print(f"      installed by: {consumer}")
        for doc in row["docs"]:
            print(f"      it documents what a consumer owes: {doc}")
    print("  a push here is a deploy there — report it and file it; sweeping their tree is not yours to do")


def _print_superseded(state: dict[str, Any] | None) -> None:
    if state is None:
        return
    print("\n== plans elsewhere naming a source file this session changed ==")
    if not state.get("names"):
        print("  none — this session changed no source file")
        return
    for row in state["candidates"]:
        print(f"    {row['plan']}")
        print(f"      names: {', '.join(row['names'])}")
    if not state["candidates"]:
        print("  none")
    print(f"  searched: {len(state['searched'])} location(s), this repo's own plans/ excluded")
    print("  limit: candidates, not a verdict — a plan naming one of these may be about something else")


def _print_processes(procs: dict[str, Any] | None) -> None:
    if procs is None:
        return
    print("\n== processes ==")
    if not procs.get("available"):
        print(f"  unavailable: {procs.get('why')}")
        return
    children = procs["session_children"]
    if procs.get("harness_pid") is None:
        # The listing ran, but no harness process was found in this process's ancestry, so the set
        # of this session's descendants was never established. Printing 0 there would be a measured
        # zero's twin, which is the one thing this sweep must not produce.
        print("  this session's surviving children: unknown — no harness process in this call's ancestry")
    else:
        print(f"  this session's surviving children: {len(children)}")
    for row in children[:15]:
        print(f"    pid {row['pid']:>7} {row['stat']:<4} {row['etimes']:>7}s  {row['args']}")
        print(f"      {_holder(row)}")
    others = procs["watchers_and_servers"]
    print(f"  watchers and servers machine-wide: {len(others)}")
    for row in others[:15]:
        print(f"    pid {row['pid']:>7} {row['kind']:<8} {row['etimes']:>7}s  {row['args']}")
        print(f"      {_holder(row)}")


def _holder(row: dict[str, Any]) -> str:
    """Who holds a process and whether it can be this session's, in one line per row.

    Both facts are what the report reasons about and neither was printed before 2026-09-06, so
    every run that reached step 5's orphan rule went and fetched them by hand.
    """
    orphaned = row.get("orphaned")
    parent = f"parent {row.get('ppid')} {row.get('parent') or '(not in the listing)'}"
    if orphaned is True:
        held = f"ORPHANED — {parent}, so no session holds it"
    elif orphaned is None:
        held = f"holder unknown — {parent}"
    else:
        held = f"held by a live process — {parent}"
    if row.get("started_after_last_activity") is True:
        held += "; started AFTER this session's last activity, so it is not this session's"
    return held


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
            if "ppid" in proc:
                print(f"      {_holder(proc)}")
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
    rows = disks.get("images_in_window", [])
    if rows:
        why = disks.get("images_attribution", "")
        if why == "this session ran docker":
            print(f"  images created during the window, this session's ({len(rows)}):")
        else:
            print(f"  images created during the window, NOT attributable to this session ({len(rows)}):")
            print(f"      ^ {why} — a parallel session is the usual author; do not propose removing these")
        for line in rows:
            print(f"    {line}")


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
    for key in ("dirty", "unpushed", "changed_by_this_session", "entries_without_provenance"):
        for line in state.get(key, []):
            print(f"  {key}: {line}")
    others = state.get("changed_by_something_else") or []
    if others:
        # A count, not a list. A refresher moving every entry's mtime is the store working as
        # designed, and printing twenty-five names buries the handful that are this session's.
        print(f"  changed_by_something_else: {len(others)} entr(ies) — a refresher, a parallel session, or a script")
    if state.get("changed_attribution"):
        print(f"  attribution: {state['changed_attribution']}")
    if others:
        # The check's own limit, printed next to its result. Attribution is by name-in-argv, so work
        # done inside a script that holds the names itself lands here — under-reported, not absent.
        print("    ^ by name in this session's own commands, so entries a script named only")
        print("      internally are under-reported here. Check before reporting a low count as a small session")
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
    """Both headings always print, so "none" and "never looked" stop reading the same."""
    state = payload.get("loose_files")
    if state is None:
        return  # the section was not requested at all
    skipped = None if state.get("available") else f"  skipped: {state.get('why')}"

    def section(heading: str, rows: list[str], limit: str = "", suffix: str = "") -> None:
        print(f"\n== {heading} ==")
        if skipped:
            print(skipped)
        elif not rows:
            print("  none")
        for path in rows:
            print(f"    {path}{suffix}")
        if not skipped and limit:
            # Printed whether or not there were rows: an empty result and an unexaminable one look
            # identical otherwise, which is the property this whole sweep exists to refuse.
            print(f"  limit: {limit}")

    section(
        "files written outside every repository",
        payload.get("written_outside_any_repo") or [],
        limit=state.get("limit", ""),
        suffix="   (no diff, no history — say what would recover it)",
    )
    reads = ", ".join(ALWAYS_LOADED_FILES)
    section(
        "paths this session wrote into files that do not exist",
        payload.get("paths_named_but_missing") or [],
        limit=f"only {reads} are read — a path in a docs page is a description, not an instruction",
    )


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
    claims, ci_claims = _green_claims(transcript.entries, args.until)
    total_bash = len(bash_calls(transcript.entries))
    payload = {
        "transcript": transcript.as_dict(),
        "bash_calls": total_bash,
        "exit_masked": len(masked),
        "green_claims": claims,
        "green_ci_claims": ci_claims,
        "masked_calls": masked[: args.samples],
    }
    if args.json:
        return payload
    print(f"# transcript: {transcript.path}")
    print(f"# {len(masked)} of {total_bash} Bash calls masked their exit code behind a filter")
    print(f"# {len(claims)} message(s) told the user a gate or suite was green")
    for claim in claims:
        print(f"    {claim['timestamp']}  {claim['line']}")
    # Reported beside the gate count and never added to it: a CI conclusion is read as JSON, so it
    # is not usually resting on the filtered evidence the pairing above is about.
    print(f"# {len(ci_claims)} message(s) told the user CI was green — counted apart, see below")
    for claim in ci_claims:
        print(f"    {claim['timestamp']}  {claim['line']}")
    for call in payload["masked_calls"]:
        print(f"    masked: {call['command'][:160]}")
    if masked and claims:
        print(
            "\nAsk the shell first: `setopt | rg pipefail` (zsh) or `set -o | rg pipefail` (bash), as a\n"
            "Bash call in this session — a pipeline under pipefail reports the rightmost non-zero status,\n"
            "so those greens stood on real exit codes and no re-run is owed. The option can be guarded on\n"
            "a harness variable, so a config file is not the answer and neither is another shell.\n"
            "Without it, re-run the repo's own gate unpiped before believing any of those greens, and\n"
            "report the count with the re-run's verdict attached — the claims are in the conversation\n"
            "either way, and the conversation is the one artefact a later commit cannot amend."
        )
    elif not masked:
        print("\nno masked exits: the session's own green results stand on unfiltered evidence")
    if ci_claims:
        print(
            "\nThe CI count is separate on purpose and does not pair with the masked-exit number: a CI\n"
            "conclusion read from `gh run list --json` has no exit code for a pipe to eat. It earns its own\n"
            "check — was the run on the commit you actually pushed, and was it read as JSON rather than\n"
            "watched through a filter."
        )
    return payload


def _green_claims(
    entries: Sequence[dict[str, Any]], until: str | None
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Gate claims and CI claims, kept apart, each sentence counted once.

    Every match rather than the first per message: a message often makes the claim twice, and an
    undercount here is the same failure the check exists to prevent, one level up. One `seen` set
    across both patterns, so a sentence that satisfies each is attributed to the gate count alone
    rather than inflating both.
    """
    seen: set[tuple[str, str]] = set()
    found: tuple[list[dict[str, str]], list[dict[str, str]]] = ([], [])
    for stamp, text in assistant_text(entries):
        if not before(stamp, until):
            continue
        for pattern, into in ((GREEN_CLAIM_RE, found[0]), (GREEN_CI_RE, found[1])):
            for match in pattern.finditer(text):
                line = _claim_line(text, match.start())
                if (stamp, line) in seen:
                    continue
                seen.add((stamp, line))
                into.append({"timestamp": stamp, "text": match.group(0), "line": line})
    return found


def _claim_line(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return text[start : end if end != -1 else len(text)].strip()[:200]


# --------------------------------------------------------------------------------------------
# subcommand: filed
# --------------------------------------------------------------------------------------------


# `boundary` is step 0 of every run, so counting those calls counts the harvests. `$H` is the alias
# the skill's own command block uses and a session that copied that block types it literally.
#
# **`(?<!-)` is the whole correctness of this pattern**, because `sweep --boundary <instant>` and
# `claims --until` carry the same word as a *flag*, and `\b` matches happily after a hyphen. Without
# it every sweep counted as a harvest: confirmed 2026-09-08, a session's first real harvest reported
# `harvest #10` off nine `sweep --boundary` calls, and printed the "an earlier harvest filed the
# artifacts below, re-derive each figure" block for eight harvests that never happened. The wrong
# count is the benign half; the instruction it triggers sends a reader looking for filings nobody
# made.
BOUNDARY_CALL_RE = re.compile(r"(?:harvest\.py|\$H)\b[^|;&\n]*(?<!-)\bboundary\b")

# What a filed measurement looks like in a plan: a rate, a labelled count, or a counted noun.
# Deliberately broad, the same choice `GREEN_CLAIM_RE` makes — an extra line is one the agent reads
# and discards, while a missed one is a number left standing at the value the first harvest took.
MEASUREMENT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s?%"
    r"|\b[a-z][\w./-]*\s?=\s?\d+"
    r"|\b\d+\s+(?:calls|commits|files|plans|sessions|tests|errors|warnings|lines|rows|hits|images)\b",
    re.IGNORECASE,
)

# One record per commit, so `--name-only`'s file list can be split back off its own header. The
# separators are asked for as git's own `%xNN` escapes rather than passed as bytes: an argv element
# may not contain a NUL at all (`ValueError: embedded null byte`, and no test with a fake runner can
# see it), and the ASCII record/unit separators cannot occur in a subject or an author name.
COMMIT_RECORD = "\x1e"
COMMIT_FIELD = "\x1f"
COMMIT_FORMAT = "--format=%x1e%H%x1f%aI%x1f%an%x1f%s"


def harvest_runs(entries: Iterable[dict[str, Any]], until: str | None = None) -> list[str]:
    """When this session ran a harvest, from its own `boundary` calls.

    Whether a run is the second harvest of a session is a fact about the transcript, not something
    the agent has to still be holding: the evidence for this whole subcommand is a session whose
    second harvest corrected the first's filed row only because it happened to remember filing it.
    """
    return [
        stamp for stamp, command in bash_calls(entries) if BOUNDARY_CALL_RE.search(command) and before(stamp, until)
    ]


def plan_roots(repos: Sequence[Path]) -> list[Path]:
    """Every directory a plan can be filed into: both plans stores, and each repo's own `plans/`.

    A path test against these roots rather than a `plans` component anywhere in the path — the
    stores are named by config and a repo directory called `plans-something` is not one of them.
    """
    return [path for name, path in _stores() if name.startswith("plans")] + [repo / "plans" for repo in repos]


def _under(path: Path, root: Path) -> bool:
    try:
        return path.expanduser().is_relative_to(root)
    except ValueError:
        return False


def measurement_lines(path: Path, limit: int = 6) -> list[str]:
    """The lines in a filed plan that carry a number this session could have re-derived since."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [line.strip()[:200] for line in text.splitlines() if MEASUREMENT_RE.search(line)][:limit]


def filed_plans(entries: Iterable[dict[str, Any]], repos: Sequence[Path]) -> list[dict[str, Any]]:
    """Plan files this session wrote, wherever they landed, each with its measurement lines."""
    roots = plan_roots(repos)
    found: list[dict[str, Any]] = []
    for path in written_paths(entries):
        if path.suffix != ".md":
            continue
        root = next((r for r in roots if _under(path, r)), None)
        if root is None:
            continue
        found.append(
            {
                "path": str(path),
                "root": str(root),
                "exists": path.exists(),
                "measurements": measurement_lines(path),
            }
        )
    return found


def store_commits(
    runner: Runner,
    name: str,
    path: Path,
    since: str | None,
    written: Sequence[Path],
    entries: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """The store's own commits since this session began, each attributed or explicitly not.

    The store is shared, so a commit inside the window is not this session's by virtue of being
    there — the same trap the disk bullet's image rows fell into. Everything it cannot attribute is
    listed under its own heading and never proposed for correction.

    **Written paths alone cannot see a deletion, and a deletion is the commonest way any session
    commits here.** `plans.py absorb --apply` *moves* a plan out of the store into a repo: the
    session writes nothing at the store path, so no `Write` or `Edit` call names it, so a purely
    conservative reading calls the session's own removal commit somebody else's. Confirmed
    2026-09-07 — a session absorbed three plans, committed each removal minutes later, and `filed`
    reported `0 commit(s) this session, 20 from elsewhere` with all three of its own listed under
    `(another session)`.

    That is the one direction the conservative reading was argued to be safe in, and it is worse
    than a mislabelled row: step 8 gives the label authority over what the harvest may then do —
    "a row marked `(another session)` is reported, never edited" — so a harvest following the
    procedure correctly declines to correct its own filings. It is self-concealing in the usual way,
    since `0 commit(s) this session` is a plausible number for a session that did no store work.

    So argv is read as well as write paths: a commit whose file this session *named* in a command —
    `plans.py commit <file>`, `plans.py absorb --only <file>`, a `git rm` — is this session's,
    provided the command ran before the commit. That proviso is not decoration: this door was
    predicted to carry no timestamp heuristic and no new parallel-session risk, and its first live
    run refuted both — see `_named_before`. What still cannot be matched is reported as unattributed
    rather than as another session's, because that is the only claim the evidence supports.
    """
    state: dict[str, Any] = {"store": name, "path": str(path)}
    if not path.is_dir() or not (path / ".git").exists():
        state["present"] = False
        return state
    state["present"] = True
    if not since:
        state["note"] = "no session start: pass --since, or a transcript the script can date"
        return state
    ran = runner(["git", "-C", str(path), "log", f"--since={since}", "--name-only", COMMIT_FORMAT])
    if not ran.ok:
        state["error"] = ran.err.strip() or f"git log exited {ran.code}"
        return state
    mine = {os.path.normpath(str(p)) for p in written}
    # Paired with their instants, because naming a file is not enough — see `_named_before`.
    named = [(as_instant(stamp), QUOTED_SPAN_RE.sub(" ", command)) for stamp, command in bash_calls(entries)]
    commits: list[dict[str, Any]] = []
    for chunk in ran.out.split(COMMIT_RECORD):
        lines = [line for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0].split(COMMIT_FIELD)
        if len(header) != 4:
            continue
        sha, when, author, subject = header
        files = lines[1:]
        wrote = any(os.path.normpath(str(path / f)) in mine for f in files)
        mentioned = _named_before(files, when, named)
        commits.append(
            {
                "sha": sha[:9],
                "when": when,
                "author": author,
                "subject": subject,
                "files": files,
                "this_session": wrote or mentioned,
                "evidence": "wrote a file in it" if wrote else "named a file in a command" if mentioned else "",
            }
        )
    state["commits"] = commits
    state["attribution"] = (
        "a commit is this session's when this session wrote or named one of its files"
        if entries
        else "no transcript: nothing here is attributable, whatever the timestamps say"
    )
    return state


def _named_before(files: Sequence[str], when: str, commands: Sequence[tuple[datetime | None, str]]) -> bool:
    """Whether this session named one of a commit's files in a command that ran *before* it.

    **The ordering is the whole check, and leaving it out was a false positive on this function's
    own first live run, 2026-09-08.** A bare name match attributed two commits a parallel session
    made at 00:18 and 00:20 to this session, because this session ran `absorb --only <file>` on the
    same filenames at 00:45. Both sessions legitimately name the same plan; only one of them made
    each commit, and a command cannot have caused a commit that already existed when it ran.

    That is the exact error the write-path-only version was guarding against, arriving through the
    door opened to fix its opposite — so the two evidence sources are not interchangeable and this
    one needs the timestamp the other never did.

    Unparseable on either side means no attribution, which keeps the original conservative default
    where the ordering cannot be established.
    """
    stamp = as_instant(when)
    if stamp is None:
        return False
    names = [Path(f).name for f in files if Path(f).name]
    # The basename rather than the full path: a plan filename carries its own date and topic
    # (`2026-09-07-stub-authoring-skill.md`), so a substring hit is evidence, and it matches however
    # the command spelled the directory in front of it.
    return any(
        moment is not None and moment <= stamp and any(name in command for name in names)
        for moment, command in commands
    )


def cmd_filed(args: argparse.Namespace, runner: Runner) -> dict[str, Any]:
    """What this session has already written into a plans store, and how many harvests wrote it.

    A harvest's report dies with the terminal; the plans it filed do not. So a second harvest owes
    the first one's artifacts a correction, and this is where it finds them rather than remembering
    them. Confirmed 2026-09-07: two harvests of one session 2h40m apart, the first filing an
    adherence row of `n=211 chain=36% head/tail=20%` that the whole session measured at
    `n=306 chain=44% head/tail=27%` — every rate moved, because a mid-session row is a *prefix* of
    the session and the last third was a different kind of work.
    """
    transcript = resolve_transcript(args.session, args.job, args.expect, Path.cwd())
    entries = transcript.entries
    since = args.since or transcript.started
    repos = _touched_repos(runner, args.repo, entries)
    written = written_paths(entries)
    runs = harvest_runs(entries, args.until)
    plans = filed_plans(entries, repos)
    stores = [
        store_commits(runner, name, path, since, written, entries)
        for name, path in _stores()
        if name.startswith("plans")
    ]

    payload = {
        "transcript": transcript.as_dict(),
        "session_started": since,
        "harvest_runs": runs,
        "plans_written": plans,
        "stores": stores,
    }
    if args.json:
        return payload
    _print_filed(payload)
    return payload


def _print_filed(payload: dict[str, Any]) -> None:
    transcript = payload.get("transcript", {})
    print(f"# transcript: {transcript.get('path')}")
    print(f"# session started: {payload.get('session_started')}")
    runs = payload.get("harvest_runs") or []
    if not runs:
        print("# no `boundary` call in this transcript — step 0 has not run, or it has not flushed yet")
    else:
        print(f"# harvest #{len(runs)} of this session; step-0 boundaries at: {', '.join(runs)}")
    if len(runs) > 1:
        print(
            "# an earlier harvest filed the artifacts below. A measurement taken then is a PREFIX of\n"
            "# this session, not a smaller version of it — re-derive each figure and correct the file\n"
            "# before writing the delta report. The report is the cheap half; the file is the durable one."
        )

    plans = payload.get("plans_written") or []
    print(f"\n## plan files this session wrote ({len(plans)})")
    for plan in plans:
        mark = "" if plan.get("exists") else "  MISSING (absorbed, or moved)"
        print(f"    {plan['path']}{mark}")
        for line in plan.get("measurements") or []:
            print(f"        {line}")

    for state in payload.get("stores") or []:
        _print_store_commits(state)


def _print_store_commits(state: dict[str, Any]) -> None:
    print(f"\n## store {state['store']}: {state['path']}")
    if not state.get("present"):
        print("    not present")
        return
    for key in ("note", "error"):
        if state.get(key):
            print(f"    {key}: {state[key]}")
    commits = state.get("commits") or []
    ours = [c for c in commits if c["this_session"]]
    theirs = [c for c in commits if not c["this_session"]]
    print(f"    {len(ours)} commit(s) this session, {len(theirs)} not attributable, since session start")
    if state.get("attribution"):
        print(f"    ^ {state['attribution']}")
    for commit in ours:
        print(f"    {commit['sha']}  {commit['when']}  {commit['subject'][:100]}")
        if commit.get("evidence"):
            print(f"        ^ this session {commit['evidence']}")
    for commit in theirs:
        print(f"    (not attributed) {commit['sha']}  {commit['when']}  {commit['subject'][:100]}")
    if theirs:
        # Deliberately not "(another session)". The evidence establishes only that nothing tied the
        # commit to this session, and the two readings — somebody else's work, versus this session's
        # through a door the check cannot see — call for opposite next steps.
        print("    rows marked (not attributed) may be another session's live work: report, do not edit.")
        print("    If one is yours through a path this check cannot see, say so rather than assuming either way")


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
    skills.add_argument(
        "--skill", action="append", help="skill name; repeatable, ADDED to the ones a harvest uses (--all replaces)"
    )
    skills.add_argument("--all", action="store_true", help="every skill in the checkout")
    skills.add_argument("--checkout", help="path to the agent-skills checkout")
    skills.add_argument("--installed", help="installed skills root (default ~/.agents/skills)")
    skills.add_argument(
        "--since",
        help="override the session start this resolves for itself; for a harness exporting no id, "
        "or to audit a window that is not this session's",
    )
    _add_transcript_flags(skills)

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

    filed = subparsers.add_parser(
        "filed", parents=[common], help="what an earlier harvest in this session already filed, and where"
    )
    _add_transcript_flags(filed)
    filed.add_argument("--since", help="session start (default: the transcript's first timestamp)")
    filed.add_argument("--until", help="ignore harvest runs at or after this instant (the boundary)")
    filed.add_argument("--repo", action="append", default=[], help="add a repo the transcript cannot show")
    return parser


COMMANDS = {
    "boundary": cmd_boundary,
    "transcript": cmd_transcript,
    "turns": cmd_turns,
    "skills-state": cmd_skills_state,
    "sweep": cmd_sweep,
    "claims": cmd_claims,
    "filed": cmd_filed,
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
    # A cut pipe is the reader's decision, not this script's error: die on SIGPIPE (exit 141)
    # rather than print a BrokenPipeError traceback that reads as a crash. Inside the guard because
    # the disposition is process-wide and the tests load this module by path.
    if hasattr(signal, "SIGPIPE"):  # absent on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    raise SystemExit(main())
