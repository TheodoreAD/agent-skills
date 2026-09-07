"""The permission replay: which Bash calls would have prompted, and why.

Approved prompts leave no trace in a transcript, so this engine is the only way the prompt rate is
ever measured — and until 2026-09-07 it had **no tests at all**. It did not appear in the coverage
report either, because nothing imported it: 240 lines of rule matching whose output `SKILL.md` tells
the reader to feed into an allowlist change.

Every case below pins either a documented approximation from the module docstring or a live probe
recorded in `references/research.md`, so a test that starts failing is a claim that stopped holding
rather than a detail that moved.
"""

# The module under test is a standalone CLI script that imports its sibling by bare name, so the
# scripts directory goes on the path and both resolve the way they do at the command line.
# pyright: reportAny=false, reportExplicitAny=false

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "skills" / "session-bash-audit" / "scripts"
# `prompts.py` imports `audit` by bare name, exactly as it resolves at the command line, so the
# scripts directory goes on the path and both are then imported dynamically — a static import would
# be one the type checker cannot resolve, since `skills/` holds no importable package.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

prompts = importlib.import_module("prompts")
audit = importlib.import_module("audit")

PROJECT = "-tmp-work"


def call(cmd: str, project: str = PROJECT):
    """A transcript call carrying only the fields the replay reads: the command and its project."""
    return audit.Call(
        cmd=cmd, model="m", project=project, session="s", subagent=False, timestamp="", error=False, result=""
    )


def rules(allow: list[str] | None = None, ask: list[str] | None = None, scope: list[str] | None = None):
    return (prompts._rule_regexes(allow or []), prompts._rule_regexes(ask or []), scope or [])


# --------------------------------------------------------------------------------------------
# rule matching — the prefix form is the one every allowlist entry uses


def test_a_prefix_rule_matches_on_a_word_boundary_not_a_substring():
    """`Bash(git status:*)` is a prefix rule: it covers `git status --short` and must not cover
    `git statusx`, which is a different command sharing seven letters."""
    matched = prompts._rule_regexes(["Bash(git status:*)"])
    assert prompts._rule_match("git status --short", matched) == "Bash(git status:*)"
    assert prompts._rule_match("git status", matched) == "Bash(git status:*)"
    assert prompts._rule_match("git statusx", matched) is None
    assert prompts._rule_match("git stat", matched) is None


def test_a_rule_without_the_prefix_marker_is_an_exact_match():
    matched = prompts._rule_regexes(["Bash(pwd)"])
    assert prompts._rule_match("pwd", matched) == "Bash(pwd)"
    assert prompts._rule_match("pwd /tmp", matched) is None


def test_a_star_inside_a_rule_body_is_a_wildcard():
    matched = prompts._rule_regexes(["Bash(git * --dry-run)"])
    assert prompts._rule_match("git push --dry-run", matched) == "Bash(git * --dry-run)"


def test_a_non_bash_rule_is_not_a_bash_rule():
    """`Read(...)` grants reach this engine through `_read_roots`, never as a command matcher."""
    assert prompts._rule_regexes(["Read(//home/x/**)", "WebFetch(domain:example.com)"]) == []


def test_read_grants_become_directory_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    roots = prompts._read_roots(["Read(//srv/data/**)", "Read(~/notes/**)", "Bash(ls:*)"])
    assert "/srv/data" in roots
    assert str(tmp_path / "notes") in roots


# --------------------------------------------------------------------------------------------
# wrappers and env prefixes — what the engine strips before matching anything


@pytest.mark.parametrize(
    ("piece", "expected"),
    [
        ("timeout 30 pytest -q", "pytest -q"),
        ("nice -n 5 cargo build", "cargo build"),
        ("command git status", "git status"),
        ("pytest -q", "pytest -q"),
    ],
)
def test_a_wrapper_and_its_own_flags_are_stripped(piece, expected):
    assert prompts.strip_wrappers(piece)[0] == expected


def test_a_leading_assignment_is_reported_because_it_defeats_every_prefix_rule():
    """A rule matches on the literal command prefix, so `PATH=... inv x` matches nothing that
    `inv x` would — which is why the engine tracks the assignment rather than dropping it."""
    stripped, env = prompts.strip_wrappers("PATH=/opt/bin:$PATH inv quality.check")
    assert (stripped, env) == ("inv quality.check", True)
    assert prompts.strip_wrappers("inv quality.check")[1] is False


def test_an_env_prefix_prompts_even_when_the_bare_command_is_allowed():
    allowed = rules(allow=["Bash(inv quality.check:*)"])
    assert prompts.classify_piece("inv quality.check", call("x"), False, False, allowed) is None
    assert prompts.classify_piece("FOO=1 inv quality.check", call("x"), False, False, allowed) == "env-prefix:inv"


# --------------------------------------------------------------------------------------------
# scope — the half that decides whether a *read* prompts


def test_a_relative_path_is_always_in_scope():
    assert prompts.in_scope("skills/x/SKILL.md", PROJECT, [])


@pytest.mark.parametrize("path", ["$HOME/x", "/tmp/*/x"])
def test_an_unresolvable_or_globbed_path_is_not_claimed_to_be_in_scope(path):
    """The docstring states both as approximations that count as prompting; a guess in the other
    direction would under-report the prompt rate, which is the number this exists to produce."""
    assert not prompts.in_scope(path, PROJECT, [])


def test_a_path_under_the_project_is_in_scope_and_a_sibling_is_not():
    assert prompts.in_scope("/tmp/work/src/a.py", PROJECT, [])
    assert not prompts.in_scope("/tmp/other/a.py", PROJECT, [])


def test_an_additional_directory_puts_a_path_back_in_scope():
    assert prompts.in_scope("/srv/data/a.csv", PROJECT, ["/srv/data"])


def test_a_quoted_pattern_containing_a_slash_is_not_a_path():
    """`rg '^## Open / to re-measure' file` — tokenizing on whitespace reads the pattern as a path
    and reports a prompt that never happened."""
    assert prompts._path_args("rg '^## Open / to re-measure' notes.md") == []
    assert prompts._path_args("rg x /etc/hosts") == ["/etc/hosts"]


def test_a_glob_is_judged_by_its_directory():
    assert prompts._path_args("ls /srv/data/*.csv") == ["/srv/data"]


def test_an_allowed_read_still_prompts_on_an_out_of_scope_path():
    """Probed live 2026-08-25: `rg -c x ~/.claude/settings.json` prompted with `Bash(rg:*)`
    allowed. An allow rule does not exempt a read outside the working directory."""
    allowed = rules(allow=["Bash(rg:*)"])
    assert prompts.classify_piece("rg -c x src/a.py", call("x"), False, False, allowed) is None
    reason = prompts.classify_piece("rg -c x /etc/hosts", call("x"), False, False, allowed)
    assert reason == "read-outscope:rg /etc/hosts"


# --------------------------------------------------------------------------------------------
# precedence — the order the engine replays


def test_an_ask_rule_beats_an_allow_rule():
    both = rules(allow=["Bash(git push:*)"], ask=["Bash(git push:*)"])
    assert prompts.classify_piece("git push", call("x"), False, False, both) == "ask:Bash(git push:*)"


def test_shell_keywords_and_control_words_are_not_commands():
    for piece in ("done", "else", "true", "export FOO=1", "{"):
        assert prompts.classify_piece(piece, call("x"), False, False, rules()) is None


def test_a_builtin_read_only_verb_needs_no_rule():
    assert prompts.classify_piece("ls -la src", call("x"), False, False, rules()) is None


def test_a_read_only_git_verb_is_free_and_anything_else_is_not():
    assert prompts.classify_piece("git status --short", call("x"), False, False, rules()) is None
    assert prompts.classify_piece("git push", call("x"), False, False, rules()) == "unmatched:git push"


def test_a_cd_anywhere_in_the_chain_takes_the_free_git_verb_away():
    """The engine cannot know where a chained `cd` left the shell, so a `git status` after one is
    no longer a statement about the project directory."""
    free = prompts.prompting_reasons(call("git status"), rules())
    assert free == []
    chained = prompts.prompting_reasons(call("cd /elsewhere && git status"), rules())
    assert chained == ["cd+git", "unmatched:git status"]


def test_an_in_scope_filesystem_command_is_granted_by_the_mode_and_an_out_of_scope_one_is_not():
    assert prompts.classify_piece("mkdir -p src/new", call("x"), False, False, rules()) is None
    assert prompts.classify_piece("rm /etc/hosts", call("x"), False, False, rules()) == "mode-outscope:rm"


def test_a_redirect_prompts_unless_it_is_dev_null_or_in_scope():
    assert prompts.classify_piece("pytest -q > out.log", call("x"), False, False, rules()) == "unmatched:pytest"
    assert prompts.classify_piece("pytest -q > /dev/null", call("x"), False, False, rules()) == "unmatched:pytest"
    reason = prompts.classify_piece("pytest -q > /etc/out.log", call("x"), False, False, rules())
    assert reason == "redirect:/etc/out.log"


def test_an_unmatched_command_is_labelled_with_its_subcommand_where_that_is_the_useful_half():
    """`inv`, `uv`, `gh` and friends carry their meaning in the second word, so the ranked reason
    list has to keep it — `unmatched:inv` across twenty tasks names nothing to allowlist."""
    inv = prompts.classify_piece("inv quality.check", call("x"), False, False, rules())
    assert inv == "unmatched:inv quality.check"
    assert prompts.classify_piece("cargo build --release", call("x"), False, False, rules()) == "unmatched:cargo"


def test_every_piece_of_a_chain_is_replayed_in_order():
    found = prompts.prompting_reasons(call("ls src && cargo build && rm /etc/x"), rules())
    assert found == ["unmatched:cargo", "mode-outscope:rm"], "the free `ls` contributes nothing"


def test_rules_are_read_from_the_settings_file_the_harness_owns(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(
        '{"permissions": {"allow": ["Bash(ls:*)", "Read(//srv/**)"], "ask": ["Bash(git push:*)"],'
        ' "additionalDirectories": ["/scratch"]}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(prompts, "SETTINGS", settings)

    allow, ask, scope = prompts.load_rules()

    assert prompts._rule_match("ls -la", allow) == "Bash(ls:*)"
    assert prompts._rule_match("git push", ask) == "Bash(git push:*)"
    assert scope == ["/scratch", "/srv"], "additionalDirectories and Read grants are one scope list"
