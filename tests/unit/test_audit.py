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
