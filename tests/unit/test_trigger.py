"""`trigger.py`'s one gate: a shipped suite is refused when it expects skills the machine lacks.

Every other measure in `skill-fitness` ranks and never gates. This one is the exception because the
cost it prevents is the reader's money — `trigger.py` is the only script in the skill that spends
tokens, and a suite ships inside its skill as a worked example, so a reader who installed two of an
author's skills holds the author's suites for every one of them. Decided 2026-09-03, built
2026-09-05.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction.
# pyright: reportAny=false

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIGGER_PY = REPO_ROOT / "skills" / "skill-fitness" / "scripts" / "trigger.py"


def _load():
    spec = importlib.util.spec_from_file_location("trigger_script", TRIGGER_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


trigger = _load()


def install(root: Path, name: str) -> None:
    (root / name).mkdir(parents=True)
    (root / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n", encoding="utf-8")


def test_a_suite_expecting_an_absent_skill_is_named(tmp_path):
    install(tmp_path, "alpha")
    cases = [
        {"prompt": "a", "expect": "alpha"},
        {"prompt": "b", "expect": "beta"},
        {"prompt": "c", "expect": None},  # should-not-trigger needs nothing installed
    ]

    assert trigger.missing_expectations(cases, roots=[tmp_path]) == ["beta"]


def test_a_suite_whose_skills_are_all_installed_passes(tmp_path):
    install(tmp_path, "alpha")
    install(tmp_path, "beta")
    cases = [{"prompt": "a", "expect": "alpha"}, {"prompt": "b", "expect": "beta"}]

    assert trigger.missing_expectations(cases, roots=[tmp_path]) == []


def test_a_directory_without_a_skill_md_does_not_count_as_installed(tmp_path):
    (tmp_path / "beta").mkdir()
    cases = [{"prompt": "b", "expect": "beta"}]

    assert trigger.missing_expectations(cases, roots=[tmp_path]) == ["beta"]


def test_the_skill_a_candidate_proposes_need_not_be_installed(tmp_path):
    """Candidate and split modes register the proposal themselves, so the incumbent's absence is
    not a reason to refuse — the proposal is exactly what is being scored."""
    cases = [{"prompt": "a", "expect": "alpha"}]

    assert trigger.missing_expectations(cases, roots=[tmp_path], exempt={"alpha"}) == []


def test_a_missing_root_is_simply_empty(tmp_path):
    cases = [{"prompt": "a", "expect": "alpha"}]

    assert trigger.missing_expectations(cases, roots=[tmp_path / "nowhere"]) == ["alpha"]
