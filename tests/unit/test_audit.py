"""`session-bash-audit`'s pattern detectors, against hand-written commands.

The skill's own rule: test the regex against hand-written cases before trusting its count. Every
case here is a shape a real transcript produced, and the first group is the one that flattered the
number — a `|` inside a quoted regex alternation counted as a pipe to `head`/`tail`.
"""

# Loaded by path because `skills/` holds no importable package, so every symbol is Any by
# construction — same suppression as test_harvest.py, for the same structural reason.
# pyright: reportAny=false

import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

AUDIT_PY = Path(__file__).resolve().parents[2] / "skills" / "session-bash-audit" / "scripts" / "audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("audit_script", AUDIT_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_script"] = module
    spec.loader.exec_module(module)
    return module


audit = _load()


def tags_of(cmd: str) -> set[str]:
    return {name for name, (predicate, _why) in audit.PATTERNS.items() if predicate(cmd)}


@pytest.mark.parametrize(
    "cmd",
    [
        'rg -n "^#|head|tail|pipe" contributing/global-agents-md.md',
        "rg -n 'head|tail|READ_ONLY' scripts/prompts.py",
        'rg -n "tail|head" ~/.claude/settings.json',
        'git commit -m "plans: a piped gate | tail is not a rule"',
    ],
)
def test_a_pipe_inside_quotes_is_not_a_pipe(cmd):
    """Confirmed 2026-09-05: a session measured at 4% `head/tail` had three hits, every one an `rg`
    pattern naming the very tags it was being counted as. The real rate was 0%."""
    assert "head/tail" not in tags_of(cmd)
    assert "exit-masked" not in tags_of(cmd)
    assert "search|head" not in tags_of(cmd)


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("inv quality.precommit 2>&1 | tail -3", {"head/tail", "exit-masked"}),
        ("git log --oneline | head -5", {"head/tail"}),
        ("rg -n foo . | head -20", {"head/tail", "search|head"}),
        ('echo "a | tail" | tail -1', {"head/tail"}),
        ("pytest -q > log 2>&1; rg -n FAILED log | head -3", {"head/tail", "redirect-then-filter", "search|head"}),
    ],
)
def test_a_real_pipe_still_counts(cmd, expected):
    assert expected <= tags_of(cmd)


def test_a_heredoc_body_is_not_a_command():
    cmd = "python3 - <<'PY'\nprint('x | head')\nPY"
    assert "head/tail" not in tags_of(cmd)
    assert "heredoc" in tags_of(cmd)


def test_strip_quoted_keeps_the_shell_shape():
    assert audit.strip_quoted('rg -n "a|b" f | tail -1') == 'rg -n "" f | tail -1'
    assert audit.strip_quoted("echo 'it | is' > f") == 'echo "" > f'


# --------------------------------------------------------------------------------------------
# a heredoc hides its body, not the commands after it


def test_the_gate_run_after_a_heredoc_is_still_a_command():
    """`strip_heredoc` cut at the marker and returned everything before it, so a patch heredoc
    followed by the gate handed the table `python3 -` and nothing else. Measured 2026-09-06 over 7
    days: 1,267 tag hits lost across 30 sessions, 437 of them `head/tail` and 381 `exit-masked`, and
    per session the correction reached +12pp. One understated session is sample 6 of the published
    adherence corpus — 27% recorded against a real 37%."""
    cmd = "python3 - <<'PY'\nprint('x')\nPY\ninv quality.precommit 2>&1 | tail -30"
    tags = tags_of(cmd)
    assert "exit-masked" in tags
    assert "head/tail" in tags
    assert "heredoc" in tags


def test_two_heredocs_in_one_call_both_close():
    cmd = "cat > a <<'EOF'\nbody | head -1\nEOF\ncat > b <<'EOF'\nmore | head -1\nEOF\nsed -n '1,5p' a"
    tags = tags_of(cmd)
    assert "sed-n" in tags, "the command after the second body is still a command"
    assert "head/tail" not in tags, "neither body is"


def test_an_unterminated_heredoc_still_cuts_to_the_end():
    """Nothing after an unclosed body can be told from body, so the old behaviour is right there —
    a transcript entry truncated mid-write is the case that produces one."""
    assert audit.strip_heredoc("python3 - <<'PY'\nprint('x')\ninv precommit | tail -3") == "python3 - "


def test_a_here_string_is_not_a_heredoc():
    """`<<<` feeds one line to stdin and has no terminator, so reading it as a heredoc cut the
    command there and tagged `heredoc`. The only instance in the 7 days to 2026-09-06 was a `<<<`
    inside a quoted `rg` pattern, which quoting does not protect: `strip_heredoc` runs first."""
    cmd = "rg -o '<<< finished=[^>]*>>>' log | tail -1"
    assert "heredoc" not in tags_of(cmd)
    assert "head/tail" in tags_of(cmd), "and the rest of the command survives"


def test_a_dash_heredoc_closes_on_an_indented_terminator():
    """`<<-WORD` allows leading whitespace on the closing line and plain `<<WORD` does not, which is
    the shell's own rule. The strict form for plain `<<` is deliberate: resuming inside a body whose
    text happens to be the delimiter puts body text back into the table."""
    assert "head/tail" in tags_of("cat > f <<-EOF\n\tbody\n\tEOF\nrg x f | head -3")
    assert "head/tail" not in tags_of("cat > f <<EOF\n  EOF\nstill body | head -3\nEOF")


# --------------------------------------------------------------------------------------------
# a counter keyed on a bare tool name must not match its own prose


@pytest.mark.parametrize(
    ("cmd", "row"),
    [
        ('git commit -m "audit: rg -rn ate the bundle and rewrote every match"', "rg-replace"),
        ("python3 plans.py commit -m '2026-09-02-rg-replace-flag-used-twice.md'", "rg-replace"),
        ('git commit -m "prefer fd; find . -name x needs -not -path excludes"', "find-not-fd"),
        ("audit.py --days 30 --samples 0 | rg 'find-not-fd|grep-r-not-rg|find-exempt'", "find-not-fd"),
        ("audit.py --days 30 | rg 'grep-r-not-rg|grep/find'", "grep-r-not-rg"),
    ],
)
def test_a_tool_name_inside_quotes_is_not_an_invocation(cmd, row):
    """The bias is one-directional and lands where it hurts: the count rises exactly when someone is
    working on the audit, writing about the anti-pattern, or reading the report — which is exactly
    when the number is read. Measured over the seven days to 2026-09-05: `rg-replace` 39 tagged / 32
    real (~8% over), `find-not-fd` 41 / 37 (~10% over), every false positive from prose. The last
    two rows are the sharpest case, a session grepping the audit's own output for these row names
    and being counted as violating the rule the row measures — the `|` inside the quoted alternation
    read as a segment boundary, and `find-exempt` after it read as a `find`.
    """
    assert row not in tags_of(cmd)


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        ("rg -rn pattern src/", {"rg-replace"}),
        ("rg -ril needle .", {"rg-replace"}),
        ("cd ../other-repo && rg -rn pattern .", {"rg-replace"}),
        ("git log --oneline | rg -rn pattern", {"rg-replace"}),
        ("rg --replace X pattern src/", {"rg-replace"}),
        ("find . -name '*.py'", {"find-not-fd"}),
        ("grep -rn needle src/", {"grep-r-not-rg"}),
    ],
)
def test_a_real_invocation_still_counts(cmd, expected):
    """Anchoring must not cost the finding. `cd <path> && rg` is the one chain shape ~/AGENTS.md
    blesses and did occur in the corpus; it needs no special case, because `&&` is already one of
    the segment boundaries."""
    assert expected <= tags_of(cmd)


def test_printf_is_the_find_only_capability_the_exempt_row_exists_for():
    """`-printf` was missing from both rows' flag lists, so a call using find's own formatter was
    tagged a violation and never as exempt. The two rows are read as a ratio, so one call in the
    wrong row moves the number twice."""
    tags = tags_of("find tests -name 'test_*.py' -printf '%f\\n'")
    assert "find-exempt" in tags
    assert "find-not-fd" not in tags


# --------------------------------------------------------------------------------------------
# the own-repo tags compare against the slug the harness actually writes


@pytest.mark.parametrize(
    ("target", "project"),
    [
        ("/home/u/projects/my_repo", "-home-u-projects-my-repo"),
        ("/home/u/projects/a.b/c+d", "-home-u-projects-a-b-c-d"),
        ("/home/u/projects/x", "-home-u-projects-x"),
        ("C:\\Users\\u\\projects\\x", "C--Users-u-projects-x"),
    ],
)
def test_the_slug_replaces_every_non_alphanumeric(target, project):
    """Read from the Claude Code binary 2026-09-05: `replace(/[^a-zA-Z0-9]/g, "-")`. The tags
    replaced only `/` and `.`, so an underscore, a space or a Windows separator slugged to a
    directory the harness never writes and both own-repo rows reported zero — on every platform,
    not only the Windows one the skill had been warning about."""
    assert audit.slug_matches(target, project)
    assert audit._cd_tag(f"cd {target} && ls", project) == {"cd-own-repo"}
    assert audit._git_c_tag(f"git -C {target} status", project) == {"git-C-own-repo"}


def test_a_different_directory_is_still_not_the_own_repo():
    assert audit._cd_tag("cd /home/u/projects/other && ls", "-home-u-projects-my-repo") == {"cd-other"}
    assert audit._git_c_tag("git -C /home/u/projects/other log", "-home-u-projects-my-repo") == set()


def test_a_slug_past_the_cap_matches_on_its_prefix():
    """Past 200 characters the harness cuts the slug and appends a hash nobody can recompute, so
    equality has to become a prefix match — otherwise a deep path silently never matches."""
    deep = "/home/u/" + "/".join(["directory"] * 30)
    slug = audit.project_slug(deep)
    assert len(slug) > audit.SLUG_CAP
    assert audit.slug_matches(deep, slug[: audit.SLUG_CAP] + "-abc123")
    assert not audit.slug_matches(deep, slug[: audit.SLUG_CAP - 1] + "-abc123")


def test_short_project_no_longer_knows_the_authors_root(monkeypatch):
    monkeypatch.setattr(audit.Path, "home", classmethod(lambda cls: Path("/home/u")))
    assert audit.short_project("-home-u-projects-some-root-repo-tasks") == "some-root-repo-tasks"
    assert audit.short_project("-home-u-projects-flat-repo") == "flat-repo"
    assert audit.short_project("-home-u-elsewhere-thing") == "elsewhere-thing"
    assert audit.short_project("-tmp-scratch-x") == "-tmp-scratch-x"


# --------------------------------------------------------------------------------------------
# a baseline is irreplaceable, so writing one may not destroy one


@pytest.fixture
def _no_git(monkeypatch):
    """`instrument_commit` shells out; every test here is about the writer, not about git."""
    monkeypatch.setattr(audit, "instrument_commit", lambda: "abc1234")


@pytest.mark.usefixtures("_no_git")
def test_writing_a_baseline_refuses_to_destroy_one(tmp_path):
    """The default path is UTC-dated, so a run at 02:13 local wrote the name the previous
    afternoon's baseline already had, and destroyed it with no prompt, no backup and no mention that
    anything was there — the only line of output being `baseline written to …`, last in a report
    several hundred lines long. A baseline measures a corpus that has since moved on, so it cannot
    be re-taken; every other writer in this corpus that can overwrite asks or diffs first.
    """
    path = tmp_path / "2026-09-04.json"
    audit.save_baseline([], path, days=4.0, note="pipefail live")

    with pytest.raises(SystemExit) as refusal:
        audit.save_baseline([], path, days=7.0, note="a later run")

    assert "refusing to overwrite" in str(refusal.value)
    assert "pipefail live" in str(refusal.value), "the refusal has to name what it would have destroyed"
    assert json.loads(path.read_text(encoding="utf-8"))["note"] == "pipefail live"


@pytest.mark.usefixtures("_no_git")
def test_force_is_how_a_baseline_is_destroyed_on_purpose(tmp_path):
    path = tmp_path / "2026-09-04.json"
    audit.save_baseline([], path, days=4.0, note="first")
    audit.save_baseline([], path, days=4.0, note="second", force=True)
    assert json.loads(path.read_text(encoding="utf-8"))["note"] == "second"


@pytest.mark.usefixtures("_no_git")
def test_a_baseline_records_the_instrument_that_wrote_it(tmp_path):
    """Two baselines a day apart were compared as though one instrument made both, while a pattern
    commit had landed 22 minutes before the second was written. A `--compare` straddling such a
    commit attributes a pattern change to the change being measured, in the direction that flatters
    it, and nothing in the JSON let a reader notice."""
    path = tmp_path / "b.json"
    audit.save_baseline([], path, days=4.0, note="")
    assert json.loads(path.read_text(encoding="utf-8"))["instrument"] == "abc1234"


@pytest.mark.usefixtures("_no_git")
def test_saved_carries_the_local_moment_not_a_bare_utc_date(tmp_path):
    """The corpus is local-time sessions, the plans are local-dated, and the user's day is local, so
    a bare UTC date in `saved` claimed the wrong one: both files on the machine that produced this
    finding recorded 2026-09-04, one of them written on the 5th. The filename stays UTC-dated, so an
    artefact already on disk keeps its scheme."""
    path = tmp_path / "b.json"
    audit.save_baseline([], path, days=4.0, note="")
    saved = json.loads(path.read_text(encoding="utf-8"))["saved"]
    assert datetime.fromisoformat(saved).tzinfo is not None


def test_no_checkout_means_no_instrument_rather_than_a_wrong_one(monkeypatch, tmp_path):
    """The installed copy is not in a checkout, and `None` there is the useful answer — a SHA
    borrowed from whatever repo the file happened to sit under would be worse than none."""

    def untracked(argv, **kwargs):
        assert argv[0] == "git"
        return subprocess.CompletedProcess(argv, 1, "", "not in a git dir")

    monkeypatch.setattr(audit.subprocess, "run", untracked)
    assert audit.instrument_commit() is None


# --------------------------------------------------------------------------------------------
# the session view: one row per line, count first, and every row printed


def _call(cmd: str) -> object:
    call = audit.Call(
        cmd=cmd, model="m", project="p", session="s", subagent=False, timestamp="", error=False, result=""
    )
    audit.classify(call)
    return call


def test_the_session_view_prints_every_row_including_the_zeros(capsys):
    """A session could commit `rg-replace` and read an adherence line that never mentioned it, in
    either direction — `RATE_COLUMNS` was built for the per-model corpus table and the session view
    inherited it. A row nobody prints cannot be read as zero; a row printed as `0` can."""
    audit._print_session_rows([_call("ls")])
    out = capsys.readouterr().out
    for row in ("rg-replace", "find-not-fd", "grep-r-not-rg", "find-exempt"):
        assert f"{row:24}     0" in out, f"{row} has to print its zero"
    for row in audit.EXPECTATIONS:
        assert row in out, "a verdict without a printed number behind it is the defect this fixes"


def test_a_single_instance_prints_as_a_count_not_as_zero_percent(capsys):
    """Rates print as `:.0%`, so at a median session of 247 calls one instance is 0.40% and rounds
    away. Measured 2026-09-06 over 67 sessions: of the 30 with an `rg-replace` hit, 13 would print
    `0%`. The count is what the reader acts on; the rate stays because `--compare` judges it."""
    calls = [_call("rg -rn pattern src")] + [_call("ls") for _ in range(299)]
    audit._print_session_rows(calls)
    row = next(line for line in capsys.readouterr().out.splitlines() if "rg-replace" in line)
    assert "1" in row.split()[1], "the count says one"
    assert row.split()[2] == "0%", "and the rate still rounds to zero, which is why the count is there"


def test_the_masked_row_separates_a_gate_from_a_listing(capsys):
    """The raw `exit-masked` rate ranks sessions backwards on consequence: masking forty listings has
    no reader, masking one gate run and saying "green" does. A count rather than a listing of the
    calls — at corpus scale the gate half is 50% of the masked population, non-empty for 55 of 67
    sessions, median 14 distinct shapes."""
    calls = [
        _call("inv quality.precommit 2>&1 | tail -30"),
        _call("pytest tests/unit 2>&1 | tail -3"),
        _call("plans.py list 2>&1 | head -60"),
    ]
    assert len(audit.masked_gate(calls)) == 2
    audit._print_session_rows(calls)
    row = next(line for line in capsys.readouterr().out.splitlines() if "exit-masked" in line)
    assert "2 wrapped a gate, 1 a listing" in row


@pytest.mark.parametrize(
    ("cmd", "bundled"),
    [
        ("rg -rn cd src", True),
        ("rg -ril todo .", True),
        ("rg -nr pat f", True),
        ("rg -o -r '' 'v[0-9]+' notes.md", False),
        ("rg --replace '' -o pat f", False),
        ("rg -il todo .", False),
    ],
)
def test_only_a_bundled_r_is_the_accident(cmd, bundled):
    """A flag group of two or more letters containing `r` means `-r` took the rest of the group as
    its replacement string, and nobody wants that. A lone `-r` is the deliberate `rg -o -r ''`
    extraction idiom — 13 of the parent row's 86 hits over the 30 days to 2026-09-06 — which is why
    `EXPECTATIONS` scores the bundle and leaves `rg-replace` itself unjudged."""
    tags = tags_of(cmd)
    assert ("rg-replace-bundle" in tags) is bundled
    assert "rg-replace" in tags or not bundled


def test_the_bundle_is_the_row_that_carries_the_expectation():
    assert audit.EXPECTATIONS["rg-replace-bundle"] == "zero"
    assert "rg-replace" not in audit.EXPECTATIONS, (
        "the parent row counts deliberate --replace too, so zero there is a verdict nobody can satisfy"
    )


def test_every_judged_row_is_a_row_that_gets_computed():
    """`EXPECTATIONS` judged `find-not-fd` while `rates()` computed `RATE_COLUMNS` plus two, and that
    row was in neither. `compare` read it as absent from both runs and skipped it as "a pattern added
    since this baseline was saved" — every time, silently, permanently. A judged row that is never
    computed is the same defect as a computed row that is never displayed."""
    computed = audit.rates([_call("ls")])
    assert not [tag for tag in audit.EXPECTATIONS if tag not in computed]


def test_the_replace_row_names_the_spelling_that_produced_it():
    """`-rn` loses line numbers and rewrites the matched text; `-ril` turns a case-insensitive
    file-list search into a case-sensitive line search. One count cannot say which is happening, and
    a lone `-r` is the deliberate extraction idiom — 13 of 86 hits over the 30 days to 2026-09-06,
    which is why the row cannot be scored as one number."""
    flags = audit.rg_replace_flags(
        [
            _call("rg -rn cd src"),
            _call("rg -ril todo ."),
            _call("rg -o -r '' 'v[0-9]+' notes.md"),
        ]
    )
    assert flags == {"-rn": 1, "-ril": 1, "-r": 1}


# --------------------------------------------------------------------------------------------
# `--session` is the mode a harvest runs, so a flag it accepts has to work there or refuse


def _transcript(tmp_path: Path, calls: list[tuple[str, str]]) -> Path:
    """A minimal transcript: one assistant message per (timestamp, command)."""
    path = tmp_path / "0f0e0d0c-1111-2222-3333-444455556666.jsonl"
    lines = [
        json.dumps(
            {
                "timestamp": stamp,
                "message": {
                    "model": "claude-opus-5",
                    "content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": cmd}}],
                },
            }
        )
        for i, (stamp, cmd) in enumerate(calls)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run(monkeypatch, argv: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["audit.py", *argv])
    audit.main()


def test_session_mode_honours_the_json_dump_it_used_to_swallow(monkeypatch, tmp_path):
    """`--session` returned before the tail of `main()`, so `argparse` accepted `--json`, the report
    printed, no file was written and nothing said so. Found 2026-09-06 by a harvest, whose adherence
    step is always a `--session` run — the machine-readable form was unavailable in exactly the mode
    that wanted it, and a caller after the tags had to re-derive them by hand.

    The dump is the `--until`-filtered set the report was about, not the whole transcript: a run
    measuring itself excludes its own sweep, and a JSON disagreeing with the rates beside it would
    be worse than none.
    """
    transcript = _transcript(
        tmp_path,
        [
            ("2026-09-06T10:00:00+03:00", "rg -n pattern src && git status"),
            ("2026-09-06T12:00:00+03:00", "python3 audit.py --session x"),
        ],
    )
    out = tmp_path / "calls.json"

    _run(monkeypatch, ["--session", str(transcript), "--until", "2026-09-06T11:00:00+03:00", "--json", str(out)])

    dumped = json.loads(out.read_text(encoding="utf-8"))
    assert [c["cmd"] for c in dumped] == ["rg -n pattern src && git status"]
    assert "chain2" in dumped[0]["tags"], "the tags are the reason a caller asks for the dump"


def test_save_baseline_in_session_mode_refuses_rather_than_being_skipped(monkeypatch, tmp_path, capsys):
    """The same early return also swallowed `--save-baseline`. Skipping it is right on the merits —
    one session's rates are not a corpus baseline — but silence made a flag that does nothing look
    like a flag that worked, which this corpus holds to be worse than an error."""
    transcript = _transcript(tmp_path, [("2026-09-06T10:00:00+03:00", "ls")])

    with pytest.raises(SystemExit) as refusal:
        _run(monkeypatch, ["--session", str(transcript), "--save-baseline", str(tmp_path / "b.json")])

    assert refusal.value.code == 2
    assert "not a baseline" in capsys.readouterr().err
    assert not (tmp_path / "b.json").exists()
