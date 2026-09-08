---
status: idea
updated: 2026-09-05
---

# Restating a published figure needs old and new patterns over one corpus, and that is hand-rolled

## Context

When `audit.py`'s pattern layer changes, every figure already published in `references/research.md`
and in several plans is on the old scale. The decision taken 2026-09-05 was to **restate** them
rather than leave two scales in circulation — which means running the old and new patterns over one
identical corpus, so the only thing that can move a count is the pattern change.

`audit.py` has no way to do that. `--compare` diffs two **baselines**, which is a different
question: baselines are separated by time as well as by code, so a `--compare` across a pattern
change cannot say which of the two moved a row. That is the defect
`2026-09-05-quiet-gate-changes-what-the-instruments-see.md` §1 records from the other side, and the
new `instrument` field makes it _detectable_ rather than _answerable_.

So the session that changed the patterns wrote two throwaway scripts in its scratchpad: one loading
`git show HEAD:…/audit.py` and the checkout's copy side by side and printing per-row before/after
plus every command the two disagree about, and one classifying each disagreement by cause. Both are
gone with the scratchpad. The **results** are in `references/research.md`; the method is not.

## Why it is worth a flag rather than a note

The restatement decision makes this recurring, not one-off: any future pattern change owes the same
before/after table, and re-deriving the comparison each time is exactly the drift `harvest.py` was
extracted to stop. `skill-fitness` already names the shape — repeated one-off scripts an agent keeps
writing should become code inside a skill.

It also produced the run's most interesting number, which a count alone would have hidden.
`rg-replace` moved 84 -> 81, a change small enough to read as "the fix barely mattered". The
disagreement listing showed 10 prose hits leaving and **7 real ones arriving** — the old pattern's
forward scan stopped at a `|` inside the search pattern, so every deliberate `--replace` with an
alternation had been invisible. A fifth of the row's contents changed under a nearly-flat count.
Nothing but a per-command diff surfaces that.

## It recurred on 2026-09-08, in a different instrument, exactly as predicted

Three more throwaway scripts, same scratchpad shape, same outcome — results published, method gone.
They measured `GREEN_CLAIM_RE` before changing it, and the numbers are now quoted in
`skills/session-harvest/references/rationale.md` and in two plans:

| what it measured                                            | result                                       |
| ----------------------------------------------------------- | -------------------------------------------- |
| which of four alternations fires, 1,201 transcripts         | 587 / 213 / 89 / 29, plus 100 multi-matching |
| what a subject requirement keeps and drops on the bare rule | 303 total, 158 kept, 145 dropped             |
| CI-phrased greens the pattern matched nothing at all        | 329                                          |
| open plans naming a source file that moved after them       | 72 of 167 (43%); 23 (14%) under a 3× proxy   |

**The method, so the figures are re-derivable without the scripts.** Each walked
`~/.claude/projects/**/*.jsonl`, took `type == "assistant"` entries' `text` blocks, split them on
sentence boundaries and newlines, and counted per compiled alternation — attributing a sentence to a
single alternation only when exactly one matched, so overlaps land in their own bucket instead of
double-counting. The subject-requirement figure re-ran the same walk with the candidate pattern and
partitioned the bare-alternation hits by whether the candidate still matched. The open-plan figure
walked every `plans/` under `projects_root`, read `status`/`updated` from frontmatter, extracted
basenames matching a source-suffix set with generic names excluded, and compared each against
`git log -1 --format=%cs -- '*/<name>' <name>` in that repo.

**This is the second instance and it was not one instrument's accident.** The 2026-09-05 case was
`audit.py`'s pattern layer; this one is `harvest.py`'s claim matcher, in a different skill, by a
different session, which is what turns "a flag on `audit.py`" into the wrong shape for the fix — the
recurring need is _measure a pattern over the transcript corpus before changing it_, and at least
two skills' patterns want it. That is an argument for the third open question below resolving toward
`fitness.py` or a shared place, not toward `audit.py`.

[PITFALL: **the plan predicted its own recurrence in the sentence "any future pattern change owes
the same before/after table", and the recurrence still happened** — by a session that had this plan
in its own repo, open, three days later. Nothing surfaced it at the moment of writing the scripts;
the sweep's outside-any-repo check named the three files only afterwards, at harvest. That is the
gap `2026-09-08-stale-claims-in-live-plans-have-no-prompt.md` describes from the other side: the
prompt has to reach the session _writing_ the measurement, and no check here does.]

## Open questions

[NEEDS CLARIFICATION: what shape it takes. A `--patterns-from <git-ref>` flag on the existing run is
the smallest thing that works — load a second `PATTERNS` table from a revision of this file and
report both columns. Against: importing a second copy of the module under a different name is the
kind of cleverness a stdlib script should not carry, and a `git show` to a temp file plus an import
by path is what the throwaway did.]

[NEEDS CLARIFICATION: whether the disagreement listing is part of it or a separate flag. The counts
alone would not have found the seven gains; the listing is where the finding was. But it is
unbounded output on a corpus of 29,000 calls, so it wants a cap and a per-row split.]

[NEEDS CLARIFICATION: whether this belongs in `audit.py` or in `fitness.py`. `fitness.py` already
owns `derivable --compare <baseline>`, which is the same "did this corpus drift against a saved
reference" question — but the corpus here is transcripts rather than skills, and every pattern lives
in `audit.py`.]

## Evidence

- The throwaway scripts ran over 29,389 Bash calls, 30 days to 2026-09-05, and produced the
  before/after table now in `references/research.md` under "The counters matched their own prose".
- The classification that made the table honest — 8 prose, 2 reclassified to `find-exempt`, 3 inside
  a `bash -c` body, for `find-not-fd`'s 13 drops — came from a second pass keyed on whether the
  dropped command contained a shell wrapper. That distinction is what turned "13 dropped" into an
  accepted cost with a stated reason, and it is the part most likely to be skipped next time.

## Recommended direction

Smallest useful version first: one flag that takes a git ref, prints the per-row before/after, and
prints a capped sample of the commands the two tables disagree about. Leave the classification by
cause as the reader's judgement — it needed knowing that `bash -c` bodies are exempt under a rule
living in another repo's instructions file, which no script here should be deciding.
