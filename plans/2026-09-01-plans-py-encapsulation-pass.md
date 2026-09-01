---
status: in-progress
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

## What this pass is actually about, restated 2026-09-01 by the user

Not OOP over functions. **Clear boundaries, with the types reflecting them; objects rather than
dicts and tuples; and each contiguous unit having an API surface that callers cannot reach around.**
The shape of the data is information, and an agent reading a signature to decide what to do with a
value is the reader that suffers most when the shape is anonymous. This is not a DAMP-vs-DRY
question — deduplication is a side effect, not the goal.

The first draft of this plan led with config threading, which is the smaller half. Measured:

| the anonymous shape                                 | count       |
| --------------------------------------------------- | ----------- |
| bare `tuple[...]` returns                           | **22**      |
| sites unpacking them positionally                   | **39**      |
| dict-shaped returns / fields / parameters           | 8 / 13 / 10 |
| stringly-keyed `routing.dirs["store"]` accesses     | 7           |
| `NamedTuple` in the file today / frozen dataclasses | **0** / 6   |

`walk_projects() -> tuple[list[str], list[LayoutProblem]]` and
`scan_text() -> list[tuple[int, str, str]]` are the shape of the problem: a reader has to find the
`return` statement to learn what the second element is.

[DECISION: **the baseline decides whether `NamedTuple` is an upgrade, and it is not a general
default.** A `NamedTuple` is indexable, unpackable and iterable, and compares equal to any plain
tuple with the same values — `Point(1, 2) == (1, 2)` is `True`. That is a second, positional API
surface nobody designed, which is the opposite of "callers cannot reach around the API", and
inserting a field in the middle silently changes what `x[1]` means at every call site with no error.
`python-conventions` carries the measured case: `Quantity(5, "ml") < Quantity(300, "mg")` returns
`True` rather than raising, because tuple ordering is inherited whether or not the values are
comparable.

So the rule is about what is being replaced, not about which class syntax is nicer:

- **bare tuple → `NamedTuple` is a clear upgrade.** Names where there were none, and the positional
  surface already exists and is already being unpacked at 39 sites, so nothing new leaks. This is
  exactly the drop-in-positional-compatibility case the conventions name as the legitimate reach.
- **frozen dataclass → `NamedTuple` is a downgrade**, adding indexing, unpacking and structural
  equality the type does not want.

The 22 bare-tuple returns are the candidates. The 6 frozen dataclasses stay as they are.]

[DECISION: **validation belongs at parse time, in the constructor, and that is what keeps
`@dataclass(frozen=True)` for config.** Config is static, read once, and every later reader should
be able to assume it is well formed — "parse, don't validate" applied with nothing but the standard
library. `__post_init__` is where that goes, and `NamedTuple` has no equivalent: it needs a
`__new__` override or a classmethod factory, which is more ceremony than the dataclass it was meant
to be cheaper than. `Config` is already a frozen dataclass, so this mostly confirms the existing
shape rather than changing it — what is missing is that several of its fields are still bare dicts.]

[DECISION: **dicts stay at the serialisation boundary and nowhere else.** The 10 `dict[str, object]`
payload builders exist to be handed to `json.dumps`, and giving them types would be ceremony in both
directions. The dicts to remove are the ones used as records: `Routing.dirs` with its 7
stringly-keyed lookups is the clearest, where two named fields turn a typo from a runtime `KeyError`
into an error a checker catches.]

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

## Progress

Steps 1, 2 and 3 landed 2026-09-01, in five commits. Re-measured with the same ast walk against the
same file (which had grown to 3,476 lines since the table above was taken):

| signal                                       | before | after | note                       |
| -------------------------------------------- | -----: | ----: | -------------------------- |
| stringly-keyed `routing.dirs[...]` accesses  |     14 | **0** | step 1                     |
| bare + nested anonymous `tuple[...]` returns |     22 | **5** | steps 2 and 3              |
| — of those, record-shaped                    |     16 | **0** | the 5 left are collections |
| positional unpacking of an anonymous return  |      9 | **0** |                            |
| `NamedTuple` classes                         |      0 |    13 |                            |
| frozen dataclasses                           |      6 |     7 | `Store`                    |
| `dict[...]` class fields                     |      4 |     3 | `Routing.dirs` gone        |
| functions taking `cfg`/`routing`             |     47 |    47 | untouched: steps 4-6       |

Two counts in the original table did not reproduce and the discrepancy is the plan's, not the
file's. **69 cfg-taking functions** measures as 47 with `cfg`/`config` leading and 55 with either
anywhere in the signature; there is no reading of the AST that gives 69, so steps 4-6 should be
judged against 47/55. **7 `dirs` lookups** was 14 by the time step 1 ran. The 22 tuple returns
reproduced exactly (12 bare + 10 nested inside a `list[...]`).

**All 5 anonymous tuple returns left are `tuple[str, ...]`** — `_strings`, `parse_depends_on`,
`migrated_targets`, `public_root_names`, `shareable_root_names`. A homogeneous variadic tuple is a
collection, not a record: there are no positions to name, so a `NamedTuple` has nothing to add. The
DECISION above is about anonymous _records_, and these were counted with them; the honest reading of
the original 22 is that 16 were records and all 16 are now named.

The oracle held: **not one of the 65 CLI-driven tests changed**, and 15 of the other 40 changed call
form only — 7 `.dirs["store"]` -> `.store_dir`, 6 for `Store`, one `[1]` -> `.source`, one
positional unpack -> `hit.text`. The `.store_dir` rewrites were checked against rule 3 by breaking
`store_dir` in `resolve` and confirming they fail. The test comparing a `SessionAnchor` to a plain
tuple literal was left as it was, and still passes — the positional compatibility this choice of
record rests on, asserted by a test nobody had to write for it.

[DECISION: **a type change under a name every caller uses needs a second oracle, because its failure
mode is silent.** Step 3 renamed nothing: `cfg.store` stayed `cfg.store` and became a record, so a
missed call site does not raise — it interpolates `Store(tier=..., path=..., source=...)` into
output, and the suite only covers the lines it asserts on. The check that actually settles it is
running every read-only command before and after and diffing: all 15, `--json` payloads included,
byte-identical. Cheap (one shell script in the scratchpad), and it is the only evidence that reaches
the output lines no test reads. Any later step that changes a widely-used field's _type_ rather than
its name should do the same.]

Noticed and deliberately not done, each its own small commit whenever:
`holding: list[tuple[str,
int]]` threaded through `doctor` and `_print_doctor` is the same anonymous
shape one layer out from what step 2 counted (parameters, not returns, so the measurement never saw
it); and `_plan_payload(rel, plan)` could take a `ScopedPlan` now that one exists.

## Sequencing

Naming the shapes comes first, because it is what a reader gains most from and what every later step
is then easier to verify against.

1. ~~**`Routing.dirs` → named fields.**~~ **Landed 2026-09-01.** 14 stringly-keyed lookups, not the
   7 measured here. `repo_dir` became a property derived from `repo_root` rather than a second
   field, and `dir_for(where)` is the single string-keyed door left, for the names that arrive from
   the config file and from `--to`.
2. ~~**The 22 bare-tuple returns → `NamedTuple`**~~ **Landed 2026-09-01**, in three batches: the
   listing pairs (`PlanDir`, `ScopedPlan`), the scanning ones (`TagHit`, `ScanHit`, `ScanTarget`,
   `HistoryEntry`), and the ones callers were indexing into (`RuleMatch`, `ProjectsWalk`,
   `SessionAnchor`, `TakenPlans`/`MovedPlan`, `ConfigKey`, `LineSpan`). 16 of the 22 were records
   and all 16 are named; see Progress for why the other 6 are not, and why one of them waits for
   step 3.
3. ~~**`Store` as a frozen record**~~ **Landed 2026-09-01.** `(tier, path, source)` replaced the
   four parallel `Config` fields and deleted `store_source_of`. `store_of`, `store_for` and
   `stores()` return the record now, so a caller picks the aspect it wants rather than calling a
   second accessor for the other half of the same thing — and the tier is stamped at load, where the
   device is known, which also removed the single-store branch from `stores()`.
4. `Workspace` with `config` only; convert the 21 `load_config()` sites; gate; commit.
5. `routing` and `require_routable`; convert the 12 + 7 prologue sites.
6. One derived property per commit: `private_terms`, `known_repos`, `stores`.
7. Re-measure **both** tables with the same scripts. The anonymous-shape counts should be near zero
   and the 69 should have moved most of the way down; a large diff that moves neither means the pass
   did not do its job, whatever it looks like.
8. Then, and only then, decide the skill question with a measured candidate description.

## Explicitly not in this pass

- **No file split.** Stated above; the single-file property is load-bearing for a skill script.
- **No `cmd_*` → methods**, pending the first open question, and leaning against.
- **No frozen-record sweep** — deferred above, its own commit.
- **No behaviour change of any kind**, including "obvious" improvements noticed in passing. Those
  become plans; the whole value of this pass is that its diff is verifiable as behaviour-preserving.
