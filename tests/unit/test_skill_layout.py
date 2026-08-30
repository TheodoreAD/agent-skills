"""Layout and frontmatter gate for every skill in this repo.

The `skills` CLI installs whatever it finds without validating much, and an agent silently never
matches a skill whose `description` is missing or malformed — so the failure mode this catches is
"published, installed, and never triggered", which nothing else in the pipeline notices.

Frontmatter is parsed with a line scan rather than a YAML dependency, but the scan has to be
**continuation-aware**. An earlier version skipped every indented line on the reasoning that
frontmatter is "a flat `key: value` block by the format's own spec"; that is false for exactly the
values this gate exists to measure, because a description long enough to breach the cap is long
enough to have been wrapped across lines. Measured 2026-08-30: `python-conventions` read as 612
characters to the old scan and 1302 in fact, so the one real violation in the corpus was the one
the gate could not see. Keeping the no-dependency stance is fine; keeping the flat-block assumption
was not.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# The Agent Skills specification's cap: `description` must be 1 to 1024 characters. A validity
# limit, not a rendering one — Claude Code separately truncates the combined description and
# `when_to_use` at 1536 in its skill listing, and budgets that listing as a whole. 1024 is the
# tightest and the one that makes a skill valid everywhere, so it is what this gates on.
MAX_DESCRIPTION_CHARS = 1024

# The spec's `name` rules: 1 to 64 characters, lowercase alphanumerics and hyphens, no leading or
# trailing hyphen and no consecutive hyphens.
MAX_NAME_CHARS = 64
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Everything a skill directory is allowed to contain. `references/` is read on demand, `scripts/`
# holds anything the skill runs, and `evals/` holds trigger cases for the skill — added 2026-08-31
# with the first suite, and recorded in AGENTS.md. A fifth entry means either a typo or a layout
# decision that should be made deliberately, in AGENTS.md, before it ships.
ALLOWED_ENTRIES = {"SKILL.md", "references", "scripts", "evals"}

# Skills knowingly over the cap, each with the plan that owns the fix. An entry here is a debt on
# the record, not an exemption: `test_no_stale_cap_debt` fails once the skill comes back under the
# limit, so the entry cannot outlive the breach it documents.
KNOWN_OVER_CAP = {
    "python-conventions": (
        "1302 chars. Trimming would delete trigger vocabulary, which is backwards; the likely fix "
        "is a split, and plans/2026-08-30-skill-fitness-analyzer.md holds it until the analyzer "
        "can say whether the pieces would contend."
    ),
}


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


def parse_frontmatter(text: str) -> dict[str, str]:
    """The `key: value` pairs between the opening and closing `---` markers, values unquoted.

    A value wrapped across several physical lines is joined back together, so what this returns is
    what an agent actually matches on. Returns an empty mapping when the file has no frontmatter
    block at all — the tests below report that as the missing-field failure it is, rather than
    raising here.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fields: dict[str, str] = {}
    key: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if key is not None:
            value = " ".join(p for p in parts if p).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key] = value

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip():
            continue
        # A new key starts only at column zero; anything indented continues the value above it.
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match and not line.startswith((" ", "\t")):
            flush()
            key, first = match.group(1), match.group(2)
            parts = [first.strip()]
        elif key is not None:
            parts.append(line.strip())
    flush()
    return fields


def skill_id(path: Path) -> str:
    return path.name


# Parametrizing directly rather than through a params= fixture: `request.param` is untyped, and the
# repo's basedpyright profile rejects the Any that leaks out of it.
each_skill = pytest.mark.parametrize("skill", skill_dirs(), ids=skill_id)


def test_repo_has_skills():
    assert skill_dirs(), f"no skill directories under {SKILLS_DIR} — the repo would install nothing"


def test_parser_joins_a_wrapped_value():
    """The regression this file was blind to for a week.

    Tests the parser rather than the corpus, so the case survives a corpus in which nothing happens
    to be wrapped — which is how the original bug stayed invisible.
    """
    wrapped = '---\nname: demo\ndescription: "one two\n  three four\n  five"\nother: x\n---\nbody\n'
    fields = parse_frontmatter(wrapped)
    assert fields["description"] == "one two three four five"
    assert fields["name"] == "demo"
    assert fields["other"] == "x", "a key after a wrapped value must still be seen"


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
def test_name_is_spec_valid(skill: Path):
    name = parse_frontmatter((skill / "SKILL.md").read_text()).get("name", "")
    assert len(name) <= MAX_NAME_CHARS, f"{skill.name} name is {len(name)} chars, over {MAX_NAME_CHARS}"
    assert NAME_PATTERN.match(name), (
        f"{skill.name} name {name!r} breaks the spec: lowercase alphanumerics and single "
        "hyphens only, never leading, trailing or consecutive"
    )


@each_skill
def test_description_is_present_and_within_limit(skill: Path):
    description = parse_frontmatter((skill / "SKILL.md").read_text()).get("description", "")
    assert description, f"{skill.name}/SKILL.md has no description — agents match on this field"
    if skill.name in KNOWN_OVER_CAP:
        pytest.xfail(f"known over cap: {KNOWN_OVER_CAP[skill.name]}")
    assert len(description) <= MAX_DESCRIPTION_CHARS, (
        f"{skill.name}/SKILL.md description is {len(description)} chars, over the {MAX_DESCRIPTION_CHARS}-char limit"
    )


@each_skill
def test_description_has_no_xml_tags(skill: Path):
    """The spec requires the description be free of XML tags.

    Backticked spans are exempt, and the exemption is the whole subtlety. Claude Code escapes angle
    brackets in the description either way, so `<namespace>` is mangled in the listing whichever
    side of this check it falls — but the rule exists to stop a description imitating the harness's
    internal formatting, and a code placeholder is not that. Flagging every `<placeholder>` would
    make the check noise, and a noisy gate gets switched off. Confirmed 2026-08-30: this check's
    first run flagged `inv <namespace>.<task>` in `invoke-task-conventions`, which is notation, not
    markup.
    """
    description = parse_frontmatter((skill / "SKILL.md").read_text()).get("description", "")
    outside_code = re.sub(r"`[^`]*`", "", description)
    assert not re.search(r"</?[A-Za-z][^>]*>", outside_code), (
        f"{skill.name}/SKILL.md description contains an XML tag outside a code span; the spec "
        "forbids it, and the harness escapes it rather than honouring it"
    )


def test_no_stale_cap_debt():
    """A skill that has come back under the cap must lose its entry, or the registry rots."""
    for name, reason in KNOWN_OVER_CAP.items():
        skill = SKILLS_DIR / name
        assert skill.is_dir(), f"KNOWN_OVER_CAP names {name}, which no longer exists"
        description = parse_frontmatter((skill / "SKILL.md").read_text()).get("description", "")
        assert len(description) > MAX_DESCRIPTION_CHARS, (
            f"{name} is now {len(description)} chars and within the cap — drop its KNOWN_OVER_CAP "
            f"entry, which still claims: {reason}"
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
