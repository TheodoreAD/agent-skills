---
status: landed
updated: 2026-09-09
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

[DECISION: **not a mechanism — the cheapest thing, exactly as this question framed it.** Shipped
2026-09-09 as `source_plan`, a line in what `new --for` emits naming which of the source repo's
plans owns the decision. The counter-argument stands and is why nothing bigger was built: this
failure needed a same-day reversal by the user of a decision the filing session had itself proposed,
which is rare, and cost about an hour to recover. What was missing was never that looking is
expensive, only that nobody knew there was somewhere to look.]

[DECISION: **a frontmatter field, and the objection is answered by naming the recovery route.** A
pointer into a deleted file would be worse than none only if the reader did not know the file is
still readable — and it is: the filing repo retires plans by deleting them, so `archive --file`
reads one back out of its own retirement commit. `absorb` prints that instruction beside the pointer
rather than leaving it to be remembered, so a retired target degrades to "no further information"
instead of to a dead end.

One thing this went past the question on, deliberately: the field is **printed by `absorb`** under
`decision owned elsewhere`, not merely written into frontmatter for a reader to find. That is the
same standing argument the corpus applied twice on 2026-09-08 — a rule whose evidence the tool does
not print is a rule the next run re-derives differently — and it is not the watcher this plan
resists, because it displays a field that is already there rather than going to look at anything.]

[DECISION: **only `plan-docs`.** A harvest check would fire after the work is done, where this fires
before, and "both" would mean two mechanisms for one fact with the expensive one catching nothing
the cheap one missed. The harvest's own step 0 comparison is the structural analogue and stays where
it is; nothing here needs it.]

## Corroboration for a neighbouring plan

Separately, this session hit the edit-versus-absorb race from the other side and harmlessly. It had
filed `power-user-linux-setup/2026-09-04-docs-build-gate-verification.md` earlier in the run, and
later tried to extend it — by which time a session in that repo had absorbed it, so the store path
no longer existed.

**The Edit tool's existence check is what caught it**, returning `File does not exist` rather than
recreating the file: an `Edit` against an absorbed plan fails loudly, while a `Write` to the same
path recreates it and `plans.py commit` then commits a resurrection under a message written for an
append. The distinction is the tool, not the convention, so it is luck rather than design — but it
is reproducible luck worth knowing about.

**Both halves of that race are now handled and the plan describing it is retired**, 2026-09-09:
`plans.py commit` says when a path is gone because `absorb` took it and names where it went, and the
`Edit`-over-`Write` mitigation above is a `PITFALL` in `plan-docs`' own "Commit a store plan the
moment it is written" section. What this plan is about — a filed plan whose **source** changed its
mind after absorption — is untouched by either, since nothing there is a missing file.

## What landed, 2026-09-09

Exactly the recommended direction, one field and one paragraph, plus the print at the moment of use.

`new --for` emits `source_plan` alongside the three provenance fields; `absorb` lists any that are
filled under `decision owned elsewhere` with the instruction to read the named plan before
implementing and to reach for `archive --file` if it is gone. A blank is a real answer meaning "this
reports a fact"; an unfilled template comment is normalised to blank, so nothing reads as an owner
that is not one.

No watcher and no staleness scan, as this plan asked.

## Migrated to

- **The failure and what the field is for** -> `plan-docs`' "Plans that arrive from another repo",
  which now carries the 2026-09-04 incident, the fill-it-when-you-propose rule, and the `DECISION`
  recording why one field beat a mechanism.
- **Why blank and unfilled mean the same thing** -> `read_plan`'s own comment, and
  `test_an_unfilled_source_plan_reads_as_no_owner_rather_than_as_a_comment`.
- **The prompt arriving at the moment of use** -> `_report_absorbable`, held by
  `test_a_filed_plan_that_proposes_names_who_still_owns_the_decision`.
- **The `Edit`-over-`Write` mitigation** was migrated separately on 2026-09-09 into `plan-docs`'
  "Commit a store plan the moment it is written", when the neighbouring plan it corroborated was
  retired.

Deliberately not migrated: the four-step sequence of who did what in the original incident. The
commit message keeps it, and what a reader needs is the rule plus one line of why, not the
reconstruction.
