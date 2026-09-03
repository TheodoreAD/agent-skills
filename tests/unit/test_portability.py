"""The portability audit's declaration check: whether a skill owns its environment assumptions.

The finding is never "this skill names the author's repo" — evidence is supposed to name real
things. It is an assumption stated as **fact**: a pointer to a document only the author can open, a
command whose task only the author's repos define, a `$VAR` nobody was told to set. So every
reference is `declared` or `bare`, and only the bare ones are findings.

Every test here pins a false negative found by running the measure over this repo's own corpus,
which is where they all came from. A declaration check that misses real declarations reports
compliant skills as defective, and that is how an audit gets switched off after its first run.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction.
# pyright: reportAny=false, reportExplicitAny=false

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FITNESS_PY = REPO_ROOT / "skills" / "skill-fitness" / "scripts" / "fitness.py"


def _load():
    spec = importlib.util.spec_from_file_location("fitness_portability", FITNESS_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fitness = _load()


def scan_one(tmp_path: Path, body: str, name: str = "demo") -> dict[str, Any]:
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Use when testing.\n---\n\n{body}\n", encoding="utf-8"
    )
    skills = fitness.load_skills([tmp_path])
    return fitness.scan_portability(skills)["skills"][0]


def tokens(row: dict[str, Any]) -> set[str]:
    return {s["token"] for s in row["samples"]}


# --------------------------------------------------------------------------------------------
# a declaration is matched against the whole block, never one line


def test_a_declaration_split_by_a_line_wrap_still_counts(tmp_path):
    """This corpus's markdown is reflowed by a formatter, so a multi-word idiom lands wherever the
    wrap falls. Found on the measure's own author 2026-09-03: a sentence ending "(`~/.local/state/…`
    by" / "default)" declared the path in prose and was reported bare. A per-line search reads
    perfectly to a human and misses it, and the same break could hit any phrase on any reflow."""
    row = scan_one(tmp_path, "A baseline goes to `~/.local/state/demo/` (`~/.local/state` by\ndefault).")

    assert row["bare"] == 0, f"still bare: {tokens(row)}"


def test_an_undeclared_path_in_its_own_block_is_still_a_finding(tmp_path):
    """The other half: joining a block must not make every block declared. A bare path in a
    paragraph that owns nothing stays a finding."""
    row = scan_one(tmp_path, "Read the notes in `~/notes/mine.md` before starting.")

    assert row["bare"] == 1
    assert tokens(row) == {"~/notes/mine.md"}


# --------------------------------------------------------------------------------------------
# a declared path covers what sits under it


def test_declaring_a_directory_covers_the_files_under_it(tmp_path):
    """A skill that says what `~/.local/state` is has told its reader about the file it writes
    there. Requiring the declaration to name each leaf reports one assumption once per filename."""
    row = scan_one(
        tmp_path,
        "State lives in `~/.local/state` by default.\n\nIt writes `~/.local/state/demo/2026-01-01.json`.",
    )

    assert row["bare"] == 0, f"still bare: {tokens(row)}"


def test_a_sibling_directory_is_not_covered(tmp_path):
    """Prefix, not neighbour. Declaring one directory says nothing about the one beside it."""
    row = scan_one(tmp_path, "State lives in `~/.local/state` by default.\n\nIt also reads `~/.config/demo`.")

    assert tokens(row) == {"~/.config/demo"}


def test_one_env_var_never_covers_another(tmp_path):
    """Deliberately not prefix-matched. `$PLANS_HOME` says nothing about `$PLANS_SENSITIVE_HOME`,
    and treating one as covering the other would hide exactly the pair a reader must tell apart —
    one of which is the store that must never leave the machine."""
    row = scan_one(tmp_path, "`$PLANS_HOME` defaults to `~/plans`.\n\nPlans also go to `$PLANS_SENSITIVE_HOME`.")

    assert tokens(row) == {"$PLANS_SENSITIVE_HOME"}
