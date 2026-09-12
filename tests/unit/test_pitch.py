"""Tests for `skills/repo-pitch/scripts/pitch.py`.

The script's whole claim is that its gate/warn split is a measurement rather than a preference, so
the first test here asserts that invariant directly: a rule may block only where the controlled
corpus says it almost never fires. Everything else is one test per rule, plus the README extractor,
which is where the real defects were — three of them, each found by running it against a second
repo rather than by reading it.
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
SCRIPT = REPO_ROOT / "skills" / "repo-pitch" / "scripts" / "pitch.py"


def _load():
    spec = importlib.util.spec_from_file_location("pitch_script", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pitch = _load()


def levels(report) -> dict[str, str]:
    return {finding.rule: finding.level for finding in report.findings}


# What makes this a checker rather than an opinion


def test_a_rule_may_block_only_where_the_controlled_corpus_clears_it():
    """The invariant the whole script rests on, asserted rather than described.

    Each rule carries the rate at which it fires against 85,842 Debian synopses — a corpus governed
    by written rules and checked by lintian. A rule that fires there is a rule about taste, and the
    script must not let it block. If somebody adds a rule with a high rate and marks it a gate, this
    fails.
    """
    for rule in pitch.RULES.values():
        if rule.debian_rate is None:
            assert rule.level == "style", f"{rule.name} has no measurement, so it cannot gate or warn"
        elif rule.debian_rate <= pitch.GATE_MAX_FALSE_POSITIVE:
            assert rule.level == "gate", f"{rule.name} is clean on the control corpus and should gate"
        else:
            assert rule.level == "warn", f"{rule.name} fires on real linted synopses and must not block"


def test_the_gate_threshold_sits_in_empty_space():
    """The 0.35% line is only defensible because nothing is near it: moving it slightly must not
    reclassify any rule. If a future rule lands in the gap, this fails and the line needs an
    argument rather than a number."""
    rates = sorted(rule.debian_rate for rule in pitch.RULES.values() if rule.debian_rate is not None)
    below = [rate for rate in rates if rate <= pitch.GATE_MAX_FALSE_POSITIVE]
    above = [rate for rate in rates if rate > pitch.GATE_MAX_FALSE_POSITIVE]
    assert max(below) <= 0.35
    assert min(above) >= 1.0, "a rule has landed in the gap the threshold relies on"


# The rules themselves


def test_a_clean_pitch_is_clean():
    """jq's real description, which violates nothing and is 27 characters."""
    assert check("Command-line JSON processor", name="jq").findings == []


def check(text: str, **kwargs):
    return pitch.check_text(text, **kwargs)


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("A tool that turns one thing into another thing entirely, for people who need that", "leading_article"),
        ("The Kubernetes package manager, rewritten again from scratch for the third time now", "leading_article"),
        ("Docs at https://example.com", "contains_url"),
        ("🚀 Ship faster", "contains_emoji"),
        ("Ship it :rocket:", "contains_emoji"),
        ("A seamless developer experience", "superlative"),
        ("We build tools for developers", "first_person"),
        ("Trailing space ", "stray_whitespace"),
        ("Double  space", "stray_whitespace"),
    ],
)
def test_gate_rules_fire_and_block(text, rule):
    report = check(text)
    assert levels(report).get(rule) == "gate", f"{rule} should block on {text!r}"
    assert report.gated


def test_a_description_over_a_hundred_characters_blocks():
    report = check("x" * 101)
    assert levels(report)["too_long"] == "gate"


def test_between_eighty_and_a_hundred_warns_rather_than_blocks():
    """2.32% of linted synopses are over 80, so this cannot be a gate — but it is the most useful
    signal in the set, because 80 is the shortest surface that carries a pitch unabridged."""
    report = check("y" * 85)
    assert levels(report) == {"over_80": "warn"}
    assert not report.gated


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("Reads, writes, validates, and signs", "feature_list"),
        ("Static typing for widgets, built on widgets", "repeats_name"),
    ],
)
def test_warn_rules_never_block(text, rule):
    report = check(text, name="widgets")
    assert levels(report).get(rule) == "warn"
    assert not report.gated


def test_opening_with_your_own_name_and_a_copula_is_a_different_finding_from_mentioning_it():
    """Both are about the name and they are not the same defect. Opening with it is near-pure waste
    — the surface renders the name directly above — while mentioning it later is sometimes the
    clearest phrasing, so only the first may block."""
    opening = check("Widgets is a library for widget wrangling", name="Widgets")
    assert levels(opening)["restates_name"] == "gate"

    mentioning = check("Type stubs for widgets", name="widgets")
    assert levels(mentioning) == {"repeats_name": "warn"}


def test_an_empty_pitch_reports_once_rather_than_every_rule():
    report = check("   ")
    assert [finding.rule for finding in report.findings] == ["stray_whitespace"]


# Surfaces


def test_exactly_eighty_passes_show_hn_because_the_check_is_greater_than():
    """`news.arc` reads `(len> title title-limit*)` with the limit at 80, so 80 itself is accepted
    even though the error message says "less than 80". 39 titles in a 1,000-title sample sit at
    exactly 80 and none above."""
    assert check("z" * 80, surface=pitch.SURFACES["hn"]).findings == []
    over = check("z" * 81, surface=pitch.SURFACES["hn"])
    assert any(finding.rule == "surface_limit" for finding in over.findings)


def test_a_soft_surface_limit_warns_rather_than_blocks():
    """AppStream emits `summary-too-long` as a validator warning, not a rejection."""
    report = check("w" * 95, surface=pitch.SURFACES["appstream"])
    limit = next(finding for finding in report.findings if finding.rule == "surface_limit")
    assert limit.level == "warn"


def test_x_counts_weight_not_characters():
    """twitter-text v3: Latin costs 1, anything outside those ranges costs 2, and a URL is a flat 23
    whatever it says. A character count would call all three of these the same length."""
    assert pitch.weighted_length("hello") == 5
    assert pitch.weighted_length("日本語") == 6
    assert pitch.weighted_length("see https://example.com/a/very/long/path/indeed") == 4 + 23


def test_a_url_costs_the_same_however_long_it_is():
    short = pitch.weighted_length("https://a.co")
    long = pitch.weighted_length("https://example.com/" + "x" * 300)
    assert short == long == pitch.X_URL_WEIGHT


# House style, which has no default


def test_the_two_style_axes_are_off_unless_asked_for():
    """Obsidian mandates a trailing period, Homebrew forbids one, Debian omits it in 99.1% of
    synopses. A default here would be wrong for about half of all targets."""
    assert check("Ends with a period.").findings == []
    assert check("ends lowercase").findings == []


@pytest.mark.parametrize(
    ("text", "style", "fires"),
    [
        ("No period here", {"trailing-period": "required"}, True),
        ("Has a period.", {"trailing-period": "required"}, False),
        ("Has a period.", {"trailing-period": "forbidden"}, True),
        ("No period here", {"trailing-period": "forbidden"}, False),
        ("lowercase opener", {"leading-capital": "required"}, True),
        ("Capital opener", {"leading-capital": "required"}, False),
        ("Capital opener", {"leading-capital": "forbidden"}, True),
    ],
)
def test_a_style_axis_blocks_only_in_the_direction_it_was_given(text, style, fires):
    report = check(text, style=style)
    assert bool(report.findings) is fires


def test_etc_is_not_a_trailing_period():
    assert check("Widgets, gadgets, etc.", style={"trailing-period": "forbidden"}).gated is False


def test_an_unknown_style_axis_is_refused_rather_than_ignored():
    with pytest.raises(SystemExit):
        pitch.parse_style(["trailing-comma=required"])
    with pytest.raises(SystemExit):
        pitch.parse_style(["trailing-period=maybe"])


# The README extractor, where the real bugs were


def test_a_heading_is_never_the_short_description():
    """Found by running the extractor against a second repo: `power-user-linux-setup`'s H1 is 30
    characters, so once the leading `#` was stripped it cleared the minimum and was returned as the
    pitch. The heading has to be rejected before the `#` comes off."""
    markdown = "# Power User Linux Setup (PULSE)\n\nAn opinionated workstation setup for one machine.\n"
    assert pitch.readme_pitch(markdown) == "An opinionated workstation setup for one machine."


def test_a_link_keeps_its_text_while_an_image_is_dropped():
    """The other real bug: deleting both markdown forms is the obvious one-liner and it eats words.
    This repo's own README opens with a linked term, and dropping it produced "Personal — plain
    SKILL.md directories"."""
    markdown = (
        "# repo\n\n![badge](https://img.example/b.svg)\n\nPersonal [Agent Skills](https://x.example) in plain files.\n"
    )
    assert pitch.readme_pitch(markdown) == "Personal Agent Skills in plain files."


def test_a_wrapped_paragraph_is_joined_rather_than_truncated():
    """Every formatter in this repo family wraps prose, so the short description arrives split
    across two or three lines. Reading only the first line silently truncates it."""
    markdown = "# repo\n\nA sentence that the formatter\nwrapped across two lines entirely.\n"
    assert pitch.readme_pitch(markdown) == "A sentence that the formatter wrapped across two lines entirely."


def test_furniture_is_skipped_until_real_prose_appears():
    markdown = (
        "# repo\n\n"
        "[![build](https://img.example/ci.svg)](https://ci.example)\n\n"
        "<picture><source srcset='a.png'><img alt='logo' src='b.png'></picture>\n\n"
        "Installation instructions live below.\n\n"
        "Command-line JSON processor.\n"
    )
    assert pitch.readme_pitch(markdown) == "Command-line JSON processor."


def test_a_readme_with_no_prose_returns_nothing_rather_than_furniture():
    assert pitch.readme_pitch("# repo\n\n![badge](https://img.example/b.svg)\n") is None


def test_drift_comparison_ignores_wrapping_and_case_only():
    """Two surfaces that differ only in whitespace are the same string; two that differ in a word
    are not, however small the word. `opencode` carries "The open source coding agent." on GitHub
    and "The open source AI coding agent." in its README."""
    assert pitch.normalise("A  b\nc") == pitch.normalise("a b c")
    assert pitch.normalise("The open source coding agent.") != pitch.normalise("The open source AI coding agent.")
