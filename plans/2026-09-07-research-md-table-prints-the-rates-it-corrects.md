---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/power-user-linux-setup
source_session: 9164dacd-2813-4087-a593-14dc24c44782.jsonl
source_moment: 2026-09-07T18:22:27+03:00
---

# `research.md` prints the pre-fix rates forty lines below the section that corrects them

## Context

`skills/session-bash-audit/references/research.md` carries two sections that disagree about the same
four numbers, and the disagreement is invisible unless both are read in one sitting:

- **"A heredoc hid every command that followed it (2026-09-06)"** states sample 6's `exit-masked` is
  **38%** at the row's own boundary, and its `PITFALL` explains why a whole-transcript figure is a
  different measurement rather than a correction.
- **"One rate over two outcomes (2026-09-06)"**, migrated from
  `plans/2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` on retirement, opens with a
  four-row table that prints the **pre-fix** rates the section above corrects: sample 6 at 27%,
  sample 2 at 28%, sample 7 at 22%, sample 8 at 25%.

The second table is the load-bearing one — every rejected design in that section is argued from it.

`power-user-linux-setup`'s corpus was re-scored on 2026-09-07 at each row's own recorded `--until`
boundary, with `audit.py` at `95f8af7`, and the denominators reproduce the published `calls` figures
exactly:

| sample | table says | re-scored | derived split       |
| ------ | ---------: | --------: | ------------------- |
| 6      |        27% |   **38%** | 30 gate, 52 listing |
| 7      |        22% |   **28%** | 31 gate, 5 listing  |
| 8      |        25% |   **18%** | 16 gate, 23 listing |
| 11     |          — |   **12%** | 25 gate, 3 listing  |

## Two of the section's own arguments turn on cells that moved

**The anchor is not the row it is described as.** The table calls sample 6 "read-only listings —
damage structurally impossible", and it is the row the gate-versus-listing argument leans on hardest
("the cleanest possible case of a high rate that means nothing"). The instrument's own split says
**30 of its 82 masked calls wrapped a gate**, and `--samples` names them:
`inv quality.precommit 2>&1 | tail -5` and `python3 -m pytest … -q 2>&1 | tail -30`. The
characterisation was read off a call list `strip_heredoc` had already pruned — which is a sharper
version of the section's own thesis, not a refutation of it: the punchline that a reader ranking by
headline number ranks backwards on consequence survives, and the highest rate in the table is still
the row whose greens all held.

**"Rejected 1 — a second column" was killed by a sample-8 reading the instrument does not
reproduce.** The section says that session "is 99% listings and the 1% is the part a reader needs",
and its table row says "listings throughout, **one** masked gate run, five green claims". Re-scored
at that row's recorded boundary (`--until 2026-09-04T11:57:51+03:00`) the split is **16 gate, 23
listing** over 220 calls, and the corpus records **ten** green claims for it, not five. Whole
transcript it is 269 calls, 15%, 16 gate / 25 listing — so no window makes it 25%, one gate run, or
five claims. Something else produced that row and it is not obvious what.

The adopted design is probably unaffected: two counts would print `39 masked, 16 wrapped a gate` for
sample 8, which is a useful line either way. What is affected is the stated **reason** the second
column was rejected, since the extreme case it rests on may not exist.

## Evidence

Reproduce with `agent-skills`' own script at `95f8af7`, one call per row:

```shell
audit.py --session 13aa58df-3551-49b7-ac0e-0c3693bf8221 --until 2026-09-02T20:32:51+03:00 --samples 0
audit.py --session 7dab6dae-7c67-454f-bba1-981fe3845089 --until 2026-09-03T13:47:32+03:00 --samples 0
audit.py --session 92f54986-8a19-49a4-b792-8ebb1d5fcf1a --until 2026-09-04T11:57:51+03:00 --samples 0
audit.py --session 6291d9d1-b8ed-4826-9967-9ae30f70bebf --until 2026-09-05T10:21:37Z --samples 0
```

Those transcripts expire around 2026-10-02, so the check is cheap now and impossible later.

The applied re-score, the floor annotation on every uncorrected row, and the instrument-commit
convention are in `power-user-linux-setup`'s
`plans/2026-09-02-agents-md-adherence-sample-corpus.md`, commits `faceb15` and `0e61d2b`. The plan
that decided it was retired in the same pass; `plans.py archive --search heredoc` reads it back.

No user correction prompted this. It came out of applying the re-score decision and checking, per
its own step 3, what the corrected rate does to the arguments built on it — one of which lives in
this repo. Distinctive phrase from the applying session: "the mitigation this row was famous for was
an artefact of the bug".

## Open questions

[NEEDS CLARIFICATION: **is the migrated table worth correcting in place, or annotating?** In place
keeps one set of numbers in the file, and the pre-fix figures then survive only in git history. An
annotation preserves what the decision was actually taken on, which is the honest record of a design
argument — and this file's own `PITFALL` next door already models that shape.]

[NEEDS CLARIFICATION: **where did sample 8's row come from?** 25%, one masked gate run and five
green claims match no window of that transcript. Worth resolving before the "99% listings" reasoning
is cited again, since it is the only evidence offered against the second-column design.]

## Recommended direction

Correct or annotate the four cells, and keep the section's conclusions — they survive the re-score
and one of them is strengthened by it. Then decide what to do about the sample 8 row, which is the
only part where a number cannot be traced to a run.
