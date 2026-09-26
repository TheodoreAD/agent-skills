"""Tests for `skills/session-harvest/scripts/harvest.py`.

Every input to that script is either a transcript on disk or the output of an external command, so
both are seams: transcripts are built as dicts here, and commands go through an injected runner.
**No test may shell out**, and that is asserted rather than intended — the autouse fixture below
replaces `subprocess.run` with something that fails the test if it is called.

One test per correction the script exists to make permanent. Each of those was a prose warning in
`SKILL.md` first, and each recurred at least once after the warning existed; a test is what stops
the fix being re-lost the next time somebody rewrites the paragraph.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# `typing.override` is 3.12+ and this repo develops at its 3.11 floor.
from typing_extensions import override

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "session-harvest" / "scripts" / "harvest.py"


def _load():
    spec = importlib.util.spec_from_file_location("harvest_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harvest = _load()
# Captured before the autouse fixture below replaces it, for the one test that checks the real one.
REAL_PROJECTS_ROOT = harvest.projects_root


@pytest.fixture(autouse=True)
def _no_subprocess(monkeypatch):
    """The requirement, enforced: every command in these tests comes from the fake runner."""

    def refuse(*args, **kwargs):
        raise AssertionError(f"a test shelled out: {args!r} {kwargs!r}")

    monkeypatch.setattr(harvest.subprocess, "run", refuse)


@pytest.fixture(autouse=True)
def _no_real_machine(tmp_path, monkeypatch):
    """The checkout detection walks the projects root `plan-docs` is configured with, and on the
    author's machine that root holds this very repo — so without this every "no checkout" test
    would find one. An empty root and no configured checkout is the reader's machine."""
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(tmp_path / "no-config.toml"))
    monkeypatch.delenv("SESSION_HARVEST_CHECKOUT", raising=False)
    monkeypatch.setattr(harvest, "projects_root", lambda: tmp_path / "no-projects")
    # Every fixture here is `ps`/`ss` output; the Windows tests set the constant themselves.
    monkeypatch.setattr(harvest, "WINDOWS", False)


class FakeRunner:
    """Canned command output, keyed by the start of the command line.

    Keys are matched as prefixes of `" ".join(argv)`, longest first, so a test states only the part
    of a command it cares about. An unmatched command returns exit 0 and no output rather than
    raising: most of the script's commands are irrelevant to any one test, and a fake that demands
    every one of them be declared makes the tests about the fake.
    """

    def __init__(self, responses: dict[str, tuple[int, str, str]] | None = None):
        # Keys built from a real `tmp_path` carry backslashes on Windows; normalise both sides.
        self.responses: dict[str, tuple[int, str, str]] = {
            key.replace("\\", "/"): value for key, value in (responses or {}).items()
        }
        self.calls: list[list[str]] = []

    def __call__(self, argv, cwd=None):
        args = [str(a) for a in argv]
        self.calls.append(args)
        # Keys are written with POSIX separators; a `Path("/repo")` renders as `\repo` on Windows.
        line = " ".join(args).replace("\\", "/")
        for key in sorted(self.responses, key=len, reverse=True):
            if line.startswith(key):
                code, out, err = self.responses[key]
                return harvest.Ran(tuple(args), code, out, err)
        return harvest.Ran(tuple(args), 0, "", "")


def entry(**fields):
    return {"type": "assistant", "timestamp": "2026-09-02T10:00:00.000Z", **fields}


def user_entry(text, timestamp="2026-09-02T10:00:00.000Z", **fields) -> dict[str, object]:
    return {"type": "user", "timestamp": timestamp, "message": {"content": text}, **fields}


def blocks_entry(kind, blocks, timestamp="2026-09-02T10:00:00.000Z") -> dict[str, object]:
    return {"type": kind, "timestamp": timestamp, "message": {"content": blocks}}


def write_transcript(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------------
# the transcript reader
# --------------------------------------------------------------------------------------------


ASK_ANSWER = 'Your questions have been answered: "Push?"="Yes". You can now continue.'
TYPED_ANSWER = 'The user answered: "How should this be grouped?"="flat table, tags as a column"'


def transcript_with_answers() -> list[dict[str, object]]:
    """One listed answer, one typed answer, and a Bash result quoting the marker.

    The third entry is the trap: a session that greps its own transcript for the preamble puts the
    preamble at the start of a tool result that is not an answer at all.
    """
    return [
        user_entry("do the harvest"),
        blocks_entry("assistant", [{"type": "tool_use", "id": "t1", "name": "AskUserQuestion", "input": {}}]),
        blocks_entry("user", [{"type": "tool_result", "tool_use_id": "t1", "content": ASK_ANSWER}]),
        blocks_entry("assistant", [{"type": "tool_use", "id": "t2", "name": "AskUserQuestion", "input": {}}]),
        blocks_entry("user", [{"type": "tool_result", "tool_use_id": "t2", "content": TYPED_ANSWER}]),
        blocks_entry("assistant", [{"type": "tool_use", "id": "t3", "name": "Bash", "input": {"command": "rg x"}}]),
        blocks_entry(
            "user",
            [{"type": "tool_result", "tool_use_id": "t3", "content": TYPED_ANSWER + "\n(grep output)"}],
        ),
    ]


def test_answers_are_found_by_tool_use_id_not_by_preamble():
    """Both answer shapes are recovered, and a grep's output quoting one is not counted.

    The filter has been wrong in both directions on the same day: a heuristic that returned `Read`
    outputs alongside real answers, then a narrowing to `Your questions have been answered:` that
    missed every typed answer — and typed answers are where the brief actually lives.
    """
    found, preamble_hits = harvest.answers(transcript_with_answers())
    assert [t.text for t in found] == [ASK_ANSWER, TYPED_ANSWER]
    assert preamble_hits == 3, "the raw preamble count must still see the impostor, so it can be reported"


def test_user_turns_separate_real_text_from_command_wrappers():
    entries = [
        user_entry("<command-name>/clear</command-name>"),
        user_entry("do the session harvest plan"),
        user_entry("<local-command-caveat>noise</local-command-caveat>", isMeta=True),
        user_entry("keep going<system-reminder>ignore this</system-reminder>"),
    ]
    turns = harvest.user_turns(entries)
    assert [(t.kind, t.text) for t in turns] == [
        ("command", "<command-name>/clear</command-name>"),
        ("user", "do the session harvest plan"),
        ("command", "<local-command-caveat>noise</local-command-caveat>"),
        ("user", "keep going"),
    ]


def queued(text, operation="enqueue", timestamp="2026-09-02T10:05:00.000Z") -> dict[str, object]:
    return {"type": "queue-operation", "operation": operation, "timestamp": timestamp, "content": text}


def test_a_message_sent_mid_turn_is_recovered(tmp_path, monkeypatch):
    """The third population, and the one whose absence is invisible.

    A message the user sends while a turn is running is recorded as a `queue-operation`, not as
    `type: "user"`, so a scan built on user turns plus answers finds neither. Filed 2026-09-02 by a
    session where the richest instruction of the run — new scope, its last third, six commits — was
    exactly such a message and appeared nowhere in the extraction.
    """
    entries = [
        user_entry("start here"),
        queued("i also want an asciinema recording for the front page"),
        queued("i also want an asciinema recording for the front page", operation="remove"),
    ]
    found, attachments = harvest.queued_messages(entries)
    assert [(t.kind, t.text) for t in found] == [("mid-turn", "i also want an asciinema recording for the front page")]
    assert attachments == 0, "no queued_command attachment in this fixture"


def test_a_queued_message_is_counted_once_not_twice():
    """Each is recorded as `enqueue` and again as `remove` when it is delivered."""
    entries = [queued("do the thing"), queued("do the thing", operation="remove")]
    found, _ = harvest.queued_messages(entries)
    assert len(found) == 1


def test_the_harness_speaking_is_not_the_user_speaking():
    """A background-task notification arrives in the same population as a mid-turn message, and an
    interruption marker arrives as a user turn. Both are real signal and neither is an instruction,
    so they are labelled rather than counted as the brief."""
    notification = "<task-notification>\n<task-id>abc</task-id>\n<status>completed</status>\n</task-notification>"
    found, _ = harvest.queued_messages([queued(notification)])
    assert [t.kind for t in found] == ["notification"]

    turns = harvest.user_turns([user_entry("[Request interrupted by user for tool use]")])
    assert [t.kind for t in turns] == ["interrupt"]


def test_the_attachment_copy_is_a_cross_check_not_a_second_source():
    """`attachment` carries mostly harness noise — 230 token reminders in the transcript this was
    measured on — so matching the type would be the over-broad half of the mistake this step has
    already made twice on the answer filter. Only `queued_command` is counted, and only to compare."""
    entries = [
        {"type": "attachment", "attachment": {"type": "queued_command", "command": "x"}},
        {"type": "attachment", "attachment": {"type": "total_tokens_reminder"}},
    ]
    found, attachments = harvest.queued_messages(entries)
    assert found == []
    assert attachments == 1


def test_turns_reports_all_three_populations(tmp_path, monkeypatch):
    path = write_transcript(
        tmp_path / "s.jsonl",
        [
            user_entry("the opening brief"),
            *transcript_with_answers()[1:5],
            queued("and also do this other thing"),
        ],
    )
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    args = harvest.build_parser().parse_args(["turns", "--session", str(path), "--json"])
    payload = harvest.cmd_turns(args, FakeRunner())
    counts = payload["counts"]
    assert (counts["user"], counts["mid_turn"], counts["answers"]) == (1, 1, 2)


def test_written_paths_ignore_reads():
    """A repo this session only read is not a repo it touched — the difference between a sweep
    reporting six repos and reporting the two that matter."""
    entries = [
        blocks_entry(
            "assistant",
            [
                {"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": "/repo/a.py"}},
                {"type": "tool_use", "id": "b", "name": "Read", "input": {"file_path": "/other/b.py"}},
                {"type": "tool_use", "id": "c", "name": "Write", "input": {"file_path": "/repo/c.md"}},
            ],
        )
    ]
    assert [p.as_posix() for p in harvest.written_paths(entries)] == ["/repo/a.py", "/repo/c.md"]


def test_shell_targets_read_cd_and_git_c():
    entries = [
        blocks_entry(
            "assistant",
            [
                {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "cd /other/repo && git status"}},
                {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": "git -C /third/repo push"}},
            ],
        )
    ]
    assert sorted(p.as_posix() for p in harvest.shell_targets(entries)) == ["/other/repo", "/third/repo"]


def test_a_repo_the_session_only_read_is_not_enrolled():
    """Confirmed 2026-09-12: `git -C … status`, `git -C … log` and one `cd … && git check-ignore`
    against `repo-tasks`, read to write a filed plan accurately, enrolled a repo the session changed
    nothing in — and the sweep printed "a push here is a deploy there" for it.

    A `cd` is the exception unless the harness reset it: a `cd` that sticks moves every later
    unscoped command into the repo it named."""

    def call(command: str, call_id: str, result: str = "") -> list[dict[str, object]]:
        use = {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": command}}
        done = {"type": "tool_result", "tool_use_id": call_id, "content": result}
        return [blocks_entry("assistant", [use]), blocks_entry("user", [done])]

    entries = [
        *call("git -C /read/repo status --short", "a"),
        *call("git -C /read/repo log --oneline -5 | head -3; git -C /read/repo worktree list", "b"),
        *call("cd /read/repo && git check-ignore -v x", "c", "x\n\nShell cwd was reset to /home/u/own"),
        *call("cd /sticky/repo && git log -1", "d", "abc1234 a subject"),
    ]
    assert [p.as_posix() for p in harvest.shell_targets(entries)] == ["/sticky/repo"]


@pytest.mark.parametrize(
    ("command", "read_only"),
    [
        ("git -C /r status --short", True),
        ("git --no-pager -C '/a path' log --format='%h|%s' -3", True),
        ("git -C /r log --oneline 2>&1 | rg 'fix|feat' 2>/dev/null", True),
        ("FOO=1 git -C /r rev-parse HEAD", True),
        ("find /r -name '*.md'", True),
        ("git -C /r worktree list", True),
        ("git -C /r worktree add ../x", False),
        ("git -C /r commit -m 'a | b'", False),
        ("git -C /r log > /tmp/log.txt", False),
        ("git -C /r show $(git -C /r rev-parse HEAD)", False),
        ("git -C /r status && git -C /r push", False),
        ("find /r -name '*.pyc' -delete", False),
        ("cd /r && inv quality.precommit", False),
        ("git -C /r fetch", False),
    ],
)
def test_what_counts_as_a_read(command, read_only):
    """A closed list, so anything unrecognised enrols: an omission is a row of noise, never a repo the
    session changed going unswept."""
    assert harvest.read_only_call(command) is read_only


# --------------------------------------------------------------------------------------------
# resolving which transcript is ours
# --------------------------------------------------------------------------------------------


def test_job_state_is_found_in_either_location(tmp_path, monkeypatch):
    """`$CLAUDE_JOB_DIR/../state.json` was simply the wrong path on one build.

    Following it raised `FileNotFoundError` (2026-09-02, CLI 2.1.252), where the file sits in the
    job directory itself. Both spellings are real on some build, so both are tried.
    """
    job = tmp_path / "jobs" / "abcd1234"
    job.mkdir(parents=True)
    (job / "state.json").write_text(json.dumps({"sessionId": "abcd1234", "linkScanPath": "/x.jsonl"}))
    monkeypatch.setenv("CLAUDE_JOB_DIR", str(job))
    found = harvest.job_state()
    assert found is not None
    assert found[0] == job / "state.json"

    nested = tmp_path / "jobs" / "efgh" / "tmp"
    nested.mkdir(parents=True)
    (nested.parent / "state.json").write_text(json.dumps({"sessionId": "efgh", "linkScanPath": "/y.jsonl"}))
    monkeypatch.setenv("CLAUDE_JOB_DIR", str(nested))
    found = harvest.job_state()
    assert found is not None
    assert found[0] == nested.parent / "state.json"


def test_a_job_id_resolves_to_the_transcript_its_state_names(tmp_path, monkeypatch):
    """A background job has two ids and they are not interchangeable.

    `sessionId` names the job *and* names a real transcript file in the same directory, so a guess
    resolves successfully to a stranger's session. Confirmed 2026-09-01: 386 calls reported as the
    job's, not one of them its own, with nothing in the output reading as wrong.
    """
    real = write_transcript(tmp_path / "real.jsonl", [user_entry("mine")])
    job = tmp_path / "jobs" / "c9a20dab"
    job.mkdir(parents=True)
    (job / "state.json").write_text(
        json.dumps({"sessionId": "c9a20dab-1111", "resumeSessionId": "13aa", "linkScanPath": str(real)})
    )
    monkeypatch.setenv("CLAUDE_JOB_DIR", str(job))

    resolved = harvest.resolve_transcript(None, None, None, tmp_path)
    assert resolved.path == real
    assert "linkScanPath" in resolved.how

    # An id whose job claims a different sessionId is not that job's, and must not borrow its path.
    assert harvest._from_job(None, must_match="somebody-else") is None


def test_no_transcript_is_an_error_rather_than_a_guess(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    with pytest.raises(harvest.HarvestError, match=r"no transcript resolved"):
        harvest.resolve_transcript(None, None, None, tmp_path)


def test_the_harness_session_id_resolves_a_bare_call(tmp_path, monkeypatch):
    """Claude Code exports `CLAUDE_CODE_SESSION_ID` into every Bash call, and it is the transcript's
    own stem — confirmed 2026-09-05 in a session whose bare `turns` had just exited 1 with
    "no transcript resolved" one line after `transcript --expect` printed the right path. Three
    harvests in two days had re-typed `--session` by hand; none of them needed to.
    """
    projects = tmp_path / "projects" / "-home-u-repo"
    projects.mkdir(parents=True)
    mine = write_transcript(projects / "4e6fc3cc-eebb-4ea1-b035-ca0112dc9982.jsonl", [user_entry("mine")])
    write_transcript(projects / "5554513b-6e49-4d0b-be8f-cba212809203.jsonl", [user_entry("theirs")])
    monkeypatch.setattr(harvest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "4e6fc3cc-eebb-4ea1-b035-ca0112dc9982")

    resolved = harvest.resolve_transcript(None, None, None, tmp_path)
    assert resolved.path == mine
    assert "CLAUDE_CODE_SESSION_ID" in resolved.how

    # A job's own state still wins: in a background job the environment names the parent session.
    real = write_transcript(tmp_path / "job.jsonl", [user_entry("the job's")])
    job = tmp_path / "jobs" / "c9a20dab"
    job.mkdir(parents=True)
    (job / "state.json").write_text(json.dumps({"sessionId": "c9a20dab-1111", "linkScanPath": str(real)}))
    monkeypatch.setenv("CLAUDE_JOB_DIR", str(job))
    assert harvest.resolve_transcript(None, None, None, tmp_path).path == real


def test_an_explicit_session_that_names_nothing_is_an_error_not_a_fallback(tmp_path, monkeypatch):
    """Found 2026-09-05 by passing a nonsense `--session` inside a live session: the call resolved
    the harness's own transcript and labelled it as resolved by the environment. The caller pinned
    a session; answering about a different one is the failure this whole resolver exists to
    prevent, and it read as success."""
    projects = tmp_path / "projects" / "-home-u-repo"
    projects.mkdir(parents=True)
    write_transcript(projects / "4e6fc3cc-eebb-4ea1-b035-ca0112dc9982.jsonl", [user_entry("mine")])
    monkeypatch.setattr(harvest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "4e6fc3cc-eebb-4ea1-b035-ca0112dc9982")

    with pytest.raises(harvest.HarvestError, match=r"names no transcript"):
        harvest.resolve_transcript("nonexistent-zzz", None, None, tmp_path)


def test_expect_verifies_a_transcript_it_did_not_choose(tmp_path, monkeypatch):
    path = write_transcript(tmp_path / "s.jsonl", [user_entry("hello")])
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    resolved = harvest.resolve_transcript(str(path), None, "no-such-command", tmp_path)
    assert any("NOT FOUND" in note for note in resolved.notes)
    assert any("somebody else's session" in note for note in resolved.notes)


# --------------------------------------------------------------------------------------------
# instants
# --------------------------------------------------------------------------------------------


def test_instants_are_compared_as_moments_not_as_strings():
    """The transcript stamps UTC with `Z`, git prints local time with an offset.

    Lexically `2026-09-02T09:00:00Z` sorts before `2026-09-02T11:30:00+03:00`; as moments the
    second is earlier. A string comparison here is wrong by the offset, silently.
    """
    utc = "2026-09-02T09:00:00Z"
    local = "2026-09-02T11:30:00+03:00"
    assert utc < local, "the string comparison this rule exists to prevent"
    assert harvest.as_instant(local) < harvest.as_instant(utc)
    assert harvest.before(local, utc)


def test_docker_created_at_is_parsed():
    assert harvest._docker_instant("img\t1GB\t2026-09-01 12:33:44 +0300 EEST") is not None
    assert harvest._docker_instant("img\t1GB\tnonsense") is None


def bash_entry(command: str, timestamp: str = "2026-09-02T10:00:00.000Z") -> dict[str, object]:
    block = {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": command}}
    return blocks_entry("assistant", [block], timestamp=timestamp)


def test_a_session_that_ran_no_docker_command_owns_no_image(monkeypatch, tmp_path):
    """Confirmed 2026-09-06: a sweep reported twenty images, 2.4 GB, as "new this session" for a
    session whose 183 Bash calls contained no `docker` at all — a parallel session's container
    testing. The bullet reading that report proposes a removal line, so the mislabel is a proposal
    to delete another session's work while it may still be running against it."""
    monkeypatch.setattr(harvest.shutil, "which", lambda name: str(tmp_path / name))
    images = "sample-service:latest\t1.2GB\t2026-09-06 01:10:00 +0300 EEST\n"
    runner = FakeRunner({"docker images": (0, images, ""), "docker system df": (0, "TYPE\n", "")})
    since = "2026-09-06T00:00:00+03:00"

    unattributed = harvest.disk(runner, since, ran_docker=False)
    assert unattributed["images_in_window"], "the row is still reported — the size is worth seeing"
    assert unattributed["images_attribution"] == "no docker command in this session's transcript"

    assert harvest.disk(runner, since, ran_docker=True)["images_attribution"] == "this session ran docker"
    assert "no transcript" in harvest.disk(runner, since, ran_docker=None)["images_attribution"]


def test_docker_is_counted_at_command_position_not_wherever_the_word_appears():
    """A session that greps for the word, or writes it into a plan, has not run it."""
    assert harvest.invoked_docker([bash_entry("docker images --format '{{.Repository}}'")])
    assert harvest.invoked_docker([bash_entry("inv build && docker compose up -d")])
    assert harvest.invoked_docker([bash_entry("sudo -A docker system prune")])
    assert not harvest.invoked_docker([bash_entry("rg -n docker skills/session-harvest/SKILL.md")])
    assert not harvest.invoked_docker([bash_entry("git commit -m 'note the docker images'")])
    # The false positive on this check's own first live run, 2026-09-06: an alternation inside a
    # quoted search pattern is a pipe followed by the command, by every rule the regex knows.
    assert not harvest.invoked_docker([bash_entry('rg -n "def sweep|docker|listener" harvest.py')])


def test_last_activity_is_the_latest_entry_parsed_not_the_latest_string():
    entries = [
        bash_entry("first", timestamp="2026-09-06T09:00:00Z"),
        bash_entry("second", timestamp="2026-09-06T11:30:00+03:00"),  # 08:30Z — earlier
    ]
    assert harvest.as_instant(harvest.last_activity(entries)) == harvest.as_instant("2026-09-06T09:00:00Z")
    assert harvest.last_activity([]) is None


# --------------------------------------------------------------------------------------------
# git state
# --------------------------------------------------------------------------------------------


# One unpushed commit, in the `%h\x1f%an\x1f%cI\x1f%s` shape the script asks git for.
AHEAD_LOG = "abc123\x1fMe\x1f2026-09-02T10:00:00+03:00\x1fwork\n"


def test_upstream_is_read_never_typed():
    """Measured 2026-08-30 across this machine's clones: 22 of 71 were on `main`, fewer than were
    on `master`. Typing `origin/main` is wrong more often than right, and wrong quietly."""
    runner = FakeRunner({"git -C /repo rev-parse --abbrev-ref @{u}": (0, "origin/master\n", "")})
    upstream, why = harvest.upstream_of(runner, Path("/repo"))
    assert upstream == "origin/master"
    assert why == ""
    assert not any("origin/main" in " ".join(call) for call in runner.calls)


def test_a_branch_with_no_upstream_says_so_instead_of_counting():
    runner = FakeRunner(
        {
            "git -C /repo rev-parse --abbrev-ref @{u}": (128, "", "fatal: no upstream"),
            "git -C /repo rev-parse --abbrev-ref HEAD": (0, "spike\n", ""),
        }
    )
    state = harvest.repo_state(runner, Path("/repo"), since=None, do_fetch=True)
    assert state.upstream is None
    assert state.ahead == []
    assert any("no upstream for spike" in note for note in state.notes)


def test_a_failed_fetch_makes_the_ahead_count_suspect():
    """A failed fetch leaves `origin/<branch>` exactly where it was, so the count still prints a
    plausible number computed against a stale ref — the wrong answer and the right one look
    identical. Confirmed repeatedly; the fetch's exit code is the only thing that separates them."""
    runner = FakeRunner(
        {
            "git -C /repo rev-parse --abbrev-ref @{u}": (0, "origin/main\n", ""),
            "git -C /repo fetch origin": (128, "", "Permission denied (publickey)"),
            "git -C /repo log -1 --format=%cr origin/main": (0, "3 days\n", ""),
            "git -C /repo log origin/main..HEAD --format=": (0, AHEAD_LOG, ""),
        }
    )
    state = harvest.repo_state(runner, Path("/repo"), since=None, do_fetch=True)
    assert state.fetch.startswith("FAILED")
    assert state.ref_age == "3 days"
    assert any("stale" in note or "last updated" in note for note in state.notes)


def test_git_log_failure_is_reported_rather_than_read_as_zero():
    """`git log origin/main..HEAD` against a `master` repo exits 128; piped into `wc -l` that
    became a calm `0` for a store 32 commits ahead. Here the exit code is the answer."""
    runner = FakeRunner(
        {
            "git -C /repo rev-parse --abbrev-ref @{u}": (0, "origin/main\n", ""),
            "git -C /repo log origin/main..HEAD --format=": (128, "", "fatal: ambiguous argument"),
        }
    )
    state = harvest.repo_state(runner, Path("/repo"), since=None, do_fetch=False)
    assert state.ahead == []
    assert any("exited 128" in note for note in state.notes)


def test_an_unpushed_commit_touching_an_already_published_path_is_flagged():
    """Not proof of a correction, but a short list to read: a session pushed a claim, learned it was
    false, committed the fix and never pushed — so the remote serves a known-wrong justification
    while its correction sits in the ahead-count looking like ordinary tidying."""
    runner = FakeRunner(
        {
            "git -C /repo rev-parse --abbrev-ref @{u}": (0, "origin/main\n", ""),
            "git -C /repo log origin/main..HEAD --format=%h": (0, AHEAD_LOG, ""),
            "git -C /repo log origin/main..HEAD --name-only": (0, "README.md\nnotes.md\n", ""),
            "git -C /repo log origin/main --since=": (0, "README.md\n", ""),
        }
    )
    state = harvest.repo_state(
        runner,
        Path("/repo"),
        since="2026-09-02T08:00:00+03:00",
        do_fetch=False,
        written=[Path("/repo/README.md"), Path("/repo/notes.md")],
    )
    assert state.overlap == ["README.md"]


def test_a_path_this_session_never_wrote_is_not_a_correction():
    """`--since` on the upstream log means "authored recently", not "this session published it". On
    a store several sessions commit to, all of their commits land in `published`, so any later
    commit by anyone to the same file reads as this session correcting itself. Confirmed 2026-09-04:
    a harvest pushed a 22-commit backlog it had not authored, and the next session's ordinary
    follow-up to one of those files was reported as a correction."""
    runner = FakeRunner(
        {
            "git -C /repo rev-parse --abbrev-ref @{u}": (0, "origin/main\n", ""),
            "git -C /repo log origin/main..HEAD --format=%h": (0, AHEAD_LOG, ""),
            "git -C /repo log origin/main..HEAD --name-only": (0, "README.md\nnotes.md\n", ""),
            "git -C /repo log origin/main --since=": (0, "README.md\n", ""),
        }
    )
    state = harvest.repo_state(
        runner,
        Path("/repo"),
        since="2026-09-02T08:00:00+03:00",
        do_fetch=False,
        written=[Path("/repo/notes.md")],  # this session wrote notes.md, never README.md
    )
    assert state.overlap == []


def test_the_overlap_line_reports_what_it_measured_and_does_not_claim_a_correction(capsys):
    """Two of this check's three failure shapes were fixed by narrowing; the third cannot be. The
    intersection is "touched before a push" and "touched after it", which contains every file a long
    session keeps working on. Confirmed 2026-09-04: an `ingesta` harvest flagged `AGENTS.md`,
    `tasks/seed_database.py` and `tests/unit/test_store.py`, all three this session's own writes in
    its own repo, all three passing every filter, and all three wrong — each later commit added to
    what was published rather than correcting it. The remote was serving less, not serving wrong.

    Correction is a property of the diff, so the line gives up the claim and keeps the finding."""
    harvest._print_repo(
        {
            "path": "/repo",
            "branch": "main",
            "upstream": "origin/main",
            "fetch": "ok",
            "dirty": [],
            "ahead": [],
            "overlap": ["AGENTS.md"],
            "notes": [],
        }
    )
    out = capsys.readouterr().out

    assert "AGENTS.md" in out
    assert "CORRECTION" not in out, "the path sets cannot tell a correction from continued work"
    assert "both sides of a push this session made" in out
    assert "read the unpushed commit's diff" in out


# --------------------------------------------------------------------------------------------
# skills state
# --------------------------------------------------------------------------------------------


def make_skill(root: Path, name: str, body: str, script: str = "print(1)\n") -> Path:
    skill = root / "skills" / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(body)
    (skill / "scripts" / "x.py").write_text(script)
    return skill


def make_installed(root: Path, name: str, body: str, script: str = "print(1)\n") -> Path:
    skill = root / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(body)
    (skill / "scripts" / "x.py").write_text(script)
    return skill


def test_pycache_does_not_make_scripts_look_different(tmp_path):
    """The checkout accumulates a `__pycache__` the moment a script is imported; the installed copy
    does not. Comparing them raw reported three skills' `scripts/` as differing at once — a false
    "the install is behind", which is exactly the reading this comparison must get right."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    source = make_skill(checkout, "demo", "body\n")
    installed = make_installed(installed_root, "demo", "body\n")
    (source / "scripts" / "__pycache__").mkdir()
    (source / "scripts" / "__pycache__" / "x.cpython-311.pyc").write_bytes(b"\x00")
    assert harvest._subdir_diffs(installed, source) == []


def test_a_changed_script_is_not_an_install_that_matches(tmp_path):
    """The verdict branched on SKILL.md alone, so a skill whose script had changed while its
    procedure had not reported "installed copy matches the checkout" — with `subdirs_differing`
    naming `scripts` in the same payload, computed one line above the branch and never read.

    Confirmed 2026-09-05 by running this check right after fixing two bugs in this very script: the
    installed copy did not contain the function committed an hour earlier, and two of the three rows
    printed contradicted their own verdict.
    """
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same body\n", script="print('new')\n")
    make_installed(installed_root, "demo", "same body\n", script="print('old')\n")

    state = harvest.skill_state(FakeRunner(), "demo", checkout, installed_root, since=None)

    assert state["skill_md_identical"] is True
    assert state["subdirs_differing"] == ["scripts"]
    assert "matches" not in state["verdict"]
    assert "scripts/" in state["verdict"]
    assert "EXECUTES" in state["verdict"], "a stale script cannot be re-read into correctness"


OLD_SCRIPT = """
PATTERN = "old"


def helper():
    return PATTERN


def cmd_sweep(args):
    return helper()


def cmd_boundary(args):
    return 1


def cmd_skills_state(args):
    return 2
"""


def test_which_subcommands_differ_is_read_per_definition_not_per_file(tmp_path):
    """A `harvest.py` diff is nearly always somewhere else. Observed 2026-09-07: six commits stale,
    every one of them in `sweep`, so all three pre-check answers were current and the run had no way
    to know it — it diffed the whole file by hand instead."""
    old, new = tmp_path / "old.py", tmp_path / "new.py"
    old.write_text(OLD_SCRIPT)
    new.write_text(OLD_SCRIPT.replace('PATTERN = "old"', 'PATTERN = "new"'))

    # `sweep` reaches PATTERN through `helper`; the other two do not touch it.
    assert harvest.entry_points_differing(old, new) == ["sweep"]
    assert harvest.entry_points_differing(old, old) == []


def test_a_file_that_will_not_parse_answers_none_rather_than_nothing_differs(tmp_path):
    """An absent measurement must not read as a measured zero — the same rule the processes step
    follows when `ps` does not run."""
    old, new = tmp_path / "old.py", tmp_path / "new.py"
    old.write_text(OLD_SCRIPT)
    new.write_text("def cmd_sweep(:\n")
    assert harvest.entry_points_differing(old, new) is None


def test_a_stale_script_says_whether_the_answers_already_collected_are_affected(tmp_path, monkeypatch):
    """`skills-state` answers the staleness question from inside the copy under test: on a stale
    install `boundary`, `transcript` and `skills-state` itself have already run from the old code,
    and no ordering fixes that, because resolving the checkout is `skills-state`'s own job. Reported
    rather than removed, per the 2026-09-07 plan that found it benign by luck."""
    checkout, installed_root = tmp_path / "checkout", tmp_path / "installed"
    source = make_skill(checkout, "session-harvest", "same\n", script=OLD_SCRIPT)
    installed = make_installed(installed_root, "session-harvest", "same\n", script=OLD_SCRIPT)
    running = installed / "scripts" / "x.py"
    monkeypatch.setattr(harvest, "__file__", str(running))

    # Only `sweep` differs: the answers this run already collected are current.
    (source / "scripts" / "x.py").write_text(OLD_SCRIPT.replace('PATTERN = "old"', 'PATTERN = "new"'))
    state = harvest.skill_state(FakeRunner(), "session-harvest", checkout, installed_root, since=None)
    assert state["entry_points_differing"] == ["sweep"]
    assert "none of boundary, transcript, skills-state differ" in state["verdict"]

    # Now the check itself differs, so its own answer came from the old code.
    (source / "scripts" / "x.py").write_text(OLD_SCRIPT.replace("return 2", "return 3"))
    state = harvest.skill_state(FakeRunner(), "session-harvest", checkout, installed_root, since=None)
    assert state["entry_points_differing"] == ["skills-state"]
    assert "re-run them from the checkout" in state["verdict"]


def test_a_harvest_already_running_from_the_checkout_is_not_warned_about_itself(tmp_path, monkeypatch):
    """The note is about executing the copy under test. A run that has already switched to the
    checkout is using current code and has nothing to re-run."""
    checkout, installed_root = tmp_path / "checkout", tmp_path / "installed"
    source = make_skill(checkout, "session-harvest", "same\n", script=OLD_SCRIPT)
    make_installed(installed_root, "session-harvest", "same\n", script=OLD_SCRIPT.replace("return 2", "return 3"))
    monkeypatch.setattr(harvest, "__file__", str(source / "scripts" / "x.py"))

    state = harvest.skill_state(FakeRunner(), "session-harvest", checkout, installed_root, since=None)

    assert "entry_points_differing" not in state
    assert "IS the stale copy" not in state["verdict"]


def test_a_references_only_difference_is_not_a_stale_install(tmp_path):
    """`references/` is read on demand and inert, so a difference there changes no run. Counting it
    as staleness is how a check with three honest branches becomes one nobody reads — the same
    directory-scoped comparison fired the most expensive branch on a references-only commit in
    2026-08-30, which is why `_subdir_diffs` splits them at all."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    source = make_skill(checkout, "demo", "same body\n")
    installed = make_installed(installed_root, "demo", "same body\n")
    (source / "references").mkdir()
    (source / "references" / "r.md").write_text("new\n")
    (installed / "references").mkdir()
    (installed / "references" / "r.md").write_text("old\n")

    state = harvest.skill_state(FakeRunner(), "demo", checkout, installed_root, since=None)

    assert state["subdirs_differing"] == ["references"]
    assert "references/" in state["verdict"]
    assert "stale" not in state["verdict"]


def test_a_dirty_checkout_is_reached_when_only_the_script_differs(tmp_path):
    """The dirty and unpushed branches sat behind `if same:`, so a checkout dirty only in `scripts/`
    never reached the branch that says another session is mid-restructure — the case that rule was
    written for."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same body\n", script="print('new')\n")
    make_installed(installed_root, "demo", "same body\n", script="print('old')\n")
    runner = FakeRunner(
        {f"git -C {checkout} status --porcelain -- skills/demo": (0, " M skills/demo/scripts/x.py\n", "")}
    )

    state = harvest.skill_state(runner, "demo", checkout, installed_root, since=None)

    assert "DIRTY" in state["verdict"]
    assert "elsewhere in the skill" in state["verdict"]


@pytest.mark.parametrize(
    ("dirty", "ahead", "expected"),
    [
        ("", "", "install is stale"),
        (" M skills/demo/SKILL.md", "", "DIRTY"),
        ("", "abc123 an unpushed skill edit", "unpushed skill work"),
    ],
)
def test_the_same_diff_means_three_different_things(tmp_path, dirty, ahead, expected):
    """The diff is the trigger; the checkout's state is what decides the remedy.

    Confirmed both ways a day apart: the same non-empty diff meant "re-install" on a clean, pushed
    checkout and "another session is mid-restructure, touch nothing" on a dirty one. And a
    re-install cannot deliver an unpushed commit — the installer clones from the remote.
    """
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "new body\n")
    make_installed(installed_root, "demo", "old body\n")
    runner = FakeRunner(
        {
            "git -C": (0, "", ""),
            f"git -C {checkout} status --porcelain -- skills/demo": (0, dirty + "\n" if dirty else "", ""),
            f"git -C {checkout} rev-parse --abbrev-ref @{{u}}": (0, "origin/main\n", ""),
            f"git -C {checkout} log origin/main..HEAD --oneline": (0, ahead + "\n" if ahead else "", ""),
        }
    )
    state = harvest.skill_state(runner, "demo", checkout, installed_root, since=None)
    assert expected in state["verdict"]


def test_naming_a_skill_adds_it_rather_than_replacing_the_defaults(tmp_path):
    """`--skill` reads as additive in SKILL.md — "add `--skill <name>` for anything else this run
    used" — and dropped the defaults instead, so the harvest's own skill was the one that went
    unchecked. Confirmed 2026-09-05: a run passed `--skill plan-docs --skill
    invoke-task-conventions`, got two clean rows, and only a second call naming session-harvest
    explicitly found its SKILL.md had moved after session start with two unpushed commits.
    """
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    for name in (*harvest.DEFAULT_SKILLS, "invoke-task-conventions"):
        make_skill(checkout, name, "body\n")
        make_installed(installed_root, name, "body\n")
    args = harvest.build_parser().parse_args(
        [
            "skills-state",
            "--json",
            "--checkout",
            str(checkout),
            "--installed",
            str(installed_root),
            "--skill",
            "invoke-task-conventions",
        ]
    )

    payload = harvest.cmd_skills_state(args, FakeRunner())

    assert [s["skill"] for s in payload["skills"]] == [*harvest.DEFAULT_SKILLS, "invoke-task-conventions"]


def test_naming_a_default_skill_does_not_report_it_twice(tmp_path):
    """The additive form has to dedupe, or `--skill session-harvest` — the exact call the incident
    above ended with — reports that skill in two rows."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    for name in harvest.DEFAULT_SKILLS:
        make_skill(checkout, name, "body\n")
        make_installed(installed_root, name, "body\n")
    args = harvest.build_parser().parse_args(
        [
            "skills-state",
            "--json",
            "--checkout",
            str(checkout),
            "--installed",
            str(installed_root),
            "--skill",
            "session-harvest",
        ]
    )

    payload = harvest.cmd_skills_state(args, FakeRunner())

    assert [s["skill"] for s in payload["skills"]] == list(harvest.DEFAULT_SKILLS)


def test_a_skill_that_moved_after_the_session_began_is_named(tmp_path):
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    edit = "\x1eabc123 Me a later edit\n\nskills/demo/SKILL.md\n"
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, edit, "")})
    state = harvest.skill_state(runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z")
    assert state["moved_since_session_start"] is True
    assert "SKILL.md moved after this session began (1 commit(s)) — re-read" in state["verdict"]
    assert state["move_baseline"] == {"instant": "2026-09-02T09:00:00Z", "is": "this session began"}


def test_a_skill_whose_scripts_moved_and_skill_md_did_not_is_still_named(tmp_path):
    """The trigger was the last commit touching `SKILL.md`, so a change to `scripts/` alone — the
    code a session executes — was never reported. Confirmed 2026-09-13: `session-bash-audit` had two
    commits since session start, to `scripts/` and `references/`, and reported no move. Each part
    gets its own remedy, and none of them is the `SKILL.md` re-read."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    log = (
        "\x1e28099cd Me counted once\n\nskills/demo/scripts/audit.py\n"
        "\x1e692a391 Me research note\n\nskills/demo/references/research.md\n"
    )
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, log, "")})

    state = harvest.skill_state(runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z")

    assert state["moved_since_session_start"] is True
    assert "scripts/ moved after this session began (1 commit(s)) — a call made earlier" in state["verdict"]
    assert "references/ moved after this session began (1 commit(s)) — read on demand" in state["verdict"]
    assert "SKILL.md moved" not in state["verdict"]
    assert "re-read" not in state["verdict"]


def test_a_history_that_cannot_be_read_is_not_reported_as_nothing_moved(tmp_path):
    """A failed log read as an empty one says "nothing moved", the one wrong answer that prompts
    nobody — the same failure the store's git log check guards against."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    runner = FakeRunner({f"git -C {checkout} log --since=": (128, "", "fatal: bad default revision")})

    state = harvest.skill_state(runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z")

    assert state["moved_since_session_start"] is None
    assert "could not read what moved" in state["verdict"]


def test_each_moved_commit_says_which_part_of_the_skill_it_touched(tmp_path):
    """Confirmed 2026-09-13: `plan-docs` showed seven commits under a line naming `SKILL.md`, to a
    session that had never loaded that file and had run `plans.py` eight times. Four of the seven
    touched `scripts/` — the code it had executed — and nothing in the output said which four."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    log = (
        "\x1e15ab22d Me say what the first call does\n\nskills/demo/SKILL.md\n"
        "\x1ed7f1184 Me commit takes a set\n\nskills/demo/SKILL.md\nskills/demo/scripts/plans.py\n"
        "\x1e6b0e71d Me a reference note\n\nskills/demo/references/rationale.md\n"
    )
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, log, "")})

    state = harvest.skill_state(runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z")

    assert state["moves_since_session_start"] == [
        "15ab22d Me say what the first call does (SKILL.md)",
        "d7f1184 Me commit takes a set (SKILL.md, scripts/)",
        "6b0e71d Me a reference note (references/)",
    ]


def test_the_move_baseline_is_named_in_the_verdict_it_produced(tmp_path):
    """Session start is the wrong instant for the skill doing the asking. Confirmed 2026-09-07: a
    harvest invoked in a session's last minutes had its own body enter context *after* the three
    commits the check reported, so the warning said the held copy might be superseded when it was
    the newest text on the machine — a false positive every harvest gets on itself.

    The baseline is therefore per skill, and the verdict names which one it used: a baseline that
    changes silently is the same defect one level up from the one it fixes.
    """
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    edit = "\x1eabc123 Me a later edit\n\nskills/demo/SKILL.md\n"
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, edit, "")})
    state = harvest.skill_state(
        runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z", baseline="this skill entered context"
    )
    assert "moved after this skill entered context" in state["verdict"]
    assert "moved after this session began" not in state["verdict"]


def test_a_held_skill_md_that_is_neither_side_gets_the_help_probe_first(tmp_path):
    """Install and checkout agree, and SKILL.md moved after the skill was loaded: a re-install ran
    mid-session, so the copy in context is on neither side of any diff. Confirmed 2026-09-26 on
    `plan-docs`, ten commits: two `--help` calls answered what a ~700-line re-read would have."""
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    edit = "\x1eabc123 Me a later edit\n\nskills/demo/SKILL.md\n"
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, edit, "")})
    state = harvest.skill_state(
        runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z", baseline="this skill entered context"
    )
    assert f"python3 {installed_root / 'demo' / 'scripts' / 'x.py'} <subcommand> --help" in state["verdict"]
    assert "neither side" in state["verdict"]


def test_no_help_probe_when_the_diff_is_still_sound_or_there_is_no_script(tmp_path):
    """A differing install still holds the loaded text on one side, so the diff remains the remedy;
    and a prose-only skill has no CLI surface to probe."""
    edit = "\x1eabc123 Me a later edit\n\nskills/demo/SKILL.md\n"
    checkout = tmp_path / "a" / "checkout"
    installed_root = tmp_path / "a" / "installed"
    make_skill(checkout, "demo", "new\n")
    make_installed(installed_root, "demo", "old\n")
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, edit, "")})
    state = harvest.skill_state(
        runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z", baseline="this skill entered context"
    )
    assert "--help" not in state["verdict"]

    checkout = tmp_path / "b" / "checkout"
    installed_root = tmp_path / "b" / "installed"
    for skill in (make_skill(checkout, "demo", "same\n"), make_installed(installed_root, "demo", "same\n")):
        (skill / "scripts" / "x.py").unlink()
    runner = FakeRunner({f"git -C {checkout} log --since=": (0, edit, "")})
    state = harvest.skill_state(
        runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z", baseline="this skill entered context"
    )
    assert "--help" not in state["verdict"]


def test_a_skills_load_instant_comes_from_the_sessions_own_skill_calls(monkeypatch):
    """The instant that matters for "did this move under me" is when the text was read. It is in the
    transcript: a `Skill` tool call names the skill and carries a timestamp."""

    entries = [
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "a", "name": "Skill", "input": {"skill": "plan-docs"}}],
            timestamp="2026-09-08T09:06:44.390Z",
        ),
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "b", "name": "Skill", "input": {"skill": "plan-docs"}}],
            timestamp="2026-09-08T11:00:00.000Z",
        ),
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "c", "name": "Bash", "input": {"command": "ls"}}],
            timestamp="2026-09-08T12:00:00.000Z",
        ),
    ]
    monkeypatch.setattr(harvest, "resolve_transcript", lambda *a, **k: SimpleNamespace(entries=entries))
    args = argparse.Namespace(since=None, session=None, job=None, expect=None)

    # The earliest call wins: a skill re-invoked later was already in context.
    assert harvest._skill_load_instants(args) == {"plan-docs": "2026-09-08T09:06:44.390Z"}

    # An explicit --since is the override, and overriding every row's baseline is legitimate.
    supplied = argparse.Namespace(since="2026-01-01T00:00:00Z", session=None, job=None, expect=None)
    assert harvest._skill_load_instants(supplied) == {}


def test_a_slash_command_invocation_is_a_load_too(monkeypatch):
    """A user-typed `/<skill>` is not a `Skill` tool call — the harness records it as a
    `<command-name>` in a *user* message. Reading tool calls alone therefore missed the invocation
    path this skill's own description calls the one to rely on.

    Confirmed 2026-09-08 on the first real `/session-harvest` run after the load baseline landed: it
    fell back to session start and produced exactly the false positive the baseline exists to
    remove — eleven commits reported as possibly superseding a copy that had been read after all of
    them.
    """
    typed = "<command-message>session-harvest</command-message>\n<command-name>/session-harvest</command-name>"
    entries = [{"type": "user", "timestamp": "2026-09-08T14:05:55.319Z", "message": {"content": typed}}]
    monkeypatch.setattr(harvest, "resolve_transcript", lambda *a, **k: SimpleNamespace(entries=entries))
    args = argparse.Namespace(since=None, session=None, job=None, expect=None)

    assert harvest._skill_load_instants(args) == {"session-harvest": "2026-09-08T14:05:55.319Z"}


def test_a_boundary_flag_is_not_a_boundary_call():
    """`sweep --boundary` and `boundary` carry the same word, and `\\b` matches after a hyphen. Every
    sweep therefore counted as a harvest: confirmed 2026-09-08, a session's first real harvest
    reported `harvest #10` off nine `sweep --boundary` calls and printed the "an earlier harvest
    filed the artifacts below" instruction for eight harvests that never happened."""
    assert harvest.BOUNDARY_CALL_RE.search("python3 $H boundary")
    assert harvest.BOUNDARY_CALL_RE.search("python3 ~/.agents/skills/session-harvest/scripts/harvest.py boundary")
    assert not harvest.BOUNDARY_CALL_RE.search("python3 $H sweep --boundary 2026-09-08T17:06:03+03:00")
    assert not harvest.BOUNDARY_CALL_RE.search("python3 $H claims --until X --boundary Y")


def test_a_manifest_comment_does_not_make_a_consumer(tmp_path):
    """A manifest comment citing the repo's own `plans/` directory matched the plans store by its
    basename, so a sweep reported the store as installed by three repos that merely mention the
    word. Confirmed 2026-09-08 by the check's own first real run. A consumer relationship is
    declared in configuration; commentary is not a declaration."""
    candidate = tmp_path / "a-repo"
    candidate.mkdir()
    (candidate / "pyproject.toml").write_text("# see plans/2026-08-27-survey.md for why\ndependencies = []\n")
    assert not harvest._installs(candidate, "plans")

    (candidate / "pyproject.toml").write_text('dependencies = ["plans @ git+ssh://x/plans"]\n')
    assert harvest._installs(candidate, "plans")


# --------------------------------------------------------------------------------------------
# the sweep's parsers
# --------------------------------------------------------------------------------------------


def test_a_plan_in_another_repo_naming_a_changed_source_file_is_a_candidate(tmp_path, monkeypatch):
    """Every other check in the sweep asks what is dangling *for* this session; this asks the
    inverse. Confirmed 2026-09-05: a session replaced a repo's gate-output mechanism and a plan in a
    different repo recorded that mechanism as its landed layer 2 — with a comparison scheduled a
    week later against a baseline saved to isolate exactly that layer, so it would have measured a
    week of sessions in neither mode and read the null result as "the change did nothing".
    """
    root = tmp_path / "projects"
    mine = root / "mine"
    theirs = root / "theirs"
    for repo in (mine, theirs):
        (repo / ".git").mkdir(parents=True)
        (repo / "plans").mkdir()
    (theirs / "plans" / "2026-09-05-layered.md").write_text("layer 2 lives in `steps.py` and is landed\n")
    (mine / "plans" / "2026-09-05-my-own.md").write_text("this plan also names steps.py constantly\n")
    store = tmp_path / "store"
    (store / "theirs").mkdir(parents=True)
    (store / "theirs" / "filed.md").write_text("nothing relevant here\n")

    monkeypatch.setattr(harvest, "projects_root", lambda: root)
    monkeypatch.setattr(harvest, "_stores", lambda: [("plans", store), ("plans-sensitive", tmp_path / "nope")])
    entries = [
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": str(theirs / "steps.py")}}],
        )
    ]

    found = harvest.superseded_candidates(entries, mine)

    assert found["names"] == ["steps.py"]
    assert [Path(row["plan"]).name for row in found["candidates"]] == ["2026-09-05-layered.md"]
    assert all("mine" not in row["plan"] for row in found["candidates"]), (
        "the session's own plans are the one place it is already reading; including them turns every "
        "edit to a well-discussed file into a page of true-but-useless rows"
    )


def test_repos_that_install_a_changed_repo_are_named_from_their_own_manifests(tmp_path):
    """Confirmed 2026-09-05: a session changed the module every gate step in a repo now calls,
    pushed it, and the sweep reported dirty 0, unpushed 0, CI green, nothing owed. By every check
    the skill ran that session was finished, and it was not — that repo's bootstrap is unpinned, so
    every consumer's next CI run installs whatever `main` is at that moment.

    Consumers are derived from the machine rather than from documentation, the same move `scan`
    makes for private terms: it works for a repo that documents nothing, and a manifest naming the
    repo is evidence whether or not either side wrote the relationship down.
    """
    root = tmp_path / "projects"
    library = root / "repo-tasks"
    consumer = root / "a-consumer"
    stranger = root / "unrelated"
    for repo in (library, consumer, stranger):
        (repo / ".git").mkdir(parents=True)
    (consumer / "pyproject.toml").write_text('dependencies = ["repo-tasks @ git+ssh://..."]\n')
    (stranger / "pyproject.toml").write_text('dependencies = ["httpx"]\n')
    (library / "contributing").mkdir()
    (library / "contributing" / "consumer-sweep.md").write_text("A push to main is a deploy.\n")

    found = harvest.consumer_candidates(root, [library])

    assert len(found) == 1
    assert found[0]["consumers"] == [str(consumer)]
    assert found[0]["docs"] == ["contributing/consumer-sweep.md"]

    # A repo nobody installs and that documents nothing produces no row at all.
    assert harvest.consumer_candidates(root, [stranger]) == []


def _edit(path: Path) -> dict[str, object]:
    block = {"type": "tool_use", "id": str(path), "name": "Edit", "input": {"file_path": str(path)}}
    return blocks_entry("assistant", [block])


SWEEP_DOC = """# Consumer sweep

## When to sweep

After changing any of: the `repo-tasks-quality` manifest in `pyproject.toml`, anything under
`src/repo_tasks/configs/`, or a `quality.*` / `test.*` step that shells out to a binary.

## The sweep
"""


def test_a_consumer_doc_trigger_decides_whether_a_push_obliges_anyone(tmp_path, capsys):
    """Confirmed 2026-09-18: five consumers and an instruction to report an obligation, for a push
    of a CI workflow, docs, plans and one test — none of it under the paths the repo's own
    `consumer-sweep.md` lists under "When to sweep". The check named that doc and never read it."""
    root = tmp_path / "projects"
    library, consumer = root / "repo-tasks", root / "a-consumer"
    for repo in (library, consumer):
        (repo / ".git").mkdir(parents=True)
    (consumer / "pyproject.toml").write_text('dependencies = ["repo-tasks @ git+ssh://..."]\n')
    (library / "contributing").mkdir()
    (library / "contributing" / "consumer-sweep.md").write_text(SWEEP_DOC)

    def edits(*paths: str) -> list[dict[str, object]]:
        return [_edit(library / p) for p in paths]

    quiet = harvest.consumer_candidates(root, [library], entries=edits(".github/workflows/ci.yml", "tests/test_x.py"))
    assert quiet[0]["trigger"]["matched"] == []
    harvest._print_consumers(quiet)
    out = capsys.readouterr().out
    assert "matches nothing this session wrote here" in out
    assert "a push here is a deploy there" not in out

    fired = harvest.consumer_candidates(
        root, [library], entries=edits("src/repo_tasks/configs/ruff.toml", "tasks/quality.py")
    )
    assert fired[0]["trigger"]["matched"] == ["src/repo_tasks/configs/ruff.toml", "tasks/quality.py"]
    harvest._print_consumers(fired)
    assert "a push here is a deploy there" in capsys.readouterr().out

    # A doc stating no trigger keeps the unconditional warning, and says why.
    (library / "contributing" / "consumer-sweep.md").write_text("A push to main is a deploy.\n")
    unknown = harvest.consumer_candidates(root, [library], entries=edits("README.md"))
    harvest._print_consumers(unknown)
    out = capsys.readouterr().out
    assert "no trigger could be read" in out
    assert "a push here is a deploy there" in out


def test_a_throwaway_repo_under_a_scratch_root_is_set_aside_not_swept(tmp_path, monkeypatch):
    """Confirmed 2026-09-18: a repo a session `git init`-ed in its job scratchpad to probe one
    question was swept as touched — no upstream, no GitHub host, and its basename `clone` matched two
    unrelated repos' installers as consumers. It is named rather than dropped."""
    scratch_root = tmp_path / "jobs"
    real, throwaway = tmp_path / "work" / "real", scratch_root / "abc" / "tmp" / "clone"
    monkeypatch.setattr(harvest, "_scratch_roots", lambda: [scratch_root.resolve()])
    for repo in (real, throwaway):
        repo.mkdir(parents=True)
    entries = [_edit(p / "f.py") for p in (real, throwaway)]

    def runner(argv, cwd=None):
        if "rev-parse" in argv and "--show-toplevel" in argv:
            return harvest.Ran(tuple(argv), 0, str(argv[2]) + "\n", "")
        return harvest.Ran(tuple(argv), 0, "", "")

    set_aside: list[Path] = []
    swept = harvest._touched_repos(runner, [], entries, set_aside)
    assert swept == [real]
    assert set_aside == [throwaway]
    # Asked for by name, it is swept.
    assert harvest._touched_repos(runner, [str(throwaway)], [], []) == [throwaway]


def test_a_bootstrap_script_counts_as_a_manifest(tmp_path):
    """The unpinned bootstrap is the mechanism that makes a push a deploy, so the file that carries
    it has to be one of the places a consumer is recognised from."""
    root = tmp_path / "projects"
    library = root / "repo-tasks"
    consumer = root / "a-consumer"
    for repo in (library, consumer):
        (repo / ".git").mkdir(parents=True)
    (consumer / "bootstrap-repo-tasks.sh").write_text("uv tool install git+https://x/repo-tasks\n")

    found = harvest.consumer_candidates(root, [library])
    assert found[0]["consumers"] == [str(consumer)]


def test_an_open_plan_about_a_file_this_session_changed_is_offered_back(tmp_path):
    """The case is a session that builds everything a plan designed and never touches the plan:
    it keeps saying `idea`, `absorb` never raises it because nothing is terminal, and the next
    session reading `list` sees live design work. Confirmed 2026-09-05, two plans in one repo.

    A prompt rather than a gate, and the measurement is the reason. Family-wide 2026-09-08, 43% of
    open plans name a source file that moved after them — noise. The three-mention subject proxy
    puts it at 14%, and what is left is structural: a session that edits a file makes every plan
    about that file look stale.
    """
    repo = tmp_path / "repo"
    (repo / "plans").mkdir(parents=True)
    subject = "---\nstatus: idea\nupdated: 2026-09-01\n---\n\nsteps.py, steps.py again, and steps.py once more\n"
    (repo / "plans" / "2026-09-01-designs-steps.md").write_text(subject)
    (repo / "plans" / "2026-09-01-mentions-once.md").write_text(
        "---\nstatus: idea\nupdated: 2026-09-01\n---\n\nas context, steps.py exists\n"
    )
    (repo / "plans" / "2026-09-01-already-landed.md").write_text(
        "---\nstatus: landed\nupdated: 2026-09-01\n---\n\nsteps.py steps.py steps.py\n"
    )
    (repo / "plans" / "2026-09-07-written-during.md").write_text(
        "---\nstatus: idea\nupdated: 2026-09-07\n---\n\nsteps.py steps.py steps.py\n"
    )
    entries = [
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": str(repo / "steps.py")}}],
        )
    ]

    found = harvest.plans_this_session_may_have_landed(entries, repo, "2026-09-05T09:00:00Z")

    named = [row["plan"] for row in found["candidates"]]
    assert named == ["2026-09-01-designs-steps.md"], (
        "one mention is a citation, a terminal plan is already handled by the retirement prompt, and "
        "a plan updated after the session began cannot have been left behind by it"
    )


def _open_plan(repo: Path, name: str, body: str) -> None:
    (repo / "plans" / name).write_text(f"---\nstatus: idea\nupdated: 2026-09-01\n---\n\n{body}\n")


def test_rows_naming_only_the_repos_vocabulary_fold_into_a_count(tmp_path, capsys):
    """Measured 2026-09-26 on a replayed setup-repo session: 15 rows, 11 matching only `setup.toml`,
    which is the subject of 23% of that repo's open plans — its vocabulary, not a signal about one
    plan. The rows that also named `netdoctor.py` or `wsl.py` were the informative ones."""
    repo = tmp_path / "repo"
    (repo / "plans").mkdir(parents=True)
    for i in range(5):
        _open_plan(repo, f"2026-09-01-config-{i}.md", "setup.toml " * 3)
    _open_plan(repo, "2026-09-01-wsl.md", "setup.toml " * 3 + "wsl.py " * 3)
    _open_plan(repo, "2026-09-01-util.md", "util.py " * 3)
    for i in range(13):
        _open_plan(repo, f"2026-09-01-unrelated-{i}.md", "nothing here")
    entries = [_edit(repo / name) for name in ("setup.toml", "wsl.py", "util.py")]

    found = harvest.plans_this_session_may_have_landed(entries, repo, "2026-09-05T09:00:00Z")
    assert found["open_plans"] == 20
    assert found["vocabulary"] == {"setup.toml": 6}
    assert sum(row["vocabulary_only"] for row in found["candidates"]) == 5

    harvest._print_may_have_landed(found)
    out = capsys.readouterr().out
    assert "2026-09-01-wsl.md" in out, "a row that also names a specific file stays listed"
    assert "2026-09-01-util.md" in out
    assert "2026-09-01-config-0.md" not in out
    assert "+ 5 more name only setup.toml (setup.toml is the subject of 6 of 20 open plans here)" in out

    harvest._print_may_have_landed(found, verbose=True)
    out = capsys.readouterr().out
    assert all(f"2026-09-01-config-{i}.md" in out for i in range(5))
    assert "more name only" not in out


def test_a_small_repo_never_folds_on_share_alone(tmp_path):
    """1 of 8 open plans is already 12%, so share needs a count floor or a small repo folds everything."""
    repo = tmp_path / "repo"
    (repo / "plans").mkdir(parents=True)
    for i in range(4):
        _open_plan(repo, f"2026-09-01-config-{i}.md", "setup.toml " * 3)
    found = harvest.plans_this_session_may_have_landed([_edit(repo / "setup.toml")], repo, "2026-09-05T09:00:00Z")
    assert found["vocabulary"] == {}
    assert not any(row["vocabulary_only"] for row in found["candidates"])


def test_a_session_that_changed_no_source_file_searches_nothing(tmp_path, monkeypatch):
    """Documents are excluded on purpose: a plan naming another plan is a citation, which
    `plan-docs`' own `refs` answers, and searching for `.md` basenames would hit every retirement."""
    monkeypatch.setattr(harvest, "projects_root", lambda: tmp_path)
    monkeypatch.setattr(harvest, "_stores", lambda: [])
    entries = [
        blocks_entry(
            "assistant",
            [{"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": "/repo/plans/2026-09-08-x.md"}}],
        )
    ]
    assert harvest.superseded_candidates(entries, None) == {
        "names": [],
        "not_searched": [],
        "unowned": [],
        "searched": [],
        "candidates": [],
    }


def test_a_name_every_package_has_its_own_copy_of_is_not_searched(tmp_path, monkeypatch, capsys):
    """Confirmed 2026-09-13 on a `repo-tasks` session: 24 rows, 22 matching nothing but `__init__.py`
    or `pyproject.toml`, and the two real ones — both on `selfinstall.py` — below them. Those two names
    are tracked by 36 and 27 of the machine's 71 checkouts; `selfinstall.py` by one. The sibling
    written-paths check learned the same lesson: a section that has been all-false-positive once is
    one the next harvest skims. The skipped names are printed, so the omission is not silent."""
    root = tmp_path / "projects"
    mine, theirs = root / "repo-tasks", root / "a-consumer"
    for repo in (mine, theirs):
        (repo / ".git").mkdir(parents=True)
        (repo / "plans").mkdir()
    (theirs / "plans" / "2026-08-23-tool-conflict.md").write_text("repo-tasks' fix lives in selfinstall.py\n")
    (theirs / "plans" / "2026-09-01-packaging.md").write_text("pyproject.toml and src/pkg/__init__.py\n")
    monkeypatch.setattr(harvest, "projects_root", lambda: root)
    monkeypatch.setattr(harvest, "_stores", lambda: [])

    def edit(path: Path) -> dict[str, object]:
        block = {"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": str(path)}}
        return blocks_entry("assistant", [block])

    entries = [edit(mine / "src" / "pkg" / name) for name in ("__init__.py", "selfinstall.py")]
    entries.append(edit(mine / "pyproject.toml"))

    found = harvest.superseded_candidates(entries, mine)
    assert found["names"] == ["selfinstall.py"]
    assert found["not_searched"] == ["__init__.py", "pyproject.toml"]
    assert [Path(row["plan"]).name for row in found["candidates"]] == ["2026-08-23-tool-conflict.md"]

    harvest._print_superseded(found)
    assert "not searched: __init__.py, pyproject.toml" in capsys.readouterr().out

    # A session that changed only such names still says what it skipped, rather than "no source file".
    only = harvest.superseded_candidates([edit(mine / "pyproject.toml")], mine)
    harvest._print_superseded(only)
    out = capsys.readouterr().out
    assert "not searched: pyproject.toml" in out
    assert "changed no other source file" in out

    # Tool config is searched even though its name is as fixed: `repo-tasks` propagates a canonical
    # `pytest.ini`, so a consumer's plan naming it may be about exactly this change.
    (theirs / "plans" / "2026-09-02-testpaths.md").write_text("repo-tasks' canonical pytest.ini broke collection\n")
    config = harvest.superseded_candidates([edit(mine / "src" / "repo_tasks" / "configs" / "pytest.ini")], mine)
    assert config["not_searched"] == []
    assert [Path(row["plan"]).name for row in config["candidates"]] == ["2026-09-02-testpaths.md"]


def test_a_plan_elsewhere_must_name_the_changed_files_repo_too(tmp_path, monkeypatch, capsys):
    """Matching on the basename alone made every sibling's own `ci.yml` or `util.py` a candidate.
    Measured twice, 2026-09-13 and 2026-09-20: 0 true positives in the cross-repo rows, 12 of 12 noise
    on the second run. A plan about another repo's mechanism names that repo, or its own reader could
    not follow it — so the subject is the pair, and a plan that lives in the owning repo, in its
    checkout or its store mirror, needs no mention of it."""
    root = tmp_path / "projects"
    mine, theirs = root / "power-user-linux-setup", root / "a-consumer"
    for repo in (mine, theirs):
        (repo / ".git").mkdir(parents=True)
        (repo / "plans").mkdir()
    (theirs / "plans" / "own-ci.md").write_text("our ci.yml runs the gate twice\n")
    (theirs / "plans" / "about-it.md").write_text("power-user-linux-setup's ci.yml pins the runner\n")
    (theirs / "plans" / "far-apart.md").write_text(
        "we install through power-user-linux-setup.\n\nseparately, our own ci.yml is slow\n"
    )
    store = tmp_path / "store"
    (store / "github.com-personal" / "power-user-linux-setup").mkdir(parents=True)
    (store / "github.com-personal" / "power-user-linux-setup" / "filed.md").write_text("ci.yml is slow\n")
    (store / "github.com-personal" / "a-consumer").mkdir(parents=True)
    (store / "github.com-personal" / "a-consumer" / "filed.md").write_text("ci.yml is slow here too\n")
    monkeypatch.setattr(harvest, "projects_root", lambda: root)
    monkeypatch.setattr(harvest, "_stores", lambda: [("plans", store)])

    def edit(path: Path) -> dict[str, object]:
        block = {"type": "tool_use", "id": "a", "name": "Edit", "input": {"file_path": str(path)}}
        return blocks_entry("assistant", [block])

    found = harvest.superseded_candidates([edit(mine / ".github" / "workflows" / "ci.yml")], mine)
    assert sorted(Path(row["plan"]).relative_to(tmp_path).as_posix() for row in found["candidates"]) == [
        "projects/a-consumer/plans/about-it.md",
        "store/github.com-personal/power-user-linux-setup/filed.md",
    ]

    # A file outside every repository has no repo for a plan to name, so it is not searched — and says so.
    scratch = harvest.superseded_candidates([edit(tmp_path / "scratch" / "ci.yml")], mine)
    assert scratch["candidates"] == []
    assert scratch["unowned"] == ["ci.yml"]
    harvest._print_superseded(scratch)
    assert "not searched: ci.yml — outside every repository" in capsys.readouterr().out


def test_depends_on_is_matched_in_frontmatter_at_line_start(tmp_path):
    """A bare search for the word also hits a plan whose body tabulates a schema field of that
    name, and a false positive here reads exactly like a real queue entry."""
    plans = tmp_path / "plans"
    plans.mkdir()
    (plans / "real.md").write_text("---\nstatus: idea\ndepends_on: [repo-a, repo-b]\n---\n\nbody\n")
    (plans / "impostor.md").write_text("---\nstatus: idea\n---\n\n| field | depends_on: something |\n")
    (plans / "indented.md").write_text("---\nstatus: idea\n---\n\n  depends_on: not frontmatter\n")
    found = harvest.depends_on(tmp_path)
    assert found == [{"plan": "real.md", "targets": ["repo-a", "repo-b"]}]


def test_a_loopback_bind_does_not_close_the_finding(tmp_path, monkeypatch):
    """Liveness and bind address are two of three questions; the third is what it serves.

    Confirmed 2026-09-02: an `http.server` deliberately bound to `127.0.0.1`, orphaned, three and a
    half hours old, serving a repository root whose gitignored `.env` answered 200. A check framed
    entirely as reachability terminates at the safe-looking branch.
    """
    served = tmp_path / "repo"
    (served / ".git").mkdir(parents=True)
    (served / ".env").write_text("SECRET=1\n")
    ss_output = (
        "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
        'LISTEN 0      5      127.0.0.1:8765     0.0.0.0:*         users:(("python3",pid=42,fd=3))\n'
    )
    runner = FakeRunner({"ss -ltnp": (0, ss_output, "")})
    table = {42: harvest.Process(1, 42, "S", 12862, f"python3 -m http.server 8765 --directory {served}")}
    result = harvest.sockets(runner, table)
    listener = result["listeners"][0]
    assert listener["exposed"] is False, "the bind really is loopback"
    assert result["over_a_repo"] == [listener], "and it is still a finding"
    assert listener["processes"][0]["readable_secrets"] == [".env"]


def test_a_browsers_working_directory_is_not_what_it_serves(tmp_path):
    """Every process has a cwd; reading one as "what it serves" turned a browser that happened to
    be started from a repository into a finding about that repository."""
    ss_output = 'LISTEN 0 5 127.0.0.1:9533 0.0.0.0:* users:(("chrome",pid=99,fd=7))\n'
    runner = FakeRunner({"ss -ltnp": (0, "header\n" + ss_output, "")})
    table = {99: harvest.Process(1, 99, "S", 500, "/opt/chrome --remote-debugging-port=9533")}
    result = harvest.sockets(runner, table)
    assert result["over_a_repo"] == []
    assert "serves" not in result["listeners"][0]["processes"][0]


def test_the_sweeps_own_pipeline_is_not_a_surviving_process(monkeypatch):
    """The `ps` reading the table and whatever filters its output are children of the harness with
    an age of zero. Reporting them as processes this session left running is the sweep measuring
    itself, and it buries the real survivors under noise."""
    monkeypatch.setattr(harvest.os, "getpid", lambda: 500)
    table = {
        10: harvest.Process(1, 10, "S", 9999, "claude --session"),
        500: harvest.Process(10, 500, "S", 0, "python3 harvest.py sweep"),
        501: harvest.Process(500, 500, "S", 0, "ps -eo pid="),
        600: harvest.Process(10, 600, "S", 36000, "bash -c until gh run view; do sleep 30; done"),
    }
    result = harvest.processes(FakeRunner(), table)
    assert [row["pid"] for row in result["session_children"]] == [600]
    assert result["harness_pid"] == 10


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "127.0.0.53%lo", "127.0.0.54", "127.1.2.3", "::1", "[::1]", "[::ffff:127.0.0.1]", "localhost"],
)
def test_all_of_the_loopback_range_is_loopback(host):
    """Confirmed 2026-09-12 on this skill's own sweep: systemd-resolved's `127.0.0.53%lo:53` and
    `127.0.0.54:53` were reported `EXPOSED beyond loopback`, because loopback was a tuple of four
    spellings rather than a range. The first one names the `lo` interface in its own zone suffix."""
    assert harvest.is_loopback(host) is True


@pytest.mark.parametrize("host", ["0.0.0.0", "[::]", "::", "*", "192.168.1.5", "10.0.0.1", "not-an-address"])
def test_a_wildcard_or_routable_bind_stays_exposed(host):
    """The asymmetry is the point: the failure this row exists to prevent is calling a reachable
    server safe, so anything that does not parse as loopback is reported as exposed."""
    assert harvest.is_loopback(host) is False


def test_a_listener_says_whether_a_session_still_holds_it():
    """Step 5's rule turns on "reparented to `systemd --user` rather than held by a live session",
    and until 2026-09-06 the sweep printed neither the parent nor its command. Confirmed 2026-09-05:
    deciding what to report took two further `ps -o pid,ppid` calls the sweep had the data for, and
    without the second one "orphaned" would have been an assumption."""
    ss_output = 'LISTEN 0 5 127.0.0.1:8765 0.0.0.0:* users:(("python3",pid=42,fd=3))\n'
    runner = FakeRunner({"ss -ltnp": (0, "header\n" + ss_output, "")})
    table = {
        7: harvest.Process(1, 7, "S", 90000, "/usr/lib/systemd/systemd --user"),
        42: harvest.Process(7, 42, "S", 900, "python3 -m http.server 8765"),
    }
    served = harvest.sockets(runner, table)["listeners"][0]["processes"][0]
    assert served["orphaned"] is True, "parented to systemd --user, so no session holds it"
    assert served["parent"].endswith("systemd --user")

    table[42] = harvest.Process(7, 42, "S", 900, "python3 -m http.server 8765")
    table[7] = harvest.Process(1, 7, "S", 90000, "-zsh")
    held = harvest.sockets(runner, table)["listeners"][0]["processes"][0]
    assert held["orphaned"] is False, "a live shell holds it — somebody is working"


def test_a_parent_missing_from_the_listing_is_unknown_rather_than_orphaned():
    """The sweep supplies this fact; inventing it would defeat the point of supplying it."""
    proc = harvest.Process(4242, 99, "S", 900, "python3 -m http.server")
    assert harvest.parentage({99: proc}, proc)["orphaned"] is None


def test_a_process_started_after_the_sessions_last_activity_is_not_that_sessions():
    """Confirmed 2026-09-05: an `http.server` whose start was 36 minutes after the harvested
    session's last entry was nearly reported as that session's own leftover — the misattribution
    step 5 already warns about for unpushed commits, arriving through a different door."""
    two_hours_ago = (harvest.datetime.now(harvest.UTC) - harvest.timedelta(hours=2)).isoformat()
    assert harvest.started_after(600, two_hours_ago) is True, "ten minutes old, so it began after"
    assert harvest.started_after(36000, two_hours_ago) is False, "ten hours old, so it predates it"
    assert harvest.started_after(600, None) is None, "no transcript, so no claim either way"


def test_a_machine_without_ps_reports_unavailable_rather_than_no_survivors():
    """`ps -eo` is POSIX and does not exist on Windows. An empty table cannot mean "nothing is
    running" — `ps` cannot omit the process reading it — so zero survivors there would be a clean
    bill of health from a step that never ran, which is the failure this sweep exists to prevent.
    The sockets step already answers this way; the processes step did not until 2026-09-04."""
    result = harvest.processes(FakeRunner({"ps": (127, "", "ps: command not found")}))
    assert result["available"] is False
    assert "session_children" not in result, "an absent measurement must not read as a measured zero"


class BoundedTable(dict[int, object]):
    """A process table that refuses to be walked forever.

    The bug this guards was an ancestor walk with no visited-set: a `ppid` cycle made it append
    until the machine ran out of memory. Reproducing that literally would hang the suite for
    thirteen minutes and then die, which is what it did in CI — so the table bounds the walk and
    fails immediately instead. The limit is far above what a correct walk needs (a few lookups for
    the chain, then at most twelve per process for the descendant walk) and far below anything a
    runaway reaches.

    `Process` is not available as a type here: the script is loaded by path, so every symbol it
    exposes is a value rather than a name a type expression can use — the same reason this file
    suppresses `reportAny` at the top.
    """

    def __init__(self, rows: dict[int, object], limit: int = 1000):
        super().__init__(rows)
        self.limit: int = limit
        self.lookups: int = 0

    @override
    def __getitem__(self, key: int) -> object:
        self.lookups += 1
        if self.lookups > self.limit:
            raise AssertionError(f"walked the process table {self.limit} times — it is not terminating")
        return super().__getitem__(key)


def test_a_cycle_in_the_parent_chain_terminates_instead_of_exhausting_memory(monkeypatch):
    """Confirmed 2026-09-10: a Windows CI runner died with MemoryError inside this walk, and because
    the sweep then printed nothing at all, the visible failure was a JSON parse error in the script
    reading its stdout — a defect here surfacing as a defect two processes away.

    PID reuse is what makes a cycle reachable: a process exits, its pid is recycled, and a survivor
    still carrying the old number as its `ppid` now points at a descendant. Nothing about that is
    Windows-specific; Windows CI just has the churn to produce it.
    """
    monkeypatch.setattr(harvest.os, "getpid", lambda: 500)
    table = BoundedTable(
        {
            10: harvest.Process(1, 10, "S", 9999, "claude --session"),
            300: harvest.Process(400, 300, "S", 8000, "recycled pid, parent of its own ancestor"),
            400: harvest.Process(300, 400, "S", 8000, "the other half of the cycle"),
            500: harvest.Process(400, 500, "S", 0, "python3 harvest.py sweep"),
            600: harvest.Process(10, 600, "S", 36000, "bash -c until gh run view; do sleep 30; done"),
        }
    )
    result = harvest.processes(FakeRunner(), table)
    assert result["available"] is True, "a cycle must not take the step out of service"

    # The walk stops at the cycle, so it never reaches pid 10 and reports no harness. That is the
    # honest answer for this table rather than a degraded one: with 500's chain looping between 400
    # and 300, no ancestor of this process is the harness.
    assert result["harness_pid"] is None
    assert result["session_children"] == [], "no harness means no descendants to attribute to one"


def test_paths_written_into_files_that_do_not_exist_are_reported(tmp_path, monkeypatch):
    """A rule written into an always-loaded instructions file names a path on this machine.

    Confirmed 2026-08-29: a session deployed a `~/AGENTS.md` rule pointing at a script that did not
    exist in the installed skill, so a machine-wide rule instructed every future session to run a
    missing file. The checkout worked perfectly throughout, which is why nothing surfaced it.
    """
    # A fake HOME, because the paths this scans for are home-rooted ones — the shape an instructions
    # file actually names — and a test that wrote into the real home would leave a file per run.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # what `expanduser` reads on Windows
    (tmp_path / "here.py").write_text("x = 1\n")
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Edit",
                    "input": {"new_string": "run ~/here.py and ~/.agents/skills/demo/scripts/gone.py for the check"},
                }
            ],
        )
    ]
    assert harvest.promised_paths(entries) == ["~/.agents/skills/demo/scripts/gone.py"]


def test_a_path_invented_inside_a_scratch_file_is_a_fixture_not_an_instruction(tmp_path, monkeypatch):
    """Confirmed 2026-09-07: a harvest reported `~/work/ops/deploy.sh` as a machine-wide instruction
    pointing at a missing file. It was an invented path inside a throwaway `SKILL.md` written into
    the session's scratchpad, to audit a portability tool against a synthetic corpus — the same
    fixture case a test file already gets exempted for, since a scratch file instructs nobody."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    def wrote_into(path: str) -> list[dict[str, object]]:
        block = {
            "type": "tool_use",
            "id": "a",
            "name": "Write",
            "input": {"file_path": path, "content": "Run the deploy from ~/work/ops/deploy.sh"},
        }
        return [blocks_entry("assistant", [block])]

    scratch = "/tmp/claude-1000/session/scratchpad/other-user/skills/demo/SKILL.md"
    assert harvest.promised_paths(wrote_into(scratch)) == []

    # The control is a plain instructions file — and deliberately not `tmp_path`, which is itself
    # under the temp root and would be exempt for the right reason.
    assert harvest.promised_paths(wrote_into("/home/someone/repo/AGENTS.md")) == ["~/work/ops/deploy.sh"]

    # A repo's own `tmp/` is part of that repo; only the temp root and a scratch segment are exempt.
    assert harvest.promised_paths(wrote_into("/home/someone/repo/tmp/AGENTS.md")) == ["~/work/ops/deploy.sh"]


def test_a_path_edited_away_later_in_the_session_is_no_longer_reported(tmp_path):
    """The check reads the session's writes, so a line revised later is still in the transcript. The
    finding is "a future session is told to run this", which a revised file no longer says.
    Confirmed 2026-09-07: the run that added the scratch exemption spelled a missing path in full in
    a docstring, shortened it in the next edit, and the check went on reporting the first version.

    The predicate is exercised directly rather than through `promised_paths`, because every file
    pytest hands out lives under the temp root and is therefore exempt one rule earlier — which is
    the scratch exemption doing its job, not a gap.
    """
    doc = tmp_path / "notes.md"
    doc.write_text("the path was shortened away\n", encoding="utf-8")
    assert harvest._still_written("~/gone/script.py", str(doc)) is False

    doc.write_text("see ~/gone/script.py for the check\n", encoding="utf-8")
    assert harvest._still_written("~/gone/script.py", str(doc)) is True

    # A target that cannot be read is kept: an unreadable file is not evidence of absence.
    assert harvest._still_written("~/gone/script.py", str(tmp_path / "deleted.md")) is True
    assert harvest._still_written("~/gone/script.py", "") is True


def test_a_store_entry_without_provenance_is_found_one_level_down(tmp_path):
    """The buckets are not entries. Treating them as such reported the whole library as three
    unprovenanced entries — true of nothing, and it buries the one entry that really is missing."""
    library = tmp_path / "research"
    (library / "repos" / "github.com--a--b").mkdir(parents=True)
    (library / "repos" / "github.com--a--b" / "SOURCE.md").write_text("url: x\n")
    (library / "repos" / "github.com--c--d").mkdir(parents=True)
    state = harvest.store_state(FakeRunner(), "research", library, since=None)
    assert state["entries_without_provenance"] == ["repos/github.com--c--d"]


# --------------------------------------------------------------------------------------------
# attribution: a time window is not evidence of who did the thing
#
# Four checks in this file have made the same mistake, and the corpus now treats it as one defect
# with per-check mechanisms rather than four coincidences. `_correction_overlap` and the docker
# rows were fixed first; the two below are the same root in the library and the plans store.


def test_skills_state_resolves_its_own_since_and_says_which_it_used(tmp_path, monkeypatch, capsys):
    """`--since <session start>` was a placeholder with no stated source, so six harvests guessed
    it. One guessed ninety minutes early and got the right verdict anyway, which is how a
    placeholder survives: the wrong input produced the right answer. Too early fires the procedure's
    most expensive step on evidence that does not support it; too late drops a superseding commit
    out of the window and fails closed behind a clean report.

    The printed value is the other half. The harm was never the wrong window but that a wrong one
    was indistinguishable from a right one in the output, so nothing prompted a second look — and an
    operator passing the override can still pass it wrongly.
    """
    args = argparse.Namespace(since=None, session=None, job=None, expect=None)

    class FakeTranscript:
        started: str = "2026-09-07T21:03:53.947Z"
        path: Path = Path("/x/d6cb66aa-0a0b-4ed2-8219-786174c4904a.jsonl")

    monkeypatch.setattr(harvest, "resolve_transcript", lambda *a, **k: FakeTranscript())
    assert harvest._resolve_since(args) == ("2026-09-07T21:03:53.947Z", "transcript start (d6cb66aa)")

    # The override still wins, and now says how it sits against the real start. A supplied value is
    # never rejected — auditing a wider window is the flag's own second purpose — but a guess and a
    # deliberate audit are indistinguishable until the two instants are printed side by side, and a
    # guess is what all six instances were.
    early = argparse.Namespace(since="2026-09-07T19:33:53.947Z", session=None, job=None, expect=None)
    value, why = harvest._resolve_since(early)
    assert value == "2026-09-07T19:33:53.947Z"
    assert "90 min before this session's start" in why
    assert "wider" in why

    exact = argparse.Namespace(since=FakeTranscript.started, session=None, job=None, expect=None)
    assert "this session's own start" in harvest._resolve_since(exact)[1]

    late = argparse.Namespace(since="2026-09-07T21:33:53.947Z", session=None, job=None, expect=None)
    assert "30 min after" in harvest._resolve_since(late)[1]
    assert "narrower" in harvest._resolve_since(late)[1]

    # No transcript is the reader's ordinary case: the comparison still runs and only this half goes
    # unanswered. A silent None would have read as "nothing moved".
    def refuse(*_args, **_kwargs):
        raise harvest.HarvestError("no transcript")

    monkeypatch.setattr(harvest, "resolve_transcript", refuse)
    value, why = harvest._resolve_since(args)
    assert value is None
    assert "unavailable" in why


def test_a_library_entry_a_refresher_touched_is_not_this_sessions(tmp_path):
    """Confirmed 2026-09-07: a sweep reported **30** entries changed since session start, including
    `cpython`, `node`, `git` and a dotfile-manager cluster that was visibly another session's
    research topic. **Five were this session's** — it ran `library.py add` exactly five times — and
    its own transcript said which. A harvest reading that output would report touching thirty
    reference clones: specific, plausible, and wrong in the direction nobody re-checks."""
    library = tmp_path / "research"
    for name in ("github.com--seddonym--import-linter", "github.com--python--cpython", "github.com--twpayne--chezmoi"):
        (library / "repos" / name).mkdir(parents=True)
    entries = [bash_entry("python3 library.py add https://github.com/seddonym/import-linter")]

    state = harvest.store_state(FakeRunner(), "research", library, "2000-01-01T00:00:00Z", entries)
    assert state["changed_by_this_session"] == ["repos/github.com--seddonym--import-linter"]
    assert sorted(state["changed_by_something_else"]) == [
        "repos/github.com--python--cpython",
        "repos/github.com--twpayne--chezmoi",
    ]
    assert state["changed_attribution"] == "1 of 3 named in this session's own commands"


def test_an_entry_is_matched_by_the_url_that_made_it_and_not_only_its_directory_name():
    """The two spellings are not interchangeable and only one of them is the directory. A session
    that *reads* an entry names the directory; a session that *adds* one names a URL, and the entry
    name is derived from it afterwards. Matching the directory alone attributes every entry a
    session read and none it added — backwards, since an add is the event worth attributing and a
    read does not move an mtime at all."""
    assert harvest.entry_needles("github.com--seddonym--import-linter") == (
        "github.com--seddonym--import-linter",
        "seddonym/import-linter",
    )
    # A flat name has no owner/repo tail to derive, and must not grow a bogus one.
    assert harvest.entry_needles("skillsbench-2026.pdf") == ("skillsbench-2026.pdf",)


def test_searching_for_an_entrys_name_is_not_touching_it(tmp_path):
    """The lesson the docker check paid for on its first live run, applied before this one has a
    chance to repeat it: a quoted span is where a name appears without being used. Grepping the
    corpus for an entry name is the single most likely way it shows up in a session that never went
    near the library."""
    library = tmp_path / "research"
    (library / "repos" / "github.com--block--goose").mkdir(parents=True)
    entries = [bash_entry('rg -n "github.com--block--goose" ~/notes.md')]

    state = harvest.store_state(FakeRunner(), "research", library, "2000-01-01T00:00:00Z", entries)
    assert state["changed_by_this_session"] == []


def test_reading_a_clone_a_refresher_moved_is_not_touching_it(tmp_path):
    """The plans store's command door, one store along: a session credited with a commit it had only
    read the log of, 2026-09-12. A read names the entry and cannot move its mtime, so an `rg` over a
    clone some refresher updated in the same window is not this session's change."""
    library = tmp_path / "research"
    for name in ("github.com--block--goose", "github.com--a--b"):
        (library / "repos" / name).mkdir(parents=True)
    entries = [
        bash_entry(f"rg -n 'def main' {library}/repos/github.com--block--goose | head"),
        bash_entry(f"python3 library.py update {library}/repos/github.com--a--b"),
    ]

    state = harvest.store_state(FakeRunner(), "research", library, "2000-01-01T00:00:00Z", entries)
    assert state["changed_by_this_session"] == ["repos/github.com--a--b"]


def test_without_a_transcript_no_library_entry_is_claimed(tmp_path):
    """The same shape as the docker rows: the entries are still reported, and no claim is made about
    whose they are. An empty attributed list plus a count is the honest answer, not silence."""
    library = tmp_path / "research"
    (library / "repos" / "github.com--a--b").mkdir(parents=True)

    state = harvest.store_state(FakeRunner(), "research", library, "2000-01-01T00:00:00Z")
    assert state["changed_by_this_session"] == []
    assert state["changed_by_something_else"] == ["repos/github.com--a--b"]
    assert "no transcript" in state["changed_attribution"]


# --------------------------------------------------------------------------------------------
# the claims count
# --------------------------------------------------------------------------------------------


def test_green_claims_are_counted_against_the_masked_exits(tmp_path, monkeypatch):
    """The re-run settles whether the greens were true; it does not touch the fact that they were
    asserted. Confirmed 2026-09-02 on a ten-hour session at 28% `exit-masked` that had reported the
    gate green roughly fifteen times, every one from a `| tail`-ed run."""
    path = write_transcript(
        tmp_path / "s.jsonl",
        [
            user_entry("go"),
            blocks_entry(
                "assistant",
                [
                    {
                        "type": "tool_use",
                        "id": "a",
                        "name": "Bash",
                        "input": {"command": "inv quality.precommit 2>&1 | tail -30"},
                    }
                ],
            ),
            blocks_entry("assistant", [{"type": "text", "text": "Gate green, committing now."}]),
            blocks_entry("assistant", [{"type": "text", "text": "Nothing to report."}]),
        ],
    )
    args = harvest.build_parser().parse_args(["claims", "--session", str(path)])
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    payload = harvest.cmd_claims(args, FakeRunner())
    assert payload["exit_masked"] == 1
    assert [claim["line"] for claim in payload["green_claims"]] == ["Gate green, committing now."]


def test_the_printed_claims_advice_puts_the_gate_split_before_the_shell_check(tmp_path, monkeypatch, capsys):
    """The body says to read `audit.py`'s gate/listing split first, because a zero there needs no
    command at all; the printed block said "ask the shell first". Confirmed 2026-09-13: a harvest
    followed the body and ignored the block, which is the tell that the block was behind."""
    path = write_transcript(
        tmp_path / "s.jsonl",
        [
            bash_entry("inv quality.precommit 2>&1 | tail -30"),
            blocks_entry("assistant", [{"type": "text", "text": "Gate green, committing now."}]),
        ],
    )
    args = harvest.build_parser().parse_args(["claims", "--session", str(path)])
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    harvest.cmd_claims(args, FakeRunner())
    out = capsys.readouterr().out
    assert "Ask the shell first" not in out
    assert out.index("gate/listing split first") < out.index("setopt | rg pipefail")


def test_the_claims_ratio_counts_one_window_on_both_sides(tmp_path, monkeypatch, capsys):
    """Confirmed 2026-09-13: `claims --until <boundary>` printed `0 of 39` where `audit.py --until`
    on the same boundary counted 32 calls. The numerator honoured the cutoff and the denominator did
    not, so the harvest's own unpiped inspection calls diluted the rate."""
    path = write_transcript(
        tmp_path / "s.jsonl",
        [
            bash_entry("pytest 2>&1 | tail -3", "2026-09-13T14:00:00.000Z"),
            bash_entry("git status", "2026-09-13T14:05:00.000Z"),
            bash_entry("python3 harvest.py boundary", "2026-09-13T14:15:12.000Z"),
            bash_entry("python3 harvest.py sweep", "2026-09-13T14:16:00.000Z"),
        ],
    )
    args = harvest.build_parser().parse_args(["claims", "--session", str(path), "--until", "2026-09-13T14:15:12Z"])
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)

    payload = harvest.cmd_claims(args, FakeRunner())

    assert (payload["exit_masked"], payload["bash_calls"], payload["bash_calls_excluded_by_until"]) == (1, 2, 2)
    out = capsys.readouterr().out
    assert "# 1 of 2 Bash calls masked" in out
    assert "excluding 2 at or after 2026-09-13T14:15:12Z" in out


def test_a_bare_exit_code_needs_a_gate_shaped_subject_beside_it():
    """Measured 2026-09-08 over 1,201 transcripts: the subject-less alternation matched 303
    sentences, of which a gate-shaped subject keeps 158 and drops 145. The must-not-match cases are
    verbatim from that corpus; deleting the alternation outright was the cheaper fix and would have
    lost the must-match ones, which no other alternation reaches.

    A positive-only suite would pass for a matcher that matches everything, which is the failure
    already recorded for `--expect`'s quote handling.
    """
    must_match = [
        "- Gate re-run unpiped at harvest time: **exit 0, 402 tests**.",
        "Gate exits 0 unpiped — all five green claims hold.",
        "- Gate re-run **unpiped: exit 0**, 452 passed, ruff/dprint/basedpyright/zizmor clean.",
    ]
    must_not_match = [
        "`git fetch` run unpiped, **exit 0** — so the sync numbers are computed against a fresh ref.",
        "Dry-run against that exact file version: exit 0, zero private terms left.",
        "`gh run list --commit` matches only the full 40-char SHA, so a short SHA returns `[]` and exits 0.",
        # The 2026-09-08 session whose subject was a packaging probe: prose about a probe's result.
        "Non-editable fails silently — exit 0, found nothing.",
        "The plain install succeeds, exits 0, and silently finds nothing.",
    ]
    for sentence in must_match:
        assert harvest.GREEN_CLAIM_RE.search(sentence), sentence
    for sentence in must_not_match:
        assert not harvest.GREEN_CLAIM_RE.search(sentence), sentence


def test_a_green_with_a_test_count_is_a_claim_without_the_word_gate():
    """Confirmed 2026-09-26: one session said "gate green, 716 tests" and, fifty minutes later,
    "Green, 707 tests"; `claims` counted the first and missed the second. The number is what makes
    it a claim about a run, so the noun is optional and the count is not — which keeps prose about
    greenness out, since a matcher on "green" alone would score the plan that reported this."""
    must_match = [
        "Green, 707 tests. Now the reporter ...",
        "402 tests pass, basedpyright clean.",
        "All 12 tests passed on the retry.",
        "716 passed in 2.06s",
        "- pytest: 452 passed, 3 skipped",
        "Suite result: 30 passed.",
    ]
    must_not_match = [
        "The green path is the one most sessions take.",
        "which is why 3 passed arguments were dropped",
        "Green is the colour the badge uses for 5 tests' worth of history",
    ]
    for sentence in must_match:
        assert harvest.GREEN_CLAIM_RE.search(sentence), sentence
    for sentence in must_not_match:
        assert not harvest.GREEN_CLAIM_RE.search(sentence), sentence


def test_a_denial_that_a_gate_ran_is_still_counted_and_is_a_known_limit():
    """Pinned rather than fixed. The first alternation matches `no test anywhere runs the gate on a
    clean machine`, and general negation handling in a regex is not a one-line change. Recorded as a
    test so the next editor meets the known false positive instead of rediscovering it."""
    assert harvest.GREEN_CLAIM_RE.search("no test anywhere runs the gate on a clean machine")


def test_ci_greens_are_counted_apart_from_gate_greens():
    """The pattern had no term for CI at all, so `Both CI legs green` matched nothing — 329 sentences
    corpus-wide, more than the whole bare-exit-code alternation, and the phrasing this skill's own
    step 5 leads a harvest to write.

    Separate rather than folded in: a CI conclusion is read from `gh run list --json`, which has no
    exit code for a pipe to eat, so it is not usually resting on the filtered evidence the gate
    pairing is about. Folding 329 in would have inflated that paired number by half.
    """
    for sentence in ["Both CI legs green (CI 23s, Windows 1m42s).", "CI green including the final push."]:
        assert harvest.GREEN_CI_RE.search(sentence), sentence
        assert not harvest.GREEN_CLAIM_RE.search(sentence), f"still counted as a gate claim: {sentence}"


def test_a_claim_made_inside_a_question_is_still_a_claim():
    """An `AskUserQuestion`'s wording is a sentence the user reads and decides on.

    Confirmed 2026-09-02 on the session that wrote this: `claims` reported zero green-gate
    assertions while two of the three questions it had asked opened "Gate green, scan clean" — the
    same shape as the answer filter's miss, a user-facing population that is not the obvious entry
    type.
    """
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "q1",
                    "name": "AskUserQuestion",
                    "input": {"questions": [{"question": "Gate green, scan clean. Push?"}]},
                }
            ],
        ),
        blocks_entry("assistant", [{"type": "text", "text": "Nothing to report."}]),
    ]
    texts = [t for _, t in harvest.assistant_text(entries)]
    assert "Gate green, scan clean. Push?" in texts


# --------------------------------------------------------------------------------------------
# what an earlier harvest in this session already filed
# --------------------------------------------------------------------------------------------


def write_entry(path: str, timestamp: str = "2026-09-07T08:20:00.000Z", content: str = "") -> dict[str, object]:
    block = {"type": "tool_use", "id": "w", "name": "Write", "input": {"file_path": path, "content": content}}
    return blocks_entry("assistant", [block], timestamp=timestamp)


def edit_entry(path: str, old: str, new: str) -> dict[str, object]:
    block = {
        "type": "tool_use",
        "id": "e",
        "name": "Edit",
        "input": {"file_path": path, "old_string": old, "new_string": new},
    }
    return blocks_entry("assistant", [block])


def test_a_second_harvest_is_counted_from_the_transcript_not_remembered():
    """Confirmed 2026-09-07: a second harvest corrected the row the first had filed only because it
    happened to still be holding the memory of filing it. Whether a run is the second harvest of a
    session is a fact about the transcript — `boundary` is step 0 of every run, so the calls are
    there to be counted, and the skill's own `$H` alias is one of the spellings they arrive in."""
    entries = [
        bash_entry("python3 ~/.agents/skills/session-harvest/scripts/harvest.py boundary", "2026-09-07T08:12:00.000Z"),
        bash_entry("python3 $H boundary", "2026-09-07T10:55:00.000Z"),
        bash_entry("git status --short", "2026-09-07T10:56:00.000Z"),
    ]
    assert harvest.harvest_runs(entries) == ["2026-09-07T08:12:00.000Z", "2026-09-07T10:55:00.000Z"]
    assert harvest.harvest_runs(entries, until="2026-09-07T09:00:00Z") == ["2026-09-07T08:12:00.000Z"]


def test_a_filed_plan_carries_the_measurements_a_second_harvest_must_re_derive(tmp_path, monkeypatch):
    """The row this rule exists for: `n=211 chain=36% head/tail=20%`, filed 2h40m before the session
    ended and wrong by every rate once it had. The prose lines around it are not the finding, so a
    plan is reported by the lines carrying a number rather than in full."""
    store = tmp_path / "plans"
    (store / "power-user-linux-setup").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    plan = store / "power-user-linux-setup" / "2026-09-07-adherence-row.md"
    text = "# a row\n\nn=211  chain=36%  head/tail=20%  sed-n=0%(1)\n\nprose carrying no measurement\n"
    plan.write_text(text, encoding="utf-8")

    (row,) = harvest.filed_plans([write_entry(str(plan), content=text)], repos=[])
    assert row["exists"]
    assert row["measurements"] == ["n=211  chain=36%  head/tail=20%  sed-n=0%(1)"]
    assert row["measurements_unestablished"] == []


SHARED_PLAN = """\
# consumer transitions

- `inv quality.precommit` here: 0 errors, 0 warnings, 294 unit tests.
- one more measured row: 353 tests

## Appended

- the anchor line, 27 tests, which this session's edit repeated
"""


def test_a_number_in_a_plan_this_session_only_appended_to_is_not_its_to_re_derive(tmp_path, monkeypatch, capsys):
    """Confirmed 2026-09-12 in `repo-tasks`: one section appended to a plan several sessions share,
    and all five sampled lines were other sessions' numbers, days old — which step 8 sends a harvest
    to re-derive and edit. Reproduced 2026-09-13 by a one-paragraph edit in a second repo.

    The anchor line an Edit repeats is the file's existing text, so it is not the session's either."""
    store = tmp_path / "plans"
    (store / "repo-tasks").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    plan = store / "repo-tasks" / "2026-08-25-consumer-transitions.md"
    anchor = "- the anchor line, 27 tests, which this session's edit repeated"
    appended = "- this session's own sweep: 12 files changed, 3 errors"
    plan.write_text(SHARED_PLAN + appended + "\n", encoding="utf-8")

    (row,) = harvest.filed_plans([edit_entry(str(plan), anchor, f"{anchor}\n{appended}")], repos=[])
    assert row["measurements"] == [appended]
    assert row["measurements_unestablished"] == [
        "- `inv quality.precommit` here: 0 errors, 0 warnings, 294 unit tests.",
        "- one more measured row: 353 tests",
        anchor,
    ]

    harvest._print_filed({"plans_written": [row]})
    out = capsys.readouterr().out
    assert f"        {appended}" in out
    assert "(authorship unestablished) - one more measured row: 353 tests" in out


def test_a_missing_plan_row_names_no_cause(capsys):
    """A plan this session wrote and then retired is gone exactly the way an absorbed one is, and
    only the absorbed one owes a correction — so the row states the absence, not a diagnosis."""
    harvest._print_filed({"plans_written": [{"path": "plans/2026-09-06-landed.md", "exists": False}]})
    out = capsys.readouterr().out
    assert "plans/2026-09-06-landed.md  MISSING (cause not determined)" in out
    assert "absorbed" not in out.split("MISSING", 1)[1].splitlines()[0]
    assert "retired by this session needs nothing" in out


def test_no_missing_footer_when_every_plan_is_present(capsys):
    harvest._print_filed({"plans_written": [{"path": "plans/2026-09-06-live.md", "exists": True}]})
    assert "MISSING" not in capsys.readouterr().out


def test_a_line_the_gate_reflowed_is_still_the_line_this_session_wrote(tmp_path, monkeypatch):
    """dprint reflows prose and re-pads tables after every write, so the file never holds the bytes
    the Write sent. Whitespace is what moves, so whitespace is what the comparison ignores."""
    store = tmp_path / "plans"
    (store / "agent-skills").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    plan = store / "agent-skills" / "2026-09-13-a-measurement.md"
    sent = "Over seven days 109 of 110 commits had a receipt and 6 recorded rows resolved.\n\n| a | 3 calls |\n"
    plan.write_text(
        "Over seven days 109 of 110 commits had a receipt\nand 6 recorded rows resolved.\n\n| a   | 3 calls |\n",
        encoding="utf-8",
    )

    (row,) = harvest.filed_plans([write_entry(str(plan), content=sent)], repos=[])
    assert row["measurements_unestablished"] == []
    assert len(row["measurements"]) == 2


def test_the_sample_limit_does_not_hide_the_lines_this_session_wrote(tmp_path, monkeypatch):
    """A long shared plan's first number lines are its oldest. Sampling the whole file and then
    truncating printed only other sessions' rows, and never the one this session appended."""
    store = tmp_path / "plans"
    (store / "repo-tasks").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    plan = store / "repo-tasks" / "2026-08-25-long.md"
    old = "".join(f"- row {n}: {n} tests\n" for n in range(10))
    mine = "- appended today: 99 tests"
    plan.write_text(old + mine + "\n", encoding="utf-8")

    (row,) = harvest.filed_plans([edit_entry(str(plan), "- row 9: 9 tests", f"- row 9: 9 tests\n{mine}")], repos=[])
    assert row["measurements"] == [mine]
    assert len(row["measurements_unestablished"]) == 6


def test_a_markdown_file_outside_every_plan_root_is_not_a_filing(tmp_path, monkeypatch):
    """`plans` as a path component is not the test — the stores are named by config, and a repo may
    hold a `plans-archive/` that nothing files into."""
    monkeypatch.setenv("PLANS_HOME", str(tmp_path / "plans"))
    repo = tmp_path / "repo"
    (repo / "plans").mkdir(parents=True)
    entries = [
        write_entry(str(repo / "AGENTS.md")),
        write_entry(str(repo / "plans" / "2026-09-07-thing.md")),
    ]
    assert [Path(row["path"]).name for row in harvest.filed_plans(entries, repos=[repo])] == ["2026-09-07-thing.md"]


def result_entry(content: object, timestamp: str = "2026-09-07T12:00:00.000Z") -> dict[str, object]:
    block = {"type": "tool_result", "tool_use_id": "b", "content": content}
    return blocks_entry("user", [block], timestamp=timestamp)


def test_a_store_commit_from_another_session_is_not_this_sessions_to_correct(tmp_path, monkeypatch):
    """The store is shared, so a commit inside the window is not this session's by virtue of being
    there — the same trap the disk bullet's image rows fell into on 2026-09-06. Attribution is the
    commit's receipt in this session's own output, and an unattributable row is listed rather than
    dropped."""
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    log = (
        "\x1eaaaaaaaaaaaa\x1f2026-09-07T08:30:00+03:00\x1fT\x1fpower-user-linux-setup: an adherence row\n"
        "power-user-linux-setup/2026-09-07-adherence-row.md\n"
        "\x1ebbbbbbbbbbbb\x1f2026-09-07T09:02:00+03:00\x1fT\x1frepo-tasks: somebody else's plan\n"
        "repo-tasks/2026-09-07-other.md\n"
    )
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})
    entries = [result_entry("committed: aaaaaaaaaaaa in /home/u/plans\nmessage:   an adherence row")]

    state = harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [], entries)
    assert [c["subject"] for c in state["commits"] if c["this_session"]] == ["power-user-linux-setup: an adherence row"]
    assert [c["subject"] for c in state["commits"] if not c["this_session"]] == ["repo-tasks: somebody else's plan"]


def test_a_store_commit_that_only_deletes_is_still_this_sessions(tmp_path, monkeypatch):
    """The conservative reading's one false claim, and it fires on the commonest store commit there
    is. `plans.py absorb --apply` *moves* a plan out of the store, so the session writes nothing at
    the store path and no Write or Edit call names it.

    Confirmed 2026-09-07: a session absorbed three plans, committed each removal minutes later, and
    `filed` reported `0 commit(s) this session, 20 from elsewhere` with all three of its own among
    the strangers. Worse than a mislabelled row, because step 8 gives the label authority — "a row
    marked (another session) is reported, never edited" — so a harvest following the procedure
    correctly declines to correct its own filings. A deletion prints its receipt like any commit.
    """
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    log = (
        "\x1e719a495a2\x1f2026-09-07T15:08:41+03:00\x1fT\x1fpower-user-linux-setup: absorbed, take invoke-stubs\n"
        "power-user-linux-setup/2026-09-07-take-invoke-stubs-0-2-0.md\n"
    )
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})
    entries = [
        bash_entry("python3 plans.py commit plans/2026-09-07-take-invoke-stubs-0-2-0.md", "2026-09-07T12:08:30.000Z"),
        result_entry("[main 719a495] power-user-linux-setup: absorbed, take invoke-stubs\n 1 file changed"),
    ]

    # Written paths alone: the file was deleted, so nothing this session wrote names it.
    blind = harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [])
    assert [c["this_session"] for c in blind["commits"]] == [False]

    seeing = harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [], entries)
    (commit,) = seeing["commits"]
    assert commit["this_session"] is True
    assert commit["evidence"] == "reported making it"


def test_a_path_match_is_contact_with_a_file_not_authorship_of_a_commit(tmp_path, monkeypatch, capsys):
    """Both doors over-claimed, and each fix to one moved the error to the other. Every recorded
    shape, from the plan that merged them:

    - 2026-09-09: a filer credited with the owning repo's absorption of its plan — the write door.
    - 2026-09-10: a filer credited with another session's in-place correction of it — the write door
      again, with no deletion anywhere for a deletion-only rule to catch.
    - 2026-09-12: a session credited with an absorption it had only read the log of, running the
      confirmation step 8 prescribes — the command door, and the log's output carries the id.

    None of the three is this session's, and none is a stranger's the check can prove, so each is
    its own bucket. Only a receipt makes a commit this session's.
    """
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    filed = "github.com-personal/agent-skills/2026-09-09-checkout-v7.md"
    read = "github.com-personal/repo-tasks/2026-09-12-consumer-sweep.md"
    # Commit ids are hex, because a receipt is matched as one.
    log = (
        f"\x1eab50b0001\x1f2026-09-09T12:00:00+03:00\x1fT\x1fagent-skills: absorbed the checkout bump\n{filed}\n"
        f"\x1ec0cc00002\x1f2026-09-09T12:30:00+03:00\x1fT\x1fagent-skills: a second instance\n{filed}\n"
        f"\x1e4ead00003\x1f2026-09-09T13:00:00+03:00\x1fT\x1frepo-tasks: absorbed the consumer sweep\n{read}\n"
        f"\x1e5e1f00004\x1f2026-09-09T13:30:00+03:00\x1fT\x1fagent-skills: filed a finding\n{filed}\n"
    )
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})
    entries = [
        # Confirming the filing is still there, minutes before the owning repo's session absorbs it.
        bash_entry(f"git -C {store} cat-file -e HEAD:{read}", "2026-09-09T09:55:00.000Z"),
        bash_entry(f"git -C {store} log --oneline -1 -- {read}", "2026-09-09T10:05:00.000Z"),
        result_entry("4ead000 repo-tasks: absorbed the consumer sweep", "2026-09-09T10:05:01.000Z"),
        result_entry("committed: 5e1f00004 in /home/u/plans", "2026-09-09T10:30:01.000Z"),
    ]

    state = harvest.store_commits(runner, "plans", store, "2026-09-09T08:00:00+03:00", [store / filed], entries)
    by_sha = {c["sha"]: (c["this_session"], c["touched"], c["evidence"]) for c in state["commits"]}
    assert by_sha == {
        "ab50b0001": (False, True, "wrote a file in it"),
        "c0cc00002": (False, True, "wrote a file in it"),
        "4ead00003": (False, True, "named a file in a command"),
        "5e1f00004": (True, False, "reported making it"),
    }

    harvest._print_store_commits(state)
    out = capsys.readouterr().out
    assert "1 commit(s) this session, 3 of authorship unestablished, 0 not attributable" in out
    for sha in ("ab50b0001", "c0cc00002", "4ead00003"):
        assert f"(authorship unestablished) {sha}" in out


def test_a_store_swept_as_a_repo_prints_its_unpushed_commits_once(capsys):
    """The store is a git repository, so a session that touched it gets both sections: `== repo ==`
    for the git state and `== store ==` for what plan-docs means by it. Confirmed 2026-09-18: 32
    unpushed commits printed in both, about 64 lines of one report, and the length is set by the
    store's backlog rather than by the session. Both notes stay — each answers what the other does
    not — and the rows print in the section that timestamps them.

    A double-digit ahead-count is the fixture on purpose: the duplication is invisible at 0 and 1."""
    shas = [f"{i:04x}a0{i:02d}" for i in range(12)]
    payload = {
        "repos": [
            {
                "path": "/home/u/plans",
                "branch": "main",
                "upstream": "origin/main",
                "fetch": "ok",
                "dirty": [],
                "ahead": [
                    {"sha": sha, "when": "2026-09-18T10:00:00+03:00", "author": "T", "subject": f"filed a plan, {n}"}
                    for n, sha in enumerate(shas)
                ],
                "overlap": [],
                "notes": [],
            }
        ],
        "stores": [
            {
                "store": "plans",
                "path": "/home/u/plans",
                "present": True,
                "dirty": [],
                "unpushed": [f"{sha} T filed a plan, {n}" for n, sha in enumerate(shas)],
            }
        ],
    }

    harvest._print_sweep(payload)
    out = capsys.readouterr().out

    for sha in shas:
        assert out.count(sha) == 1, f"{sha} is printed by both sections"
    assert "unpushed: 12 commit(s), listed with their timestamps under == repo /home/u/plans ==" in out
    assert "costs off-machine backup and nothing else" in out, "the store's own note is not the duplicate"
    assert "parallel sessions the ahead-count is not necessarily this session's work" in out


def test_a_store_with_nothing_to_report_says_so_rather_than_printing_a_bare_heading(capsys):
    """Every other section of the sweep states what it found, so a heading with nothing under it
    reads as a check that did not run rather than as one that came back clean. Confirmed 2026-09-22
    on a store that was committed and pushed by the time the harvest ran."""
    harvest._print_store({"store": "plans", "path": "/home/u/plans", "present": True})
    out = capsys.readouterr().out

    assert "== store plans /home/u/plans ==" in out
    assert "clean: nothing uncommitted, nothing unpushed, no entry changed" in out


def test_a_store_that_was_not_swept_as_a_repo_still_lists_its_own_commits(capsys):
    """The count-and-point line is only sound while something else printed the rows. A sweep scoped
    with --only stores, or one whose session never touched the store's own tree, has no `== repo ==`
    section to point at, and dropping the rows there would lose them."""
    payload = {
        "repos": [],
        "stores": [
            {
                "store": "plans",
                "path": "/home/u/plans",
                "present": True,
                "dirty": [],
                "unpushed": ["ab50b00 T agent-skills: filed a finding"],
            }
        ],
    }

    harvest._print_sweep(payload)
    out = capsys.readouterr().out

    assert "unpushed: ab50b00 T agent-skills: filed a finding" in out
    assert "listed with their timestamps" not in out


def test_a_receipt_counts_only_as_tool_output_at_a_line_start():
    """A session that quotes a commit line in its own prose, or reads a log that prints the id bare,
    did not make that commit."""
    entries = [
        blocks_entry("assistant", [{"type": "text", "text": "[main 1111111] committed earlier"}]),
        result_entry("2222222 agent-skills: a subject, as git log --oneline prints it"),
        result_entry("see [main 3333333] inside a sentence"),
        result_entry("[main (root-commit) 4444444] first\n"),
        result_entry([{"type": "text", "text": "noise\ncommitted: 5555555555ab in /x"}]),
    ]
    assert harvest.commit_receipts(entries) == ["4444444", "5555555555ab"]


def test_naming_a_file_after_a_commit_does_not_make_that_commit_yours(tmp_path, monkeypatch):
    """The false positive reading argv opened, caught on this check's own first live run 2026-09-08.

    A parallel session committed to two plans at 00:18 and 00:20; this session ran
    `absorb --only <file>` on the same filenames at 00:45, and a bare name match called both commits
    its own. Both sessions legitimately name the same plan — a command simply cannot have caused a
    commit that already existed when it ran, which is the one thing that separates them.

    That is the exact error the write-path-only version was guarding against, arriving through the
    door opened to fix its opposite. So the two evidence sources are not interchangeable, and this
    one needs a timestamp the other never did.
    """
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    log = (
        "\x1etheirs001\x1f2026-09-08T00:18:16+03:00\x1fT\x1fagent-skills: the ratio moved inside its own window\n"
        "github.com-personal/agent-skills/2026-09-07-web-fetch.md\n"
        "\x1emine00001\x1f2026-09-08T00:45:32+03:00\x1fT\x1fagent-skills: absorbed seven\n"
        "github.com-personal/agent-skills/2026-09-07-web-fetch.md\n"
    )
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})
    entries = [bash_entry("plans.py absorb --apply --only 2026-09-07-web-fetch.md", "2026-09-07T21:45:00.000Z")]

    state = harvest.store_commits(runner, "plans", store, "2026-09-07T20:00:00+03:00", [], entries)
    touched = {c["sha"]: c["touched"] for c in state["commits"]}
    assert touched == {"theirs001": False, "mine00001": True}


def test_an_unattributable_commit_time_is_not_attributed(tmp_path, monkeypatch):
    """Where the ordering cannot be established the original conservative default stands, rather
    than the check falling back to the name match that has a known false positive."""
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    log = "\x1enodate001\x1fnot-a-timestamp\x1fT\x1fagent-skills: something\nagent-skills/2026-09-07-thing.md\n"
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})
    entries = [bash_entry("plans.py commit 2026-09-07-thing.md")]

    state = harvest.store_commits(runner, "plans", store, "2026-09-07T20:00:00+03:00", [], entries)
    assert [(c["this_session"], c["touched"]) for c in state["commits"]] == [(False, False)]


def test_an_unmatched_store_commit_is_not_asserted_to_be_another_sessions(tmp_path, monkeypatch, capsys):
    """The heading is the finding. Nothing here establishes that a commit belongs to somebody else —
    only that this session's transcript did not tie it to this one, and the two readings call for
    opposite next steps. A row the check simply cannot see must not read as a stranger's."""
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    log = "\x1eccccccccc\x1f2026-09-07T09:02:00+03:00\x1fT\x1frepo-tasks: somebody's plan\nrepo-tasks/x.md\n"
    runner = FakeRunner({f"git -C {store} log": (0, log, "")})

    state = harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [], [bash_entry("ls")])
    harvest._print_store_commits(state)
    out = capsys.readouterr().out
    assert "1 not attributable" in out
    assert "(not attributed)" in out
    assert "(another session)" not in out


def test_the_commit_separator_is_asked_for_rather_than_passed_as_a_byte(tmp_path, monkeypatch):
    """Found live 2026-09-07, on the first real run of this subcommand, and invisible to every test
    around it: a `--format` built with a real NUL raises `ValueError: embedded null byte` inside
    `subprocess.run`, which a fake runner never reaches. git's own `%xNN` escape keeps the argv
    ASCII and still separates the output."""
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    runner = FakeRunner()

    harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [])
    (call,) = runner.calls
    assert all("\x00" not in part for part in call), "an argv element may not contain a NUL"
    assert "--format=%x1e" in " ".join(call)


def test_a_store_git_log_that_fails_is_reported_rather_than_read_as_nothing_filed(tmp_path, monkeypatch):
    """The same failure the ahead-count had: a non-zero exit read as an empty answer says "the first
    harvest filed nothing", which is the one wrong answer this subcommand can give silently."""
    store = tmp_path / "plans"
    (store / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLANS_HOME", str(store))
    runner = FakeRunner({f"git -C {store} log": (128, "", "fatal: bad revision")})

    state = harvest.store_commits(runner, "plans", store, "2026-09-07T07:00:00+03:00", [])
    assert "commits" not in state
    assert state["error"] == "fatal: bad revision"


def test_a_reference_clone_is_not_a_repo_this_session_owns(tmp_path, monkeypatch):
    """One `cd` into a vendor clone to read its refspec pulled it into the sweep, which then
    fetched a stranger's remote and reported eight of that project's CI runs as findings."""
    library = tmp_path / "research"
    (library / "repos" / "github.com--astral-sh--uv").mkdir(parents=True)
    monkeypatch.setenv("RESEARCH_HOME", str(library))
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Bash",
                    "input": {"command": f"cd {library}/repos/github.com--astral-sh--uv && git status"},
                }
            ],
        )
    ]

    def runner(argv, cwd=None):
        if "rev-parse" in argv and "--show-toplevel" in argv:
            return harvest.Ran(tuple(argv), 0, str(argv[2]) + "\n", "")
        return harvest.Ran(tuple(argv), 0, "", "")

    swept = harvest._touched_repos(runner, [], entries)
    assert not any("github.com--astral-sh--uv" in str(p) for p in swept)


def test_a_reference_clone_outside_research_home_is_excluded_too(tmp_path):
    """The 2026-09-02 exclusion keyed on `$RESEARCH_HOME`, and the identical failure recurred one
    path away on 2026-09-08: a session probing text-only clones built a second library under its own
    scratchpad, and the sweep fetched that clone's remote, read its CI, and reported the untracked
    `SOURCE.md` as dirt — the same two symptoms in a tree the location test could not see.

    A library is recognisable by shape, so that is what is matched: a `SOURCE.md` under a `repos/`
    bucket. Both halves are needed — `SOURCE.md` alone would exclude any project shipping one, and a
    `repos/` parent alone would exclude a legitimate checkout in a directory of that name.
    """
    entry = tmp_path / "scratch" / "store" / "repos" / "github.com--intellectronica--ruler"
    entry.mkdir(parents=True)
    (entry / "SOURCE.md").write_text("url: x\n", encoding="utf-8")
    assert harvest._is_library_entry(entry)

    # Neither half on its own.
    plain = tmp_path / "repos" / "an-actual-project"
    plain.mkdir(parents=True)
    assert not harvest._is_library_entry(plain), "a checkout under a repos/ directory is still a checkout"

    sourced = tmp_path / "projects" / "ships-a-source-md"
    sourced.mkdir(parents=True)
    (sourced / "SOURCE.md").write_text("not a library entry\n", encoding="utf-8")
    assert not harvest._is_library_entry(sourced)


def test_a_skipped_loose_files_check_says_so_rather_than_vanishing(capsys):
    """Both transcript-derived checks used to disappear from the report when no transcript resolved —
    absent, not empty — so a reader scanning a full-looking report had no gap to notice. Confirmed
    2026-09-03 and again 2026-09-04, the second time by a harvest that read the whole sweep and found
    the hole only when re-reading the skill for a later step."""
    harvest._print_loose_files(harvest._sweep_loose_files(FakeRunner(), [], have_transcript=False))
    out = capsys.readouterr().out

    assert "== files written outside every repository ==" in out
    assert "== paths this session wrote into files that do not exist ==" in out
    assert out.count("skipped: no transcript") == 2
    assert "none" not in out, "a check that did not run must not read as a check that found nothing"


def test_a_loose_files_check_that_ran_and_found_nothing_says_none(capsys):
    """The other half of the same distinction, and the reason `skipped` is not enough on its own: a
    resolved run with no findings also printed nothing at all, so the two silences were identical."""
    harvest._print_loose_files(harvest._sweep_loose_files(FakeRunner(), [], have_transcript=True))
    out = capsys.readouterr().out

    assert out.count("none") == 2
    assert "skipped" not in out


def test_the_store_rows_name_their_own_cost_and_the_two_costs_differ(capsys):
    """A row that reports a state and stops leaves the reporting session to supply the reason, and it
    will — plausibly, out of the nearest thing it remembers. Confirmed 2026-09-08: the unpushed row
    said to report the count and not what it cost, and one harvest filled the gap with "no future
    session gets offered them by absorb", stated twice and unchallenged because it sounds like the
    mechanism working. It is false — absorb reads a local directory, and `plans.py` has no `fetch`,
    `pull` or `ls-remote` anywhere in it.

    The two rows also carry different urgency and must not be collapsed: a dirty store is a live
    same-machine concurrency cost, an unpushed one is an off-machine backup preference."""
    harvest._print_store(
        {
            "store": "plans",
            "path": "/home/x/plans",
            "present": True,
            "dirty": [" M a.md"],
            "unpushed": ["abc1234 Someone: a plan"],
        }
    )
    out = capsys.readouterr().out

    assert "add-a-new-file fallback" in out, "the dirty row's cost is concurrency, and it is the urgent one"
    assert "off-machine backup and nothing else" in out
    assert "Not a handoff failure" in out, "the wrong answer nearest to hand has to be refused by name"


def test_a_clean_store_is_not_lectured_about_costs_it_is_not_paying(capsys):
    """The consequence lines hang off findings, not off the section. A store with nothing to report
    printing two paragraphs about what unpushed commits would cost is the alarm-fatigue shape this
    corpus refuses everywhere else."""
    harvest._print_store({"store": "plans", "path": "/home/x/plans", "present": True, "dirty": [], "unpushed": []})
    out = capsys.readouterr().out

    assert "off-machine backup" not in out
    assert "add-a-new-file fallback" not in out


def test_a_sweep_with_no_transcript_declares_its_narrowed_repo_scope(monkeypatch, capsys):
    """The repo set comes from the transcript's own write paths and shell targets, so without one it
    collapses to the working directory. Measured 2026-09-03: one repo where the resolved run of the
    same session covered three, in a report that read as complete.

    **Both anchors have to go, and this test stripped only one until 2026-09-09.** `resolve_transcript`
    tries the job directory before the session id, so a suite run from inside a session that has a
    `$CLAUDE_JOB_DIR` resolved that session's real transcript and the sweep never degraded — the test
    then failed on a missing `repo_scope` key rather than on its own assertion. It passed everywhere
    the variable is unset, CI included, which is what let a one-line omission survive: every other
    test in this file that must not resolve a transcript already deletes the pair.
    """
    monkeypatch.delenv("CLAUDE_JOB_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    args = argparse.Namespace(
        boundary="2026-09-08T12:00:00+03:00",
        since=None,
        session=None,
        job=None,
        expect=None,
        repo=[],
        only=["paths"],
        no_fetch=True,
        checkout=None,
        json=False,
    )
    payload = harvest.cmd_sweep(args, FakeRunner())

    assert "with no transcript the session's repo set is unknown" in payload["repo_scope"]
    assert "# repos swept:" in capsys.readouterr().out


def test_children_are_unknown_rather_than_zero_when_no_harness_is_found(capsys):
    """`session_children` is derived by walking up to the harness process. When that walk finds no
    harness the set was never established, and a printed `0` is a measured zero's twin — the one
    thing this sweep exists not to produce."""
    harvest._print_processes(
        {"available": True, "harness_pid": None, "session_children": [], "watchers_and_servers": []}
    )
    out = capsys.readouterr().out

    assert "surviving children: unknown" in out
    assert "surviving children: 0" not in out


def test_a_path_inside_a_test_file_is_a_fixture_not_an_instruction():
    """The target is a fixture `SKILL.md` rather than a `test_*.py`, because since the always-loaded
    filter landed a `.py` is never read at all and this test would pass without exercising the
    exemption. What is left for it to prove is the real surviving case: an always-loaded *name*
    under a tests tree, which this repo's own fixtures create by the dozen."""
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Edit",
                    "input": {
                        "file_path": "/repo/tests/fixtures/demo/SKILL.md",
                        "new_string": "run `python3 ~/.agents/skills/demo/scripts/gone.py`",
                    },
                }
            ],
        )
    ]
    assert harvest.promised_paths(entries) == []


def test_only_a_file_an_agent_always_loads_can_carry_an_instruction():
    """Confirmed 2026-09-04: a harvest of a session whose subject was where each coding agent reads
    its instructions reported ten paths, all ten false positives — vendor directories for agents not
    installed here, and a docs table recording where three *other* agents look. Those never exist on
    this machine and the documentation is right anyway.

    The damage is not the noise. A section that has been all-false-positive once is one the next
    harvest skims, and the true positive looks identical in the list to a table entry.
    """
    described = blocks_entry(
        "assistant",
        [
            {
                "type": "tool_use",
                "id": "a",
                "name": "Edit",
                "input": {
                    "file_path": "/repo/docs/where-agents-read.md",
                    "new_string": "| opencode | `~/.config/opencode/AGENTS.md` |",
                },
            }
        ],
    )
    instructed = blocks_entry(
        "assistant",
        [
            {
                "type": "tool_use",
                "id": "b",
                "name": "Write",
                "input": {
                    "file_path": "/home/someone/AGENTS.md",
                    "content": "always run `python3 ~/.agents/skills/demo/scripts/gone.py` first",
                },
            }
        ],
    )
    assert harvest.promised_paths([described]) == []
    assert harvest.promised_paths([instructed]) == ["~/.agents/skills/demo/scripts/gone.py"]

    # A block naming no destination is kept. An unknown target demonstrates nothing about whether
    # the write was descriptive, and dropping it would be this group's own defect: a check that
    # quietly stops looking.
    unknown = blocks_entry(
        "assistant",
        [
            {
                "type": "tool_use",
                "id": "c",
                "name": "Edit",
                "input": {"new_string": "run `~/.agents/skills/demo/scripts/gone.py`"},
            }
        ],
    )
    assert harvest.promised_paths([unknown]) == ["~/.agents/skills/demo/scripts/gone.py"]


def test_one_missing_path_written_three_ways_is_one_row():
    """Three of the ten false positives were the same directory in three spellings, which is noise
    under every filter."""
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Write",
                    "input": {
                        "file_path": "/home/someone/AGENTS.md",
                        "content": (
                            "see ~/.agents/skills/demo/scripts/gone.py and "
                            f"{Path('~/.agents/skills/demo/scripts/gone.py').expanduser()} — both."
                        ),
                    },
                }
            ],
        )
    ]
    assert len(harvest.promised_paths(entries)) == 1


def test_each_differing_subdirectory_gets_its_own_consequence():
    assert "inert" in harvest.SUBDIR_CONSEQUENCE["references"]
    assert "earlier" in harvest.SUBDIR_CONSEQUENCE["scripts"]


# --------------------------------------------------------------------------------------------
# the shape of the tool itself
# --------------------------------------------------------------------------------------------


def test_the_live_runner_never_uses_a_shell(monkeypatch):
    """No shell means no pipe, and no pipe means the exit code is the command's own.

    Every documented failure in this area came from a filter reporting its own success, so this is
    checked rather than intended.
    """
    seen: dict[str, object] = {}

    class Result:
        returncode: int = 0
        stdout: str = ""
        stderr: str = ""

    def fake_run(args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr(harvest.subprocess, "run", fake_run)
    harvest.LiveRunner()(["git", "status"])
    assert seen["args"] == ["git", "status"]
    assert "shell" not in str(seen["kwargs"]), "shell=True would let a pipe eat the exit code"


def test_a_missing_binary_is_an_exit_code_not_a_crash(monkeypatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError(args[0])

    monkeypatch.setattr(harvest.subprocess, "run", fake_run)
    ran = harvest.LiveRunner()(["docker", "images"])
    assert ran.code == 127
    assert not ran.ok


def test_every_subcommand_accepts_the_shared_flags_after_its_name():
    """`harvest.py turns --json` has to work: declared only above the subcommand, argparse takes
    the flag only *before* it, which reads as the flag having been ignored."""
    for command in ("boundary", "transcript", "turns", "skills-state", "sweep", "claims", "filed"):
        args = harvest.build_parser().parse_args([command, "--json"])
        assert args.json is True
        assert args.command == command


# --------------------------------------------------------------------------------------------
# finding the skills checkout


def test_the_checkout_is_found_by_walking_up_from_the_script(tmp_path):
    repo = tmp_path / "anywhere" / "my-skills"
    (repo / "skills").mkdir(parents=True)
    (repo / ".git").mkdir()
    script = repo / "skills" / "session-harvest" / "scripts" / "harvest.py"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")

    assert harvest.find_checkout(None, start=script) == repo


def test_no_checkout_asks_rather_than_guessing_at_a_path(tmp_path):
    """This carried a hard-coded `~/projects/<owner>/<repo>` fallback until 2026-09-03 — the
    author's own checkout, in code shipped to strangers. It was guarded and so harmed nobody, which
    is exactly why it survived review: a path that only ever helps one machine is invisible
    everywhere else, right up until someone else's directory happens to match it."""
    stranded = tmp_path / "installed" / "session-harvest" / "scripts" / "harvest.py"
    stranded.parent.mkdir(parents=True)
    stranded.write_text("", encoding="utf-8")

    with pytest.raises(harvest.HarvestError, match="pass --checkout"):
        harvest.find_checkout(None, start=stranded)


def test_an_explicit_path_without_skills_is_rejected(tmp_path):
    with pytest.raises(harvest.HarvestError, match="no skills/ directory"):
        harvest.find_checkout(str(tmp_path))


def _source_repo(root: Path, *parts: str, skill: str = "session-harvest") -> Path:
    repo = root.joinpath(*parts)
    (repo / ".git").mkdir(parents=True)
    (repo / "skills" / skill).mkdir(parents=True)
    (repo / "skills" / skill / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n", encoding="utf-8")
    return repo


def _stranded_script(tmp_path: Path) -> Path:
    stranded = tmp_path / "installed" / "session-harvest" / "scripts" / "harvest.py"
    stranded.parent.mkdir(parents=True)
    stranded.write_text("", encoding="utf-8")
    return stranded


@pytest.mark.parametrize("layout", [("github.com-someone", "my-skills"), ("my-skills",)])
def test_the_checkout_is_detected_under_the_projects_root_whatever_its_layout(tmp_path, monkeypatch, layout):
    """The installed copy has no repo above it, so until 2026-09-05 the author's own machine could
    not answer step 0 from the install without `--checkout`. Detection walks the projects root
    `plan-docs` is configured with, so a `<root>/<host>/<repo>` tree and a flat `<root>/<repo>` one
    both resolve, and no script names either layout."""
    projects = tmp_path / "projects"
    repo = _source_repo(projects, *layout)
    _source_repo(projects, "other", "unrelated", skill="something-else")
    monkeypatch.setattr(harvest, "projects_root", lambda: projects)

    assert harvest.find_checkout(None, start=_stranded_script(tmp_path)) == repo


def test_two_checkouts_holding_the_skill_ask_rather_than_pick(tmp_path, monkeypatch):
    """A fork beside its upstream is a decision, and picking one silently would file fixes into a
    repo the user did not mean."""
    projects = tmp_path / "projects"
    _source_repo(projects, "upstream", "my-skills")
    _source_repo(projects, "fork", "my-skills")
    monkeypatch.setattr(harvest, "projects_root", lambda: projects)

    with pytest.raises(harvest.HarvestError, match=r"several checkouts.*pass --checkout"):
        harvest.find_checkout(None, start=_stranded_script(tmp_path))


def test_a_configured_checkout_beats_detection(tmp_path, monkeypatch):
    """Explicit argument, then the skill's own variable, then detection — the order every script
    in this corpus resolves a location in."""
    projects = tmp_path / "projects"
    _source_repo(projects, "detected")
    configured = _source_repo(tmp_path, "elsewhere")
    monkeypatch.setattr(harvest, "projects_root", lambda: projects)
    monkeypatch.setenv("SESSION_HARVEST_CHECKOUT", str(configured))

    assert harvest.find_checkout(None, start=_stranded_script(tmp_path)) == configured


def test_a_symlinked_repo_is_not_followed_by_detection(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    real = _source_repo(tmp_path, "outside", "my-skills")
    projects.mkdir()
    try:
        (projects / "linked").symlink_to(real)
    except OSError as exc:
        pytest.skip(f"this runner cannot create a symlink: {exc}")
    monkeypatch.setattr(harvest, "projects_root", lambda: projects)

    with pytest.raises(harvest.HarvestError, match="no skills checkout found"):
        harvest.find_checkout(None, start=_stranded_script(tmp_path))


def test_the_no_checkout_error_says_what_a_reader_does_with_skill_friction(tmp_path):
    with pytest.raises(harvest.HarvestError, match=r"report skill friction.*file nothing"):
        harvest.find_checkout(None, start=_stranded_script(tmp_path))


# --------------------------------------------------------------------------------------------
# plan-docs' locations are read as configuration, never re-derived


def test_the_stores_and_projects_root_come_from_plan_docs_config(tmp_path, monkeypatch):
    """`harvest.py` used to carry its own `~/plans` and `~/plans-sensitive` defaults beside the ones
    in `plans.py` — two copies of a default that had to agree, with nothing keeping them in step.
    The contract is the config file and the variables, which both skills read."""
    config = tmp_path / "plan-docs.toml"
    config.write_text(
        f'projects_root = "{(tmp_path / "code").as_posix()}"\nstore = "{(tmp_path / "ideas").as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(config))
    monkeypatch.delenv("PLANS_HOME", raising=False)
    monkeypatch.delenv("PLANS_SENSITIVE_HOME", raising=False)

    stores = dict(harvest._stores())

    assert REAL_PROJECTS_ROOT() == tmp_path / "code"
    assert stores["plans"] == tmp_path / "ideas"
    assert stores["plans-sensitive"] == tmp_path / "ideas-sensitive", "the sensitive tier derives from the store"


def test_the_variable_beats_the_config_for_a_store(tmp_path, monkeypatch):
    config = tmp_path / "plan-docs.toml"
    config.write_text(f'store = "{(tmp_path / "ideas").as_posix()}"\n', encoding="utf-8")
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(config))
    monkeypatch.setenv("PLANS_HOME", str(tmp_path / "pinned"))
    monkeypatch.delenv("PLANS_SENSITIVE_HOME", raising=False)

    assert dict(harvest._stores())["plans"] == tmp_path / "pinned"


def test_a_missing_or_broken_config_falls_back_to_the_documented_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(tmp_path / "nowhere.toml"))
    monkeypatch.delenv("PLANS_HOME", raising=False)
    monkeypatch.delenv("PLANS_SENSITIVE_HOME", raising=False)
    assert dict(harvest._stores())["plans"] == Path.home() / "plans"

    broken = tmp_path / "broken.toml"
    broken.write_text("store = [unclosed\n", encoding="utf-8")
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(broken))
    assert harvest.plan_docs_config() == {}


def test_a_worktree_checkout_is_named_as_one(tmp_path):
    """Nothing else in this subcommand's output distinguishes a worktree: it is clean, it is ahead
    by commits, and push-then-re-install succeeds at every step while installing nothing, because
    `skills add <owner>/<repo>` takes the remote's default branch.

    The marker is written by hand because this suite forbids shelling out. That the shape is what
    git really produces is proved against a live `git worktree add` in `test_plan_store.py` —
    `test_linked_worktree_of_names_the_checkout_it_belongs_to`, which covers the same parser.
    """
    repo = tmp_path / "my-skills"
    (repo / ".git" / "worktrees" / "feat").mkdir(parents=True)
    tree = tmp_path / "my-skills.worktrees" / "feat"  # VS Code's default layout
    tree.mkdir(parents=True)
    (tree / ".git").write_text(f"gitdir: {repo / '.git' / 'worktrees' / 'feat'}\n", encoding="utf-8")

    assert harvest.worktree_main(tree) == repo
    assert harvest.worktree_main(repo) is None  # `.git` is a directory here, not a file


def test_a_submodule_is_not_mistaken_for_a_worktree(tmp_path):
    """Both put a `.git` FILE where a checkout has a directory; only one names `worktrees`."""
    fake = tmp_path / "vendor" / "sub"
    fake.mkdir(parents=True)
    (fake / ".git").write_text("gitdir: ../../.git/modules/vendor/sub\n", encoding="utf-8")

    assert harvest.worktree_main(fake) is None


# --------------------------------------------------------------------------------------------
# the transcript directory is named the way the harness names it


def test_by_content_scopes_to_the_slug_the_harness_writes(tmp_path, monkeypatch):
    """Claude Code slugs a project path as `[^a-zA-Z0-9]` -> `-` (read from the binary
    2026-09-05). This lookup replaced only `/` and `.`, so a cwd holding an underscore looked in a
    directory that does not exist and fell back to searching every project on the machine — where a
    marker distinctive within one project is rarely distinctive at all."""
    projects = tmp_path / "projects"
    own = projects / "-home-u-projects-my-repo"
    other = projects / "-home-u-projects-other"
    own.mkdir(parents=True)
    other.mkdir(parents=True)
    (own / "a.jsonl").write_text("ran the marker here\n", encoding="utf-8")
    (other / "b.jsonl").write_text("ran the marker here\n", encoding="utf-8")
    monkeypatch.setattr(harvest, "PROJECTS_DIR", projects)

    hits = harvest._by_content("the marker", Path("/home/u/projects/my_repo"))

    assert hits == [own / "a.jsonl"]


def test_a_path_past_the_slug_cap_searches_machine_wide(tmp_path, monkeypatch):
    """Past 200 characters the harness appends a hash this script cannot recompute, so the scoped
    directory cannot be named and the honest fallback is the whole store, not a guessed name."""
    projects = tmp_path / "projects"
    (projects / "-deep").mkdir(parents=True)
    (projects / "-deep" / "a.jsonl").write_text("the marker\n", encoding="utf-8")
    monkeypatch.setattr(harvest, "PROJECTS_DIR", projects)
    deep = Path("/home/u/" + "/".join(["directory"] * 30))

    assert harvest.project_slug(deep) == ""
    assert harvest._by_content("the marker", deep) == [projects / "-deep" / "a.jsonl"]


def test_expect_selects_a_command_containing_double_quotes(tmp_path, monkeypatch):
    """The transcript stores a command as a JSON string, so `"` is `\\"` on disk and a raw substring
    search misses the exact command a caller is most likely to paste. Confirmed 2026-09-05:
    `--expect 'git tag -l "SINGLE-LINE-TEST"'` reported `no transcript resolved` against a
    transcript holding that command three times, while the vaguer `git tag -l` resolved it — the
    more specific needle being the one that fails.
    """
    projects = tmp_path / "projects"
    own = projects / "-home-u-projects-my-repo"
    own.mkdir(parents=True)
    command = 'git tag -l "SINGLE-LINE-TEST"'
    write_transcript(own / "a.jsonl", [user_entry(f"ran {command} here")])
    monkeypatch.setattr(harvest, "PROJECTS_DIR", projects)

    raw = (own / "a.jsonl").read_text(encoding="utf-8")
    assert command not in raw, "the escaping this test is about"
    assert harvest._by_content(command, Path("/home/u/projects/my-repo")) == [own / "a.jsonl"]


def test_expect_still_says_not_found_for_a_quoted_command_that_is_absent():
    """The matcher must not become a matcher for anything: a quote-carrying needle that is genuinely
    absent still has to miss, or the self-check note becomes decoration."""
    stored = json.dumps({"cmd": 'git tag -l "PRESENT"'})
    assert harvest._contains('git tag -l "PRESENT"', stored)
    assert not harvest._contains('git tag -l "ABSENT"', stored)


# --------------------------------------------------------------------------------------------
# the sweep's Windows arms, against the documented output shapes
#
# Nothing in this repo has run on Windows; these pin the parsers to the column layouts the tools
# document, and the Windows CI leg is what turns them from reasoned into measured.


def test_windows_process_table_keeps_the_sweeps_own_pipeline_out(monkeypatch):
    """`Win32_Process` has no process groups, and `processes()` uses the group to leave this
    call's own pipeline out of the survivors. So the table gives every process its own group
    except this script's direct children, which join its group — the PowerShell reading the table
    is one of them, and reporting it would be the sweep measuring itself."""
    monkeypatch.setattr(harvest, "WINDOWS", True)
    monkeypatch.setattr(harvest.os, "getpid", lambda: 500)
    listing = (
        "10\t1\t9999\tC:\\Users\\u\\claude.exe --session\n"
        "500\t10\t0\tpython harvest.py sweep\n"
        "501\t500\t0\tpowershell -NoProfile -Command ...\n"
        "600\t10\t36000\tcmd /c until gh run view\n"
        "700\t1\t12\t\n"  # a process with no command line, which CIM does report
        "garbage line\n"
    )
    runner = FakeRunner({"powershell": (0, listing, "")})

    table = harvest.process_table(runner)
    result = harvest.processes(runner, table)

    assert runner.calls[0][:2] == ["powershell", "-NoProfile"], "the POSIX ps must not be tried"
    assert table[501].pgid == 500
    assert table[600].pgid == 600
    assert table[700].args == ""
    assert result["harness_pid"] == 10
    assert [row["pid"] for row in result["session_children"]] == [600]


def test_windows_netstat_listeners_use_the_same_shape_as_ss(tmp_path, monkeypatch):
    """`netstat -ano` prints the pid alone, so the name comes from the process table; only TCP rows
    in LISTENING state are listeners, and a UDP row has no state column at all. The served
    directory still resolves through `--directory`, which is the only route on Windows since there
    is no `/proc` to read a cwd from."""
    monkeypatch.setattr(harvest, "WINDOWS", True)
    served = tmp_path / "repo"
    (served / ".git").mkdir(parents=True)
    (served / ".env").write_text("SECRET=1\n")
    listing = (
        "\nActive Connections\n\n"
        "  Proto  Local Address          Foreign Address        State           PID\n"
        "  TCP    0.0.0.0:8765           0.0.0.0:0              LISTENING       42\n"
        "  TCP    [::1]:9000             [::]:0                 LISTENING       43\n"
        "  TCP    127.0.0.1:52000        127.0.0.1:443          ESTABLISHED     42\n"
        "  UDP    0.0.0.0:5353           *:*                                    44\n"
    )
    runner = FakeRunner({"netstat -ano": (0, listing, "")})
    table = {
        42: harvest.Process(1, 42, "", 100, f"C:\\Python\\python.exe -m http.server 8765 --directory {served}"),
        43: harvest.Process(1, 43, "", 50, "node.exe server.js"),
    }

    result = harvest.sockets(runner, table)

    assert [x["local"] for x in result["listeners"]] == ["0.0.0.0:8765", "[::1]:9000"]
    exposed, loopback = result["listeners"]
    assert exposed["exposed"] is True
    assert loopback["exposed"] is False
    assert exposed["processes"][0]["name"] == "python.exe"
    assert exposed["processes"][0]["readable_secrets"] == [".env"]
    served_keys = {"serves", "is_repo_root", "readable_secrets"}
    assert [(p["name"], p["pid"]) for p in loopback["processes"]] == [("node.exe", 43)]
    assert not served_keys & set(loopback["processes"][0]), "nothing is claimed about what it serves"
    assert result["over_a_repo"] == [exposed]


def test_a_windows_machine_without_powershell_output_reports_unavailable(monkeypatch):
    monkeypatch.setattr(harvest, "WINDOWS", True)
    result = harvest.processes(FakeRunner({"powershell": (1, "", "not recognized")}))
    assert result["available"] is False
    assert "Win32_Process" in result["why"]


def test_inline_script_calls_quantify_the_subprocess_seam():
    """The seam is stated on every transcript-derived count, so a reader who has met it once reads
    the next occurrence as boilerplate. A number cannot be read that way.

    Confirmed 2026-09-26: a harvest whose plan edits all went through `python3 - <<PY` heredocs
    listed one of the two plan files that session wrote, and marked the lines it had written in the
    one it did list as authorship-unestablished. The generic limit printed correctly, directly
    under a list it had silently halved.
    """
    entries = [
        bash_entry("python3 - <<'PY'\nPath('x').write_text('y')\nPY"),
        bash_entry('python3 -c "import sys; print(sys.version)"'),
        bash_entry("cat <<-EOF > out.txt\nhello\nEOF"),
        bash_entry("git status --short"),
        bash_entry("rg -n 'heredoc' README.md"),
    ]
    assert harvest.inline_script_calls(entries) == 3

    assert harvest.inline_script_calls([bash_entry("ls -la")]) == 0
