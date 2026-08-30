---
status: idea
updated: 2026-08-30
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

## The first true positives, and a second gap they exposed

Measured 2026-08-30, in this repo, by acting on the pairings rather than judging them: **five
clusters, twelve files, and every pairing was genuine.** That is the confirmed-true count this plan
recorded as zero, against the two false positives above. It does not overturn the asymmetry argument
— a wrong merge is still the expensive direction — but "two false, zero true" is now "two false,
five true", and recommendation 2's threshold for a write-time marker is further away, not closer.

One pair was correctly left alone, and `absorb` never proposed it: a plan filed mid-session
(`2026-08-30-session-harvest-filed-plan-may-be-absorbed.md`) is about the same skill and the same
store as `2026-08-29-session-harvest-plans-store-sweep.md`, but edits a different section of it. The
judgement that separated them was the one recommendation 3 asks the skill to state — and it had to
be made without the skill stating it.

**The second gap: `absorb` says "consolidate" and nothing says how.** `SKILL.md:454` is the whole
procedure — "merge the two into one plan, keep the earlier filename, delete the other" — and each
clause broke on contact:

- **"The earlier filename" is undefined when both plans share a date**, which is the common case,
  because the pairing is usually two sessions hitting one thing on one day. Two of the five had each
  file explicitly nominating _the other_ as the survivor. The tiebreak used, and worth stating: keep
  the name that describes the merged subject rather than one case of it.
- **A correction is merged in place, not appended.** Two of the five were corrections to plans this
  repo had already absorbed. Appending would leave the wrong argument standing above the right one
  and make the reader arbitrate; rewriting the argument and recording that the premise was corrected
  keeps one document with one claim.
- **Provenance has to name the merged-away file**, or `archive` cannot find it — the deleted plan is
  in git and the merged file's opening line is the only thing pointing at the name to search for.
  Retirement's step 5 already has this rule for retired plans ("must say _retired_"); merges have no
  equivalent and need one.
- **A cluster member already landed in the skill is marked done, not carried.** Two of the twelve
  had been implemented hours earlier by other sessions; merging them in as open work would have
  queued edits that already existed.

## A third false positive, from the plainest citation shape yet

Measured 2026-08-30, absorbing `2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` into
this repo. Its citation is a closing paragraph that opens with the word **`Related:`** and then says
why: the other plan "is actively reshaping this skill's CLI surface … so whatever lands here should
be checked against it rather than designed independently." That is a request to _consult_ a sibling,
stated as plainly as prose can state it, and `absorb` reported it as `consolidate with …`.

It sharpens recommendation 1 into something almost mechanical: the report's own string is the whole
problem, because nothing about this citation was ambiguous to a reader. The pairing was also worse
than merely wrong here — the plan it named was being retired in the same session, so acting on the
instruction would have folded a fresh idea into a file about to be deleted.

## Recommended direction

Rough, weakest-commitment first.

1. **Stop asserting the cause in the report**, whatever else is done. `consolidate with …` reads as
   a verdict; `references …, check whether the separation was deliberate` reads as what it is. One
   string.
2. **Consider a write-time marker** only if the genuine split turns out to be common enough to be
   worth a mechanism. Three false positives against five confirmed true ones (both counts measured
   2026-08-30, above) is not that case — it is an argument for rewording the report, not for
   building a detector.
3. **Say plainly in the skill that a cited sibling is usually just a related plan.** The current
   text only describes the dirty-store cause, so a reader who has not hit the other case has no
   reason to suspect it exists.
4. **Write the merge procedure down**, since the instruction to merge already exists and the four
   rules above were each derived at the point of needing them. Four sentences beside `SKILL.md:454`,
   not a section.

[DEFERRED: the same asymmetry may apply to the collision rule one paragraph up — "a name collision
is a merge, not a rename", justified as "two plans sharing a name means both cover the topic". That
is a much stronger signal than a citation and probably holds, but it was written with the same
reasoning and has not been tested against a real collision.]
