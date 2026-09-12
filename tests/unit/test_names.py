"""Tests for `skills/skill-authoring/scripts/names.py`.

Two behaviours carry this script and both are easy to get subtly wrong: the registry endpoint is a
*fuzzy* search, so an exact-match filter is the difference between a useful report and noise; and a
skill that appears in both a source checkout and the installed hub is one skill, not a collision —
getting that wrong fires on every skill an author has installed, which is how a check gets switched
off.

Every test is offline. The network call is injected, so nothing here reaches the registry.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "skill-authoring" / "scripts" / "names.py"


def _load():
    spec = importlib.util.spec_from_file_location("names_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


names = _load()


def hit(source: str, skill: str) -> dict[str, object]:
    return {"id": f"{source}/{skill}", "skillId": skill, "source": source}


def fetcher(*hits: dict[str, object]):
    return lambda _name: list(hits)


def skill_at(root: Path, name: str, body: str = "x") -> None:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(body, encoding="utf-8")


# The registry half


def test_only_an_exact_name_is_a_collision():
    """The endpoint is fuzzy: querying `plan-docs` returns `plan-docs-lite` too. A near miss is a
    different skill with a different primary key, and reporting it would train the reader to skim
    past real hits."""
    fetch = fetcher(hit("someone/skills", "plan-docs"), hit("other/skills", "plan-docs-lite"))
    owners, reachable = names.owners_of("plan-docs", fetch)
    assert owners == ["someone/skills"]
    assert reachable


def test_your_own_publications_are_not_collisions_with_yourself():
    fetch = fetcher(hit("theodoread/agent-skills", "plan-docs"), hit("someone/skills", "plan-docs"))
    owners, _ = names.owners_of("plan-docs", fetch, mine="theodoread")
    assert owners == ["someone/skills"]


def test_owners_are_sorted_and_deduplicated():
    fetch = fetcher(hit("b/skills", "x"), hit("a/skills", "x"), hit("b/skills", "x"))
    owners, _ = names.owners_of("x", fetch)
    assert owners == ["a/skills", "b/skills"]


def test_a_free_name_reports_no_owners_while_still_being_reachable():
    owners, reachable = names.owners_of("repo-pitch", fetcher())
    assert owners == []
    assert reachable is True


# The unknown state, which is the whole reason this can be trusted


@pytest.mark.parametrize("failure", [TimeoutError("slow"), OSError("no route"), ValueError("not json")])
def test_an_unreachable_registry_is_unknown_rather_than_clean(failure):
    """A check that silently passes when it could not run is worse than no check, because the
    answer is trusted. `ValueError` covers `json.JSONDecodeError`, which subclasses it."""

    def explode(_name: str):
        raise failure

    owners, reachable = names.owners_of("anything", explode)
    assert owners == []
    assert reachable is False


def test_unknown_exits_three_and_never_zero():
    unreachable = names.NameCheck(name="x", reachable=False)
    assert names.verdict([unreachable], offline=False) == names.INDETERMINATE


def test_offline_does_not_report_unknown_because_nothing_was_attempted():
    """`--offline` is not a failed lookup; it is a narrower question that was answered."""
    unreachable = names.NameCheck(name="x", reachable=False)
    assert names.verdict([unreachable], offline=True) == 0


def test_a_real_collision_outranks_an_unknown():
    """Two names, one certainly taken and one unanswerable: the certain finding decides the exit
    code, because it is actionable and the other is not."""
    found = names.NameCheck(name="taken", owners=["someone/skills"])
    unknown = names.NameCheck(name="other", reachable=False)
    assert names.verdict([found, unknown], offline=False) == 1


# The local half, where the false positive lives


def test_one_skill_in_two_roots_is_not_a_collision(tmp_path):
    """A source checkout and the installed hub both hold the skill you wrote. Flagging that fires
    on every skill an author has installed — the failure mode that gets a check disabled."""
    source, installed = tmp_path / "src", tmp_path / "hub"
    skill_at(source, "plan-docs", "identical")
    skill_at(installed, "plan-docs", "identical")
    local = names.local_skills([source, installed])
    check = names.NameCheck(name="plan-docs", local=local["plan-docs"])
    assert len(check.local) == 2
    assert check.local_conflict is False
    assert check.collides is False


def test_two_different_skills_under_one_name_is_a_collision(tmp_path):
    """The silent-drop condition itself: the loader keeps the first it walks and says nothing."""
    mine, theirs = tmp_path / "mine", tmp_path / "theirs"
    skill_at(mine, "skill-authoring", "my version")
    skill_at(theirs, "skill-authoring", "somebody else's version")
    local = names.local_skills([mine, theirs])
    check = names.NameCheck(name="skill-authoring", local=local["skill-authoring"])
    assert check.local_conflict is True
    assert check.collides is True


def test_a_directory_without_a_manifest_is_not_a_skill(tmp_path):
    (tmp_path / "notaskill").mkdir()
    skill_at(tmp_path, "real", "body")
    assert sorted(names.local_skills([tmp_path])) == ["real"]


def test_a_missing_root_is_skipped_rather_than_raising(tmp_path):
    assert names.local_skills([tmp_path / "nope"]) == {}


def test_local_conflict_is_reported_even_with_no_network(tmp_path):
    """The offline half still answers the question that actually bites, so an unreachable registry
    never leaves the reader with nothing."""
    mine, theirs = tmp_path / "a", tmp_path / "b"
    skill_at(mine, "x", "one")
    skill_at(theirs, "x", "two")
    local = names.local_skills([mine, theirs])
    results = names.run_checks(["x"], local, None, None)
    assert names.verdict(results, offline=True) == 1


# Wiring


def test_shared_options_may_follow_the_subcommand(tmp_path):
    """Argparse only accepts a top-level option before the subcommand, which reads as a typo to
    anybody who has used a CLI built any other way. The parent-parser trick is what allows
    `audit --offline`, and it is worth a test because it is invisible in the help output."""
    parsed = names.build_parser().parse_args(["audit", "--offline", "--root", str(tmp_path)])
    assert parsed.offline is True
    assert parsed.root == [str(tmp_path)]


def test_check_takes_several_candidates_at_once():
    parsed = names.build_parser().parse_args(["check", "one", "two", "three"])
    assert parsed.name == ["one", "two", "three"]


def test_roots_expand_a_leading_tilde():
    assert not str(names.resolve_roots(["~/somewhere"])[0]).startswith("~")


def test_the_default_roots_are_loader_scopes_and_not_a_source_checkout():
    """A source checkout is not a scope the loader walks, and including it by default flags every
    skill whose source is ahead of its install — which is what normal authoring looks like. Caught
    live: editing this very skill made it report a conflict against its own installed copy."""
    assert names.DEFAULT_ROOTS == ("~/.agents/skills", ".agents/skills")
    assert "skills" not in names.DEFAULT_ROOTS
