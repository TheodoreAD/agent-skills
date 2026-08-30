---
status: idea
updated: 2026-08-30
---

## Context

The `repo:` frontmatter key is defined in `SKILL.md` as belonging to store-held plans only —
"store-held plans only — location no longer names the repo". It exists because a plan sitting in the
store mirror has no directory that names its origin, so the key supplies what the path stopped
saying.

The key is added on the way out and never removed on the way back:

- `plans.py:2048` — `move --to store` inserts `repo: <origin URL>` when the frontmatter lacks it.
- `move --to repo` has no matching branch, and `absorb`'s `_take_plans` (`plans.py:2013`) is a plain
  file move with no frontmatter handling at all.

Measured 2026-08-30 in this repo: **10 of 22** plans in the committed `plans/` directory carry a
`repo:` line, every one of them a plan absorbed out of the store. The path now names the repo, so
each line is a second, redundant answer to a question the location already answers — which is the
exact condition the skill uses to argue _against_ marking in-transit plans ("route plus location
already says it, so there is nothing to set and nothing to drift").

Nothing reads the key, so this is drift rather than breakage. It matters because the skill teaches
the key as a location signal: a reader who trusts that reads ten repo-held plans as store-held.

[PITFALL: the asymmetry is invisible from either command on its own. `move --to store` is correct
and `absorb` is correct as a file move; the defect only exists in the round trip, which no single
call performs. It surfaced from counting the corpus, not from using either command.]

## Open questions

[NEEDS CLARIFICATION: strip on absorption, or stop treating the key as location-derived? Stripping
keeps the key's stated meaning exact and is a few lines in `_take_plans` plus `move --to repo`.
Keeping it — and redefining it as durable provenance, "this plan was once filed through the store" —
costs nothing and might even be useful to `archive`. Only the first matches what `SKILL.md`
currently says, so the second is a documentation change as much as a code one.]

[NEEDS CLARIFICATION: what happens to the ten files already carrying it. A one-off sweep is trivial
if the answer is "strip", but it rewrites ten plans' frontmatter in one commit, which is exactly the
hand-editing that `2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` argues nothing
should do outside `set-status`. A `plans.py` subcommand that does it, or an extension of `doctor`
that reports it, keeps the edit inside the tool.]

[NEEDS CLARIFICATION: should `doctor` report this at all? It already has a problems list, and "a
repo-held plan carrying a store-only key" is the same shape as the status drift it already reports.
That may be the whole fix — the corpus is small, the cost is cosmetic, and a reported problem is
cheaper than a migration.]

## Recommended direction

Rough. Strip in `_take_plans` and in `move --to repo`, so the key's meaning stays exactly what
`SKILL.md` claims, and add the mismatch to `doctor`'s problems list so the existing ten are visible
without a migration commit. Test it in `tests/unit/test_plan_store.py` against the `ws` fixture as a
round trip — repo → store → repo — since that is the path no single command exercises and the reason
the gap survived.
