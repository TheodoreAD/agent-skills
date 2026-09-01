# The pilot: a whole-module encapsulation pass, 2026-09-01

Every rule in `SKILL.md` comes from one pass, run on one real module before any of it was written
down. The repo's own authoring rule is that a convention is applied to a real repo before it becomes
a shareable artifact — a pilot surfaces what research cannot — so this file is the evidence, and the
skill body is what survived it.

**The subject**: `skills/plan-docs/scripts/plans.py` in this repo, 3,210 lines at the time the plan
was written and 3,476 by the time the pass ran, built incrementally over two weeks and never
reviewed as a whole. A review of _recent changes_ had already been done and had found one real bug
and two cleanups; the structural pass is the one nothing else does.

## The complaint, stated as counts

Taken 2026-09-01, before anything moved:

| signal                                                     | count              |
| ---------------------------------------------------------- | ------------------ |
| functions taking `cfg` (or `cfg, routing`) as leading args | 69 (see below)     |
| `load_config()` calls                                      | 21 for 18 commands |
| `resolve(args.path, cfg)`                                  | 12                 |
| `require_ok(resolve(args.path, cfg))` — the same prologue  | 7                  |
| module length / function count                             | 3,210 lines / 158  |

And the second half, which the first draft of the plan led with the smaller of:

| the anonymous shape                                 | count       |
| --------------------------------------------------- | ----------- |
| bare `tuple[...]` returns                           | 22          |
| sites unpacking them positionally                   | 39          |
| dict-shaped returns / fields / parameters           | 8 / 13 / 10 |
| stringly-keyed `routing.dirs["store"]` accesses     | 7           |
| `NamedTuple` in the file today / frozen dataclasses | 0 / 6       |

**158 functions at ~20 lines each was not the problem**, and a pass that "fixed" it would have made
things worse. The file was already decomposed; the longest function was a declarative parser
builder. The complaint was that state which is constant for a whole invocation was passed as an
argument dozens of times, and that a reader — human or agent — could not tell from a signature
whether a function needed the config for a path, a rule, a tier or a root.

Restated by the user mid-plan, and this is the framing worth keeping: **not OOP over functions.
Clear boundaries, with the types reflecting them; objects rather than dicts and tuples; and each
contiguous unit having an API surface that callers cannot reach around.** The shape of the data is
information, and an agent reading a signature to decide what to do with a value is the reader that
suffers most when the shape is anonymous. Deduplication was a side effect, never the goal.

## The target shape

One object per invocation, constructed in `main()` from the one argument every subcommand has,
holding what is resolved once and exposing the rest as `cached_property`:

```python
class Workspace:
    """Everything one invocation needs, resolved once: the config, where this repo routes, the stores."""

    def __init__(self, path: Path) -> None: ...

    @cached_property
    def config(self) -> Config: ...
    @cached_property
    def routing(self) -> Routing: ...
    def require_routable(self) -> Routing: ...  # was: require_ok(resolve(args.path, cfg))
```

Three properties it buys, in the order they mattered: the three-line prologue disappears; the
expensive derivations are computed once instead of per command that needs them; and a signature says
what a function needs.

Decisions taken along the way that the skill body only summarises:

- **A per-invocation object, not the module-singleton pattern.** `python-conventions`' `globals.py`
  shape is for process-wide state; this is per-invocation, and the tests construct it repeatedly
  against different fake homes. A module-level instance would have been exactly the shared global
  the suite avoids.
- **The command functions stayed free functions** taking the workspace as an argument, rather than
  becoming methods. The encapsulation win is in the shared state, not in where command bodies live,
  and making them methods would have put argument parsing and domain logic in one 2,000-line class —
  the extract-on-sight instinct `python-conventions` warns about.
- **`NamedTuple` was an upgrade for bare tuples and would have been a downgrade for the frozen
  dataclasses.** A `NamedTuple` is indexable, unpackable, iterable and compares equal to a plain
  tuple, which is a second positional API surface nobody designed. Replacing a bare tuple, that
  surface already exists and is already being unpacked at 39 sites, so nothing new leaks. Replacing
  a frozen dataclass, it adds all three. The 6 frozen dataclasses stayed as they were.
- **Dicts stay at the serialisation boundary and nowhere else.** The `dict[str, object]` payload
  builders exist to be handed to `json.dumps`; the dicts worth removing are the ones used as
  records, where two named fields turn a typo from a runtime `KeyError` into an error a checker
  catches.

## What actually moved

Nine commits, steps 1-7, all landed 2026-09-01. Re-measured with the same AST walk against the same
file:

| signal                                       | before | after | note                       |
| -------------------------------------------- | -----: | ----: | -------------------------- |
| stringly-keyed `routing.dirs[...]` accesses  |     14 | **0** | step 1                     |
| bare + nested anonymous `tuple[...]` returns |     22 | **5** | steps 2 and 3              |
| — of those, record-shaped                    |     16 | **0** | the 5 left are collections |
| positional unpacking of an anonymous return  |      9 | **0** |                            |
| `NamedTuple` classes                         |      0 |    13 |                            |
| frozen dataclasses                           |      6 |     7 |                            |
| `dict[...]` class fields                     |      4 |     3 |                            |
| functions taking `cfg` first                 |     47 |    38 | steps 4-6                  |
| `load_config()` calls                        |     20 | **2** | step 4                     |
| `resolve(args.path, cfg)`                    |     12 | **0** | step 5                     |
| `require_ok(resolve(...))`                   |      8 | **1** | step 5                     |
| projects-tree walks in one command run       |      5 | **1** | step 6                     |

The order was: name the shapes first (stringly-keyed lookups → named fields; anonymous tuple returns
→ `NamedTuple`; four parallel `Config` fields → one frozen record, which deleted the accessor that
existed only to pick between two of them), then introduce the object with one property, then one
derived property per commit.

## The two counts that did not reproduce, and why it matters

**69 config-taking functions measured 47 with `cfg`/`config` leading and 55 with either anywhere in
the signature.** There is no reading of the AST that gives 69, so steps 4-6 had to be judged against
47/55 rather than against the number the plan had been arguing from. **7 `dirs` lookups was 14** by
the time step 1 ran. The 22 tuple returns reproduced exactly (12 bare + 10 nested inside a `list`).

This is why `SKILL.md` says to take the baseline with the script rather than by hand: a
hand-collected count is not merely imprecise, it silently changes what the pass appears to have
achieved, in either direction.

The related honesty point: **all 5 anonymous tuple returns left are `tuple[str, ...]`** —
homogeneous variadic tuples, which are collections rather than records. There are no positions to
name, so a `NamedTuple` has nothing to add. The honest reading of the original 22 is that 16 were
records and all 16 are now named.

## The oracle, as it actually held

The suite was 105 tests in one file, classified before anything moved:

| tests  | what they do                             | may they change?          |
| ------ | ---------------------------------------- | ------------------------- |
| **65** | drive the CLI only — `plans.main([...])` | **no, not one character** |
| 24     | drive the CLI _and_ touch an internal    | the call form only        |
| 16     | touch an internal name only              | the call form only        |

**Not one of the 65 CLI-driven tests changed.** 15 of the other 40 changed call form only: 7
`.dirs["store"]` → `.store_dir`, 6 for the new record, one `[1]` → `.source`, one positional unpack
→ a named attribute.

**The revert-check was run and it earned its place**: the `.store_dir` rewrites were checked by
breaking `store_dir` in the resolver and confirming the edited tests fail. Without that, an edited
test that still asserts the same thing but no longer reaches the code under it is indistinguishable
from a correct rename by reading the diff.

Two smaller findings from the same area:

- A test comparing one of the new records to a plain tuple literal was left exactly as it was and
  still passes — the positional compatibility that made `NamedTuple` the right replacement for a
  bare tuple, asserted by a test nobody had to write for it.
- **`load_config` appearing in 20 tests was an argument for the pass, not a cost of it.** The tests
  reached for a module-level loader because there was no object to construct; afterwards they
  construct one against a fake home, which is better ergonomics than monkeypatching a global.

## The second oracle, and the pitfall that produced it

[DECISION: **a type change under a name every caller uses needs a second oracle, because its failure
mode is silent.** Step 3 renamed nothing: `cfg.store` stayed `cfg.store` and became a record, so a
missed call site does not raise — it interpolates `Store(tier=..., path=..., source=...)` into
output, and the suite only covers the lines it asserts on. The check that settles it is running
every read-only command before and after and diffing: all 15, `--json` payloads included,
byte-identical. Cheap — one shell script in the scratchpad — and it is the only evidence that
reaches the output lines no test reads.]

[PITFALL: **the output oracle compares live machine state, so a long session's two captures are not
comparable.** The step 6 diff came back with changes to plan files in two unrelated repos — tag
counts and `updated` stamps — which no part of the pass touched: a parallel session had edited them
between the baseline capture and the check, and the command being captured reads every repo on the
machine. Capture both sides back to back instead, running the committed copy of the script
(`git show HEAD:<path> > <tmp>`) against the working tree seconds apart. The corrected form is what
the step 4-6 commits were verified with.]

## What was dropped mid-pass, and why that is the rule working

- **A `stores` property did not go on the workspace.** `Config.stores()` is a pure function of the
  config with nothing to cache, so a workspace property would have been a second door to the same
  answer — the opposite of "callers cannot reach around the API".
- **The session anchor was not cached.** It measures **1.9 ms**, against the tree walk's 3.9 ms,
  which was the one being repeated five times. Caching it would have been the speculative-need case
  the stopping rule rejects.
- **Three config reads deliberately stayed direct**, each a place the cache would be wrong rather
  than merely unnecessary: a command that re-reads the file it just wrote so it can reject a bad
  value next to the change, and two that resolve a path which is not the session's — a different
  question the workspace cannot answer.
- **A frozen-record sweep over four unfrozen classes was deferred to its own commit.** Real and
  small, but bundling it here would have made the diff harder to verify as behaviour-preserving.

## What the numbers do and do not say

The invocation-scoped threading is gone: nothing re-reads the config, nothing re-resolves the
routing, and no answer derived from the projects tree is computed twice. What did **not** move much
is the count of functions taking `cfg` first, 47 → 38 — and on reading them, that is the right
answer rather than unfinished work. What is left is pure functions _of_ the config: a rule matcher,
a tree walk, a term derivation, the session-anchor family. A function that takes the config because
it derives something from it has a signature that says exactly that; handing it a whole workspace
instead would be the same anonymity one level up. The original 69 counted those together with the
threading, which is why the problem read as bigger than it was.

**The performance win is honest but small**: five walks to one saves about 16 ms on the heaviest
command. The value is structural — one answer computed in one place — not speed, and the write-up
should not be read as having claimed otherwise.

**Two findings the plan did not predict**, both of which are the argument for the pass rather than
consequences of it:

- **Two commands never needed the config at all.** Each held one only to feed the resolver or a
  derivation, and the linter flagged the variable as unused the moment the prologue went. The
  config-taking opening was hiding what those commands actually depend on.
- **One command resolved the session's own path twice in one function**, once for each of two
  fields. That is duplication the object removes rather than tidies.

Two shapes were noticed and deliberately left for their own commits: an anonymous
`list[tuple[str, int]]` threaded through two functions as a _parameter_ — the same shape one layer
out from what the measurement counted, which is why the measurement never saw it — and a payload
builder that could now take one of the new records.

## Source

The now-retired `plans/2026-09-01-plans-py-encapsulation-pass.md` in this repo — this page is where
its content went, so there is nothing left to go and read — and the nine commits `2efb0c8..9dd62dd`.
The commit sequence is itself the worked example of the loop: each one property, each message saying
what moved and what was verified.
