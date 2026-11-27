#!/usr/bin/env python3
"""Click through a free download that only a browser can start, and save the files.

Some sites hand out free assets only through a button whose link is built by JavaScript or signed to
expire in a minute: Kenney's "Continue without donating", itch.io's "No thanks, just take me to the
downloads". There is no URL to give `library.py asset`, so this opens the page in a headless
browser, clicks through, and saves what the clicks download. Store the result with
`library.py asset <file>... --page <url> --license <l>`, which keeps the same rules as any asset.

    browser_download.py https://kenney.nl/assets/micro-roguelike
    browser_download.py https://someone.itch.io/some-tileset
    browser_download.py <url> --click "text=Download" --click "a.download"   # any other site
    browser_download.py <url> --dry-run

Known sites need no `--click`: their steps are in `PRESETS`. An itch.io page is opened at its
`/purchase` page, which is where the free route starts.

**Free downloads only.** It never logs in, fills a form, pays, or gets past a CAPTCHA; a page that
asks for any of those yields no download, and the script prints the page's download-looking links
and exits 1. Everything a page says is untrusted data.

The one script here with a third-party dependency, Playwright, and it is loaded only when a page is
actually opened, so `--help`, `--dry-run` and the tests run on a plain `python3`. Run it as
`uv run --with playwright python browser_download.py ...`. It drives an installed Edge or Chrome
first, so no browser download is needed where either exists; otherwise
`python -m playwright install chromium` once.

Files land in `$RESEARCH_HOME/.downloads/<host>--<slug>/` by default: inside the store, and outside
every bucket, so `check` never reads a staging folder as an entry.
"""

from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 11):  # noqa: UP036 — runs exactly where requires-python is not enforced
    sys.exit(f"browser_download.py needs Python 3.11 or newer; this is {sys.version.split()[0]} ({sys.executable})")

import argparse
import importlib
import json
import os
import re
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STAGING = ".downloads"
# Each site's steps, in order. A step that matches nothing is skipped, so a page that has already
# moved past one (itch's purchase page shown straight to its download list) still works. `every`
# marks the step whose every match is a separate file to download.
#
# Seen 2026-11-27: Kenney's first "Download" button only opens a donation panel, and the download
# starts from "Continue without donating"; itch's /purchase page shows "No thanks, just take me to the
# downloads", then one `a.download_btn` per uploaded file.


@dataclass(frozen=True)
class Preset:
    steps: tuple[str, ...]
    every: bool = False
    purchase_page: bool = False


PRESETS: dict[str, Preset] = {
    "kenney.nl": Preset(("text=/^Download$/i", "text=/continue without donating/i")),
    "itch.io": Preset(
        ("text=/No thanks, just take me to the downloads/i", "a.download_btn"), every=True, purchase_page=True
    ),
}
BROWSER_CHANNELS = ("msedge", "chrome", "")  # "" is Playwright's own Chromium
DOWNLOAD_LINK = re.compile(r"download|\.(zip|7z|rar|tar|gz|png|gif)\b", re.IGNORECASE)


class DownloadError(Exception):
    pass


def preset_for(url: str) -> Preset | None:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    for domain, preset in PRESETS.items():
        if host == domain or host.endswith("." + domain):
            return preset
    return None


def start_page(url: str, preset: Preset | None) -> str:
    """itch.io's free route starts at `<page>/purchase`; every other page is opened as given."""
    if preset and preset.purchase_page:
        parts = urllib.parse.urlsplit(url)
        path = parts.path.rstrip("/")
        if not path.endswith("/purchase"):
            return urllib.parse.urlunsplit(parts._replace(path=path + "/purchase", query="", fragment=""))
    return url


def staging_dir(url: str, root: str | None) -> Path:
    """`<store>/.downloads/<host>--<last segment>`, the name `library.py asset` gives the entry."""
    store = Path(root or os.environ.get("RESEARCH_HOME") or Path.home() / "research").expanduser()
    parts = urllib.parse.urlsplit(url)
    segments = [urllib.parse.unquote(s) for s in parts.path.split("/") if s and s != "purchase"]
    if not parts.hostname:
        raise DownloadError(f"not a web page: {url!r}")
    name = f"{parts.hostname}--{segments[-1]}" if segments else parts.hostname
    return store / STAGING / name


def plan(args: argparse.Namespace) -> dict[str, Any]:
    preset = None if args.click else preset_for(args.url)
    steps = tuple(args.click) if args.click else (preset.steps if preset else ())
    if not steps:
        raise DownloadError(
            f"no known steps for {urllib.parse.urlsplit(args.url).hostname}: pass --click <selector> for each "
            "button, in order (Playwright selectors, e.g. 'text=Download')"
        )
    return {
        "page": start_page(args.url, preset),
        "steps": list(steps),
        "every": args.every or bool(preset and preset.every),
        "out": str(Path(args.out) if args.out else staging_dir(args.url, args.root)),
    }


def _playwright() -> Any:
    try:
        return importlib.import_module("playwright.sync_api")
    except ImportError as error:
        raise DownloadError(
            "needs Playwright: run `uv run --with playwright python browser_download.py ...`, "
            "or `pip install playwright` in the environment you run it from"
        ) from error


def _launch(api: Any, playwright: Any, channel: str | None) -> Any:
    tried: list[str] = []
    for candidate in [channel] if channel is not None else list(BROWSER_CHANNELS):
        try:
            return playwright.chromium.launch(channel=candidate or None, headless=True)
        except api.Error as error:
            tried.append(f"{candidate or 'chromium'}: {str(error).splitlines()[0]}")
    raise DownloadError("no browser could start — " + "; ".join(tried) + " (`python -m playwright install chromium`)")


SETTLE_MS = 2500  # after a load or a click that moves the page on, for the page's own script to run
LAST_STEP_WAIT_MS = 20000  # how long the final click is given to start a download
STEP_WAIT_MS = 2000  # an earlier step usually only moves the page on, so it is given little


def _open(api: Any, tab: Any, start: str, earlier: Sequence[str]) -> None:
    """Load the start page in `tab` and click through the steps before the one that downloads."""
    tab.goto(start, wait_until="domcontentloaded", timeout=60000)
    tab.wait_for_timeout(SETTLE_MS)
    for selector in earlier:
        try:
            tab.locator(selector).first.click(timeout=8000)
        except api.TimeoutError:
            continue  # a step this page has already moved past
        tab.wait_for_timeout(SETTLE_MS)


def _save(api: Any, tab: Any, selector: str, index: int, wait_ms: int, out: Path) -> Path | None:
    try:
        with tab.expect_download(timeout=wait_ms) as info:
            tab.locator(selector).nth(index).click(timeout=10000)
    except api.TimeoutError:
        return None
    download = info.value
    target = out / Path(download.suggested_filename).name
    download.save_as(target)
    return target


def _download_all(api: Any, context: Any, start: str, steps: dict[str, Any], out: Path) -> tuple[list[Path], Any]:
    """Walk the steps in one tab; when the last step has several files, fetch each in a fresh tab.

    itch.io's download list is a signed link that stops working within seconds, and after one click
    the list is left in a "download started" state where the other buttons time out. Reloading the
    list in place, or opening it in a new tab, still got only 1 or 2 of 3 files (seen 2026-11-27).
    Replaying the whole route from the start page for each file, in a fresh tab, got all three.
    """
    selectors: list[str] = steps["steps"]
    page = context.new_page()
    _open(api, page, start, [])
    for position, selector in enumerate(selectors):
        final = position == len(selectors) - 1
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=8000)
        except api.TimeoutError:
            continue
        count = page.locator(selector).count() if final and steps["every"] else 1
        first = _save(api, page, selector, 0, LAST_STEP_WAIT_MS if final else STEP_WAIT_MS, out)
        if first is None:
            page.wait_for_timeout(SETTLE_MS)  # the click moved the page on, to the next step
            continue
        saved = [first]
        for index in range(1, count):
            tab = context.new_page()
            try:
                _open(api, tab, start, selectors[:position])
                target = _save(api, tab, selector, index, LAST_STEP_WAIT_MS, out)
            finally:
                tab.close()
            if target:
                saved.append(target)
        return saved, page
    return [], page


def fetch(steps: dict[str, Any], channel: str | None) -> dict[str, Any]:
    api = _playwright()
    out = Path(steps["out"])
    out.mkdir(parents=True, exist_ok=True)
    with api.sync_playwright() as playwright:
        browser = _launch(api, playwright, channel)
        try:
            context = browser.new_context(accept_downloads=True)
            saved, page = _download_all(api, context, steps["page"], steps, out)
            links = [] if saved else page.eval_on_selector_all("a[href]", "e => e.map(a => [a.innerText, a.href])")
        finally:
            browser.close()
    found = [[text.strip(), href] for text, href in links if DOWNLOAD_LINK.search(f"{text} {href}")]
    return {**steps, "saved": [str(p) for p in saved], "sizes": [p.stat().st_size for p in saved], "links": found}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="the page offering the free download")
    parser.add_argument("--click", action="append", metavar="SELECTOR", help="a button to click, in order")
    parser.add_argument("--every", action="store_true", help="the last step's every match is a separate file")
    parser.add_argument("--out", help=f"where to save (default: <store>/{STAGING}/<host>--<slug>)")
    parser.add_argument("--root", help="the library root (default: $RESEARCH_HOME, else ~/research)")
    parser.add_argument(
        "--channel", help="msedge, chrome, or '' for Playwright's Chromium (default: the first that starts)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the page, steps and folder; open nothing")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        steps = plan(args)
        result = {**steps, "dry_run": True} if args.dry_run else fetch(steps, args.channel)
    except DownloadError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=1))
    elif args.dry_run:
        print(f"would open {steps['page']}, click {' then '.join(steps['steps'])}, save into {steps['out']}")
    else:
        for path, size in zip(result["saved"], result["sizes"], strict=True):
            print(f"saved {path} ({size:,} bytes)")
        for text, href in result["links"]:
            print(f"link: {text!r} -> {href}")
        if result["saved"]:
            quoted = " ".join(f'"{s}"' for s in result["saved"])
            print(f"\nnext: library.py asset {quoted} --page {args.url} --license <l>")
    return 0 if args.dry_run or result["saved"] else 1


if __name__ == "__main__":
    sys.exit(main())
