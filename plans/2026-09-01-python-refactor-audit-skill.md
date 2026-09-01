---
status: landed
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

## The description that was measured, verbatim

**Use this wording, or re-measure.** It is what scored 12/12; a redraft is an unmeasured wording,
which is the one thing `skill-fitness` says measures below having no skill at all. 900 characters
(this said 907 until it was measured against the adopted frontmatter — see Progress), against the
1024 cap the layout test enforces.

```text
Use when an existing Python module has grown and the question is how to restructure it safely, not what to write — auditing a file nobody has reviewed as a whole, planning the change as a sequence of small commits each verified on its own, deciding which tests may be edited to follow a rename and which must not change at a character, proving an edited test still fails when the production change is reverted, finding a second oracle when the suite cannot see the change (a field's type changing under a name every caller already uses), measuring the shape you are trying to remove before and after so a large diff that moves nothing is caught, and deciding when not to restructure at all. For what a given piece of Python should look like — data modeling, dates, settings, modularity and singleton defaults — see the Python conventions skill; for what a test should cover, the Python testing skill.
```

Re-running either suite, once the skill exists — they are its trigger cases, not just the evidence
for creating it:

```shell
python3 skills/skill-fitness/scripts/trigger.py run skills/skill-fitness/evals/refactor-audit-candidate.json
```

`run` rather than `candidate` at that point: the skill is installed by then, so the real listing is
the thing under test. Each run costs 12 cases x 3 model probes.

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

[DECISION: **Python-specific for now, and the skill says why in its own `references/prior-art.md`
rather than leaving it to memory.** The loop, the oracle rules and the stopping rule are
language-neutral; only the examples are not. A wider `refactor-audit` would contend with nothing in
this corpus — but the measured description is the Python one, and a wider description is a different
description. Widen it only through `trigger.py`, never by editing the wording and assuming the score
carries.]

[DECISION: **this skill owns the "which tests may change" rule.** Measured rather than argued, both
ways. `fitness.py overlap` puts the pair with `python-testing-conventions` outside the top 12 — no
shared trigger vocabulary worth flagging — and both live runs had `python-testing-conventions` win
its own fixture-scope case 3/3 while this skill won its three narrow cases 3/3. The rule is about a
refactor, and nothing measured suggests a reader arriving from the test side is being misrouted.]

## Recommended direction

Write it from the pilot rather than from research: every rule above already has a dated incident
behind it, which is the bar the repo's own authoring rules set. Keep the body to the procedure and
push the stories into `references/`, then re-run the two suites already written — they are the
skill's own trigger cases, not just the evidence for creating it — and add the should-not-trigger
cases the pair with `python-conventions` needs.

Then `skill-authoring`'s deploy sequence, in full: the push is the step that gets skipped, and the
installer clones from the remote, so a committed but unpushed skill reaches nothing.

## What the gate will demand, so none of it is a surprise

`pytest tests/unit/test_skill_layout.py` is parametrized over every skill directory and enforces
most of this mechanically — it is the gate a new skill has to pass, so add the skill and run the
suite rather than eyeballing the frontmatter:

- `name` matches the directory, and is spec-valid.
- `description` present and within 1024 characters.
- The directory holds only `SKILL.md`, `references/`, `scripts/`, `evals/` and nothing else.
- **A row in `README.md`'s table**, with a `Scope` value. `test_listed_in_readme` fails without it.
  Scope here is "Opinionated but general": the procedure depends on no machine-specific thing, and
  the one command it names (`pytest`) is not this machine's.
- Any install command in a fenced block that names an `owner/repo` source carries `--global`.

## Progress

**Written 2026-09-01.** `skills/python-refactor-audit/` holds `SKILL.md` plus `references/pilot.md`
(the worked example — the counts, the oracle results, the two counts that did not reproduce, the
dropped items, the unpredicted findings) and `references/prior-art.md` (the survey, the
separate-skill measurement, and both open questions restated as things to measure rather than
argue). The README row is in, with `Scope: Opinionated but general`;
`pytest tests/unit/test_skill_layout.py` and `inv quality.precommit` are green, and `plans.py scan`
is clean.

**The measured description is in verbatim — and it is 900 characters, not the 907 this plan
claimed.** Confirmed by diffing the frontmatter value against this file's own fenced block: byte
identical, 900 both sides. The wording is unaffected; only the number here was wrong.

Two measurements taken while writing, both free:

- **`fitness.py overlap --root skills`**: `python-conventions <-> python-refactor-audit` ranks third
  by shared vocabulary (sim=0.08, 13 shared terms) but is **not** flagged as shadowing in either
  direction — the coverage is mutual rather than one-sided, which is the shape the live 12/12 run
  already showed. The pair with `python-testing-conventions` does not appear in the top 12 at all,
  which is the first evidence on the second open question: the "which tests may change" rule creates
  no measurable contention from the test side.
- **`fitness.py budget --root skills`**: 925 characters, the largest single listing entry in the
  corpus, in a listing already over budget for a 200k window. Priority is usage-weighted, so a brand
  new skill sits at 0.0 and is among the first demoted to name-only. Recorded in `prior-art.md`,
  because it means an early miss may be a truncated listing rather than a bad description.

**Shipped 2026-09-01**: commits `3f8260d` and `b3ca069`, pushed, installed with
`npx skills add TheodoreAD/agent-skills --global --skill python-refactor-audit`, installed copy
verified byte-identical to source and visible in this session's own listing.

### The live re-run is 11/12, not the 12/12 this plan promised

`trigger.py run refactor-audit-candidate.json`, immediately after installing, three runs each.
Precision 1.0 for every skill, nothing stolen, `python-conventions` kept all four of its cases,
`python-testing-conventions` its one, all three negatives held. **The single failure is case 1 — the
flagship prompt, "this module is 3,000 lines and nobody has ever reviewed it as a whole" — which
fired the skill once in three runs and nothing twice.** Recall 0.83, fn=2. That is the same prompt,
and the same miss, that sank the extend option.

Two conclusions, both checked rather than assumed:

- **Not truncation.** `fitness.py budget` after the run reports no new truncated listing and no new
  bare-name observation, so all 36 probes saw the full description. The priority-0.0 hypothesis this
  plan recorded an hour earlier is refuted for this case and must not be used to explain it.
- **Candidate mode overestimated**, on identical cases with nothing else changed — a measured
  counterexample to `skill-fitness`' documented "a candidate score is a lower bound". Folded back
  into `skill-fitness`' SKILL.md and `references/measurements.md`, and into `skill-authoring`, all
  three of which asserted the bound; the claim is now "an estimate that errs in both directions".

**Re-run to separate a real miss from variance: 11/12 again, case 1 at 0/3 — 1 fire in 6.** Every
other case held at 3/3 across both runs. So case 1 is a reproducible miss to silence, not variance,
and the plan's promised 12/12 does not survive shipping.

**And it is not the usual cause.** A miss to silence in this corpus has twice been a description
speaking the tool's vocabulary instead of the request's; here the description already carries the
prompt's own words nearly verbatim — "auditing a file nobody has reviewed as a whole", "how to
restructure it safely" against "nobody has ever reviewed it as a whole", "restructuring it without
breaking anything". Three narrower prompts for the same skill fire 3/3 with the same wording. The
same sentence also selected nothing for the rejected extend option, so it is the request shape, not
this description, that is hard — a broad "how do I go about X" seems to be answered directly rather
than routed. Recorded as a pitfall in `skill-fitness`' `measurements.md`, because it refutes the
diagnosis that file was carrying.

[DECISION: **ship at 11/12; no redraft. 2026-09-01, by the user, offered the alternatives.** A
redraft is a new unmeasured wording, and with vocabulary ruled out as the cause it would be a guess
rather than a fix — the one move `skill-fitness` says not to make. The skill is deployed and
working: 11 of 12 cases pass, precision 1.0, nothing stolen, and the failure is a miss rather than a
steal. Case 1 is revisited at the next fitness audit, when the skill also has real usage behind it,
and the two candidates for that pass are recorded above: isolate what suppresses selection on a
broad "how do I go about X" request before touching wording.]

This plan closes here. What it leaves behind is a skill, and a measurement that corrected two of
`skill-fitness`' own claims — which is worth more than the 12/12 it set out to confirm.

## Migrated to

- `skills/python-refactor-audit/` — the skill, its worked example and its prior art.
- `skills/python-refactor-audit/references/prior-art.md` — the live 11/12, the flagship-case miss,
  and why truncation and vocabulary are both ruled out.
- `skills/skill-fitness/SKILL.md` and `references/measurements.md` — the two corrections: a
  candidate score errs in both directions rather than being a lower bound, and vocabulary is not the
  only cause of a miss to silence.
- `skills/skill-authoring/SKILL.md` — the same lower-bound correction, where it was also asserted.
- `skills/skill-fitness/evals/refactor-audit-candidate.json` — both runs recorded in its `about`.

The encapsulation-pass plan's condition — "stays open until that skill exists" — is met, and it is
set `landed` with its content living on in `skills/python-refactor-audit/references/pilot.md`. This
plan stays `in-progress` on the case-1 question alone.

## Sources this is written from

Everything listed above already exists; none of it needs re-deriving.

- `plans/2026-09-01-plans-py-encapsulation-pass.md` — the pilot. Its **Progress** section holds the
  oracle rules as they were actually applied, the output-diff DECISION and its live-state PITFALL,
  the before/after tables, and the two counts that did not reproduce. That plan stays open until
  this skill exists, because it is this skill's source material.
- The pass's own commits, `2efb0c8..9dd62dd` — nine of them, each one property, each message saying
  what moved and what was verified. The commit sequence _is_ the worked example of the loop.
- `skills/skill-fitness/evals/refactor-audit-candidate.json` and
  `refactor-audit-extend-alternative.json` — the decision's evidence, results recorded in `about`.
- `skills/python-conventions/SKILL.md` — the boundary to write against, especially its Modularity
  and Modules-as-singletons sections, which stay where they are.
