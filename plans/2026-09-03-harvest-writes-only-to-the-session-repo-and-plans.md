---
status: idea
updated: 2026-09-03
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

[NEEDS CLARIFICATION: **does "instructions" mean the deployed file only, or its source as well?**
"Live skills or instructions" most naturally reads as the deployed `~/AGENTS.md` and the installed
`~/.agents/skills/` copies — editing either is already banned, by PULSE's own rules and by this
skill's self-update mechanics respectively, so on that reading the sentence changes nothing and the
new content is only the positive write set. The stronger reading also rules out editing
`config/agents-md/` fragments from a session in that repo, which would be a real change and sits
oddly with that being ordinary work for a session working there — this very session did it as its
main task, at the user's direction. Resolve before rewording step 2, since the two readings produce
different instructions.]

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

## Open questions

[NEEDS CLARIFICATION: **does anything else in the procedure write outside the allowed set?** Step 5
prescribes running another repo's gate and re-running commands; those are reads. Step 8 says "fix
what is cheap and unambiguous rather than only reporting it — kill the orphaned loops", which is a
machine-level mutation outside any repo, not a file write. Worth deciding whether the rule is about
**file writes** specifically or about **side effects** generally, because killing a stray process is
plainly wanted and is not an edit.]

[NEEDS CLARIFICATION: how should the report name a candidate that the old routing would have written
into `~/AGENTS.md` and the new one files? The risk is that a filed instruction-file candidate reads
as deferred rather than routed, and the whole point of `--for` is that it is a delivery. One line in
the report's "to a plan in another repo" group probably covers it.]

## Recommended direction

1. Resolve the deployed-versus-source ambiguity above; it decides the wording of change 2.
2. Reword step 6 to derive the skills-repo carve-out from "the repo the session is in" rather than
   naming the repo, and step 2 to file rather than edit when the instructions file's source is
   elsewhere.
3. State the allowed write set positively, once, near the top of the procedure — the current text
   distributes it across steps 2, 6 and the self-update mechanics, which is why it reads as three
   exceptions rather than one rule.
