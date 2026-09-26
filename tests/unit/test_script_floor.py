"""The shipped scripts' contract with a stranger's ambient `python3`: 3.11, standard library only.

Nothing resolves these scripts' dependencies or interpreter — a consumer runs them by path — so
`requires-python` enforces nothing for them, and this suite is the only check. It means something
only while the dev venv sits at the floor, which `.python-version` pins.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted(ROOT.glob("skills/*/scripts/*.py"))
IDS = [f"{path.parent.parent.name}/{path.name}" for path in SCRIPTS]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_there_are_scripts_to_check():
    assert len(SCRIPTS) >= 10, "the glob found almost nothing, so every test below would pass vacuously"


@pytest.mark.parametrize("script", SCRIPTS, ids=IDS)
def test_a_shipped_script_imports_only_the_standard_library(script: Path):
    """A third-party import works on the author's machine and fails mid-task on a stranger's."""
    siblings = {path.stem for path in script.parent.glob("*.py")}
    foreign = _imported_modules(script) - set(sys.stdlib_module_names) - siblings - {"__future__"}
    assert not foreign, f"{script.relative_to(ROOT)} imports {sorted(foreign)}, which a consumer may not have"


@pytest.mark.parametrize("script", SCRIPTS, ids=IDS)
def test_a_shipped_script_starts_on_this_interpreter(script: Path):
    """Run for real rather than compiled: an import of a 3.12-only name compiles fine on 3.11."""
    ran = subprocess.run(
        [sys.executable, str(script), "--help"], capture_output=True, text=True, timeout=60, check=False
    )
    assert ran.returncode == 0, ran.stderr


def _below_the_floor() -> str | None:
    """A 3.10 interpreter, if this machine has one. uv's managed copies are where it usually is."""
    found = shutil.which("python3.10")
    if found:
        return found
    uv = shutil.which("uv")
    if uv is None:
        return None
    ran = subprocess.run(
        [uv, "python", "find", "--no-project", "3.10"], capture_output=True, text=True, timeout=60, check=False
    )
    return ran.stdout.strip() or None if ran.returncode == 0 else None


@pytest.mark.parametrize("script", SCRIPTS, ids=IDS)
def test_below_the_floor_a_script_says_so_rather_than_raising(script: Path):
    """Measured 2026-09-18: on 3.10 two scripts died with `ModuleNotFoundError: No module named
    'tomllib'` — a stdlib module named, the interpreter not. A consumer on Ubuntu 22.04 gets exactly
    that mid-task. Either the script works there or it exits with a sentence naming 3.11.

    Skipped where no 3.10 exists, which includes CI; the dev machine is where it runs."""
    python = _below_the_floor()
    if python is None:
        pytest.skip("no Python 3.10 on this machine")
    ran = subprocess.run([python, str(script), "--help"], capture_output=True, text=True, timeout=60, check=False)
    assert "Traceback" not in ran.stderr, ran.stderr
    assert ran.returncode == 0 or "needs Python 3.11 or newer" in ran.stderr, ran.stderr
