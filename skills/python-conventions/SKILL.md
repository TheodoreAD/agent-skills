---
name: python-conventions
description: "Use when writing, reviewing or refactoring Python and you want one settled answer rather than an evaluation — choosing between a dataclass, a Pydantic model, a NamedTuple, a TypedDict, attrs or msgspec; handling dates, times and timezones, including DST folds and gaps and where to convert to UTC; loading settings and secrets; when to use a guard clause, an early return or EAFP; designing an exception hierarchy; keeping type ignores honest; laying a package out under `src/`; building a CLI; async and concurrency; and how an HTTP client should handle sessions, timeouts and retries. Also when a module has accumulated global state, grown hard to follow, or needs restructuring — how far to break it up, when a module-level singleton with lazy properties is the right shape, and how to keep objects immutable and functions stateless. For tests see the Python testing skill; for MCP server internals see the MCP Python skill."
metadata:
  family: python
---

# Python design and style defaults

Personal, agent-maintained Python projects. Applies when writing new code or reviewing existing code
against one of the topics below without an explicit "evaluate alternatives" request — pick the
default, don't re-litigate from scratch each session. Deviating is fine when a case genuinely
matches one of the named escalation paths — the point is to stop a fresh session/model from silently
picking something different for no reason, not to forbid judgment calls.

**Two topics were split out on 2026-08-31** and are separate installs: test-suite conventions are in
`python-testing-conventions`, and the stdio-logging, tool-boundary and tool-docstring rules for MCP
servers are in `mcp-python-conventions`. The split was measured before it was made — the pieces were
checked against real requests to confirm each wins its own and none steals from the others.

**This is design guidance, not tool config.** Nothing here tells you which type checker or linter to
install or how to configure it — that's `power-user-linux-setup`'s `contributing/quality-tooling.md`
(basedpyright, ruff, shellcheck/shfmt, dprint, pytest config mechanics), with `repo-tasks`'
`contributing/type-checking.md` for the tuned basedpyright profile. This skill is what to reference
_while writing code_; those are what a repo's tooling enforces _once, at setup_.

**Each topic below states whether it's overriding your own default instinct or just confirming
one.** A capable model already gets a lot of this right without being told — early returns, EAFP for
runtime lookups, reasonable async code, `pathlib` over `os.path`. This skill isn't trying to
relitigate those; it exists for the choices where a model left alone drifts (six equally-plausible
data-modeling options, a DRY instinct that over-abstracts, a settings pattern borrowed from the last
framework seen in training data) or where a convention is genuinely non-obvious/project-specific
rather than general Python knowledge (the `globals.py` singleton shape). Each **Model default** line
below says which case you're in — skim past the ones that just confirm what you'd already do, weight
the ones that don't.

## Data modeling

- Snippet: [`references/snippets/data-modeling.py`](references/snippets/data-modeling.py)
- Default: **Pydantic v2**, `frozen=True`, for anything parsing external/untrusted data (API
  responses, MCP tool args) or settings/config. **`@dataclass(frozen=True)`** for everything else —
  internal structured data, function returns, records.
- Why: two defaults, not six, so agents mimicking existing code have less room to pick the wrong
  one. Pydantic's Rust core closed the validation-speed gap with v1, but never closed the
  plain-attribute-access gap with a dataclass — the split isn't about which is "faster" in the
  abstract, it's boundary-validation vs. everything else.
- Escalate to: `attrs` (validators/converters without Pydantic's validation+serialization bundling),
  `NamedTuple` (drop-in positional-tuple compatibility, or a small closed record where order _is_
  the meaning — never past ~3 fields), `msgspec` (once Pydantic overhead is a _measured_
  bottleneck), `TypedDict` (value must genuinely stay a plain dict, not become an object).
- **The NamedTuple clause's third condition — zero validation or behavioural needs — is the one that
  bites, and "past ~3 fields" is the weaker test.** A two-field `Quantity(amount, unit)` looks like
  a textbook NamedTuple and is a bug: it inherits tuple ordering, so comparing `Quantity(5, "ml")`
  against `Quantity(300, "mg")` with `<` returns `True` instead of raising, silently succeeding
  across incompatible units. Free tuple ordering is a hazard, not a convenience, for any value type
  whose comparisons carry a precondition.
- **That hazard and NamedTuple's benefit are the same property seen from two sides, so the question
  is never "is a NamedTuple nicer here" — it is what is being replaced.** A **bare tuple ->
  `NamedTuple`** is a clear upgrade: names where there were none, and the positional surface already
  exists and is already being unpacked, so nothing new leaks. A **frozen dataclass -> `NamedTuple`**
  is a downgrade: it _adds_ indexing, unpacking, iteration, and equality with any plain tuple
  carrying the same values — a second positional API nobody designed — and inserting a field in the
  middle silently changes what `x[1]` means at every call site, with no error anywhere. Confirmed
  2026-09-01 auditing a 3,200-line stdlib-only script: 16 anonymous record-shaped tuple returns
  became `NamedTuple`s and the 6 frozen dataclasses were deliberately left alone.
- **Where the dependency is not available — a stdlib-only script, a vendored tool — validating in
  `__post_init__` is what keeps config a frozen dataclass.** That is "parse, don't validate" with
  nothing but the standard library, worth naming by the phrase because the phrase is what makes it
  findable. Config is read once and every later reader should be able to assume it is well formed.
  It is also the concrete form of the NamedTuple clause's zero-validation condition: `NamedTuple`
  has no `__post_init__`, so the same guarantee costs a `__new__` override or a classmethod factory
  — more ceremony than the dataclass it was meant to be cheaper than.
- **A `dict` is a mapping, or it is a record that lost its type; the test is whether the keys are
  data or names you chose.** Keys arriving from outside — a config file, a JSON payload — are data,
  and that stays a dict. Keys the author typed are field names: a `dirs["store"]` read with string
  literals at 7 sites is a record, and two named fields move a typo from a runtime `KeyError` to an
  error the checker catches. The legitimate exception is the **serialisation boundary** — a
  `dict[str, object]` built to be handed to `json.dumps` should stay a dict, where typing it is
  ceremony in both directions.
- Alternative, project-wide: **if a project uses Pydantic for anything, it uses Pydantic for
  everything.** A legitimate substitute for the split above, not a divergence from it, and it cuts
  both ways — it also makes "no Pydantic anywhere" a real answer, rather than letting the dependency
  arrive one convenient module at a time. Take it when a project already has Pydantic at its
  boundary and would otherwise run two record idioms, leaving an agent to guess which to mimic; the
  split's own reasoning (measured plain-attribute-access cost, dependency weight) is what you are
  trading away, so decide once, at the top of the project, not per module.
- **The strongest reason to take it is not consistency.** Measured on a project that migrated ~30
  frozen dataclasses: a single `Annotated` alias replaced thirteen hand-maintained
  `object.__setattr__` normalisation sites of that codebase's most load-bearing invariant.
  Validation that a frozen dataclass can only express in `__post_init__` gymnastics is the real
  trade, and it is a better argument than "one idiom, not two".
- Model default: **overrides.** Left alone, a model mixes Pydantic/dataclass/TypedDict/NamedTuple
  inconsistently across a codebase depending on what it last saw — there's no strong single default
  instinct here to confirm.

### Pydantic traps a dataclass never had

Four measured against pydantic 2.13.5, all of which bite a project migrating dataclasses → Pydantic
or following the all-or-nothing alternative above. The last is the one that changes a public API
rather than a call site.

- **`model_copy(update=...)` performs no validation** — its own docstring says so. A frozen model
  copied with `update=` accepts a naive datetime, or a cross-field violation, that every other
  construction path rejects. This is a genuine regression from `dataclasses.replace`, which
  revalidates, and it hits mechanically at every `replace()` call site being ported. Use the
  revalidating helper in the snippet, not `model_copy`.
- **Lax mode coerces `float` into `Decimal`.** For any field that is `Decimal` _because_ floats are
  unacceptable, the default silently removes the guarantee. `Annotated[Decimal, Strict()]` restores
  it and keeps the metadata in the annotation where the rest of it lives.
- **Config belongs in the class declaration.** `class Q(BaseModel, frozen=True)` is verified
  equivalent to `model_config = ConfigDict(frozen=True)`, composes with other keywords, and reads on
  the line that names the class rather than as an attribute assignment that looks like data.
- **A validator's `ValueError` is swallowed and re-raised as `pydantic.ValidationError`** — anything
  that is not a `ValueError` propagates untouched. Harmless until the project's own exception
  hierarchy is rooted at `ValueError`, which is a common and well-reasoned choice made so callers
  handling bad input generically keep working. After the migration every class in that hierarchy
  stops reaching a caller: a construction that raised `MyValidationError` now raises
  `pydantic.ValidationError`, and the subclass distinction survives only in message text. Measured
  on a project whose two classes were a validation error and a unit-mismatch error, where telling
  them apart is the entire point of having both. The fix is to drop `ValueError` from the base — and
  to write down the consequence, since `pydantic.ValidationError` _is_ a `ValueError`: catching
  everything a construction can raise becomes `(ProjectError, ValueError)`, the project's own
  complaints plus the structural ones pydantic raises on its own.
  - **The inverse is equally right at a parsing boundary**: raise plain `ValueError` deliberately so
    pydantic _does_ capture it, attach the field's location, and collect several complaints into one
    report — then render that report back into the project's own error type at the boundary. So the
    rule is not "never subclass `ValueError`"; it is that the choice now decides whether an error
    carries a **type** or a **location**, and it is made per layer.
- Model default: **overrides.** `model_copy(update=...)` reads as the obvious `replace` equivalent
  and is the natural first reach; nothing about the call site suggests validation was skipped. The
  `ValueError` trap is worse in the same way — the base class is chosen once, long before the
  migration, and nothing at the point of the change points back at it.

## Dates, times, and timezones

- Default: **aware datetimes only, normalised to UTC at every boundary.** Reject a naive datetime
  where it enters, never coerce it, and `astimezone(UTC)` everything you store or compare. Convert
  to a local wall clock only at the point of display. `zoneinfo` for zones (stdlib since 3.9), never
  `pytz`.
- Why: **two aware datetimes that share a non-UTC `tzinfo` subtract and compare on their wall
  clock**, silently ignoring any DST transition between them. A "24 hour" trailing window spans 23
  real hours across spring-forward; a six-hour minimum interval between two doses elapses an hour
  early. Worse, near a fold `==` and `-` disagree — an ambiguous datetime and its own UTC equivalent
  subtract to exactly zero while comparing unequal — so any branch on instant equality is wrong.
  Normalising on the way in is what makes every later comparison mean elapsed time. Measured live
  2026-08-27 in `ingesta`, where both failures were real and neither was visible by reading the
  code.
- The canonical spelling, for a project that has Pydantic:

  ```python
  Utc = Annotated[datetime, AwareDatetime, AfterValidator(lambda v: v.astimezone(UTC))]
  ```

  Verified: it normalises an aware non-UTC datetime and rejects a naive one, on every construction
  path the model has. That is the whole rule above as one reusable annotation, and it replaces the
  hand-maintained `object.__setattr__` normalisation a frozen dataclass needs at each field. Without
  Pydantic, the equivalent is still a `__post_init__` doing both halves explicitly — reject naive,
  then `astimezone(UTC)` — never one or the other.
- Resolving a local wall time: `fold` (PEP 495) is the whole API, and each case needs a stated
  policy rather than whatever `replace(tzinfo=...)` happens to do. Detect by comparing **offsets,
  not datetimes** — intra-zone comparison ignores `fold`, so the datetimes compare equal either way.
  `wall.replace(tzinfo=z, fold=0).utcoffset() < ...fold=1...` means the time is _nonexistent_ (a
  spring-forward gap); `>` means _ambiguous_ (a fall-back). Then choose deliberately: round-tripping
  a gap time through UTC shifts it past the gap, and `fold=0` takes the first occurrence of an
  ambiguous one.
- Testing: DST correctness needs **known-answer tests at real transitions**, expected instants
  worked out by hand and asserted literally. A property test restates the implementation and passes
  straight through this bug. Normalise in the test helpers too — a property test computing
  `anchor - duration` on zone-aware values has the bug itself and will report correct code as
  broken, which is exactly what happened before the helpers were fixed.
- **Don't**: `datetime.utcnow()` — it returns a _naive_ datetime and is deprecated since 3.12; use
  `datetime.now(UTC)`. Don't store a float timestamp to sidestep the problem either: an aware UTC
  datetime is the value, not an encoding of it. ruff's `DTZ` ruleset catches the naive-construction
  half of this automatically and none of the same-zone-arithmetic half.
- Model default: **overrides.** Models use `astimezone`/`ZoneInfo` correctly in isolation but do not
  default to normalising at the boundary, and reliably write same-zone arithmetic that is wrong only
  across a transition — invisible to review, and to every test that doesn't sit on a DST boundary.

## Settings and secrets management

- Snippet: [`references/snippets/settings.py`](references/snippets/settings.py)
- Default: `pydantic-settings`. Base `Settings` class with production-safe defaults, one subclass
  per non-prod environment overriding only what differs, an `ENVIRONMENT`-env-var-driven selector
  wired at the top of the package's `__init__.py`, assigned once to a module-level name.
  `frozen=True` throughout.
- Why: this is the module-singleton pattern (below) applied to settings — eager construction fails
  fast at import time, and a plain (non-Singleton) class means tests can freely construct an
  isolated instance instead of fighting shared global state.
- Escalate to: `dynaconf` — only once a repo genuinely grows a multi-environment deployment matrix
  (Vault/Redis-backed dynamic sources, non-Python operators hand-editing config).
- **Don't**: FastAPI's `@lru_cache`-wrapped settings factory, outside an actual FastAPI app. Its
  rationale (amortizing repeated `.env` reads across requests) doesn't transfer to a CLI tool or MCP
  server, its test-override mechanism is FastAPI-dependency-injection-specific, and it trades away
  fail-fast-at-import-time for a benefit that doesn't apply here. Full reasoning in the rationale
  doc.
- Model default: **overrides.** A model trained heavily on FastAPI examples defaults toward the
  `@lru_cache` factory pattern, not this one — the eager base+subclass+env-selector shape is a
  specific chosen idiom, not what falls out naturally.

## Early returns, guard clauses, fail-fast, and EAFP

- Snippet: [`references/snippets/guard-clauses.py`](references/snippets/guard-clauses.py)
- Rule: a guard clause is for the asymmetric case — one happy path, one rare exceptional early-out.
  Don't use one to split two co-equal business branches; that's a plain `if`/`else`. Guard clauses
  validate the _caller's contract_ (argument types/ranges); EAFP handles _runtime_ operations Python
  already fails loudly on (dict/attr lookups, I/O, network).
- Fail-fast: `assert` is for internal "can't happen" self-checks only (compiled out under
  `python -O`) — never for input validation. Anything triggerable by bad input or external state
  `raise`s a real exception. Never return `None`/a sentinel/`(success, result)` on failure — falsy
  values make "empty" and "failed" indistinguishable to the caller.
- Exception hierarchy: [`references/snippets/exceptions.py`](references/snippets/exceptions.py) —
  one root exception per package minimum, deeper leaves only once a caller actually needs to
  discriminate (2–3 levels, matching `requests`/`click`'s own shape).
- Model default: **mostly confirms.** Early-return style and EAFP-for-runtime-lookups are already
  close to default behavior; the real add is the guard-clause/co-equal-branch nuance and the
  never-return-None-on-failure rule, which models don't reliably self-apply.

## Modularity, testability, DRY, readability, encapsulation

- Default: lean toward duplication over premature abstraction (Fowler's Rule of Three: duplicate
  once freely, wince at twice, refactor on three) — a wrong abstraction is harder for an agent to
  safely touch than duplicated code, not easier.
- Architecture: Functional Core, Imperative Shell fits CLI/data-pipeline-shaped code well; strains
  for code whose entire job _is_ I/O orchestration (MCP servers) — reach for Michael Feathers'
  "seams" vocabulary there instead.
- Encapsulation: Python has no real privacy (PEP 8: single underscore is a "weak indicator," nothing
  more). Internal helper modules public-by-default; reserve `__all__` + underscore discipline for
  genuine package-public surfaces (MCP tool definitions, CLI entrypoints).
- Model default: **overrides, actively.** A model asked to "clean up" or even just implementing a
  feature proactively tends to extract shared helpers/abstractions on sight — this is the section
  most likely to be fought against if skipped, not a minor nudge.

## Modules-as-singletons and lazy-loading properties

- Snippet: [`references/snippets/settings.py`](references/snippets/settings.py) (same pattern,
  generalized beyond settings)
- Default: instantiate a plain class once at module level (the `globals.py` pattern) —
  stdlib-endorsed
  ("[The Global Object Pattern](https://python-patterns.guide/python/module-globals/)"), not a GoF
  Singleton, so tests can freely construct a second, isolated instance. `@property`/
  `cached_property` for lazy-loaded fields, but only when the getter is idempotent and
  side-effect-free — an explicit `.load()` method otherwise, since a property can't signal cost at
  the call site.
- Caveats to keep in view: `cached_property`'s thread-safety guarantee (exactly-once under
  concurrent first access) was **removed in Python 3.12** — a correctness change if the getter isn't
  idempotent, not just a performance one. `monkeypatch.setattr` in tests must target the module
  attribute itself (`monkeypatch.setattr(config_module, "X", ...)`), not a name already pulled in
  via `from config import X`.
- Model default: **overrides.** A model reaches for dependency injection, a class-based Singleton,
  or a per-call instantiation before it reaches for a bare module-level instance — this pattern is
  idiosyncratic to this project family, not a common default.

## Statelessness and immutability

- Default: `frozen=True` on data/value objects crossing a boundary (function args, MCP payloads,
  config, records) — the same default as the data-modeling table above, not a separate decision.
  Ordinary local mutation (loop accumulators, building a result before returning it) stays
  conventionally mutable; don't route around Python's own idioms to avoid it.
- Legitimate stateful exceptions, not edge cases to explain away: caches, connection pools, rate
  limiters. Make the state explicit, scoped, and (if concurrent) protected — not eliminated.
- One gotcha across every immutability mechanism: freezing a container only freezes the container,
  never its contents (`obj.items.append(x)` works fine on a frozen dataclass with a `list` field).
  `Final`/`ClassVar` have zero runtime enforcement — a type checker actually running is what makes
  them real (see the scaffolding plan's basedpyright config).
- Model default: **overrides.** Models don't default to `frozen=True` — mutable-by-default matches
  Python's own language default, so this is a deliberate opt-in a model won't reach for unassisted.

## Command-line interfaces

- Default: **Typer**, for anything with subcommands, options, or a `[project.scripts]` entry.
  Annotated types carry the CLI metadata, which is the same rule this skill already applies to data
  modeling — the metadata rides in the annotation, not on the right-hand side of a default.
- **`argparse` only under a genuine standard-library-only constraint**, and name the constraint
  rather than assuming it. The real ones are narrow: a script that must run on a bare interpreter
  with no install step, a bootstrap that runs before any environment exists, and code shipped
  somewhere dependencies cannot follow (a Pyodide payload). "It's only a small script" is not one.
- **Typer over raw Click.** Typer is built on Click, so these are not opposites — but a project
  reaching for raw Click is choosing more boilerplate for the same result. Click stays what it is
  underneath, and is the escape hatch for a Typer limitation, not a starting point.
- **Not a rule about task runners.** `inv` is for repo-local work — see `invoke-task-conventions` —
  and a CLI is the program a user installs. They do not compete, and a new command belongs to
  whichever of those two it actually is.
- Model default: **overrides.** Left alone a model writes `argparse`, because that is what the
  standard library offers and what most training data shows.

## Type hygiene

- Scope `# type: ignore`/`# pyright: ignore` comments to a specific error code — never blanket-
  silence a line. Type real code fully, including throwaway example/snippet code — an untyped
  snippet reads as license to skip typing elsewhere to a pattern-matching agent.
- Model default: **mostly confirms.** Scoped ignores are already close to default behavior; "type
  even throwaway snippets" is the real add — the shortcut a model takes when told "just a quick
  example."
- **Testing a type rather than a value:** `assert_type` compares the declared type _exactly_, and a
  function type carries its parameter names — a decorated task body is `(c: Context) -> None`, which
  no `Callable[[Context], None]` expression can spell, so `assert_type` can never match it. Don't
  read that as the assertion failing; it is the precision doing its job. Use an annotated assignment
  instead (`body: Callable[[Context], None] = obj.body`), which still fails if the type degrades to
  `Any` (via `reportAny`) or becomes some other concrete callable. Note that such assertions are
  checked by the type checker and are no-ops at runtime, so say so in the file — a green pytest run
  is not evidence about any of them.
- Model default: **overrides.** Reaching for `assert_type` is the natural first move for "prove this
  type is what I think", and its exactness is easy to misread as a broken assertion rather than a
  precise one.

## Package layout: `src/` over flat

- Default: any installable/importable package in this family uses `src/<pkg_name>/`, not a flat
  `<pkg_name>/` at repo root. A repo's own `tasks.py`/`tasks/` invoke entrypoint isn't a package and
  stays flat at repo root regardless — every repo in this family has one, it's never installed or
  imported elsewhere, and this convention governs the thing that gets built into a wheel and
  imported, not that repo's own tooling scripts. (Confirmed live 2026-08-19 on
  `power-user-linux-setup` itself: its `tasks/` holds ~25 modules of repo-specific invoke tasks, not
  a distributable library — moving it under `src/` would also collide with invoke's own
  `FilesystemLoader`, which walks upward from cwd for a literal `tasks.py`/`tasks/__init__.py` and
  never consults an installed copy.)
- Why: a flat layout lets `pytest`/an import silently resolve to the _uninstalled, cwd_ copy of the
  package instead of what's actually installed (Python puts the cwd first on the import path) —
  masking real packaging bugs (a missing sub-package, an unincluded resource file) until a real user
  installs it. `src/` makes the project root itself un-importable, so both a test run and an
  editable install are forced through the same path a real install goes through. See
  `references/rationale.md` §14 for the full PyPA/Hynek Schlawack citations.
- Escalate to: nothing — this is the default, not an escalation path. A pure script never meant to
  be installed/imported elsewhere (a one-off notebook, `tasks.py` itself) is out of scope for this
  convention entirely, not an exception to it.
- Model default: **overrides.** Flat layout (package directory directly at repo root) is what most
  quick/tutorial code — and most models, absent instruction — default to; `src/` is a deliberate
  opt-in.

## Async and concurrency

- Snippet: [`references/snippets/async-fanout.py`](references/snippets/async-fanout.py)
- Default: plain `def`, not `async def`, for MCP tool functions — FastMCP already dispatches sync
  tools onto a thread pool (`anyio.to_thread.run_sync`), giving real concurrency for free, and 100%
  of this family's existing tool code is sync. For genuine fan-out code (an orchestrator calling
  several MCP clients concurrently), default to `asyncio.TaskGroup`, not `asyncio.gather()` — it
  cancels sibling tasks on the first uncaught exception where `gather()` leaves them running
  orphaned. Reach for `gather(return_exceptions=True)`-style partial tolerance only via a per-child
  `try`/`except` _inside_ a `TaskGroup`, not bare `gather`.
- Why: `gather()`'s siblings-keep-running-after-a-failure behavior is a real resource leak for a
  deliberately throttled/session-holding "polite" client — one site erroring shouldn't leave other
  sites' rate-limited calls or browser sessions running unobserved.
- Escalate to: `asyncio.Semaphore` to cap concurrent in-flight calls at a fan-out layer — a
  different axis from a per-site rate limiter (concurrency count vs. request spacing), compose both
  rather than picking one. If a sync call is unavoidable inside `async def` code,
  `asyncio.to_thread()` is the stdlib escape hatch (the same mechanism FastMCP already uses
  internally for sync tool dispatch).
- **Don't**: run a blocking call (`time.sleep()`, a `threading.Lock`-based throttle, a sync HTTP
  call) directly inside `async def` code — it freezes the entire event loop for its duration, not
  just the calling task.
- Model default: **partial.** Models write async syntax correctly; the specific choice of
  `TaskGroup` over `gather`, and the sync/async tool-function boundary FastMCP imposes, aren't
  something a model infers without being told the framework's actual dispatch mechanism.

### AnyIO as the async API

For a project whose async surface is more than one fan-out — a store, a bot, a service — write
against **AnyIO** rather than `asyncio` directly, and run it **on the asyncio backend**. All four
points confirmed at source.

- **The reason is safety and structure, not portability.** A task group cannot orphan a task the way
  a dropped `create_task` handle can; cancellation propagates through cancel scopes instead of being
  reimplemented per call site; and one set of primitives replaces choosing between
  `gather`/`wait`/`as_completed`/`wait_for` with their differing cancellation semantics. The
  portability argument is the weakest one and should not be the headline — stdlib
  `asyncio.TaskGroup` already gives the fan-out case above most of the structure, so the AnyIO
  decision is about the rest of the surface.
- **asyncio is the backend to be on; trio is a separate choice most projects should decline.** The
  ecosystem is asyncio: SQLAlchemy's async support is asyncio-specific (its `util/concurrency.py`
  uses `asyncio.Lock`/`asyncio.Runner` and greenlet, and "trio" appears nowhere in the library), as
  are `asyncpg` and Starlette. AnyIO's full API is available on asyncio, so this costs nothing.
- **The pytest plugin parametrizes over installed backends only.** The `anyio_backend` fixture uses
  `get_available_backends()`, which returns backends that actually import (AnyIO ≥ 4.12) — so with
  trio absent, every test runs once, on asyncio. Pinning the fixture is a one-line statement of
  intent, not a fix. Worth knowing both halves, because the docs' phrase "all supported backends"
  reads as "all backends that exist".
- **Don't** install `pytest-asyncio` alongside it — AnyIO's own docs call out the conflict in auto
  mode, and AnyIO's plugin ships with AnyIO, so there is nothing extra to install.
- Bridging a synchronous entrypoint (a CLI) to an async layer: `asyncer`'s `runnify` is the small
  wrapper for exactly that, over hand-rolled `asyncio.run` plumbing at each command.
- Model default: **overrides.** A model reaches for bare `asyncio` by default and treats AnyIO as a
  trio-compatibility library, which inverts the actual reason to adopt it.

## HTTP client, sessions, timeouts, and retry/backoff

- Snippet: [`references/snippets/http-retry.py`](references/snippets/http-retry.py)
- Default: `httpx` for any new plain-HTTP fetch path (requests-compatible API, safer default
  timeouts, async-ready). One `Client`/`Session` per fetcher instance, constructed once and reused
  for its lifetime — never a new connection per request. An explicit, site-tuned timeout on every
  request, regardless of client. `tenacity` for retry/backoff: exponential with jitter, scoped to a
  narrow retryable-status set (429/502/503/504) and transient network exceptions, never plain 4xx
  "real answers" like 404/403 — and honor a response's `Retry-After` header when present, in
  preference to the computed delay.
- Why: connection reuse and conservative, `Retry-After`-respecting retry aren't just performance —
  they're direct service to a "polite," rate-limited client's actual mission; retrying aggressively
  or opening a fresh connection per request is antithetical to it.
- Escalate to: nothing — this is the default, not an escalation path. Existing working code using
  `requests` isn't something to churn to httpx without a concrete driving need (see Modularity's
  lean-toward-duplication stance).
- **Don't**: assume any HTTP client's own built-in retry covers HTTP-level conditions — httpx's/
  requests' built-in retry is connection-level only; a 503 or a `Retry-After`-bearing 429 needs an
  actual retry library or hand-rolled logic layered on top. If a rate limiter's throttle call wraps
  a retried function, the retry must happen _inside_ the throttled call, not around it, or a slow
  retry's backoff sleep holds the site-wide rate-limit lock too.
- Model default: **mostly confirms, one real gap.** Models already default to setting a timeout and
  reusing a session/client; they do _not_ reliably default to jittered (vs. plain
  linear/exponential) backoff or to honoring `Retry-After` — the retry-scoping specifics are the
  real add here.

## Full rationale

See [`references/rationale.md`](references/rationale.md) — the full citation trail: sources
consulted, options considered and rejected per topic, and the reasoning behind every branch/
escalation path above. Sections keep their original numbers, so the file has gaps where the testing
and MCP sections were moved out to their own skills on 2026-08-31 — the numbers are stable
references, not a sequence. §1–8 were originally researched and written up in
`plans/2026-08-15-python-conventions.md`, migrated here once that plan promoted from `idea` to this
built skill (the plan file has since been retired — see git history if you need it). §12 onward
(async/concurrency, HTTP/retry, and `src/`-layout) were researched directly against this skill after
that promotion, with no separate plan-file stage.

## Starter snippets

`references/snippets/` has one real, ruff-clean, self-contained Python file per pattern above — each
directly copy-pasteable rather than a tutorial to adapt. Each topic's "Snippet:" line above links
straight to its own file.

## Editing this skill

This file is _copied_ into `~/.agents/skills/python-conventions` at install time, never symlinked.
Edit the source in the [`agent-skills`](https://github.com/TheodoreAD/agent-skills) repo, push, then
re-run the install (`npx skills add TheodoreAD/agent-skills --global --skill python-conventions`) to
refresh every project's copy. Editing the deployed copy in place is local drift — the exact thing
this skill exists to prevent — and it reaches no other machine.
