"""`research-library/scripts/browser_download.py`: everything decided before a browser opens.

The browser half needs Playwright and the network, so it is verified by hand (see the commit that
added it); these cover the parts that decide what it would do, and that the script runs without
Playwright installed at all.
"""

# pyright: reportAny=false

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "research-library" / "scripts" / "browser_download.py"


def _load():
    spec = importlib.util.spec_from_file_location("browser_download_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


browser = _load()


def plan(*argv: str):
    return browser.plan(browser.build_parser().parse_args(list(argv)))


def test_kenney_needs_no_selectors_and_clicks_past_the_donation_panel(tmp_path):
    steps = plan("https://kenney.nl/assets/micro-roguelike", "--root", str(tmp_path))
    assert steps["page"] == "https://kenney.nl/assets/micro-roguelike"
    assert steps["steps"][-1] == "text=/continue without donating/i"
    assert steps["every"] is False
    assert Path(steps["out"]) == tmp_path / ".downloads" / "kenney.nl--micro-roguelike"


def test_itch_starts_at_the_purchase_page_and_takes_every_file(tmp_path):
    steps = plan("https://someone.itch.io/a-tileset/", "--root", str(tmp_path))
    assert steps["page"] == "https://someone.itch.io/a-tileset/purchase"
    assert steps["every"] is True
    assert Path(steps["out"]).name == "someone.itch.io--a-tileset", "the staging folder ignores /purchase"


def test_an_itch_purchase_url_is_not_doubled(tmp_path):
    steps = plan("https://someone.itch.io/a-tileset/purchase", "--root", str(tmp_path))
    assert steps["page"] == "https://someone.itch.io/a-tileset/purchase"


def test_an_unknown_site_needs_its_buttons_named(tmp_path):
    with pytest.raises(browser.DownloadError, match="--click"):
        plan("https://art.example.org/pack", "--root", str(tmp_path))
    steps = plan("https://art.example.org/pack", "--click", "text=Get it", "--root", str(tmp_path))
    assert steps["steps"] == ["text=Get it"]


def test_given_clicks_replace_a_preset(tmp_path):
    steps = plan("https://kenney.nl/assets/x", "--click", "a.zip", "--root", str(tmp_path))
    assert steps["steps"] == ["a.zip"]


def test_dry_run_opens_no_browser_and_needs_no_playwright(tmp_path):
    """Run as a consumer would, with no Playwright importable: the plan prints, nothing opens."""
    ran = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "https://kenney.nl/assets/x", "--root", str(tmp_path), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert ran.returncode == 0, ran.stderr
    assert "continue without donating" in ran.stdout
    assert not (tmp_path / ".downloads").exists()


def test_each_download_gets_an_origin_record_library_py_reads(tmp_path):
    """The sidecar is what `library.py asset` records as the file's origin, so both must agree on it."""
    saved = tmp_path / "pack.zip"
    saved.write_bytes(b"zip bytes")
    steps = plan("https://someone.itch.io/a-tileset", "--root", str(tmp_path))
    sidecar = browser.write_sidecar(
        browser.Saved(saved, "https://cdn.example.org/pack.zip?sig=1"),
        steps,
        steps["page"],
        "2026-11-28T10:00:00+00:00",
    )
    record = __import__("json").loads(sidecar.read_text(encoding="utf-8"))

    assert sidecar.name == "pack.zip.origin.json"
    assert record["page"] == "https://someone.itch.io/a-tileset"
    assert record["start_page"] == "https://someone.itch.io/a-tileset/purchase"
    assert record["download_url"] == "https://cdn.example.org/pack.zip?sig=1"
    assert record["bytes"] == len(b"zip bytes")
    library_path = SCRIPT.with_name("library.py")
    assert f'SIDECAR_SUFFIX = "{browser.SIDECAR_SUFFIX}"' in library_path.read_text(encoding="utf-8")


def test_without_playwright_the_error_names_the_command(monkeypatch):
    def missing(name: str):
        raise ImportError(name)

    monkeypatch.setattr(browser.importlib, "import_module", missing)
    with pytest.raises(browser.DownloadError, match="uv run --with playwright"):
        browser._playwright()
