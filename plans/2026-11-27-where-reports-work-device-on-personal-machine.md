---
status: landed
updated: 2026-11-27
source_repo: personal/nexus
source_session: 34294f1e-3eff-4138-9e6f-91db7335af4d.jsonl
source_moment: 2026-11-27
source_plan:
---

# plan-conveyor `where` reports "device: work" on a personal machine

## Context

Two sessions independently noticed it: `plans.py where` prints "device: work — one organisation" on
this personal Windows machine whenever there is a single store. One session described it as a
one-line fix in `skills/plan-conveyor/scripts/plans.py`.

Also still open from the plan-conveyor work (see
`plans/2026-11-25-plan-conveyor-ownership-and-activity-classification.md`):
`plans.py links rename --yes` on `~/plans` (8 store folders still named after the Linux machine's
directories), deferred until the Linux machine is onboarded, then `sync`.

## Evidence

Cross-session wrap-up messages received in the nexus session above on 2026-11-27, from nexus-38
("plan-conveyor's `where` prints 'device: work — one organisation' on this personal machine whenever
there is a single store") and nexus-22 ("Plan-conveyor's config reports `device: work`. That looks
wrong for this personal machine").

## Open questions

- Is the label derived from the store count alone, or from the `[activity]` classification? The fix
  depends on which.

## Recommended direction

Reproduce with `plans.py where` from a personal repo on a single-store machine, derive the device
label from the activity classification instead of the store count, and add a test for the
single-store personal case.

## Migrated to

- **The fix**: `3106b68`. The open question resolves to "neither": `where` printed `work` for every
  machine that is not a `contractor`, so the label came from the store split, while `cfg.device`
  already held `personal`, derived from the activities. `where` now prints `cfg.device`. The same
  commit found and fixed a worse sibling: `join` raised a KeyError on a personal device, since
  `DEVICE_JOIN_NOTES` had no `personal` entry, and the Windows machine still to join is personal.
  `test_a_personal_device_names_itself_and_joins_any_confirmed_remote` in
  `tests/unit/test_plan_sync.py` covers both.
- **The `links rename --yes` aside**: done on 2026-11-26 by store commits `a838fe6` through
  `a53dfc8`; the store holds only `_unscoped/` and `github.com/` folders and is level with its
  remote. Recorded in `plans/2026-11-25-plan-conveyor-ownership-and-activity-classification.md`.
- Not migrated: the two cross-session messages that reported it, which say nothing the fix's commit
  body does not.
