---
status: landed
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-03T11:05:00+03:00
---

# `session-harvest`'s write scope, stated positively

## Context

Stated by the user 2026-09-03, during a harvest, close to verbatim:

> we for sure shouldn't edit live skills or instructions now, since we rely on plan docs to capture
> all that. harvest should exclusively edit things in the repo where the session is happening and,
> via plan docs, to the plans in the current session's and the plans in the central store repo.

That is a **specification of the allowed write set**, and it is narrower than what `SKILL.md`
currently permits.

| harvest may write to               | via                                                |
| ---------------------------------- | -------------------------------------------------- |
| the repo the session is running in | ordinary edits and commits                         |
| that repo's `plans/`               | `plan-docs`                                        |
| the central plans store            | `plan-docs`, including plans filed for other repos |

Everything else is out — and the two the current text still allows are named below.

## What this changes in `SKILL.md`

**1. Step 6's carve-out for the skills repo becomes conditional on the session being there.** The
step already says "in the skills repo: edit the source and commit it locally without asking;
anywhere else: file it". Under this rule that is still right, but only because being _in_
`agent-skills` makes it "the repo where the session is happening". The wording should derive it from
the session's own repo rather than naming `agent-skills` as a special case, so the rule reads the
same from every repo and the exception stops looking like a licence.

**2. Step 2's routing to `~/AGENTS.md` needs re-reading, and this is the substantive change.** The
routing filter sends cross-repo preferences to the always-loaded instructions file, and on this
machine that file is assembled from fragments in a _different_ repo (`power-user-linux-setup`). From
any other session that is a cross-repo write, which the global rules already forbid; the filter's
own text handles it by saying to find and edit the generated file's source. **Under this rule that
is out too** unless the session happens to be in that repo — the candidate is filed as a plan
instead.

[DECISION: **the deployed copies only** — chosen by the user 2026-09-05. A session in the repo that
holds the fragment sources edits them as ordinary work; from any other repo the candidate is filed
for that repo. So the write set is the rule, and being in the owning repo is what makes an edit
ordinary rather than an exception to it — which is how the skill now states it, once, at the top of
its procedure.]

## Why it converges with the Socket finding

Recorded because the two arrived independently, hours apart, and point the same way.

Socket's audit of `session-harvest`
(`plans/2026-09-02-skill-risk-ratings-are-user-facing-and-unwatched.md`) names three components of
its concern. **Two of them are exactly what this rule removes:**

- _"writes to always-loaded instruction files"_ → filed as a plan instead, under change 2 above.
- _"some autonomous local commits"_ → confined to the session's own repo, and the "commit locally
  without asking" licence stops being readable as machine-wide.

The third, _"transcript mining, multi-repo inspection"_, is what the skill is for and stays.

[DECISION: **this is capability reduction the skill does not need, which is the test the user set**
— _"we also can look into doing less intrusive things if it helps, unless the skill needs them."_
Harvest never needed to write outside the session's repo: `plans.py new --for <repo>` plus `absorb`
gives a filed change a real trigger in the session that can act on it, which is strictly better than
a commit in a tree nobody asked it to touch. So the narrowing costs nothing and removes two of the
three things a scanner objected to. It is worth doing on its own merits and the rating is a second
reason, not the reason.]

## The two remaining questions, settled 2026-09-05

[DECISION: **the rule is about file writes and commits; side effects are governed where they are
proposed.** Killing an orphaned process the sweep found is plainly wanted and is not an edit, so
step 8 keeps it and the write-set statement says so explicitly. Same carve-out
`2026-09-03-skills-disclose-what-they-write.md` records for the disclosure format.]

[DECISION: **a filed instruction-file candidate is reported in the "to a plan in another repo" group
like any other filing** — the report already has the group, and `--for` is a delivery, so no new
wording is needed to stop it reading as deferred.]

## Recommended direction

All three done 2026-09-05:

1. ~~Resolve the deployed-versus-source ambiguity~~ — deployed copies only, above.
2. ~~Reword step 6 and step 2~~ — step 6 names "the repo that holds the skill's source, the checkout
   `skills-state` named" and files with the command that subcommand prints; step 2 files an
   instructions-file candidate from any repo but the one holding the fragments.
3. ~~State the allowed write set positively, once~~ — the first paragraph under `## Procedure`, and
   the skill's new disclosure section repeats it as its **Writes** line.

## Migrated to

- **`skills/session-harvest/SKILL.md`** — the write set stated positively once at the top of the
  procedure, repeated as the **Writes** line of the disclosure; step 6 deriving the skills-repo case
  from the session's own repo rather than naming that repo; and step 2 filing an instructions-file
  candidate from any repo but the one holding the fragments.
- **`skills/session-harvest/references/rationale.md`, "Why the write set is stated positively, and
  why narrowing it cost nothing"** — the specification in the user's own words, what the two removed
  permissions were, the capability-reduction test that justified it independently, the convergence
  with an outside risk rating and why that is a second reason rather than the reason, and the
  side-effect carve-out.

Deliberately not migrated: the reporting-group question. `--for` is a delivery, so a filed candidate
appears in the existing "to a plan in another repo" group and needed no new wording — a decision
that changed nothing, which is exactly the kind that does not survive its plan.
