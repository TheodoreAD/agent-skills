---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest`'s loose-state sweep never looks at the plans store

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
2. **The git bullet cannot reach it.** "Git state, every repo the session touched" is built entirely
   around `git log origin/<branch>..HEAD`, a fetch, and who authored the unpushed commits. The store
   is created by `plan-docs install` as a local git repository **with no remote** — confirmed on
   this machine, `git -C ~/plans remote -v` is empty. So a dirty store has nothing to push, the
   ahead-count is zero, and the bullet reads clean while an uncommitted plan sits there.
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

Nothing was actually dangling when this was found: `~/plans` was clean at `11b27e4`.

[PITFALL: the reason this survived a skill whose whole subject is unswept state is that the store
looks like it is already covered twice over — it is a git repository (so the git bullet seems to own
it) and it is a shared store outside any repo (so that bullet seems to own it). Each bullet's
framing hands it to the other. A check written for either one alone would still miss it.]

## Open questions

[NEEDS CLARIFICATION: one bullet or two? The store needs `git -C $PLANS_HOME status --porcelain`
(uncommitted plans) and `plans.py absorb` (plans filed _for_ the current repo that nobody took).
They are different failures with different owners — the first is this session's mess, the second is
another session's gift — but they are one command each against the same directory, and splitting
them across two bullets risks one being read as covering both, which is how gap 3 happened.]

[NEEDS CLARIFICATION: should the sweep run `plans.py doctor`? It reports a store that lost its git
identity, a store that has grown a remote, an unset `PLANS_HOME`, and repos holding plans no rule
routes — all of which are silent, machine-level breakage rather than session state. That argues it
belongs in a periodic check rather than in every harvest. Against: it is one call, and the failures
it names make `archive` silently retrieve nothing, which is the kind of thing discovered far too
late.]

[NEEDS CLARIFICATION: does the `$RESEARCH_HOME` bullet's justification need rewriting, or just
widening? "Invisible to every other check here precisely because the store is not version-
controlled" is a true statement about `$RESEARCH_HOME` and a false one about `$PLANS_HOME`. Making
it a two-item bullet with one shared rationale would reintroduce the same wrong reasoning; the
honest fix may be to keep them separate and say why each is invisible for a _different_ reason.]

[NEEDS CLARIFICATION: is `absorb`-on-first-call already enough? `plan-docs` tells every session to
run `absorb` as its first plan-docs call, so a session that follows that rule has already drained
what was filed for it. The harvest bullet would then only catch sessions that never invoked
`plan-docs` at all — which is most of them, since the rule fires on the skill being loaded and a
session that never planned anything never loads it. Worth stating that reasoning in the bullet, so
it is not later deleted as redundant with `plan-docs`.]

## Recommended direction

Rough, and the questions above come first.

1. **Add the store to the loose-state sweep**, as its own bullet rather than folded into either
   existing one — the pitfall above is that both existing bullets appear to cover it.
2. **State the no-remote fact explicitly** wherever the bullet lands. It is the whole reason the
   ahead-count check does not apply, and without it the next reader deletes the bullet as
   duplicating the git one.
3. **Fix the `$RESEARCH_HOME` justification** either way, since it is currently a sentence that
   would mislead anyone reasoning from it about any other store.
4. **Verify by running it, not by reading it** — the same rule that bullet list already applies to
   itself. Dirty the store deliberately with an uncommitted file, run a harvest, and confirm it is
   reported; then clean up. A bullet that describes a check nobody has executed is how gap 2 got
   written in the first place.

[DEFERRED: this plan covers `session-harvest` only. Whether any _other_ skill's checks quietly
assume "a store outside a repo is not version-controlled" was not surveyed — `session-bash-audit`
and `research-library` both touch shared locations and were not read.]
