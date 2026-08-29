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
import json
import shutil
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
    # The real session's transcript lives in the real ~/.claude and would otherwise be found by the
    # session anchor, making every test depend on where the suite happens to be run from.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
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


def test_new_in_a_repo_route_omits_the_repo_field(ws, capsys, monkeypatch):
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.chdir(ws.personal)  # a repo-routed create is only allowed from inside that repo
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
    assert plans.main(["list", "--all", "--path", str(ws.client)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-old.md" in out  # the repo's own plans/
    assert "new-thing.md" in out  # the store mirror this repo also writes to
    assert "idea (1)" in out
    assert "landed (1)" in out


def test_a_landed_plan_is_hidden_from_the_rows_but_never_silently(ws, capsys):
    """`plans/` is a working set that empties out, so a terminal plan still sitting in one is a
    retirement owed — the count says so in a line even when nothing open is left to list."""
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-done.md", "status: landed\nupdated: 2026-01-01")

    assert plans.main(["list", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "(no open plans)" in out
    assert "2026-01-01-done.md" not in out
    assert "1 plan(s) at a terminal status await retirement" in out

    assert plans.main(["list", "--all", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-done.md" in out
    assert "await retirement" not in out  # --all already shows them; the nudge would be noise


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
# the listing, at each scope


def plan(directory: Path, name: str, front: str, body: str = "") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f"---\n{front}\n---\n\n## Context\n{body}", encoding="utf-8")
    return path


def test_family_scope_spans_repos_and_hides_finished_plans(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-open.md", "status: idea\nupdated: 2026-01-01")
    plan(
        ws.store / "client.com-bitbucket" / "team" / "api",
        "2026-01-02-shipped.md",
        "status: landed\nupdated: 2026-01-02",
    )

    assert plans.main(["list", "--scope", "family", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-open.md" in out
    assert "2026-01-02-shipped.md" not in out  # terminal statuses are not open work

    plans.main(["list", "--scope", "family", "--all", "--path", str(ws.personal)])
    assert "2026-01-02-shipped.md" in capsys.readouterr().out


def test_family_scope_sees_a_repo_no_routing_rule_covers(ws, capsys):
    """Discovery must not depend on the config being complete — the unrouted repo is exactly the one
    whose backlog would otherwise stay invisible."""
    write_config(ws, "")
    plan(ws.personal / "plans", "2026-01-01-orphan.md", "status: idea\nupdated: 2026-01-01")
    assert plans.main(["where", "--path", str(ws.personal)]) == plans.NEEDS_DECISION
    capsys.readouterr()

    assert plans.main(["list", "--scope", "family", "--path", str(ws.personal)]) == 0
    assert "2026-01-01-orphan.md" in capsys.readouterr().out


def test_repo_scope_reads_the_store_mirror_and_unscoped_whatever_the_route_says(ws, capsys):
    """The regression this scope exists for: under a `mode = "repo"` root, routing named only the
    repo's own directory, so an unscoped plan was unreachable from every repo on the machine."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-committed.md", "status: idea\nupdated: 2026-01-01")
    mirror = ws.store / "github.com-personal" / "agent-skills"
    plan(mirror, "2026-01-02-left-behind.md", "status: idea\nupdated: 2026-01-02")
    plan(ws.store / "_unscoped", "2026-01-03-homeless.md", "status: idea\nupdated: 2026-01-03")

    assert plans.main(["list", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "scope:   repo (auto)" in out
    assert "2026-01-01-committed.md" in out
    assert "2026-01-02-left-behind.md" in out
    assert "2026-01-03-homeless.md" in out


def test_scope_falls_back_to_family_outside_a_repo_and_inside_the_store(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-open.md", "status: idea\nupdated: 2026-01-01")
    outside = ws.home / "elsewhere"
    outside.mkdir()

    assert plans.main(["list", "--path", str(outside)]) == 0
    assert "scope:   family (auto)" in capsys.readouterr().out

    # The store is itself a git repository, so `resolve` finds a root there — but it is not a
    # project, and a session that has cd'd into it is asking about everything.
    make_repo(ws.store)
    assert plans.main(["list", "--path", str(ws.store)]) == 0
    assert "scope:   family (auto)" in capsys.readouterr().out


def test_the_idea_tier_is_capped_and_the_live_tiers_never_are(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n[view]\nidea_limit = 2\n')
    for day in range(1, 6):
        plan(ws.personal / "plans", f"2026-01-0{day}-idea.md", f"status: idea\nupdated: 2026-01-0{day}")
    for day in range(6, 9):
        plan(ws.personal / "plans", f"2026-01-0{day}-live.md", f"status: in-progress\nupdated: 2026-01-0{day}")

    assert plans.main(["list", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "idea (5, showing 2)" in out
    assert "in-progress (3)" in out  # no cap, and no "showing"
    assert "3 idea(s) not shown" in out
    # Newest kept: an idea nobody has touched is the row a cap may drop.
    assert "2026-01-05-idea.md" in out
    assert "2026-01-01-idea.md" not in out

    assert plans.main(["list", "--limit", "0", "--path", str(ws.personal)]) == 0
    assert "2026-01-01-idea.md" in capsys.readouterr().out


def test_stale_filters_by_age_and_keeps_an_unstamped_plan(ws, capsys):
    """A plan with no `updated` stamp is drift; treating it as fresh would hide the file most likely
    to have been abandoned."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-ancient.md", "status: idea\nupdated: 2026-01-01")
    plan(ws.personal / "plans", "2099-01-01-fresh.md", "status: idea\nupdated: 2099-01-01")
    plan(ws.personal / "plans", "2026-01-01-unstamped.md", "status: idea")

    assert plans.main(["list", "--stale", "30", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-ancient.md" in out
    assert "2026-01-01-unstamped.md" in out
    assert "2099-01-01-fresh.md" not in out


def test_since_and_stale_treat_an_unstamped_plan_oppositely(ws, capsys):
    """Not an inconsistency — the questions are opposites. "What has nobody touched" must surface a
    file with no evidence of being touched; "what moved this week" must not claim one moved."""
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-old.md", "status: idea\nupdated: 2026-01-01")
    plan(ws.personal / "plans", "2026-06-01-recent.md", "status: idea\nupdated: 2026-06-01")
    plan(ws.personal / "plans", "2026-01-01-unstamped.md", "status: idea")

    assert plans.main(["list", "--since", "2026-05-01", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-06-01-recent.md" in out
    assert "2026-01-01-old.md" not in out
    assert "2026-01-01-unstamped.md" not in out  # nothing says it moved

    assert plans.main(["list", "--stale", "30", "--path", str(ws.personal)]) == 0
    assert "2026-01-01-unstamped.md" in capsys.readouterr().out  # nothing says it did not


def test_since_rejects_a_date_that_is_not_iso(ws):
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    with pytest.raises(SystemExit):  # argparse rejects it at parse time, before anything is listed
        plans.main(["list", "--since", "01-01-2026", "--path", str(ws.personal)])


def test_family_scope_summarises_depends_on_while_repo_scope_names_the_plans(ws, capsys):
    """Every edge printed is a line that grows with the corpus, so the family view counts them and
    the repo being waited on gets the actionable list."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    plan(
        other / "plans",
        "2026-01-01-waiting.md",
        "status: idea\nupdated: 2026-01-01\ndepends_on: [agent-skills]",
    )
    plan(ws.personal / "plans", "2026-01-02-here.md", "status: idea\nupdated: 2026-01-02")

    assert plans.main(["list", "--scope", "family", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "agent-skills <- 1 plan(s)" in out
    assert "2026-01-01-waiting.md" not in out.split("blocked by another repo")[1]

    assert plans.main(["list", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "waiting on this repo (1)" in out
    assert "github.com-personal/repo-tasks/2026-01-01-waiting.md" in out


def test_status_drift_no_single_repo_can_see(ws, capsys):
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

    assert plans.main(["list", "--scope", "family", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "status drift (2)" in out
    assert "'done'" in out
    assert "hooks still unadopted" in out
    assert "2026-01-03-fine.md" in out  # a reason after `blocked on` is the vocabulary, not drift


def test_listing_filters_by_tag(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-deferred.md", "status: idea\nupdated: 2026-01-01", "\n[DEFERRED: later]\n")
    plan(ws.personal / "plans", "2026-01-02-clean.md", "status: idea\nupdated: 2026-01-02")

    assert plans.main(["list", "--scope", "family", "--tag", "DEFERRED", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-01-deferred.md" in out
    assert "2026-01-02-clean.md" not in out


# --------------------------------------------------------------------------------------------
# tags and the status gates


def test_every_reading_command_offers_json(ws, capsys):
    """A flag available on some commands and not others costs a retry each time an agent assumes
    uniformity, which is cheaper to finish than to document."""
    write_config(ws, '[roots]\n"github.com-personal" = "repo"\n')
    target = plan(ws.personal / "plans", "2026-01-01-one.md", "status: idea\nupdated: 2026-01-01", "\n[DEFERRED: x]\n")
    commit(ws.personal, "notes.md", f"see {target.name}\n")

    assert plans.main(["tags", "--json", "--path", str(ws.personal)]) == 0
    tags = json.loads(capsys.readouterr().out)
    assert [hit["tag"] for hit in tags] == ["DEFERRED"]

    assert plans.main(["refs", target.name, "--json", "--path", str(ws.personal)]) == 0
    refs = json.loads(capsys.readouterr().out)
    assert refs["file"] == target.name
    assert any(hit["path"].endswith("notes.md") for hit in refs["references"])

    assert plans.main(["set-status", target.name, "planned", "--json", "--path", str(ws.personal)]) == 0
    moved = json.loads(capsys.readouterr().out)
    assert (moved["from"], moved["to"]) == ("idea", "planned")


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


def test_config_set_keeps_every_comment_and_fills_in_the_commented_example(ws, capsys):
    """The skeleton's comments carry the reasoning for each key, and the rule that routing is
    configuration rather than a per-session judgement rests on them staying readable."""
    plans.main(["config", "init"])
    # Every comment except the commented-out example itself, which is what `set` consumes.
    example = '# default = "store"'
    prose = [line for line in ws.config.read_text().splitlines() if line.startswith("#") and line != example]
    capsys.readouterr()

    assert plans.main(["config", "set", "default", "store"]) == 0
    assert "set:" in capsys.readouterr().out
    after = ws.config.read_text()

    assert [line for line in after.splitlines() if line.startswith("#")] == prose
    assert 'default = "store"' in after
    assert example not in after  # the example became the value, in its own place
    assert plans.load_config().default.write == "store"


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("view.idea_limit", "20", "idea_limit = 20"),  # an integer stays one
        ("private.extra", '["acme-corp"]', 'extra = ["acme-corp"]'),  # an array stays one
        ("projects_root", "~/code", 'projects_root = "~/code"'),  # a bare word becomes a string
        ("roots.github.com-personal", "repo", '"github.com-personal" = "repo"'),  # dots are a path
        ("repos.a/b", '{ mode = "both", write = "store" }', '"a/b" = { mode = "both"'),
    ],
)
def test_config_set_encodes_each_value_shape(ws, capsys, key, value, expected):
    plans.main(["config", "init"])
    capsys.readouterr()
    assert plans.main(["config", "set", key, value]) == 0
    assert expected in ws.config.read_text()


def test_config_set_creates_a_missing_table_and_rejects_a_value_toml_cannot_read(ws, capsys):
    plans.main(["config", "init"])
    capsys.readouterr()
    assert plans.main(["config", "set", "about.some/repo", "what it is for"]) == 0
    assert '"some/repo" = "what it is for"' in ws.config.read_text()

    # A value that parses as TOML but not as this config's schema fails next to the change, not on
    # some later command that has nothing to do with it — and is not left on disk, where it would
    # break every subsequent command.
    before = ws.config.read_text()
    assert plans.main(["config", "set", "view.idea_limit", "-4"]) == 1
    assert ws.config.read_text() == before
    assert plans.load_config().idea_limit == plans.DEFAULT_IDEA_LIMIT


def test_config_set_refuses_without_a_config(ws):
    assert plans.main(["config", "set", "default", "store"]) == 1


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


def test_unscoped_plans_are_isolated_by_scope_but_visible_from_a_repo(ws, capsys):
    """`--scope unscoped` is the repo-less backlog on its own; repo scope shows it alongside the
    repo's own plans, because an unscoped plan nothing surfaces is one nobody comes back to."""
    write_config(ws, 'default = "store"\n')
    plans.main(["new", "half-an-idea", "--unscoped", "--path", str(ws.client)])
    plans.main(["new", "repo-scoped", "--path", str(ws.client)])
    capsys.readouterr()

    plans.main(["list", "--scope", "unscoped", "--path", str(ws.client)])
    unscoped = capsys.readouterr().out
    assert "half-an-idea" in unscoped
    assert "repo-scoped" not in unscoped

    plans.main(["list", "--path", str(ws.client)])
    scoped = capsys.readouterr().out
    assert "repo-scoped" in scoped
    assert "half-an-idea" in scoped


def test_filing_for_another_repo_never_touches_its_tree(ws, capsys):
    """The whole point: a session in one repo records something against another without a commit
    landing in a tree a parallel session may be holding."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ws.personal, capture_output=True, text=True, check=True
    ).stdout

    target = "github.com-personal/agent-skills"
    assert plans.main(["new", "found-elsewhere", "--for", target, "--path", str(ws.client)]) == 0
    out = capsys.readouterr().out

    filed = ws.store / "github.com-personal" / "agent-skills" / f"{plans.today()}-found-elsewhere.md"
    assert filed.is_file()
    assert not (ws.personal / "plans").exists()  # the target's own directory was never created
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ws.personal, capture_output=True, text=True, check=True
    ).stdout
    assert after == before
    # A repo-routed target means the file is in transit, and the note has to say how it lands.
    assert "in transit" in out
    assert "move <file> --to repo" in out
    assert plans.parse_frontmatter(filed.read_text())["repo"] == "git@example.com:x/agent-skills.git"


def anchor_session_to(ws: Workspace, repo: Path, monkeypatch) -> None:
    """Fake the harness transcript that says which repo this session started in.

    Clears any previous anchor: two directories holding the same session id is ambiguous, and the
    lookup deliberately returns nothing rather than guessing — so leaving the old one behind would
    silently test the fallback instead of the re-anchor.
    """
    root = ws.home / ".claude" / "projects"
    if root.is_dir():
        shutil.rmtree(root)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(ws.home / ".claude"))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")
    directory = root / plans.encode_project_dir(repo)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sess-1.jsonl").write_text("", encoding="utf-8")


def test_the_session_anchor_survives_a_drifted_cwd(ws, capsys, monkeypatch):
    """The failure the cwd-only guard could not see: with no --path, target and session repo both
    came from cwd, drifted together, always compared equal, and the plan landed in the wrong repo.
    Anchoring to where the session started gives the comparison two independent sides."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    anchor_session_to(ws, ws.personal, monkeypatch)
    monkeypatch.chdir(other)  # cwd drifted; the session still belongs to ws.personal

    assert plans.main(["new", "drifted"]) == 1
    assert not (other / "plans").exists()
    err = capsys.readouterr().err
    assert "this session started in" in err
    assert "cwd has drifted" not in err  # the anchor is authoritative, so no cwd caveat


def test_the_anchor_prevents_refusing_a_correct_action_under_drift(ws, capsys, monkeypatch):
    """The mirror-image failure: --path naming the session's real repo while cwd is elsewhere was
    refused, and the suggested --for would have filed to the store instead of the repo."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    anchor_session_to(ws, ws.personal, monkeypatch)
    monkeypatch.chdir(other)

    assert plans.main(["new", "correct", "--path", str(ws.personal)]) == 0
    assert (ws.personal / "plans" / f"{plans.today()}-correct.md").is_file()


def test_the_anchor_falls_back_to_cwd_outside_claude_code(ws, capsys, monkeypatch):
    """The skill has to work under any harness; an absent or unmatched session id is a fallback to
    the previous behaviour, not a failure."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.chdir(ws.personal)

    assert plans.claude_session_repo(plans.load_config()) is None
    anchor, source = plans.session_anchor(plans.load_config())
    assert anchor == ws.personal
    assert source.startswith("cwd")
    assert not plans.session_is_anchored(plans.load_config())
    assert plans.main(["new", "no-harness"]) == 0


def test_a_non_claude_harness_gets_the_same_guard_via_the_neutral_variable(ws, capsys, monkeypatch):
    """PLAN_DOCS_SESSION_REPO is the tier any harness can supply, and it must be exactly as strong
    as the Claude-specific one — including catching a drifted cwd."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    monkeypatch.setenv("PLAN_DOCS_SESSION_REPO", str(ws.personal))
    monkeypatch.chdir(other)  # drifted

    assert plans.session_is_anchored(plans.load_config())
    assert plans.session_anchor(plans.load_config())[1] == "$PLAN_DOCS_SESSION_REPO"
    assert plans.main(["new", "drifted"]) == 1  # caught, with no Claude env at all
    assert not (other / "plans").exists()


def test_the_neutral_variable_wins_over_the_claude_transcript(ws, capsys, monkeypatch):
    """An explicit answer beats an inferred one, so a harness that knows can always say."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    anchor_session_to(ws, ws.personal, monkeypatch)
    monkeypatch.setenv("PLAN_DOCS_SESSION_REPO", str(other))

    assert plans.session_anchor(plans.load_config()) == (other, "$PLAN_DOCS_SESSION_REPO")


def test_a_bogus_neutral_variable_fails_loudly_rather_than_silently_degrading(ws, monkeypatch):
    """Falling back to cwd here would silently weaken the guard the user just tried to strengthen."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.setenv("PLAN_DOCS_SESSION_REPO", str(ws.home / "not-a-repo"))
    with pytest.raises(plans.PlanError):
        plans.session_anchor(plans.load_config())


def test_doctor_reports_the_anchor_tier_and_flags_the_weak_one(ws, capsys, monkeypatch):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.chdir(ws.personal)

    assert plans.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "session repo:" in out
    assert "no session anchor" in out  # listed as a problem, not left silent

    monkeypatch.setenv("PLAN_DOCS_SESSION_REPO", str(ws.personal))
    assert plans.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "$PLAN_DOCS_SESSION_REPO" in out
    assert "no session anchor" not in out


def test_new_refuses_to_create_a_plan_in_another_repos_tree(ws, capsys, monkeypatch):
    """Now that --for exists, writing a new file into another repo's tree has no legitimate use —
    so this refuses and names the alternative rather than warning and doing it anyway."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.chdir(ws.client)  # the session lives here

    assert plans.main(["new", "sneaky", "--path", str(ws.personal)]) == 1
    assert not (ws.personal / "plans").exists()

    # From inside that repo it is an ordinary create.
    monkeypatch.chdir(ws.personal)
    assert plans.main(["new", "sneaky", "--path", str(ws.personal)]) == 0
    assert (ws.personal / "plans" / f"{plans.today()}-sneaky.md").is_file()


def test_graduate_into_another_repo_warns_rather_than_refusing(ws, capsys, monkeypatch):
    """It moves a file that already exists and has legitimate uses, so it is a warning — but a
    parallel session sharing that tree deserves the line every time."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    monkeypatch.chdir(ws.client)
    plans.main(["new", "homeless", "--unscoped"])
    capsys.readouterr()

    assert plans.main(["graduate", f"{plans.today()}-homeless.md", "--to", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "not the repo this session is in" in out
    assert (ws.personal / "plans" / f"{plans.today()}-homeless.md").is_file()


def test_filing_accepts_an_absolute_path_and_refuses_the_current_repo(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    assert plans.main(["new", "by-abs-path", "--for", str(ws.client), "--path", str(ws.personal)]) == 0
    capsys.readouterr()
    assert (ws.store / "client.com-bitbucket" / "team" / "api" / f"{plans.today()}-by-abs-path.md").is_file()

    # Filing against the repo you are already in is a mistake, not a shorthand.
    assert plans.main(["new", "here", "--for", str(ws.personal), "--path", str(ws.personal)]) == 1
    assert plans.main(["new", "here", "--for", str(ws.personal), "--to", "store", "--path", str(ws.client)]) == 1


def test_filing_for_a_store_routed_repo_is_at_home_not_in_transit(ws, capsys):
    """A client repo's plans live in the store permanently, so nothing is owed and the note must not
    claim the file is waiting to be absorbed."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    assert plans.main(["new", "client-thing", "--for", str(ws.client), "--path", str(ws.personal)]) == 0
    assert "in transit" not in capsys.readouterr().out


def test_absorb_completes_the_round_trip_and_empties_the_store(ws, capsys, monkeypatch):
    """File from elsewhere, absorb from inside the owning repo — the full cycle, with the target's
    tree untouched until its own session does the taking."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    anchor_session_to(ws, ws.personal, monkeypatch)  # --apply is only allowed from the owning repo
    plans.main(["new", "filed-thing", "--for", "github.com-personal/agent-skills", "--path", str(ws.client)])
    capsys.readouterr()
    name = f"{plans.today()}-filed-thing.md"
    mirror = ws.store / "github.com-personal" / "agent-skills" / name

    # Reporting is read-only: nothing moves until --apply.
    assert plans.main(["absorb", "--path", str(ws.personal)]) == 0
    assert "awaiting absorption" in capsys.readouterr().out
    assert mirror.is_file()

    assert plans.main(["absorb", "--apply", "--path", str(ws.personal)]) == 0
    assert "absorbed:" in capsys.readouterr().out
    assert (ws.personal / "plans" / name).is_file()
    assert not mirror.exists()

    assert plans.main(["absorb", "--path", str(ws.personal)]) == 0
    assert capsys.readouterr().out == ""  # silent once drained


def test_absorb_apply_refuses_for_a_repo_this_session_does_not_belong_to(ws, capsys, monkeypatch):
    """The most destructive cross-repo write in the tool — several files into a foreign tree plus
    deletions from the store — and it had no guard at all until live testing found it."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    other = make_repo(ws.projects / "github.com-personal" / "repo-tasks")
    plan(ws.store / "github.com-personal" / "repo-tasks", "2026-01-01-filed.md", "status: idea\nupdated: 2026-01-01")
    anchor_session_to(ws, ws.personal, monkeypatch)

    # Reporting from elsewhere is a harmless question.
    assert plans.main(["absorb", "--path", str(other)]) == 0
    assert "awaiting absorption" in capsys.readouterr().out

    # Applying is not.
    assert plans.main(["absorb", "--apply", "--path", str(other)]) == 1
    assert not (other / "plans").exists()
    assert (ws.store / "github.com-personal" / "repo-tasks" / "2026-01-01-filed.md").is_file()

    # From inside the owning repo it works.
    anchor_session_to(ws, other, monkeypatch)
    assert plans.main(["absorb", "--apply", "--path", str(other)]) == 0
    assert (other / "plans" / "2026-01-01-filed.md").is_file()


def test_absorb_is_silent_when_there_is_nothing_and_never_touches_a_store_routed_repo(ws, capsys):
    """A client repo's mirror is its permanent home, so nothing there is ever in transit."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.store / "client.com-bitbucket" / "team" / "api", "2026-01-01-home.md", "status: idea\nupdated: 2026-01-01")

    assert plans.main(["absorb", "--path", str(ws.client)]) == 0
    assert capsys.readouterr().out == ""
    assert (ws.store / "client.com-bitbucket" / "team" / "api" / "2026-01-01-home.md").is_file()

    assert plans.main(["absorb", "--verbose", "--path", str(ws.client)]) == 0
    assert "nothing filed" in capsys.readouterr().out


def test_absorb_refuses_to_rename_around_a_name_collision(ws, capsys, monkeypatch):
    """Two plans sharing a name is the moment a merge is wanted; a silent rename hides exactly
    that."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    anchor_session_to(ws, ws.personal, monkeypatch)
    plans.main(["new", "same-name", "--for", "github.com-personal/agent-skills", "--path", str(ws.client)])
    capsys.readouterr()
    name = f"{plans.today()}-same-name.md"
    plan(ws.personal / "plans", name, "status: idea\nupdated: 2026-01-01", "\nalready here\n")

    assert plans.main(["absorb", "--apply", "--path", str(ws.personal)]) == 1
    out = capsys.readouterr().out
    assert "CONFLICT" in out
    assert "merge, not a rename" in out
    # Neither copy was destroyed.
    assert (ws.store / "github.com-personal" / "agent-skills" / name).is_file()
    assert "already here" in (ws.personal / "plans" / name).read_text()


def test_absorb_pairs_up_the_split_a_dirty_store_forced(ws, capsys, monkeypatch):
    """The full dirty-store cycle: a harvest that could not edit an existing filed plan wrote a
    second one referencing it, and absorption is where that debt is paid — the first moment both
    halves are in one tree with one session owning them."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    anchor_session_to(ws, ws.personal, monkeypatch)
    mirror = ws.store / "github.com-personal" / "agent-skills"
    plan(mirror, "2026-01-01-caching.md", "status: idea\nupdated: 2026-01-01", "\nfirst half\n")
    plan(
        mirror,
        "2026-01-02-caching-more.md",
        "status: idea\nupdated: 2026-01-02",
        "\nstore was dirty; relates to 2026-01-01-caching.md\n",
    )
    plan(mirror, "2026-01-03-unrelated.md", "status: idea\nupdated: 2026-01-03")

    assert plans.main(["absorb", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "consolidate with 2026-01-01-caching.md" in out
    assert "two halves of one topic" in out
    assert "2026-01-03-unrelated.md" in out  # listed, but carries no consolidation note

    assert plans.main(["absorb", "--apply", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "consolidate: 2026-01-02-caching-more.md with 2026-01-01-caching.md" in out
    assert (ws.personal / "plans" / "2026-01-01-caching.md").is_file()
    assert (ws.personal / "plans" / "2026-01-02-caching-more.md").is_file()


def test_absorb_pairs_against_a_plan_already_committed_in_the_repo(ws, capsys):
    """The referenced half may already have been absorbed in an earlier pass."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(ws.personal / "plans", "2026-01-01-caching.md", "status: idea\nupdated: 2026-01-01")
    plan(
        ws.store / "github.com-personal" / "agent-skills",
        "2026-01-02-caching-more.md",
        "status: idea\nupdated: 2026-01-02",
        "\nrelates to 2026-01-01-caching.md\n",
    )

    assert plans.main(["absorb", "--json", "--path", str(ws.personal)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["absorbable"][0]["consolidate_with"] == ["2026-01-01-caching.md"]


def test_a_reference_to_a_plan_that_does_not_exist_is_not_a_pair(ws, capsys):
    """Plans cite retired and foreign plans in prose all the time; only a name that resolves to a
    real file on either side is a consolidation."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plan(
        ws.store / "github.com-personal" / "agent-skills",
        "2026-01-02-thing.md",
        "status: idea\nupdated: 2026-01-02",
        "\nextracted from the now-retired 2020-01-01-ancient.md\n",
    )

    assert plans.main(["absorb", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "consolidate" not in out
    assert "2026-01-02-thing.md" in out


def test_list_footer_surfaces_absorbable_plans(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    plans.main(["new", "waiting", "--for", "github.com-personal/agent-skills", "--path", str(ws.client)])
    capsys.readouterr()

    assert plans.main(["list", "--path", str(ws.personal)]) == 0
    assert "1 plan(s) filed for this repo await absorption" in capsys.readouterr().out


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


def test_explain_writes_nothing_and_names_the_decisions(ws, capsys):
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    before = ws.config.read_text()

    assert plans.main(["install", "--explain", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "nothing was written" in out
    assert not ws.store.exists()
    assert ws.config.read_text() == before
    for key in ("projects_root", "store", "default", "public_roots", "private.extra"):
        assert f"decision: {key}" in out


def test_explain_asks_per_root_only_when_no_default_answers_it(ws, capsys):
    """With a default set every unrouted root has the same answer already, and asking anyway turns a
    short walkthrough into one the user pays for question by question."""
    write_config(ws, 'default = "store"\n')
    assert plans.main(["install", "--explain", "--path", str(ws.personal)]) == 0
    assert "decision: roots." not in capsys.readouterr().out

    write_config(ws, "")
    assert plans.main(["install", "--explain", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "decision: roots.client.com-bitbucket" in out
    assert "decision: roots.github.com-personal" in out


def test_doctor_aggregates_by_root_and_names_only_repos_holding_plans(ws, capsys):
    """A per-repo listing named every employer and client repo on the machine — 71 rows on this
    author's, which is exactly the listing this skill exists to keep from being produced casually."""
    write_config(ws, 'default = "store"\n[roots]\n"github.com-personal" = "repo"\n')
    make_repo(ws.projects / "client.com-bitbucket" / "team" / "quiet")
    plan(ws.personal / "plans", "2026-01-01-open.md", "status: idea\nupdated: 2026-01-01")

    assert plans.main(["doctor", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "enrolled (2 root(s), 3 repo(s))" in out
    assert "github.com-personal/agent-skills" in out  # holds a plan, so it is named
    assert "quiet" not in out  # holds none, so it is not
    assert "1 idea" in out
    assert "not yours to disclose" in out  # a non-public root is present


def test_doctor_reports_a_store_that_lost_its_git_identity(ws, capsys):
    """`install` reported this once and never again, so a store broken afterwards stayed broken
    silently until `archive` returned nothing and looked like an empty history."""
    write_config(ws, 'default = "store"\n')
    plans.main(["install", "--path", str(ws.personal)])
    subprocess.run(["git", "config", "--unset", "user.email"], cwd=ws.store, check=False)
    capsys.readouterr()

    assert plans.main(["doctor", "--path", str(ws.personal)]) == 0
    assert "no git identity" in capsys.readouterr().out


def test_doctor_flags_a_repo_holding_plans_that_no_rule_routes(ws, capsys):
    write_config(ws, "")  # no default, no roots — nothing routes anything
    plan(ws.personal / "plans", "2026-01-01-orphan.md", "status: idea\nupdated: 2026-01-01")

    assert plans.main(["doctor", "--path", str(ws.personal)]) == 0
    assert "holds plans but no rule routes it" in capsys.readouterr().out


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


# --------------------------------------------------------------------------------------------
# retired plans
#
# The convention deletes a retired plan outright and calls git history the archive. That is only a
# safe rule while the retrieval path works, so these are the tests that keep the rule honest.

PLAN_NAME = "2026-08-20-store-routing.md"

RETIRED_PLAN = """\
---
status: landed
updated: 2026-08-20
---

## Context

The store mirrors
each repo's path rather than slugging it, so two clients' `api` never collide.

## Migrated to

- skills/plan-docs/references/design-rationale.md — why the path is mirrored rather than slugged,
  and what the two rejected layouts were
"""


def commit_plan(repo: Path, rel: str, text: str, message: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "--", rel], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)
    return path


def retire_plan(repo: Path, rel: str) -> None:
    subprocess.run(["git", "rm", "-q", "--", rel], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"retire {rel}"], cwd=repo, check=True)


@pytest.fixture
def retired(ws):
    """A personal repo whose one plan was drafted, landed, and then deleted on retirement."""
    write_config(ws, 'public_roots = ["github.com-personal"]\n[roots]\n"github.com-personal" = "repo"\n')
    commit_plan(ws.personal, f"plans/{PLAN_NAME}", "---\nstatus: idea\n---\n\n## Context\n\nDrafting.\n", "plan: draft")
    commit_plan(ws.personal, f"plans/{PLAN_NAME}", RETIRED_PLAN, "plan: land it")
    retire_plan(ws.personal, f"plans/{PLAN_NAME}")
    return ws


def test_archive_lists_a_deleted_plan_with_its_status_and_destination(retired, capsys):
    assert plans.main(["archive", "--path", str(retired.personal)]) == 0
    out = capsys.readouterr().out
    assert PLAN_NAME in out
    assert "landed" in out  # the status it carried when it went, read from the pre-deletion blob
    assert "design-rationale.md" in out  # its `## Migrated to` line: where the content actually is
    assert f"^:plans/{PLAN_NAME}" in out  # the command that brings it back
    # One destination, not one per wrapped line — every plan in a formatted repo has wrapped bullets.
    assert out.count("migrated to:") == 1


def test_archive_show_prints_the_file_as_it_was_before_deletion(retired, capsys):
    assert plans.main(["archive", "--show", PLAN_NAME, "--path", str(retired.personal)]) == 0
    out = capsys.readouterr().out
    assert "two clients' `api` never collide" in out
    assert "Drafting." not in out  # the final state, not the first draft


def test_archive_search_matches_a_phrase_the_formatter_wrapped(retired, capsys):
    # "The store mirrors each repo's path" is split across a line break in the file, which is what
    # every phrase in a formatter-reflowed plan eventually is. A literal pickaxe would miss it.
    assert plans.main(["archive", "--search", "store mirrors each repo's path", "--path", str(retired.personal)]) == 0
    assert PLAN_NAME in capsys.readouterr().out

    assert plans.main(["archive", "--search", "kafka topic naming", "--path", str(retired.personal)]) == 0
    assert "no retired plan" in capsys.readouterr().out


def test_archive_file_prints_the_whole_lifecycle(retired, capsys):
    assert plans.main(["archive", "--file", PLAN_NAME, "--path", str(retired.personal)]) == 0
    out = capsys.readouterr().out
    assert "plan: draft" in out
    assert "plan: land it" in out
    assert "retired here" in out
    assert "3 commit(s)" in out


def test_archive_does_not_call_a_moved_plan_retired(ws, capsys):
    """A plan that went to the store is gone from the repo's history in exactly the same way a
    retired one is. Reporting it as retired would send a session digging for content that is live."""
    write_config(ws, '[repos]\n"github.com-personal/agent-skills" = { mode = "both", write = "store" }\n')
    commit_plan(ws.personal, f"plans/{PLAN_NAME}", RETIRED_PLAN, "plan: land it")
    assert plans.main(["move", PLAN_NAME, "--to", "store", "--path", str(ws.personal)]) == 0
    retire_plan(ws.personal, f"plans/{PLAN_NAME}")
    capsys.readouterr()

    assert plans.main(["archive", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert "still live" in out
    assert "^:plans/" not in out  # no restore command for a file that never left

    assert plans.main(["archive", "--show", PLAN_NAME, "--path", str(ws.personal)]) == 1
    assert "still on the working set" in capsys.readouterr().err


def test_archive_all_finds_a_retirement_in_the_store_history(ws, capsys):
    write_config(ws, 'default = "store"\npublic_roots = ["github.com-personal"]\n')
    make_repo(ws.store)
    mirrored = "client.com-bitbucket/team/api"
    commit_plan(ws.store, f"{mirrored}/{PLAN_NAME}", RETIRED_PLAN, "plan: land it")
    retire_plan(ws.store, f"{mirrored}/{PLAN_NAME}")

    assert plans.main(["archive", "--all", "--path", str(ws.personal)]) == 0
    out = capsys.readouterr().out
    assert PLAN_NAME in out
    assert mirrored in out  # a store path names the repo it mirrors, which is the owner
    assert "never for pasting into a repo you publish" in out


def test_archive_reports_a_store_that_cannot_archive_anything(ws, capsys):
    """The store is a git repository on purpose — an unversioned one silently loses every plan it
    is handed, and the only moment anyone would notice is the one this line exists for."""
    write_config(ws, 'default = "store"\n')
    (ws.store / "client.com-bitbucket" / "team" / "api").mkdir(parents=True)

    assert plans.main(["archive", "--path", str(ws.client)]) == 0
    assert "not a git repository" in capsys.readouterr().out
