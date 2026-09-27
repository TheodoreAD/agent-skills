# Why these testing defaults

Extracted from `python-conventions`' rationale on 2026-08-31, where this was section 7. The
surrounding sections it referred to now live in that skill's own rationale.

## 7. Testing conventions

**Fixture scope directly ties to the modules-as-singletons concern** in `python-conventions`, which
is where that pattern is decided. Official rule of thumb: narrowest scope that keeps tests correct,
widen only when setup is genuinely expensive; pytest's own docs warn that a `monkeypatch` used
inside a broad-scoped fixture stays live for the _whole_ scope, not just one test — the exact
mechanism by which a shared-scope fixture silently leaks state across tests that look independent.
**Practical rule for this repo family's module-singleton pattern**: construct the expensive object
at module/session scope, but reset/monkeypatch its _mutable_ state via a function-scoped fixture —
cheap construction stays shared, isolation stays per-test. `conftest.py`: keep one root file for
genuinely cross-cutting fixtures, split per-directory only once a real subset of tests needs
fixtures the rest shouldn't see. `parametrize`: attach `ids` once values stop being
self-explanatory.

**DAMP vs. DRY in tests — a real, sourced debate that does _not_ simply inherit the "lean toward
duplication" production-code stance** taken in `python-conventions`' modularity section. Vladimir
Khorikov's reframing ("DRY vs DAMP in Unit Tests", Enterprise Craftsmanship) resolves the popular
"DAMP not DRY" framing as a false dichotomy: "the DRY principle should be applied to the how-to's,
whereas the DAMP principle should be applied to the what-to's." The actionable split: **setup
mechanics (the "how") stay DRY** — pytest fixtures/helpers are exactly the right tool, use them
freely, no tension with anything else in this file — **but the scenario a test verifies (the "what")
stays explicit in that test**, because collapsing genuinely different scenarios into a shared
abstracted mega-test trades away the "read one test top-to-bottom, understand the scenario" property
that's the actual point of a test suite. This is a genuinely different axis from that
production-code DRY decision, not a re-derivation of it — worth stating explicitly so a reader
doesn't assume "this project avoids DRY everywhere" and over-apply it to test bodies.

_Citation check, 2026-08-25 (the now-retired
`plans/2026-08-22-damp-vs-dry-testing-convention-revisit.md`)._ An earlier wording here said
Khorikov's split was "echoed by Brian Okken" and that test bodies "stay duplicated per test, even
when tests look near-identical" — both over-extrapolated, read against the sources. Khorikov's
article never mentions parametrized/data-driven tests at all; its example of misapplied DRY is
shared mutable state (class fields) and an arrange step hidden in a setup method, not a data table.
Okken (Test & Code ep. 160, "DRY, WET, DAMP, AHA", 2021 — transcript in
`okken/testandcode_transcripts`) does not cite Khorikov and is explicitly "on the fence" about the
DAMP-for-tests framing; his own stated rule is readability-first with one standard for production
and test code, and he names parametrization as a sanctioned tool: "if there is duplication,
parameterization, fixtures, and helper functions are great to clean that duplication up, but only if
you can still read the test quickly and understand it." His book's parametrization chapters exist
precisely to replace near-identical repeated test functions. So the sourced position is _not_
"duplicate bodies even when near-identical" — it's "keep the _what_ visible." `parametrize` over a
pure input→expected matrix keeps the _what_ more visible than N copy-pasted bodies (the varying
values are isolated from the fixed logic), so it's expected, not tolerated. The dividing line the
skill now states comes from the pytest-community formulation (Simply The Test, "Keeping DRY or
staying DAMP? When to parametrize tests", 2019): _"If a value needs to be changed to add a new case,
parametrize. If logic needs to be changed to add a new case, create a new test."_ The thing actually
warned against is a parametrized test that branches on its parameters, or a `check_*` helper that
owns the assertion — those hide the scenario; a data table doesn't. The three sources are mirrored
in `$RESEARCH_HOME/pages/testing-dry-vs-damp/` (see the `research-library` skill).

**Fixtures wherever possible — a stated preference of this repo family's owner (2026-08-25), not
just a sourced default.** The "how" side of the split above is not merely _allowed_ to be DRY; it
should be, via `pytest` fixtures specifically. Beyond removing duplication, the argument that made
it a rule is discoverability: setup hand-rolled inside test bodies has no name and no shared
location, so a suite can accumulate three different ways of doing the same thing (three fake-repo
builders, three env-patching idioms) with nothing that ever puts them side by side. Fixtures give
each piece of setup a name and a home (`conftest.py`), which is exactly what makes the duplication
visible and mergeable. This is consistent with every source above — Okken's own list of duplication
cleanups is "parameterization, fixtures, and helper functions" — and with Khorikov's DRY-the-how; it
just makes the fixture the default form of the "how" rather than one option among helpers.
