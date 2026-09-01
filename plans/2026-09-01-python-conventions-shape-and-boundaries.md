---
status: idea
updated: 2026-09-01
---

# What `python-conventions` is missing: data shape as an API surface, and how to audit for it

Harvested from a 2026-09-01 session that reviewed `plan-docs`' 3,210-line `plans.py`. The review
itself was `plans/2026-09-01-plans-py-encapsulation-pass.md`, since retired into
`skills/python-refactor-audit/references/pilot.md`; this plan holds only what generalises past that
one file, because that is what belongs in a skill.

**Why it is worth writing up rather than just doing.** The session is a clean case study of the loop
this repo keeps asserting and rarely gets to demonstrate end to end: a convention was stated, the
code was measured against it, the measurement contradicted a stated intention, and the rule that
came out is sharper than either the original guidance or the user's first framing. Nothing here was
reasoned from taste.

## The gap in the skill today

`python-conventions` answers **"what should this code look like"** per topic. It has no procedure
for **"this module grew for two weeks; what is wrong with its shape"** — which is the request that
actually arrives, and the one where a model left alone reaches for the wrong tool (it extracts
helpers on sight, which the skill's own Modularity section flags as `overrides, actively`).

The missing content is not more defaults. It is:

1. a way to **measure** shape problems rather than eyeball them,
2. the **boundary rules** that decide which container a value gets, and
3. a **stopping rule**, since the failure mode of this kind of pass is doing too much.

## 1. The measurements, which are the reusable part

Every number below came from a short `ast`-walk over one file, and each maps to a specific defect.
An agent can run these on any module without reading it, which is the point:

| what to count                                              | what it means when high                                   |
| ---------------------------------------------------------- | --------------------------------------------------------- |
| functions whose leading parameters are the same object(s)  | state constant for a whole invocation, passed by hand     |
| bare `tuple[...]` returns, and sites unpacking them        | the shape is real information and it was thrown away      |
| `dict[str, X]` as a **field or parameter** type            | a record wearing a mapping's clothes                      |
| stringly-keyed access into such a dict (`x.dirs["store"]`) | a typo is a runtime `KeyError` instead of a checker error |
| `dict[str, object]` **returns**                            | usually fine — see the serialisation-boundary rule below  |

Measured on `plans.py`: 69 of 158 functions took `cfg` or `(cfg, routing)`; 22 bare-tuple returns
unpacked at 39 sites; 13 dict fields and 10 dict parameters; 7 stringly-keyed lookups; 0 NamedTuples
against 6 frozen dataclasses.

[DECISION: **the counts are the review, not a preamble to it.** The same session had already run a
diff-scoped review of the file that week and found one bug and two cleanups — nothing structural,
because a diff cannot show state threaded through 69 signatures. Counting is what made the shape
visible, and re-counting afterwards is the only check that a large mechanical diff actually did
something.]

## 2. The boundary rules, and the one that corrects the skill

The user's framing, which is the right frame: **clear boundaries, types that reflect them, objects
over dicts, and each contiguous unit having an API surface callers cannot reach around.** Data shape
is information, and an agent reading a signature to decide what to do with a value is the reader
that suffers most when the shape is anonymous.

Three rules came out of applying that to real code:

**a. The baseline decides whether `NamedTuple` is an upgrade — it is not a general default.**

This is the correction worth shipping, because the user's opening position was that NamedTuples are
"very cheap and increase readability tremendously", and that is true in exactly one direction:

- **bare tuple → `NamedTuple` is a clear upgrade.** Names where there were none; the positional
  surface already exists and is already being unpacked, so nothing new leaks.
- **frozen dataclass → `NamedTuple` is a downgrade.** It _adds_ indexing, unpacking, iteration and
  structural equality — `Point(1, 2) == (1, 2)` is `True` — which is a second, positional API
  surface nobody designed. Inserting a field in the middle silently changes what `x[1]` means at
  every call site, with no error anywhere.

The skill already carries the hazard (the measured `Quantity(5, "ml") < Quantity(300, "mg")` case,
where inherited tuple ordering returns `True` instead of raising). What it does not say is that the
hazard and the benefit are **the same property seen from two sides**, so the question is never "is
NamedTuple nice" but "what is being replaced". That reframing is what makes the rule decidable
rather than a matter of taste.

**b. Validation belongs at parse time, in the constructor — which is what keeps config a frozen
dataclass.** Config is static, read once, and every later reader should be able to assume it is well
formed. `__post_init__` is the stdlib home for that; `NamedTuple` has no equivalent and needs a
`__new__` override or a classmethod factory, which is more ceremony than the dataclass it was meant
to be cheaper than. This is "parse, don't validate" with nothing but the standard library, and it is
worth naming as such because the phrase is what makes it findable.

**c. Dicts are legitimate at a serialisation boundary and nowhere else.** A `dict[str, object]`
built to be handed to `json.dumps` should stay a dict; typing it would be ceremony in both
directions. A `dict[str, Path]` held as a field and read with string literals is a record that lost
its type. The test is whether the keys are **data** (a mapping) or **names the author chose** (a
record).

## 3. The stopping rule

The most likely failure of a pass like this is doing too much, and the skill's Modularity section
already says why
(`a wrong abstraction is harder for an agent to safely touch than duplicated code`). Two things
sharpen it:

- **Fowler's threshold applied literally.** The session extracted exactly one helper —
  `store_source_of` — on the third repetition of the same ternary, and left a mutate-and-return
  function and four unfrozen records alone because each occurred once. Recording _what was not
  changed and why_ turned out to be as useful as the diff.
- **A "when NOT to refactor" list**, taken from external prior art and worth stealing: the structure
  is not impeding the work; the restructure serves speculative needs; **the only justification is
  testability**; the code is good enough for the current phase.

## 4. The test rule, which the session got wrong first

Worth including because the wrong version is the one a model reaches for. The session first wrote
_"no test may be edited to make a refactor pass"_, which the user corrected: a test naming a renamed
function has to change, and changing it costs nothing. What must not change is **what** is tested.

The version that survived is countable rather than definitional, and that is the transferable idea:

- **Tests that drive the public surface are frozen** — for `plans.py`, the 65 of 105 that call
  `main([...])`. One of them changing _is_ the refactor leaking into behaviour.
- In the rest, **only the call form may change**; no assertion edited, no case dropped.
- The check that separates a rename from a weakening: **revert the production change, and the edited
  test must still fail.** An assertion diff misses a test that still asserts the right thing but no
  longer reaches the code that could break it.

[DECISION: **a refactor that improves the test surface is evidence the shape was wrong, not churn to
be tolerated.** `load_config` appeared at 20 test sites because there was no object to construct;
after the pass the tests build one against a fake home. Worth stating in the skill, because the
instinct is to count test churn as a cost of the refactor rather than as a symptom it is fixing.]

## Where this lands, and the open question

The content above is not one edit. Rough split:

- **`python-conventions`' Data modeling section** gains the baseline rule (2a) as a clause on the
  existing NamedTuple escalation, and the record-versus-mapping test (2c). Both are small.
- **The measurement table, the stopping rule and the test rule** are a procedure, not a default, and
  the skill has no section shaped like that today.

[NEEDS CLARIFICATION: extend `python-conventions` with a "restructuring a module that grew" section,
or make it a separate skill? Same question the encapsulation-pass plan raises, and it should be
answered once, for both. Extending keeps one home and avoids a description competing with
`python-conventions` on every "clean up this Python" request; a separate skill has a genuinely
different trigger ("review and restructure this module" against "how should I write this") and would
not bloat a skill already at 411 lines, which SkillsBench scores against. **Settle it with
`trigger.py candidate` against the installed set rather than by argument** — and only after the
`plans.py` pass has run, since `AGENTS.md` requires piloting a convention on one real repo before it
is written into a shareable artifact.]

[DEFERRED: whether any of this belongs in `skill-authoring` instead. The case study's meta-shape —
state a convention, measure the code against it, let the measurement correct the convention — is
about how this family builds guidance, not about Python. It may be a `skill-fitness` reference
rather than a `python-conventions` one. Not urgent, and easier to answer once the Python half has
landed.]
