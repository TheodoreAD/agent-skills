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

# YAML block-scalar indicators, which open a folded or literal value rather than being part of it.
BLOCK_SCALARS = frozenset({">", "|", ">-", "|-", ">+", "|+"})

# Everything a skill directory is allowed to contain. `references/` is read on demand, `scripts/`
# holds anything the skill runs, and `evals/` holds trigger cases for the skill — added 2026-08-31
# with the first suite, and recorded in AGENTS.md. A fifth entry means either a typo or a layout
# decision that should be made deliberately, in AGENTS.md, before it ships.
ALLOWED_ENTRIES = {"SKILL.md", "references", "scripts", "evals"}

# Every frontmatter key a skill may declare: exactly the specification's six. Re-read from
# agentskills.io/specification on 2026-09-05, which corrected the 2026-09-04 gate that allowed only
# `name` and `description` on the reasoning that "the reference corpus defines no such key" — the
# spec does define `license`, `compatibility` (environment requirements, 500 chars), `metadata` (a
# string-to-string map for what the spec does not define) and the experimental `allowed-tools`, and
# the reference corpus uses `license` on nearly every skill. What that gate was right about is the
# *sub-key*: `metadata: family:` was a local invention five of fourteen skills carried and nothing
# read, and a half-covered taxonomy is worse than none. So the spec's keys are open, and a key
# under `metadata:` is still a decision recorded in AGENTS.md first — see KNOWN_METADATA_KEYS.
ALLOWED_FRONTMATTER = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# The spec's cap on `compatibility`, and the field's job: environment requirements — the product it
# is meant for, system packages, network access. This corpus uses it for exactly that on every skill
# that ships a script or instructs a write outside the session's repo.
MAX_COMPATIBILITY_CHARS = 500

# `metadata:` sub-keys this corpus has decided on. Empty: the field is the spec's, the keys would be
# ours, and none has earned a reader yet.
KNOWN_METADATA_KEYS: frozenset[str] = frozenset()

# The disclosure every skill that touches the machine carries — what it reads, what it runs, and
# above all what it writes and where. Decided 2026-09-05 from the user's 2026-09-03 request for
# total transparency; the heading is fixed so a reader (or a scanner) finds it in every skill at
# the same place, and the `Writes` line is the one that must exist, since it is the one a reader
# deciding whether to trust the skill is looking for.
DISCLOSURE_HEADING = "## What this skill reads, runs and writes"
DISCLOSURE_REQUIRED_LINE = "**Writes"

# Skills knowingly over the cap, each with the plan that owns the fix. An entry here is a debt on
# the record, not an exemption: `test_no_stale_cap_debt` fails once the skill comes back under the
# limit, so the entry cannot outlive the breach it documents.
#
# Empty since 2026-08-31, when `python-conventions` was split into three skills rather than trimmed.
# Trimming would have deleted trigger vocabulary to satisfy a length check, which is backwards; the
# split was measured first — each piece was checked against real requests to confirm it wins its own
# and steals none.
KNOWN_OVER_CAP: dict[str, str] = {}


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
            # `description: >-` opens a folded block scalar; the indicator is syntax, not the first
            # word of the value. Keeping it prefixed ">- " to every folded description and made this
            # gate measure three characters too many. Found 2026-08-31.
            body = parts[1:] if parts and parts[0] in BLOCK_SCALARS else parts
            value = " ".join(p for p in body if p).strip()
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


def test_parser_drops_the_block_scalar_indicator():
    """`>-` opens a folded value; it is not the first word of one.

    Same shape as the bug above and found the same way — two measurements of one description
    disagreeing — so it is pinned the same way, against the parser rather than against the corpus.
    Left in, it prefixed ">- " to every folded description: three characters of overcount against
    the cap, and a `Use when` lead-in that appeared to start at offset 3 rather than 0.
    """
    for indicator in (">-", ">", "|", "|-"):
        folded = f"---\nname: demo\ndescription: {indicator}\n  one two\n  three\n---\nbody\n"
        assert parse_frontmatter(folded)["description"] == "one two three", indicator


SKILLS_ADD = re.compile(r"\bskills\s+add\s+(\S+)")
FENCE = re.compile(r"^```")


def _fenced_lines(text: str) -> list[str]:
    """Only lines inside fenced code blocks — the ones a reader is meant to run.

    Scoping the check here is what makes it usable. A prose mention like "installed by strangers via
    `npx skills add`" is a reference to the tool, not an instruction, and gating on those would fire
    on documentation that is doing nothing wrong.
    """
    out, inside = [], False
    for line in text.splitlines():
        if FENCE.match(line.strip()):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return out


@each_skill
def test_remote_install_commands_are_global(skill: Path):
    """`--global` is not a default, and its absence is silent in both directions.

    Without it the CLI resolves scope from the current directory: run inside a repo it writes
    `.agents/skills/`, a `.claude/skills` symlink and a `skills-lock.json` into that working tree —
    none of them gitignored, and a harness-specific directory this repo refuses on principle — while
    the user-scope copy the reader meant to update stays stale. Both halves print a green summary.

    A *local path* source is the exception rather than the flaw: `skills add ../my-skills` installs
    a working tree as-is and is the documented way to iterate while drafting. So the rule is about
    remote sources, which is what dissolved the objection that deferred this check.
    """
    for line in _fenced_lines((skill / "SKILL.md").read_text()):
        m = SKILLS_ADD.search(line)
        if not m:
            continue
        source = m.group(1)
        if "/" not in source or source.startswith((".", "/", "~")):
            continue  # a local path: the drafting form, deliberately scope-by-cwd
        assert "--global" in line or " -g" in line, (
            f"{skill.name}/SKILL.md installs a remote source without --global: {line.strip()!r}. "
            "Without it the scope depends on the reader's cwd, silently."
        )


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
def test_only_known_frontmatter_keys(skill: Path):
    fields = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    unexpected = sorted(set(fields) - ALLOWED_FRONTMATTER)
    assert not unexpected, (
        f"{skill.name}/SKILL.md declares {unexpected}; the specification defines {sorted(ALLOWED_FRONTMATTER)} "
        "and nothing else. A local key goes under `metadata:`, and is a decision to record in AGENTS.md first."
    )


@each_skill
def test_metadata_keys_are_decided_not_added(skill: Path):
    """`metadata:` is the spec's escape hatch for what it does not define, which makes every key
    under it ours to explain. `family:` was added in passing and read by nothing."""
    fields = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    declared = set(re.findall(r"(?:^|\s)([A-Za-z_][\w-]*):", fields.get("metadata", "")))
    unexpected = sorted(declared - KNOWN_METADATA_KEYS)
    assert not unexpected, (
        f"{skill.name}/SKILL.md declares metadata keys {unexpected}; a key nothing reads is a taxonomy "
        "nobody finished. Record it in AGENTS.md and KNOWN_METADATA_KEYS first."
    )


@each_skill
def test_compatibility_is_within_the_spec_cap(skill: Path):
    value = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8")).get("compatibility", "")
    assert len(value) <= MAX_COMPATIBILITY_CHARS, (
        f"{skill.name}/SKILL.md compatibility is {len(value)} chars, over the spec's {MAX_COMPATIBILITY_CHARS}"
    )


@each_skill
def test_a_skill_that_touches_the_machine_discloses_it(skill: Path):
    """Every skill that ships a script, or instructs a write outside the session's repo, says what
    it reads, runs and writes under one fixed heading, and declares its environment requirements
    in `compatibility`. A read-only convention skill carries neither — noise in twelve skills is
    how a section stops being read.

    The gate checks that the disclosure exists and has its load-bearing line; it cannot check that
    it is true. That is deliberate and worth stating: the disclosure is for a reader checking the
    skill by hand against its code, not a manifest anything enforces.
    """
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    touches = (skill / "scripts").is_dir() or DISCLOSURE_HEADING in text
    if not touches:
        return
    assert DISCLOSURE_HEADING in text, f"{skill.name} ships scripts but has no {DISCLOSURE_HEADING!r} section"
    section = text.split(DISCLOSURE_HEADING, 1)[1].split("\n## ", 1)[0]
    assert DISCLOSURE_REQUIRED_LINE in section, f"{skill.name}'s disclosure has no {DISCLOSURE_REQUIRED_LINE} line"
    assert fields.get("compatibility"), (
        f"{skill.name} discloses what it touches but declares no `compatibility:` — the spec's field for "
        "environment requirements, which is where a reader looks first"
    )


@each_skill
def test_listed_in_readme(skill: Path):
    # A skill nobody can find is a skill nobody installs — the README table is the only index.
    readme = (REPO_ROOT / "README.md").read_text()
    assert f"skills/{skill.name}/" in readme, f"{skill.name} is not linked from README.md's skill table"
