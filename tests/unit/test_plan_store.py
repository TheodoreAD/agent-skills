"""Routing and lifecycle gate for `skills/plan-docs/scripts/plans.py`.

The script decides where a plan file is written, and one of its answers is "inside a repo you do not
own" — so the routing table is the part worth a test rather than an eyeball. Everything here runs
against a fake `$HOME` and a fake projects root: the real config, the real store and the real
`~/projects` are never read or written.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at 74 call sites.
# pyright: reportAny=false

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "plan-docs" / "scripts" / "plans.py"


def _load():
    # The script is a standalone CLI, not an importable package — load it by path, once.
    spec = importlib.util.spec_from_file_location("plans_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


plans = _load()


@dataclass
class Workspace:
    home: Path
    projects: Path
    store: Path
    config: Path
    personal: Path
    client: Path


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", f"git@example.com:x/{path.name}.git"], cwd=path, check=True)
    return path


def commit(repo: Path, name: str, text: str) -> Path:
    path = repo / name
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"add {name}"], cwd=repo, check=True)
    return path


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A fake machine: $HOME, a projects root with a personal and a deep client repo, no config."""
    home = tmp_path / "home"
    projects = home / "projects"
    (home / ".config").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("PLANS_HOME", raising=False)
    config = home / ".config" / "plan-docs" / "config.toml"
    monkeypatch.setenv("PLAN_DOCS_CONFIG", str(config))
    return Workspace(
        home=home,
        projects=projects,
        store=home / "plans",
        config=config,
        # depth 1, the ordinary case; depth 3, the Bitbucket project/repo hierarchy the store
        # layout has to mirror rather than flatten.
        personal=make_repo(projects / "github.com-personal" / "agent-skills"),
        client=make_repo(projects / "client.com-bitbucket" / "team" / "api"),
    )


def write_config(ws: Workspace, body: str) -> None:
    ws.config.parent.mkdir(parents=True, exist_ok=True)
    ws.config.write_text(f'projects_root = "{ws.projects}"\nstore = "{ws.store}"\n{body}', encoding="utf-8")


def route(path: Path):
    return plans.resolve(path, plans.load_config())


# --------------------------------------------------------------------------------------------
# config parsing


@pytest.mark.parametrize(
    ("value", "read", "write"),
    [
        ("repo", ("repo",), "repo"),
        ("store", ("store",), "store"),
        ("both", ("repo", "store"), "repo"),
        ({"mode": "both", "write": "store"}, ("repo", "store"), "store"),
    ],
)
def test_parse_rule_shapes(value, read, write):
    rule = plans.parse_rule(value, "repos.x")
    assert rule.read == read
    assert rule.write == write


@pytest.mark.parametrize(
    "value",
    [
        "central",  # not one of the three modes
        {"mode": "repo", "write": "store"},  # writing somewhere the mode never reads
        {"mode": "repo", "when": "friday"},  # unknown field, so a silently ignored intent
        7,
    ],
)
def test_parse_rule_rejects(value):
    with pytest.raises(plans.PlanError):
        plans.parse_rule(value, "repos.x")


def test_plans_home_env_beats_config_store(ws, monkeypatch):
    write_config(ws, "")
    monkeypatch.setenv("PLANS_HOME", str(ws.home / "elsewhere"))
    cfg = plans.load_config()
    assert cfg.store == ws.home / "elsewhere"
    assert cfg.store_source == "$PLANS_HOME"


# --------------------------------------------------------------------------------------------
# routing


def test_no_config_at_all_needs_a_decision(ws):
    routing = route(ws.client)
    assert routing.verdict == "needs-decision"
    assert "no config file" in routing.reason
    assert plans.main(["where", "--path", str(ws.client)]) == plans.NEEDS_DECISION


def test_unmatched_repo_needs_a_decision_even_with_a_config(ws):
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    routing = route(ws.client)
    assert routing.verdict == "needs-decision"
    assert "no rule matches" in routing.reason


def test_root_rule_routes_personal_repo_to_itself(ws):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    routing = route(ws.personal)
    assert routing.verdict == "ok"
    assert routing.source == 'roots entry "github.com-personal"'
    assert routing.write_dir == ws.personal / "plans"


def test_default_routes_client_repo_to_the_mirrored_store_path(ws):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    routing = route(ws.client)
    assert routing.verdict == "ok"
    # Mirrored at full depth: a fixed "<root>/<repo>" rule would lose the `team` level.
    assert routing.write_dir == ws.store / "client.com-bitbucket" / "team" / "api"


def test_repo_entry_beats_root_entry(ws):
    write_config(
        ws,
        'default = "store"\n'
        '[roots]\n"github.com-personal" = "repo"\n'
        '[repos]\n"github.com-personal/agent-skills" = { mode = "both", write = "store" }\n',
    )
    routing = route(ws.personal)
    assert routing.source == 'repos entry "github.com-personal/agent-skills"'
    assert [where for where, _ in routing.read_dirs()] == ["repo", "store"]
    assert routing.write_dir == ws.store / "github.com-personal" / "agent-skills"


def test_routing_is_the_same_from_a_subdirectory(ws):
    write_config(ws, 'default = "store"\n')
    nested = ws.client / "src" / "deep"
    nested.mkdir(parents=True)
    assert route(nested).write_dir == route(ws.client).write_dir


def test_repo_outside_projects_root_needs_a_decision(ws, tmp_path):
    write_config(ws, 'default = "store"\n')
    stray = make_repo(tmp_path / "stray")
    routing = route(stray)
    assert routing.verdict == "needs-decision"
    assert "not under projects_root" in routing.reason


def test_non_repo_directory_needs_a_decision(ws):
    loose = ws.home / "notes"
    loose.mkdir()
    assert route(loose).verdict == "needs-decision"


# --------------------------------------------------------------------------------------------
# creating, listing, moving


def test_new_writes_into_the_store_with_the_origin_url(ws, capsys):
    write_config(ws, 'default = "store"\n')
    assert plans.main(["new", "store-routing", "--path", str(ws.client)]) == 0
    created = Path(capsys.readouterr().out.splitlines()[0].split(": ", 1)[1])
    assert created.parent == ws.store / "client.com-bitbucket" / "team" / "api"
    front = plans.parse_frontmatter(created.read_text())
    assert front["status"] == "idea"
    assert front["repo"] == "git@example.com:x/api.git"


def test_new_in_a_repo_route_omits_the_repo_field(ws, capsys):
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    assert plans.main(["new", "trigger-eval", "--path", str(ws.personal)]) == 0
    created = Path(capsys.readouterr().out.splitlines()[0].split(": ", 1)[1])
    assert created.parent == ws.personal / "plans"
    # Location already says which repo it is; a second source of truth is a second thing to rot.
    assert "repo:" not in created.read_text()


def test_new_refuses_a_second_file_for_the_same_topic(ws):
    write_config(ws, 'default = "store"\n')
    assert plans.main(["new", "store-routing", "--path", str(ws.client)]) == 0
    assert plans.main(["new", "store-routing", "--path", str(ws.client)]) == 1


def test_new_rejects_a_non_kebab_topic(ws):
    write_config(ws, 'default = "store"\n')
    assert plans.main(["new", "Store Routing", "--path", str(ws.client)]) == 1


def test_list_reads_both_directories_in_both_mode(ws, capsys):
    write_config(ws, '[repos]\n"client.com-bitbucket/team/api" = { mode = "both", write = "store" }\n')
    (ws.client / "plans").mkdir()
    (ws.client / "plans" / "2026-01-01-old.md").write_text(
        "---\nstatus: landed\nupdated: 2026-01-02\n---\n\n## Context\n", encoding="utf-8"
    )
    plans.main(["new", "new-thing", "--path", str(ws.client)])
    capsys.readouterr()
    assert plans.main(["list", "--path", str(ws.client)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-old.md" in out
    assert "new-thing.md" in out
    assert "idea (1)" in out
    assert "landed (1)" in out


def test_move_relocates_and_stamps_the_repo_field(ws, capsys):
    write_config(ws, '[repos]\n"client.com-bitbucket/team/api" = { mode = "both", write = "store" }\n')
    source = ws.client / "plans" / "2026-01-01-old.md"
    source.parent.mkdir()
    source.write_text("---\nstatus: idea\nupdated: 2026-01-02\n---\n\n## Context\n", encoding="utf-8")
    assert plans.main(["move", "2026-01-01-old.md", "--to", "store", "--path", str(ws.client)]) == 0
    capsys.readouterr()
    moved = ws.store / "client.com-bitbucket" / "team" / "api" / "2026-01-01-old.md"
    assert not source.exists()
    assert plans.parse_frontmatter(moved.read_text())["repo"] == "git@example.com:x/api.git"


# --------------------------------------------------------------------------------------------
# the cross-repo view


def plan(directory: Path, name: str, front: str, body: str = "") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f"---\n{front}\n---\n\n## Context\n{body}", encoding="utf-8")
    return path


def test_backlog_spans_repos_and_hides_finished_plans(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-open.md", "status: idea\nupdated: 2026-01-01")
    plan(
        ws.store / "client.com-bitbucket" / "team" / "api",
        "2026-01-02-shipped.md",
        "status: landed\nupdated: 2026-01-02",
    )

    assert plans.main(["backlog", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-open.md" in out
    assert "2026-01-02-shipped.md" not in out  # terminal statuses are not open work

    plans.main(["backlog", "--all", "--path", str(ws.personal)])
    assert "2026-01-02-shipped.md" in capsys.readouterr().out


def test_backlog_sees_a_repo_no_routing_rule_covers(ws, capsys):
    """Discovery must not depend on the config being complete — the unrouted repo is exactly the one
    whose backlog would otherwise stay invisible."""
    write_config(ws, "")
    plan(ws.personal / "plans", "2026-01-01-orphan.md", "status: idea\nupdated: 2026-01-01")
    assert plans.main(["where", "--path", str(ws.personal)]) == plans.NEEDS_DECISION
    capsys.readouterr()

    assert plans.main(["backlog", "--path", str(ws.personal)]) == 0
    assert "2026-01-01-orphan.md" in capsys.readouterr().out


def test_backlog_turns_depends_on_into_blocked_by_edges(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(
        ws.personal / "plans",
        "2026-01-01-waiting.md",
        "status: idea\nupdated: 2026-01-01\ndepends_on: [repo-tasks, scaffoldapy]",
    )
    assert plans.main(["backlog", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "repo-tasks <- github.com-personal/agent-skills/2026-01-01-waiting.md" in out
    assert "scaffoldapy <- github.com-personal/agent-skills/2026-01-01-waiting.md" in out


def test_backlog_reports_status_drift_no_single_repo_can_see(ws, capsys):
    """`done` where `landed` is defined, and prose where an enum belongs. Each repo's own gate sees
    one repo, so this is the only place either can surface."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-drifted.md", "status: done\nupdated: 2026-01-01")
    plan(
        ws.store / "client.com-bitbucket" / "team" / "api",
        "2026-01-02-prose.md",
        "status: idea — hooks still unadopted, re-measure later\nupdated: 2026-01-02",
    )
    plan(ws.personal / "plans", "2026-01-03-fine.md", "status: blocked on the upstream API\nupdated: 2026-01-03")

    assert plans.main(["backlog", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "status drift (2)" in out
    assert "'done'" in out
    assert "hooks still unadopted" in out
    assert "2026-01-03-fine.md" in out  # a reason after `blocked on` is the vocabulary, not drift


def test_backlog_filters_by_tag(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-deferred.md", "status: idea\nupdated: 2026-01-01", "\n[DEFERRED: later]\n")
    plan(ws.personal / "plans", "2026-01-02-clean.md", "status: idea\nupdated: 2026-01-02")

    assert plans.main(["backlog", "--tag", "DEFERRED", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-deferred.md" in out
    assert "2026-01-02-clean.md" not in out


# --------------------------------------------------------------------------------------------
# tags and the status gates


def test_tag_matching_is_anchored(ws):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "tagged", "--path", str(ws.client)])
    path = next((ws.store / "client.com-bitbucket" / "team" / "api").glob("*-tagged.md"))
    path.write_text(
        path.read_text()
        + "\n[NEEDS CLARIFICATION: which store]\n"
        + "- [DEFERRED: the aggregator]\n"
        + "prose mentioning [DEFERRED: ...] inside a sentence must not count\n",
        encoding="utf-8",
    )
    assert [line for _, line in plans.open_tags(path, "DEFERRED")] == ["- [DEFERRED: the aggregator]"]
    assert len(plans.open_tags(path, "NEEDS CLARIFICATION")) == 1


def test_promotion_gate_blocks_planned_while_questions_are_open(ws):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "gated", "--path", str(ws.client)])
    path = next((ws.store / "client.com-bitbucket" / "team" / "api").glob("*-gated.md"))
    path.write_text(path.read_text() + "\n[NEEDS CLARIFICATION: unresolved]\n", encoding="utf-8")

    assert plans.main(["set-status", str(path), "planned", "--path", str(ws.client)]) == 1
    assert plans.parse_frontmatter(path.read_text())["status"] == "idea"

    assert plans.main(["set-status", str(path), "planned", "--force", "--path", str(ws.client)]) == 0
    assert plans.parse_frontmatter(path.read_text())["status"] == "planned"


def test_set_status_bumps_updated_and_keeps_other_fields(ws):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "moving", "--path", str(ws.client)])
    path = next((ws.store / "client.com-bitbucket" / "team" / "api").glob("*-moving.md"))
    assert plans.main(["set-status", path.name, "blocked on the store landing", "--path", str(ws.client)]) == 0
    front = plans.parse_frontmatter(path.read_text())
    assert front["status"] == "blocked on the store landing"
    assert front["updated"] == plans.today()
    assert front["repo"] == "git@example.com:x/api.git"
    assert path.read_text().count("## Context") == 1


def test_landed_gate_blocks_on_unverified(ws):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "unproven", "--path", str(ws.client)])
    path = next((ws.store / "client.com-bitbucket" / "team" / "api").glob("*-unproven.md"))
    path.write_text(path.read_text() + "\n- [UNVERIFIED: never actually run]\n", encoding="utf-8")
    assert plans.main(["set-status", path.name, "landed", "--path", str(ws.client)]) == 1


# --------------------------------------------------------------------------------------------
# config and store bootstrap


def test_config_init_writes_a_skeleton_and_never_overwrites(ws):
    assert plans.main(["config", "init"]) == 0
    assert "[roots]" in ws.config.read_text()
    ws.config.write_text('default = "store"\n', encoding="utf-8")
    assert plans.main(["config", "init"]) == 0
    assert ws.config.read_text() == 'default = "store"\n'


# --------------------------------------------------------------------------------------------
# confidentiality


def test_private_terms_stop_at_the_repo_boundary(ws):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    # Directory names *inside* a work repo are not identities — collecting them is what turns the
    # gate into noise nobody reads.
    (ws.client / "src").mkdir()
    (ws.client / "internal-service").mkdir()
    terms = plans.private_terms(plans.load_config())
    assert "client.com-bitbucket" in terms
    assert "team" in terms  # the project level of the clone path identifies the client too
    assert "internal-service" not in terms
    assert "src" not in terms
    assert "agent-skills" not in terms  # public root
    assert "github.com-personal" not in terms


def test_private_terms_split_a_root_into_its_organisation(ws):
    # The same client appears as a directory name and as an email domain. Measured 2026-08-28: a
    # term list holding only `client.com-bitbucket` scanned a document full of `@client.com`
    # addresses and reported it clean.
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    terms = plans.private_terms(plans.load_config())
    assert "client" in terms
    assert "bitbucket" not in terms  # a hosting word, identifies nobody
    assert "com" not in terms


def test_scan_catches_a_work_email_domain(ws):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    (ws.personal / "keys.md").write_text("someone@client.com__laptop_rsa\n", encoding="utf-8")
    assert plans.main(["scan", "--path", str(ws.personal)]) == 1


def test_private_terms_honour_extra_and_ignore(ws):
    write_config(
        ws,
        'default = "store"\npublic_roots = ["github.com-personal"]\n'
        '[private]\nextra = ["someone@client.example"]\nignore = ["client.com-bitbucket"]\n',
    )
    terms = plans.private_terms(plans.load_config())
    assert "someone@client.example" in terms
    assert "client.com-bitbucket" not in terms


def test_scan_fails_on_a_private_name_in_the_tree_and_passes_when_clean(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    clean = commit(ws.personal, "notes.md", "nothing sensitive here\n")
    assert plans.main(["scan", "--path", str(ws.personal)]) == 0

    clean.write_text("we mirror ~/projects/client.com-bitbucket/team/api here\n", encoding="utf-8")
    assert plans.main(["scan", "--path", str(ws.personal)]) == 1
    assert "client.com-bitbucket" in capsys.readouterr().out


def test_scan_catches_an_untracked_file(ws):
    # The file most likely to carry a fresh leak is the one written a second ago, before any add.
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    (ws.personal / "draft.md").write_text("notes on client.com-bitbucket/team/api\n", encoding="utf-8")
    assert plans.main(["scan", "--path", str(ws.personal)]) == 1


def test_scan_history_finds_what_the_working_tree_no_longer_shows(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    commit(ws.personal, "leak.md", "client.com-bitbucket runs this\n")
    commit(ws.personal, "leak.md", "redacted\n")
    assert plans.main(["scan", "--path", str(ws.personal)]) == 0  # tree is clean now
    assert plans.main(["scan", "--mode", "history", "--path", str(ws.personal)]) == 1
    assert "client.com-bitbucket" in capsys.readouterr().out


def test_scan_lists_its_terms_without_scanning(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    assert plans.main(["scan", "--list-terms", "--path", str(ws.personal)]) == 0
    assert "client.com-bitbucket" in capsys.readouterr().out


# --------------------------------------------------------------------------------------------
# repo-less plans, and graduating them


def test_new_unscoped_needs_no_repo_at_all(ws, capsys):
    write_config(ws, "")
    loose = ws.home / "not-a-repo"
    loose.mkdir()
    assert plans.main(["new", "half-an-idea", "--unscoped", "--path", str(loose)]) == 0
    created = Path(capsys.readouterr().out.splitlines()[0].split(": ", 1)[1])
    assert created.parent == ws.store / "_unscoped"
    assert plans.parse_frontmatter(created.read_text())["status"] == "idea"


def test_unscoped_plans_are_listed_separately(ws, capsys):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "half-an-idea", "--unscoped", "--path", str(ws.client)])
    plans.main(["new", "repo-scoped", "--path", str(ws.client)])
    capsys.readouterr()

    plans.main(["list", "--unscoped", "--path", str(ws.client)])
    unscoped = capsys.readouterr().out
    assert "half-an-idea" in unscoped
    assert "repo-scoped" not in unscoped

    plans.main(["list", "--path", str(ws.client)])
    scoped = capsys.readouterr().out
    assert "repo-scoped" in scoped
    assert "half-an-idea" not in scoped


def test_graduate_moves_an_idea_into_its_new_repo(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plans.main(["new", "grown-up", "--unscoped", "--path", str(ws.personal)])
    source = next((ws.store / "_unscoped").glob("*-grown-up.md"))
    capsys.readouterr()

    assert plans.main(["graduate", source.name, "--to", str(ws.personal), "--path", str(ws.personal)]) == 0
    assert not source.exists()
    assert (ws.personal / "plans" / source.name).is_file()


def test_graduate_into_a_store_routed_repo_stamps_the_origin(ws, capsys):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "grown-up", "--unscoped", "--path", str(ws.client)])
    source = next((ws.store / "_unscoped").glob("*-grown-up.md"))
    capsys.readouterr()

    plans.main(["graduate", source.name, "--to", str(ws.client), "--path", str(ws.client)])
    landed = ws.store / "client.com-bitbucket" / "team" / "api" / source.name
    assert plans.parse_frontmatter(landed.read_text())["repo"] == "git@example.com:x/api.git"


# --------------------------------------------------------------------------------------------
# repo knowledge


def test_repos_describes_each_repo_and_flags_the_private_ones(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    (ws.personal / "README.md").write_text("# agent-skills\n\nPublished Agent Skills.\n", encoding="utf-8")
    plans.main(["repos", "--path", str(ws.personal)])
    out = capsys.readouterr().out
    assert "Published Agent Skills." in out  # the README's first real line, not a grep
    assert "public" in out
    assert "work" in out


def test_describe_overrides_the_readme_and_survives_a_rewrite(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    (ws.personal / "README.md").write_text("# x\n\nStale one-liner.\n", encoding="utf-8")
    assert plans.main(["describe", "github.com-personal/agent-skills", "The real thing."]) == 0
    assert plans.main(["describe", "github.com-personal/agent-skills", "The corrected thing."]) == 0
    capsys.readouterr()

    plans.main(["repos", "--path", str(ws.personal)])
    out = capsys.readouterr().out
    assert "The corrected thing." in out
    assert "Stale one-liner." not in out
    assert out.count("The") >= 1
    assert plans.load_config().about["github.com-personal/agent-skills"] == "The corrected thing."


def test_repos_search_ranks_by_description(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    plans.main(["describe", "github.com-personal/agent-skills", "Agent Skills, published"])
    plans.main(["describe", "client.com-bitbucket/team/api", "Billing service"])
    capsys.readouterr()
    plans.main(["repos", "--search", "billing", "--path", str(ws.personal)])
    out = capsys.readouterr().out
    assert "client.com-bitbucket/team/api" in out
    assert "agent-skills" not in out


# --------------------------------------------------------------------------------------------
# install / uninstall


def test_install_is_idempotent_and_sets_the_store_up(ws, capsys):
    assert plans.main(["install", "--path", str(ws.personal)]) == 0
    assert ws.config.is_file()
    assert (ws.store / ".git").is_dir()
    assert (ws.store / "README.md").is_file()
    assert (ws.store / "_unscoped").is_dir()
    edited = ws.config.read_text() + '\ndefault = "store"\n'
    ws.config.write_text(edited, encoding="utf-8")

    capsys.readouterr()
    assert plans.main(["install", "--path", str(ws.personal)]) == 0
    assert ws.config.read_text() == edited  # never clobbers a config that already exists


def test_uninstall_keeps_the_store_unless_told_twice(ws, capsys):
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "keep-me", "--unscoped", "--path", str(ws.client)])
    capsys.readouterr()

    assert plans.main(["uninstall", "--path", str(ws.client)]) == 0
    assert not ws.config.exists()
    assert ws.store.is_dir()

    write_config(ws, 'default = "store"\n')
    # A store holding plans is their only copy: --purge-store alone must not delete it.
    assert plans.main(["uninstall", "--purge-store", "--path", str(ws.client)]) == 1
    assert ws.store.is_dir()

    write_config(ws, 'default = "store"\n')
    assert plans.main(["uninstall", "--purge-store", "--force", "--path", str(ws.client)]) == 0
    assert not ws.store.exists()
