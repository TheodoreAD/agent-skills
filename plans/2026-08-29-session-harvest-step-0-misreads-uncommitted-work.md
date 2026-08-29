---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` step 0 reads another session's uncommitted work as a stale install

**Overlaps `2026-08-29-session-harvest-stale-install-third-case.md`, which reached the same
conclusion four minutes earlier from a parallel session** and states the three-cause fix more
crisply — consolidate into that one and keep only what is listed as additive below. This file was
written without re-checking `absorb`, which had been clean for this repo ten minutes before and was
not re-run; that miss is itself worth a line in the skill.

Additive over that plan: the step 6 reconciliation question below, and the `[DEFERRED:]` warning
that the two-tier store split undercuts the companion plan's no-remote argument. Everything else
here is duplicated.

Companion to `2026-08-29-session-harvest-plans-store-sweep.md`, filed the same day from the same
`repo-tasks` session. **Separate file rather than an edit to that one because the store was dirty**
— a parallel session had a modified `README.md` and an untracked plan of its own in flight — which
is the fallback `plan-docs` prescribes and, incidentally, a live demonstration of the hazard the
companion plan is about. Consolidate the two on absorption.

## Context

Step 0 says to diff the installed skill copy against the checkout before starting, and:

> If they differ, say so and offer to re-install first; a stale harvest is worse than no harvest,
> because its report reads identical.

Run on 2026-08-29, that check fired. `session-harvest/SKILL.md` and `plan-docs/SKILL.md` matched;
`plan-docs/scripts/plans.py` **differed**. Following the instruction literally, the next move is to
offer a re-install.

That would have been wrong, in a way the step cannot currently distinguish:

- The difference was **uncommitted work in the checkout** — a parallel session mid-restructure, four
  modified files, mtimes in the same minute as the check. Not a stale install.
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
`git -C <checkout> status --short` plus the file's mtime. In this run the mtime and the wall clock
agreed to the minute, which is what made "another session is editing this right now" obvious rather
than inferred. `git log` would not have shown it — the work is uncommitted, so the history looks
settled.]

## Open questions

[NEEDS CLARIFICATION: should step 0 do the disambiguation itself, or just stop and report? Doing it
means two more calls per skill checked (`status --short`, an mtime), on a step that runs before the
harvest has established anything. Reporting means the step ends with "these differ, and here is what
I did not conclude", which is honest but hands the user a decision at the least informed moment of
the run.]

[NEEDS CLARIFICATION: does an uncommitted-checkout finding block the run, or only the self-update?
The harvest itself was unaffected here — the installed `plans.py` behaved consistently all session,
and every command it ran was against the committed version. What it blocked was step 6/7: the skill
edit could not be made in a checkout another session is editing. That suggests the finding belongs
to the self-update mechanics rather than to step 0's go/no-go, and that step 0 should say so.]

[NEEDS CLARIFICATION: what should step 6 do when the checkout is unavailable? This run answered it
by filing the finding as a store plan for `agent-skills`, which is the routing filter the skill
already has for a candidate belonging to another repo. But step 6 says "default to editing the
source now, not filing it for later; a deferred skill fix is a skill fix that does not happen" —
which reads as an instruction to override exactly the routing that was correct here. The two need
reconciling, and the honest reconciliation is probably that "file it" and "defer it" are different
things: a filed plan has a mechanism that surfaces it (`absorb`), and that is what makes it not a
deferral.]

## Recommended direction

1. **Split step 0's remedy by cause**, using the table above. The diff stays the trigger; the
   response depends on `status --short`, not on the diff.
2. **Say plainly that a re-install cannot fix a checkout-ahead difference**, since that is the
   non-obvious half — the installer's source is the remote, not the working tree, so the natural
   mental model ("re-install syncs them") is wrong in both of the last two rows.
3. **Reconcile step 6's "edit now, do not file" with the cross-repo filing filter**, so a run that
   cannot touch the checkout has an unambiguous path rather than two rules pointing opposite ways.

[DEFERRED: the same run found `plan-docs` mid-restructure toward a two-tier store (`$PLANS_HOME`
shareable, which **may have a remote**, plus a local-only sensitive tier). The companion plan's gap
2 argues the harvest's ahead-count check cannot reach the store _because it has no remote_ — which
stays true for the sensitive tier and stops being true for the shareable one. Whoever absorbs these
two should re-check that argument against whatever the split actually lands as, rather than carrying
it across.]
