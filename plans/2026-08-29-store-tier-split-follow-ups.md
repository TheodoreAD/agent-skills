---
status: in-progress
updated: 2026-08-30
---

# Follow-ups left by the store tier split

## Context

The session of 2026-08-29 split the plans store into a shareable tier (`~/plans`, pushed to the
private `TheodoreAD/plans`) and a sensitive tier (`~/plans-sensitive`, local-only, currently empty).
It left work undone, and this file is what carries it — `plans.py list` surfaces it, because
`in-progress` sorts above everything else. **Only work this repo can do itself** — anything owed to
another repo is filed there and travels via the store, per the section at the end.

**Each item is a check to run before acting, not a fact to trust.** This machine runs parallel
sessions and state moves underneath you: `plans/2026-08-29-next-session-prompt.md` measured five
assertions going stale inside one hour, one of which caused duplicated work. If a check no longer
holds, strike the item.

Nothing here is durable reasoning. When the items are done this file is retired outright, with no
`## Migrated to` section to write — that is the difference between a working list and a plan, and
the reason it is one file rather than several.

## Design

### 1. Merge three plan clusters `absorb` will never mention again

Absorption reported these as consolidate-with pairs exactly once. The pairing lives only in prose,
so nothing re-surfaces it.

- Check: `ls plans/ | grep -E 'session-harvest|trigger|prompt|description-cap'` — expect 8 files
  while none are merged. The `description-cap` alternative is not decoration: without it the check
  returns 7 and silently omits one member of the skill-triggers cluster, which is how a merge ends
  up two-thirds done. Found by running it, 2026-08-29.
- Act: merge each cluster into one plan, keep the earliest filename, delete the others.
  - session-harvest: `2026-08-29-session-harvest-step-0-misreads-uncommitted-work.md` +
    `2026-08-29-session-harvest-plans-store-sweep.md` +
    `2026-08-29-session-harvest-stale-install-third-case.md`
  - skill triggers: `2026-08-22-skill-trigger-quality-review.md` +
    `2026-08-29-skill-description-cap-gate-blind-to-wrapped-yaml.md` +
    `2026-08-29-trigger-contention-scanner.md`
  - prompts: `2026-08-29-next-session-prompt.md` +
    `2026-08-29-retirement-prompt-on-the-session-sweep.md` — these two are explicitly meant to be
    decided together rather than bolted onto `absorb` independently

### 2. Retire `2026-08-28-plans-outside-the-repo.md`, or record why not

- Check: `plans.py tags --file 2026-08-28-plans-outside-the-repo.md --tag DEFERRED`
- Act: it is `landed` with DEFERRED tags blocking deletion. Move each into an open plan first, then
  retire.

**Use `set-status`, never a frontmatter edit.** A hand-edit skips the gate silently; that happened
on 2026-08-29 and is written up as a `[PITFALL:]` in
`plans/2026-08-29-retirement-prompt-on-the-session-sweep.md`.

### 3. Absorb what other sessions have filed for this repo — done as the first call, every session

Not a one-off item: `plans.py absorb` is the first call of any session here, and the store fills up
between sessions. Five plans were waiting on 2026-08-30, four of them about `session-harvest` and
`plan-docs`, each pairing with a plan already in `plans/` — so absorbing grows the clusters in item
1 rather than being separate from it.

- Check: `plans.py absorb`
- Act: `--apply`, commit here and in the store, then fold the new arrivals into item 1's clusters
  before merging.

## Done, kept only so nobody re-adds them

- **The store push.** `~/plans` had four unpushed commits, three from parallel sessions. Resolved
  2026-08-30 — a parallel session pushed, and `origin/master` now contains everything. Nothing here
  is owed to the store any more; the ordinary "commit, then push" rule in `plan-docs` covers it from
  now on.

## Filed elsewhere — not this repo's work, and deliberately not listed here

Four plans were filed for other repos while this list was being written: three for
`power-user-linux-setup` and one for `ingesta`. **What they ask for is not repeated here**, and
should not be added back.

Confirmed working 2026-08-30, which is why the rule is worth keeping: without any prompting from
here, an `ingesta` session absorbed both of its plans, and a `power-user-linux-setup` session
absorbed the ssh one and merged it into the plan it paired with. The store plus `absorb` delivered
all three; a copy in this file would only have been a second thing to retire.

They are already routed: each sits in the store, and `plans.py absorb` hands it to the session that
next works in that repo, which `plan-docs` makes the first call of every session. A copy here would
be a second thing to retire, would go stale on its own, and aims a reminder at the one repo that
cannot act on it. Nothing in this file is blocked on any of them.

## Verification

Done when `plans.py list` shows the three clusters as single files, and the `landed` plan is either
retired or carries a recorded reason not to be. Then delete this file.
