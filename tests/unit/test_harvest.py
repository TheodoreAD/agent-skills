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

import importlib.util
import json
import sys
from pathlib import Path

import pytest

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


@pytest.fixture(autouse=True)
def _no_subprocess(monkeypatch):
    """The requirement, enforced: every command in these tests comes from the fake runner."""

    def refuse(*args, **kwargs):
        raise AssertionError(f"a test shelled out: {args!r} {kwargs!r}")

    monkeypatch.setattr(harvest.subprocess, "run", refuse)


class FakeRunner:
    """Canned command output, keyed by the start of the command line.

    Keys are matched as prefixes of `" ".join(argv)`, longest first, so a test states only the part
    of a command it cares about. An unmatched command returns exit 0 and no output rather than
    raising: most of the script's commands are irrelevant to any one test, and a fake that demands
    every one of them be declared makes the tests about the fake.
    """

    def __init__(self, responses: dict[str, tuple[int, str, str]] | None = None):
        self.responses: dict[str, tuple[int, str, str]] = responses or {}
        self.calls: list[list[str]] = []

    def __call__(self, argv, cwd=None):
        args = [str(a) for a in argv]
        self.calls.append(args)
        line = " ".join(args)
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
    assert [str(p) for p in harvest.written_paths(entries)] == ["/repo/a.py", "/repo/c.md"]


def test_shell_targets_read_cd_and_git_c():
    entries = [
        blocks_entry(
            "assistant",
            [
                {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "cd /other/repo && git status"}},
                {"type": "tool_use", "id": "b", "name": "Bash", "input": {"command": "git -C /third/repo log -1"}},
            ],
        )
    ]
    assert sorted(str(p) for p in harvest.shell_targets(entries)) == ["/other/repo", "/third/repo"]


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


def test_a_skill_that_moved_after_the_session_began_is_named(tmp_path):
    checkout = tmp_path / "checkout"
    installed_root = tmp_path / "installed"
    make_skill(checkout, "demo", "same\n")
    make_installed(installed_root, "demo", "same\n")
    runner = FakeRunner(
        {
            f"git -C {checkout} log -1 --format=%cI": (0, "2026-09-02T15:00:00+03:00\n", ""),
            f"git -C {checkout} log --since=": (0, "abc123 Me a later edit\n", ""),
        }
    )
    state = harvest.skill_state(runner, "demo", checkout, installed_root, since="2026-09-02T09:00:00Z")
    assert state["moved_since_session_start"] is True
    assert "re-read" in state["verdict"]


# --------------------------------------------------------------------------------------------
# the sweep's parsers
# --------------------------------------------------------------------------------------------


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


def test_a_machine_without_ps_reports_unavailable_rather_than_no_survivors():
    """`ps -eo` is POSIX and does not exist on Windows. An empty table cannot mean "nothing is
    running" — `ps` cannot omit the process reading it — so zero survivors there would be a clean
    bill of health from a step that never ran, which is the failure this sweep exists to prevent.
    The sockets step already answers this way; the processes step did not until 2026-09-04."""
    result = harvest.processes(FakeRunner({"ps": (127, "", "ps: command not found")}))
    assert result["available"] is False
    assert "session_children" not in result, "an absent measurement must not read as a measured zero"


def test_paths_written_into_files_that_do_not_exist_are_reported(tmp_path, monkeypatch):
    """A rule written into an always-loaded instructions file names a path on this machine.

    Confirmed 2026-08-29: a session deployed a `~/AGENTS.md` rule pointing at a script that did not
    exist in the installed skill, so a machine-wide rule instructed every future session to run a
    missing file. The checkout worked perfectly throughout, which is why nothing surfaced it.
    """
    # A fake HOME, because the paths this scans for are home-rooted ones — the shape an instructions
    # file actually names — and a test that wrote into the real home would leave a file per run.
    monkeypatch.setenv("HOME", str(tmp_path))
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


def test_a_path_inside_a_test_file_is_a_fixture_not_an_instruction():
    entries = [
        blocks_entry(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Edit",
                    "input": {
                        "file_path": "/repo/tests/unit/test_harvest.py",
                        "new_string": "assert x == '~/.agents/skills/demo/scripts/gone.py'",
                    },
                }
            ],
        )
    ]
    assert harvest.promised_paths(entries) == []


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
    for command in ("boundary", "transcript", "turns", "skills-state", "sweep", "claims"):
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
