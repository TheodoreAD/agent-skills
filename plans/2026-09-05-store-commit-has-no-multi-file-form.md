---
status: landed
updated: 2026-09-09
---

# `plans.py commit` takes one file, so a bulk absorption is N commits or a rule reasoned around

## Context

`plan-docs` says plainly to use its own command rather than `git add && git commit`, and gives the
mechanism: the store is one working tree with one index, so a parallel session's staged work can
ride along under your message. Measured 142 calls across 23 sessions before the command existed.

`commit` takes **one positional file**. An absorption commits the removals of every plan it took —
eleven on 2026-09-05, then four more the same evening — so following the rule literally means eleven
single-file commits in the store for one logical change.

**Both times, this session did not.** It used `git -C <store> commit -m "…" -- <mirror dir>`, on the
reasoning that a pathspec commit builds from `HEAD` plus the named paths and therefore gives the
same guarantee the rule exists for, at one commit instead of eleven. That reasoning is, as far as
this session can tell, correct — `git commit -- <paths>` does not ship the index.

**The finding is not that the reasoning was wrong; it is that the rule could be argued with at
all.** This is the second of the three misuse shapes the harvest names: a rule that states a
**mechanism** rather than a **constraint**, and a mechanism can be argued around by anyone who
accepts it. The session had `plan-docs` loaded from its first call and used every other part of it
as written.

## Evidence

- Two `git -C /home/tdumitrescu/plans commit` calls in session
  `c6a6f4e9-de5b-428d-ad95-03adca699e91`, 2026-09-05, tagged `git-C-mutating` by `audit.py` — the
  only two mutating cross-repo git calls in 154, and both to the store.
- Each commit message states the deviation and its reasoning in full, so this was a decision taken
  in the open rather than a slip. That is what makes it evidence about the wording rather than about
  the session.
- The same shape is one the global instructions independently bless: "Commit by pathspec — a
  parallel session's staged file can then neither ride along nor be disturbed." So the agent was
  choosing between two documents that both address index safety and only one of which knows about
  the store's command.

## Two more occurrences, and they fall on opposite sides of the rule

Merged from `2026-09-05-three-confirmations-from-a-harvest-in-another-repo.md`, which reproduced the
signature verbatim in a different repo on the same day, from a session that had not read this plan:

```
plans.py commit <a>.md <b>.md <c>.md -m "power-user-linux-setup: absorbed, three plans leave the store"
plans.py: error: unrecognized arguments: <b>.md <c>.md
```

Recovered as three commits, one per file, with three messages each describing one third of one
logical change. It adds nothing to the diagnosis and everything to its weight: **a second occurrence
in a different repo on a different day is what separates an awkwardness from a shape.**

A third, 2026-09-06, from the session absorbing two plans into `agent-skills`: it **paid the cost
rather than arguing with the rule** — two `plans.py commit` calls for one absorption, two messages
for one logical change. Worth recording because the first session's deviation could be read as a
lapse; a session that complies and still produces a split history shows the cost is structural. That
run also answers the whole-directory question below from the pessimistic side: at the moment of
those commits the store simultaneously held **three unrelated deletions in another repo's mirror**,
staged by a parallel session mid-absorption. A `<mirror dir>` argument would have been correct here
because the two absorptions touched different mirrors — but the margin was one directory level, and
nothing in the command would have said so.

## A fourth occurrence, 2026-09-08, and it is the plan's own case at scale

An `agent-skills` session absorbed **seven** filed plans in one pass — five moved into the repo, two
merged into plans that already owned their subject — which leaves seven store-side removals to
commit. `plans.py commit` takes one file, so following it meant seven commits recording one
operation, each with the same subject.

It did what the earlier sessions did, and for the same stated reason:
`git -C <store> add -A <dir> && git -C <store> commit -m "…"`, one commit for the whole absorption.
Then again three commits later, for a second absorption of two more. Both hits are in that session's
`git-C-mutating` row, which is 3 of 3 — the third being the `git rm` of the two merged files.

Two things this adds. **The cost the deviation avoids is now measured at seven, not two**, which is
the largest on record and the shape a routine bulk absorb produces rather than an unusual day; the
absorb queue reached seven because five sessions in three repos had been filing into it. And
**`plans.py absorb --apply` prints the instruction that gets argued with** — "Commit both: this repo
(the additions) and the store (the removals)" — where "the removals" is plural and the command it
points at is singular. The friction is not only in the rule's wording; the tool that creates the
work states it in the plural one line above the command that cannot do it.

## Open questions

[DECISION: **the multi-file form, and it was enough on its own.** `commit <path>...` builds one
commit from `HEAD` plus every named path, through the same private index, with a loop. Shipped
2026-09-09. `-m` became required past one file, which was not in the question and had to be: the
generated message names a single plan's topic, so a set falling back to it would produce exactly the
thing this plan is about — one message describing a third of its own diff.]

[DECISION: **no whole-directory form.** The argument against held and gained an instance while this
plan was open: at the moment of the third occurrence's commits the store simultaneously held three
unrelated deletions in another repo's mirror, staged by a parallel session mid-absorption. A
`<mirror dir>` argument would have been correct there — by one directory level, with nothing in the
command to say so. Naming paths prevents that by construction and the cost it was avoiding is now
gone.]

[DECISION: **name the pathspec reasoning as correct, and let the loop retire it.** Neither of the
two options as posed. Staying silent leaves a correct alternative undocumented, which is what made
the deviation feel safe; blessing it invites the next reader to decide equivalence again. The skill
now says the sessions who reached for it reasoned correctly — a pathspec commit does not ship the
index — and then that the multi-file form is the same mechanism with a loop, so there is nothing
left to argue with. The reasoning is acknowledged rather than an alternative being sanctioned.]

## What landed, 2026-09-09

`plans.py commit` takes several files, `absorb`'s own report points at that form instead of stating
"the removals" in the plural one line above a singular command, and `plan-docs` carries the four
occurrences as evidence about the wording rather than about those sessions.

## Migrated to

- **Why the rule was argued with, and why the loop settles it** -> `plan-docs`' "Commit a store plan
  the moment it is written" section, which now carries the four occurrences, the two constraints and
  the reason there is no directory form. That is where a reader arrives with the question.
- **The mechanism and its 2026-09-09 reason** -> `commit_paths`' own docstring.
- **The three constraints as executable statements** ->
  `test_commit_takes_a_whole_absorption_as_one_commit`,
  `test_commit_refuses_a_set_with_no_message_because_no_default_describes_one` and
  `test_commit_refuses_paths_that_span_two_repositories`.

Deliberately not migrated: the per-session call counts (154 calls, 3 of 3 in the fourth session's
`git-C-mutating` row). They were the argument for changing the command and are not facts about it.

**The general finding this plan is an instance of** — a rule stating a mechanism can be argued
around by anyone who accepts the mechanism, whereas a rule stating a constraint cannot — is the
second of the three misuse shapes `session-harvest` step 2 already names, and needs no new home.
