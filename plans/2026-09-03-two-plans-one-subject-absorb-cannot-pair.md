---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-03T23:04:44+03:00
---

# Two plans on one subject, filed hours apart, and nothing pairs them

## Context

`plan-docs`' absorb section says a **name** collision is a merge rather than a rename, and that is
the only collision it detects. Two plans on the **same subject** with **different names**, filed for
the same repo by parallel sessions, are invisible to it — and that is the shape that actually occurs
on this machine, because parallel sessions pick their own filenames.

Confirmed 2026-09-03, and the pair is a good one because neither is wrong:

- `2026-09-03-skills-disclose-what-they-write.md`, filed from `power-user-linux-setup` into the
  store — what a skill declares about its config and mutations, and how `skill-authoring`
  scrutinises them.
- `plans/2026-09-03-where-skills-put-things-on-disk.md`, committed in `agent-skills` by a parallel
  session within hours — where a skill may put things at all: XDG config versus data versus state,
  `$PLANS_HOME`, `$RESEARCH_HOME`.

They compose rather than duplicate, and the dependency runs one way: **a disclosure names locations,
so its format cannot be settled before the locations are.** A session absorbing the first without
the second would design the disclosure format against locations that are about to change.

`absorb` reports neither fact. It prints `references …` beside plans that cite each other by
filename; these did not cite each other, because neither author knew the other existed.

[PITFALL: **the collision is least visible exactly when it is most likely.** Two sessions converge
on one subject because the user raised it with both, in the same period — which is also when neither
can see the other's filename, since the other plan may not exist yet at filing time. The mechanism
that would catch it (citation) requires knowledge the authors cannot have, and the mechanism that
does run (name equality) is defeated by the ordinary act of choosing a descriptive filename.]

## What might actually work

[NEEDS CLARIFICATION: **is this `absorb`'s job, or the filing session's?** Two very different fixes.
`absorb` could surface likely pairs among what it is about to hand over — title-word overlap across
the incoming set and the repo's existing `plans/`, reported as "these two may be one subject" with
no automatic action, in the same spirit as the existing `references` line. The filing session could
instead check the target repo's `plans/` and the store mirror for the same subject _before_ writing,
which is cheaper but only helps when the other plan already exists — and in this instance the two
were hours apart, so it would have caught it in one direction and not the other.]

[NEEDS CLARIFICATION: what signal is good enough without being noise? Filename word overlap is
crude; both of these share only "skills". Frontmatter is no help — neither carries a topic field,
and adding one is a new thing to maintain and get wrong. The honest option may be that no automatic
signal is reliable and the fix is a line in the absorb procedure telling the session to read the
incoming titles as a set and ask whether any two are one subject, which is judgement rather than
detection.]

[NEEDS CLARIFICATION: does the same gap apply within one repo's own `plans/`? Nothing prevents two
sessions in the same repo from opening two plans on one subject either, and `plans.py list` groups
by status rather than by topic, so a reader scanning it sees them apart. The store case is the one
observed; the in-repo case is the same mechanism with no store involved.]

## A second, smaller instance of the same shape

`skills-state`'s verdict for `plan-docs` **changed between two harvests in one session**: at 10:16
it read "unpushed skill work — a re-install reinstalls the same stale copy; the push belongs to
whoever authored them", and at 23:04 it read "install is stale against a clean, pushed checkout — a
re-install is the remedy". A parallel session pushed in the interval, so the row moved from the
second of the skill's three cases to the first, and **the remedy inverted**: from "a re-install
cannot fix this" to "a re-install is exactly the fix".

`SKILL.md` already carries this principle for git ahead-counts — _"That the count is from now.
Re-read it at report time; one taken earlier in the session is the session's memory wearing a
measurement's clothes."_ It does not carry it for `skills-state`, and `skills-state` is the check
whose output most directly becomes advice to the user. A harvest that read the verdict once and
reported it an hour later would have told the user a re-install was pointless when it had just
become the answer.

Cheapest fix: one clause in step 0 saying the verdict is a reading rather than a fact, and that a
second harvest re-runs it rather than quoting the first. Rule count unchanged.

## Recommended direction

Decide the `absorb`-versus-filing-session question first; it decides whether anything is built at
all. The judgement-only option — a line in the absorb procedure asking the session to read the
incoming set as a set — is worth taking seriously rather than treating as the fallback, because both
detection ideas above are weak and a weak detector that is trusted is worse than a prompt to think.

The `skills-state` clause is independent, small, and can land whenever someone is next in the file.
