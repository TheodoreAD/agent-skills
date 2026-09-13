---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-09T22:59:29+03:00
---

# `harvest.py` reads a path it matched as proof that this session authored the change

**Merged 2026-09-13 from two plans.** This file, renamed from
`2026-09-09-harvest-attributes-another-sessions-absorption.md`, recorded the **write door**: a
commit to a file this session wrote is credited to this session whoever made it.
`2026-09-12-harvest-attribution-fires-on-its-own-investigation.md` — filed from
`power-user-linux-setup`, session `30c6413a-66ed-4f51-b8f5-eb3dddd550cc.jsonl`,
2026-09-12T12:05:00+03:00, findable by the phrase "this session named a file in a command" —
recorded the **command door**: a path this session merely read is credited the same way. It asked
for this merge, and the reason holds: a fix to either door alone moves the error to the other, so
the two are one subject and have to be decided together. Both originals are in this repo's history,
the second under `e0dd11e`.

## Landed, 2026-09-13

Both doors decided in one change, as asked, and every open question below is answered. Retire once
the commits are pushed; the reasoning lives in `harvest.py`'s docstrings and step 8.

[DECISION: **authorship is the commit's receipt, not the third bucket alone** (`43f481a`). The
bucket as recommended would have made every commit either touched or unattributed, leaving step 8's
edit authority nothing to key on. Making a commit prints its id at a line start — git's
`[main 7e23df7]`, `plans.py commit`'s `committed: …` — and reading history does not, so no command
needs classifying. Measured over seven days of the store: 109 of 110 commits carried a receipt (the
miss was a `| tail -3` cutting it off), none came from a non-commit command, and all six
mis-attributions recorded below resolve to the session that made them. A path match without a
receipt is the bucket, printed `(authorship unestablished)` — the wording the lines plan shares.]

[DECISION: **the sweep enrols a `git -C` target only for a call that is not a read** (`8730971`),
against closed read-only lists so an omission costs noise, never a missed repo. A `cd` is exempt
only when its own result carries the harness's `Shell cwd was reset to` notice, since a `cd` that
sticks moves later unscoped commands into the repo it named. On the 2026-09-12 session `repo-tasks`
drops out and the store and the session's own repo stay.]

The store plans section claims no authorship, so it needed nothing. The research attribution shared
the command door and now skips read-only calls too (`e96e489`).

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

### The second harvest also caught the check doing the right thing

By then the session **had** absorbed a plan of its own and committed the store-side removal
(`849bbe5a8`). `filed` attributed it — correctly — and said how:

```
849bbe5a8  repo-tasks: absorbed, node20 blocker cleared by agent-skills
    ^ this session named a file in a command
9d68dbb39  agent-skills: absorbed the actions/checkout v7 bump
    ^ this session wrote a file in it
```

**The two doors are already distinguished in the output.** A removal commit reached through
`named a file in a command` looked, on this evidence, like a session absorbing something — the case
the widening was built for. One reached through `wrote a file in it` is a session that authored the
plan and had it taken by somebody else. The reason string the check already computes and prints was
the discriminator this section proposed; the 2026-09-12 evidence below shows the first door is not
as clean as this one run made it look.

[DECISION: **a deletion attributed only by the write path cannot be this session's own absorption**,
because absorbing is something you do with a command. That part stands. What it covers is narrower
than it first read — see the next two sections, which each find a case it misses.]

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

## The write door also catches edits, not only absorptions (2026-09-10)

Added by an `agent-skills` harvest that hit this from the filing side, without having read this plan
first — so the confirmation is independent. `filed` reported
`7 commit(s) this session, 7 not attributable`, and **three of the seven were not this session's**:

| store commit | message                                                         | door                 |
| ------------ | --------------------------------------------------------------- | -------------------- |
| `0082f40`    | `power-user-linux-setup: absorbed, five plans leave the store`  | `wrote a file in it` |
| `03d9744`    | `power-user-linux-setup: a third shape, and it is the one …`    | `wrote a file in it` |
| `1cf3341`    | `power-user-linux-setup: a second instance, where the commit …` | `wrote a file in it` |

The first is the absorption case, third instance: that session had filed
`2026-09-09-commit-message-rule-misses-the-double-quote.md` for `power-user-linux-setup`, another
session absorbed it in a batch of five, and the removal was credited back to the filer.

**The other two are a different event, and the deletion rule above does not catch them.** They are
not absorptions and not deletions — they are another session **editing** the filed plan in place,
adding two sections that corrected a claim in it, and committing. Same `wrote a file in it` door,
same wrong attribution, no removal anywhere. So **the write door credits any commit anybody makes to
a file this session wrote**, and absorption is only its commonest shape. On a machine where filed
plans are edited by the repo they were filed for — the mechanism working as designed — the edit case
is not an edge.

That section proposed gating the write door on the session having run an absorbing command at all.
It is right about the write door for a session that absorbed nothing, and it leaks for one that
absorbed something **else**: the gate is session-wide, so one `absorb --apply` anywhere re-opens the
write door for every file that session wrote. And the next section shows the command door it would
have leant on is not clean either.

[PITFALL: **a label naming the outcome needs as many labels as there are outcomes.** "Your filing,
absorbed elsewhere" is exactly right for `0082f40` and wrong for the other two, where the filing was
not taken anywhere — it was corrected in place and still sat in the store awaiting absorption. A
label naming the _evidence_ — `(a file you wrote, changed by someone else)` — covers both and claims
less.]

## The command door over-claims too (2026-09-12)

`filed` reported **3 commits this session** in a `power-user-linux-setup` harvest, and one of them
was not:

```
8d61ea026  2026-09-12T11:57:53+03:00  repo-tasks: absorbed the consumer sweep report,
                                      merged into the consumer-transitions plan
    ^ this session named a file in a command
```

That commit is another session's `absorb --apply` of a plan this session had filed hours earlier.
The session did name the file — twice, in `git -C <store> log --oneline -1 -- <path>` and
`git -C <store> cat-file -e HEAD:<path>` — and it ran both **because the procedure says to**: the
sweep's own instruction is to confirm a filed plan is still there before naming it in the report,
and step 8 adds that a parallel session may have absorbed it, "which is normal and means the work
arrived; say that instead".

**So following the skill correctly is what produced the false attribution.** The commands are the
ones the report step prescribes, they are read-only, and they name exactly the path whose commit is
about to be misattributed. Reading commands made an absorption attributable to whoever absorbed it
**and** to whoever merely looked at it — and the skill guarantees someone looks, every run, at
exactly these paths. The two doors cannot both be satisfied by matching on paths alone.

[PITFALL: **the false positive lands on the row a reader is least able to check.** An unattributed
row is explicitly hedged — "may be another session's live work: report, do not edit" — while an
attributed one carries no such warning, so the one that is wrong is the one presented as settled.
That session caught it only because it had watched that commit appear in real time, twenty minutes
earlier, and knew whose it was.]

### The same root cause reaches `sweep`, and there it is louder

`filed` is the cheap symptom. The expensive one is in the same run's sweep, from the same premise —
a repo named in a read-only command is enrolled as a repo the session touched.

That session read `repo-tasks` three times (`git -C … status`, `git -C … log`, `cat …/plans/…`) and
wrote nothing in that checkout. The sweep enrolled it anyway, which produced two rows:

- **Its unpushed commits, listed as this session's repo state.** Two commits timestamped _during the
  harvest_, both another session's live work. The row is correctly hedged ("check who authored
  these"), so this half costs a sentence in the report and no more.
- **The consumer warning, which is not hedged.** `consumer_candidates(projects_root(), repos)` takes
  the same enrolled set, so the sweep reported `repo-tasks` under **"repos on this machine that
  install a repo this session changed"**, naming five consumers and closing with _"a push here is a
  deploy there"_. That session changed nothing in `repo-tasks` and had nothing to push there.

[PITFALL: **that is the loudest line in the sweep, and the skill's own text says why it has to be.**
The check exists because a push to a shared tool deploys to every consumer's next CI run with no
notice — a genuine, documented, expensive failure. A warning that important firing on a repo the
session only _read_ is the shape that teaches a reader to skim the section, which costs the true
positive it was built for. The skill already makes this argument for a different check, after ten
false positives in the written-paths list: "a section that has been all-false-positive once is one
the next harvest skims, and the true positive would have been the eleventh line."]

Reading a repo is not incidental here either — it is prescribed. The cross-repo rules say reading
another repo "stays fine, and is how a filed plan gets written accurately enough to act on", and
that session read `repo-tasks` for exactly that reason.

## Open questions, answered 2026-09-13

The questions as they stood, each with its answer; the decisions are in "Landed" above.

- **Can touching and authoring be separated by static analysis of the transcript at all?** Yes, and
  not by classifying the command that names the path. The commit's receipt in the session's own tool
  output separates them directly.
- **Or is the honest answer a third bucket rather than a better binary?** Both: the bucket holds
  every path match without a receipt, and the receipt keeps "this session's" from being empty.
- **Should the sweep enrol a repo on a read-only command at all?** No, for `git -C`. A `cd` still
  enrols unless the harness reset it.
- **Does the same over-claim reach the sweep's `store plans` section?** No. It lists dirty and
  unpushed rows and makes no authorship claim to over-make.
- **Does the command-door loop reach the `research` store attribution?** The mechanism did, so it
  now skips read-only calls, which cannot move an mtime.

## Recommended direction

Rough. **Decide both doors in one change**, because every fix recorded so far was right about the
evidence in front of it and moved the error somewhere the next session found it.

Cost the third bucket first. It needs no command classification, it is honest about what path
matching can support, it covers all three observed shapes — absorbed elsewhere, edited elsewhere,
merely read — and the skill already prefers an explicit gap to a confident wrong answer elsewhere
(`holder unknown` on a process, `unavailable` on a listing that did not run). Only if the bucket
turns out too coarse in practice, add the per-path command classification to promote rows back to
attributed: a mutating command naming _that_ path is authorship, a read-only one is not.

For the sweep, enrol a repo on a write or a mutating command, not on a read. That removes the false
consumer warning without touching the check itself.

Fixtures for every direction at once, since fixing one direction is what broke the other: a session
that absorbed its own filing (attributed), a filing absorbed by another session (bucket), a filing
edited in place by another session (bucket), a filing this session only read (bucket), and a sweep
over a repo this session only read (not enrolled).

## Related, kept apart

`2026-09-12-filed-shows-numbers-the-session-did-not-write.md` is the same root error one level down:
a **line** in a file this session touched is not a line it wrote. Kept separate because it is about
lines rather than commits and its fix is the session's own writes rather than a receipt. Both hedge
as `(authorship unestablished)`, so the two halves of `filed` speak in one voice.
