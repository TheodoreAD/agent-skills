---
status: landed
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_session: 156d723c-4e21-41ef-aac9-bfd6c05b681c.jsonl
source_moment: 2026-09-05T19:40:00+03:00
---

# `skills-state --since` asks the operator for a value the script already knows

## Context

`session-harvest`'s step 0 prescribes `python3 $H skills-state --since <session start>`, and it is
the **first** substantive command of a harvest. But the session start is printed by `transcript`,
which the same block lists afterwards — so at the moment the value is needed it has not been
produced, and the operator supplies it by hand.

Confirmed 2026-09-05, this session: the first call passed midnight local as a stand-in, because that
was the only bound to hand. It reported `session-harvest` `SKILL.md` as moved by **9** commits;
re-run with the real start (`2026-09-04T22:43:15Z`, from `transcript`) it reported **8**. Small, and
in the direction that inflates — an over-count makes the staleness branch look more urgent than it
is, which is the branch that costs the most to walk.

The value is not hard to get: `skills-state` runs in the same process as the resolver that `turns`,
`sweep` and `claims` already use, and that resolver prints `started:` from the transcript's first
entry. Every other subcommand resolves the session from `$CLAUDE_CODE_SESSION_ID` without being
told; this one alone requires the operator to fetch a timestamp from a sibling subcommand and retype
it.

[DECISION: **this belongs in the script, not in a clearer sentence in step 0.** The skill's own
standard — "a correction that a script can simply not make belongs in the script" — applies exactly:
reordering the block so `transcript` comes first would still leave a value to copy between two
commands, and the copy is the error surface. Default `--since` to the resolved session start, keep
the flag as an override for auditing a window that is not this session's.]

## Confirmed again the same day, by a second session in a different repo

A harvest in `agent-skills` on 2026-09-05 hit it from the other side: rather than substituting a
stand-in, it **reordered the block** — running `transcript` first purely to obtain the value, then
passing `2026-09-05T16:22:47.492Z` to `skills-state` by hand. No wrong number resulted, which is the
point worth adding: the friction is not that the value comes out wrong, it is that step 0's
prescribed order cannot be followed as written. A session either substitutes something (the first
instance, which inflated a count) or silently re-orders the block (this one). Both are the operator
standing in for a resolver that is already in the process.

## A third instance, and the first where the wrong value pointed the other way

Merged from `2026-09-05-three-confirmations-from-a-harvest-in-another-repo.md`, filed by a
`power-user-linux-setup` harvest the same evening. It substituted **14:00 local** — again the only
bound to hand at step 0 — and reported **10** moved commits for `session-harvest`, **3** for
`plan-docs`, **6** for `session-bash-audit`. Re-run with the real start (`2026-09-05T16:36:54.394Z`,
from `transcript`): **5**, **0** and **3**. The largest over-count on record.

**The `plan-docs` row is the one that changes the argument, because 3 became 0 rather than merely
shrinking.** An inflated count makes the staleness branch look more urgent than it is; a count that
should have been zero routes a skill that had not moved at all into "re-read `SKILL.md` from
whichever side is ahead" — step 0's most expensive branch — and the commits it named were real and
all predated the session, so nothing downstream would have revealed the mistake. So the flag's cost
is not only a number reading high: **a clean skill can be routed into the staleness branch, and the
routing is silent.** Consistent with the decision above; it raises what that decision is worth, not
what it should be.

## A fourth instance, and it is the first to err the _other_ way

Merged from `2026-09-07-skills-state-since-is-a-guess-the-script-could-compute.md`, filed by a
`power-user-linux-setup` harvest on 2026-09-07 that could not edit this file, and which said in its
own opening line that it was evidence for this plan rather than a second topic. Its distinctive
transcript phrase: "`--since` guessed late hid four of eight commits — including the one whose
instruction I followed."

Every instance above over-counted. **This one under-counted, and by half.** Session
`11ef513d-37c0-4bc6-ba25-dd40d8551940` passed `--since 2026-09-07T13:00:00+03:00` against a
transcript starting `2026-09-07T08:18:30.693Z`, about three hours earlier, and `skills-state`
reported **4** commits to `session-harvest`'s `SKILL.md` where there were **8** — `6aa620e`,
`c0a2beb`, `5e2d8b5` and `39d569a` were all hidden.

**The two directions are not symmetric, and this is the dangerous one.** An over-count sends the
reader down the staleness branch unnecessarily: expensive, and self-correcting the moment they look.
An under-count argues for **doing nothing**, and shortens the very judgement step 0 makes the list
the input to — "re-read it from whichever side is ahead, unless every one of those commits is this
session's own". A short list makes "this session's own" easier to conclude and offers no signal that
anything is missing, because every row it _does_ print is true.

Sharper still: two of the four hidden commits were ones that run then depended on. `5e2d8b5` is the
instruction to **diff** a stale `SKILL.md` rather than re-read it, which the run followed, and
`39d569a` is `skills-state` learning to report its own blind spot, which told the run which earlier
answers to re-run. Both reached it through the diff rather than the commit list — which is why the
under-count did no damage there, and exactly why it would on the branch where the list _is_ the
evidence.

## The default may not be session start at all, for one row

A fifth instance, from the same filing. Session `9164dacd` passed
`--since
2026-09-07T15:00:00+03:00` — a guess, close enough to the transcript's `14:55:16Z` that the
count was right — and still produced a false alarm, for a reason no earlier instance reaches: **the
harvest was invoked in the session's last minutes, so `session-harvest`'s own body was loaded
_after_ the three commits the check reported.** The warning said the held copy might be superseded;
the held copy was the newest text on the machine.

So the instant that matters is **when the skill was loaded, not when the session began**, and for a
skill invoked late those differ by hours. Session start is right for a skill the session has been
leaning on throughout — `plan-docs` there, loaded at 18:40 and genuinely four commits stale by the
end — and wrong for the skill doing the asking, which is loaded last by construction. A run treating
them alike gets a false positive on itself every time, in the step whose whole purpose is deciding
whether to trust its own instructions.

Cheap version if per-skill load times are not recoverable: exempt the harvest's own skill from the
warning, or label that row. The transcript does record when a skill's body entered context, so the
precise version is available.

[DECISION: **on top of it, as a per-row refinement — and load time was cheap, so the exemption was
not needed.** Landed 2026-09-08. A skill's body entering context is a `Skill` tool call in the
transcript, carrying the skill name and a timestamp, read by the same `iter_blocks` walk everything
else here uses; the earliest call per skill wins, since a re-invocation was already in context. So
the resolution decided above computes the session-wide default and each row then baselines on its
own load instant where one exists. A skill never invoked this session falls back to session start,
`--since` still overrides every row, and `move_baseline` records which of the two each row used —
the point being that a baseline changing silently per row would be this plan's own defect one level
up.]

[DECISION: **print the value used**, whichever way the default goes — a
`# since: <instant>
(transcript start | supplied)` line. Folded in from the merged plan, and it is
the only part of this a default alone does not cover: the specific harm was never the wrong window
but that the wrong window was indistinguishable from the right one in the output, so nothing
prompted a second look. An operator who passes `--since` explicitly can still pass a wrong one.]

[PITFALL: **the merged plan was filed as a standalone proposal and rewritten as evidence minutes
later, inside the same harvest.** The session filed it without checking whether the topic was
already owned — which `session-harvest`'s own step 2 requires, in the bullet immediately after the
one that told it to file — and found this plan only while double-checking something else. The check
is cheap (`ls` the store directory the filing went into, `rg -l` the target repo's `plans/`). Worth
knowing that the rule's placement, file first and report second, reads as urgency, and urgency is
what skipped the lookup.]

## A sixth instance, and it names the cause the other five described around

Merged from `2026-09-08-skills-state-since-has-an-unstated-source.md`, filed by a `repo-tasks`
harvest. Every instance above is a session substituting a value; this one says **why the
substitution is the natural move**: `<session start>` is a placeholder with **no stated source**.
The value exists — `transcript` prints it as `started:` — but nothing in step 0's command block or
its prose says to take it from there, and the two commands are independent, so a session batching
its tool calls runs them in parallel and must supply `--since` before `transcript` has answered.

That harvest ran both in one message and guessed `2026-09-07T18:00:00+03:00` against a real start of
`19:27:31+03:00` — ninety minutes early. **The verdict was correct anyway**, because the install was
genuinely stale by five commits and the widened window changed nothing. Luck rather than robustness,
and the shape that keeps a placeholder unnoticed: the wrong input produced the right answer.

The error is directional and silent both ways, which the earlier instances only half stated. **Too
early** widens the window, so commits predating the session are listed as having moved under it and
the verdict prescribes a re-read on evidence that does not support one — the most expensive step in
the procedure, fired on the case the skill already warns it should not fire on. **Too late** narrows
it, and a genuinely superseding commit lands outside; that is the failure the whole branch exists to
catch, failing closed behind a clean-looking report.

[PITFALL: **`boundary` is documented as the first command and does not print session start.** So the
reader holds a timestamp from the very first call and it is the wrong one for this flag — `boundary`
is "now", `--since` wants "when this session began". Using it would narrow the window to nothing and
report that no skill had moved: the failure that looks most like success.]

[DECISION: **reported, never rejected — and the question's premise was wrong.** It called an
earlier-than-start value always a mistake, since no session began before it began. But the flag's
own second purpose is auditing a window that is not this session's, and an earlier instant is
exactly what that takes; rejecting it would also remove the way to correct a typo. So
`_supplied_note` names the gap in minutes and which way the window moved, which is what separates a
guess from a deliberate audit — indistinguishable until the two instants are printed side by side.
Verified on the session that made the change: a value 92 minutes early reported four skill commits
moved where the real start reported three, and nothing but the note made that difference visible.]

This does not reopen the decision; it is the strongest argument yet for it. Documenting the source
in prose is the alternative the filing considered and rejected: it explains the placeholder where
defaulting deletes it, and makes the common invocation `skills-state` with no arguments.

## Resolved questions

[DECISION: **when no session resolves, the comparison still runs and only the moved-since-start half
goes unanswered** — the guess in the original question, and better than the "keep requiring the
flag" it hedged toward. `since: unresolved — no session resolved` prints in place of a value, so the
reader's ordinary case (an installed copy, no harness id) is a stated gap rather than an error or a
silent `None`. A silent `None` would have read as "nothing moved", which is the failure the whole
plan is about, one level down.]

## What landed, 2026-09-08

Exactly the recommended direction: one resolver call, the flag kept as an override, the placeholder
gone from step 0's block. `skills-state` now resolves the session the way `turns`, `sweep` and
`claims` already do, so the common invocation takes no arguments at all.

**And it prints the value it used, every time**, which is the half the plan's own evidence argued
for without naming: the harm across all six instances was never the wrong window but that a wrong
one was indistinguishable from a right one in the output, so nothing prompted a second look. That
holds for an operator passing the override too, which is what the supplied-value note above exists
for.

## Recommended direction

One resolver call in `skills-state`, the flag kept as an override, and step 0's command block loses
the placeholder. The other change to the same subcommand's argument handling — making `--skill`
additive rather than replacing the defaults — has since landed and been retired, so this is now the
last of the pair rather than half of a shared review.
