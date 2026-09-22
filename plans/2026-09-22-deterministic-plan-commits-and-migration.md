---
status: in-progress
updated: 2026-09-22
---

# The commit step made deterministic, and a consolidation that can prove it lost nothing

## Context

`plans.py commit` exists because sessions were hand-rolling
`git -C <store> add … && git -C <store>
commit …` 142 times across 23 sessions. The command took the
mechanism away from them; it left the two things either side of it — deciding what the message says,
and checking what git is about to record — as prose for the agent to follow. Measured 2026-09-22
over `~/.claude/projects/*.jsonl` (118 transcripts that call `plans.py` at all):

| shape                                                         | count |
| ------------------------------------------------------------- | ----- |
| `plans.py commit` calls                                       | 403   |
| …carrying a hand-written `-m`                                 | 369   |
| …whose message is mechanically derivable from the diff        | 134   |
| `git status` naming a plan or a store, within ±2 calls of one | 83    |
| `git commit` naming a plan path, within ±2 calls of one       | 88    |
| `git add` / `git rm` naming a plan path, same window          | 42    |
| `git log` naming a plan or a store, same window               | 30    |

Three findings, and each names a different gap.

**A third of the messages are the diff read back in words.** 97 say some form of "absorbed", 17
"filed", 10 name a status the frontmatter already carries, 10 say "removed". The remaining 235 are
genuine prose — the reason, which only the author has. So the split is not "generate the message"
versus "write it by hand"; it is that a commit message here has two halves and the script owns one
of them.

[DECISION: the derived half is the **subject** — what git will record — and the author's half is the
**body**, the reason. That matches the house commit rule, which asks a subject for the change and a
body for what it is for, and it matches the one exception that rule already names: a plan filed into
the store commits as `<repo>: <what it is>` with no body, which is exactly a case where the subject
is fully derivable and there is no reason to state.]

**The default message was unusable, so nobody used it.** `f"{repo}: {named[0].stem}"` yields
`agent-skills: 2026-09-13-repo-visual-assets-process` — a date-prefixed slug, which is why 369 of
403 calls overrode it. A default that is never taken is not a default.

**The verification is hand-rolled on both sides of the call.** 83 `git status --short` against the
store before committing, 30 `git log @{u}..HEAD` after it. Both ask questions the script is already
holding the answer to: it resolved the repo, it knows the file set, and it just built the commit.

**Sessions still fall back to raw git**: 88 `git commit` and 42 `git add`/`git rm` naming plan paths
sit within two calls of a `plans.py commit` in the same session. That is the shared-index hazard the
command exists to close, reopened by hand.

### The second gap: consolidation loses information

Separate ask, same root cause. A session ends with a plan file, two scratch docs and a body of
reasoning that never reached either. Asked to consolidate, an agent summarises — and summarising is
lossy in a way nothing detects, because the output looks finished. Reported by the user 2026-09-22:
"some agents tend to compact or summarize larger bodies of work in a very lossy way, I just had that
experience a couple of times today on another machine using this skill."

`plans.py` already has the vocabulary to make that loss measurable. The five tags are the atoms of
costly knowledge — a `DECISION` records what an option beat, a `PITFALL` a trap paid for by hitting
it — and a dated line is this corpus's own form for evidence. A consolidation that drops one of
those is the failure; a consolidation that rewords prose is the job.

## Open questions

None outstanding. The three below were answered while designing; they are recorded because the
answer is not the obvious one.

## Recommended direction

### 1. `commit` derives its subject from the change git will record

Per named path, read the previous content out of `HEAD` and the current content off disk, and
classify the transition:

| transition                                     | derived subject                                      |
| ---------------------------------------------- | ---------------------------------------------------- |
| added                                          | `<repo>: <the plan's H1 title>`                      |
| deleted, and `absorbed_to` finds the twin      | `<repo>: absorbed <topic> into <destination repo>`   |
| deleted, previous content had `## Migrated to` | `<repo>: retire <topic>, migrated to <destinations>` |
| deleted, otherwise                             | `<repo>: remove <topic>`                             |
| status changed                                 | `<repo>: <topic> is now <status>`                    |
| content changed only                           | `<repo>: <topic> — <the tag deltas>`                 |

[DECISION: the H1 title, never the filename stem. The stem is a slug with a date glued to the front,
and the file already carries a human sentence one line into the body. Falling back to the stem only
when there is no H1 keeps the old behaviour as the floor rather than the default.]

`--why <text>` means one thing — the reason — and the script decides where it goes: the body under a
derived subject, and the subject itself where nothing could be derived. `-m` keeps overriding both,
so nothing that works today stops working.

[DECISION: `--why` places itself rather than being two flags. The first draft made it strictly the
body, which left a prose-only edit unable to commit at all with the one flag documented for it —
caught by its own test. Inventing a filler subject (`<repo>: update <topic>`) to sit above the
reason was the alternative, and it is worse: a line that reads as information and carries none.]

[DECISION: the `<label>:` prefix names **which part of the repository changed**, which reads as
`plans:` in a repo that keeps its own and as `<repo>:` in a store mirror. Both halves are read from
this corpus's own history rather than chosen — store commits were measured as `api:`,
`invoke-stubs:`, `agent-skills:`, repo commits as `plans:` — and the house commit rule states the
store form outright. The first implementation used the repo's own directory name in both places,
which would have relabelled every repo-held plan commit in this family.]

**Several files stop requiring `-m` when they share one transition kind.** Today's refusal — "no
default message describes a set" — was right about a _guessed_ message and wrong about an enumerated
one: `agent-skills: absorbed 4 plans from the store` describes an absorption exactly. Mixed kinds
still refuse, and now name the kinds they saw instead of refusing flatly.

[PITFALL: a derived subject must never describe the side of the change it is not on. An absorption
is an addition in the repo and a deletion in the store, and the existing `NOTE:` about that exists
because messages announced the addition while committing the removal. The derivation reads `HEAD`
per path in the repo that path is in, so it cannot make that mistake — but any future shortcut that
derives from the _plan's_ frontmatter alone would reintroduce it.]

### 2. `commit` prints the verification, and `pending` answers it before the fact

After committing: the unpushed count for that repo, and any plan file still uncommitted in the
directories this session reads. That is the `git log @{u}..HEAD` and `git status --short` pair, from
the process that already knows the answer.

Before committing, a new read-only `pending`: every plan file this session can see that git does not
agree with, its state (untracked, modified, deletion), the repo it belongs to, and the subject
`commit` would derive for it. `--json` like every other reading command.

[DECISION: `pending` is its own command rather than a flag on `list`. `list` answers "what is open"
— a lifecycle question about content — and this answers "what is uncommitted", a git question about
files. Same nouns, different axis; folding them makes one row mean two things.]

### 3. `migrate`: consolidate without a lossy summary, and prove it

Three phases, one command:

```shell
plans.py migrate start <topic> --from <path>...   # canonical plan, sources carried verbatim
plans.py migrate check <plan>                     # what of each source is still unaccounted for
plans.py migrate finish <plan>                    # gate, then classify the sources for deletion
```

`start` writes a plan with correct frontmatter, a `migrated_from:` list, and every source's content
appended verbatim under a per-source heading. The agent then rewrites it into the standard sections
— editing down, which is a different act from recalling, and the one that cannot silently lose what
it never read.

`check` compares the plan against the sources **on disk**, every time.

[DECISION: no manifest file. `check` re-reads the sources live, so the comparison can never go
stale, and the design avoids adding a second lifecycle store with no retirement of its own — the
same objection this convention already makes to parking anything outside `plans/`. A source already
deleted is read back from `HEAD`; one that is neither is reported, not guessed at.]

What is gated, and what is not:

- **Gated**: every `[TAG: …]` line in every source, and every line carrying a `YYYY-MM-DD` date.
  Those are the units whose loss is expensive and silent.
- **Not gated**: prose. Rewording is the job; a verbatim-coverage metric would forbid it.
- **The escape hatch is a section, not a flag**: `## Deliberately dropped`, naming each item and
  why. Anything named there counts as accounted for — the same shape as `## Migrated to` in the
  retirement procedure, so it reads as the convention rather than as a bypass.

Matching is loose on purpose: an item is accounted for when one paragraph of the plan carries enough
of its significant tokens. Exact substring is the fast path; the ratio is reported for every miss so
a near-miss is visible rather than binary.

`finish` runs the gate, then classifies each source for deletion:

| the source                                | offered for deletion? |
| ----------------------------------------- | --------------------- |
| untracked                                 | yes                   |
| tracked, and the plan landed in this repo | yes                   |
| tracked, and the plan landed in the store | **no**                |

[DECISION: the third row is the user's rule and it is sound for a reason worth writing down. The
deletion is only cheap because the content is still recoverable and the trail from the file to its
replacement is readable. Delete a tracked file whose replacement lives outside the repo and the
repo's history holds a deletion pointing nowhere, while the store holds a plan the repo cannot see —
one lifecycle, two histories, which is the same failure the "absorb before retiring" rule exists to
prevent.]

`finish` never deletes on its own: it prints the offer, and `--delete-sources` does it once the user
has said yes. Deleting an untracked file is the one irreversible step in the procedure, which is why
the coverage gate runs first and why the offer goes to the user rather than to the agent's judgment.

### 4. What the same audit turned up and this plan did not take

Three more hand-rolled shapes, measured in the same pass and left alone deliberately. Each is a
candidate rather than a decision, and none is blocked by anything above.

[DECISION: **a `push` that scans first — built.** The store's own README prescribed
`scan --mode history` before the first push and `scan --mode staged` before each one after. Measured
2026-09-22 over the transcripts: **101 pushes to a plans store, 32 of them (32%) with no `scan`
anywhere in the eight calls before.** A rule stated in a README is read once at install time and
never again at the moment it applies. The objection — that a push is the irreversible outward-facing
step, so wrapping it risks making it feel routine — lost to the observation that the push was
already routine and the scan was the part that was not. A command rather than a git hook, per the
house rule that an agent should know what to run instead of being corrected behind its back. It
scans the **outgoing range** rather than the working tree, since that is what a push actually
publishes and is exactly the case `--mode tree` cannot see.]

[DEFERRED: **the raw-git fallback has not been re-measured.** 88 `git commit` and 42 `git add` /
`git rm` calls naming plan paths sat within two Bash calls of a `plans.py commit` — the shared-index
hazard reopened by hand. The messages and the verification either side of the call were two of the
reasons for reaching past it, so the right next step is to re-run the audit after this change rather
than to add anything.]

[DEFERRED: **the gate runs in the wrong order.** 95 `inv quality.precommit` calls came _after_ a
`plans.py commit` against 42 before it. The first reading of that — sessions committing before
gating — does not survive its own check: of the 95, only **2** re-committed the same plan, while 89
went on to commit a _different_ one, which is a batch rhythm rather than a mistake. The real
evidence is elsewhere and is weaker but genuine: `power-user-linux-setup` carries four reflow-only
cleanup commits against plan files (`e79bb6b`, `7869a38`, `f195fef`, and `ddec24d`'s tail) and one,
`bb74cce`, whose subject records "4 dprint-shaped CI failures". The cost is paid a push later, not a
call later, which is why the transcript window could not see it. Whether `commit` should run the
repo's gate itself still has its objection — it would make a plan commit in the store run a work
repo's toolchain, which is what the store exists to avoid.]

### 5. What the derived subject costs, measured after the fact

The change above makes `--why` optional wherever a subject can be derived. Asked what that loses,
this pass read every commit that ever touched a plan file across four repos and both store tiers —
1,639 commits — and classified each by what its **diff** did rather than by what its subject said.
(The first attempt classified on subject words and put "the sweep asks whether this session landed a
plan it never bumped" in the status-change bucket; the number below is from the patch.)

| operation    | in the store | in a repo  |
| ------------ | ------------ | ---------- |
| added        | 22% of 249   | 97% of 202 |
| content-edit | 32% of 87    | 97% of 752 |
| deleted      | 14% of 119   | 88% of 106 |
| status-only  | —            | 100% of 7  |
| mixed        | 50% of 4     | 99% of 113 |
| **overall**  | **22%**      | **97%**    |

(the share of commits carrying a body longer than 80 characters)

[DECISION: **destination predicts the body; the operation barely moves it.** Every operation splits
the same way and by the same factor, so the per-operation table this plan started from was measuring
where a commit landed. The explanation is the two histories' different readerships: a store is
local, private and frequently remote-less, and nothing does archaeology in it — `archive` reads
content back, never messages — while a repo's history is published, is read by later sessions
through `git log`, and is the artifact the user named as the reason to want bodies at all.]

[PITFALL: **a subject requirement and a body expectation are two rules, and reading them as one
produced a wrong conclusion here first.** The refusal this shipped with — no `--why`, no commit, for
a prose-only edit — is about the **subject**: nothing can be derived, so the script has nothing to
put on the first line, and that is true in the store exactly as in a repo. It is not evidence about
bodies, and the store's 32% does not argue against it, because all 87 of those commits necessarily
had a subject. The first draft of this section called the gate "inverted on both sides" on that
misreading. It is wrong on one side only.]

So the correction is a single new case rather than a redesign. Composed against the destination
finding, the four quadrants are:

| where    | subject derivable? | today                | should be                      |
| -------- | ------------------ | -------------------- | ------------------------------ |
| store    | yes                | commits silently     | unchanged — 22% ever bodied    |
| store    | no                 | refuses, wants text  | unchanged — it needs a subject |
| **repo** | **yes**            | **commits silently** | **expect `--why`** — 97%       |
| repo     | no                 | refuses, wants text  | unchanged                      |

One quadrant moves. `-m` stays the escape hatch for the genuine minority, and it is deliberately the
more expensive path to type, so it is not the lazy default — an opt-out cheaper than compliance is
the opt-out everyone takes.

[UNVERIFIED: the 97% is strong evidence of practice and weaker evidence of necessity. Every one of
those bodies was written when the author had to write the whole message anyway, so the marginal cost
of a body was near zero; now that the subject is free, the rate might have fallen on its own without
anything being lost. Two things argue it would not. A body's vocabulary is a median 73% already
present in the plan it commits, so most of them are restatement — and restatement _at `git log`
speed_ is exactly the artifact being asked for, since the alternative is opening forty files. And
the retirement case is not restatement at all: the file is gone from the tip, so the commit is the
only thing there. Settling this properly means re-measuring the rate after the rule ships.]

[DECISION: a status change is worth asking about after all, against the initial guess that it is not
— but the reason is that it is **rare**, not that it is rich. Seven status-only commits exist in
1,639, and all seven carry a body averaging 443 characters, because a status bump almost never gets
committed alone: it rides along with the edit that justified it. The seven that stand alone are
deliberate triage sweeps — "four in-progress plans that nothing here can move", "done is not a
status, landed is" — where the status line is the residue and the judgment is the point. Asking
there costs seven prompts across a corpus and catches the one case where the frontmatter genuinely
cannot say why it moved.]

### 6. `rename`, because a plan's filename is not only its own name

Three things are keyed on a plan's stem and none of them is visible from the file being moved: its
committed attachments (a directory beside it, named for the stem), its local attachments
(`<store>/_attachments/<rel>/<stem>/`), and every plan citing it by filename — which is how this
convention asks plans to reference each other in the first place.

[DECISION: a command rather than advice, because the local-attachments half fails **silently**. Git
never sees that directory, so a hand-rolled `git mv` leaves the plan's own `## Attachments` rows
naming files that are no longer where the rows say, and nothing in the toolchain ever reports it.
The committed half at least shows up as an untracked directory; the local half shows up as nothing
at all.]

[DECISION: citations are reported and rewritten only under `--update-refs`, not by default. A
filename substitution is right for a link and wrong for a sentence — a reference that quoted a
section title still points at the old wording — and some hits are prose _about_ the plan rather than
a pointer to it. Same judgement the retirement procedure already asks for at step 5, and the same
reason it is not automatic there.]

[DECISION: `commit` learns the rename rather than `rename --commit` being the only way to record
one. A rename arrives as a deletion plus an addition, which the mixed-set refusal would reject —
correctly by its own logic and uselessly. Content decides it: the removed path's blob in `HEAD`
against the added path's bytes. An edit made in the same breath does not match and stays a mixed
set, which is honest, since that genuinely is two changes and no one sentence covers both.]

[PITFALL: every collision is checked before the first move. A rename that relocated the plan and
then found its attachments directory blocked would leave the two halves under different names, with
the plan's rows pointing at neither — a worse state than either doing it or refusing.]
