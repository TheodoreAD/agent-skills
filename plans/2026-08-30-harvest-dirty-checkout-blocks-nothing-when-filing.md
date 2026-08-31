---
status: idea
updated: 2026-08-30
---

# `session-harvest` step 0's dirty-checkout note describes a block that no longer exists

## Context

Found while running a harvest from `power-user-linux-setup`, 2026-08-30. Two findings, one of them
evidence for a plan that already exists — see the second section, which should be merged rather than
kept as a separate file.

## Step 0 and step 6 are out of sync

Step 0's dirty-checkout table ends: _"A dirty checkout does **not** block the run. … What it blocks
is the self-update in step 6 — an edit into a checkout another session is holding — so treat it as a
finding about the fold-back."_

Step 6 no longer works that way. It now says only a session already working in the skills repo edits
the source; from anywhere else the fold-back is a filing via `plans.py new --for`, because
`~/AGENTS.md` forbids writing to another repo outright. So for a harvest run anywhere but
`agent-skills` — which is nearly all of them — **a dirty checkout blocks nothing**, since no edit
was going to be attempted.

The note is not wrong so much as stranded: it was written when step 6 still edited the checkout
directly, and step 6's rewrite (the `[DECISION:]` block citing the 2026-08-30 failure) did not reach
back to it. As written it tells a session to treat a dirty checkout as a finding about a fold-back
that would have been a filing regardless.

[NEEDS CLARIFICATION: is the fix to delete the sentence, or to make it conditional — "if you are in
the skills repo, this blocks the self-update; otherwise it does not"? The conditional keeps the
information for the one case where it is true, at the cost of a clause on a step that is already the
longest in the procedure. Deleting it loses nothing for a harvest run elsewhere and slightly
under-warns the in-repo case, which is the rarer one and the one where `git status` is in front of
you anyway.]

Confirmed on this run: the checkout was dirty (4 files, including another skill's `references/`),
the harvest was run from a different repo, and nothing about the fold-back was blocked — this plan
is the fold-back, and filing it needed nothing from that checkout.

## One more occurrence of the `main`/`master` ahead-count trap

Merge this section into `2026-08-30-harvest-assumes-the-branch-is-main.md`, already absorbed into
this repo — it is a data point for that plan, not a second plan about it.

The store's branch is `master`. This run typed `git -C ~/plans log origin/main..HEAD` anyway, **with
step 5's "do not type `main`" sentence in front of it**, and got
`fatal: ambiguous argument 'origin/main..HEAD'`.

Two things worth adding to that plan:

- **It failed loudly only by luck of the pipe.** The call was `… | head -20`, and `head` passed the
  `fatal:` through on stderr so it was visible. Step 5's documented failure is `| wc -l`, which
  swallows it into a calm `0` — the difference between the two is which filter happened to be
  reached for, not anything the session did right.
- **This is the "not followed, repeatedly" shape rather than a wording problem.** The rule is
  unambiguous and was in context; it still did not fire at the moment of typing. That is the
  category step 2 says is a measurement question, and it is now at least the second occurrence after
  the rule existed. Whatever fix that plan lands on should assume rereading is not the lever.

## The skill listing changing mid-session is itself a currency signal

Added from a second harvest in the same session, 2026-08-31, ~40 minutes after the first.

Step 0 prescribes two checks, both of which cost something: diff the installed copy against the
checkout, and compare the skill's last commit against the session's start. Neither is what actually
triggered the re-check on this run. What triggered it was **the available-skills listing having
changed since the session began** — a skill present that was not there before (`skill-fitness`), and
another whose one-line description had been reworded (`invoke-task-conventions`).

That is free evidence, arriving unprompted in the context, that the installer has run since the
session started. It is strictly cheaper than the diff, and it covers a case the diff does not
naturally reach: a re-install that touched skills this run was _not_ leaning on still tells you the
install state moved, which is exactly when the timestamp check is worth paying for on the skills it
_is_ leaning on.

[NEEDS CLARIFICATION: is this a new bullet in step 0, or a sentence on the existing timestamp
paragraph? It is a trigger rather than a check — it tells you _when_ to run the checks step 0
already has, not a fourth thing to verify — so a sentence may be the honest shape. Against that:
step 0 is already the longest step, and a trigger buried in a paragraph about instants is easy to
miss, which is the failure mode this whole step exists to prevent.]

Confirmed on the run that noticed it: both changed skills' installed copies matched the checkout, so
the diff said "same" for everything and would have prompted nothing. The re-check happened only
because the listing looked different, and it was worth doing — `invoke-task-conventions` had been
used earlier in the session, and confirming its change was description-only is what established that
the naming decision made under the older wording did not need re-auditing.
