---
status: idea
updated: 2026-09-06
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

## Open questions

[NEEDS CLARIFICATION: give `commit` a multi-file form, or state the rule as a constraint? They are
not exclusive and the first is probably enough on its own — the pressure to reach for `git` came
entirely from the one-file signature. `commit <path>...` building one commit from `HEAD` plus every
named path is the same private-index mechanism it already uses, with a loop.]

[NEEDS CLARIFICATION: whether a whole-directory form is wanted too. An absorption's natural unit is
"every plan that left this repo's mirror", which is a directory, and naming eleven paths on a
command line is its own error surface. Against: a directory argument makes it easy to sweep a file
the session did not touch, which is the class of mistake the one-file signature currently prevents
by construction.]

[NEEDS CLARIFICATION: whether the skill should say that a pathspec commit is an acceptable
equivalent, or say nothing and rely on the command being sufficient. Blessing it invites the reader
to decide equivalence for themselves, which is what happened here; staying silent leaves a correct
alternative undocumented, which is what made the deviation feel safe.]

## Recommended direction

Take the multi-file signature first and re-read the rule afterwards. If `commit` covers the case
that produced this, the wording may not need to change at all — the reason it was argued with was
that following it cost eleven commits, and nothing in the file acknowledged that cost or offered a
way around it.
