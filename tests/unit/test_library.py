"""The research library's conventions in `research-library/scripts/library.py`.

Naming is a pure function and is tested as one. Everything else takes a fake git runner and a
temporary store, so **no test shells out and no test touches the real `$RESEARCH_HOME`** — asserted
by the autouse fixture below rather than intended, because a test that clones for real would be slow
and a test that writes into the real library would corrupt the thing it is checking.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "research-library" / "scripts" / "library.py"


def _load():
    spec = importlib.util.spec_from_file_location("library_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


library = _load()


@pytest.fixture(autouse=True)
def _no_subprocess(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(f"a test shelled out: {args!r} {kwargs!r}")

    monkeypatch.setattr(library.subprocess, "run", refuse)


class FakeGit:
    """Canned git output, keyed by the start of the command line, longest match first."""

    def __init__(self, responses: dict[str, tuple[int, str, str]] | None = None):
        self.responses: dict[str, tuple[int, str, str]] = responses or {}
        self.calls: list[list[str]] = []

    def __call__(self, argv, cwd=None):
        args = [str(a) for a in argv]
        self.calls.append(args)
        line = " ".join(args)
        for key in sorted(self.responses, key=len, reverse=True):
            if key in line:
                code, out, err = self.responses[key]
                return library.Ran(tuple(args), code, out, err)
        return library.Ran(tuple(args), 0, "", "")


def make_store(tmp_path: Path) -> Path:
    for bucket in library.BUCKETS:
        (tmp_path / bucket).mkdir(parents=True)
    return tmp_path


def make_clone(store: Path, name: str, provenance: str | None = "url: u\nkind: repo-clone\nref: r\nfetched: f\n"):
    entry = store / "repos" / name
    (entry / ".git").mkdir(parents=True)
    if provenance is not None:
        (entry / "SOURCE.md").write_text(provenance, encoding="utf-8")
    return entry


# --------------------------------------------------------------------------------------------
# naming: the derivation the skill used to spell out in prose


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/encode/httpx", "github.com--encode--httpx"),
        ("https://github.com/encode/httpx.git", "github.com--encode--httpx"),
        ("https://github.com/encode/httpx/", "github.com--encode--httpx"),
        ("git@gitlab.gnome.org:GNOME/gnome-shell.git", "gitlab.gnome.org--GNOME--gnome-shell"),
        ("ssh://git@github.com/encode/httpx", "github.com--encode--httpx"),
        ("git+https://github.com/encode/httpx", "github.com--encode--httpx"),
        ("https://www.github.com/encode/httpx", "github.com--encode--httpx"),
        ("https://GitHub.com/encode/httpx", "github.com--encode--httpx"),
    ],
)
def test_every_spelling_of_a_remote_gives_one_name(url, expected):
    assert library.entry_name(url) == expected


def test_the_host_is_never_special_cased():
    """The convention's one absolute: same shape for every host. A self-hosted instance looks like
    the popular one and is not it, which is why the rule has no GitHub branch to get wrong."""
    assert library.entry_name("https://gitlab.gnome.org/GNOME/gnome-shell") == "gitlab.gnome.org--GNOME--gnome-shell"
    assert library.entry_name("https://codeberg.org/owner/repo") == "codeberg.org--owner--repo"


def test_a_nested_group_keeps_every_segment():
    """Dropping the middle of `group/sub/proj` collides two projects whose names match under
    different subgroups — a silent collision in a store nothing version-controls."""
    assert library.entry_name("https://gitlab.com/group/sub/proj") == "gitlab.com--group--sub--proj"


def test_case_below_the_host_is_preserved():
    """The store already holds `gitlab.gnome.org--GNOME--gnome-shell`, and every project `AGENTS.md`
    pointing at an entry names it exactly. Lowercasing would orphan those pointers."""
    assert library.entry_name("https://gitlab.gnome.org/GNOME/gnome-shell").endswith("--GNOME--gnome-shell")


@pytest.mark.parametrize("bad", ["", "   ", "not a url", "https://github.com", "ftp://host/owner/repo"])
def test_an_unreadable_url_is_an_error_not_a_guess(bad):
    with pytest.raises(library.LibraryError):
        library.entry_name(bad)


def test_the_name_can_be_read_from_a_clones_own_remote(tmp_path):
    git = FakeGit({"remote get-url origin": (0, "https://gitlab.gnome.org/GNOME/gnome-shell.git\n", "")})
    assert library.canonical_name(git, tmp_path) == "gitlab.gnome.org--GNOME--gnome-shell"


# --------------------------------------------------------------------------------------------
# add


def test_add_dry_run_writes_nothing_and_prints_both_halves(tmp_path, capsys):
    store = make_store(tmp_path)
    argv = ["add", "https://github.com/encode/httpx", "--root", str(store), "--dry-run"]
    args = library.build_parser().parse_args(argv)
    git = FakeGit()
    payload = library.cmd_add(args, git)
    out = capsys.readouterr().out
    assert git.calls == [], "a dry run must not run git at all"
    assert not (store / "repos" / "github.com--encode--httpx").exists()
    assert "git clone --depth 1" in out
    assert "kind: repo-clone" in payload["provenance"]


def test_add_clones_writes_provenance_and_records_the_real_ref(tmp_path):
    store = make_store(tmp_path)
    target = store / "repos" / "github.com--encode--httpx"

    def fake_clone(argv, cwd=None):
        if argv[:2] == ["git", "clone"]:
            (target / ".git").mkdir(parents=True)
            return library.Ran(tuple(argv), 0, "", "")
        return git(argv, cwd)

    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/encode/httpx\n", ""),
            "rev-parse --abbrev-ref HEAD": (0, "master\n", ""),
            "rev-parse --short HEAD": (0, "abc1234\n", ""),
        }
    )
    args = library.build_parser().parse_args(["add", "https://github.com/encode/httpx", "--root", str(store)])
    payload = library.cmd_add(args, fake_clone)
    written = (target / "SOURCE.md").read_text(encoding="utf-8")
    assert "url: https://github.com/encode/httpx" in written
    assert "ref: master@abc1234" in written
    assert payload["name"] == "github.com--encode--httpx"


def test_add_renames_to_the_name_the_remote_actually_resolves_to(tmp_path):
    """A renamed or transferred repo redirects silently, so the URL you were handed and the URL the
    clone ends up with can disagree — and the entry would carry a name nothing else agrees with."""
    store = make_store(tmp_path)
    typed = store / "repos" / "github.com--old--name"

    def fake_clone(argv, cwd=None):
        if argv[:2] == ["git", "clone"]:
            (typed / ".git").mkdir(parents=True)
            return library.Ran(tuple(argv), 0, "", "")
        return git(argv, cwd)

    git = FakeGit({"remote get-url origin": (0, "https://github.com/new/name\n", "")})
    args = library.build_parser().parse_args(["add", "https://github.com/old/name", "--root", str(store)])
    payload = library.cmd_add(args, fake_clone)
    assert payload["renamed_from"] == "github.com--old--name"
    assert (store / "repos" / "github.com--new--name" / "SOURCE.md").is_file()
    assert not typed.exists()


def test_add_refuses_an_entry_that_already_exists(tmp_path):
    store = make_store(tmp_path)
    make_clone(store, "github.com--encode--httpx")
    args = library.build_parser().parse_args(["add", "https://github.com/encode/httpx", "--root", str(store)])
    with pytest.raises(library.LibraryError, match="already exists"):
        library.cmd_add(args, FakeGit())


def test_a_missing_library_is_an_error_rather_than_a_directory_this_script_creates(tmp_path):
    with pytest.raises(library.LibraryError, match="no research library"):
        library.store_root(str(tmp_path / "nope"))


# --------------------------------------------------------------------------------------------
# check


def test_a_normal_shallow_clone_is_not_a_finding(tmp_path):
    """`git clone --depth 1` implies `--single-branch`, so a refspec naming one branch is what a
    correct entry looks like. A rule that flagged every non-wildcard refspec reported 49 of 52
    entries on the real library — every one of them cloned exactly as the skill instructs."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--astral-sh--uv")
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/astral-sh/uv\n", ""),
            "config --get-all remote.origin.fetch": (0, "+refs/heads/main:refs/remotes/origin/main\n", ""),
            "symbolic-ref -q HEAD": (0, "refs/heads/main\n", ""),
        }
    )
    assert library.check_entry(git, store, entry)["findings"] == []


def test_a_clone_pinned_at_a_tag_is_the_documented_trap(tmp_path):
    """The failure it produces: `git fetch origin` re-fetches the same pinned ref forever, so a
    refresh reports up to date on an entry that is years stale."""
    store = make_store(tmp_path)
    entry = make_clone(store, "gitlab.gnome.org--GNOME--gnome-shell")
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://gitlab.gnome.org/GNOME/gnome-shell\n", ""),
            "config --get-all remote.origin.fetch": (0, "+refs/heads/48.2:refs/remotes/origin/48.2\n", ""),
            "symbolic-ref -q HEAD": (1, "", ""),
        }
    )
    findings = library.check_entry(git, store, entry)["findings"]
    assert any("HEAD is detached" in f for f in findings)


def test_the_remote_default_branch_check_is_opt_in(tmp_path):
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--owner--repo")
    responses = {
        "remote get-url origin": (0, "https://github.com/owner/repo\n", ""),
        "config --get-all remote.origin.fetch": (0, "+refs/heads/old:refs/remotes/origin/old\n", ""),
        "symbolic-ref -q HEAD": (0, "refs/heads/old\n", ""),
        "ls-remote --symref origin HEAD": (0, "ref: refs/heads/main\tHEAD\n", ""),
    }
    local = FakeGit(responses)
    assert library.check_entry(local, store, entry)["findings"] == []
    assert not any("ls-remote" in " ".join(c) for c in local.calls), "the default check must stay offline"

    remote = FakeGit(responses)
    findings = library.check_entry(remote, store, entry, remote=True)["findings"]
    assert any("default branch is main" in f for f in findings)


def test_a_name_that_stopped_matching_its_own_remote_is_a_finding(tmp_path):
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--old--name")
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/new/name\n", ""),
            "symbolic-ref -q HEAD": (0, "refs/heads/main\n", ""),
        }
    )
    findings = library.check_entry(git, store, entry)["findings"]
    assert any("should be github.com--new--name" in f for f in findings)


def test_a_clone_that_failed_partway_is_named_as_such(tmp_path):
    """The store's characteristic failure: an entry that is present, looks conformant from a
    listing, and is not a clone at all."""
    store = make_store(tmp_path)
    entry = store / "repos" / "github.com--owner--repo"
    entry.mkdir(parents=True)
    (entry / "SOURCE.md").write_text("url: u\nkind: repo-clone\nref: r\nfetched: f\n", encoding="utf-8")
    findings = library.check_entry(FakeGit(), store, entry)["findings"]
    assert any("not a git clone" in f for f in findings)


def test_provenance_is_checked_by_the_shape_each_bucket_uses(tmp_path):
    store = make_store(tmp_path)
    missing = make_clone(store, "github.com--a--b", provenance=None)
    assert any("no provenance file" in f for f in library.check_entry(FakeGit(), store, missing)["findings"])

    thin = make_clone(store, "github.com--c--d", provenance="url: u\nkind: repo-clone\n")
    assert any("missing: ref, fetched" in f for f in library.check_entry(FakeGit(), store, thin)["findings"])

    pdf = store / "docs" / "paper.pdf"
    pdf.write_bytes(b"%PDF")
    assert any("no provenance file" in f for f in library.check_entry(FakeGit(), store, pdf)["findings"])
    pdf.with_name("paper.pdf.source.md").write_text("url: u\nkind: site-mirror\nref: r\nfetched: f\n", encoding="utf-8")
    assert library.check_entry(FakeGit(), store, pdf)["findings"] == []


def test_a_kind_outside_the_stores_vocabulary_is_reported(tmp_path):
    """Found on the real library: three `docs/` entries carrying `reference-pdf` and
    `site-mirror (single PDF)`. Reported rather than silently accepted — the vocabulary belongs to
    the store's own README, and widening it is a decision, not a parser change."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b", provenance="url: u\nkind: reference-pdf\nref: r\nfetched: f\n")
    findings = library.check_entry(FakeGit(), store, entry)["findings"]
    assert any("not one of" in f for f in findings)


def test_the_buckets_themselves_are_not_entries(tmp_path):
    store = make_store(tmp_path)
    make_clone(store, "github.com--a--b")
    (store / "README.md").write_text("the store's own readme\n", encoding="utf-8")
    entries = [p.name for p in library.iter_entries(store)]
    assert entries == ["github.com--a--b"]


def test_strict_turns_a_finding_into_a_non_zero_exit(tmp_path, capsys):
    store = make_store(tmp_path)
    make_clone(store, "github.com--a--b", provenance=None)
    assert library.main(["check", "--root", str(store)], FakeGit()) == 0
    assert library.main(["check", "--root", str(store), "--strict"], FakeGit()) == 1
    capsys.readouterr()
