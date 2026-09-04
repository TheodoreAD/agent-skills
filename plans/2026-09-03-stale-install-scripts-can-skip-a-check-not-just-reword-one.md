---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/ingesta
source_session: 7dab6dae-7c67-454f-bba1-981fe3845089.jsonl
source_moment: 2026-09-03T13:47:32+03:00
---

# A stale `scripts/` can skip a check, not only reword an output

`session-harvest` step 0, the stale-install branch. Found by running it: the branch worked, caught
the staleness, and its prescribed remedy for the `scripts/` half was one step short of what the case
needed.

## What happened

`skills-state --since <session start>` reported `plan-docs` as _install stale against a clean,
pushed checkout_, with `SKILL.md`, `scripts/` and `references/` all differing. The commit predated
session start, so `moved_since_session_start` was `false` and the re-read branch correctly did not
fire.

The session had run `plans.py list` several times during the work, against the **installed** copy.
Diffing the two `plans.py` showed the change was `_print_status_drift` moving from family scope only
to **every** scope. So every `list` this session ran had silently omitted a check the current code
performs — not a reworded line, an answer never computed.

Re-running `list --limit 0` from the checkout returned no drift, so nothing was actually missed in
`ingesta`. The point is that a note would have left that unknown.

## What the skill says now

Step 0, on the three subdirectories:

> `scripts/` is shelled out to, so the next call already runs the new code — but a call made
> _earlier_ in the session ran the old one, which is worth its own one-line note.

"Self-update mechanics" is stronger, and says the right thing —

> Either call the checkout's copy for the rest of the run, or note which results predate the
> re-install; do not re-derive the results from the new source and assume they match.

— but that passage is scoped to **this session having edited the script itself**, and its confirming
example is a renamed output string ("harmless there, and it would not have been if the change had
altered behaviour rather than a string"). Step 0's branch, which covers _someone else's_ commit, is
the one a harvest actually reaches on a machine running parallel sessions, and there the
prescription is only a note.

## Suggested change, small and additive

In step 0's subdirectory paragraph, after the `scripts/` sentence: **read the diff before deciding a
note is enough.** A change that reworks output is a note; a change that _adds or widens a check_
means the earlier call answered a question the current code would have answered differently, and the
remedy is to re-run that command from the checkout. The distinction is cheap — `diff -u` on the one
script, which the harvest is already positioned to run — and it is the difference between "this
result is stale" and "this result was never computed".

The confirming instance is worth carrying because it is the benign one: the re-run came back clean.
An example where nothing was wrong is what stops the rule reading as alarmism, and it is the same
argument the `exit-masked` paragraph already makes for reporting a count whose claims all held.

[NEEDS CLARIFICATION: whether this belongs in `skills-state` itself rather than in prose. The
subcommand already has both copies of the script in hand and could classify the diff — "output only"
versus "touches a check" is not decidable in general, but "the diff adds a call to a function whose
name starts with `_print_`" would have caught this exact case. Probably too clever; the prose
version costs one sentence and one `diff` and generalises to changes no heuristic would classify.
Recorded so the cheap-and-general option is chosen deliberately rather than by default.]
