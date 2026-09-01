---
status: planned
updated: 2026-09-01
---

# A holistic encapsulation pass over `plans.py`, and whether a skill should own that kind of pass

`plans.py` is 3,210 lines built incrementally over two weeks and never reviewed as a whole. The
2026-09-01 review found one real bug and two small cleanups, but it was a review of _recent
changes_, which is the only kind the existing tooling does. This plan is the structural pass that
nothing has done: one object holding what an invocation needs, so the config-threading disappears
rather than being tidied.

**One file, deliberately.** Splitting it is the obvious suggestion and it is wrong here: the script
ships inside a skill and is run as `python3 <path>` from any repo on any machine, with no install
step and no package to import. A second module means a second path to resolve at runtime. The goal
is encapsulation, not files.

## The measurement that motivates it

Taken 2026-09-01, and the plan should be re-measured against these before and after:

| signal                                                     | count                  |
| ---------------------------------------------------------- | ---------------------- |
| functions taking `cfg` (or `cfg, routing`) as leading args | **69 of 158**          |
| `load_config()` calls                                      | **21** for 18 commands |
| `resolve(args.path, cfg)`                                  | 12                     |
| `require_ok(resolve(args.path, cfg))` — the same prologue  | 7                      |
| module length / function count                             | 3,210 lines / 158      |

**The shape is a constructor waiting to happen.** Every command re-reads the config from disk, re-
resolves the same routing, then hands both down through three or four call layers as parameters.
Nothing is wrong with any single site; the cost is that a reader — human or agent — cannot tell from
a signature whether a function needs the config because it reads a path, a rule, a tier or a root.

[PITFALL: **158 functions at ~20 lines each is not the problem, and a pass that "fixes" it would
make things worse.** The file is already decomposed; the longest function is a declarative parser
builder. The complaint is not size or nesting, it is that state which is constant for a whole
invocation is passed as an argument 69 times. Any proposal that moves lines around without reducing
that number is not this plan.]

## What the shape should become

One object per invocation, constructed in `main()`, holding what is resolved once and exposing the
rest as properties:

```python
class Workspace:
    """Everything one invocation needs, resolved once: the config, where this repo routes, the stores."""

    def __init__(self, path: Path) -> None: ...

    @cached_property
    def config(self) -> Config: ...
    @cached_property
    def routing(self) -> Routing: ...
    @cached_property
    def stores(self) -> list[Store]: ...
    @cached_property
    def private_terms(self) -> list[str]: ...  # today: a free function taking cfg
    @cached_property
    def known_repos(self) -> list[RepoInfo]: ...  # today: a free function taking cfg

    def locate(self, name: str) -> PlanFile: ...
    def plans(self, scope: str) -> list[PlanFile]: ...
    def require_routable(self) -> Routing: ...  # today: require_ok(resolve(args.path, cfg))
```

Three properties this buys, in the order they matter:

1. **The prologue disappears.** `load_config()` + `resolve` + `require_ok` becomes one construction
   in `main()`, and the 7 repetitions of the three-line opening become `ws.require_routable()`.
2. **The expensive derivations are computed once.** `private_terms`, `known_repos` and
   `walk_projects` all walk the projects root; today each command that needs two of them walks it
   twice.
3. **A signature says what a function needs.** `def scan_text(text, terms)` already does; the 69
   that take `cfg` do not.

[DECISION: **a per-invocation object, not the module-singleton pattern.** `python-conventions`'
`globals.py` shape is for process-wide state; this is per-invocation and the tests construct it
repeatedly against different fake homes. A module-level instance would be exactly the shared global
the test suite currently avoids by passing `--path`.]

[NEEDS CLARIFICATION: how far the `cmd_*` functions move. Two shapes. **(a)** They stay free
functions and take `ws` instead of reading config themselves — smallest diff, keeps `argparse`
wiring untouched, and the 18 entrypoints stay greppable. **(b)** They become methods on `Workspace`,
which reads better but makes the class a 2,000-line god object and couples argument parsing to
domain logic. Leaning hard toward **(a)**: the encapsulation win is in the shared state, not in
where the command bodies live, and (b) is the "extract on sight" instinct the conventions warn
about.]

[NEEDS CLARIFICATION: whether `Store` becomes a small frozen dataclass — `(tier, path, source)` —
replacing the parallel `store` / `store_source` / `sensitive_store` / `sensitive_store_source`
fields. It would delete `store_source_of`, which today exists only to pick between two parallel
fields. Cheap and clearly right; the question is whether it belongs in this pass or its own commit
before it.]

[DEFERRED: `fill_details` mutates the `Retired` it is handed and returns it, and `Retired`,
`PlanFile`, `RepoInfo` and `_Walk` are unfrozen where the rest of the file's records are frozen.
Real, small, and **out of scope for this pass** — the conventions class build-then-enrich as
ordinary local mutation, and bundling it here makes the diff harder to verify as
behaviour-preserving. Its own commit, before or after.]

## How the pass is run, which matters more than the target shape

Adapted from the external refactoring skill surveyed below, whose loop is the part worth taking:

**BASELINE → CHECKPOINT → REFACTOR → VERIFY → CHECKPOINT**, one property per commit.

- **The test suite is the oracle**, and the rule has three parts rather than one. An earlier draft
  of this plan said flatly "no test may be edited to make a refactor pass", which is wrong and would
  have blocked the pass outright: a test naming a function that gets renamed has to change, and
  changing it costs nothing. What must not change is _what_ is tested. Measured 2026-09-01 across
  the 105 tests in `test_plan_store.py`:

  | tests  | what they do                               | may they change?          |
  | ------ | ------------------------------------------ | ------------------------- |
  | **65** | drive the CLI only — `plans.main([...])`   | **no, not one character** |
  | 24     | drive the CLI _and_ touch an internal name | the call form only        |
  | 16     | touch an internal name only                | the call form only        |

  1. **The 65 CLI-driven tests are frozen.** They exercise behaviour through argv and assert on
     output and filesystem state, so nothing this pass does can legitimately touch them. One of them
     changing is the definition of the refactor having leaked into behaviour.
  2. **In the other 40, only the call form may change** — `plans.load_config()` becoming
     `Workspace(path).config`. Mechanical substitution, no assertion edited, no case dropped.
  3. **The check that separates "renamed" from "weakened": revert the production change, and the
     edited test must still fail.** An assertion-diff review misses the case where a test still
     asserts the same thing but no longer reaches the code that could break it; this catches it.

  The names the suite actually reaches for are the ones this pass targets — `load_config` at 20
  sites, `private_terms` at 4, `walk_projects` at 3, `repo_paths` at 1 — while `parse_frontmatter`
  (9) and `today` (9) are pure functions it never touches. So the churn is bounded and predictable
  before the first line moves.

[DECISION: **`load_config` appearing in 20 tests is an argument _for_ the refactor, not a cost of
it.** The tests reach for a module-level loader because there is no object to construct; after the
pass they construct a `Workspace` against a fake home, which is better test ergonomics than
monkeypatching a global. Where a refactor improves the test surface, that is evidence the shape was
wrong, not churn to be tolerated.]

- **The measured counts above are the second oracle.** Each commit should move at least one of them
  and the final state should be re-measured with the same script, not asserted.
- **One property per commit**, not one class per commit: introduce `Workspace` with `config` only,
  convert call sites, gate, commit; then `routing`; then each derived property. A single commit that
  introduces the whole object and rewrites 69 signatures cannot be reviewed.

[PITFALL: **the diff will be enormous and almost entirely mechanical, which is exactly when a
behaviour change hides.** 69 signature changes read as noise, and the one that also flipped an
argument order reads as noise too. The per-property sequencing exists to keep each commit's
mechanical part small enough that the non-mechanical part is visible.]

## Prior art, checked 2026-09-01

**Locally available, and closer than expected — none of it does this job:**

- **`/simplify`** → the bundled `code-simplifier` agent. "Simplifies and refines code for clarity,
  consistency, and maintainability while preserving all functionality. **Focuses on recently
  modified code unless instructed otherwise.**" That last clause is the gap: it is a diff-scoped
  pass, and the problem here is whole-module state threading that no diff contains. Its instructions
  are also visibly JS/React-shaped ("ES modules", "prefer `function` keyword", "explicit Props
  types"), so its project-standards section does not transfer.
- **`/code-review`** → bugs and cleanups in a diff or PR. Same scoping limit, by design.
- **`code-modernization`** (in the official marketplace, not installed) → the most interesting one.
  It is a **sequenced pipeline with artifacts and an approval gate** —
  `preflight → assess → map → extract-rules → brief → transform|reimagine|uplift → harden` — with a
  `architecture-critic` agent whose stated default stance is skeptical ("does every service boundary
  correspond to a real domain seam, or is this microservices-for-the-resume?"). Aimed at COBOL and
  legacy monoliths, so far too heavy for one file, but two ideas transfer: **discovery produces an
  artifact before any code moves**, and **an adversarial reviewer whose job is to argue the
  restructure is unnecessary**.
- **`architecture-critic`'s stance is the one to borrow verbatim**, because it is the check this
  plan most needs against itself.

**External, from a web pass:**

- A widely-referenced personal refactoring skill states the loop above and, more usefully, a **"when
  NOT to refactor"** list: the current structure is not impeding the work; the restructure serves
  speculative future needs; **the only justification is testability**; the code is good enough for
  the current phase. Its DRY rule is the same one `python-conventions` already holds — abstract only
  when two things are "the same business concept" and "would change together", not when they merely
  look alike.
- The most-installed refactoring skill in one directory is not a refactorer at all: it is
  `request-refactor-plan`, which interviews the user and files a plan of tiny commits. That is
  evidence for the shape of this file rather than for a tool.

[DECISION: **take the loop and the not-refactoring list; leave the pipelines.** The
`code-modernization` sequencing is right for a system and absurd for a 3,210-line script. What this
pass needs from prior art is a stopping rule and a discipline, both of which are one paragraph
each.]

## Does this belong in a skill?

The user's framing: a Python authoring/conventions skill ought to be able to do this. Worth deciding
before, not after, since it changes what the pass produces.

`python-conventions` today answers _"what should this code look like"_ per topic — data modeling,
dates, settings, guard clauses — and its Modularity section already carries the load-bearing rule
(**"lean toward duplication over premature abstraction … a wrong abstraction is harder for an agent
to safely touch than duplicated code"**, flagged as **overrides, actively**). What it does not carry
is a _procedure_ for auditing an existing module against those defaults.

[NEEDS CLARIFICATION: extend `python-conventions` with a "restructuring a module that grew" section,
or a separate skill? Arguments both ways, and the corpus has a way to settle it.

- **Extend**: the rules are already there and would only gain a procedure; a second skill would
  contend with `python-conventions` on every "clean up this Python" request, and `skill-fitness`'
  measured pattern is that the corpus's real failures are misses rather than steals, so a new
  description competing in the same region is the one case where a steal is plausible.
- **Separate**: the trigger is genuinely different — "review and restructure this module" against
  "how should I write this" — and the procedure is long enough (a loop, a stopping rule, an
  oracle-preservation rule) to bloat a skill already at 411 lines, which SkillsBench scores badly.

**This is exactly what `trigger.py candidate` settles**, and it should be settled that way rather
than argued: draft the description, score it against the installed set, and check whether it takes
anything from `python-conventions`. Do not ship either wording unmeasured.]

[DECISION: **whatever it becomes, it is written after this pass, not before.** `AGENTS.md`' own rule
is that conventions get applied to one real repo before being written into a shareable artifact — a
pilot surfaces what research cannot. This pass _is_ that pilot, and its findings are the content.
Writing the skill first would be authoring the guidance unaided, which is the one thing
`skill-fitness` says measures below having no skill at all.]

## Sequencing

1. `Store` as a frozen record, if the second open question resolves that way — its own commit,
   first, because it shrinks `Config` before anything depends on the new shape.
2. `Workspace` with `config` only; convert the 21 `load_config()` sites; gate; commit.
3. `routing` and `require_routable`; convert the 12 + 7 prologue sites.
4. One derived property per commit: `private_terms`, `known_repos`, `stores`.
5. Re-measure the table at the top with the same script. If the 69 has not moved most of the way to
   zero, the pass did not do its job whatever the diff looks like.
6. Then, and only then, decide the skill question with a measured candidate description.

## Explicitly not in this pass

- **No file split.** Stated above; the single-file property is load-bearing for a skill script.
- **No `cmd_*` → methods**, pending the first open question, and leaning against.
- **No frozen-record sweep** — deferred above, its own commit.
- **No behaviour change of any kind**, including "obvious" improvements noticed in passing. Those
  become plans; the whole value of this pass is that its diff is verifiable as behaviour-preserving.
