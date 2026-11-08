"""Where a skill's script puts its config and its state, on both platforms it can run on.

`skill-authoring-taudelta` states the resolution order once — explicit argument, then the skill's own
variable, then `$XDG_*`, then the Linux-layout default on every OS — and every script copies three
lines rather than importing a sibling, because skills install individually and one cannot import
another. Duplicated code is what drifts, so the order is pinned here for each copy rather than
trusted to review.

The one Windows arm left since 2026-11-08 is the fallback to the old `%APPDATA%`/`%LOCALAPPDATA%`
defaults while they hold the only copy. It is exercised by pinning each script's own `WINDOWS`
constant, so the Linux leg tests it too.

The constant exists *because* of this file. Patching `os.name` — the obvious way to fake a platform
— makes `pathlib` hand out `WindowsPath` objects that a Linux interpreter refuses to instantiate, so
every path in the process dies rather than the branch being exercised. A per-module constant is the
seam, and it costs the scripts one line each.
"""

# The modules under test are standalone CLI scripts, loaded by path because `skills/` holds no
# importable package — so every symbol they expose is Any by construction.
# pyright: reportAny=false

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, script: Path):
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


plans = _load("plans_locations", REPO_ROOT / "skills" / "plan-conveyor" / "scripts" / "plans.py")
audit = _load("audit_locations", REPO_ROOT / "skills" / "session-bash-audit" / "scripts" / "audit.py")
harvest = _load("harvest_locations", REPO_ROOT / "skills" / "session-harvest" / "scripts" / "harvest.py")


@pytest.fixture
def bare_env(tmp_path, monkeypatch):
    """A machine with nothing set: no XDG variables, no Windows bases, a fake home."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # what `expanduser` reads on Windows
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for var in (
        "XDG_CONFIG_HOME",
        "XDG_STATE_HOME",
        "PLAN_CONVEYOR_CONFIG",
        "PLAN_DOCS_CONFIG",
        "APPDATA",
        "LOCALAPPDATA",
    ):
        monkeypatch.delenv(var, raising=False)
    # POSIX by default whatever the runner is; the Windows tests flip the seam themselves. Found on
    # the first Windows CI run, where the "POSIX defaults are unchanged" test read the real platform.
    monkeypatch.setattr(audit, "WINDOWS", False)
    monkeypatch.setattr(plans, "WINDOWS", False)
    monkeypatch.setattr(harvest, "WINDOWS", False)
    # Each script prints its legacy-location notice once per process; a test must see its own.
    monkeypatch.setattr(audit, "_LEGACY_NOTED", set())
    monkeypatch.setattr(plans, "_LEGACY_NOTED", set())
    return tmp_path


def test_the_xdg_variable_wins_on_windows_too(bare_env, monkeypatch):
    """A reader who exports `$XDG_STATE_HOME` on Windows means it. Only the *default* is
    per-platform; making the platform decide first would silently ignore a setting the user made."""
    monkeypatch.setattr(audit, "WINDOWS", True)
    monkeypatch.setenv("LOCALAPPDATA", str(bare_env / "AppData" / "Local"))
    monkeypatch.setenv("XDG_STATE_HOME", str(bare_env / "elsewhere"))
    assert audit.state_dir() == bare_env / "elsewhere" / "session-bash-audit"

    monkeypatch.setattr(plans, "WINDOWS", True)
    monkeypatch.setenv("APPDATA", str(bare_env / "AppData" / "Roaming"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(bare_env / "elsewhere"))
    assert plans.config_path() == bare_env / "elsewhere" / "plan-conveyor" / "config.toml"


def _windows_with_bases(bare_env, monkeypatch) -> None:
    monkeypatch.setattr(audit, "WINDOWS", True)
    monkeypatch.setattr(plans, "WINDOWS", True)
    monkeypatch.setattr(harvest, "WINDOWS", True)
    monkeypatch.setenv("LOCALAPPDATA", str(bare_env / "AppData" / "Local"))
    monkeypatch.setenv("APPDATA", str(bare_env / "AppData" / "Roaming"))


def test_windows_gets_the_linux_layout(bare_env, monkeypatch):
    """One layout on every OS, since 2026-11-08: backup and restore is one procedure across machines
    only if config and state sit in the same place everywhere. `%APPDATA%`/`%LOCALAPPDATA%` being set
    changes nothing when nothing was ever written there."""
    _windows_with_bases(bare_env, monkeypatch)
    assert audit.state_dir() == bare_env / ".local" / "state" / "session-bash-audit"
    assert audit.config_dir() == bare_env / ".config" / "session-bash-audit"
    assert plans.config_path() == bare_env / ".config" / "plan-conveyor" / "config.toml"
    assert plans.state_home() == bare_env / ".local" / "state" / "plan-conveyor"


def test_windows_reads_the_old_location_while_it_is_the_only_copy(bare_env, monkeypatch, capsys):
    """Until 2026-11-08 the Windows defaults were `%APPDATA%` (config) and `%LOCALAPPDATA%` (state).
    Reading past what is already there would answer with nothing — and for plans.py, lay a skeleton
    over the absent path and drop `[private] extra`. So the old copy is used, and the move named."""
    _windows_with_bases(bare_env, monkeypatch)
    old_state = bare_env / "AppData" / "Local" / "session-bash-audit"
    old_state.mkdir(parents=True)
    old_config = bare_env / "AppData" / "Roaming" / "plan-conveyor" / "config.toml"
    old_config.parent.mkdir(parents=True)
    old_config.write_text('[private]\nextra = ["acme"]\n', encoding="utf-8")
    old_plans_state = bare_env / "AppData" / "Local" / "plan-conveyor"
    old_plans_state.mkdir(parents=True)

    assert audit.state_dir() == old_state
    assert plans.config_path() == old_config
    assert plans.state_home() == old_plans_state
    assert harvest.plan_conveyor_config() == {"private": {"extra": ["acme"]}}
    err = capsys.readouterr().err
    assert "move it to" in err
    assert str(bare_env / ".local" / "state" / "session-bash-audit") in err


def test_once_moved_the_old_location_is_ignored_quietly(bare_env, monkeypatch, capsys):
    """A copy left behind after the move is not consulted, and nothing is printed."""
    _windows_with_bases(bare_env, monkeypatch)
    for path in (
        bare_env / "AppData" / "Local" / "session-bash-audit",
        bare_env / ".local" / "state" / "session-bash-audit",
    ):
        path.mkdir(parents=True)
    assert audit.state_dir() == bare_env / ".local" / "state" / "session-bash-audit"
    assert capsys.readouterr().err == ""


def test_posix_never_looks_at_the_windows_bases(bare_env, monkeypatch):
    """The fallback is Windows-only: a POSIX machine with an `APPDATA` export (WSL inherits one) and
    a directory there must still resolve the Linux layout."""
    monkeypatch.setenv("LOCALAPPDATA", str(bare_env / "AppData" / "Local"))
    (bare_env / "AppData" / "Local" / "session-bash-audit").mkdir(parents=True)
    assert audit.state_dir() == bare_env / ".local" / "state" / "session-bash-audit"
    assert plans.config_path() == bare_env / ".config" / "plan-conveyor" / "config.toml"


def test_the_explicit_variable_beats_everything(bare_env, monkeypatch):
    """`$PLAN_CONVEYOR_CONFIG` is the skill's own variable, one step above `$XDG_CONFIG_HOME` in the
    order — a reader who names a file means that file, whatever the platform or the XDG setting."""
    monkeypatch.setattr(plans, "WINDOWS", True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(bare_env / "xdg"))
    monkeypatch.setenv("APPDATA", str(bare_env / "AppData" / "Roaming"))
    monkeypatch.setenv("PLAN_CONVEYOR_CONFIG", str(bare_env / "pinned.toml"))
    assert plans.config_path() == bare_env / "pinned.toml"


def test_the_pre_rename_variable_alone_is_refused_not_ignored(bare_env, monkeypatch):
    """`$PLAN_DOCS_CONFIG` was this skill's variable before the 2026-09-27 rename, read as a fallback
    until 2026-09-28. Ignoring it would resolve the default path, which the writers skeletonise, so a
    reader who still exports it is told the new name instead."""
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(bare_env / "pinned.toml"))
    with pytest.raises(plans.PlanError, match="PLAN_CONVEYOR_CONFIG"):
        plans.config_path()


def test_the_current_variable_set_makes_a_leftover_old_one_harmless(bare_env, monkeypatch):
    """Both exported is a machine mid-migration, and the current name is the one that means now."""
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(bare_env / "old.toml"))
    monkeypatch.setenv("PLAN_CONVEYOR_CONFIG", str(bare_env / "new.toml"))
    assert plans.config_path() == bare_env / "new.toml"


def test_a_config_left_at_the_pre_rename_directory_is_refused_with_the_move(bare_env, monkeypatch):
    """The writers lay down a skeleton over an absent path, so reading past a config still at the
    old directory would answer with an empty one, silently dropping the `[private] extra` terms a
    public-repo scan cannot derive. The refusal names both paths and moves nothing."""
    legacy = bare_env / ".config" / "plan-docs" / "config.toml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("[private]\nextra = []\n", encoding="utf-8")
    current = bare_env / ".config" / "plan-conveyor" / "config.toml"
    with pytest.raises(plans.PlanError) as refused:
        plans.config_path()
    assert str(legacy) in str(refused.value)
    assert str(current) in str(refused.value)
    assert legacy.is_file()
    assert not current.exists()


def test_the_current_directory_wins_and_stays_quiet(bare_env, monkeypatch, capsys):
    """Once migrated, the pre-rename directory is not consulted and nothing is printed, even while
    a copy is still sitting there."""
    for name in ("plan-docs", "plan-conveyor"):
        path = bare_env / ".config" / name / "config.toml"
        path.parent.mkdir(parents=True)
        path.write_text("", encoding="utf-8")
    assert plans.config_path() == bare_env / ".config" / "plan-conveyor" / "config.toml"
    assert capsys.readouterr().err == ""
