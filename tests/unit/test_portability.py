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
    """Prefix, not neighbour. Declaring one directory says nothing about the one beside it.

    The example is deliberately not a standard location: `~/.config` became portable on 2026-09-04,
    so an earlier version of this test asserted a finding that is correctly no longer one."""
    row = scan_one(tmp_path, "Notes live in `~/notes` by default.\n\nIt also reads `~/scratch/demo`.")

    assert tokens(row) == {"~/scratch/demo"}


def test_one_env_var_never_covers_another(tmp_path):
    """Deliberately not prefix-matched. `$PLANS_HOME` says nothing about `$PLANS_SENSITIVE_HOME`,
    and treating one as covering the other would hide exactly the pair a reader must tell apart —
    one of which is the store that must never leave the machine."""
    row = scan_one(tmp_path, "`$PLANS_HOME` defaults to `~/plans`.\n\nPlans also go to `$PLANS_SENSITIVE_HOME`.")

    assert tokens(row) == {"$PLANS_SENSITIVE_HOME"}


# --------------------------------------------------------------------------------------------
# a published standard location is not an assumption about a machine


def test_the_xdg_base_directories_are_portable(tmp_path):
    """`~/.config` is not the author's path, it is the specification's default, and it means the
    same thing on every machine. Found 2026-09-04: documenting the destinations in `skill-authoring`
    produced eleven findings for a section whose whole purpose is declaring where things go."""
    row = scan_one(
        tmp_path,
        "Config goes in `~/.config/demo/`, state in `~/.local/state/demo/`, "
        "cache in `~/.cache/demo/` and data in `~/.local/share/demo/`.",
    )

    assert row["bare"] == 0, f"still bare: {tokens(row)}"


def test_an_xdg_variable_is_not_a_setting_the_skill_invented(tmp_path):
    """Using `$XDG_STATE_HOME` *removes* a setting — the user already controls it. A skill-invented
    `$SOMETHING_HOME` is the finding; the specification's own variable never is."""
    row = scan_one(tmp_path, "It writes to `$XDG_STATE_HOME/demo/`, and to `$DEMO_HOME` if you set one.")

    assert tokens(row) == {"$DEMO_HOME"}


def test_a_dotfile_beside_a_standard_directory_is_still_a_finding(tmp_path):
    """Prefix-portability must not leak: `~/.claude` is one tool's private store, not a standard,
    and sits beside directories that are."""
    row = scan_one(tmp_path, "It reads `~/.claude/projects/` and writes `~/.config/demo/`.")

    assert tokens(row) == {"~/.claude/projects"}


def test_the_cross_tool_instructions_file_is_portable(tmp_path):
    """`~/AGENTS.md` is where every harness reads the always-loaded instructions; naming it is
    naming a convention, not one machine's dotfile."""
    row = scan_one(tmp_path, "A rule that applies everywhere belongs in `~/AGENTS.md` instead.")

    assert row["bare"] == 0, f"still bare: {tokens(row)}"


def test_naming_the_harness_that_owns_a_location_declares_it(tmp_path):
    """Found 2026-09-05: three of the corpus's seven remaining findings were declared in substance
    — "Claude Code's own transcript store, so that one reads nothing on another harness", "which
    Claude Code exports into every Bash call" — in wording the idiom list did not know."""
    row = scan_one(
        tmp_path,
        "It reads `~/.claude/projects/*.jsonl` — Claude Code's own transcript store, so that one\n"
        "reads nothing on another harness.\n\n"
        "The bare form resolves the id from `$CLAUDE_CODE_SESSION_ID`, which Claude Code exports\n"
        "into every Bash call.",
    )

    assert row["bare"] == 0, f"still bare: {tokens(row)}"


def test_a_dated_measurement_quotes_rather_than_instructs(tmp_path):
    """ "Confirmed 2026-08-30: the run left a `~/skills-lock.json`" reports what a machine had. The
    same path in an undated sentence is an instruction the reader cannot follow."""
    evidence = scan_one(tmp_path, "Confirmed 2026-08-30: the second run left a `~/skills-lock.json` behind.")
    instruction = scan_one(tmp_path, "Delete `~/skills-lock.json` before re-running.")

    assert evidence["bare"] == 0, f"still bare: {tokens(evidence)}"
    assert tokens(instruction) == {"~/skills-lock.json"}


# --------------------------------------------------------------------------------------------
# the scripts half: a literal path in code that only one machine has


def scan_script_text(tmp_path: Path, code: str) -> set[str]:
    script = tmp_path / "demo.py"
    script.write_text(code, encoding="utf-8")
    return {h["token"] for h in fitness.scan_script(script)}


def test_a_home_path_two_segments_deep_is_a_finding(tmp_path):
    """The shape `harvest.py` shipped until 2026-09-03: the author's own checkout as a guarded
    fallback, invisible on every machine but one."""
    code = 'from pathlib import Path\nFALLBACK = Path.home() / "projects" / "some-org" / "a-repo"\n'

    assert scan_script_text(tmp_path, code) == {"~/projects/some-org/a-repo"}


def test_a_single_segment_default_is_not(tmp_path):
    """`~/plans` is a documented default a skill declares in prose; the rule is two segments
    because that is where a path stops being a convention and starts being one machine's tree."""
    code = (
        'import os\nfrom pathlib import Path\nSTORE = Path(os.environ.get("PLANS_HOME", str(Path.home() / "plans")))\n'
    )

    assert scan_script_text(tmp_path, code) == set()


def test_another_tools_directory_and_the_platform_defaults_are_not(tmp_path):
    code = (
        "from pathlib import Path\n"
        'PROJECTS = Path.home() / ".claude" / "projects"\n'
        'STATE = Path.home() / ".local" / "state" / "demo"\n'
        'ROAMING = Path.home() / "AppData" / "Roaming"\n'
    )

    assert scan_script_text(tmp_path, code) == set()


def test_a_string_literal_counts_the_same_as_a_path_chain(tmp_path):
    code = 'A = "~/projects/x/y"\nB = "$HOME/work/thing"\nC = "/home/someone/projects/x"\nD = "~/notes"\n'

    assert scan_script_text(tmp_path, code) == {"~/projects/x/y", "$HOME/work/thing", "/home/someone/projects/x"}


def test_a_fixed_tmp_path_is_a_finding_and_tempfile_is_not(tmp_path):
    code = 'import tempfile\nOUT = "/tmp/demo/calls.json"\nSCRATCH = tempfile.mkdtemp(prefix="demo-")\n'

    assert scan_script_text(tmp_path, code) == {"/tmp/demo/calls.json"}


def test_a_docstring_or_comment_quoting_a_path_is_not_a_finding(tmp_path):
    """Evidence and the history of a fix live in docstrings. Only a string the code can use is."""
    code = (
        '"""Usage:\n    python3 audit.py --json /tmp/x/calls.json\n"""\n'
        "def f():\n"
        '    """Carried `~/projects/<owner>/<repo>` as a fallback until 2026-09-03."""\n'
        "    # once ~/projects/org/repo, now gone\n"
        "    return 1\n"
    )

    assert scan_script_text(tmp_path, code) == set()


def test_a_regex_about_paths_is_not_a_path(tmp_path):
    """This file's own `HOME_PATH` pattern begins with `~/` and reported itself on the first run."""
    code = 'import re\nHOME_PATH = re.compile(r"~/[\\w./*-]*[\\w*]")\n'

    assert scan_script_text(tmp_path, code) == set()


def test_a_computed_segment_is_not_a_literal_path(tmp_path):
    code = 'from pathlib import Path\ndef where(name):\n    return Path.home() / "projects" / name\n'

    assert scan_script_text(tmp_path, code) == set()


def test_script_findings_reach_the_skill_row(tmp_path):
    """The row is what the report prints, and a script hit is bare by construction — a body that
    declares `~/projects` in prose does not make a hard-coded path in the script acceptable."""
    directory = tmp_path / "demo"
    (directory / "scripts").mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when testing.\n---\n\n"
        "On this author's machine repos live in `~/projects`.\n",
        encoding="utf-8",
    )
    (directory / "scripts" / "run.py").write_text(
        'from pathlib import Path\nX = Path.home() / "projects" / "org" / "r"\n', encoding="utf-8"
    )
    row = fitness.scan_portability(fitness.load_skills([tmp_path]))["skills"][0]

    assert row["in_script"] == 1
    assert row["bare"] == 1
    assert {s["where"] for s in row["samples"]} == {"script"}
