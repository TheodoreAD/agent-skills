---
status: idea
updated: 2026-09-07
---

# The research library should own its clones' whole lifecycle in code, size included

## Context

Asked for by the user 2026-09-07, twice. First: keep clones shallow on update, keep a record of
repos that cause disk-space trouble, warn when cloning, when updating and on demand — all
scriptable. Then, on reading the first draft: _"everything in a skill that can be done with a script
should be done with a script, we should have a rule for that already. the library skill should be
able to clone, update, clone with larger history, reduce to shallow again, create a size report with
a minimum problematic size, and so on."_

**The rule does already exist**, in this repo's `AGENTS.md` and in `skill-authoring`: anything a
skill can derive deterministically belongs in `scripts/`, not in the body, because prose telling an
agent how to spell a command has to be followed correctly on every run and fails silently when it is
not. `fitness.py derivable --compare` measures the drift and `tests/unit/test_derivable.py` gates
it. So this plan is that rule applied to one skill, not a new principle.

Everything below was measured before designing anything, and the measurements changed the plan
twice.

## What the measurements say

### The store today

71 repo entries, **4.8 GB**. The largest three are 2.1 GB of it — 43% in three directories.

| entry             | on disk | `.git` | working tree | commits |
| ----------------- | ------- | ------ | ------------ | ------- |
| `nodejs/node`     | 940 MB  | 122 MB | ~818 MB      | 1       |
| `block/goose`     | 646 MB  | 296 MB | ~350 MB      | 1       |
| `RooCode`         | 473 MB  | —      | —            | 1       |
| `aiogram/aiogram` | 33 MB   | 9 MB   | ~24 MB       | **436** |

**70 of 71 entries sit at exactly one commit.** Shallowness is not eroding, because the machine's
refresher already re-shallows on every fetch (`git fetch --depth 1 origin` then
`reset --hard FETCH_HEAD`). So the request's premise — clones drifting deep over time — is not what
is happening here, and a plan that only kept them shallow would have reported success while the
store grew.

### 1. Depth is not where the size is

`nodejs/node` is 940 MB at **one commit**, and the breakdown says why:

| directory | size       |
| --------- | ---------- |
| `deps/`   | **675 MB** |
| `test/`   | 100 MB     |
| `doc/`    | 19 MB      |
| `src/`    | 8 MB       |
| `lib/`    | 7 MB       |

`deps/` is vendored V8, OpenSSL and friends — third-party code with its own upstream, and precisely
what nobody greps to learn how node itself works. The parts a reference clone exists for total **~34
MB of 940**. That makes a targeted sparse checkout a ~6× lever on the worst entry, and reframes it
from "risky, breaks grep" to "the single biggest saving available, decided per entry".

### 2. A blobless partial clone saves nothing here

Measured on the same repo, same minute: `git clone --depth 1` and
`git clone --depth 1 --filter=blob:none` both produce **6 MB total, 3 MB `.git`**. At depth 1 the
checkout materialises every blob at HEAD anyway, so the filter has nothing left to defer. `--filter`
is a history optimisation and this store has no history to optimise. Ruled out, with a number.

### 3. Re-shallowing reclaims nothing — until the tags go

This is the finding that changes the design, and it contradicts the advice every guide gives.
Measured end to end on one repo (`encode/httpx`), `.git` in KB:

| step                                                                     | `.git`       | commits |
| ------------------------------------------------------------------------ | ------------ | ------- |
| fresh `clone --depth 1`                                                  | **2,492 KB** | 1       |
| `fetch --deepen 400`                                                     | ~6,000 KB    | 401     |
| `fetch --depth 1` + `reset --hard`                                       | ~6,000 KB    | **1**   |
| \+ `reflog expire --expire=now --all` + `gc --prune=now`                 | 5,000 KB     | 1       |
| \+ `repack -a -d` + `prune --expire=now` + `gc --aggressive --prune=now` | **4,852 KB** | 1       |
| \+ **`git tag -d $(git tag)`** + `reflog expire` + `gc --prune=now`      | **2,472 KB** | 1       |

The commit count returns to 1 at step three while the disk does not move at all, and every
documented reclaim command after it recovers about half. The cause is **tags**: `fetch --deepen`
brings 18 of them, each pinning a commit deep in history, so those objects stay reachable and no
`gc` will ever drop them. Delete the tags and the clone returns to **below** its fresh-clone
footprint.

Consulted while measuring, and it is where the omission shows: a widely-circulated write-up gives
`fetch --depth` → `reset --hard` → `reflog expire` → `gc --prune`, explicitly says plain `fetch`
alone is insufficient, and names re-cloning as the alternative — with no mention of tags. Run
verbatim, that sequence leaves a clone permanently **95% larger** than a fresh one and reports
success.

This is the case the existing rule is about. Nobody will type five commands in the right order,
including one that no reference material mentions, on every entry, correctly, forever.

### 4. GitHub's reported size is a trigger, never a number

`gh api repos/<owner>/<repo> --jq .size` returns the packed repository in KB. Against on-disk cost
at depth 1:

| repo                  | API     | on disk | ratio     |
| --------------------- | ------- | ------- | --------- |
| `python/cpython`      | 851 MB  | 192 MB  | **0.23×** |
| `sst/opencode`        | 488 MB  | 224 MB  | 0.46×     |
| `nodejs/node`         | 1513 MB | 940 MB  | 0.62×     |
| `block/goose`         | 947 MB  | 646 MB  | 0.68×     |
| `RooCodeInc/Roo-Code` | 359 MB  | 473 MB  | **1.32×** |

A 5.7× spread, and **not an upper bound** — `RooCode` lands above its API size. So it is usable to
decide _whether to warn_ (everything ≥ 350 MB reported came out ≥ 224 MB on disk; everything small
stayed small) and unusable to state _how much_. A warning quoting a predicted megabyte figure would
be wrong by 4× in the reassuring direction on `cpython`.

### 5. The shallow guarantee is unowned, and the derivable gate cannot see it

`library.py` has `name`, `add`, `provenance` and `check`, and **no `update`**. The re-shallowing
lives in `~/.local/bin/research-update`, a script in a different repo that `SKILL.md` mentions only
as "where the machine provides a refresher on `PATH`". A reader who installs the published skill has
prose to follow rather than code to run — and `SKILL.md`'s own disclosure block already claims
"`update` refreshes clones", naming a subcommand that does not exist.

`fitness.py derivable` scores this skill **0 derivable, 6 delegated** — a clean bill of health. It
is right about what it measures and blind to this: the measure reads _command lines in fenced
blocks_, and an operation described in prose with no command line at all scores exactly like a
perfectly delegated one. Filed separately as `2026-09-07-derivable-cannot-see-a-missing-command.md`.

### 6. The refresher will silently destroy a deliberate divergence

`aiogram` sits at 436 commits because a session deepened it on purpose to read a dependency's
constraint history — recorded at the time as a store divergence. The next `research-update` run
loops every entry under `repos/` with `fetch --depth 1` and truncates it back to 1, with no warning
and nothing to notice afterwards. A live hazard in the current tooling, found by measurement.

## Recommended direction

A command per lifecycle operation, each carrying a sequence nobody should be retyping. Names are
provisional; the shape is the proposal.

```shell
library.py add <url> [--depth N] [--sparse <path>...] [--yes]   # clone, sized and warned first
library.py update [<entry>...] [--all]                          # refresh, preserving intent
library.py deepen <entry> [--depth N | --full]                  # and record why
library.py reshallow <entry>                                    # the five steps, tags included
library.py size [--min MB] [--json]                             # the report, on demand
library.py check                                                # unchanged: conventions
```

**`add`** asks the host for the repo's size first and warns above a threshold, apt-shaped: proceed
by default, `--yes` to skip the prompt, never refuse. It warns that the repo is large without
claiming how large, per finding 4.

**`update`** is the existing refresher moved into the skill, plus the two things a directory loop
cannot do: skip an entry whose provenance records a deliberate depth, and print a per-entry size
delta so a clone that grew is visible in the run that grew it.

**`deepen`** exists so that deepening is a recorded act rather than a hand-typed `git fetch` that
`update` later undoes. It writes `depth:` into `SOURCE.md`, which `provenance` already owns and
`check` already reads.

**`reshallow`** is finding 3 as code — including `git tag -d`, which is the step that makes the
other four worth running. It is the answer to "reduce to shallow again", and it is the clearest case
in this plan for the rule the user restated.

**`size`** answers "when a report is requested": per entry, `.git` split from the working tree,
sorted, with a store total and a `--min` threshold below which nothing is printed. That is the
"minimum problematic size", and making it a flag rather than a constant is what stops the number
becoming an argument.

**The record is derived wherever it can be.** `du` per entry is exact, needs no maintenance and
cannot go stale; the host's API covers the one case measurement cannot reach, which is the moment
before a clone exists. A hand-curated list is a third source of truth that would disagree with both.

## Open questions

[NEEDS CLARIFICATION: what is the default `--min` for the size report, and does `add` warn at the
same number? 100 MB fires on 14 of 71 entries here, 500 MB on 3. The two thresholds may want
different answers — a report wants to be readable, a pre-clone warning wants to fire before the
download rather than after.]

[NEEDS CLARIFICATION: does `add` take `--sparse` at all, given finding 1 is a 6× lever and finding 2
ruled out the safe alternative? The saving is real and the cost is that a grep silently does not see
excluded paths — silent, which is the failure mode this corpus weighs heaviest. A middle answer
worth testing: allow it, record the excluded paths in `SOURCE.md`, and have `check` report any entry
whose checkout is partial, so "the grep saw everything" is never assumed.]

[NEEDS CLARIFICATION: does `update` re-shallow by default, or only when an entry has no recorded
depth? Re-shallowing every entry every run is what destroys `aiogram`. Doing it only for entries
without a `depth:` field is safe but means the field must exist before the first run of the new
command, or the first run destroys the divergence it was written to protect. A one-time migration
that records the current depth of every entry is probably the honest answer.]

[NEEDS CLARIFICATION: does the size report belong in `check` or its own `size` command? `check`
answers "does this store follow its conventions" and size is not a convention violation. Separate
keeps each answer clean; folding it in means one call rather than two. Leaning separate, with
`check` printing a one-line pointer when the store is above some total.]

[NEEDS CLARIFICATION: what happens to the machine's `research-update` once `library.py update`
exists? Two implementations of one guarantee is the thing worth avoiding — the wrapper should become
a one-line call into the skill's script, which is a change in another repo and therefore filed
rather than made from here.]

[NEEDS CLARIFICATION: is the tag deletion in `reshallow` ever wrong? It is right for a disposable
reference clone, which is what every entry here is. It would be wrong for anything where a tag is
the thing being read — a clone made to compare release tags, say. `check` already detects the
pinned-at-a-tag shape, so refusing to reshallow such an entry is probably the guard.]
