"""Syncing a plans store across machines: `sync`, `join`, and the conflicts they settle on their own.

Two machines are two clones of one bare repository standing in for the remote, under a fake `$HOME`.
"Here" is the store `plans.py` is configured with; "there" is a second clone the test drives with
plain git, the way another machine's session would. Nothing touches a network or the real store.
"""

# The module under test is a standalone CLI script, loaded by path, so every symbol is Any.
# pyright: reportAny=false

import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "plan-conveyor" / "scripts" / "plans.py"


def _load():
    spec = importlib.util.spec_from_file_location("plans_sync_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


plans = _load()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def identify(repo: Path) -> Path:
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    return repo


def write(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def commit(repo: Path, rel: str, text: str, message: str = "") -> None:
    write(repo, rel, text)
    git(repo, "add", "--", rel)
    git(repo, "commit", "-q", "-m", message or f"change {rel}")


def plan(title: str, body: str = "", updated: str = "2026-01-01") -> str:
    return f"---\nstatus: idea\nupdated: {updated}\n---\n\n# {title}\n\n{body}"


@dataclass
class Machines:
    home: Path
    personal: Path
    config: Path
    remote: Path
    here: Path
    there: Path

    def run(self, *args: str) -> int:
        return plans.main([*args, "--path", str(self.personal)])

    def configure(self, sync: str = "manual", extra: str = "") -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(
            f'projects_root = "{(self.home / "projects").as_posix()}"\n'
            f'store = "{self.here.as_posix()}"\n'
            'default = "store"\npublic_roots = ["github.com-personal"]\n'
            f'sync = "{sync}"\n{extra}'
            '[private]\nignore = ["client"]\n[roots]\n"github.com-personal" = "repo"\n',
            encoding="utf-8",
        )

    def clone_here(self) -> Path:
        git(self.home, "clone", "-q", str(self.remote), str(self.here))
        return identify(self.here)


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "remote", "add", "origin", f"git@example.com:x/{path.name}.git")
    return path


@pytest.fixture
def machines(tmp_path, monkeypatch) -> Machines:
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    for var in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(var, str(home))
    for var in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "LOCALAPPDATA", "PLANS_HOME", "PLANS_SENSITIVE_HOME"):
        monkeypatch.delenv(var, raising=False)
    for var in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CONFIG_DIR"):
        monkeypatch.delenv(var, raising=False)
    for prefix in ("PLAN_CONVEYOR_", "PLAN_DOCS_"):
        monkeypatch.delenv(f"{prefix}SESSION_REPO", raising=False)
        monkeypatch.delenv(f"{prefix}DEVICE", raising=False)
    config = home / ".config" / "plan-conveyor" / "config.toml"
    monkeypatch.setenv("PLAN_CONVEYOR_CONFIG", str(config))
    personal = make_repo(home / "projects" / "github.com-personal" / "agent-skills")
    make_repo(home / "projects" / "client.com-bitbucket" / "team" / "api")
    remote = home / "shared.git"
    git(home, "init", "--bare", "-q", "--initial-branch=master", str(remote))
    there = home / "there"
    git(home, "clone", "-q", str(remote), str(there))
    identify(there)
    commit(there, "_unscoped/2026-01-01-seed.md", plan("Seed"), "seed")
    git(there, "push", "-q", "origin", "master")
    return Machines(home, personal, config, remote, home / "plans", there)


def push_there(machines: Machines) -> None:
    git(machines.there, "push", "-q", "origin", "master")


# --------------------------------------------------------------------------------------------
# sync = off is a machine that reaches no remote at all


def test_off_is_the_default_and_reaches_no_remote(machines, capsys):
    machines.clone_here()
    machines.configure(sync="off")
    commit(machines.there, "_unscoped/2026-01-02-new.md", plan("New"))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    assert machines.run("push") == 0
    out = capsys.readouterr().out
    assert 'sync = "off"' in out
    assert not (machines.here / "_unscoped" / "2026-01-02-new.md").exists()


def test_a_misspelt_mode_is_refused_rather_than_read_as_off(machines, capsys):
    machines.clone_here()
    machines.configure(sync="automatic")
    assert machines.run("sync") == 1
    assert "sync must be one of off, manual, auto" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# sync: fetch, merge, settle what is safe, push


def test_sync_brings_the_other_machines_plans_in_and_publishes_this_ones(machines, capsys):
    here = machines.clone_here()
    machines.configure()
    commit(here, "_unscoped/2026-01-02-here.md", plan("Here"))
    commit(machines.there, "_unscoped/2026-01-02-there.md", plan("There"))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    out = capsys.readouterr().out
    assert "merged the remote's commits" in out
    # The receipt session-harvest's `filed` attributes a store commit by: one space, own line.
    assert re.search(rf"^committed: {git(here, 'rev-parse', '--short=12', 'HEAD')}  ", out, re.MULTILINE)
    assert "pushed:    ok" in out
    assert (here / "_unscoped" / "2026-01-02-there.md").exists()
    git(machines.there, "pull", "-q")
    assert (machines.there / "_unscoped" / "2026-01-02-here.md").exists()


def test_two_edits_of_one_plan_merge_once_the_updated_line_is_settled(machines, capsys):
    """Every edit rewrites `updated:`, so without this two machines editing different sections of one
    plan always conflict on line 3."""
    here = machines.clone_here()
    machines.configure()
    rel = "_unscoped/2026-01-01-seed.md"
    body = "## One\n\nfirst\n\n## Two\n\nsecond\n\n## Three\n\nthird\n"
    commit(machines.there, rel, plan("Seed", body))
    push_there(machines)
    git(here, "pull", "-q")
    commit(here, rel, plan("Seed", body.replace("first", "first, edited here"), updated="2026-02-01"))
    commit(machines.there, rel, plan("Seed", body.replace("third", "third, edited there"), updated="2026-03-01"))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    merged = (here / rel).read_text(encoding="utf-8")
    assert "first, edited here" in merged
    assert "third, edited there" in merged
    assert "updated: 2026-03-01" in merged
    assert "later date, 2026-03-01" in capsys.readouterr().out


def test_one_name_filed_on_both_machines_keeps_both(machines, capsys):
    here = machines.clone_here()
    machines.configure()
    rel = "_unscoped/2026-01-05-same-idea.md"
    commit(here, rel, plan("Same idea", "written here\n"))
    commit(machines.there, rel, plan("Same idea", "written there\n"))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    assert "written there" in (here / rel).read_text(encoding="utf-8")
    local = here / "_unscoped" / "2026-01-05-same-idea-local.md"
    assert "written here" in local.read_text(encoding="utf-8")


def test_an_edit_survives_the_other_machine_deleting_the_plan(machines, capsys):
    """`absorb --apply` on one machine deletes a filed plan the other machine may be editing."""
    here = machines.clone_here()
    machines.configure()
    rel = "_unscoped/2026-01-01-seed.md"
    commit(here, rel, plan("Seed", "edited here\n"))
    git(machines.there, "rm", "-q", "--", rel)
    git(machines.there, "commit", "-q", "-m", "absorbed")
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    assert "edited here" in (here / rel).read_text(encoding="utf-8")
    assert "kept the edit" in capsys.readouterr().out


def test_the_link_table_merges_by_identity_and_moves_plans_into_the_remotes_folder(machines, capsys):
    """Adjacent links collide in git's line merge, and one repository spelled in two letter cases
    merges cleanly into two folders — so the table is never left to git."""
    here = machines.clone_here()
    machines.configure()

    def table(*lines: str) -> str:
        return plans.LINKS_HEADER + "".join(f"{line}\n" for line in lines)

    aaa = '"github.com/me/aaa" = "github.com-personal/aaa"'
    commit(here, "repos.toml", table(aaa))
    commit(here, "repos.toml", table('"github.com/Me/Tool" = "personal/tool"', aaa))
    commit(here, "personal/tool/2026-01-03-tool-idea.md", plan("Tool idea"))
    tool = '"github.com/me/tool" = "github.com-personal/tool"'
    commit(machines.there, "repos.toml", table('"github.com/me/aab" = "github.com-personal/aab"', tool))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    merged = (here / "repos.toml").read_text(encoding="utf-8")
    assert '"github.com/me/aaa"' in merged
    assert '"github.com/me/aab"' in merged
    assert tool in merged
    assert "personal/tool" not in merged.replace("github.com-personal/tool", "")
    assert (here / "github.com-personal" / "tool" / "2026-01-03-tool-idea.md").exists()


def test_a_real_conflict_aborts_the_merge_and_changes_nothing(machines, capsys):
    here = machines.clone_here()
    machines.configure()
    rel = "_unscoped/2026-01-01-seed.md"
    commit(here, rel, plan("Seed", "the same line, here\n"))
    commit(machines.there, rel, plan("Seed", "the same line, there\n"))
    push_there(machines)
    before = git(here, "rev-parse", "HEAD")
    capsys.readouterr()

    assert machines.run("sync") == 1
    out = capsys.readouterr().out
    assert "CONFLICT" in out
    assert f"unresolved {rel}" in out
    assert git(here, "rev-parse", "HEAD") == before
    assert not (here / ".git" / "MERGE_HEAD").exists()
    assert git(here, "status", "--porcelain") == ""


def test_the_push_scan_reads_what_a_merge_commit_itself_added(machines, capsys):
    """`git log -p` prints no diff for a merge commit, so text written while resolving a conflict by
    hand would have been published unscanned."""
    here = machines.clone_here()
    machines.configure()
    rel = "_unscoped/2026-01-01-seed.md"
    commit(here, rel, plan("Seed", "the same line, here\n"))
    commit(machines.there, rel, plan("Seed", "the same line, there\n"))
    push_there(machines)
    git(here, "fetch", "-q")
    subprocess.run(["git", "merge", "-q", "origin/master"], cwd=here, capture_output=True, check=False)
    write(here, rel, plan("Seed", "resolved by hand, about the team/api work\n"))
    git(here, "add", "--", rel)
    git(here, "commit", "-q", "--no-edit")
    capsys.readouterr()

    assert machines.run("push") == 1
    assert "REFUSED" in capsys.readouterr().out


def test_another_sessions_staged_work_postpones_the_merge(machines, capsys):
    """`git merge` refuses when the index differs from HEAD, and that index is shared."""
    here = machines.clone_here()
    machines.configure()
    write(here, "_unscoped/2026-01-09-staged.md", plan("Staged"))
    git(here, "add", "--", "_unscoped/2026-01-09-staged.md")
    commit(machines.there, "_unscoped/2026-01-02-there.md", plan("There"))
    push_there(machines)
    capsys.readouterr()

    assert machines.run("sync") == 0
    assert "another session has staged work" in capsys.readouterr().out
    assert git(here, "diff", "--cached", "--name-only") == "_unscoped/2026-01-09-staged.md"


def test_auto_syncs_a_store_commit_straight_after_it(machines, capsys):
    here = machines.clone_here()
    machines.configure(sync="auto")
    path = write(here, "_unscoped/2026-01-02-auto.md", plan("Auto"))
    capsys.readouterr()

    assert machines.run("commit", str(path), "-m", "unscoped: auto") == 0
    assert "pushed:    ok" in capsys.readouterr().out
    assert git(machines.remote, "rev-parse", "master") == git(here, "rev-parse", "HEAD")


def test_no_sync_keeps_one_commit_local(machines, capsys):
    here = machines.clone_here()
    machines.configure(sync="auto")
    path = write(here, "_unscoped/2026-01-02-local.md", plan("Local"))

    assert machines.run("commit", str(path), "-m", "unscoped: local", "--no-sync") == 0
    assert git(machines.remote, "rev-parse", "master") != git(here, "rev-parse", "HEAD")


def test_absorb_with_auto_sees_a_plan_filed_on_the_other_machine(machines, capsys):
    """Without the fetch, "nothing waiting" and "never fetched" print the same nothing."""
    machines.clone_here()
    machines.configure(sync="auto")
    folder = "github.com-personal/agent-skills"
    commit(machines.there, f"{folder}/2026-01-04-filed-there.md", plan("Filed there"))
    push_there(machines)
    capsys.readouterr()

    machines.run("absorb")
    assert "2026-01-04-filed-there.md" in capsys.readouterr().out


def test_manual_warns_at_session_start_when_the_store_was_never_fetched(machines, capsys):
    machines.clone_here()
    (machines.here / ".git" / "FETCH_HEAD").unlink(missing_ok=True)
    machines.configure(sync="manual")
    capsys.readouterr()

    machines.run("absorb")
    assert "last fetched never (sync = manual)" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# join: once per machine, on a URL the user confirmed


def local_store(machines: Machines, branch: str = "main") -> Path:
    """A store set up on its own, before any remote: plans, a link table, and the generated files."""
    here = machines.here
    here.mkdir(parents=True)
    git(here, "init", "-q", f"--initial-branch={branch}")
    identify(here)
    commit(here, "_unscoped/2026-01-07-only-here.md", plan("Only here"))
    write(here, "README.md", "generated, never committed\n")
    return here


def test_join_dry_run_lists_both_sides_and_changes_nothing(machines, capsys):
    here = local_store(machines)
    machines.configure()
    before = git(here, "rev-parse", "HEAD")
    capsys.readouterr()

    assert machines.run("join", str(machines.remote), "--dry-run") == 0
    out = capsys.readouterr().out
    assert "renamed to master" in out
    assert "only here: 1 plan file(s)" in out
    assert "publishes: 1 local commit(s)" in out
    assert git(here, "remote") == ""
    assert git(here, "rev-parse", "HEAD") == before
    assert git(here, "symbolic-ref", "--short", "HEAD") == "main"


def test_join_names_the_device_first_and_flags_paths_differing_only_in_letter_case(machines, capsys):
    """Two files on Linux are one on Windows and macOS by default, where the checkout keeps one and a
    plan silently goes missing. And which store may go where depends on the kind of machine."""
    here = local_store(machines)
    commit(here, "_unscoped/2026-01-01-Seed.md", plan("Seed, capitalised here"))
    machines.configure()
    capsys.readouterr()

    assert machines.run("join", str(machines.remote), "--dry-run") == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("device:    contractor")
    assert "case     _unscoped/2026-01-01-Seed.md / _unscoped/2026-01-01-seed.md" in out


def test_doctor_names_a_local_attachment_that_stayed_on_another_machine(machines, capsys):
    """`_attachments/` never syncs, so a plan from another machine can cite a file that is not here."""
    here = machines.clone_here()
    machines.configure()
    stem = "2026-01-08-evidence"
    row = f"- `dump.log` — local only, 3 MB, sha256 abc, attached 2026-01-08, in ~/plans/_attachments/_unscoped/{stem}"
    commit(here, f"_unscoped/{stem}.md", plan("Evidence", f"## Attachments\n\n{row}\n"))
    capsys.readouterr()

    machines.run("doctor")
    out = capsys.readouterr().out
    assert "local attachments not on this machine (1)" in out
    assert f"{stem}.md: dump.log" in out

    write(here, f"_attachments/_unscoped/{stem}/dump.log", "the file, present\n")
    machines.run("doctor")
    assert "not on this machine" not in capsys.readouterr().out


def test_join_adopts_a_store_that_already_holds_plans_without_losing_one(machines, capsys):
    here = local_store(machines)
    machines.configure()
    capsys.readouterr()

    assert machines.run("join", str(machines.remote)) == 0
    assert git(here, "symbolic-ref", "--short", "HEAD") == "master"
    assert (here / "_unscoped" / "2026-01-07-only-here.md").exists()
    assert (here / "_unscoped" / "2026-01-01-seed.md").exists()
    assert git(here, "rev-parse", "--abbrev-ref", "@{upstream}") == "origin/master"

    assert machines.run("sync") == 0
    git(machines.there, "pull", "-q")
    assert (machines.there / "_unscoped" / "2026-01-07-only-here.md").exists()


def test_join_stops_on_an_uncommitted_plan_the_remote_also_has(machines, capsys):
    here = local_store(machines)
    write(here, "_unscoped/2026-01-01-seed.md", plan("Seed", "never committed here\n"))
    machines.configure()

    assert machines.run("join", str(machines.remote)) == 1
    assert "Commit them with plans.py commit first" in capsys.readouterr().err
    assert git(here, "remote") == ""


def test_join_clones_into_a_store_that_does_not_exist_yet(machines, capsys):
    machines.configure()
    assert machines.run("join", str(machines.remote)) == 0
    assert (machines.here / "_unscoped" / "2026-01-01-seed.md").exists()


def test_join_refuses_a_store_already_tied_to_another_remote(machines, capsys):
    here = local_store(machines)
    git(here, "remote", "add", "origin", "git@example.com:someone/else.git")
    machines.configure()

    assert machines.run("join", str(machines.remote)) != 0
    assert "Which one is right is your call" in capsys.readouterr().err


def test_join_on_a_work_device_needs_a_sanctioned_destination(machines, capsys, monkeypatch):
    monkeypatch.setenv("PLAN_CONVEYOR_DEVICE", "work")
    local_store(machines)
    machines.configure()

    assert machines.run("join", str(machines.remote)) == 1
    assert "sanctioned_remotes" in capsys.readouterr().err
