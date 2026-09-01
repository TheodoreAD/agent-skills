# Prior art, and why this is a separate skill

## What was surveyed, 2026-09-01

**Locally available, and closer than expected — none of it does this job.**

- **A bundled code-simplifier agent** (Claude Code's `/simplify`): "simplifies and refines code for
  clarity, consistency, and maintainability while preserving all functionality. **Focuses on
  recently modified code unless instructed otherwise.**" That last clause is the whole gap — it is a
  diff-scoped pass, and whole-module state threading is what no diff contains. Its project-standards
  section is also visibly JS/React-shaped ("ES modules", "prefer the `function` keyword", "explicit
  Props types"), so it does not transfer.
- **A bundled code-review command**: bugs and cleanups in a diff or a PR. Same scoping limit, by
  design, and correctly so.
- **`code-modernization`** (in the official marketplace, not installed): a sequenced pipeline with
  artifacts and an approval gate —
  `preflight → assess → map → extract-rules → brief →
  transform|reimagine|uplift → harden` —
  including an `architecture-critic` agent whose stated default stance is skeptical ("does every
  service boundary correspond to a real domain seam, or is this microservices-for-the-resume?").
  Aimed at COBOL and legacy monoliths, so far too heavy for one file. Two ideas transfer:
  **discovery produces an artifact before any code moves**, and **an adversarial reviewer whose job
  is to argue the restructure is unnecessary**. The second is where the skill's stopping-rule
  section gets its stance.

**External, from a web pass:**

- A widely-referenced personal refactoring skill states the BASELINE → CHECKPOINT → REFACTOR →
  VERIFY → CHECKPOINT loop and, more usefully, a **"when NOT to refactor"** list: the current
  structure is not impeding the work; the restructure serves speculative future needs; the only
  justification is testability; the code is good enough for the current phase. Its DRY rule is the
  one `python-conventions` already holds — abstract only when two things are the same business
  concept and would change together, not when they merely look alike.
- The most-installed refactoring skill in one directory is not a refactorer at all: it is a
  `request-refactor-plan` that interviews the user and files a plan of tiny commits. Evidence for
  the shape of a plan file rather than for a tool.

[DECISION: **take the loop and the not-refactoring list; leave the pipelines.** The
`code-modernization` sequencing is right for a system and absurd for a single script. What this
procedure needs from prior art is a stopping rule and a discipline, one paragraph each — and the
oracle rules, which are the half no surveyed source had.]

## Why a separate skill rather than a section of `python-conventions`

The question was real: `python-conventions` answers "what should this code look like" per topic, and
its Modularity section already carries the load-bearing rule (lean toward duplication over premature
abstraction, flagged as **overrides, actively**). What it does not carry is a _procedure_ for
auditing an existing module against those defaults. Extending it would have avoided a second
description competing in the same region.

**Settled by measurement rather than argument, 2026-09-01: twelve prompts at three runs each, both
options.** The suites are `skills/skill-fitness/evals/refactor-audit-candidate.json` and
`refactor-audit-extend-alternative.json`; four of the twelve prompts are the modularity ones
`python-conventions`' description already claims, and a third of each suite is negatives.

| option                                   | score     | what happened                                     |
| ---------------------------------------- | --------- | ------------------------------------------------- |
| **separate skill**                       | **12/12** | took nothing from `python-conventions` — fp=0     |
| extend `python-conventions`' description | 10/12     | the two most characteristic prompts fired nothing |

**The extend option fails as a miss, not as a steal**, which is this corpus's own known failure
mode. "This module is 3,000 lines and nobody has reviewed it as a whole — how do I restructure it
without breaking anything?" selected **no skill at all**, three runs of three, and the type-change
prompt selected none in two of three. Precision stayed 1.0 throughout: the extended wording never
stole anything, it simply did not fire on the requests the procedure exists for.

The steal the plan worried about did not happen either. With the separate skill in the listing,
`python-conventions` kept every one of its own four cases — including "this module has accumulated
global state and is hard to follow, how far should I break it up?", the sentence its description
already owns. The two triggers are genuinely different, and the model can see it.

**Extending also costs a trim, which is the second argument against it.** `python-conventions`'
description is 927 of the 1024-character cap, so the procedure's clauses do not fit: the measured
wording had to cut the DST-folds phrase, the `src/`-layout prose and the exception-hierarchy
wording, and still reached only 1021. The trimmed wording then lost even its own cases to the
untrimmed incumbent — 6 of 18 fires against 12.

## The description is measured; a redraft is not

The `description` in `SKILL.md` is the wording that scored 12/12, at 900 characters (the plan that
recorded the measurement said 907; the count of the wording actually adopted is 900). **Editing it
is re-measuring it**, not a wording change: an unmeasured model-authored description is the one
thing published measurement puts _below_ having no skill at all. Re-run its own suite after any
edit, with `run` rather than `candidate` now that the skill is installed and the real listing is
under test:

```shell
python3 <skill-fitness>/scripts/trigger.py run <path>/refactor-audit-candidate.json
```

Each run costs 12 cases × 3 model probes.

### The live run does not reproduce the 12/12, and that is the number to quote

**Measured 2026-09-01, immediately after installing: 11/12 at three runs each, against the candidate
mode's 12/12.** Precision stayed 1.0 for every skill and nothing was stolen — `python-conventions`
kept all four of its cases, `python-testing-conventions` its one, and all three negatives held. The
single failure is the suite's **flagship** prompt, the sentence the skill exists for:

> "This module is 3,000 lines built over two weeks and nobody has ever reviewed it as a whole. How
> do I go about restructuring it without breaking anything?"

It selected the skill once in three runs and **nothing** the other two — the same miss, on the same
prompt, that sank the extend-`python-conventions` option. Recall 0.83, fn=2.

Two things follow, and both are corrections to what was believed before the run:

- **Truncation is ruled out, so this is a real selection miss.** The hypothesis was that a brand-new
  skill sits at priority 0.0 and loses its description first. Checked rather than assumed:
  `fitness.py budget` after the run reports no new truncated listing and no new bare-name
  observation, so all 36 probes saw the full description. Do not attribute this miss to the listing.
- **Candidate mode overestimated here.** `skill-fitness` documents a candidate score as a _lower
  bound_, because a proposal is registered as a command file rather than a real skill. This is a
  measured counterexample in the other direction: the same twelve cases scored 12/12 as a proposal
  and 11/12 once installed, with nothing else about the corpus changed. Treat a candidate score as
  an estimate with error in both directions, and re-run after shipping — which is the reason the
  plan said to.

**Open, and not to be fixed by rewording on a hunch.** A wording change is a new unmeasured
description; the only legitimate move is `candidate` on a redraft, then `run` after adopting it, and
the flagship prompt is the case to judge it on.

**What it costs the listing.** Measured with `fitness.py budget` on the day it was added: 925
characters, the largest single entry in the corpus, in a listing already over the 8,000-character
budget a 200k window allows. Priority in that listing is usage-weighted, so a skill nobody has
invoked yet sits at 0.0 and **is among the first to be demoted to name-only when the listing
overflows** — an unavoidable property of being new, not a fault in the wording. It did not cause the
miss above, but check `fitness.py budget` before concluding anything from a future one.

## Open, deliberately

- **Is the skill Python-specific, or only its vocabulary?** The loop, the oracle rules and the
  stopping rule are language-neutral; only the examples (`NamedTuple` versus frozen dataclass,
  `cached_property`) are not. A `refactor-audit` any language could use would contend with nothing
  in this corpus — but the measured description is the Python one, and a wider description is a
  different description that would have to be measured rather than assumed. Widen it only through
  `trigger.py`.
- **Which skill owns the "which tests may change" rule?** It is about a refactor rather than about a
  test, so it reads as this skill's — but a reader arriving from the test side is exactly who needs
  it. Check with `fitness.py overlap` and a `run`, rather than deciding it by argument.
