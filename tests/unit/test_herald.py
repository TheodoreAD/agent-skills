"""Tests for `skills/release-herald/scripts/herald.py`.

Every test runs against a fake `gh` that answers from in-memory fixtures, on a GitHub Enterprise
Server host — `ghes.example` — so a `github.com` leaking into any URL, path or argument is caught
by construction rather than by a dedicated check. The gitflow fixture is the case the skill exists
for: a squash-merged release PR, whose comparison from the previous tag reaches back to the start of
history, a back-merge PR, a version bump and a direct fix on the release branch.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction. The fixtures below are
# the GitHub API's own JSON shapes, which are `dict[str, Any]` for the same reason.
# pyright: reportAny=false, reportExplicitAny=false

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "release-herald"


def _load():
    spec = importlib.util.spec_from_file_location("herald_script", SKILL_DIR / "scripts" / "herald.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


herald = _load()

HOST = "ghes.example"
URL = f"https://{HOST}/acme/app"


def sha(ch: str) -> str:
    return ch * 40


@pytest.fixture(autouse=True)
def sandboxed_home(tmp_path, monkeypatch):
    """Nothing here may write to the real home: config, cache and state all resolve under tmp."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for var in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


# --------------------------------------------------------------------------------------------
# A fake gh.
# --------------------------------------------------------------------------------------------


def commit(oid: str, message: str, parents: int = 1, login: str = "dev") -> dict[str, Any]:
    return {
        "sha": oid,
        "commit": {"message": message, "author": {"name": login}},
        "parents": [{"sha": "x"}] * parents,
        "author": {"login": login},
    }


def pr(
    number: int,
    title: str,
    *,
    base: str = "develop",
    head: str = "feature/x",
    merge: str | None = None,
    body: str = "",
    labels: tuple[str, ...] = (),
    files: tuple[str, ...] = ("src/app/core.py",),
    author: str = "alice",
    head_oid: str | None = None,
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "url": f"{URL}/pull/{number}",
        "merged": True,
        "mergedAt": f"2026-10-{number:02d}T00:00:00Z",
        "baseRefName": base,
        "headRefName": head,
        "headRefOid": head_oid or sha("0"),
        "author": {"login": author},
        "mergeCommit": {"oid": merge},
        "labels": {"nodes": [{"name": n} for n in labels]},
        "files": {"totalCount": len(files), "nodes": [{"path": f, "additions": 1, "deletions": 1} for f in files]},
        "closingIssuesReferences": {"nodes": []},
        "commits": {"totalCount": 1, "nodes": []},
        "baseRepository": {"nameWithOwner": "acme/app"},
    }


class FakeGh:
    """Answers `gh` argv from a few dictionaries; anything unrouted is a 404, and is recorded."""

    def __init__(self) -> None:
        self.rest: dict[str, Any] = {}
        self.assoc: dict[str, list[dict[str, Any]]] = {}
        self.prs: dict[int, dict[str, Any]] = {}
        self.releases: set[str] = set()
        self.calls: list[list[str]] = []
        self.unrouted: list[str] = []
        self.release_args: list[str] | None = None

    def __call__(self, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append(argv)
        assert argv[0] == "gh"
        args = argv[1:]
        if args[:2] == ["repo", "view"]:
            return 0, json.dumps({"url": URL, "nameWithOwner": "acme/app", "defaultBranchRef": {"name": "main"}}), ""
        if args[:2] == ["release", "view"]:
            return (0, "{}", "") if args[2] in self.releases else (1, "", "release not found")
        if args[:2] in (["release", "create"], ["release", "edit"]):
            self.release_args = args
            return 0, f"{URL}/releases/tag/{args[2]}\n", ""
        assert args[0] == "api"
        assert args[1:3] in (["--hostname", HOST], ["graphql", "--hostname"]), args
        if args[1] == "graphql":
            return self._graphql(args)
        path = args[-1]
        if path in self.rest:
            value = self.rest[path]
            return 0, value if isinstance(value, str) else json.dumps(value), ""
        self.unrouted.append(path)
        return 1, "", "gh: Not Found (HTTP 404)"

    def _graphql(self, args: list[str]) -> tuple[int, str, str]:
        assert args[2:4] == ["--hostname", HOST]
        query = next(a for a in args if a.startswith("query="))
        repository: dict[str, Any] = {}
        for alias, oid in re.findall(r'(c\d+): object\(oid: "(\w+)"\)', query):
            repository[alias] = {"associatedPullRequests": {"nodes": self.assoc.get(oid, [])}}
        for alias, number in re.findall(r"(p\d+): pullRequest\(number: (\d+)\)", query):
            repository[alias] = self.prs.get(int(number))
        return 0, json.dumps({"data": {"repository": repository}}), ""


def make_gh(fake: FakeGh):
    return herald.Gh(runner=fake)


def repo():
    return herald.Repo(host=HOST, owner="acme", name="app", url=URL, default_branch="main")


def tags_route(fake: FakeGh, names: list[str]) -> None:
    fake.rest["repos/acme/app/tags?per_page=100&page=1"] = [{"name": n} for n in names]


def tag_route(fake: FakeGh, tag: str, oid: str) -> None:
    fake.rest[f"repos/acme/app/commits/{tag}"] = {"sha": oid}


def compare_route(fake: FakeGh, base: str, head: str, commits: list[dict[str, Any]], ahead: int | None = None) -> None:
    fake.rest[f"repos/acme/app/compare/{base}...{head}?per_page=100&page=1"] = {
        "ahead_by": len(commits) if ahead is None else ahead,
        "total_commits": len(commits),
        "commits": commits,
    }


# --------------------------------------------------------------------------------------------
# The gitflow world: v1.0.0 → v1.1.0, release PR squash-merged into main.
# --------------------------------------------------------------------------------------------


def gitflow_world() -> FakeGh:
    fake = FakeGh()
    tags_route(fake, ["v1.1.0", "v1.1.0rc1", "v1.0.0"])
    tag_route(fake, "v1.1.0", sha("b"))
    tag_route(fake, "v1.0.0", sha("a"))
    fake.rest["repos/acme/app/branches/develop"] = {"name": "develop"}

    release = pr(10, "Release 1.1.0", base="main", head="release/1.1.0", merge=sha("b"), head_oid=sha("h"))
    release["body"] = "Retries and a settings rework."
    previous_release = pr(5, "Release 1.0.0", base="main", head="rel-1.0", merge=sha("a"), head_oid=sha("g"))
    fake.assoc[sha("b")] = [release]
    fake.assoc[sha("a")] = [previous_release]
    fake.prs[10] = release

    feature = pr(
        7,
        "Add max_retries to submit",
        merge=sha("1"),
        body="Adds `max_retries` to `submit()` so a failing upload stops after N attempts instead of retrying "
        "forever. Defaults to unbounded, so existing callers see no change. Documented in docs/retries.md.",
        files=("src/app/retry.py", "docs/retries.md"),
    )
    sync = pr(8, "Sync v1.0.0 into develop", head="sync/v1.0.0", merge=sha("2"))
    breaking = pr(
        9,
        "Timeout is seconds",
        merge=sha("5"),
        body="BREAKING CHANGE: `timeout` is now in seconds.",
        labels=("breaking",),
        files=("src/app/settings.py",),
        author="bob",
    )
    for p in (feature, sync, breaking):
        fake.prs[p["number"]] = p
    fake.assoc[sha("1")] = [feature, release]
    fake.assoc[sha("2")] = [sync, release]
    fake.assoc[sha("3")] = [release]
    fake.assoc[sha("4")] = [release]
    fake.assoc[sha("5")] = [breaking, release]

    commits = [
        commit(sha("1"), "Add max_retries to submit (#7)"),
        commit(sha("2"), "Sync v1.0.0 into develop (#8)", parents=2),
        commit(sha("3"), "Bump version: 1.0.0 → 1.1.0"),
        commit(sha("4"), "Fix crash on an empty config file\n\nAn empty file used to raise a KeyError."),
        commit(sha("5"), "Timeout is seconds (#9)"),
    ]
    # From the previous tag, a squash-merged world reaches back to the start of history.
    compare_route(fake, sha("a"), sha("h"), [], ahead=812)
    compare_route(fake, sha("g"), sha("h"), commits)
    fake.rest[f"repos/acme/app/commits/{sha('4')}"] = {
        "files": [{"filename": "src/app/config.py", "patch": "@@\n-raise\n+return {}"}]
    }
    fake.rest["repos/acme/app/pulls/9/files?per_page=100&page=1"] = [
        {"filename": "src/app/settings.py", "patch": "@@\n-TIMEOUT_MS = 5000\n+TIMEOUT_S = 5"}
    ]
    return fake


def test_gitflow_takes_the_smaller_comparison_and_expands_the_release_pr():
    fake = gitflow_world()
    out = herald.collect(make_gh(fake), repo(), "v1.1.0", None, None)

    assert out["flow"]["name"] == "gitflow"
    assert out["range"]["previous"] == "v1.0.0", "a final release skips the rc between"
    assert out["range"]["base"] == sha("g"), "the previous release PR's tip, not the previous tag"
    assert "812" not in out["range"]["base_reason"]
    refs = [herald._item_ref(i) for i in out["items"]]
    assert refs == ["#7", "#9", sha("4")[:7]], refs
    reasons = {e["ref"]: e["reason"] for e in out["excluded"]}
    assert "back-merge" in reasons["#8"]
    assert reasons[sha("3")[:7]] == "version bump"
    assert out["release_context"] == "Retries and a settings rework."


def test_a_mis_named_release_branch_is_still_the_release_pr():
    """`rel-1.0` is not `release/*`, and it is still found — by its base, the production branch."""
    fake = gitflow_world()
    out = herald.collect(make_gh(fake), repo(), "v1.1.0", None, None)
    heads = {c["headRefName"] for c in out["range"]["containers"]}
    assert heads == {"release/1.1.0", "rel-1.0"}


def test_signals_and_surface_diffs_reach_the_digest():
    fake = gitflow_world()
    out = herald.collect(make_gh(fake), repo(), "v1.1.0", None, None)
    by_ref = {herald._item_ref(i): i for i in out["items"]}
    assert by_ref["#9"]["signals"]["breaking"] == ["label", "text"]
    assert by_ref["#9"]["surface_patches"]["src/app/settings.py"].endswith("+TIMEOUT_S = 5")
    assert by_ref["#7"]["signals"]["docs"] == ["docs/retries.md"]
    digest = Path(out["paths"]["digest"]).read_text(encoding="utf-8")
    assert "BREAKING?" in digest
    assert "+TIMEOUT_S = 5" in digest


def test_nothing_points_at_github_com():
    """A GHES repository must never produce a github.com URL, path or argument."""
    fake = gitflow_world()
    out = herald.collect(make_gh(fake), repo(), "v1.1.0", None, None)
    assert "github.com" not in json.dumps(out)
    assert all("github.com" not in " ".join(c) for c in fake.calls)
    assert out["compare_url"] == f"{URL}/compare/v1.0.0...v1.1.0"


def test_a_hotfix_compares_from_the_previous_tag():
    """A hotfix branches off the production branch, so there the previous tag is the closer start."""
    fake = gitflow_world()
    tags_route(fake, ["v1.1.1", "v1.1.0", "v1.0.0"])
    tag_route(fake, "v1.1.1", sha("c"))
    hotfix = pr(11, "Hotfix 1.1.1", base="main", head="hotfix/1.1.1", merge=sha("c"), head_oid=sha("k"))
    fake.assoc[sha("c")] = [hotfix]
    fake.assoc[sha("b")] = [fake.prs[10]]
    fix = pr(12, "Fix retry off-by-one", base="hotfix/1.1.1", merge=sha("6"), body="Retries ran one time too many.")
    fake.prs[12] = fix
    fake.assoc[sha("6")] = [fix, hotfix]
    compare_route(fake, sha("b"), sha("k"), [commit(sha("6"), "Fix retry off-by-one (#12)")])
    compare_route(fake, sha("h"), sha("k"), [], ahead=640)
    out = herald.collect(make_gh(fake), repo(), "v1.1.1", None, None)
    assert out["range"]["base"] == sha("b")
    assert [herald._item_ref(i) for i in out["items"]] == ["#12"]
    assert out["range"]["delta"] == "patch"


# --------------------------------------------------------------------------------------------
# The trunk world: direct commits, no PRs.
# --------------------------------------------------------------------------------------------


def trunk_world() -> FakeGh:
    fake = FakeGh()
    tags_route(fake, ["v0.2.0", "v0.1.0"])
    tag_route(fake, "v0.2.0", sha("d"))
    tag_route(fake, "v0.1.0", sha("e"))
    compare_route(
        fake,
        sha("e"),
        sha("d"),
        [
            commit(sha("1"), "plans: file the next idea"),
            commit(sha("2"), "Bump version: 0.1.0 → 0.2.0"),
            commit(sha("3"), "cli: add --dry-run\n\nPrints what would run."),
            commit(sha("4"), "Merge branch 'x'", parents=2),
            commit(sha("5"), "ci: pin actions"),
        ],
    )
    fake.rest[f"repos/acme/app/commits/{sha('3')}"] = {"files": [{"filename": "src/app/cli.py", "patch": "+x"}]}
    fake.rest[f"repos/acme/app/commits/{sha('5')}"] = {"files": [{"filename": ".github/workflows/ci.yml"}]}
    return fake


def test_trunk_goes_through_commits_and_warns_on_thin_messages():
    fake = trunk_world()
    out = herald.collect(make_gh(fake), repo(), "v0.2.0", None, None)
    assert out["flow"]["name"] == "trunk"
    assert out["source"] == "commits", "no commit maps to a PR, so auto falls back to commits"
    assert [i["title"] for i in out["items"]] == ["cli: add --dry-run"]
    reasons = sorted(e["reason"] for e in out["excluded"])
    assert reasons == ["merge commit", "title prefix 'plans:'", "touches only internal paths", "version bump"]
    assert out["quality"]["level"] == "low"
    summary = herald.render_summary(out)
    assert "WARNING:   low signal" in summary
    assert out["items"][0]["signals"]["surface"] == ["src/app/cli.py"]


def test_a_first_release_asks_for_a_previous_tag():
    fake = FakeGh()
    tags_route(fake, ["v0.1.0"])
    tag_route(fake, "v0.1.0", sha("e"))
    with pytest.raises(herald.HeraldError, match="--previous"):
        herald.collect(make_gh(fake), repo(), "v0.1.0", None, None)


def test_a_tag_missing_on_the_remote_is_refused_by_name():
    with pytest.raises(herald.HeraldError, match="never creates one"):
        herald.collect(make_gh(FakeGh()), repo(), "v9.9.9", "v9.9.8", None)


# --------------------------------------------------------------------------------------------
# Pieces.
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("https://ghes.example/acme/app", "ghes.example/acme/app"),
        ("https://ghes.example/acme/app.git", "ghes.example/acme/app"),
        ("git@ghes.example:acme/app.git", "ghes.example/acme/app"),
        ("ssh://git@ghes.example/acme/app", "ghes.example/acme/app"),
        ("ghes.example/acme/app", "ghes.example/acme/app"),
        ("acme/app", "acme/app"),
    ],
)
def test_every_spelling_of_a_repository_normalises(spec, expected):
    assert herald.normalise_repo_spec(spec) == expected


def test_the_host_comes_from_the_repository_url():
    resolved = herald.resolve_repo(make_gh(FakeGh()), "git@ghes.example:acme/app.git")
    assert (resolved.host, resolved.slug, resolved.full) == (HOST, "acme/app", "ghes.example/acme/app")


@pytest.mark.parametrize(
    ("current", "tags", "expected"),
    [
        ("v1.2.0", ["v1.2.0rc2", "v1.2.0rc1", "v1.1.3", "v1.1.0"], "v1.1.3"),
        ("v1.2.0rc2", ["v1.2.0rc1", "v1.1.3"], "v1.2.0rc1"),
        ("v1.2.0-rc.1", ["v1.1.3", "v1.2.0-beta.4"], "v1.2.0-beta.4"),
        ("api-v2.0.0", ["v9.0.0", "api-v1.4.0", "api-v1.10.0"], "api-v1.10.0"),
        ("v2026.11.02", ["v2026.10.28", "v2026.10.28.1"], "v2026.10.28.1"),
    ],
)
def test_the_previous_release_is_chosen_by_version(current, tags, expected):
    found = herald.previous_version(herald.parse_version(current), tags)
    assert found is not None
    assert found.tag == expected


@pytest.mark.parametrize(
    ("current", "previous", "delta"),
    [("v2.0.0", "v1.9.9", "major"), ("v1.3.0", "v1.2.4", "minor"), ("v1.2.5", "v1.2.4", "patch")],
)
def test_version_delta(current, previous, delta):
    assert herald.version_delta(herald.parse_version(current), herald.parse_version(previous)) == delta


def test_a_pr_template_left_unfilled_counts_as_empty():
    template = """<!-- Describe your change -->
## Summary

## Checklist
- [ ] Tests added
- [x] Docs updated

https://ghes.example/acme/app/issues/1
"""
    assert herald.informative_words(template) == 0
    assert herald.grade(0) == "empty"
    assert herald.grade(herald.ADEQUATE_MIN_WORDS - 1) == "thin"
    assert herald.grade(herald.RICH_MIN_WORDS) == "rich"


# --------------------------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------------------------


GOOD_NOTES = f"""Adds bounded retries; `timeout` is now in seconds.
1 change requires action — see below.

## ⚠ Action required

### Breaking changes

**`timeout` is now in seconds** ([#9]({URL}/pull/9))
Previously milliseconds. Now seconds. To migrate, divide by 1000.

## Highlights

### Bounded retries

Pass `max_retries=` to `submit()`.

## All changes

### Features

- Added `max_retries` to `submit()` ([#7]({URL}/pull/7), @alice)
- **Breaking:** `timeout` is now in seconds ([#9]({URL}/pull/9), @bob)

### Fixes

- Fixed a crash on an empty config file ([{sha("4")[:7]}]({URL}/commit/{sha("4")}))

**Full Changelog**: [v1.0.0...v1.1.0]({URL}/compare/v1.0.0...v1.1.0)
"""


@pytest.fixture
def collected():
    return herald.collect(make_gh(gitflow_world()), repo(), "v1.1.0", None, None)


def levels(findings) -> list[tuple[str, str]]:
    return [(f.level, f.message) for f in findings]


def test_good_notes_are_clean(collected):
    assert levels(herald.check_notes(GOOD_NOTES, collected)) == []


def test_a_missing_item_is_an_error_unless_dropped(collected):
    notes = GOOD_NOTES.replace(f"- Added `max_retries` to `submit()` ([#7]({URL}/pull/7), @alice)\n", "")
    errors = [m for lvl, m in levels(herald.check_notes(notes, collected)) if lvl == "error"]
    assert errors == ["#7 (Add max_retries to submit) is neither in the notes nor in --dropped"]
    assert herald.check_notes(notes, collected, dropped=["7"]) == []


def test_a_link_to_the_wrong_host_is_an_error(collected):
    notes = GOOD_NOTES.replace(f"{URL}/pull/7", "https://github.com/acme/app/pull/7")
    errors = [m for lvl, m in levels(herald.check_notes(notes, collected)) if lvl == "error"]
    assert any("github.com" in e for e in errors)


@pytest.mark.parametrize(
    ("edit", "expected"),
    [
        (lambda t: t.replace(f"[#7]({URL}/pull/7)", f"[PR 7]({URL}/pull/7)"), "link text should be just `#7`"),
        (lambda t: t + "\nSee #7.\n", "bare `#7`"),
        (lambda t: t.replace("**Full Changelog**", "Full").replace("/compare/", "/tree/"), "no compare link"),
        (lambda t: t.replace(f"([#9]({URL}/pull/9))\nPreviously", "\nPreviously"), "#9 carries a breaking signal"),
    ],
)
def test_warnings(collected, edit: Callable[[str], str], expected):
    messages = [m for _, m in levels(herald.check_notes(edit(GOOD_NOTES), collected))]
    assert any(expected in m for m in messages), messages


def test_an_empty_section_is_an_error(collected):
    notes = GOOD_NOTES.replace("## Highlights", "### Deprecations\n\n## Highlights")
    assert ("error", "section `Deprecations` is empty; omit it") in levels(herald.check_notes(notes, collected))


# --------------------------------------------------------------------------------------------
# publish
# --------------------------------------------------------------------------------------------


def test_publish_creates_a_draft_naming_the_host_and_verifying_the_tag(tmp_path):
    fake = gitflow_world()
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    herald.publish(make_gh(fake), repo(), herald.PublishRequest("v1.1.0", notes))
    assert fake.release_args is not None
    args = fake.release_args
    assert args[:5] == ["release", "create", "v1.1.0", "-R", "ghes.example/acme/app"]
    assert "--verify-tag" in args
    assert "--draft" in args
    assert "--prerelease" not in args


def test_publish_live_and_prerelease(tmp_path):
    fake = gitflow_world()
    tag_route(fake, "v1.1.0rc1", sha("f"))
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    herald.publish(make_gh(fake), repo(), herald.PublishRequest("v1.1.0rc1", notes, live=True))
    assert fake.release_args is not None
    assert "--draft" not in fake.release_args
    assert "--prerelease" in fake.release_args


def test_publish_refuses_an_existing_release_and_updates_on_request(tmp_path):
    fake = gitflow_world()
    fake.releases.add("v1.1.0")
    notes = tmp_path / "notes.md"
    notes.write_text("x", encoding="utf-8")
    with pytest.raises(herald.HeraldError, match="--update"):
        herald.publish(make_gh(fake), repo(), herald.PublishRequest("v1.1.0", notes))
    herald.publish(make_gh(fake), repo(), herald.PublishRequest("v1.1.0", notes, update=True))
    assert fake.release_args is not None
    assert fake.release_args[:2] == ["release", "edit"]


def test_publish_runs_the_check_first(tmp_path, capsys):
    fake = gitflow_world()
    gh = make_gh(fake)
    herald.collect(gh, repo(), "v1.1.0", None, None)
    notes = tmp_path / "notes.md"
    notes.write_text("Nothing here.\n", encoding="utf-8")
    code = herald.main(["publish", "--tag", "v1.1.0", "--notes-file", str(notes)], gh=gh)
    assert code == 1
    assert fake.release_args is None
    assert "refusing to publish" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# setup: workflow clues
# --------------------------------------------------------------------------------------------

RELEASE_WORKFLOW = """name: release
on:
  push:
    tags: ["v*"]
jobs:
  pypi:
    environment:
      name: pypi
      url: https://pypi.corp.example/project/app/
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://artifactory.corp.example/api/pypi/pypi-local
  image:
    env:
      JF_URL: https://artifactory.corp.example
    steps:
      - uses: docker/metadata-action@v5
        with:
          images: |
            artifactory.corp.example/docker-local/app
      - run: jf rt upload dist/app.tar.gz generic-local/app/${{ github.ref_name }}/
      - run: inv dist.publish --index internal
"""

CI_WORKFLOW = """name: ci
on:
  pull_request:
jobs:
  release:
    steps:
      - run: docker push should.not.count/app
"""


def test_a_release_workflow_yields_destinations_on_any_registry():
    clues = herald.scan_workflow(".github/workflows/release.yml", RELEASE_WORKFLOW)
    found = {(c.kind, c.destination) for c in clues}
    assert ("deployment", "https://pypi.corp.example/project/app/") in found
    assert ("pypi", "https://artifactory.corp.example/api/pypi/pypi-local") in found
    assert ("artifactory", "https://artifactory.corp.example") in found
    assert ("docker", "artifactory.corp.example/docker-local/app") in found
    assert ("artifactory", "generic-local/app/${{ github.ref_name }}/") in found, "an expression is one token"
    assert any(c.kind == "task" and c.destination and "dist.publish" in c.destination for c in clues)
    assert {c.job for c in clues} >= {"pypi", "image"}


def test_triggers_read_the_on_block_not_a_job_named_release():
    assert herald.workflow_triggers(RELEASE_WORKFLOW) == ["push", "push-tags"]
    assert herald.workflow_triggers(CI_WORKFLOW) == ["pull_request"]


def test_only_release_workflows_propose_artifacts():
    ctx = herald.SetupContext(
        repo=repo(),
        variables={},
        previous=herald.parse_version("v1.0.0"),
        triggers={
            "rel.yml": herald.workflow_triggers(RELEASE_WORKFLOW),
            "ci.yml": herald.workflow_triggers(CI_WORKFLOW),
        },
        called=set(),
        deployments={"https://pypi.corp.example/project/app/": "pypi"},
    )
    clues = herald.scan_workflow("rel.yml", RELEASE_WORKFLOW) + herald.scan_workflow("ci.yml", CI_WORKFLOW)
    artifacts, _ = herald.propose_artifacts(clues, ctx)
    assert all(a["workflow"] == "rel.yml" for a in artifacts)
    seen = [a for a in artifacts if a["confidence"] == "seen-in-run"]
    assert [a["destination"] for a in seen] == ["https://pypi.corp.example/project/app/"]
    task = next(a for a in artifacts if a["kind"] == "task")
    assert task["destination"] == "", "a task runner's command is not a place"
    assert any("dist.publish" in e for e in task["evidence"])
    assert any("ask the user" in e for e in task["evidence"])


def test_a_destination_is_templated_on_the_previous_version():
    out = herald.resolve_expression(
        "registry.corp/app:1.0.0 and ${{ github.ref_name }} and ${{ secrets.X }}",
        repo(),
        {},
        herald.parse_version("v1.0.0"),
    )
    assert out == "registry.corp/app:{version} and {tag} and ${{ secrets.X }}"


# --------------------------------------------------------------------------------------------
# Config: keyed by URL, the Linux layout everywhere.
# --------------------------------------------------------------------------------------------


def test_config_is_keyed_by_host_and_lives_under_dot_config(sandboxed_home):
    home = sandboxed_home
    assert herald.config_path(repo()) == home / ".config" / "release-herald" / "repos" / HOST / "acme" / "app.toml"
    assert herald.repo_cache_dir(repo()) == home / ".cache" / "release-herald" / HOST / "acme" / "app"
    assert herald.repo_state_dir(repo()) == home / ".local" / "state" / "release-herald" / HOST / "acme" / "app"


def test_xdg_variables_win(sandboxed_home, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(sandboxed_home / "cfg"))
    assert herald.config_root() == sandboxed_home / "cfg" / "release-herald"


def test_setup_accept_validates_and_writes(tmp_path):
    proposal = tmp_path / "p.toml"
    proposal.write_text(f'url = "{URL}"\nflow = "gitflow"\n\n[[artifacts]]\nkind = "docker"\n', encoding="utf-8")
    written = herald.accept_proposal(repo(), proposal)
    assert written == herald.config_path(repo())
    config = herald.load_config(repo())
    assert config.flow == "gitflow"
    assert config.artifacts == [{"kind": "docker"}]

    proposal.write_text('url = "https://elsewhere.example/x/y"\n', encoding="utf-8")
    with pytest.raises(herald.HeraldError, match="url must be"):
        herald.accept_proposal(repo(), proposal)
    proposal.write_text(f'url = "{URL}"\nflow = "trunkish"\n', encoding="utf-8")
    with pytest.raises(herald.HeraldError, match="flow must be"):
        herald.accept_proposal(repo(), proposal)


def test_a_workflow_change_after_setup_is_reported(tmp_path):
    """The artifact answer was derived from specific workflow files; once they change it may be wrong."""
    fake = gitflow_world()
    fake.rest["repos/acme/app/contents/.github/workflows?ref=main"] = [
        {"name": "release.yml", "path": ".github/workflows/release.yml", "sha": "new"}
    ]
    proposal = tmp_path / "p.toml"
    proposal.write_text(f'url = "{URL}"\nworkflow_digest = "from-an-older-tree"\n', encoding="utf-8")
    herald.accept_proposal(repo(), proposal)
    out = herald.collect(make_gh(fake), repo(), "v1.1.0", None, None)
    assert out["config"]["stale"] is True
    assert "re-run `setup`" in herald.render_summary(out)


def test_configured_flow_overrides_detection(tmp_path):
    proposal = tmp_path / "p.toml"
    proposal.write_text(f'url = "{URL}"\nflow = "trunk"\n', encoding="utf-8")
    herald.accept_proposal(repo(), proposal)
    flow = herald.detect_flow(make_gh(gitflow_world()), repo(), herald.load_config(repo()))
    assert flow.name == "trunk"
    assert "set in" in flow.evidence


# --------------------------------------------------------------------------------------------
# The standalone prompt says what the script does.
# --------------------------------------------------------------------------------------------

PROMPT = (SKILL_DIR / "references" / "prompt.md").read_text(encoding="utf-8")


def _squash(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.parametrize("name", ["ASSOCIATED_PR_FIELDS", "PR_FIELDS"])
def test_the_prompt_quotes_the_scripts_graphql_verbatim(name):
    """A reader without the skill runs the same query the script does, or the two silently diverge."""
    assert _squash(getattr(herald, name)) in _squash(PROMPT)


def test_the_prompt_states_the_scripts_thresholds():
    rows = re.findall(r"^\|\s*(empty|thin|adequate|rich)\s*\|\s*([^|]+?)\s*\|", PROMPT, re.MULTILINE)
    table = dict(rows)
    dash = "\N{EN DASH}"  # the prompt's typography; spelled out so the linter does not read it as a hyphen
    assert table["thin"] == f"{herald.THIN_MIN_WORDS}{dash}{herald.ADEQUATE_MIN_WORDS - 1}"
    assert table["adequate"] == f"{herald.ADEQUATE_MIN_WORDS}{dash}{herald.RICH_MIN_WORDS - 1}"
    assert table["rich"] == f"{herald.RICH_MIN_WORDS} or more"
    assert herald.LOW_SIGNAL_SHARE == 0.5
    assert "**half or more**" in PROMPT
    assert herald.MIXED_SIGNAL_SHARE == 0.25
    assert "a quarter or more" in PROMPT
