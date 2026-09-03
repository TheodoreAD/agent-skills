"""Who a `skill-fitness` run is for, and which files it is actually describing.

Both questions come from one correction, made by the user 2026-09-02 on being shown a portability
audit of this corpus: a published skill must not force its reader to look at reports of things they
cannot fix. A reader installs a skill and cannot edit the deployed copy — editing it is drift that
reaches nothing — so a section whose remedy is "edit the skill" is work only its author can do.

These are hard to test the ordinary way, because on the author's machine the install hub and the
source checkout hold the same fourteen names, so a broken split still looks right. Every test here
therefore builds its own corpus rather than reading the real one.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction.
# pyright: reportAny=false

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FITNESS_PY = REPO_ROOT / "skills" / "skill-fitness" / "scripts" / "fitness.py"


def _load():
    spec = importlib.util.spec_from_file_location("fitness_audience", FITNESS_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fitness = _load()

AUTHOR_SIDE = ("overlap", "absorb", "derivable", "portability")
INSTALLER_SIDE = ("inventory", "budget", "usage")


def skill(root: Path, name: str, description: str = "Use when testing.") -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n", encoding="utf-8"
    )
    return directory


def args(**overrides) -> argparse.Namespace:
    base = {"root": None, "exclude": [], "top": 12, "compare": None, "author_repo": [], "context_window": 200_000}
    return argparse.Namespace(**{**base, **overrides})


@pytest.fixture(autouse=True)
def _no_real_transcripts(tmp_path, monkeypatch):
    """`report` collects usage and budget, both of which read this machine's own Claude Code state.

    Left alone these tests took 16 seconds and their result depended on whose laptop ran them —
    and a suite that reads the real store is one bad path away from writing to it. Pointed at an
    empty directory the same tests run in well under a second and assert the same things, since
    what they check is which sections exist, never what is in them.
    """
    monkeypatch.setattr(fitness, "TRANSCRIPTS", tmp_path / "no-transcripts")
    monkeypatch.setattr(fitness, "HARNESS_STATE", tmp_path / "no-harness-state.json")


# --------------------------------------------------------------------------------------------
# report is installer-side only


def test_report_omits_every_author_side_section(tmp_path):
    """The default entry point is what a reader types, so it decides what they are handed. Before
    this split, `report` gave a stranger four sections of work they could not do, under a heading
    that reads as a defect list."""
    skill(tmp_path, "alpha")
    skills = fitness.load_skills([tmp_path])

    out, _ = fitness.collect("report", skills, args(root=[tmp_path]))

    for section in AUTHOR_SIDE:
        assert section not in out, f"report must not carry the author-side section {section!r}"


def test_report_still_carries_every_installer_side_section(tmp_path):
    """The other half of the split, and the part that makes it a split rather than a deletion: a
    stale copy, the listing cost and what actually fires are all the runner's own business."""
    skill(tmp_path, "alpha")
    skills = fitness.load_skills([tmp_path])

    out, _ = fitness.collect("report", skills, args(root=[tmp_path]))

    assert "inventory" in out
    assert "budget" in out
    assert "usage" in out


def test_each_author_side_section_still_runs_when_named(tmp_path):
    """Opt-in, not removal. Naming one is how an author reaches it."""
    skill(tmp_path, "alpha")
    skills = fitness.load_skills([tmp_path])

    for section in AUTHOR_SIDE:
        out, _ = fitness.collect(section, skills, args(root=[tmp_path]))
        key = "absorbable" if section == "absorb" else section
        assert key in out, f"{section} must still produce its section when asked for by name"


def test_the_split_is_a_property_of_the_command_not_of_the_corpus(tmp_path):
    """The rule must not be implemented by inspecting the roots. A roots-based rule behaves one way
    on the author's machine, where the hub and the checkout hold the same names, and another way
    everywhere else — which is the very bug this exists to prevent."""
    skill(tmp_path, "alpha")
    skills = fitness.load_skills([tmp_path])

    explicit, _ = fitness.collect("portability", skills, args(root=[tmp_path]))
    defaulted, _ = fitness.collect("portability", skills, args(root=None))

    assert "portability" in explicit
    assert "portability" in defaulted


# --------------------------------------------------------------------------------------------
# which population the run is describing


def test_an_explicit_root_is_named_as_such(tmp_path):
    skill(tmp_path, "alpha")
    skills = fitness.load_skills([tmp_path])

    corpus = fitness.describe_corpus(skills, args(root=[tmp_path]))

    assert corpus["kind"] == "explicit"
    assert str(tmp_path) in corpus["where"]


def test_a_corpus_read_only_from_the_hub_says_it_is_not_the_readers_to_edit(tmp_path, monkeypatch):
    """The case the whole correction was about. A reader running this gets findings in files they
    must not touch, so the report has to say so and name what to do instead."""
    hub = tmp_path / ".agents" / "skills"
    skill(hub, "alpha")
    monkeypatch.setattr(fitness, "DEFAULT_SCOPES", [hub])
    skills = fitness.load_skills([hub])

    corpus = fitness.describe_corpus(skills, args(root=None))

    assert corpus["kind"] == "installed"
    assert "not yours to edit" in corpus["note"]


def test_a_checkout_alongside_the_hub_reads_as_the_working_tree(tmp_path, monkeypatch):
    """A skill present in both is loaded from the checkout, so the run describes the working tree
    and must not claim to describe the install."""
    hub = tmp_path / ".agents" / "skills"
    checkout = tmp_path / "repo" / "skills"
    skill(hub, "alpha")
    skill(checkout, "alpha")
    monkeypatch.setattr(fitness, "DEFAULT_SCOPES", [hub])
    skills = fitness.load_skills([checkout, hub])

    corpus = fitness.describe_corpus(skills, args(root=None))

    assert corpus["kind"] == "working tree"
    assert corpus["note"] == ""


def test_a_checkout_is_ordered_ahead_of_the_installed_hub(tmp_path, monkeypatch):
    """Standing in a skills repo is an unambiguous statement about which corpus you mean, and
    `load_skills` is first-occurrence-wins — so the ordering *is* the behaviour.

    Measured 2026-09-03 before the fix: a bare run inside this repo reported 1025 body lines for
    `plan-docs` from the hub while the working tree held 1039, and only `inventory`'s stale-copy
    line hinted at it. The first version of this test asserted against `load_skills` directly and
    passed against the unfixed code, because the defect was never in `load_skills` — it was in which
    order the roots were handed to it.
    """
    hub = tmp_path / ".agents" / "skills"
    checkout = tmp_path / "repo"
    skill(hub, "alpha", description="The stale installed wording.")
    skill(checkout / "skills", "alpha", description="The wording being edited right now.")
    monkeypatch.setattr(fitness, "DEFAULT_SCOPES", [hub])

    roots = fitness.resolve_roots(None, checkout)

    assert roots[0] == checkout / "skills", "the checkout must be ordered ahead of the hub"
    assert fitness.load_skills(roots)[0].description == "The wording being edited right now."


def test_an_explicit_root_replaces_the_defaults_rather_than_joining_them(tmp_path):
    """`--root` is documented as replacing the set, which is what makes it usable for scoring a
    corpus you do not have installed."""
    assert fitness.resolve_roots([tmp_path], Path("/nowhere")) == [tmp_path]


# --------------------------------------------------------------------------------------------
# measuring a git ref, which is the only population that describes the product


def _init_repo(root: Path) -> None:
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.invalid"],
        ["git", "config", "user.name", "T"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "seed"],
    ):
        subprocess.run(argv, cwd=root, check=True, capture_output=True)


def test_a_ref_is_materialized_and_labelled_with_its_sha(tmp_path):
    """`skills add <owner>/<repo>` clones the remote, so the ref is the product. Until this existed
    every count described the working tree or the install, and none was a statement about what a
    reader could actually get."""
    repo = tmp_path / "repo"
    skill(repo / "skills", "alpha", description="As published.")
    _init_repo(repo)

    root, label = fitness.materialize_ref("HEAD", repo, tmp_path / "out")

    assert (root / "alpha" / "SKILL.md").is_file()
    assert label.startswith("HEAD @ ")
    assert fitness.load_skills([root])[0].description == "As published."


def test_a_ref_reflects_the_commit_not_the_working_tree(tmp_path):
    """The whole point: an uncommitted edit must not show up in a number that claims to describe
    what is published."""
    repo = tmp_path / "repo"
    skill(repo / "skills", "alpha", description="As published.")
    _init_repo(repo)
    skill(repo / "skills", "alpha", description="Edited but never committed.")

    root, _ = fitness.materialize_ref("HEAD", repo, tmp_path / "out")

    assert fitness.load_skills([root])[0].description == "As published."


def test_an_unknown_ref_says_it_never_fetches(tmp_path):
    """Refusing beats fetching: every script here is read-only and network-free, and trading that
    for a convenience would make an audit reach the network without being asked."""
    repo = tmp_path / "repo"
    skill(repo / "skills", "alpha")
    _init_repo(repo)

    with pytest.raises(SystemExit, match="never fetches"):
        fitness.materialize_ref("origin/nope", repo, tmp_path / "out")
