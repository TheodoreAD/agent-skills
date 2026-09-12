---
status: idea
updated: 2026-09-09
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-09T22:59:29+03:00
---

# `harvest.py filed` credits this session with another session's absorption of its filing

## Context

`filed`'s attribution rule is "a commit is this session's when this session wrote or named one of
its files". That rule was widened deliberately, and the reason is in `SKILL.md`: a write-path test
alone called a session's own `absorb --apply` removals a stranger's, because absorption **moves**
the file out of the store so the absorbing session writes nothing at the store path. Reading the
session's own commands as well as its writes fixed that case.

**It over-corrects into the mirror case, which is at least as common on this machine.** When session
A files a plan `--for <repo>` and session B — working in that repo — absorbs it, the absorption
commit removes a file **A wrote**. So A is credited with a commit B made, in A's own harvest report,
under the heading that exists to separate the two.

Measured live, 2026-09-09, in the session that filed this:

| store commit | message                                               | attributed to | actually            |
| ------------ | ----------------------------------------------------- | ------------- | ------------------- |
| `9d68dbb39`  | `agent-skills: absorbed the actions/checkout v7 bump` | this session  | **another session** |
| `1cad274d3`  | `agent-skills: absorbed, stale claims in live plans`  | this session  | **another session** |

At the moment those rows were read, that session had filed two plans for `agent-skills` and **never
run `absorb --apply` at all** — its only `absorb` call was the read-only one at session start. Both
absorptions were another session's work, minutes after each filing. `filed` reported
`8 commit(s) this session, 2 not attributable`, and two of the eight were not this session's.

The genuinely unattributed rows were correctly marked, so the failure is one-directional: the check
never wrongly disowns, it only wrongly claims.

**Re-derived at the same session's second harvest, 2026-09-09T23:47, and the counts above are a
prefix**: `11 commit(s) this session, 3 not attributable`. The two mis-attributed rows are unchanged
and still mis-attributed. Recorded because a figure filed mid-session is a prefix of that session
rather than a smaller version of it, and this plan's argument does not turn on which way it moved.

### The second harvest also caught the check doing the right thing, and that is the fix

By then the session **had** absorbed a plan of its own and committed the store-side removal
(`849bbe5a8`). `filed` attributed it — correctly — and said how:

```
849bbe5a8  repo-tasks: absorbed, node20 blocker cleared by agent-skills
    ^ this session named a file in a command
9d68dbb39  agent-skills: absorbed the actions/checkout v7 bump
    ^ this session wrote a file in it
```

**The two doors are already distinguished in the output.** A removal commit reached through
`named a file in a command` is a session absorbing something — the case the widening was built for,
working. One reached through `wrote a file in it` is a session that authored the plan and had it
taken by somebody else. So the discriminator needs no new evidence and no transcript re-scan: it is
the reason string the check already computes and prints.

[DECISION: **that makes the first open question below cheaper than it was written.** It proposed
gating on whether the session ran an absorbing command at all, or on whether its commands named that
specific path — both real, both requiring new logic. The narrower fact is simply that a **deletion**
attributed _only_ by the write path cannot be this session's own absorption, because absorbing is
something you do with a command. Same conclusion, no new inputs.]

## Why it matters more than the count suggests

- **It inflates exactly the number a harvest reports as its own output.** "8 store commits this
  session" reads as a measure of what the session produced, and the report's opening groups are
  built from it.
- **It is invisible without independent memory.** This run caught it only because the session knew
  it had never run `absorb --apply`. A compacted session, or a second harvest reading the first's
  report, has no such check — and `SKILL.md` already warns that a plausible number nobody can
  falsify is the dangerous shape.
- **It is the good outcome misread as your own work.** Another session absorbing your filing within
  minutes is the cross-repo mechanism working perfectly. Reporting it as this session's commit hides
  the one fact worth knowing — that the filing _landed_.

[PITFALL: **the `MISSING` row and the attribution row disagree about the same event, in the same
report, and only one of them is right.** `filed` correctly printed both agent-skills plans as
`MISSING (absorbed, or moved)` under "plan files this session wrote" — which is the true and useful
statement — while simultaneously listing the two absorption commits as this session's. A reader who
trusts the second reads the first as this session having done the absorbing. The two halves already
hold the evidence to contradict each other.]

## A third session, and it refutes the narrowing above (2026-09-10)

Added by an `agent-skills` harvest that hit this from the filing side, without having read this plan
first — so the confirmation is independent. `filed` reported
`7 commit(s) this session, 7 not
attributable`, and **three of the seven were not this session's**:

| store commit | message                                                         | door                 |
| ------------ | --------------------------------------------------------------- | -------------------- |
| `0082f40`    | `power-user-linux-setup: absorbed, five plans leave the store`  | `wrote a file in it` |
| `03d9744`    | `power-user-linux-setup: a third shape, and it is the one …`    | `wrote a file in it` |
| `1cf3341`    | `power-user-linux-setup: a second instance, where the commit …` | `wrote a file in it` |

The first is this plan's existing case, third instance: that session had filed
`2026-09-09-commit-message-rule-misses-the-double-quote.md` for `power-user-linux-setup`, another
session absorbed it in a batch of five, and the removal was credited back to the filer.

**The other two are a different event, and the `DECISION` above would not catch them.** They are not
absorptions and not deletions — they are another session **editing** the filed plan in place, adding
two sections that corrected a claim in it, and committing. Same `wrote a file in it` door, same
wrong attribution, no removal anywhere.

So the narrowing — "a **deletion** attributed only by the write path cannot be this session's own
absorption" — is right about deletions and covers less than half of what this session saw. The
general statement is stronger and simpler: **the write-path door credits any commit anybody makes to
a file this session wrote**, and absorption is only its commonest shape. On a machine where filed
plans are edited by the repo they were filed for — which is the mechanism working as designed, and
which produced two of these three rows — the edit case is not an edge.

[DECISION: **that makes the first open question's command-side gate the right fix after all, and the
deletion shortcut the wrong one.** Gating the write-path door on the session having run an absorbing
command handles both shapes, because a session that ran no absorbing command authored neither the
removal nor the edit. The deletion test was cheaper and is a strict subset. Recorded here rather
than by rewriting the `DECISION` above, because the reasoning that produced it was sound on the
evidence it had — two absorptions and no edits.]

[PITFALL: **the third label proposed below needs a fourth, or a wording that covers both.** "Your
filing, absorbed elsewhere" is exactly right for `0082f40` and wrong for the other two, where the
filing was not taken anywhere — it was corrected in place and is still sitting in the store awaiting
absorption. A label naming the outcome will need two; one naming the _evidence_ —
`(a file you wrote, changed by someone else)` — covers both and claims less.]

## Open questions

[NEEDS CLARIFICATION: what distinguishes the two cases mechanically? The obvious discriminator is
whether the session ran `absorb --apply` (or `move --to repo`) at all — a session that never did
cannot have authored a removal commit, whatever files it wrote. That is a command-side test, and
`filed` already reads the session's commands. A narrower version keys on the individual file:
attribute a removal only when this session's own commands named _that_ path in an absorbing
capacity. Both are cheap; the second is stricter and probably right.]

[NEEDS CLARIFICATION: should a removal commit for a file this session wrote get its own label rather
than falling to one side? It is neither "yours" nor "not attributable" — it is **your filing, taken
by someone else**, which is a third state and the most informative one. A row reading
`(your filing, absorbed elsewhere)` would carry more than either existing label and needs no new
evidence to compute.]

[NEEDS CLARIFICATION: does the same over-claim reach the sweep's `store plans` section? That section
lists filed-and-not-taken plans rather than commits, so it looked correct in this run — but it is
built from the same store and worth checking rather than assumed.]

## Recommended direction

Rough, and the first open question mostly settles it.

Gate the command-side half of the attribution on the session having actually run an absorbing
command. A session with no `absorb --apply` and no `move --to repo` in its transcript cannot have
authored a store removal, so for that session the write-path test alone is correct — which is the
rule that existed before the widening, applied only where it was never wrong.

Prefer the third label over reclassifying to `(not attributed)`. The event is worth surfacing: it
tells the filing session its plan reached the repo that can act on it, which is the outcome
`new --for` exists to produce and which nothing else in the report states.

Worth adding a fixture for both directions at once — a session that absorbed its own filing, and a
session whose filing was absorbed by another — since fixing one direction is what broke the other.
