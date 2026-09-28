---
status: idea
updated: 2026-09-28
depends_on: [repo-tasks]
---

# This repo is as far behind on the shipped configs as the worst consumer, and nobody had looked

Filed 2026-09-13 from a `repo-tasks` session. Nothing was written to this tree — the measurement is
read-only, run from outside the repo, and no `pull`, `ensure-deps` or lock ran here.

**Amended 2026-09-26** by merging in `2026-09-26-bootstrap-pin-decision-and-two-reported-items.md`,
filed from `repo-tasks` session `a9904181-df08-4eb5-945e-8aab9336d457`. That filed plan described
itself as an amendment to this one. It added the stamp step (step 7), corrected step 1's "no pin to
bump", and marked two complement items as reported by `consumers.diff`. The decision behind the
pinning is owned by `repo-tasks`' `plans/2026-08-25-consumer-transitions.md`: read it before
implementing, since it may have moved on since.

**Amended again 2026-09-27** by merging in `2026-09-27-sweep-to-repo-tasks-v0-5-0.md`, filed from
`repo-tasks` session `bcf810d6-38c7-48d3-adfe-2ff30399d4c9` after `v0.5.0` was released. That filed
plan said this one "may fold into this one". It is the same sweep one release later, so it lands
here as the section "What v0.5.0 adds, measured 2026-09-27", and not as a second plan for one job.

**Amended a third time 2026-09-28** by merging in `2026-09-28-sweep-to-repo-tasks-v0-6-0.md`, filed
from `repo-tasks` session `44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl` (moment 2026-09-28T11:15:00Z)
after `v0.6.0` was released. Same sweep, one release later, so it lands as the section "What v0.6.0
adds, measured 2026-09-28". The filed original is in the shareable store's history, removed by its
absorption commit `e61e8ba`.

## Why this arrives now, three days after being recorded as a consumer

`repo-tasks` ships four config files and a `repo-tasks-quality` dependency manifest that every
consumer snapshots and then drifts from. This repo was recorded as a consumer on 2026-09-10, after
an earlier plan there had wrongly stated it was not one — it has had `tasks.py` and
`bootstrap-repo-tasks.sh` since `9e49f39`, 2026-08-27.

Being recorded changed nothing, because measuring still meant somebody deciding to go and look, and
for three days nobody did. What found it was `inv consumers.diff` landing in `repo-tasks` on
2026-09-13: **this repo came out of its first run item-for-item as drifted as `ingesta`**, which was
the worst of the three consumers measured by hand earlier that day.

That is worth stating plainly here rather than only in the producer's plan: membership and
measurement are different problems, and being on the list is not being looked at.

## What it is behind on (measured 2026-09-13, read-only)

`inv consumers.diff --name agent-skills`, from the `repo-tasks` working tree at `da9b8b7` (reporting
as `0.3.0`):

| what                    | state                                                                          |
| ----------------------- | ------------------------------------------------------------------------------ |
| `ruff.toml`             | behind — the `sys.path` / `site.addsitedir` bans, and the `target-version` pin |
| `pyrightconfig.json`    | behind — derived `pythonVersion`, `extraPaths: ["."]`                          |
| `dprint.json`           | behind — sha256 checksums on all five plugins                                  |
| `pytest.ini`            | behind — derived `anyio_mode`, three `filterwarnings` ignores                  |
| `dependency-groups.dev` | **missing `pytest-socket`, `pytest-timeout`**; `hadolint-py` unconstrained     |

Four files and two missing manifest entries. `scaffoldapy` is behind on three files and no entries;
`invoke-stubs` on two.

**Re-measured 2026-09-26: the table above still holds item for item**, and `inv consumers.diff` now
reports two more lines of its own, `bootstrap unpinned` and no caller for `security-reusable.yml`.
Both used to be complement items that someone had to remember; the tool now reports them. See the
sweep's step 7 and "What no diff can tell you" below.

## What v0.5.0 adds, measured 2026-09-27

`repo-tasks` `v0.5.0` was released 2026-09-27, and this machine's global tool is on it. It was
measured read-only from `repo-tasks`' session with the installed tool, and `git status` here was
clean after. This repo had the largest findings of the five consumers.

- **`inv configs.check-include`: `skills/` holds 34 tracked `.py` files that basedpyright has never
  checked**, plus 1 under `plans/`. The skill scripts are shipped code that other machines run, so
  `skills*` probably belongs in `repo-tasks.toml`'s `[pyright] extra-include`, then
  `inv configs.pull`. `plans*` belongs in `[pyright] unchecked`. How many findings basedpyright
  reports once `skills/` is covered was not measured. Stdlib-only scripts written without the gate
  may carry a real backlog.
- **`inv deps.check-currency`, run after `inv deps.lock`: 7 of 14 manifest entries are behind.**
  `invoke-stubs` is 0.1.0, locked at `c2a1a7c`, while its default branch is at `f70ff01` (0.3.0),
  the same lag `power-user-linux-setup` has. Also behind:
  - `basedpyright` 1.39.10 (latest 1.40.1)
  - `ruff` 0.16.4 (0.16.9)
  - `shfmt-py` 4.0.0 (4.2.0)
  - `dprint-py` 0.56.1.0 (0.57.4.0)
  - `actionlint-py` 1.7.12.24 (1.7.12.25)
  - `zizmor` 1.29.0 (1.30.1)

  A plain lock keeps old pins, so take each one with `inv deps.lock --package <name>`.
- **`pytest-socket` and `pytest-timeout` are still missing from the dev group**, as in the
  2026-09-13 table. `configs.ensure-deps` adds them (step 5).
- Also new in `v0.5.0`, not needed for this sweep: `inv dist.check-isolated`, the pin-comment check
  in `inv ci.check-actions`, `inv repo-tasks.status --latest`, `docker.logout`/`helm.logout`, and
  `venv.sync --extra/--group`.

[NEEDS CLARIFICATION: cover `skills/` in this sweep, or first measure its basedpyright backlog
without declaring it? Declaring it makes the gate red until the backlog is fixed. The filing
session's recommendation: measure first (`basedpyright skills` against this repo's venv), then
decide whether to declare now or in a follow-up.]

## What v0.6.0 adds, measured 2026-09-28

`repo-tasks` `v0.6.0` was released 2026-09-28 (tag on `a2d9cf5`, CI/Security/Canary green), and this
machine's global tool is already on it. What it carries for a consumer:

- **Shipped configs:** `pyrightconfig.json` drops `allowedUntypedLibraries: ["invoke"]`.
  `zizmor.yml` disables zizmor 1.30's `self-repository` audit, because actionlint and act both
  reject its `uses: $/` fix.
- **`deps.check-currency`:** an excluded latest reads as excluded, not BEHIND. uv and gh output is
  forced plain wherever `repo-tasks` parses it.
- **gitflow PR mode:** finished branches are deleted, and a stale base is refused. Does not apply
  here — this repo uses no `gitflow.*`.

`inv consumers.diff` from `repo-tasks`, 2026-09-28, reports this repo as **the widest drift in the
family**:

- **Config files behind: `ruff.toml`, `pyrightconfig.json`, `dprint.json`, `pytest.ini`, and now
  `zizmor.yml`** — five, one more than the 2026-09-13 table.
- **Dev group still missing `pytest-socket` and `pytest-timeout`.**
- **`hadolint-py` still declared without the manifest's constraint, `!=2.15.1.2`.** That release's
  macOS wheel is a corrupt zip, so a lock taking it breaks on macOS (step 4).
- **Bootstrap still unpinned** (step 7).
- **Still no caller for the shared `security-reusable.yml`**, so this repo runs no dependency audit
  (see "What no diff can tell you").

Nothing in v0.6.0 changes the sweep's order. Five configs at once is where a reflowed file or a
tightened lint shows up, so step 2's "read the diff rather than accepting it" carries more weight
than it did.

## The one item that can turn this repo's gate red, and it is a real defect

**`pyrightconfig.json` has no `pythonVersion`, so basedpyright validates against this repo's 3.14.5
venv rather than the `>=3.11` it declares. Pulling the config moves it to the declared floor** — and
`tests/unit/test_harvest.py:24` does `from typing import override`, which is 3.12+ (PEP 698) and
does not exist on 3.11. No `typing-extensions` is declared.

This is the third occurrence of the same thing and the pattern is now clear:

| repo                     | where                                  | when       |
| ------------------------ | -------------------------------------- | ---------- |
| `power-user-linux-setup` | two test modules                       | 2026-09-05 |
| `ingesta`                | four modules, two shipped in the wheel | 2026-09-13 |
| `agent-skills`           | one test module                        | 2026-09-13 |

**This one is the mildest of the three**, and that matters for how it is fixed: the import is in a
test, not in anything this repo ships, so the choice is local rather than a decision about a
published artifact. Either import `override` from `typing_extensions` and declare it as a dev
dependency — which is what `power-user-linux-setup` had already done deliberately, with a comment
saying so — or raise `requires-python`. The first is the smaller change and matches the family.

[PITFALL: this is a finding, not a regression the sweep causes. The test has been passing only
because nothing was checking at the declared floor. Both guards that would have caught it are
**absent rather than failing** — a suite run on 3.14 and a type check run on 3.14 agree with each
other perfectly and neither is looking at 3.11.]

## The sweep, in order

`repo-tasks`' `contributing/consumer-sweep.md` is the authority; this is the per-repo shape.

1. `inv repo-tasks.update` — one global step, not per-consumer. Locally this repo takes `repo-tasks`
   as the global `uv tool` install, so its **task code is current on this machine**; the pulled
   config files and the dev group are snapshots that lag. **CI is a different matter, corrected
   2026-09-26.** `bootstrap-repo-tasks.sh` here carries the unpinned form, `repo-tasks @ git+<url>`
   with no `@vX.Y.Z`, and `ci.yml` runs it. So CI installs whatever `repo-tasks` `main` is at run
   time, while a developer here is on whatever `update` last fetched, and a local green says nothing
   about CI. The pin is step 7. Run `update` first for a second reason as well: the sweep runs
   whatever `repo-tasks` this machine has installed, and one installed before 2026-09-26 has the
   `configs.ensure-deps` bug described under step 5.
2. `inv configs.pull`, then read the diff rather than accepting it — particularly the derived
   `pythonVersion` and `anyio_mode`, which are computed per consumer and so are not expected to
   match another repo's copy byte for byte.
3. Fix the `typing.override` import, per the section above. The gate will not pass until it is done.
4. Edit `hadolint-py` to `hadolint-py!=2.15.1.2` by hand — `ensure-deps` is additive and will not
   rewrite an entry already present.
5. `inv configs.ensure-deps` for the two missing entries, `inv deps.lock`, then
   `inv deps.check-currency` and `inv deps.lock --package <name>` for each entry it names
   (`invoke-stubs` among them; see "What v0.5.0 adds"), then sync. Run `inv configs.check-include`
   and settle `skills/` per the open question there.

   [PITFALL: before 2026-09-26, `configs.ensure-deps` corrupted a consumer whose dev group opens
   with an extras entry (`"pkg[extra]"`), because its array regex stopped at the first `]`. This
   repo was never exposed: measured, all twelve of its dev entries parse out cleanly. The tell that
   the installed tool predates the fix is `configs.diff` and `ensure-deps` disagreeing in one run,
   the diff naming two missing entries while `ensure-deps` prints `added` for all fourteen.]

6. The gate, whole.
7. **`inv repo-tasks.stamp`, last, after the gate passes**, then push and read CI. Added 2026-09-26,
   when `repo-tasks` settled its release question as **pinning** and its
   `contributing/consumer-sweep.md` gained this step. It pins the version active in the process
   running it, so running it after the gate records what this repo was actually verified against
   rather than the newest tag. It needs the network, for the tag list. The old reason for being
   unpinned, "until a tag exists", has been false since `v0.2.0` (2026-09-04) and `v0.3.0`
   (2026-09-08), and nothing prompts a re-stamp here.

[PITFALL: `requires-python` must exist before pulling `ruff.toml`, because the shipped copy no
longer carries `target-version` and the linter reads the floor from that field instead. It does
exist here (`>=3.11`), so this is a check that passes rather than a blocker.]

## What no diff can tell you, and has to be read

- ~~**Report-mode wiring.**~~ **Does not apply — checked 2026-09-13.** `tasks.py` is
  `from repo_tasks import ns` with no root `Collection` of its own, and `repo_tasks/__init__.py`
  already calls `runner.configure(ns)` on that object. Recorded rather than left as a check, because
  this is the item where "the consumer looks fine" is not evidence: an unwired consumer's output is
  byte-identical to a wired one with the variable unset.
- **The security workflow caller.** This repo has none — `ci.yml` and `tests-windows.yml` only. It
  is an addition rather than a `configs.pull`: about six lines, a `.github/workflows/security.yml`
  whose one meaningful line is a job-level `uses:` naming `repo-tasks`' `security-reusable.yml` at a
  full 40-character SHA, with the readable version in a trailing comment. **Since 2026-09-26
  `inv consumers.diff` reports it**, as a missing caller or one whose SHA is behind. It is now a
  two-repo item rather than a family-wide one. `scaffoldapy` and `ingesta` both carry current
  callers pinned `d17c607`, and `ingesta`'s was copied from `scaffoldapy`'s template. What is left
  is this repo and `power-user-linux-setup`, which the template cannot reach. `d17c607` is right
  only because `security-reusable.yml` has never been edited since, so copying either existing
  caller verbatim is correct today, and the reporter is what notices when that stops being true.

  [NEEDS CLARIFICATION: this repo has a Windows job (`tests-windows.yml`). Does the reusable
  security workflow need anything said about it, or is it Linux-only by construction? Every existing
  caller is in a Linux-only repo, so this is the first place the question arises.]
- **The packaged-`tests/` decision.** `configs.pull` writes both halves of the config but cannot
  decide whether this repo wants `__init__.py` files under `tests/`. Stays deliberate.
- **`venv.check` / `venv.recreate`.** Expect a mismatch on first run — 3.14.5 against a 3.11 floor,
  which is uv doing what it always does. Pre-existing state made visible, not something the sweep
  broke. Here it is entangled with item 3 rather than independent of it.

## What this predicts

Both halves of `configs.diff` fire, and **CI stays green through the config pull** — none of the
drifted items is a binary a gate step shells out to, which is the property that made the original
2026-08-24 incidents (`actionlint`, exit 127) expensive and that none of these shares.
`pytest-socket` and `pytest-timeout` are inert until a conftest or a marker invokes them.

The exception is the **local** gate, which goes red on the type check the moment `pythonVersion`
lands, until item 3 is done. That is the sweep working.

This repo has a **Windows job** (`tests-windows.yml`), which none of the other consumers has — worth
watching on the first green run after the pull, since the shipped `pytest.ini`'s `filterwarnings`
entries have only ever been exercised on Linux here.

This was deferred to be done in one session with the `setup-uv` bump, so that one green run would
cover every CI change here. That bump landed alone on 2026-09-28 (`8292395`, `setup-uv@v10.2.0` in
both workflows, its plan now retired), so this sweep and the security caller get their own green
run; the pairing no longer holds anything back.

[DEFERRED: record which way each prediction went, in this file, when the sweep runs. A prediction
nobody scored is a guess.]
