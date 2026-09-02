"""Dependency-health measurement for `skills/research-library/scripts/package_health.py`.

Every input to that script is a network response, so the fetch layer is a seam and everything here
drives it from fixtures captured once from the real PyPI and GitHub APIs and trimmed to the fields
the script reads. **No test may reach the network**, and that is asserted rather than intended: the
autouse fixture below replaces the two ways out and fails the test if either is called.

The tests that matter are one per trap in the plan this came from, because each of those traps
produced a wrong number in a real comparison before it was known.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "research-library" / "scripts" / "package_health.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "package_health"

# Every fixture was captured on this day, so `now` is pinned to it and the cadence numbers below are
# stable. A test whose expected value moves with the wall clock is a test nobody trusts.
CAPTURED = datetime(2026, 9, 2, tzinfo=UTC)


def _load():
    spec = importlib.util.spec_from_file_location("package_health_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


health = _load()


def fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """The requirement, enforced. `uv run --with` and an active venv both make "is it absent?"
    answerable the wrong way, so the check is not "is the network configured" but "was it used"."""

    def refuse(*args, **kwargs):
        raise AssertionError(f"a test reached the network: {args!r} {kwargs!r}")

    monkeypatch.setattr(health.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(health.subprocess, "run", refuse)


class FakeTransport:
    """The captured responses, keyed the way the script asks for them."""

    def __init__(self, pypi_payload=None, github_payloads=None):
        self.pypi_payload: object = pypi_payload if pypi_payload is not None else fixture("httpx-pypi")
        self.github_payloads: dict[str, object] = github_payloads or {}
        self.asked: list[str] = []

    def pypi(self, name: str):
        self.asked.append(f"pypi:{name}")
        return self.pypi_payload

    def github(self, path: str):
        self.asked.append(path)
        for prefix, payload in self.github_payloads.items():
            if path.startswith(prefix):
                return payload
        return []


def httpx_transport():
    return FakeTransport(
        github_payloads={
            "repos/encode/httpx/commits": fixture("httpx-commits"),
            "repos/encode/httpx/issues": fixture("httpx-issues"),
            "repos/encode/httpx": fixture("httpx-repo"),
        }
    )


# ------------------------------------------------------------------------------------------------
# PyPI


def test_a_versions_date_is_its_earliest_upload_not_its_latest():
    """A version's files are uploaded at slightly different moments and the max drifts the cadence.

    Real capture: httpx 0.10.0's two files are 2.4 seconds apart, which is the small version of a
    gap that reaches days when a build is retried the next morning.
    """
    dates = health.release_dates(fixture("httpx-pypi"))
    assert dates["0.10.0"] == datetime.fromisoformat("2019-12-29T17:02:14.432949Z")


def test_a_version_with_no_files_is_not_a_release_date():
    """httpx 0.0.1 has an empty file list — a version that exists in the index and never shipped."""
    dates = health.release_dates(fixture("httpx-pypi"))
    assert "0.0.1" not in dates


def test_a_version_is_yanked_only_when_every_one_of_its_files_is():
    payload = {
        "releases": {
            "1.0": [{"yanked": True}, {"yanked": True}],
            "1.1": [{"yanked": True}, {"yanked": False}],
            "1.2": [{"yanked": False}],
        }
    }
    assert health.yanked_versions(payload) == ["1.0"]


def test_cadence_takes_its_median_over_recent_releases_not_the_whole_history():
    """A project's first year says nothing about whether anyone is looking after it now."""
    # Eleven releases: one ancient one six years back, then ten spaced ten days apart.
    start = datetime(2026, 1, 1, tzinfo=UTC)
    dates = {"0.1": datetime(2020, 1, 1, tzinfo=UTC)}
    dates |= {f"1.{index}": start + timedelta(days=10 * index) for index in range(10)}
    pace = health.cadence(dates, [], now=CAPTURED)
    assert pace.releases == 11
    assert pace.median_gap_days == 10.0


@pytest.mark.parametrize("version", ["1.0.dev6", "1.0a1", "1.0b2", "1.0rc1", "2.0.0-beta.1", "1.0.dev0"])
def test_a_pre_release_is_recognised_by_its_pep440_spelling(version):
    assert health.is_prerelease(version)


@pytest.mark.parametrize("version", ["0.28.1", "1.0", "1.0.post1", "2.0.0", "1.2.3.4"])
def test_a_real_release_including_a_post_release_is_not_a_pre_release(version):
    assert not health.is_prerelease(version)


def test_a_moving_dev_line_is_not_a_moving_stable_line():
    """Confirmed 2026-09-02 on the real httpx capture: the three most recent uploads are 1.0.dev4,
    1.0.dev5 and 1.0.dev6. Counting them gives "4 releases in the last year, last one 1 day ago"
    for a project whose stable line stopped in 2024 — the single most misleading number this script
    could print, because it inverts the answer to "is this maintained for me"."""
    payload = fixture("httpx-pypi")
    pace = health.cadence(health.release_dates(payload), [], now=CAPTURED)
    assert pace.stable_only is True
    assert pace.last_release == "2024-12-06"
    assert pace.in_last_year == 0
    assert pace.prereleases == 9
    assert pace.last_prerelease == "2026-08-31"


def test_a_project_that_has_only_ever_shipped_pre_releases_is_measured_on_them_and_says_so():
    """Reporting zero releases for something that plainly has some would be the worse answer."""
    dates = {"0.1.dev1": datetime(2026, 1, 1, tzinfo=UTC), "0.1.dev2": datetime(2026, 2, 1, tzinfo=UTC)}
    pace = health.cadence(dates, [], now=CAPTURED)
    assert pace.stable_only is False
    assert pace.releases == 2


def test_cadence_survives_a_package_with_no_dated_release():
    pace = health.cadence({}, [], now=CAPTURED)
    assert pace.releases == 0
    assert pace.median_gap_days is None
    assert pace.days_since_last is None


def test_runtime_requirements_drop_everything_gated_on_an_extra():
    """The extras dominate the raw list and are not what a plain install pulls in.

    Real capture: httpx declares 12 `requires_dist` entries, of which 4 are unconditional. Reporting
    12 overstates what the consumer inherits by three times.
    """
    payload = fixture("httpx-pypi")
    assert len(payload["info"]["requires_dist"]) == 12
    runtime = health.runtime_requirements(payload)
    assert health.requirement_names(runtime) == ["anyio", "certifi", "httpcore", "idna"]


def test_a_platform_marker_is_not_an_extra_marker():
    """`platform_python_implementation == "CPython"` alone is a runtime dependency, conditionally."""
    payload = {"info": {"requires_dist": ['tomli; python_version < "3.11"', 'rich; extra == "cli"']}}
    assert health.runtime_requirements(payload) == ['tomli; python_version < "3.11"']


# ------------------------------------------------------------------------------------------------
# GitHub


def test_a_bot_never_counts_toward_the_human_contributor_picture():
    """Measured 2026-08-30: `renovate[bot]` was 70% of one project's commits over a year, which
    reads as a catastrophic bus factor and is dependency bumps. Excluding bots reversed the
    finding. Real capture: `dependabot[bot]` is the second-largest committer in this window."""
    people = health.contributors(fixture("httpx-commits"), truncated=False)
    logins = [login for login, _ in people.humans]
    assert "dependabot[bot]" not in logins
    assert ("dependabot[bot]", 13) in people.bots
    assert people.humans[0][0] == "lovelydinosaur"


@pytest.mark.parametrize(
    ("logins", "expected"),
    [
        (["solo"] * 10, 1),
        (["a"] * 6 + ["b"] * 4, 1),
        (["a"] * 3 + ["b"] * 3 + ["c"] * 3, 2),
        ([], 0),
    ],
)
def test_bus_factor_is_how_many_humans_cover_half_the_commits(logins, expected):
    commits = [{"author": {"login": login}} for login in logins]
    assert health.contributors(commits, truncated=False).bus_factor == expected


def test_a_commit_github_cannot_match_to_an_account_is_still_a_person():
    commits = [{"author": None, "commit": {"author": {"name": "Ada Lovelace"}}}]
    people = health.contributors(commits, truncated=False)
    assert people.humans == [("Ada Lovelace", 1)]


@pytest.mark.parametrize(
    "login",
    ["dependabot[bot]", "renovate[bot]", "pre-commit-ci[bot]", "github-actions[bot]", "snyk-bot", "some-bot"],
)
def test_the_bot_filter_covers_the_automation_that_actually_shows_up(login):
    assert health.is_bot(login)


@pytest.mark.parametrize("login", ["robotwitch", "abbot", "botanist"])
def test_the_bot_filter_does_not_eat_a_human_whose_name_contains_bot(login):
    assert not health.is_bot(login)


def test_the_close_time_median_ignores_pull_requests():
    """PRs close on a different rhythm and would flatter a project that merges fast and answers
    issues slowly. GitHub returns both from the issues endpoint; only PRs carry `pull_request`."""
    items = [
        {"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-01-11T00:00:00Z"},
        {"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-01-21T00:00:00Z"},
        {"created_at": "2026-01-01T00:00:00Z", "closed_at": "2026-01-02T00:00:00Z", "pull_request": {}},
    ]
    sample = health.issue_sample(items)
    assert sample.median_days == 15.0
    assert (sample.sampled, sample.issues) == (3, 2)


def test_a_sample_of_fifty_closed_items_can_hold_no_issues_at_all():
    """Confirmed 2026-09-02 against `encode/httpx`: 300 closed items across three pages contained
    zero issues. A bare `None` there is indistinguishable from a project that closes nothing, so
    the sample size travels with the median."""
    sample = health.issue_sample(fixture("httpx-issues"))
    assert sample.sampled == 50
    assert sample.issues == 0
    assert sample.median_days is None


def test_a_project_whose_tracker_is_used_yields_a_median_from_a_thin_slice():
    """Real capture: 4 issues among `pallets/click`'s 50 most recently closed items. The metric is
    obtainable and the sample it rests on is small, which is exactly what the report has to say."""
    sample = health.issue_sample(fixture("click-issues"))
    assert sample.sampled == 50
    assert sample.issues == 4
    assert sample.median_days is not None


def test_the_repository_reports_its_licence_field_and_flags_no_assertion():
    repo = health.repository(fixture("httpx-repo"), now=CAPTURED)
    assert repo.full_name == "encode/httpx"
    assert repo.archived is False
    assert repo.license_field == "BSD-3-Clause"
    assert repo.days_since_push is not None
    assert health.repository({"license": {"spdx_id": "NOASSERTION"}}, now=CAPTURED).license_field is None


def test_open_issues_count_is_pull_requests_on_a_repo_with_no_issue_tracker():
    """Confirmed 2026-09-02: `encode/httpx` reports `has_issues: false` and `open_issues_count:
    143`, every one of which is a pull request. Scoring "open issues relative to project size" off
    that number compares a review backlog against a support backlog."""
    repo = health.repository(fixture("httpx-repo"), now=CAPTURED)
    assert repo.has_issues is False
    assert repo.open_issues > 0
    assert health.repository(fixture("click-repo"), now=CAPTURED).has_issues is True


def test_a_payload_that_omits_has_issues_is_read_as_having_one():
    """The field is absent from some responses, and a tracker is the default state of a repo."""
    assert health.repository({}, now=CAPTURED).has_issues is True


# ------------------------------------------------------------------------------------------------
# The clone


def make_clone(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_a_generated_layer_is_segmented_out_before_the_ratio_is_taken(tmp_path):
    """Measured 2026-08-30: a candidate looked like 0.28 against a peer's 0.81 until 71% of its
    source turned out to be one-class-per-API-object binding modules. Against hand-written code it
    was 1.07 — better than the peer rather than a third as good."""
    make_clone(
        tmp_path,
        {
            "pkg/core.py": "x\n" * 100,
            "pkg/types/generated_a.py": "y\n" * 700,
            "pkg/types/generated_b.py": "y\n" * 200,
            "tests/test_core.py": "z\n" * 100,
        },
    )
    raw = health.sources(tmp_path, [])
    assert raw.raw_ratio == 0.1  # 100 test lines against 1000 "source" lines

    segmented = health.sources(tmp_path, ["pkg/types/generated_*.py"])
    assert segmented.generated_lines == 900
    assert segmented.handwritten_ratio == 1.0  # 100 against the 100 that were written by hand


def test_every_licence_file_is_listed_because_the_api_field_reports_only_one(tmp_path):
    """Confirmed 2026-08-30: the API said `GPL-3.0` for a project shipping three licence files, one
    of which says either may be chosen. Taking the field at face value would have disqualified it."""
    make_clone(tmp_path, {"LICENSE": "gpl", "LICENSE.lesser": "lgpl", "LICENSE.dual": "either", "README.md": "x"})
    assert health.license_files(tmp_path) == ["LICENSE", "LICENSE.dual", "LICENSE.lesser"]


def test_clone_facts_find_py_typed_the_ci_inventory_and_the_type_config(tmp_path):
    make_clone(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/py.typed": "",
            "pyproject.toml": "[tool.mypy]\nstrict = true\n",
            ".github/workflows/test.yml": "on: push",
            ".github/workflows/publish.yaml": "on: release",
            "LICENSE": "mit",
        },
    )
    facts = health.clone_facts(tmp_path, [])
    assert facts.py_typed is True
    assert facts.workflows == ["publish.yaml", "test.yml"]
    assert facts.type_checker_configs == ["[tool.mypy]"]
    assert facts.shallow is False


def test_a_shallow_clone_says_so_because_history_questions_need_a_deepen(tmp_path):
    """`git log -p -- pyproject.toml` on a depth-1 clone returns one commit and looks like a project
    that has never changed its pins — which is exactly the wrong answer to constraint archaeology."""
    make_clone(tmp_path, {".git/shallow": "abc123\n", "pkg/__init__.py": ""})
    assert health.clone_facts(tmp_path, []).shallow is True


def test_a_clone_path_that_is_not_a_directory_is_the_callers_error(tmp_path):
    with pytest.raises(health.HealthError, match="is not a directory"):
        health.clone_facts(tmp_path / "nope", [])


# ------------------------------------------------------------------------------------------------
# The whole answer


def test_gather_assembles_one_candidate_from_the_captured_responses():
    transport = httpx_transport()
    result = health.gather(transport, "httpx", "encode/httpx", now=CAPTURED)

    assert result.name == "httpx"
    assert result.repository is not None
    assert result.repository.full_name == "encode/httpx"
    assert result.contributors is not None
    assert result.contributors.human_count > 0
    assert health.requirement_names(result.runtime_requirements) == ["anyio", "certifi", "httpcore", "idna"]
    # The commit window is asked for by date and by page, so the bound is visible in the calls.
    assert any(path.startswith("repos/encode/httpx/commits?since=") for path in transport.asked)


def test_gather_without_a_repo_answers_from_pypi_alone():
    transport = FakeTransport()
    result = health.gather(transport, "httpx", None, now=CAPTURED)
    assert result.repository is None
    assert result.contributors is None
    assert transport.asked == ["pypi:httpx"]


def test_a_repo_with_no_tracker_is_never_asked_for_its_closed_issues():
    transport = httpx_transport()
    result = health.gather(transport, "httpx", "encode/httpx", now=CAPTURED)
    assert result.issues is None
    assert not any("issues" in path for path in transport.asked)


def test_the_report_names_what_it_refuses_to_score():
    rendered = health.render(health.gather(httpx_transport(), "httpx", "encode/httpx", now=CAPTURED))
    assert "not scored" in rendered
    assert "stars" in rendered
    assert "verify against the files" in rendered  # the licence field is never the answer
    assert "GitHub counts both" in rendered  # open_issues_count is issues plus PRs
    assert "DISABLED" in rendered  # …and httpx has no tracker at all
    assert "not counted above" in rendered  # the dev line is beside the stable line, not inside it


def test_the_report_says_why_a_median_is_missing_rather_than_printing_a_question_mark():
    repo = health.repository(fixture("click-repo"), now=CAPTURED)
    all_prs = health.IssueSample(sampled=50, issues=0, median_days=None)
    assert "all pull requests" in health._issue_line(repo, all_prs)
    real = health.issue_sample(fixture("click-issues"))
    assert "of 50 sampled" in health._issue_line(repo, real)


def test_the_json_payload_carries_the_derived_numbers_not_just_the_fields():
    payload = health.payload_of(health.gather(httpx_transport(), "httpx", "encode/httpx", now=CAPTURED))
    assert payload["contributors"]["bus_factor"] >= 1
    assert payload["contributors"]["human_count"] >= 1
    assert json.dumps(payload, default=str)  # the whole thing has to survive a dump


def test_main_reports_a_bad_name_as_the_callers_error(capsys):
    class Refusing:
        def pypi(self, name):
            raise health.HealthError(f"PyPI returned 404 for {name!r}")

        def github(self, path):
            raise AssertionError("never reached")

    assert health.main(["no-such-distribution-xyz"], transport=Refusing()) == 1
    assert "404" in capsys.readouterr().err
