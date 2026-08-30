---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` step 0: a difference has three causes, and a clean diff has a fourth

Merged 2026-08-30 from three plans that were the same finding reached from three sessions:
`2026-08-29-session-harvest-stale-install-third-case.md` (filed minutes earlier from a parallel
session), this file, and `2026-08-29-session-harvest-step-0-cannot-see-a-stale-loaded-copy.md`. Each
of the first two nominated the other as the survivor; this filename won because it names the step's
subject rather than one case of it. The collision is itself evidence for the finding — two sessions
hit the same gap within hours, and neither could see the other's work until one wrote to the store.

## Context

Step 0 says to diff the installed skill copy against the checkout before starting, and:

> If they differ, say so and offer to re-install first; a stale harvest is worse than no harvest,
> because its report reads identical.

Run on 2026-08-29, that check fired twice, in two sessions, for the same reason.
`session-harvest/SKILL.md` and `plan-docs/SKILL.md` matched; `plan-docs/scripts/plans.py`
**differed**. In the second run the checkout carried 672 uncommitted insertions across
`skills/plan-docs/`, `tests/unit/test_plan_store.py` and `README.md` — a parallel session
mid-implementation of the two-tier store split, nothing ahead of `origin/main`, mtimes in the same
minute as the check.

Following the instruction literally, the next move is to offer a re-install. That would have been
wrong, in a way the step cannot currently distinguish:

- The difference was **uncommitted work in the checkout**, not a stale install.
- **Re-installing would have changed nothing**, because the installer clones the remote. The remote
  has the committed version, which is exactly what was already installed. The offer is not merely
  unhelpful, it is a no-op dressed as a remedy.
- Worse, accepting the offer while another session is editing those files reframes a live
  restructure as an install-hygiene problem, and invites exactly the cross-repo interference
  `~/AGENTS.md` and `plan-docs` both forbid.

The step's premise — installed copy older than source — is one of at least three ways the two can
differ, and it is not the one that occurred:

| difference                             | correct response                                 |
| -------------------------------------- | ------------------------------------------------ |
| installed behind the remote            | re-install (the step's assumption)               |
| checkout ahead by **committed** work   | push, then re-install                            |
| checkout ahead by **uncommitted** work | leave it alone; it is someone's work in progress |

[PITFALL: the diff alone cannot tell these apart, and the cheap disambiguator is not the diff but
`git -C <checkout> status --short` plus the file's mtime. In the second run the mtime and the wall
clock agreed to the minute, which is what made "another session is editing this right now" obvious
rather than inferred. `git log` would not have shown it — the work is uncommitted, so the history
looks settled.]

Neither run was actually harmed: the commands each needed (`tags`, `set-status`, `scan`) predated
the diff, which was one coherent feature. That confirmation is cheap when the diff is coherent and
would not be on one touching argument parsing broadly.

**The first run where re-installing was the right answer, 2026-08-30**, which matters because every
case recorded here until now argued against the step's own instruction and the table's first row had
no observation behind it. A harvest found both `session-harvest` and `plan-docs` differing; the
checkout was **clean and level with `origin/main`**, and the two commits accounting for the diff had
been pushed minutes earlier. Row one, exactly as written — the install was stale and a re-install is
what fixes it. So the disambiguator earns its place in both directions: the same non-empty diff
meant "leave it alone" on 2026-08-29 and "re-install" on 2026-08-30, and only `status --short` plus
the ahead-count separates them.

## The fourth outcome — landed, kept for the reasoning

A clean diff is not the whole answer: the installed copy can be current while the copy frozen in the
**session's context** at load time is old, which no filesystem comparison reaches. Confirmed
2026-08-29 — a session held `plan-docs` from before `bd6c55d`, which changed the store's pre-push
gate from `scan --mode tree` to `scan --mode history`, and filed the opposite claim into a plan. A
confidentiality gate, reasoned about from stale wording.

This half is **done**: `965af2e` added the check to step 0 — compare
`git -C <checkout> log -1 --format='%cI' -- skills/<name>/` against the session transcript's first
timestamp, as instants rather than strings, and re-read the installed `SKILL.md` from disk if the
skill moved after the session began. Only the three-cause split below is still open.

[NEEDS CLARIFICATION: should the same window check generalise past `SKILL.md` to the always-loaded
instructions file? `~/AGENTS.md` is loaded once per session and regenerated by a deploy task, so the
window exists and is longer. Not investigated.]

## Open questions

[NEEDS CLARIFICATION: should step 0 do the disambiguation itself, or just stop and report? Doing it
means two more calls per skill checked (`status --short`, an mtime), on a step that runs before the
harvest has established anything. Reporting means the step ends with "these differ, and here is what
I did not conclude", which is honest but hands the user a decision at the least informed moment of
the run.]

[NEEDS CLARIFICATION: does an uncommitted-checkout finding block the run, or only the self-update?
The harvest itself was unaffected in both runs — the installed `plans.py` behaved consistently, and
every command it ran was against the committed version. What it blocked was step 6/7: the skill edit
could not be made in a checkout another session is editing. That suggests the finding belongs to the
self-update mechanics rather than to step 0's go/no-go, and that step 0 should say so.]

[NEEDS CLARIFICATION: is "confirm the commands this run needs are not in the diff" worth spelling
out as a mechanical check, or does it stay a judgment call?]

## Recommended direction

1. **Split step 0's remedy by cause**, using the table above. The diff stays the trigger; the
   response depends on `status --short`, not on the diff. Roughly:

   > A difference has three causes, not one. Check `git -C <checkout> status --short` and
   > `git log origin/<branch>..HEAD` before offering anything: a **clean checkout ahead of the
   > install** is the stale install the step assumes, and a re-install fixes it. A **dirty
   > checkout** is unpushed work in progress — very likely a parallel session's — and a re-install
   > would fetch the last pushed version, which is what is already installed; report it as in-flight
   > rather than stale, confirm the commands this run needs are not in the diff, and use the
   > installed copy. Confirmed 2026-08-29 on `plan-docs`, mid-store-split.

2. **Say plainly that a re-install cannot fix a checkout-ahead difference**, since that is the
   non-obvious half — the installer's source is the remote, not the working tree, so the natural
   mental model ("re-install syncs them") is wrong in both of the last two rows.
3. **Reconcile step 6's "edit now, do not file" with the cross-repo filing filter.** Both merged
   sources reached this from opposite ends and it is no longer this plan's to settle: it is the
   subject of `plans/2026-08-29-plan-docs-cross-repo-work-is-a-filed-plan.md`, which argues filing
   is the default rather than the exception. Step 0 only needs to point at whatever that lands as.

The `[DEFERRED:]` this file carried — that the two-tier store split undercut the companion sweep
plan's no-remote argument — is **resolved**, and the re-check it asked for was done: see
`plans/2026-08-29-session-harvest-plans-store-sweep.md`, whose gap 2 now argues from uncommitted
work rather than from the absent remote.
