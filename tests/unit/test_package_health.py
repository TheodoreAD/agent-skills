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

    def __init__(self, pypi_payload=None, github_payloads=None, npm_payloads=None):
        self.pypi_payload: object = pypi_payload if pypi_payload is not None else fixture("httpx-pypi")
        self.github_payloads: dict[str, object] = github_payloads or {}
        self.npm_payloads: dict[str, object] = npm_payloads or {}
        self.asked: list[str] = []

    def npm(self, name: str):
        """A name with no captured packument is npm's 404, which is how `@types/<name>` is absent."""
        self.asked.append(f"npm:{name}")
        if name not in self.npm_payloads:
            raise health.NotFound(f"npm returned 404 for {name!r} — check the name")
        return self.npm_payloads[name]

    def pypi(self, name: str):
        self.asked.append(f"pypi:{name}")
        return self.pypi_payload

    def github(self, path: str):
        self.asked.append(path)
        for prefix, payload in self.github_payloads.items():
            if path.startswith(prefix):
                return payload
        return []

    def machine(self):
        return MACHINE


# A fixed machine, so a floor's verdict does not move with whoever runs the suite. The values are
# this repo's development machine on 2026-09-27 (Ubuntu 24.04's glibc), with node left unset so
# the not-compared path is the default one a test sees.
MACHINE = health.Machine(python="3.12.3", glibc="2.39", node=None)


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
# PyPI: what a release ships. `shellcheck-py` is the capture: a binary wrapper whose wheels carry
# the upstream executable, recorded 2026-09-27 and trimmed to the fields the script reads.


def test_the_latest_stable_release_is_what_pypi_itself_resolves_to():
    assert health.latest_stable_version(fixture("shellcheck-py-pypi")) == "0.11.0.1"
    # httpx's info.version is the stable 0.28.1 even though 1.0.devN uploads are newer.
    assert health.latest_stable_version(fixture("httpx-pypi")) == "0.28.1"


def test_a_pre_release_info_version_falls_back_to_the_newest_stable_by_date():
    payload = {
        "info": {"version": "2.0rc1"},
        "releases": {
            "1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}],
            "2.0rc1": [{"upload_time_iso_8601": "2026-02-01T00:00:00Z"}],
        },
    }
    assert health.latest_stable_version(payload) == "1.0"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("shellcheck_py-0.11.0.1-py2.py3-none-win_amd64.whl", ("py2.py3", "none", "win_amd64")),
        ("pkg-1.0-1build-cp312-cp312-manylinux_2_17_x86_64.whl", ("cp312", "cp312", "manylinux_2_17_x86_64")),
        ("httpx-0.28.1-py3-none-any.whl", ("py3", "none", "any")),
        ("shellcheck_py-0.11.0.1.tar.gz", None),
    ],
)
def test_wheel_tags_are_the_last_three_fields_of_the_filename(filename, expected):
    assert health.wheel_tags(filename) == expected


def test_a_binary_wrapper_ships_a_linux_x86_64_wheel_and_says_so():
    """Real capture: shellcheck-py 0.11.0.1 is four platform wheels and a 3 kB sdist. The manylinux
    wheel carries the executable, so a Linux x86_64 install downloads 3.8 MB and fetches nothing."""
    ships = health.release_files(fixture("shellcheck-py-pypi"))
    assert ships.version == "0.11.0.1"
    assert (ships.wheels, ships.sdists) == (4, 1)
    assert ships.linux_x86_64_wheels == [
        "shellcheck_py-0.11.0.1-py2.py3-none-manylinux1_x86_64.manylinux2014_x86_64"
        ".manylinux_2_17_x86_64.manylinux_2_5_x86_64.whl"
    ]
    assert ships.platform_specific is True
    assert ships.pure_python is False
    assert ships.sdist_only is False
    assert ships.largest == "shellcheck_py-0.11.0.1-py2.py3-none-macosx_11_0_arm64.whl"
    assert ships.largest_size == 11381835


def test_an_sdist_only_release_is_flagged_as_building_or_fetching_at_install():
    """Real capture: shellcheck-py 0.9.0.3 shipped one sdist and no wheels, so installing that
    version on any machine ran its build hook, which is where the binary would have been fetched."""
    ships = health.release_files(fixture("shellcheck-py-pypi"), "0.9.0.3")
    assert ships.sdist_only is True
    assert ships.linux_x86_64_wheels == []
    rendered = "\n".join(health._release_file_lines(ships))
    assert "SDIST ONLY" in rendered


def test_a_pure_python_wheel_installs_anywhere():
    payload = {
        "info": {"version": "1.0"},
        "releases": {
            "1.0": [
                {"filename": "pkg-1.0-py3-none-any.whl", "packagetype": "bdist_wheel", "size": 1000},
                {"filename": "pkg-1.0.tar.gz", "packagetype": "sdist", "size": 900},
            ]
        },
    }
    ships = health.release_files(payload)
    assert ships.pure_python is True
    assert ships.platform_specific is False
    assert "pure-Python wheel" in "\n".join(health._release_file_lines(ships))


def test_platform_wheels_that_miss_this_machine_say_the_sdist_is_the_fallback():
    payload = {
        "info": {"version": "1.0"},
        "releases": {
            "1.0": [
                {"filename": "pkg-1.0-py3-none-macosx_11_0_arm64.whl", "packagetype": "bdist_wheel", "size": 5},
                {"filename": "pkg-1.0-py3-none-manylinux_2_17_aarch64.whl", "packagetype": "bdist_wheel", "size": 5},
                {"filename": "pkg-1.0.tar.gz", "packagetype": "sdist", "size": 1},
            ]
        },
    }
    ships = health.release_files(payload)
    assert ships.linux_x86_64_wheels == []
    assert "NO WHEEL for this machine" in "\n".join(health._release_file_lines(ships))


def test_a_long_file_list_keeps_this_machines_wheels_and_the_sdist_and_counts_the_rest():
    wheels = [
        {"filename": f"pkg-1.0-cp3{minor}-cp3{minor}-{plat}.whl", "packagetype": "bdist_wheel", "size": 10}
        for minor in range(10, 15)
        for plat in ("macosx_11_0_arm64", "win_amd64", "manylinux_2_17_x86_64")
    ]
    payload = {"info": {"version": "1.0"}, "releases": {"1.0": [*wheels, {"filename": "pkg-1.0.tar.gz", "size": 1}]}}
    rendered = "\n".join(health._release_file_lines(health.release_files(payload)))
    assert "6 of 16, other platforms omitted" in rendered
    assert "win_amd64" not in rendered


def test_a_musllinux_wheel_counts_for_linux_x86_64():
    assert health._is_linux_x86_64("musllinux_1_2_x86_64")
    assert not health._is_linux_x86_64("musllinux_1_2_aarch64")


def test_a_payload_without_filenames_still_yields_a_report():
    """The older httpx capture was trimmed before filenames mattered, so it carries none. The report
    must degrade to counts of unknowns, never raise."""
    ships = health.release_files(fixture("httpx-pypi"))
    assert ships.version == "0.28.1"
    assert ships.files
    assert ships.linux_x86_64_wheels == []


@pytest.mark.parametrize(
    ("size", "expected"),
    [(None, "?"), (3139, "3.1 kB"), (3800600, "3.8 MB"), (512, "512 B"), (78_000_000_000, "78.0 GB")],
)
def test_sizes_print_in_decimal_units_like_pypi_does(size, expected):
    assert health._size(size) == expected


# ------------------------------------------------------------------------------------------------
# Upstream: the project a wrapper repackages. Both release captures are `releases/latest`, recorded
# 2026-09-27 and trimmed to tag, dates and the assets' name, size, type and digest.

RELEASES_CAPTURED = datetime(2026, 9, 27, tzinfo=UTC)


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("v0.11.0", "0.11.0"), ("15.2.0", "15.2.0"), ("ripgrep-15.2.0", "15.2.0"), ("release-v1.2", "1.2")],
)
def test_a_tag_is_read_as_its_version_with_the_usual_prefixes_dropped(tag, expected):
    assert health.tag_version(tag) == expected


def test_a_wrapper_that_suffixes_the_upstream_version_is_matched_with_its_lag():
    """Real captures: shellcheck v0.11.0 was published 2025-08-04 and shellcheck-py 0.11.0.1 was
    uploaded 2025-08-09, so the wrapper tracks upstream with a five-day lag."""
    transport = FakeTransport(
        pypi_payload=fixture("shellcheck-py-pypi"),
        github_payloads={"repos/koalaman/shellcheck/releases/latest": fixture("shellcheck-release")},
    )
    result = health.gather(transport, "shellcheck-py", None, upstream_repo="koalaman/shellcheck", now=RELEASES_CAPTURED)
    up = result.upstream
    assert up is not None
    assert (up.tag, up.version, up.published) == ("v0.11.0", "0.11.0", "2025-08-04")
    assert up.wrapper_match == "0.11.0.1"
    assert up.wrapper_match_date == "2025-08-09"
    assert up.lag_days == 5
    assert up.days_since_release == 418  # 2025-08-04T00:27Z to the pinned 2026-09-27T00:00Z


def test_an_exact_version_match_beats_a_suffixed_one():
    dates = {
        "1.2": datetime(2026, 1, 2, tzinfo=UTC),
        "1.2.1": datetime(2026, 1, 1, tzinfo=UTC),
        "1.20": datetime(2026, 1, 3, tzinfo=UTC),
    }
    assert health.wrapper_match("1.2", dates) == "1.2"
    del dates["1.2"]
    assert health.wrapper_match("1.2", dates) == "1.2.1"  # never 1.20: a digit is not a separator


def test_no_matching_wrapper_release_is_said_not_guessed():
    up = health.upstream(
        FakeTransport(github_payloads={"repos/x/y/releases/latest": {"tag_name": "v9.9.9", "assets": []}}),
        "x/y",
        health.release_dates(fixture("shellcheck-py-pypi")),
        now=RELEASES_CAPTURED,
    )
    assert up.wrapper_match is None
    rendered = "\n".join(health._upstream_lines(up, "0.11.0.1"))
    assert "NO MATCHING WRAPPER RELEASE for 9.9.9" in rendered
    assert "0.11.0.1" in rendered


def test_a_release_with_no_checksum_files_says_so_and_keeps_githubs_digest_apart():
    """Real capture: shellcheck publishes no checksum or signature file at all. GitHub's own
    digest is present on every asset and proves only that the download matches the upload."""
    assets, manifests, total = health.release_assets(fixture("shellcheck-release"))
    assert total == 13
    assert manifests == []
    assert [asset.name for asset in assets] == [
        "shellcheck-v0.11.0.linux.x86_64.tar.gz",
        "shellcheck-v0.11.0.linux.x86_64.tar.xz",
    ]
    assert all(asset.checksum is None and asset.signature is None for asset in assets)
    assert all(asset.github_digest for asset in assets)
    assert all(asset.libc == "unspecified" for asset in assets)


def test_rust_triples_split_by_libc_and_find_their_sidecar_checksums():
    """Real capture: ripgrep 15.2.0 ships a musl x86_64 build and a .deb, each with a .sha256
    beside it, and no gnu x86_64 build — the aarch64 and armv7 gnu builds must not leak in."""
    assets, _, _ = health.release_assets(fixture("ripgrep-release"))
    by_name = {asset.name: asset for asset in assets}
    assert set(by_name) == {"ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz", "ripgrep_15.2.0-1_amd64.deb"}
    musl = by_name["ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz"]
    assert musl.libc == "musl"
    assert musl.checksum == "ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz.sha256"
    assert musl.size == 2265718


def test_a_checksum_manifest_and_its_signature_cover_every_asset():
    release = {
        "tag_name": "v0.10.0",
        "assets": [
            {"name": "tool_0.10.0_linux_amd64.tar.gz", "size": 7},
            {"name": "tool_0.10.0_darwin_arm64.tar.gz", "size": 7},
            {"name": "checksums.txt", "size": 1},
            {"name": "checksums.txt.sig", "size": 1},
        ],
    }
    assets, manifests, _ = health.release_assets(release)
    assert manifests == ["checksums.txt"]
    assert [(asset.name, asset.checksum, asset.signature) for asset in assets] == [
        ("tool_0.10.0_linux_amd64.tar.gz", "checksums.txt", "checksums.txt.sig")
    ]


def test_an_upstream_without_releases_is_a_finding_not_a_crash():
    class NoReleases:
        def pypi(self, name: str):
            return fixture("shellcheck-py-pypi")

        def github(self, path: str):
            raise health.HealthError(f"gh api {path} failed: HTTP 404")

    result = health.gather(
        NoReleases(),
        "shellcheck-py",
        None,
        upstream_repo="someone/tags-only",
        now=RELEASES_CAPTURED,
    )
    assert result.upstream is not None
    assert result.upstream.error is not None
    assert "none readable" in health.render(result)


def test_the_upstream_section_reaches_the_report_and_the_json():
    transport = FakeTransport(
        pypi_payload=fixture("shellcheck-py-pypi"),
        github_payloads={"repos/koalaman/shellcheck/releases/latest": fixture("shellcheck-release")},
    )
    argv = ["pypi", "shellcheck-py", "--upstream", "koalaman/shellcheck"]
    result = health.gather(transport, "shellcheck-py", None, upstream_repo="koalaman/shellcheck", now=RELEASES_CAPTURED)
    rendered = health.render(result)
    assert "upstream (koalaman/shellcheck)" in rendered
    assert "5d after upstream" in rendered
    assert "NO checksum file" in rendered
    payload = health.payload_of(result)
    assert payload["upstream"]["lag_days"] == 5
    assert health.main([*argv, "--json"], transport=transport) == 0
    # Only the one release endpoint is read: assets and version come from the same response.
    assert [path for path in transport.asked if not path.startswith("pypi:")] == [
        "repos/koalaman/shellcheck/releases/latest"
    ] * 2


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
    assert payload["release_files"]["version"] == "0.28.1"
    assert json.dumps(payload, default=str)  # the whole thing has to survive a dump


def test_the_report_and_json_carry_what_the_release_ships():
    transport = FakeTransport(pypi_payload=fixture("shellcheck-py-pypi"))
    result = health.gather(transport, "shellcheck-py", None, now=CAPTURED)
    rendered = health.render(result)
    assert "ships (0.11.0.1)" in rendered
    assert "manylinux1_x86_64" in rendered
    assert "wheel present (3.8 MB)" in rendered
    payload = health.payload_of(result)
    assert payload["release_files"]["sdist_only"] is False
    assert len(payload["release_files"]["files"]) == 5
    assert transport.asked == ["pypi:shellcheck-py"]  # the file list costs no extra request


def test_main_reports_a_bad_name_as_the_callers_error(capsys):
    class Refusing:
        def pypi(self, name):
            raise health.HealthError(f"PyPI returned 404 for {name!r}")

        def github(self, path):
            raise AssertionError("never reached")

        def machine(self):
            return MACHINE

    assert health.main(["pypi", "no-such-distribution-xyz"], transport=Refusing()) == 1
    assert "404" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------
# `github <owner/repo>`: a repo judged on its own. `ripgrep-releases.json` is the real releases list
# and `ripgrep-repo.json` the repo, both recorded 2026-09-27 and trimmed to the fields read.


def ripgrep_transport():
    return FakeTransport(
        github_payloads={
            "repos/BurntSushi/ripgrep/releases/latest": fixture("ripgrep-release"),
            "repos/BurntSushi/ripgrep/releases?": fixture("ripgrep-releases"),
            "repos/BurntSushi/ripgrep/commits": [{"author": {"login": "BurntSushi"}}] * 3,
            "repos/BurntSushi/ripgrep/issues": fixture("click-issues"),
            "repos/BurntSushi/ripgrep": fixture("ripgrep-repo"),
        }
    )


def test_github_reads_the_stable_cadence_from_the_releases_list():
    """Real capture: 75 releases, none drafts or pre-releases, the newest 15.2.0 on 2026-07-15."""
    result = health.gather_github(ripgrep_transport(), "BurntSushi/ripgrep", now=RELEASES_CAPTURED)
    listing = result.releases
    assert listing.read == 75
    assert listing.truncated is False
    assert listing.cadence.releases == 75
    assert listing.cadence.last_release == "2026-07-15"
    assert listing.cadence.in_last_year == 3  # 15.0.0, 15.1.0 and 15.2.0


def test_github_carries_the_maintenance_axis_and_the_latest_releases_assets():
    transport = ripgrep_transport()
    result = health.gather_github(transport, "BurntSushi/ripgrep", now=RELEASES_CAPTURED)
    assert result.repository is not None
    assert result.repository.stars == 68650
    assert result.contributors is not None
    assert result.contributors.humans == [("BurntSushi", 3)]
    assert result.latest.version == "15.2.0"
    assert {asset.libc for asset in result.latest.linux_x86_64} == {"musl", "unspecified"}
    rendered = health.render_github(result)
    assert "75 stable GitHub releases" in rendered
    assert "ships (BurntSushi/ripgrep, latest stable release)" in rendered
    assert "ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz" in rendered
    assert "not scored       68650 stars" in rendered


def test_a_release_flagged_or_spelled_as_a_pre_release_is_off_the_stable_line_and_drafts_are_skipped():
    releases = [
        {"tag_name": "v2.0.0-rc.1", "prerelease": False, "published_at": "2026-09-01T00:00:00Z"},
        {"tag_name": "v1.9.0-nightly", "prerelease": True, "published_at": "2026-08-01T00:00:00Z"},
        {"tag_name": "v1.8.0", "prerelease": False, "published_at": "2026-07-01T00:00:00Z"},
        {"tag_name": "v3.0.0", "draft": True, "published_at": None},
    ]
    transport = FakeTransport(github_payloads={"repos/o/r/releases?": releases})
    listing = health.release_list(transport, "o/r", now=RELEASES_CAPTURED)
    assert listing.cadence.releases == 1
    assert listing.cadence.prereleases == 2
    assert listing.drafts == 1


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("@biomejs/biome@2.5.14", "2.5.14"), ("@biomejs/js-api@6.0.0", "6.0.0")],
)
def test_a_monorepo_package_tag_is_read_as_its_version(tag, expected):
    """Live 2026-09-27: biome tags every release `@biomejs/biome@<version>`, changesets' form."""
    assert health.tag_version(tag) == expected


def test_the_github_subcommand_runs_end_to_end_and_rejects_a_non_repo(capsys):
    assert health.main(["github", "BurntSushi/ripgrep", "--json"], transport=ripgrep_transport()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["latest"]["version"] == "15.2.0"
    assert health.main(["github", "ripgrep"], transport=ripgrep_transport()) == 1
    assert "is not owner/repo" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------
# The command line: the source is a required subcommand, and the retired form says so loudly


@pytest.mark.parametrize(
    ("argv", "spelled"),
    [
        (["httpx", "encode/httpx"], "package_health.py pypi httpx --repo encode/httpx"),
        (["httpx"], "package_health.py pypi httpx"),
        (
            ["httpx", "encode/httpx", "--clone", "/r/x"],
            "package_health.py pypi httpx --repo encode/httpx --clone /r/x",
        ),
        (["shellcheck-py", "--upstream", "a/b"], "package_health.py pypi shellcheck-py --upstream a/b"),
    ],
)
def test_the_retired_positional_form_exits_2_naming_the_new_spelling(argv, spelled, capsys):
    """Decided 2026-09-27: a silent fallback to PyPI would be a default by another name. The
    cost is one line of correction for anyone running an old example from memory."""
    assert health.main(argv, transport=FakeTransport()) == 2
    err = capsys.readouterr().err
    assert spelled in err
    assert len(err.strip().splitlines()) == 1


def test_there_is_no_default_source(capsys):
    with pytest.raises(SystemExit) as raised:
        health.main([], transport=FakeTransport())
    assert raised.value.code == 2


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/encode/httpx", "encode/httpx"),
        ("git+https://github.com/biomejs/biome.git", "biomejs/biome"),
        ("git@github.com:evanw/esbuild.git", "evanw/esbuild"),
        ("https://github.com/encode/httpx/blob/master/CHANGELOG.md", "encode/httpx"),
        ("github:owner/repo", "owner/repo"),
        ("https://github.com/sponsors/encode", None),
        ("https://gitlab.com/owner/repo", None),
        ("https://www.python-httpx.org", None),
        (None, None),
    ],
)
def test_a_github_repo_is_read_from_any_common_spelling_of_its_url(url, expected):
    assert health.repo_from_url(url) == expected


def test_the_repo_is_read_from_project_urls_source_keys_first_and_the_report_says_so():
    """Live 2026-09-27: httpx's `project_urls` carry `Changelog`, `Documentation`, `Homepage` and
    `Source`, three of them on GitHub. The source-like key wins, and the report names it."""
    payload = fixture("httpx-pypi") | {
        "info": fixture("httpx-pypi")["info"]
        | {
            "project_urls": {
                "Changelog": "https://github.com/encode/httpx/blob/master/CHANGELOG.md",
                "Documentation": "https://www.python-httpx.org",
                "Homepage": "https://github.com/encode/httpx",
                "Source": "https://github.com/encode/httpx",
            }
        }
    }
    transport = httpx_transport()
    transport.pypi_payload = payload
    result = health.gather(transport, "httpx", None, now=CAPTURED)
    assert result.repo_choice == health.RepoChoice("encode/httpx", 'PyPI project_urls "Source"')
    assert result.repository is not None
    rendered = health.render(result)
    assert 'repo from        PyPI project_urls "Source"; --repo overrides' in rendered


def test_an_explicit_repo_overrides_the_metadata_and_says_so():
    result = health.gather(httpx_transport(), "httpx", "encode/httpx", now=CAPTURED)
    assert result.repo_choice == health.RepoChoice("encode/httpx", "--repo")


def test_no_repo_in_the_metadata_is_said_and_the_flag_is_named():
    rendered = health.render(health.gather(FakeTransport(), "httpx", None, now=CAPTURED))
    assert "none read — PyPI metadata names no GitHub repo; pass --repo owner/repo" in rendered


# ------------------------------------------------------------------------------------------------
# Floors: every minimum the metadata states, compared with this machine where that is cheap


@pytest.mark.parametrize(
    ("spec", "version", "expected"),
    [
        (">=3.9", "3.12.3", True),
        (">=3.13", "3.12.3", False),
        (">=3.8,<3.12", "3.12.3", False),
        (">=3.8, !=3.9.*", "3.9.1", False),
        ("~=3.10", "3.12.3", True),
        ("~=3.10.1", "3.11.0", False),
        ("==3.*", "3.12.3", True),
        (">=3.9", None, None),
        ("banana", "3.12.3", None),
    ],
)
def test_a_python_specifier_is_evaluated_against_this_interpreter(spec, version, expected):
    assert health.python_spec_met(spec, version) is expected


@pytest.mark.parametrize(
    ("spec", "version", "expected"),
    [
        (">=14.21.3", "20.11.1", True),
        (">=18", "16.20.0", False),
        ("^18 || >=20", "19.0.0", False),
        ("^18 || >=20", "18.2.0", True),
        (">= 18.0.0", "18.0.0", True),
        ("18.x", "18.19.0", True),
        ("~16.14", "16.15.0", False),
        ("16 - 18", "17.1.0", True),
        ("*", "12.0.0", True),
        (">=18", None, None),
        ("node-lts", "18.0.0", None),
    ],
)
def test_an_npm_engines_range_is_evaluated_against_this_node(spec, version, expected):
    assert health.node_range_met(spec, version) is expected


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("manylinux_2_17_x86_64", ("glibc", (2, 17))),
        ("manylinux1_x86_64.manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_5_x86_64", ("glibc", (2, 5))),
        ("manylinux2014_x86_64", ("glibc", (2, 17))),
        ("musllinux_1_2_x86_64", ("musl", (1, 2))),
        ("win_amd64", None),
    ],
)
def test_the_glibc_floor_is_read_from_the_manylinux_tag_the_lowest_member_winning(tag, expected):
    assert health.wheel_libc_floor(tag) == expected


def test_pypi_floors_carry_requires_python_and_the_manylinux_glibc_floor():
    """Real capture: shellcheck-py 0.11.0.1 declares >=3.9 and its Linux wheel carries four tags,
    the lowest being manylinux1, which is glibc 2.5."""
    result = health.gather(
        FakeTransport(pypi_payload=fixture("shellcheck-py-pypi")), "shellcheck-py", None, now=CAPTURED, machine=MACHINE
    )
    floors = {floor.what: floor for floor in result.floors}
    assert (floors["python"].required, floors["python"].met) == (">=3.9", True)
    assert (floors["glibc"].required, floors["glibc"].met) == (">=2.5", True)
    rendered = health.render(result)
    assert "met here (glibc 2.39)" in rendered
    assert "met here (python3 3.12.3)" in rendered


def test_a_floor_above_this_machine_is_flagged():
    payload = {
        "info": {"version": "1.0", "requires_python": ">=3.14"},
        "releases": {"1.0": [{"filename": "pkg-1.0-cp314-cp314-manylinux_2_41_x86_64.whl", "size": 1}]},
    }
    floors = health.pypi_floors(">=3.14", health.release_files(payload), MACHINE)
    assert [floor.met for floor in floors] == [False, False]
    assert "NOT MET HERE (glibc 2.39)" in "\n".join(health._floor_lines(floors))


def test_a_musllinux_only_release_is_a_mismatch_on_a_glibc_machine():
    wheel = {"filename": "p-1.0-py3-none-musllinux_1_2_x86_64.whl"}
    payload = {"info": {"version": "1.0"}, "releases": {"1.0": [wheel]}}
    (python, libc) = health.pypi_floors(None, health.release_files(payload), MACHINE)
    assert python.required == "undeclared"
    assert (libc.required, libc.met) == ("musl", False)


def test_a_floor_is_not_compared_when_this_machines_value_is_unreadable():
    floors = health.pypi_floors(">=3.9", health.release_files(fixture("shellcheck-py-pypi")), None)
    assert all(floor.met is None for floor in floors)
    assert "not readable here" in "\n".join(health._floor_lines(floors))


def test_github_floors_name_the_libc_family_and_say_the_number_is_not_in_the_name():
    result = health.gather_github(ripgrep_transport(), "BurntSushi/ripgrep", now=RELEASES_CAPTURED, machine=MACHINE)
    assert [(floor.required, floor.met) for floor in result.floors] == [("musl", None), ("unspecified", None)]
    assert "statically linked" in health.render_github(result)


# ------------------------------------------------------------------------------------------------
# npm. The captures are the full packuments of `@biomejs/biome`, `esbuild`, `express` and their
# platform or `@types` packages, recorded 2026-09-27 and trimmed to a handful of versions each.


def biome_transport():
    return FakeTransport(
        npm_payloads={
            "@biomejs/biome": fixture("biome-npm"),
            "@biomejs/cli-linux-x64": fixture("biome-cli-linux-x64-npm"),
            "@biomejs/cli-linux-x64-musl": fixture("biome-cli-linux-x64-musl-npm"),
        }
    )


def test_npm_judges_dist_tags_latest_never_the_newest_publish():
    """Real capture: express's `latest-4` (4.22.3, 2026-09-14) was published after `latest`
    (5.2.1, 2025-12-01). The newest key is not what `npm install express` resolves to."""
    payloads = {"express": fixture("express-npm"), "@types/express": fixture("types-express-npm")}
    transport = FakeTransport(npm_payloads=payloads)
    result = health.gather_npm(transport, "express", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert result.version == "5.2.1"
    assert result.ships.unpacked_size == 75429
    assert "latest-4 4.22.3" in health.render_npm(result)


def test_npm_size_fields_are_optional_on_old_versions():
    """Real capture: express has `unpackedSize` from 4.16.3 (2018-03-12) on, and not on 4.16.2."""
    doc = fixture("express-npm")
    old = health.npm_ships(FakeTransport(), doc["versions"]["4.16.2"], machine=MACHINE)
    assert (old.unpacked_size, old.file_count) == (None, None)
    assert "size not recorded" in "\n".join(health._npm_ship_lines(old))
    assert health.npm_ships(FakeTransport(), doc["versions"]["4.16.3"], machine=MACHINE).file_count == 16


def test_npm_resolves_the_platform_package_that_actually_carries_the_binary():
    """Real capture: the biome wrapper is 779 kB and its glibc Linux x64 package 64.7 MB, so the
    wrapper's own size understates the install by about eighty times."""
    transport = biome_transport()
    result = health.gather_npm(transport, "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    ships = result.ships
    assert ships.optional_dependencies == 8
    assert [pkg.name for pkg in ships.platform_packages] == ["@biomejs/cli-linux-x64", "@biomejs/cli-linux-x64-musl"]
    assert ships.chosen == "@biomejs/cli-linux-x64"
    assert ships.install_size == 779173 + 64693040
    # Only the two Linux x64 candidates are fetched, never all eight platforms.
    assert [ask for ask in transport.asked if ask.startswith("npm:@biomejs/cli")] == [
        "npm:@biomejs/cli-linux-x64",
        "npm:@biomejs/cli-linux-x64-musl",
    ]
    rendered = health.render_npm(result)
    assert "64.7 MB  glibc" in rendered
    assert "<- this machine" in rendered
    assert "install size     65.5 MB here" in rendered


def test_a_platform_pin_that_names_no_published_version_is_the_finding():
    """Real capture: biome 2.0.3 pinned every platform package to `workspace:*`, and carries a
    deprecation saying its manifest is broken."""
    doc = fixture("biome-npm")
    ships = health.npm_ships(biome_transport(), doc["versions"]["2.0.3"], machine=MACHINE)
    assert ships.chosen is None
    assert all("workspace:*" in (pkg.error or "") for pkg in ships.platform_packages)
    assert "UNRESOLVED" in "\n".join(health._npm_ship_lines(ships))


def test_a_musl_machine_is_not_assumed_when_glibc_is_unreadable():
    doc = fixture("biome-npm")
    unknown = health.Machine(python="3.12.3", glibc=None, node=None)
    ships = health.npm_ships(biome_transport(), doc["versions"]["2.5.14"], machine=unknown)
    assert ships.chosen is None  # two candidates and no libc to choose between them


def test_npm_install_scripts_and_provenance_are_reported_separately():
    """Real capture: esbuild resolves a platform package **and** runs a postinstall that verifies
    it. The two signals co-occur and mean different things, so each has its own line."""
    transport = FakeTransport(
        npm_payloads={"esbuild": fixture("esbuild-npm"), "@esbuild/linux-x64": fixture("esbuild-linux-x64-npm")}
    )
    result = health.gather_npm(transport, "esbuild", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert result.ships.install_scripts == {"postinstall": "node install.js"}
    assert result.ships.provenance == "https://slsa.dev/provenance/v1"
    assert result.ships.chosen == "@esbuild/linux-x64"
    rendered = health.render_npm(result)
    assert "RUNS AT INSTALL — postinstall: node install.js" in rendered


def test_npm_typing_is_own_types_or_a_separate_types_package_or_neither():
    esbuild = fixture("esbuild-npm")["versions"]["0.28.2"]
    assert health.npm_typing(FakeTransport(), "esbuild", esbuild).verdict == "own"
    express = fixture("express-npm")["versions"]["5.2.1"]
    with_types = FakeTransport(npm_payloads={"@types/express": fixture("types-express-npm")})
    typed = health.npm_typing(with_types, "express", express)
    assert typed.verdict == "@types"
    assert "@types/express 5.0.6" in typed.detail
    assert health.npm_typing(FakeTransport(), "express", express).verdict == "none"
    exports_only = {"exports": {".": {"import": {"types": "./index.d.mts", "default": "./index.mjs"}}}}
    assert health.npm_typing(FakeTransport(), "x", exports_only).verdict == "own"


@pytest.mark.parametrize(
    ("name", "expected"), [("express", "@types/express"), ("@biomejs/biome", "@types/biomejs__biome")]
)
def test_the_definitely_typed_name_follows_its_scoped_spelling(name, expected):
    assert health.types_package_name(name) == expected


def test_npm_deprecations_are_counted_and_a_deprecated_latest_is_headlined():
    result = health.gather_npm(biome_transport(), "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert result.deprecated == ["2.0.1", "2.0.2", "2.0.3"]
    assert result.latest_deprecated is None
    doc = fixture("biome-npm")
    doc["dist-tags"] = {"latest": "2.0.1"}
    transport = biome_transport()
    transport.npm_payloads["@biomejs/biome"] = doc
    stale = health.gather_npm(transport, "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert "LATEST IS DEPRECATED: This version of Biome has a broken manifest" in health.render_npm(stale)


def test_npm_cadence_keeps_nightlies_and_betas_off_the_stable_line():
    result = health.gather_npm(biome_transport(), "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert result.cadence.releases == 4  # 2.0.1, 2.0.2, 2.0.3, 2.5.14
    assert result.cadence.prereleases == 2  # the nightly and the beta


def test_npm_repository_fills_the_repo_and_the_report_names_the_field():
    transport = biome_transport()
    transport.github_payloads = {"repos/biomejs/biome": fixture("httpx-repo")}
    result = health.gather_npm(transport, "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    assert result.repo_choice == health.RepoChoice("biomejs/biome", 'npm "repository"')
    assert 'repo from        npm "repository"; --repo overrides' in health.render_npm(result)


def test_npm_floors_read_engines_and_the_platform_packages_libc():
    result = health.gather_npm(biome_transport(), "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=MACHINE)
    floors = {floor.what: floor for floor in result.floors}
    assert floors["node"].required == ">=14.21.3"
    assert floors["node"].met is None  # this machine has no node on PATH
    assert (floors["platform"].required, floors["platform"].met) == ("linux/x64/glibc", True)
    with_node = health.Machine(python="3.12.3", glibc="2.39", node="12.22.9")
    old = health.gather_npm(biome_transport(), "@biomejs/biome", None, now=RELEASES_CAPTURED, machine=with_node)
    assert "NOT MET HERE (node 12.22.9)" in health.render_npm(old)


def test_the_npm_subcommand_runs_end_to_end_with_json(capsys):
    assert health.main(["npm", "@biomejs/biome", "--json"], transport=biome_transport()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ships"]["install_size"] == 779173 + 64693040
    assert payload["typing"]["verdict"] == "none"
