---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/ingesta
source_session: 7dab6dae-7c67-454f-bba1-981fe3845089.jsonl
source_moment: 2026-09-03T13:47:32+03:00
---

# A retiring plan may never have owned what another plan says it owns

`plan-docs`, "Retiring a plan", step 5's `Don't blindly swap the old path for the new one` bullet.
Found while retiring a plan with eight inbound references.

## The case

`ingesta`'s driving-case plan carried, in its own recommended direction:

> 5. **Labs and monitoring schedules**, both of which belong with "conditions, treatments and
>    outcomes" (the link target is elided) rather than here.

The conditions plan was being retired, all four of its steps built. It had **never taken labs**. It
built signs and symptoms, and one of its own pitfalls is the FDA/NIH BEST distinction saying a
measured value is deliberately not one — so the citing sentence had been false since the day the
target plan answered that question, and nothing surfaced it until the retirement forced a read.

Every option the existing bullet offers is wrong here:

- **Repoint to where the content landed** — `contributing/domain-model.md` does not own labs either,
  so the citation stays false and now points at a file that will never grow the section.
- **Point at a third copy** — there is none.
- **Rewrite as "X landed"** — it did not land; it was never started.
- **Drop it** — silently orphans work somebody wrote down deliberately.

What was actually right was to notice that the item had lost its owner and give it one: the same
plan's own open question about lab results, which is the only thing that owns them. The fix is a
sentence, and finding it took reading both plans rather than following the reference.

## Why the current wording does not reach it

The bullet's three sub-cases are all about **where the content went** — a renamed heading, a
duplicate elsewhere, a redundant citation. This is a different axis: the citation makes a claim
about what the target plan _covers_, and retirement is the moment that claim gets checked for the
first time. A path swap preserves a false sentence perfectly.

The asymmetry is what makes it worth a rule: the swap looks like the careful option. It leaves a
valid link, a plausible sentence, and no dangling reference for the finishing grep to catch — while
the work it names has quietly stopped being anybody's.

## Suggested change

A fourth sub-case in that bullet, one sentence: **a reference that says work _belongs with_ the
retiring plan is a claim to verify, not a path to repoint** — check the plan actually took it, and
where it did not, find that work a new owner before touching the reference. Retirement is the only
occasion anybody re-reads these, so it is the only occasion the claim gets tested.

[NEEDS CLARIFICATION: whether `refs` should distinguish citation shapes. It already lists every
inbound hit with its line, and the two shapes read differently — "see `<plan>`" is navigational,
"belongs with `<plan>`" / "owned by `<plan>`" / "deferred to `<plan>`" asserts ownership. Flagging
the second class would aim the reader at the handful worth verifying rather than at all forty-five
lines, of which the corpus already records most as noise. Probably a small pattern list rather than
anything clever, and worth weighing against the same "too clever" objection the sibling filing
raises.]
