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
