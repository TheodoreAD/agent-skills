"""Layout and frontmatter gate for every skill in this repo.

The `skills` CLI installs whatever it finds without validating much, and an agent silently never
matches a skill whose `description` is missing or malformed — so the failure mode this catches is
"published, installed, and never triggered", which nothing else in the pipeline notices.

Frontmatter is parsed with a line scan rather than a YAML dependency: it is a flat `key: value`
block by the format's own spec, and adding PyYAML to a repo whose only Python is this file buys
nothing.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# Claude Code's documented cap on the frontmatter description, and the tightest limit among the
# agents that read this format — so it is the one worth gating on.
MAX_DESCRIPTION_CHARS = 1024

# Everything a skill directory is allowed to contain. `references/` is read on demand, `scripts/`
# holds anything the skill runs. A fourth entry means either a typo or a layout decision that
# should be made deliberately, in AGENTS.md, before it ships.
ALLOWED_ENTRIES = {"SKILL.md", "references", "scripts"}


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


def parse_frontmatter(text: str) -> dict[str, str]:
    """The `key: value` pairs between the opening and closing `---` markers, values unquoted.

    Returns an empty mapping when the file has no frontmatter block at all — the tests below
    report that as the missing-field failure it is, rather than raising here.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def skill_id(path: Path) -> str:
    return path.name


# Parametrizing directly rather than through a params= fixture: `request.param` is untyped, and the
# repo's basedpyright profile rejects the Any that leaks out of it.
each_skill = pytest.mark.parametrize("skill", skill_dirs(), ids=skill_id)


def test_repo_has_skills():
    assert skill_dirs(), f"no skill directories under {SKILLS_DIR} — the repo would install nothing"


@each_skill
def test_skill_md_exists(skill: Path):
    assert (skill / "SKILL.md").is_file(), f"{skill.name} has no SKILL.md, so no agent can load it"


@each_skill
def test_name_matches_directory(skill: Path):
    # The `skills` CLI installs into a directory named after the frontmatter `name`, not after the
    # source directory — a mismatch installs under a name the README never mentions.
    fields = parse_frontmatter((skill / "SKILL.md").read_text())
    assert fields.get("name") == skill.name, (
        f"{skill.name}/SKILL.md declares name={fields.get('name')!r}; it must match the directory"
    )


@each_skill
def test_description_is_present_and_within_limit(skill: Path):
    description = parse_frontmatter((skill / "SKILL.md").read_text()).get("description", "")
    assert description, f"{skill.name}/SKILL.md has no description — agents match on this field"
    assert len(description) <= MAX_DESCRIPTION_CHARS, (
        f"{skill.name}/SKILL.md description is {len(description)} chars, over the {MAX_DESCRIPTION_CHARS}-char limit"
    )


@each_skill
def test_only_known_entries(skill: Path):
    unexpected = sorted(p.name for p in skill.iterdir() if p.name not in ALLOWED_ENTRIES)
    assert not unexpected, f"{skill.name} contains {unexpected}; allowed: {sorted(ALLOWED_ENTRIES)}"


@each_skill
def test_listed_in_readme(skill: Path):
    # A skill nobody can find is a skill nobody installs — the README table is the only index.
    readme = (REPO_ROOT / "README.md").read_text()
    assert f"skills/{skill.name}/" in readme, f"{skill.name} is not linked from README.md's skill table"
