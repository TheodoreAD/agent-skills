---
status: idea
updated: 2026-09-02
source_repo: ingesta
source_session: 0228a2e1-95e6-403c-b639-ad0d853eeb74.jsonl
source_moment: 2026-09-02T20:46:18Z
---

# session-harvest's correction flag attributes a parallel session's pushes to this one

## Context

Found by a harvest run in `ingesta` on 2026-09-02. The sweep printed:

> `CORRECTION? unpushed and already published this session:
> plans/2026-09-02-status-drift-invisible-at-repo-scope.md`
> `CORRECTION? unpushed and already published this session: skills/skill-fitness/scripts/fitness.py`

Both paths are in `agent-skills`. **The session had never written to `agent-skills` at all** — every
edit it made in ten hours was in `ingesta`, which the sweep reported clean and fully pushed on the
same run.

## Evidence

`_correction_overlap` in `scripts/harvest.py` (around line 668) intersects two sets:

```python
unpushed  = git log {upstream}..HEAD --name-only
published = git log {upstream} --since={session start} --name-only
```

`published` is **every commit on the upstream branch since the session began**, with no filter on
author and no way to tell which session made it. On a machine running parallel sessions that is not
"published this session", it is "published by anybody today". The seven unpushed commits in
`agent-skills` on this run were timestamped 22:48–23:45 local, squarely inside the harvesting
session's window and authored by a concurrent session working in that repo.

## A true positive, from a different session (2026-09-03)

Added by a `power-user-linux-setup` harvest whose sweep printed two of these lines:

> `CORRECTION? unpushed and already published this session: plans/2026-08-23-global-agents-md-adherence-watch.md`
> `CORRECTION? unpushed and already published this session: tasks/ai.py`

**Both were genuinely that session's own work** — it pushed both files earlier in the run and then
committed changes to each, one of which really was a correction to a comment the remote was already
serving. So the flag is not uniformly wrong, and that matters for the fix: **the remedy is
attribution, not removal.** A version that simply dropped the line would have lost a real finding
here, in the report zone reserved for what needs action.

Between the two runs the flag is 2 true positives and 2 false ones, which is roughly the worst
possible ratio for a reader — frequent enough to be trusted, wrong often enough to mislead. The
distinguishing evidence in both cases was available locally: whether the session's own transcript
contains a write to that path. The sweep already reads those write paths to decide which repos to
report on, so the intersection could be narrowed to files this session actually wrote without any
new data source.

## Open questions

[PITFALL: **The neighbouring line already carries the caveat this one needs, which is why the gap
survived review.** Four lines above, the ahead-count prints "check who authored these before
recommending a push: on a machine running parallel sessions the ahead-count is not necessarily this
session's work." The overlap line prints no such warning — and it is the more dangerous of the two,
because `SKILL.md` routes a correction into **"needs action now"** as a live inaccuracy with a
reader, while an unexplained ahead-count is merely reported.

So the check most likely to trigger an alarm is the one with no parallel-session guard, sitting
beside the one that has it.]

[PITFALL: **It fails toward a false positive on exactly the machine the skill is written for.** A
single-session machine would never see this; a machine running several sessions across shared repos
sees it whenever any of them pushes. `SKILL.md` elsewhere devotes a whole bullet to not reporting an
already-owned finding as a discovery, citing a near-miss where a harvest was minutes from raising an
alarm about work another session had finished. This defect manufactures that same alarm
mechanically.]

[NEEDS CLARIFICATION: **Whether git can answer "this session" at all, or whether the check should be
narrowed rather than filtered.** Author is not the discriminator — every session on this machine
commits as the same person. Candidates, none obviously right:

- **Intersect with the paths this session actually wrote**, which the sweep already computes for the
  files-outside-a-repo check. Precise, and it makes the flag mean what its sentence says.
- **Restrict to repos this session wrote to**, which is cheaper and would have been enough here: the
  harvesting session touched only `ingesta`, so `agent-skills` should never have been eligible.
- **Keep the intersection and reword the flag** to "published by some session since this one began",
  which is honest but pushes the judgement onto a reader who has no way to make it.

The second is the smallest change that removes the false positive; the first is the one that makes
the check correct in principle.]

## A third shape, which survives the proposed fix (2026-09-04)

Added by an `ingesta` harvest whose sweep printed three of these lines:

> `CORRECTION? unpushed and already published this session: AGENTS.md`
> `CORRECTION? unpushed and already published this session: tasks/seed_database.py`
> `CORRECTION? unpushed and already published this session: tests/unit/test_store.py`

**All three were that session's own writes, in its own repo, and all three were false positives.**
The session pushed 17 commits mid-run, then kept working on the same three files — each later commit
_added_ to what was published rather than correcting it: a new paragraph in `AGENTS.md`, incident
recording appended to the seed task, incident assertions appended to the store test. The remote was
serving nothing wrong at any point; it was serving less.

**This matters because step 1 of the direction below would not have caught it.** Intersecting with
this session's own write paths is exactly what these three already satisfy — same session, same
repo, genuinely written. The overlap being computed is "touched before a push" ∩ "touched after it",
and that set contains every file a session keeps working on, which on a long session is most of
them. Correction is a property of _what changed in the file_, and no intersection of path sets can
see it.

So the flag now has three shapes across three runs — a parallel session's work, a real same-session
correction, and ordinary continued work on a published file — and only the middle one is worth a
line in "needs action now". Path attribution separates the first from the other two and leaves the
third firing. Narrowing further needs something about the diff (a later commit that only adds lines
to a file is not correcting it), or the line stops claiming "CORRECTION?" and says what it actually
knows: this file has commits on both sides of a push this session made.

## Recommended direction

1. Gate `_correction_overlap` on the repo having been written to by this session, or intersect with
   this session's own write paths — whichever the sweep can supply cheaply, since it already tracks
   write paths for another check. **This removes the parallel-session shape and not the third one
   above**, so it is a partial fix rather than the fix.
2. Until then, give the line the same parallel-session caveat its neighbour has, so a reader is not
   handed a correction alarm with no way to tell whose work it describes.
3. A test with two authors' commits on one upstream branch since the boundary, asserting the flag
   stays empty for a repo the session never wrote to.
4. Decide whether the line keeps the word "CORRECTION". On the evidence so far it fires right once
   in six; a line naming what it actually measured — commits on both sides of a push this session
   made — needs no narrowing at all and costs a reader nothing when it fires.

## Evidence

- Session `179f0c44-e084-4cd3-918e-77568655e419`, `ingesta`, 2026-09-04, for the third shape.
  Harvest boundary `2026-09-04T11:34:47+03:00`; that run's sweep reported `dirty: 0` and
  `unpushed: 9`, all nine this session's own, with the three flagged paths among their diffs.
- Session `0228a2e1-95e6-403c-b639-ad0d853eeb74`, `ingesta`, 2026-09-02. Harvest boundary
  `2026-09-02T23:46:18+03:00`.
- Distinctive phrase to find the moment in the transcript: "Confirmed a real defect in the harvest
  skill itself."
- The same run's `ingesta` sweep: `dirty: 0`, `unpushed: 0` — so the session's own repo was
  demonstrably settled while the flag pointed at another repo entirely.
