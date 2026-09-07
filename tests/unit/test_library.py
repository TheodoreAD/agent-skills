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


@pytest.fixture(autouse=True)
def _no_ambient_text_only(monkeypatch):
    """`$RESEARCH_TEXT_ONLY` decides `add`'s default, so a machine that sets it would otherwise
    quietly invert half the assertions below — and pass."""
    monkeypatch.delenv(library.TEXT_ONLY_ENV, raising=False)


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
# text-only clones
#
# The saving is 41% of the library's working-tree bytes and it is free by construction, which is the
# only reason it is safe to make a default: every format excluded is one ripgrep and grep already
# refuse to search. Verified end to end 2026-09-08 on `intellectronica/ruler` (97% binary), the same
# commit cloned both ways with the shipping pattern list: **257 searchable files in both trees, the
# identical set**, `grep -rIl ruler` returning 190 files in both, and one file removed — a 69 MB
# `.gif`. 141 MB became 3.0 MB, `.git` 70 MB became 644 KB.


def clone_into(target: Path, git: "FakeGit"):
    """A runner that materialises the clone the way a real `git clone` would."""

    def run(argv, cwd=None):
        if argv[:2] == ["git", "clone"]:
            (target / ".git").mkdir(parents=True)
            return library.Ran(tuple(argv), 0, "", "")
        return git(argv, cwd)

    return run


def test_no_document_format_is_excluded():
    """The line is document-versus-demo-asset, not greppable-versus-not: an agent reads a PDF
    natively. Measured 2026-09-08: 8 PDFs inside repo clones, 6.5 MB, 0.5% of the excluded weight —
    including a 4.8 MB `flameshot-documentation.pdf`, which is exactly the reference material this
    library exists to hold. Half a percent of the saving buys away the whole risk."""
    assert set(library.DOCUMENT_EXTENSIONS) & set(library.UNGREPPABLE_EXTENSIONS) == set()
    assert "pdf" in library.DOCUMENT_EXTENSIONS
    excluded = {p.removeprefix("!*.") for p in library.sparse_patterns()}
    assert excluded.isdisjoint(library.DOCUMENT_EXTENSIONS), "the patterns are what actually ships"


def test_svg_is_kept_and_svgz_is_not():
    """`.svg` is *text*, so a grep reads it and the NUL rule keeps it whatever anyone thinks of it
    as a demo asset. It is the tell that this list is a judgement about purpose constrained by a
    fact, rather than a fact on its own. `.svgz` is the gzipped one, and binary."""
    assert "svg" not in library.UNGREPPABLE_EXTENSIONS
    assert "svgz" in library.UNGREPPABLE_EXTENSIONS


def test_the_patterns_are_non_cone_because_the_criterion_is_a_file_type():
    """Cone mode matches directories and cannot express this at all — the two are not alternatives.
    Git calls non-cone deprecated and schedules no removal (`Documentation/BreakingChanges.adoc`
    does not mention sparse-checkout); the fallback is writing `.git/info/sparse-checkout` directly,
    which is the same mechanism one layer down."""
    patterns = library.sparse_patterns()
    assert patterns[0] == "/*"
    assert all(p.startswith("!*.") for p in patterns[1:])


def test_add_is_text_only_by_default_and_ships_both_levers_together(tmp_path, capsys):
    """`--filter=blob:none` and `--sparse` are useless apart and transformative together. Probed
    2026-09-07 on the same commit three ways: the sparse set alone took the working tree from 72,960
    KB to 2,348 KB while `.git` stayed at 71,204 KB; adding the filter took `.git` to 644 KB,
    because blobs the sparse set never wants are never fetched. A clone carrying one without the
    other saves a fraction of what it looks like it saves."""
    store = make_store(tmp_path)
    argv = ["add", "https://github.com/encode/httpx", "--root", str(store), "--dry-run"]
    payload = library.cmd_add(library.build_parser().parse_args(argv), FakeGit())
    out = capsys.readouterr().out

    assert payload["text_only"] is True
    assert "--filter=blob:none" in out
    assert "--sparse " in out
    assert "sparse-checkout set --no-cone" in out
    assert "!*.png" in out
    assert "!*.pdf" not in out
    assert "text-only: yes" in payload["provenance"]


def test_all_files_opts_one_clone_out(tmp_path, capsys):
    store = make_store(tmp_path)
    argv = ["add", "https://github.com/encode/httpx", "--root", str(store), "--dry-run", "--all-files"]
    payload = library.cmd_add(library.build_parser().parse_args(argv), FakeGit())
    out = capsys.readouterr().out

    assert payload["text_only"] is False
    assert "--filter=blob:none" not in out
    assert "sparse-checkout" not in out
    assert "text-only" not in payload["provenance"]


def test_the_env_var_opts_a_whole_machine_out_and_a_flag_still_beats_it(tmp_path, monkeypatch, capsys):
    """Default-on because the library's purpose is text search and the excluded bytes are useless
    for it; the env var is how a machine that wants the old behaviour says so once rather than
    remembering a flag on every call."""
    store = make_store(tmp_path)
    base = ["add", "https://github.com/encode/httpx", "--root", str(store), "--dry-run"]

    monkeypatch.setenv(library.TEXT_ONLY_ENV, "0")
    assert library.cmd_add(library.build_parser().parse_args(base), FakeGit())["text_only"] is False
    assert library.cmd_add(library.build_parser().parse_args([*base, "--text-only"]), FakeGit())["text_only"] is True

    monkeypatch.setenv(library.TEXT_ONLY_ENV, "1")
    assert library.cmd_add(library.build_parser().parse_args(base), FakeGit())["text_only"] is True
    assert library.cmd_add(library.build_parser().parse_args([*base, "--all-files"]), FakeGit())["text_only"] is False
    capsys.readouterr()


def test_the_two_flags_cannot_both_be_given(capsys):
    with pytest.raises(SystemExit):
        library.build_parser().parse_args(["add", "u", "--text-only", "--all-files"])
    capsys.readouterr()


def test_add_records_text_only_so_a_later_grep_is_not_assumed_complete(tmp_path, capsys):
    store = make_store(tmp_path)
    target = store / "repos" / "github.com--encode--httpx"
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/encode/httpx\n", ""),
            "rev-parse --abbrev-ref HEAD": (0, "main\n", ""),
            "rev-parse --short HEAD": (0, "abc1234\n", ""),
        }
    )
    argv = ["add", "https://github.com/encode/httpx", "--root", str(store)]
    library.cmd_add(library.build_parser().parse_args(argv), clone_into(target, git))
    capsys.readouterr()

    assert "text-only: yes" in (target / "SOURCE.md").read_text(encoding="utf-8")
    assert library.recorded_text_only(target)
    ran = [" ".join(call) for call in git.calls]
    assert any("sparse-checkout set --no-cone" in line for line in ran)


def test_a_failed_sparse_step_restores_the_full_checkout_rather_than_leaving_root_files(tmp_path, capsys):
    """The repair matters more than the exclusion. A `--sparse` clone starts with only its root
    files checked out, so a failed `sparse-checkout set` leaves an entry that is present, is a real
    git clone, passes every check this script makes, and holds almost none of the repo — the store's
    characteristic silent failure. The entry must end up complete and the run must end up loud."""
    store = make_store(tmp_path)
    target = store / "repos" / "github.com--encode--httpx"
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/encode/httpx\n", ""),
            "sparse-checkout set": (128, "", "fatal: unable to write sparse-checkout file"),
            "sparse-checkout disable": (0, "", ""),
        }
    )
    argv = ["add", "https://github.com/encode/httpx", "--root", str(store)]

    with pytest.raises(library.LibraryError, match="restored to every file"):
        library.cmd_add(library.build_parser().parse_args(argv), clone_into(target, git))
    capsys.readouterr()

    written = (target / "SOURCE.md").read_text(encoding="utf-8")
    assert "text-only" not in written, "the entry must not claim a narrowing that did not happen"
    assert "url: https://github.com/encode/httpx" in written, "and it must still be a conformant entry"
    assert any("sparse-checkout disable" in " ".join(call) for call in git.calls)


def test_a_sparse_checkout_nothing_records_is_a_finding(tmp_path):
    """The direction that matters, and it is not this script's own doing that it catches: an entry
    narrowed by a hand-run path-based `sparse-checkout` reads to every later session as a whole
    repo, so a grep that finds nothing is taken as an answer rather than as a question about what
    was checked out."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/a/b\n", ""),
            "config --get core.sparseCheckout": (0, "true\n", ""),
            "symbolic-ref -q HEAD": (0, "refs/heads/main\n", ""),
        }
    )
    findings = library.check_entry(git, store, entry)["findings"]
    assert any("does not see the whole" in f for f in findings)


def test_an_entry_claiming_text_only_over_a_full_checkout_is_a_finding(tmp_path):
    store = make_store(tmp_path)
    entry = make_clone(
        store, "github.com--a--b", provenance="url: u\nkind: repo-clone\nref: r\nfetched: f\ntext-only: yes\n"
    )
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/a/b\n", ""),
            "config --get core.sparseCheckout": (1, "", ""),
            "symbolic-ref -q HEAD": (0, "refs/heads/main\n", ""),
        }
    )
    findings = library.check_entry(git, store, entry)["findings"]
    assert any("core.sparseCheckout is not true" in f for f in findings)


def test_a_text_only_entry_that_matches_its_own_record_is_not_a_finding(tmp_path):
    store = make_store(tmp_path)
    entry = make_clone(
        store, "github.com--a--b", provenance="url: u\nkind: repo-clone\nref: r\nfetched: f\ntext-only: yes\n"
    )
    git = FakeGit(
        {
            "remote get-url origin": (0, "https://github.com/a/b\n", ""),
            "config --get core.sparseCheckout": (0, "true\n", ""),
            "config --get-all remote.origin.fetch": (0, "+refs/heads/main:refs/remotes/origin/main\n", ""),
            "symbolic-ref -q HEAD": (0, "refs/heads/main\n", ""),
        }
    )
    assert library.check_entry(git, store, entry)["findings"] == []


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


# --------------------------------------------------------------------------------------------
# size, and the clone lifecycle
#
# Every sequence here was measured on 2026-09-07 before it was code, and two of the measurements
# contradict what the obvious implementation would have done. Each test names which one it pins.


def fill(entry: Path, name: str, size: int) -> None:
    (entry / name).write_bytes(b"x" * size)


def test_reshallow_deletes_the_tags_and_that_is_the_step_that_reclaims_the_disk():
    """Measured on `encode/httpx`, `.git` in KB: fresh `--depth 1` is 2,492; deepened 400 commits
    and re-shallowed with `fetch --depth 1` + `reset --hard` it reports ONE commit again while the
    disk does not move; adding reflog expire, gc --prune, repack -a -d, prune and gc --aggressive
    reaches 4,852 and stops. Deepening brings the repo's tags, each pinning a deep commit, so every
    object below stays reachable. Delete them and the same clone lands at 2,472 — below where it
    started. The published sequence omits this step and reports success at 95% overhead.
    """
    git = FakeGit({"symbolic-ref": (0, "main\n", ""), " tag": (0, "0.1.0\n0.2.0\n", "")})
    steps = [" ".join(step[3:]) for step in library.reshallow(git, Path("/store/repos/x"))]

    assert steps[0] == "fetch --depth 1 origin main"
    assert "tag -d 0.1.0 0.2.0" in steps, "without this the other four reclaim nothing"
    assert steps.index("tag -d 0.1.0 0.2.0") < steps.index("gc --prune=now -q"), "delete before collecting"


def test_reshallow_on_a_clone_with_no_tags_skips_the_deletion():
    git = FakeGit({"symbolic-ref": (0, "main\n", ""), " tag": (0, "\n", "")})
    steps = [" ".join(step[3:]) for step in library.reshallow(git, Path("/store/repos/x"))]
    assert not any(s.startswith("tag -d") for s in steps)


def test_a_deep_clone_nobody_recorded_is_skipped_rather_than_truncated(tmp_path):
    """Confirmed 2026-09-07 in a real 71-entry library: exactly one entry was deep, it had been
    deepened on purpose to read a dependency's constraint history, and a loop refreshing every entry
    with `fetch --depth 1` would have destroyed that silently. Nothing distinguishes a deliberate
    deepening from an accident, and truncating is the answer that cannot be undone by reading."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    git = FakeGit({"rev-list --count HEAD": (0, "436\n", "")})

    steps, why = library.refresh_plan(git, entry)
    assert steps is None
    assert "skipped rather than truncated" in why


def test_a_recorded_depth_is_refreshed_without_re_shallowing(tmp_path):
    """And any value but `1` counts, including prose: the real library's one deep entry records a
    whole sentence in that field, because the store's convention asks for the divergence *and why*.
    A field that only accepted an integer would have read that as unrecorded and truncated it."""
    store = make_store(tmp_path)
    entry = make_clone(
        store,
        "github.com--a--b",
        provenance="url: u\nkind: repo-clone\nref: r\nfetched: f\ndepth: deepened to ~436 commits, not --depth 1\n",
    )
    git = FakeGit({"rev-list --count HEAD": (0, "436\n", "")})

    steps, why = library.refresh_plan(git, entry)
    assert steps is not None
    assert [" ".join(s[3:]) for s in steps] == ["fetch origin", "reset --hard FETCH_HEAD"]
    assert "not re-shallowed" in why


def test_an_ordinary_shallow_clone_is_re_shallowed(tmp_path):
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    git = FakeGit({"rev-list --count HEAD": (0, "1\n", ""), "symbolic-ref": (0, "main\n", "")})

    steps, why = library.refresh_plan(git, entry)
    assert steps is not None
    assert "re-shallowed" in why


def test_deepen_records_the_intent_so_the_next_update_cannot_undo_it(tmp_path, capsys):
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    args = library.build_parser().parse_args(["deepen", "github.com--a--b", "--root", str(store), "--depth", "500"])

    library.cmd_deepen(args, FakeGit({"rev-list --count HEAD": (0, "501\n", "")}))
    capsys.readouterr()
    assert "depth: 500" in (entry / "SOURCE.md").read_text(encoding="utf-8")
    assert library.recorded_depth(entry) == "500"


def test_a_recorded_depth_replaces_the_line_rather_than_appending_a_second(tmp_path):
    """The provenance file is hand-editable by design, so a second `depth:` line would be
    well-formed, ambiguous, and read by `parse_provenance` as whichever came last."""
    store = make_store(tmp_path)
    body = "url: u\nkind: repo-clone\nref: r\nfetched: f\ndepth: 50\n"
    entry = make_clone(store, "github.com--a--b", provenance=body)
    library.set_provenance_field(entry, "depth", "1")
    body = (entry / "SOURCE.md").read_text(encoding="utf-8")

    assert body.count("depth:") == 1
    assert "depth: 1" in body
    assert "note" not in body, "no field is invented on the way past"


def test_reshallow_refuses_a_detached_head_because_its_tags_may_be_the_point(tmp_path):
    """`check` already treats a detached HEAD as the pinned-at-a-tag signature. Deleting every tag
    there destroys the thing the clone exists to read."""
    store = make_store(tmp_path)
    make_clone(store, "github.com--a--b")
    args = library.build_parser().parse_args(["reshallow", "github.com--a--b", "--root", str(store)])
    git = FakeGit({"symbolic-ref": (1, "", "fatal: ref HEAD is not a symbolic ref")})

    with pytest.raises(library.LibraryError, match="detached HEAD"):
        library.cmd_reshallow(args, git)


def test_add_asks_before_cloning_a_repo_the_host_calls_large(tmp_path, capsys):
    """Exit 3, not a prompt: this runs inside an agent's Bash call, where an interactive prompt
    hangs with nothing to type into. `--yes` is the documented way past it."""
    store = make_store(tmp_path)
    big = FakeGit({"gh api": (0, f"{600 * 1024}\n", "")})
    argv = ["add", "https://github.com/nodejs/node", "--root", str(store)]

    assert library.main(argv, big) == library.NEEDS_DECISION
    assert "600 MB" in capsys.readouterr().err
    assert not (store / "repos" / "github.com--nodejs--node").exists()


def test_the_reported_size_is_a_trigger_and_the_warning_never_predicts_a_number(tmp_path, capsys):
    """Measured against five real entries at depth 1: on-disk cost ran 0.23x the reported size
    (`cpython`) to 1.32x (`Roo-Code`). A 5.7x spread and not an upper bound, so a warning quoting a
    predicted figure would have been wrong by 4x in the reassuring direction."""
    store = make_store(tmp_path)
    huge = FakeGit({"gh api": (0, "999999\n", "")})
    library.main(["add", "https://github.com/nodejs/node", "--root", str(store)], huge)
    err = capsys.readouterr().err
    assert "not a prediction" in err
    assert "0.2x and 1.3x" in err


def test_a_non_github_url_is_cloned_without_a_size_question(tmp_path):
    """The size probe is GitHub's API and nothing else. A host it cannot ask must not become a host
    it refuses to clone from."""
    assert library.reported_size_mb(FakeGit(), "https://gitlab.com/group/sub/proj") is None
    assert library.reported_size_mb(FakeGit({"gh api": (0, "1024\n", "")}), "https://github.com/a/b") == 1


def test_size_splits_the_git_directory_from_the_working_tree(tmp_path):
    """They have different remedies and the ratio says which applies: a big `.git` at one commit is
    large blobs, a big tree at one commit is vendored directories. Measured on the worst real entry —
    940 MB at ONE commit, 675 MB of it a single vendored `deps/`."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    fill(entry, "vendored.bin", 4 * library.MB)
    fill(entry / ".git", "pack", 1 * library.MB)

    row = library.entry_size(FakeGit({"rev-list --count HEAD": (0, "1\n", "")}), store, entry)
    assert library.mb(row.total) == 5
    assert library.mb(row.git) == 1
    assert library.mb(row.worktree) == 4
    assert not row.deepened


def test_size_reports_only_what_is_at_or_above_the_minimum(tmp_path, capsys):
    store = make_store(tmp_path)
    fill(make_clone(store, "github.com--big--one"), "blob", 3 * library.MB)
    fill(make_clone(store, "github.com--small--one"), "blob", 1)
    args = library.build_parser().parse_args(["size", "--root", str(store), "--min", "2"])

    payload = library.cmd_size(args, FakeGit({"rev-list --count HEAD": (0, "1\n", "")}))
    out = capsys.readouterr().out
    assert [row["entry"] for row in payload["over_min"]] == ["repos/github.com--big--one"]
    assert "github.com--small--one" not in out
    assert "2 entries" in out, "the total still counts everything"


def test_ungreppable_is_measured_by_content_and_never_by_extension(tmp_path):
    """Deliberately a different rule from the exclusion patterns, so the report can contradict them.

    Extensions are what an exclusion can express; content is what is there. Measured 2026-09-08 over
    the real library: 620 files and 16 MB carry no extension at all and are binary — 1.25% of the
    ungreppable weight, which no pattern can reach. Small enough to be the answer rather than a
    reason for a second, size-based filter, and visible only because this measure ignores the list.
    """
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    (entry / "notes.md").write_bytes(b"plain text, greppable\n" * 100)
    (entry / "photo.png").write_bytes(b"this png is somehow pure text\n" * 100)
    (entry / "a.out").write_bytes(b"\x7fELF\x00" + b"x" * 4096)
    (entry / ".git" / "pack").write_bytes(b"\x00" * (2 * library.MB))

    dark = library.ungreppable_bytes(entry)
    assert dark == (entry / "a.out").stat().st_size, "extensionless binary counts, text-in-a-png does not"


def test_size_leaves_the_ungreppable_column_out_unless_it_is_asked_for(tmp_path, capsys):
    """It reads every file in the store — 184,279 files in 2.9s warm on a 3 GB library, measured
    2026-09-08 — which is cheap enough to offer and not cheap enough to always charge for."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    fill(entry, "blob.png", 3 * library.MB)
    git = FakeGit({"rev-list --count HEAD": (0, "1\n", "")})

    plain = library.cmd_size(library.build_parser().parse_args(["size", "--root", str(store), "--min", "0"]), git)
    assert "ungreppable_mb" not in plain
    assert "ungreppable_mb" not in plain["over_min"][0]

    argv = ["size", "--root", str(store), "--min", "0", "--ungreppable"]
    measured = library.cmd_size(library.build_parser().parse_args(argv), git)
    assert measured["over_min"][0]["ungreppable_mb"] == 0, "a file of `x` bytes is greppable whatever it is called"
    capsys.readouterr()


def test_the_ungreppable_share_is_taken_against_the_working_trees(tmp_path, capsys):
    """`.git` is ungreppable in its entirety and is outside the numerator by design, so dividing by
    a store total that includes it would report the saving as smaller than it is."""
    store = make_store(tmp_path)
    entry = make_clone(store, "github.com--a--b")
    (entry / "asset.png").write_bytes(b"\x00" * (3 * library.MB))
    fill(entry / ".git", "pack", 9 * library.MB)
    argv = ["size", "--root", str(store), "--min", "0", "--ungreppable"]

    library.cmd_size(library.build_parser().parse_args(argv), FakeGit({"rev-list --count HEAD": (0, "1\n", "")}))
    out = capsys.readouterr().out
    assert "3 MB of 3 MB of working tree (100%)" in out


def test_tree_size_does_not_follow_a_symlink_out_of_the_store(tmp_path):
    """A library entry linking somewhere else would otherwise bill that directory to the store, and
    a link into a parent would recurse."""
    store = make_store(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "huge").write_bytes(b"x" * (2 * library.MB))
    entry = make_clone(store, "github.com--a--b")
    (entry / "link").symlink_to(outside)

    assert library.mb(library.tree_size(entry)) == 0
