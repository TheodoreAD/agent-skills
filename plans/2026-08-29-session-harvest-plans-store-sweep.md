---
status: idea
updated: 2026-08-30
---

# `session-harvest`'s loose-state sweep never looks at the plans store

Merged 2026-08-30 with `2026-08-29-plans-store-sweep-no-remote-premise-is-stale.md`, a correction
filed from a parallel session hours after this was written and now **merged away and deleted**
(`plans.py archive --show` reads it back). Its edits are applied below; gap 2's conclusion is
unchanged and its justification is rewritten.

Merged again 2026-08-30 with `2026-08-30-absorb-on-first-call-misses-mid-session-filings.md`,
likewise **merged away and deleted** and readable with the same command. It answered the last open
question below with a measurement, and that answer is now recorded there rather than in a second
file.

## Context

Asked directly in a `repo-tasks` session, 2026-08-29: do `plan-docs` and `session-harvest`, as
installed on this machine, know about the central plans store? Checked across every file of both
skills (`SKILL.md` and `references/`), at `~/.agents/skills/` — `~/.claude/skills` is a symlink to
it, so there is one copy, not two.

**`plan-docs`: yes, thoroughly.** It is the skill that defines the store — `$PLANS_HOME` (default
`~/plans`), the path-mirroring scheme, per-repo routing config,
`install`/`doctor`/`absorb`/`move
--to store`, `_unscoped/`, and the dirty-store protocol. Nothing
to do there.

**`session-harvest`: it knows the store exists, but its sweep cannot see it.** The routing half is
fine: it reaches for `plans.py new --for <repo>`, describes the store mirror, and says "Commit the
filed plan in the store immediately — a dirty store…". So the skill already knows the hazard by
name. What is missing is any check that would ever _find_ one.

Four specific gaps, each verified against the installed files rather than inferred:

1. **`$PLANS_HOME` is never named.** Zero hits across `SKILL.md` and `references/rationale.md`.
   Still zero on 2026-08-30.
2. **The git bullet cannot reach it.** "Git state, every repo the session touched" is built entirely
   around `git log origin/<branch>..HEAD`, a fetch, and who authored the unpushed commits. An
   **uncommitted** plan is not a commit, so no ahead-count sees it on any repository, with or
   without a remote — `git log origin/<branch>..HEAD` is the wrong instrument for a dirty working
   tree everywhere, not just here. And the store is not a repo the session "touched" in the sense
   that bullet means: it sits outside every working tree and nothing walks to it. So a dirty store
   reads clean while an uncommitted plan sits there.
3. **The "shared stores outside any repo" bullet excludes it by its own reasoning.** It names only
   `$RESEARCH_HOME`, and justifies the check with "invisible to every other check here precisely
   because the store is not version-controlled" — which is exactly false for `$PLANS_HOME`. A reader
   applying that sentence concludes the plans store is already covered by the git bullet, which gap
   2 shows it is not.
4. **`absorb` and `doctor` are absent from the sweep.** `plans.py absorb` appears once in the whole
   file, in the _routing_ section; `plans.py doctor` appears nowhere. `plan-docs` states `absorb` is
   silent when the store holds nothing for the repo, which is precisely the property that makes it
   cheap enough to run on every harvest.

The shape is the one `session-harvest` exists for: state a session leaves behind that no other check
finds. A session that files a plan for another repo and does not commit it in the store leaves
nothing in any working tree, nothing in any ahead-count, and nothing in CI. And per `plan-docs`, the
cost is not hypothetical — every minute the store is dirty is a minute another session must fall
back to adding a file it would rather have edited.

Nothing was actually dangling when this was found: `~/plans` was clean at `11b27e4`. Still true when
the correction below was written.

[PITFALL: the reason this survived a skill whose whole subject is unswept state is that the store
looks like it is already covered twice over — it is a git repository (so the git bullet seems to own
it) and it is a shared store outside any repo (so that bullet seems to own it). Each bullet's
framing hands it to the other. A check written for either one alone would still miss it.]

## The premise that rotted, and the conclusion that did not

Gap 2 originally read: the store "is created by `plan-docs install` as a local git repository **with
no remote** — confirmed on this machine, `git -C ~/plans remote -v` is empty. So a dirty store has
nothing to push, the ahead-count is zero".

Checked hours later, after the two-tier split landed: `~/plans` has an `origin` pointing at a
private repo on the personal account. Only the sensitive tier is remote-less, and that is now by
design rather than by default — `plans.py doctor` reports a remote _there_ as a problem.

**The remote was never what made gap 2 a gap**, which is why this is a correction rather than a
retraction: the conclusion stands on uncommitted work, which no ahead-count sees anywhere. Gap 2 is
rewritten above; the old phrasing is the natural one to write again, so it is recorded here rather
than deleted.

Two consequences beyond the wording. The shareable tier having a remote makes committed-but-unpushed
plans a genuine _second_ failure the sweep could catch — gated by the content scan before any push —
while the sensitive tier has nothing to push. And the `doctor` question below now means specifically
a remote on the _sensitive_ tier, plus a mirrored root filed in the wrong tier.

[PITFALL: a plan's reasoning can rot faster than its conclusion. This one was verified live, cited a
command and its output, and was wrong a few hours later because a different piece of work landed.
When a plan's argument rests on a machine-state fact, it should say which part of the conclusion
would fall if that fact changed — here, none of it.]

## Open questions

[NEEDS CLARIFICATION: one bullet or two? The store needs `git -C $PLANS_HOME status --porcelain`
(uncommitted plans) and `plans.py absorb` (plans filed _for_ the current repo that nobody took).
They are different failures with different owners — the first is this session's mess, the second is
another session's gift — but they are one command each against the same directory, and splitting
them across two bullets risks one being read as covering both, which is how gap 3 happened.]

[NEEDS CLARIFICATION: should the sweep run `plans.py doctor`? It reports a store that lost its git
identity, a remote on the sensitive tier, an unset `PLANS_HOME`, a mirrored root in the wrong tier,
and repos holding plans no rule routes — all of which are silent, machine-level breakage rather than
session state. That argues it belongs in a periodic check rather than in every harvest. Against: it
is one call, and the failures it names make `archive` silently retrieve nothing, which is the kind
of thing discovered far too late.]

[NEEDS CLARIFICATION: does the `$RESEARCH_HOME` bullet's justification need rewriting, or just
widening? "Invisible to every other check here precisely because the store is not version-
controlled" is a true statement about `$RESEARCH_HOME` and a false one about `$PLANS_HOME`. Making
it a two-item bullet with one shared rationale would reintroduce the same wrong reasoning; the
honest fix may be to keep them separate and say why each is invisible for a _different_ reason.]

[DECISION: **`absorb`-on-first-call is not enough, measured rather than argued.** The concern was
that the harvest bullet would be redundant with `plan-docs`' own first-call rule. It is not: the
queue is not drained once, it refills for as long as the session runs, because the sessions filing
into it are running concurrently. Measured 2026-08-30 in a long `power-user-linux-setup` session
that followed the rule correctly — 4 plans at session start, 4 more about two hours in, and 1 more
at the five-hour mark. Redundancy was never the risk; a rule that fires only at the beginning covers
the state of the world at the beginning.]

[PITFALL: the five-hour one is what makes this a bullet rather than a nicety. It reported a
credential exposure — an API id and hash written into another session's transcript and a
`~/.claude/file-history` snapshot, with a cleanup only the user can run — and it sat in the store
for half an hour while the session that needed it was still working. It surfaced only because the
harvest happened to be investigating why the store had uncommitted changes, not because any step
asked. That is step 6's second signal for a mis-aimed procedure: the run's best finding came from
something no step required. Confirmed again the same day from the other side — those uncommitted
changes were a parallel session's absorption in progress.]

[NEEDS CLARIFICATION: should the sweep _absorb_ what it finds, or only report it? Absorbing is a
repo write plus two commits at the very end of a session, which is a lot of state change for a step
whose job is to report; reporting alone risks the finding dying with the terminal, which is the
failure the "file first, report second" rule exists to prevent. The run above absorbed, because the
content was a credential exposure and leaving it unread was the worse option — a judgement about
severity, not a general answer.]

[NEEDS CLARIFICATION: should a dirty store change that answer? On the run above the store held nine
uncommitted deletions from a parallel session mid-absorb, so committing safely needed a pathspec
commit rather than a plain `git add` — already a `~/AGENTS.md` rule, so the skill need not restate
it. But the harvest should probably _report_ a mid-transaction store rather than quietly working
around one, since it means another session is actively holding that directory.]

## Recommended direction

Rough, and the questions above come first.

1. **Add the store to the loose-state sweep**, as its own bullet rather than folded into either
   existing one — the pitfall above is that both existing bullets appear to cover it.
2. **State why the git bullet does not cover it**: the check is for uncommitted work in a directory
   no repo walk reaches. Per tier — the shareable tier has a remote, so committed-but-unpushed plans
   there are a second thing the sweep could catch, gated by the content scan before any push; the
   sensitive tier has nothing to push. Do **not** write "the store has no remote"; that sentence was
   true for a few hours and would now ship false into the skill.
3. **Fix the `$RESEARCH_HOME` justification** either way, since it is currently a sentence that
   would mislead anyone reasoning from it about any other store.
4. **Verify by running it, not by reading it** — the same rule that bullet list already applies to
   itself. Dirty the store deliberately with an uncommitted file, run a harvest, and confirm it is
   reported; then clean up. A bullet that describes a check nobody has executed is how gap 2 got
   written in the first place.

Land it in the same pass as `plans/2026-08-30-session-harvest-filed-plan-may-be-absorbed.md`, which
adds the store's other half to the same skill — a line in the report format rather than a bullet in
this sweep, because a plan this session filed may have been absorbed and pushed by another before
the report names it.

[DEFERRED: this plan covers `session-harvest` only. Whether any _other_ skill's checks quietly
assume "a store outside a repo is not version-controlled" was not surveyed — `session-bash-audit`
and `research-library` both touch shared locations and were not read.]
