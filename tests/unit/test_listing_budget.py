"""The listing-budget arithmetic in `skill-fitness`, which is a reverse-engineered contract.

None of this is documented behaviour. It was read out of the Claude Code 2.1.251 binary on
2026-08-31 and confirmed against the CLI's own overflow warning, because the documentation's
account ("descriptions are shortened to fit") is not what the code does — an entry keeps its whole
description or loses all of it. A contract read from someone else's compiled artifact is exactly
the kind that breaks silently on an upgrade, so it is pinned here: when a future CLI changes the
formula, this suite is what says so rather than a report that quietly starts lying.

The load-bearing details, each with a test below:

- the budget is **characters**, computed as 1% of the context window *in tokens* times four, so it
  is model-dependent — the same corpus overflows on a 200k model and fits on a larger one;
- an entry costs exactly what `- <name>: <description>` renders to, description capped at 1536;
- bundled skills are **exempt**: charged first, never demoted, so their cost comes straight out of
  what is left for the user's own;
- demotion is a **greedy fit in descending priority**, not a cut-off, so a long description can be
  dropped while a shorter lower-priority one survives.
"""

# The module under test is a standalone CLI script, loaded by path because `skills/` holds no
# importable package — so every symbol it exposes is Any by construction, not through a missing
# annotation. Structural, so suppressed for the file rather than at every call site.
# pyright: reportAny=false

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FITNESS_PY = REPO_ROOT / "skills" / "skill-fitness" / "scripts" / "fitness.py"


def _load_fitness():
    spec = importlib.util.spec_from_file_location("fitness", FITNESS_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fitness"] = module
    spec.loader.exec_module(module)
    return module


fitness = _load_fitness()


def make_skill(name: str, description: str):
    return fitness.Skill(name=name, scope="test", path=Path("/nonexistent"), description=description)


# --------------------------------------------------------------------------------------------
# What one entry costs


def test_entry_chars_is_the_rendered_line():
    """`- <name>: <description>` — the four characters are "- " and ": ", not an estimate."""
    s = make_skill("plan-docs", "Use when capturing an idea.")
    assert s.entry_chars == len("- plan-docs: Use when capturing an idea.")
    assert s.name_only_chars == len("- plan-docs")


def test_when_to_use_joins_with_a_dash():
    s = make_skill("thing", "does a thing")
    s.when_to_use = "when you need one"
    assert s.listing_text == "does a thing - when you need one"


def test_description_is_capped_in_the_entry_but_not_flagged_as_over_the_spec():
    """Two different limits: 1536 truncates the *listing*, 1024 is what makes a skill valid."""
    s = make_skill("verbose", "x" * 2000)
    assert s.entry_chars == len("- verbose: ") + fitness.LISTING_ENTRY_CAP
    assert len(s.description) > fitness.SPEC_DESC_CAP


# --------------------------------------------------------------------------------------------
# What the budget is


def test_budget_is_one_percent_of_the_window_in_characters(monkeypatch):
    monkeypatch.delenv(fitness.BUDGET_ENV, raising=False)
    assert fitness.listing_budget(200_000) == 8_000
    assert fitness.listing_budget(1_000_000) == 40_000


def test_a_corpus_can_fit_one_model_and_overflow_another(monkeypatch):
    """The finding this whole section exists for: budget follows the model, not the machine."""
    monkeypatch.delenv(fitness.BUDGET_ENV, raising=False)
    measured_listing = 15_486  # this machine, 25 listed entries, 2026-08-31
    assert measured_listing > fitness.listing_budget(200_000)
    assert measured_listing < fitness.listing_budget(1_000_000)


def test_the_env_override_wins_and_is_absolute(monkeypatch):
    monkeypatch.setenv(fitness.BUDGET_ENV, "3000")
    assert fitness.listing_budget(1_000_000) == 3_000
    monkeypatch.setenv(fitness.BUDGET_ENV, "not-a-number")
    assert fitness.listing_budget(200_000) == 8_000


# --------------------------------------------------------------------------------------------
# Priority, which is not the invocation count


def test_priority_decays_with_a_seven_day_half_life(tmp_path):
    now = time.time()
    state = tmp_path / ".claude.json"
    state.write_text(
        json.dumps(
            {
                "skillUsage": {
                    "fresh": {"usageCount": 40, "lastUsedAt": now * 1000},
                    "a-week-old": {"usageCount": 40, "lastUsedAt": (now - 7 * 86400) * 1000},
                    "ancient": {"usageCount": 40, "lastUsedAt": (now - 365 * 86400) * 1000},
                }
            }
        )
    )
    scores = fitness.harness_priority(state, now=now)
    assert scores["fresh"] == pytest.approx(40, rel=1e-3)
    assert scores["a-week-old"] == pytest.approx(20, rel=1e-3)
    # The floor is what keeps a long-unused favourite ahead of a never-used skill.
    assert scores["ancient"] == pytest.approx(4, rel=1e-3)


def test_priority_is_empty_rather_than_wrong_when_the_harness_state_is_absent(tmp_path):
    assert fitness.harness_priority(tmp_path / "nothing.json") == {}


# --------------------------------------------------------------------------------------------
# Who actually loses a description


def test_a_listing_under_budget_demotes_nobody():
    skills = [make_skill("a", "x" * 50), make_skill("b", "x" * 50)]
    sim = fitness.simulate_listing(skills, {}, budget=10_000)
    assert sim["mode"] == "fits"
    assert sim["demoted"] == []


def test_bundled_chars_come_out_of_the_users_share():
    """Exempt cost is not shared pain — it is subtracted before anyone's description is priced."""
    skills = [make_skill("kept", "x" * 200), make_skill("dropped", "x" * 200)]
    priority = {"kept": 10.0, "dropped": 1.0}
    roomy = fitness.simulate_listing(skills, priority, budget=1_000, exempt_chars=0, exempt_count=0)
    squeezed = fitness.simulate_listing(skills, priority, budget=1_000, exempt_chars=600, exempt_count=3)
    assert roomy["mode"] == "fits"
    assert squeezed["demoted"] == ["dropped"]


def test_demotion_is_a_greedy_fit_not_a_cut_off():
    """A long description loses to the budget while a shorter, lower-priority one survives."""
    skills = [
        make_skill("hungry", "x" * 400),  # highest priority, but too big for the room left
        make_skill("modest", "x" * 40),  # lowest priority, and cheap enough to keep
    ]
    priority = {"hungry": 100.0, "modest": 1.0}
    floor = sum(s.name_only_chars for s in skills) + 1
    # Room for the small description and nothing else: the priority order alone does not decide it.
    budget = floor + (skills[1].entry_chars - skills[1].name_only_chars) + 10
    sim = fitness.simulate_listing(skills, priority, budget=budget)
    assert sim["demoted"] == ["hungry"]
