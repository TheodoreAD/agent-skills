---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest-plans-store-sweep`'s gap 2 argues from a premise that is no longer true

Consolidate with `plans/2026-08-29-session-harvest-plans-store-sweep.md`, which was absorbed into
this repo at `c5c7e46` carrying the stale text. This is a correction to that file, written from a
`repo-tasks` session, which does not edit another repo's tree.

## The stale claim

That plan's gap 2 reads, at `2026-08-29-session-harvest-plans-store-sweep.md:32`:

> The store is created by `plan-docs install` as a local git repository **with no remote** —
> confirmed on this machine, `git -C ~/plans remote -v` is empty. So a dirty store has nothing to
> push, the ahead-count is zero, and the bullet reads clean while an uncommitted plan sits there.

Checked 2026-08-29, after the two-tier split landed: `~/plans` has `origin`, pointing at a private
repo on the personal account. It is empty — nothing has ever been pushed, and the branch is `master`
with no upstream — but the remote exists. Only the sensitive tier is remote-less, and that is now by
design rather than by default: `plans.py doctor` reports a remote _there_ as a problem.

The claim was true when it was written and verified live at the time. It went stale within hours.

## Why the gap survives the correction

This is the part that matters, and the reason this is a correction rather than a retraction: **the
remote was never what made gap 2 a gap.** An _uncommitted_ plan is not a commit, so no ahead-count
sees it on any repository, with or without a remote. `git log origin/<branch>..HEAD` is the wrong
instrument for a dirty working tree everywhere, not just here. The store is also not a repo the
session "touched" in the sense that bullet means — it sits outside every working tree and nothing
walks to it.

So gap 2 stands exactly as filed. Only its justification has to change.

[PITFALL: a plan's reasoning can rot faster than its conclusion. This one was verified live, cited a
command and its output, and was wrong a few hours later because a different piece of work landed.
The conclusion never depended on it. Worth stating as its own lesson: when a plan's argument rests
on a machine-state fact, the plan should say which part of the conclusion would fall if that fact
changed — here, none of it.]

## The edits this implies

1. **Gap 2** — replace the no-remote reasoning with the uncommitted-work reasoning above, and keep a
   note that the premise was corrected, since the original phrasing is the natural one to write
   again.
2. **Recommendation 2**, currently "State the no-remote fact explicitly wherever the bullet lands.
   It is the whole reason the ahead-count check does not apply" — this would now ship a false
   sentence into the skill. It should instead say why the git bullet does not cover the store: the
   check is for uncommitted work in a directory no repo walk reaches. Per tier: the shareable tier
   has a remote, so committed-but-unpushed plans there are a genuine _second_ failure the sweep
   could catch, gated by the content scan before any push; the sensitive tier has nothing to push.
3. **The `doctor` open question** lists "a store that has grown a remote" among what `doctor`
   reports. That is now specifically a remote on the _sensitive_ tier, plus a mirrored root filed in
   the wrong tier.
4. The closing line "Nothing was actually dangling when this was found: `~/plans` was clean at
   `11b27e4`" is still true, and was still true when this correction was made.

## Noticed alongside, not part of this

A session's _loaded_ copy of a skill can be older than the file on disk, and the usual staleness
check cannot see it. Confirmed 2026-08-29 in the session that filed this plan: `plan-docs` was
loaded into context before `bd6c55d` landed at 19:58, so the session held the pre-correction wording
("the push gate is `scan --mode tree`") and reported the installed skill as behind its source.
`diff -rq` between `~/.agents/skills/plan-docs/` and the checkout showed them identical apart from
`__pycache__` — the install was current the whole time, and only the context was stale.

This matters beyond one wrong report: the pre-push gate for the shareable store is
`scan --mode history` before the first push, not `--mode tree`, and a session reasoning from a
loaded copy would run the wrong one and get a clean answer from it.

The generalisation belongs to `session-harvest`, whose step 0 diffs the installed copy against the
checkout and would have passed here: see
`2026-08-29-session-harvest-step-0-cannot-see-a-stale-loaded-copy.md`.
