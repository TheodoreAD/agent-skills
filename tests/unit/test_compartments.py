"""The transcript readers' compartment filter: one rule, three copies, held to the same cases.

session-harvest, session-bash-audit and skill-fitness each carry their own `Compartments`, because
skills install individually and none may import another. That makes drift between the copies the
failure to guard against, so every case here runs against all three. The flow rule is reasoned in
plan-conveyor's `references/design-rationale.md`, "Why a machine is classified by activity and
ownership".
"""

# Loaded by path because `skills/` holds no importable package, so every symbol is Any by
# construction — same suppression as test_harvest.py, for the same structural reason.
# pyright: reportAny=false

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SKILLS = Path(__file__).resolve().parents[2] / "skills"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harvest = _load("harvest_compartments", SKILLS / "session-harvest" / "scripts" / "harvest.py")
audit = _load("audit_compartments", SKILLS / "session-bash-audit" / "scripts" / "audit.py")
fitness = _load("fitness_compartments", SKILLS / "skill-fitness" / "scripts" / "fitness.py")
COPIES = [harvest, audit, fitness]
IDS = ["session-harvest", "session-bash-audit", "skill-fitness"]


def slug(path: Path) -> str:
    return harvest.project_slug(path)


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """Two clients, a public open-source root, a root of the user's own, and a repo nobody classified."""
    projects = tmp_path / "projects"
    repos = {
        name: projects / rel
        for name, rel in {
            "acme": "acme/api",
            "acme-web": "acme/web",
            "globex": "globex/svc",
            "oss": "oss-org/lib",
            "mine": "personal/tool",
            "mine-other": "personal/notes",
            "stray": "unsorted/thing",
        }.items()
    }
    for repo in repos.values():
        (repo / ".git").mkdir(parents=True)
    config = tmp_path / "config.toml"
    config.write_text(
        f'projects_root = "{projects.as_posix()}"\nonboarded = "2026-01-01"\n'
        'activities = ["public", "private", "contractor"]\n'
        '[ownership]\npersonal = "own"\nacme = "shared"\nglobex = "shared"\n"oss-org" = "shared"\n'
        '[activity]\npersonal = "private"\nacme = "contractor"\nglobex = "contractor"\n"oss-org" = "public"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PLAN_CONVEYOR_CONFIG", str(config))
    return repos, config


# (where the reader runs, whose transcript, may it be quoted)
CASES = [
    ("acme", "acme", True),  # the session's own repo
    ("acme-web", "acme", True),  # the same client's root
    ("globex", "acme", False),  # another client
    ("mine", "acme", False),  # a client's words into your own work
    ("acme", "oss", True),  # public content goes anywhere
    ("mine", "oss", True),
    ("mine-other", "mine", False),  # a private repo's content stays in that repo
    ("acme", "mine", False),  # ... and never reaches a client
    ("mine", "stray", False),  # a project no classified root explains
]


@pytest.mark.parametrize("module", COPIES, ids=IDS)
@pytest.mark.parametrize(("here", "source", "allowed"), CASES)
def test_every_copy_answers_the_flow_table_the_same_way(machine, monkeypatch, module, here, source, allowed):
    repos, _ = machine
    assert module.Compartments(repos[here]).may_quote(slug(repos[source])) is allowed


@pytest.mark.parametrize("module", COPIES, ids=IDS)
def test_before_onboarding_only_the_sessions_own_repo_is_quoted(machine, module):
    repos, config = machine
    config.write_text(config.read_text(encoding="utf-8").replace('onboarded = "2026-01-01"\n', ""), encoding="utf-8")
    compartments = module.Compartments(repos["mine"])
    assert compartments.may_quote(slug(repos["mine"]))
    assert not compartments.may_quote(slug(repos["oss"]))


@pytest.mark.parametrize("module", COPIES, ids=IDS)
def test_a_corporate_machine_is_one_compartment(machine, module):
    repos, config = machine
    config.write_text(
        f'projects_root = "{(repos["mine"].parents[1]).as_posix()}"\nonboarded = "2026-01-01"\n'
        'activities = ["corporate"]\n[ownership]\nacme = "shared"\npersonal = "own"\n',
        encoding="utf-8",
    )
    assert module.Compartments(repos["mine"]).may_quote(slug(repos["acme"]))


def test_fitness_counts_every_transcript_but_quotes_only_what_may_be_shown(machine, monkeypatch, tmp_path):
    """A cluster from a client's sessions is still counted, so the measurement is honest; its
    example is withheld, so the command never reaches a report read in another compartment."""
    repos, _ = machine
    transcripts = tmp_path / "claude-projects"
    command = "python3 -c 'import json, sys; print(json.load(sys.stdin)[\"acme_secret_field\"])'"
    for session in ("s1", "s2"):
        directory = transcripts / slug(repos["acme"])
        directory.mkdir(parents=True, exist_ok=True)
        entry = {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}]},
        }
        (directory / f"{session}.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    monkeypatch.setattr(fitness, "TRANSCRIPTS", transcripts)

    monkeypatch.chdir(repos["mine"])
    rows = fitness.scan_absorbable()
    assert rows, "the cluster is still counted"
    assert rows[0]["sessions"] == 2
    assert "acme_secret_field" not in rows[0]["example"]

    monkeypatch.chdir(repos["acme"])
    assert "acme_secret_field" in fitness.scan_absorbable()[0]["example"]
