---
status: planned
updated: 2026-09-01
---

# `python-refactor-audit`: the skill the encapsulation pass earned

## Context

`plans/2026-09-01-plans-py-encapsulation-pass.md` restructured a 3,700-line script over eight steps
and produced a procedure that has no home. Its step 8 asked whether that procedure becomes its own
skill or a section of `python-conventions`, and settled it by measurement rather than argument.

**Decided 2026-09-01: a separate skill.** Twelve prompts at three runs each, both options, suites in
`skills/skill-fitness/evals/refactor-audit-candidate.json` and
`refactor-audit-extend-alternative.json`:

| option                      | score     | what happened                                     |
| --------------------------- | --------- | ------------------------------------------------- |
| **separate skill**          | **12/12** | took nothing from `python-conventions` — fp=0     |
| extend `python-conventions` | 10/12     | the two most characteristic prompts fired nothing |

The extend option fails as a _miss_: "this module is 3,000 lines and nobody has reviewed it as a
whole" selected no skill at all, three runs of three. And `python-conventions`' description is 927
of the 1024-character cap, so extending costs a trim — the measured wording cut the DST-folds
phrase, the `src/` prose and the exception-hierarchy wording and still only reached 1021, after
which it lost its own cases to the untrimmed incumbent.

The `AGENTS.md` rule that conventions are piloted on one real repo before becoming a shareable
artifact is already satisfied: the pass **is** the pilot, and its findings are the content.

## What goes in it

The body is the procedure. Everything with a story attached goes to `references/`.

- **The loop**: BASELINE → CHECKPOINT → REFACTOR → VERIFY → CHECKPOINT, one property per commit.
  Adapted from an external refactoring skill; the sequencing exists so each commit's mechanical part
  is small enough that the non-mechanical part is visible.
- **The oracle rules, which are the load-bearing half.** Which tests may be edited (the call form
  only) and which may not change at a character (the ones driving the CLI); and the check that
  separates a rename from a weakening — revert the production change and the edited test must still
  fail. Both were used at every step of the pilot, and both caught something.
- **A second oracle when the suite cannot see the change.** A field's type changing under a name
  every caller uses fails by interpolating a repr into output, not by raising, so the suite only
  covers the lines it asserts on. Capture every read-only command's output before and after and
  diff. With the pitfall attached: that oracle reads live machine state, so the two captures must be
  taken back to back — a parallel session's edits to unrelated files otherwise arrive as a diff.
- **Measure the shape you are removing, before and after.** A large diff that moves no count did not
  do the job. The pilot's own counts are the worked example, including the two that did not
  reproduce.
- **The stopping rule**: the current structure is not impeding the work; the restructure serves a
  speculative need; the only justification is testability; the code is good enough for its phase.
  The pilot dropped two planned items under it (`stores` as a property, caching the session anchor
  at 1.9 ms).
- **Where the numbers do and do not support the conclusion.** The pilot's config-taking count moved
  47 → 38 and that was the right answer, not a shortfall; a function taking the config because it
  derives from the config has a signature that says so.

## Open questions

[NEEDS CLARIFICATION: is the skill Python-specific, or is only its vocabulary? The loop, the oracle
rules and the stopping rule are language-neutral; the examples (`NamedTuple` vs frozen dataclass,
`cached_property`) are not. A `refactor-audit` that any language could use would contend with
nothing in this corpus — but the measured description is the Python one, and a wider one is a
different description that would have to be measured again rather than assumed.]

[NEEDS CLARIFICATION: does it own the "which tests may change" rule, or does
`python-testing-conventions`? The rule is about a refactor rather than about a test, so it reads as
this skill's — but a reader arriving from the test side is exactly who needs it. Check with
`fitness.py overlap` once the skill exists, rather than deciding it in advance.]

## Recommended direction

Write it from the pilot rather than from research: every rule above already has a dated incident
behind it, which is the bar the repo's own authoring rules set. Keep the body to the procedure and
push the stories into `references/`, then re-run the two suites already written — they are the
skill's own trigger cases, not just the evidence for creating it — and add the should-not-trigger
cases the pair with `python-conventions` needs.

Then `skill-authoring`'s deploy sequence, in full: the push is the step that gets skipped, and the
installer clones from the remote, so a committed but unpushed skill reaches nothing.
