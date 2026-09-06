---
status: in-progress
updated: 2026-09-06
---

# `strip_heredoc` truncates the command, not the heredoc body — every pattern under-counts

## Context

Found 2026-09-06 while checking why `session-harvest`'s `claims` and `session-bash-audit`'s
`exit-masked` disagree on the same-named counter. They do disagree, and the reason is not the one it
looked like: `audit.py` is the instrument that is wrong, and it is wrong in the direction that
flatters every rate this corpus publishes.

`audit.py`'s `strip_heredoc` exists so a heredoc's body cannot look like chained commands. It cuts
at the marker and returns everything before it:

```python
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?[A-Za-z_]+['\"]?")


def strip_heredoc(cmd: str) -> str:
    """Drop heredoc bodies so their content can't look like chained commands."""
    m = HEREDOC_RE.search(cmd)
    return cmd[: m.start()] if m else cmd
```

**It never resumes after the terminator**, so it drops the body _and every command that follows it_.
The shape that loses is the ordinary one — a heredoc that edits a file, then the gate run:

```
python3 - <<'PY'
...
PY
inv quality.precommit 2>&1 | tail -30
```

`strip_heredoc` hands the patterns `python3 -`, so the masked gate run at the end is invisible to
`exit-masked`, `head/tail`, `chain`, and everything else in `PATTERNS`. `strip_quoted` and
`split_chain` both build on it, so the loss is uniform across the table rather than local to one
row.

## The measurement

Over 7 days of transcripts, 15,415 Bash calls, 1,563 of them carrying a heredoc. Re-tagging with the
body dropped but the tail kept:

| tag             | hits lost |
| --------------- | --------: |
| `head/tail`     |       437 |
| `exit-masked`   |       381 |
| `grep/find`     |       218 |
| `search\|head`  |       105 |
| `git-mutating`  |        38 |
| everything else |        88 |
| **total**       | **1,267** |

across 30 sessions. Corpus-wide the rates move `head/tail` 25.0% → 27.8% and `exit-masked` 15.3% →
17.8%, which understates it: the calls are concentrated in the sessions that write patch scripts, so
per session the correction is an order of magnitude larger.

| session    |   n | `exit-masked` now | with the tail kept |
| ---------- | --: | ----------------: | -----------------: |
| `db8eccf5` | 425 |               20% |            **32%** |
| `f489b075` | 361 |               26% |            **39%** |
| `492bc6a2` | 324 |               17% |            **28%** |
| `5c8ee566` | 307 |               14% |            **25%** |
| `13aa58df` | 252 |               27% |            **37%** |

[PITFALL: **the last row is sample 6 of the published adherence corpus**, cited by
`2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` and recorded in
`power-user-linux-setup`'s `plans/2026-09-02-agents-md-adherence-sample-corpus.md` at 27%. Its real
rate is 37%. That sample is the one the gate-versus-listing argument leans on hardest — "the
cleanest possible case of a high rate that means nothing" — so a correction to it is a correction to
the reasoning built on it, not just to a cell. Any row of that corpus taken from a session that
wrote patch heredocs is understated by the same mechanism.]

The two instruments' disagreement, which is what surfaced this: `harvest.py`'s `EXIT_MASKED_RE`
matches the raw command, so it sees these calls and `audit.py` does not. Of 390 calls in the week
that `harvest` tags and `audit` does not, **388 are this bug** and 2 are genuine quoted mentions —
`audit.py`'s deliberate `strip_quoted` behaviour, which is the half it gets right. So the honest
summary is that neither matcher is correct: `harvest` counts quoted prose, `audit` drops real
commands, and `audit`'s error is the larger by two orders of magnitude.

## Open questions

[DECISION: **the shell's own rule, strict for plain `<<`.** `<<-WORD` tolerates leading whitespace
on the closing line, plain `<<WORD` requires the word alone at column 0. The probe's loose
`^\s*WORD\s*$` would resume inside a body whose own text is the delimiter, and body text re-entering
the table is precisely the false positive `strip_quoted` exists to prevent — so the looser of the
two errors is the one that costs a wrong number rather than a missed one. `<<-` strips tabs in
POSIX; the implementation allows spaces too, which is the one place it stays crude.]

[DECISION: **an unterminated heredoc keeps cutting to the end**, and the corpus says the case barely
exists: **1 of 1,569 heredoc calls** in the 7 days to 2026-09-06 never closed, and it was not a
heredoc at all — a `<<<` here-string inside a quoted `rg` pattern. That is now excluded by a
lookaround, since a here-string is one line of stdin with no terminator to find; quoting was no
defence, because `strip_heredoc` runs before `strip_quoted`. So the unterminated branch is
unreachable in a week of real transcripts and is kept for the truncated-entry case rather than for
an observed one.]

[NEEDS CLARIFICATION: **does the corpus get re-scored, or annotated?** Three of the seven sample
transcripts expire around 2026-10-02, so a re-score is possible now and not later. Re-scoring
changes published numbers in another repo's plan; annotating leaves them wrong but traceable. This
plan can only fix the instrument — the corpus lives in `power-user-linux-setup` and is that repo's
to change, per the cross-repo rule.]

## What landed, 2026-09-06

`strip_heredoc` drops the body and resumes after the terminator; `HEREDOC_RE` captures the delimiter
word (digits included, so `<<PY2` finds its own terminator rather than looking for `PY`) and
excludes `<<<`. Five tests in `tests/unit/test_audit.py`, four of them confirmed failing against the
previous script — the gate run after a heredoc, two heredocs in one call, the `<<-` indented
terminator, and the here-string. The fifth guards a property that did **not** change (unterminated
cuts to the end), which is why it passes either way and is labelled as such.

**Step 2's check held exactly.** Re-measuring with the implementation rather than the probe: 1,267
newly-visible hits across 30 sessions, the same per-row counts, `head/tail` 25.0% -> 27.8% and
`exit-masked` 15.3% -> 17.8%. Nothing the old patterns tagged went untagged except the single
here-string's false `heredoc`. The probe and the implementation agreeing is the check that neither
invented the number.

`references/research.md` carries the dated finding, including the caveat that a baseline saved
before this fix cannot be compared with one saved after — the rates moved by the size of a real
regression, because the instrument changed and no session did.

## What is left

1. **The corpus question above** is the one open `NEEDS CLARIFICATION`, and it cannot be answered
   from here: the corpus lives in `power-user-linux-setup` and is that repo's to change. **Filed
   there 2026-09-06** as `2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md` — in
   the store mirror, not that repo's tree, commit `3186660` in `~/plans`. It carries the affected
   rows, the re-score-versus-annotate question, and the deadline: three of the seven sample
   transcripts expire around 2026-10-02, sample 6's among them. Nothing further to do from this
   repo.
2. `harvest.py`'s `EXIT_MASKED_RE` keeps its own defect — it counts quoted mentions, the two the
   week's divergence turned up. Fixing it means sharing `strip_quoted`/`strip_heredoc` across two
   skills that install independently and cannot import each other, which is
   `2026-09-03-skill-dependencies-and-bundling.md`'s question rather than this one's. Until then the
   divergence is worth stating in both skills, so a reader comparing the two numbers knows why they
   differ.
