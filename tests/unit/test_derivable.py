"""The derivable-work audit in `skill-fitness`: which commands a SKILL.md makes an agent compose.

The measure's whole value is that its residue is short enough to read line by line. Every test here
pins a false positive that the first runs actually produced over this repo's own corpus — an audit
whose output is mostly noise is one that gets switched off after its first run, and each of these
would have put a compliant skill at the top of the report.

The principle being measured, stated by the user 2026-09-02: anything non-trivial a skill can derive
deterministically belongs in a script, especially CLI syntax, HTTP APIs and SQL. A rule that tells
an agent how to spell a command has to be followed correctly every time; a script is followed once.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FITNESS_PY = REPO_ROOT / "skills" / "skill-fitness" / "scripts" / "fitness.py"


def _load():
    spec = importlib.util.spec_from_file_location("fitness_derivable", FITNESS_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fitness = _load()


def fenced(language: str, *lines: str) -> str:
    return "\n".join(["prose", f"```{language}", *lines, "```", "more prose"])


# --------------------------------------------------------------------------------------------
# what counts as a command at all


def test_a_directory_diagram_is_not_a_list_of_commands():
    """`research-library`'s layout block put it top of the first report with seven findings.

    None of them was a command: they are paths in an untagged fence. Untagged fences stay in scope
    because the convention is widespread, so the filter is on the line, not on the fence.
    """
    body = fenced(
        "",
        "repos/<host>--<owner>--<repo>/   # shallow git clones",
        "docs/<file>.pdf|.epub            # downloaded reference docs",
        "$RESEARCH_HOME/",
    )
    assert fitness.command_lines(body) == []


def test_a_continuation_is_one_command_not_three():
    """A wrapped `audit.py` invocation counted as three commands, two of which had lost the program
    name that made them delegation — so a delegated call was reported as two derivable ones."""
    body = fenced(
        "shell",
        "python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --session <id> \\",
        "  --until <boundary> \\",
        "  --compare <baseline>.json",
    )
    lines = fitness.command_lines(body)
    assert len(lines) == 1
    assert fitness.classify_command(lines[0]) == {"script"}


def test_prose_fences_are_not_read_as_commands():
    body = fenced("markdown", "# a heading", "- a bullet")
    assert fitness.command_lines(body) == []


def test_a_command_survives_an_env_prefix_and_a_prompt_marker():
    body = fenced("shell", "$ PATH=/x/bin inv quality.precommit")
    assert fitness.command_lines(body) == ["$ PATH=/x/bin inv quality.precommit"]


# --------------------------------------------------------------------------------------------
# delegated, derivable, fixed


def test_a_script_call_is_delegation_however_many_placeholders_it_carries():
    line = "python3 <this skill>/scripts/fitness.py overlap --top <n> | tee out.txt"
    assert fitness.classify_command(line) == {"script"}


def test_a_skill_abbreviating_its_own_script_path_still_counts_as_delegation():
    """`plan-docs` writes `python3 <path> list`, `session-harvest` writes `python3 $H sweep`.

    Requiring a literal `.py` put `plan-docs` at 48 derivable of 49 commands, when 46 of them are
    calls into `plans.py` — the measure would have reported the repo's best-delegated skill as its
    worst offender. The indirection only counts when the skill actually has a `scripts/` directory.
    """
    assert fitness.classify_command("python3 <path> new <topic>", has_scripts=True) == {"script"}
    assert fitness.classify_command("python3 $H sweep --boundary <instant>", has_scripts=True) == {"script"}
    assert "script" not in fitness.classify_command("python3 <path> new <topic>", has_scripts=False)


def test_a_placeholder_bracket_is_not_a_shell_redirect():
    """`<path>` ends in `>`, so a naive redirect test tagged 48 lines that contain no redirect —
    a whole category of the report that was pure artefact."""
    assert fitness.classify_command("git -C <store> status") == {"placeholder"}
    assert "redirect" in fitness.classify_command("inv quality.check > log 2>&1")


def test_an_install_url_is_not_an_http_api_call():
    """`uv tool install git+https://…` is a fixed line with nothing to derive. Matching bare URLs
    reported it as an API call, which is the category this measure most wants to be right about."""
    assert fitness.classify_command("uv tool install git+https://github.com/owner/repo") == set()
    assert "http" in fitness.classify_command("curl -s https://pypi.org/pypi/<name>/json")
    assert "http" in fitness.classify_command("gh api repos/<owner>/<repo>/branches")


def test_the_categories_the_principle_names():
    assert "sql" in fitness.classify_command("SELECT name FROM plans WHERE status = 'idea'")
    assert "json" in fitness.classify_command("gh run list --json status,conclusion")
    assert "pipeline" in fitness.classify_command("rg -c pattern | sort -n")
    assert "chain" in fitness.classify_command("cd <repo> && inv quality.check")
    assert "flags" in fitness.classify_command("tool --one <a> --two <b>")


def test_a_fixed_literal_is_not_a_finding():
    assert fitness.classify_command("inv quality.precommit") == set()
    assert fitness.classify_command("pytest") == set()


# --------------------------------------------------------------------------------------------
# the per-skill roll-up and its drift check


def make_skill(tmp_path: Path, name: str, body: str, with_script: bool = False):
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(body, encoding="utf-8")
    if with_script:
        (root / "scripts").mkdir()
        (root / "scripts" / "tool.py").write_text("print(1)\n", encoding="utf-8")
    return fitness.Skill(name=name, scope=str(tmp_path), path=root, description="d", has_scripts=with_script)


def test_the_rollup_separates_the_three_buckets(tmp_path):
    skill = make_skill(
        tmp_path,
        "demo",
        fenced(
            "shell",
            "python3 <this>/scripts/tool.py run --for <repo>",
            "psql -c \"SELECT id FROM t WHERE name = '<name>'\"",
            "inv quality.precommit",
        ),
        with_script=True,
    )
    (row,) = fitness.scan_derivable([skill])
    assert (row["delegated"], row["derivable"], row["fixed"]) == (1, 1, 1)
    assert "sql" in row["kinds"]


def test_drift_is_a_rise_against_a_stored_baseline(tmp_path):
    """A single run says what is true today. The question asked was whether a skill drifts back
    toward prose after a series of improvements, which nothing answers without a previous run."""
    baseline = tmp_path / "baseline.json"
    before = [{"skill": "demo", "derivable": 1, "delegated": 4}]
    fitness.save_derivable_baseline(before, baseline)

    worse = [{"skill": "demo", "derivable": 3, "delegated": 4}]
    drift = fitness.compare_derivable(worse, baseline)
    assert drift["skills"] == [{"skill": "demo", "was": 1, "derivable": 3, "delta": 2, "verdict": "DRIFTED"}]

    better = [{"skill": "demo", "derivable": 0, "delegated": 5}]
    assert fitness.compare_derivable(better, baseline)["skills"][0]["verdict"] == "improved"


def test_a_skill_missing_from_the_baseline_is_named_rather_than_ignored(tmp_path):
    baseline = tmp_path / "baseline.json"
    fitness.save_derivable_baseline([{"skill": "gone", "derivable": 2, "delegated": 0}], baseline)
    drift = fitness.compare_derivable([{"skill": "fresh", "derivable": 0, "delegated": 1}], baseline)
    assert drift["no_longer_present"] == ["gone"]
    assert drift["skills"][0]["verdict"] == "new"


def test_this_repos_own_corpus_stays_within_its_baseline():
    """The audit run against the corpus that motivated it, which is where drift would show first.

    A rise here is a real finding, not a broken test: read
    `tests/fixtures/derivable-2026-09-02.json`, decide whether the new
    command lines are legitimate residue, and either fix the skill or re-save the baseline
    deliberately.
    """
    skills = fitness.load_skills([REPO_ROOT / "skills"])
    rows = fitness.scan_derivable(skills)
    baseline_path = REPO_ROOT / "tests" / "fixtures" / "derivable-2026-09-02.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["skills"]
    risen = [
        f"{r['skill']}: {baseline[str(r['skill'])]['derivable']} -> {r['derivable']}"
        for r in rows
        if str(r["skill"]) in baseline and int(r["derivable"]) > int(baseline[str(r["skill"])]["derivable"])
    ]
    assert not risen, f"derivable work went up: {risen}"
