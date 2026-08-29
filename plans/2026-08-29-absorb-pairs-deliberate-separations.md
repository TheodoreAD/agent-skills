---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

## Context

Found while absorbing into `power-user-linux-setup` on 2026-08-29. Filed from that session, which
did not own this repo.

`absorb` pairs plans by prose reference: a plan naming another plan's filename, where that name
resolves to a real file on either side, is reported as `consolidate with …`. The skill explains the
pairing as a dirty-store split — a harvest that could not edit an existing plan because another
session held the store, so it wrote a second file referencing the first — and instructs merging
them, keeping the earlier filename, because nothing re-surfaces the pairing after absorption.

That absorb reported **two** pairs. **Both were false positives**, and in both the newer plan's own
prose argues explicitly for staying separate:

- `2026-08-29-agents-md-plan-mode-and-vendor-data.md` → `2026-08-29-attribution-session-url-off.md`.
  Verbatim from the referring plan: "the two are related but the settings change is mechanical while
  these are wording changes, so they are kept apart."
- `2026-08-29-ssh-prefix-applied-without-a-failure.md` →
  `2026-08-28-ssh-add-and-askpass-friction.md`. Verbatim: "It does not cover when an agent should
  reach for the prefix at all, so this is a new concern rather than an addition to that one." The
  referenced plan is also `landed` with a `## Migrated to` section — merging a live idea into a
  retired plan would have been actively wrong.

So the heuristic detects _a reference_, and the instruction attached to it asserts _a cause_. A plan
citing a sibling because the two are related is the common case; a plan citing a sibling because the
store was dirty is the rare one. Presented as an instruction to merge, the common case is the one an
agent acts on, and merging is not reversible in the way leaving them apart is.

The failure is asymmetric and that is what makes it worth fixing rather than tolerating. A missed
genuine split costs one duplicated topic that someone notices later. A wrongly-merged pair destroys
a deliberate separation someone reasoned about in writing, and the reasoning goes with it.

## Open questions

[NEEDS CLARIFICATION: can the genuine case be detected at all, rather than guessed? The
distinguishing fact is not in the plan text — it is that the store had uncommitted changes at the
moment the second plan was written. That is knowable from the store's own git history at write time
and unknowable afterwards. If the harvest wrote a marker when it took the fallback, the pairing
becomes exact; with no marker, any detector is reading intent out of prose.]

[NEEDS CLARIFICATION: if a marker is the answer, where does it go without becoming a sixth tag? The
tag vocabulary is deliberately closed at five, and this is not a tag — it is provenance about why a
file exists. Frontmatter is the obvious home, but the skill's own reasoning against marking
in-transit plans ("route plus location already says it, so there is nothing to set and nothing to
drift") applies here too, and a key that is only ever set by one code path is exactly the kind that
drifts.]

[NEEDS CLARIFICATION: is the cheap fix simply to reword the report? Dropping the causal claim —
`references 2026-08-…` with a line saying a reference may be a deliberate separation, read both
before merging — costs nothing, needs no mechanism, and moves the judgement to where the evidence
is. It loses the property that a genuine split is actively pushed toward consolidation, which was
the point of the pairing. Probably still the right trade, since the report is advice to an agent
that is about to read both files anyway.]

## Recommended direction

Rough, weakest-commitment first.

1. **Stop asserting the cause in the report**, whatever else is done. `consolidate with …` reads as
   a verdict; `references …, check whether the separation was deliberate` reads as what it is. One
   string.
2. **Consider a write-time marker** only if the genuine split turns out to be common enough to be
   worth a mechanism. It has happened at least once — the skill documents it from experience — but
   two consecutive false positives against zero confirmed true ones is not yet a case for one.
3. **Say plainly in the skill that a cited sibling is usually just a related plan.** The current
   text only describes the dirty-store cause, so a reader who has not hit the other case has no
   reason to suspect it exists.

[DEFERRED: the same asymmetry may apply to the collision rule one paragraph up — "a name collision
is a merge, not a rename", justified as "two plans sharing a name means both cover the topic". That
is a much stronger signal than a citation and probably holds, but it was written with the same
reasoning and has not been tested against a real collision.]
