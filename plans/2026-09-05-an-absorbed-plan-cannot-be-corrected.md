---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 1f762304-ee1a-4bfb-a78f-52da747d29e3.jsonl
source_moment: 2026-09-05T00:25:35+03:00
---

# A filed plan is a snapshot, and once absorbed nothing can correct it

## Context

`plans.py new --for <repo>` is how work crosses a repo boundary, and it works. What has no mechanism
is the **second** message: the filing repo changing its mind after the plan has been absorbed.

The sequence that cost a session real work, 2026-09-04:

1. `power-user-linux-setup` filed a plan into `repo-tasks`' store mirror specifying `docs.build` in
   `quality.check`, on that session's own reasoning.
2. **The user overturned it there the same day** — _"in theory, docs.build should be in apply, check
   shouldn't mutate"_, then after research _"i agree with docs build in precommit"_. Written into
   that repo's own plan as a "Revision" section.
3. A `repo-tasks` session absorbed the filed copy, implemented it faithfully, wrote the superseded
   argument into a shipped docstring and a `contributing/` page, retired the plan, and pushed.
4. The filing session noticed and filed a second plan reporting the contradiction, which the
   `repo-tasks` session then absorbed and acted on — reverting the placement about an hour later.

Step 3 is not a mistake anyone made. Every party did the right thing: the filing session wrote the
correction down where it belonged, flagged twice in its own reports that the filed copy was stale,
and could not write into `repo-tasks`. The absorbing session implemented exactly what it was handed.

## What is actually missing

**A filed plan carries no indication that it is a copy, or of what it is a copy of.** Once absorbed
it is an ordinary plan in the target repo, and after retirement it is not even that. There is no
back-reference the filing repo could follow, and no forward-reference the absorbing repo could
re-check.

Compare `session-harvest` step 0, which solves the same shape for skills: an installed copy can go
stale against its checkout, so the procedure compares them and re-reads the side that is ahead. A
filed plan is the same relationship — a copy taken at an instant, from a source that keeps moving —
and has none of the machinery.

[PITFALL: **the correction arrived as a second filed plan, which worked and does not generalise.**
It cost the filing session a full write-up of a decision it had already written up once, and it only
worked because that session happened to still be running and to notice. Nothing prompts a filing
session to check what became of a plan it filed, and the target repo's session is by then reasoning
from a document that reads as settled — the plan it absorbed is `landed` or deleted, with no
surviving hint that its source disagreed.]

[PITFALL: **retirement makes it worse, and the convention actively encourages retiring promptly.**
`plans/` is defined as a working set that empties out, so the absorbing session is doing exactly
what it should when it retires a landed filed plan the same day. The faster it complies, the smaller
the window in which a correction could have landed on anything.]

## Open questions

[NEEDS CLARIFICATION: is this worth a mechanism at all, or is "file a second plan" the honest
answer? The counter-argument is real: this failure needed a same-day reversal by the user of a
decision the filing session had itself proposed, which is rare, and the recovery cost about an hour.
A mechanism that fires on every filed plan to catch that is a poor trade. The cheapest thing that
would have helped is not a mechanism at all but a line in the filed plan saying which of the source
repo's plans owns the decision, so the absorbing session has somewhere to look.]

[NEEDS CLARIFICATION: if something is added, is it a frontmatter field or prose? `new --for` already
writes `source_repo`, `source_session` and `source_moment` — a `source_plan` naming the filing
repo's own plan file would be the smallest addition and needs no new machinery, since the absorbing
session can read that file directly. Against: the filing repo's plan may itself be retired by then,
and a pointer into a deleted file is worse than none unless the reader knows to reach for
`plans.py archive`.]

[NEEDS CLARIFICATION: does `session-harvest` want a check for this, or only `plan-docs`? A harvest
could ask "did this session act on a plan filed from elsewhere, and has that source moved since" —
structurally the same query step 0 already runs for skills. But it fires after the work is done,
where `plan-docs` could fire before. Both, probably, with different costs; only one of them is
cheap.]

## Corroboration for a neighbouring plan

Separately, this session hit the race that
[`2026-09-04-editing-a-filed-plan-races-with-absorb.md`](2026-09-04-editing-a-filed-plan-races-with-absorb.md)
describes, from the other side and harmlessly. It had filed
`power-user-linux-setup/2026-09-04-docs-build-gate-verification.md` earlier in the run, and later
tried to extend it — by which time a session in that repo had absorbed it, so the store path no
longer existed.

**The Edit tool's existence check is what caught it**, returning `File does not exist` rather than
recreating the file. That is worth recording in that plan as a mitigation that already exists for
one of the two shapes: an `Edit` against an absorbed plan fails loudly, while a `Write` to the same
path would recreate it and `plans.py commit` would then commit a resurrection under a message
written for an append. The distinction is the tool, not the convention, so it is luck rather than
design — but it is reproducible luck worth knowing about.

## Recommended direction

Rough, and behind the questions above.

Prefer the smallest thing that would have helped over a mechanism: a `source_plan` line in what
`new --for` emits, so an absorbing session has a named place to check before implementing, and a
sentence in `plan-docs` telling it to check there when the plan it absorbed proposes a decision
rather than reports a fact. That is one field and one paragraph, and it fails safe — an absent or
retired source plan reads as "no further information", which is the state today.

Resist a watcher or a staleness scan. The corpus of filed plans is small, the failure is rare, and
the convention's own answer to "what carries a correction" is already a plan file; the gap is that
nobody knows to look, not that looking is expensive.
