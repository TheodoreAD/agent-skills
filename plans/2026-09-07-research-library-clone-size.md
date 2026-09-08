---
status: in-progress
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
checkout materialises every blob at HEAD anyway, so the filter has nothing left to defer.

**Corrected 2026-09-07, same day: that is true of the filter _alone_ and wrong as a general
conclusion.** Give the clone a sparse set and the excluded blobs are never wanted, so they are never
fetched — `.git` on a real 97%-binary repo went 71,204 KB → **644 KB** with the same patterns
applied. The two are useless separately and transformative together, which is exactly the shape a
settled-looking negative result hides. It shipped: `skills/research-library/SKILL.md`, "Clones hold
text, because that is all anyone searches", carries the correction and the numbers. The plan that
measured it, `2026-09-07-research-library-text-only-clones.md`, is **retired** — `plans.py archive`
reads it back.

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
constraint history. `research-update` loops every entry under `repos/` with `fetch --depth 1` and
would truncate it back to 1, with no warning and nothing to notice afterwards.

**The store had already recorded the reason, and nothing was reading it.** That entry's `SOURCE.md`
carries a `depth:` line — a whole sentence, "deepened to ~436 commits …, not the usual `--depth 1`",
written when the divergence was made because the store's convention asks for the divergence _and_
why. So the fix needed no new metadata and no migration: `update` reads the field that was already
there. It is also why the field accepts prose rather than an integer — an integer-only reading would
have treated that entry as unrecorded and truncated it. The hazard stands for the external
`research-update`, which reads no provenance at all.

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

## What landed

All five commands, with tests, and each measurement above recorded at the function that depends on
it: `size --min`, `update`, `deepen`, `reshallow`, and `add`'s pre-clone size question. Verified end
to end against a real deepened clone — `.git` 5,288 KB → 2,468 KB, 401 commits → 1, 15 tags → 0,
`depth: 1` recorded — which is below the 2,492 KB a fresh `--depth 1` clone costs.

`derivable` now reports 13 commands, 12 delegated, 0 derivable, against 7/6/0 before. The score did
not move because it was already 0: the operations that had no command line at all were invisible to
it, which is the separate finding filed as `2026-09-07-derivable-cannot-see-a-missing-command.md`.

[DECISION: one threshold, 250 MB, shared by the report and the pre-clone question, moved by `--min`
on both. 100 MB names fourteen of this library's entries and reads as a list of ordinary repos; 500
names two. Shared rather than split because two numbers would need two justifications and the
evidence only supports one.]

[DECISION: `update` skips a clone deeper than one commit with nothing recorded, rather than
truncating it or migrating anything. That is safe with no migration step at all — the unsafe case is
exactly the case it declines to act on — and it turned out the real library's one deep entry already
carried its reason in `SOURCE.md`, because the store's convention had asked for it.]

[DECISION: `size` is its own command rather than a section of `check`. `check` answers "does this
store follow its conventions" and size is not a convention violation; folding it in would have made
one command answer two questions with one exit code.]

[DECISION: `reshallow` refuses on a detached HEAD, with `--force` to override. That is the
pinned-at-a-tag signature `check` already detects, and it is the one shape where deleting every tag
destroys the thing the clone exists to read.]

## Open questions

[NEEDS CLARIFICATION: does `add` take a **path**-based `--sparse` at all? The saving on
`nodejs/node` is a 6x lever and the cost is that a grep silently does not see the excluded
directories — silent, which is the failure mode this corpus weighs heaviest. Still open, and
deliberately separate from the type-based exclusion below, which is safe by construction and hits an
almost disjoint set of entries. A middle answer worth testing: allow it, record the excluded paths
in `SOURCE.md`, and have `check` report any entry whose checkout is partial, so "the grep saw
everything" is never assumed.]

[DECISION: the **type**-based half of this split off on the user's reframing — exclude what a grep
skips anyway, since the library exists to search text and never to run anything. Measured at 41% of
the library's working-tree bytes, and safe in a way path exclusion is not, so deciding the two
together because both are spelled `sparse-checkout` would have held the safe one hostage to the
risky one. **It landed 2026-09-08 and its plan, `2026-09-07-research-library-text-only-clones.md`,
is retired**: the mechanism is in `SKILL.md` and `library.py`, the retrofit's own lessons in
`references/rationale.md`. What it hands this plan is that `check` now reports any sparse checkout
nothing records, whatever narrowed it — the "so the grep saw everything is never assumed" half named
below.]

[NEEDS CLARIFICATION: what happens to the machine's `research-update` once `library.py update`
exists? Two implementations of one guarantee is the thing worth avoiding — the wrapper should become
a one-line call into the skill's script, which is a change in another repo and therefore filed
rather than made from here.]
