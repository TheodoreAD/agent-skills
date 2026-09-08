---
status: landed
updated: 2026-09-08
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

[DECISION: **the first candidate, and then the third — git cannot answer "this session", and the
transcript can only answer half of it.** Author is not the discriminator; every session on this
machine commits as the same person. `_correction_overlap` now intersects with the paths this session
actually wrote, which the sweep already computed for the files-outside-a-repo check. That is the
option that makes the flag mean what its sentence said, and it removed the parallel-session shape
and the never-touched-repo shape together, so the cheaper second candidate was never needed.

Then the third candidate as well, 2026-09-08, for the shape narrowing could not reach — see the
section below. The two are not alternatives: the filter removed what a path set can remove, and the
rewording gave up the claim a path set can never support.]

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

## The same defect in a second sweep check, 2026-09-06

Found by an `agent-skills` harvest, and it widens the plan: **this is not one function's bug.** The
disk-artifacts step printed

> `new this session: 127.0.0.1:32812/clean-os-test:0.0.0  227MB  2026-09-06 01:34:56 +0300`
> `new this session: 127.0.0.1:32812/clean-os-test:latest  227MB  2026-09-06 01:34:56 +0300`

and **that session ran no `docker` command at all**, in a run whose every call is in one transcript.
The images are a parallel session's — the name matches a clean-OS test, and `power-user-linux-setup`
was sitting dirty in seven `tasks/*.py` at the same moment. The only thing "new this session"
asserts is that the image timestamp falls inside the session's window.

So the corpus now has the identical mistake in two independent checks, and the shared root is
sharper than either instance: **a time window is being read as an attribution.** Neither check has
any evidence about _who_ did the thing; both label it with the session that happens to be asking.
That framing also predicts where else to look — anything in the sweep whose wording says "this
session" while its computation says "since the boundary".

It is the milder half of the pair, and worth saying so rather than filing it as equally urgent: an
image wrongly attributed costs a reader a moment and a possible `docker rmi` of something another
session still wants, whereas the correction line routes into "needs action now". But the fix is the
same shape, and the two should be decided together — 458 MB proposed for removal on the strength of
a timestamp is not nothing.

[PITFALL: **the disk step cannot use the fix proposed for the other one.** Intersecting with this
session's own write paths works for files in a repo and has nothing to say about a docker image,
which no transcript write-path set will ever contain. What the session _does_ know is whether it ran
`docker` at all — a cheap and complete guard for exactly this case, and one with no equivalent in
the correction check. So "attribute rather than remove" survives as the principle while the
mechanism has to differ per check, which is an argument against a single shared helper.]

## A third sweep check, and the prediction coming true (2026-09-07)

Merged from `2026-09-07-sweep-attributes-research-entries-it-cannot-attribute.md`, filed by a
`repo-tasks` session. The section above predicted where else to look — "anything in the sweep whose
wording says 'this session' while its computation says 'since the boundary'" — and this is that
search returning a hit, which is why it belongs here rather than in a file of its own.

The research-store section lists every entry under `$RESEARCH_HOME/repos/` whose mtime moved after
session start, under the heading `changed_since_session_start`. On a machine where a refresher runs
across the whole library, or where a parallel session is cloning, that is a list of everything the
machine did presented as a list of what this session did.

Session `52905ee0-50ff-4376-bd19-5ab4d9ca0a24`, boundary `2026-09-07T19:12:55+03:00`, reported **30
entries**, among them `cpython`, `node`, `ansible`, `git`, `zed`, `chezmoi`, `home-manager`, `stow`,
`yadm` and `rcm`. **Five were that session's**, and they are checkable from its own transcript: it
ran `library.py add` exactly five times, for a coupling-tool survey — `import-linter`, `grimp`,
`tach`, `deptry`, `FawltyDeps`. The dotfile-manager cluster is visibly somebody else's research
topic. Five attributable of thirty is the shape that makes the bug visible; a harvest reading its
own output would report "this session touched thirty reference clones", which is specific,
plausible, and wrong in the direction nobody re-checks.

**This is the instance where the fix is already written down**, since the docker section was
corrected on 2026-09-06 with exactly the guard this one needs: zero `docker` calls means nothing is
attributable whatever the timestamps say, and the unattributable rows print under their own heading.
The research section got no such treatment and reads with the same false authority the docker one
used to.

[DECISION: **same shape, and the under-attribution was accepted deliberately.** The cross-check is
the session's own `library.py` calls, matched on two spellings — a directory name for an entry it
read, a `<owner>/<repo>` URL for one it added — because an add is the event worth attributing and
names no directory anywhere. It does under-attribute a clone refreshed outside the script, exactly
as the question predicted, and that is the conservative direction: the alternative is claiming a
refresher's work. It is also not this check's blind spot but the corpus-wide one, since a script
doing the work inside one tool call is invisible to every check here — named `SUBPROCESS_SEAM` and
printed beside the count for that reason.]

[DECISION: **a bare count, no list.** The docker fix keeps unattributable rows under their own
heading because the sizes are worth seeing whoever made them; twenty-five refreshed clones are not —
a refresher moving every mtime is the store working as designed. The per-entry checks the skill
actually cares about (a clone without its `SOURCE.md`, an entry deepened away from `--depth 1`) are
facts about the entry rather than about who touched it, so they are unaffected either way.]

The valuable half of that section is unaffected either way: the _convention_ checks the skill
actually cares about — a clone without its `SOURCE.md`, an entry deepened away from `--depth 1` —
are per-entry facts that do not depend on who made them.

[PITFALL: **the pairing signal missed this one, and that is itself evidence.** `absorb` reports a
pair when one plan links the other; this plan and the merged one share a root cause and a fix shape
while citing only the _skill_, so the store offered no hint and the merge happened because both were
read. See `2026-09-03-two-plans-one-subject-absorb-cannot-pair.md`, which owns that gap — this is a
worked instance of it.]

### Fixed 2026-09-08

`store_state` now attributes each changed entry from this session's own commands and prints the rest
as a bare count, with `changed_since_session_start` renamed to `changed_by_this_session` so the key
stops asserting what it never measured.

**Two spellings are matched, and needing both is the non-obvious part.** A session that _reads_ an
entry names its directory (`library.py update <entry>`, an `rg` over the clone); a session that
_adds_ one names a **URL**, and the entry's name is derived from it afterwards, so `<owner>/<repo>`
is what sits in argv and the directory name appears nowhere. Matching the directory alone attributes
every entry a session read and none it added — backwards, since an add is the event worth
attributing and a read does not move an mtime at all.

[PITFALL: **it under-attributes when a script does the work, and the session that wrote the fix is
the example.** A retrofit re-cloned seven entries from a `retrofit.py` holding the names in a list,
so argv named two of the seven and the other five came back under "something else" — this session's
own work. The conservative direction, and the intended one, since the alternative is claiming a
refresher's; but it is the same blind spot one door along — **the tool call is the seam, and
anything a script does inside one is invisible whatever the check is looking for** — so the two are
one gap rather than two. Settled and named `SUBPROCESS_SEAM` in `harvest.py` on 2026-09-08, after a
third instance in a third check; the plan that established it
(`2026-09-05-sweep-misses-a-file-a-subprocess-wrote.md`) is **retired**, and the reasoning is in
`skills/session-harvest/references/rationale.md`, "What the step-5 checks owed a reader". The report
prints the limit next to the count for that reason: a low number here must not read as a small
session.]

## What the store-commit fix established for the sites still open (2026-09-08)

`2026-09-07-harvest-cannot-attribute-a-commit-that-only-deletes.md` — retired 2026-09-08, readable
through `plans.py archive --show` — was this defect's mirror image: `store_commits` calling _this_
session's commits somebody else's, where `_correction_overlap` calls somebody else's _this_ one's.
Same subject, opposite direction, different function. Its fix is the template recommendations 1 and
3 below reach for, so what it measured is a constraint on them rather than a confirmation.

**Argv attribution without an ordering test is a false positive, measured on that fix's own first
live run.** A bare name match gave this session two commits a parallel session had made at 00:18 and
00:20, because this session named the same plan files at 00:45. Both sessions legitimately name one
file; what separates them is that a command cannot have caused a commit that already existed when it
ran — so `_named_before` requires the command's instant to be at or before the commit's, and
declines to attribute when either instant is unparseable. Recommendation 3 carries the same hazard:
two sessions naming one library entry is ordinary, and an entry's mtime is the instant to compare
against.

That plan predicted the argv route would need "no timestamp heuristic and no new parallel-session
risk" and was refuted by its own first run, in the direction that would have shipped it unguarded.
Which is the argument for one attribution helper serving every site rather than a fourth
hand-written one here.

## What landed

All six, across four sessions and six days. Five had shipped by 2026-09-08 without this file being
told, which is its own small instance of the plan's subject — the work was attributed to nobody.

1. **`_correction_overlap` intersects with this session's own write paths.** Its docstring carries
   the 2026-09-04 store instance, and `test_a_path_this_session_never_wrote_is_not_a_correction`
   holds it.
1. **The disk step gates on the session having run `docker` at all.** Done 2026-09-06, and it became
   the template the other sites reached for. Its own first run counted the word inside a quoted `rg`
   pattern, so quoted spans are stripped before matching.
1. **The research-store step attributes from the session's own `library.py` calls**, matching an
   entry directory and an `<owner>/<repo>` URL, with the remainder as a bare count and
   `changed_since_session_start` renamed to `changed_by_this_session`.
1. Moot — recommendation 1 removed the shape the caveat was to cover, so the line never needed a
   warning it would then have outgrown.
1. **The two-author test exists**, asserting the flag stays empty for a repo the session never wrote
   to.
1. **The line drops "CORRECTION", 2026-09-08.** It now reads
   `both sides of a push this session
   made` and names the two readings underneath, held by
   `test_the_overlap_line_reports_what_it_measured_and_does_not_claim_a_correction`.

## Migrated to

- **The four-site pattern, and the lesson the correction check adds to it** ->
  `skills/session-harvest/references/rationale.md`, "Why the sweep now says who owns a process, an
  image and a store commit". The section already held docker, the listener and the store commit; the
  fourth site is the one that shows attribution has a floor, and that a check whose label its
  evidence cannot support has two repairs of which only one is always available.
- **The instruction a harvest follows** -> `session-harvest`'s step 5 git bullet, which now says to
  read the diff before calling anything a correction and why the line stopped doing it.
- **The three failure shapes and their evidence** -> `_correction_overlap`'s own docstring and the
  two tests named above, which is where a reader arrives with the question.

Deliberately not migrated: the per-run tallies (2 true of 4, then 3 false of 3), which were the
argument for changing the wording and are not a fact about the code that remains. The successor
question — whether a diff-shaped test is ever worth adding — is recorded in the docstring as the
narrowing that was declined, not carried forward as open work.

**What this plan does not close** is the general case.
`2026-09-06-two-sessions-share-one-working-tree.md` named this file as the one to resolve first, on
the grounds that if the fix needed a session to know which commits are its own, that primitive
should land once. It did not need it: every repair here was per-site, and `_named_before` — the
nearest thing to a shared primitive — arrived from the store-commit fix and needed an ordering
constraint the write-path route never did. That is an answer to that plan's question, and it points
away from a shared helper.

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
