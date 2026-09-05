"""`session-bash-audit`'s pattern detectors, against hand-written commands.

The skill's own rule: test the regex against hand-written cases before trusting its count. Every
case here is a shape a real transcript produced, and the first group is the one that flattered the
number — a `|` inside a quoted regex alternation counted as a pipe to `head`/`tail`.
"""

# Loaded by path because `skills/` holds no importable package, so every symbol is Any by
# construction — same suppression as test_harvest.py, for the same structural reason.
# pyright: reportAny=false

import importlib.util
import sys
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
