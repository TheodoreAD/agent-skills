---
status: landed
updated: 2026-09-07
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

[PITFALL: **the last row is sample 6 of the published adherence corpus**, recorded in
`power-user-linux-setup`'s `plans/2026-09-02-agents-md-adherence-sample-corpus.md` at 27% and cited
by the gate-versus-listing argument, now in `skills/session-bash-audit/references/research.md` under
"One rate over two outcomes". Its real rate is 37% over the whole transcript and **38% at the row's
own `--until` boundary**, which is the figure that corrects the cell — see the 2026-09-07 decision
below. That sample is the one the argument leans on hardest — "the cleanest possible case of a high
rate that means nothing" — so a correction to it is a correction to the reasoning built on it, not
just to a cell. Any row of that corpus taken from a session that wrote patch heredocs is understated
by the same mechanism.]

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

[DECISION: **re-score the rows whose boundary is recorded, annotate the rest — settled with the user
2026-09-07.** The question was filed as re-score-versus-annotate for the whole corpus and the
measurement split it: the corpus's rows are `--until` measurements and **only three of the twelve
record the boundary they used**, so only those three can be re-scored into the same denominator. Run
at their recorded boundaries the calls column reproduces exactly — 216, 129, 228 — and `exit-masked`
moves 27% → 38%, 22% → 28%, 7% → 12%. The rest are annotated as floors rather than re-measured,
because a whole-transcript re-score changes the denominator silently: sample 1 comes out at 384
calls against the row's 331 and its rate **falls** 19% → 18%, an improvement no session made, after
a fix that can only raise the count.

Also settled by measurement: **nothing has expired yet.** All eleven recorded transcripts were on
disk 2026-09-07; row 4's id was never written down, so it is the one row no deadline threatens and
none can fix. The corpus is `power-user-linux-setup`'s file, so the decision and the three re-scored
rows were **filed there**, not applied —
`2026-09-07-adherence-corpus-rescore-decision-and-boundary-numbers.md`, store commit `2829651`.]

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

1. ~~The corpus question~~ — **decided with the user 2026-09-07 and filed for the repo that owns the
   corpus**, per the DECISION above. The first filing (`3186660`, since absorbed into that repo)
   carried the question; the second (`2829651`) carries the answer, the three boundary re-scores and
   the transcript-availability check. Nothing further to do from this repo, and this time that is
   because the work is done rather than because it could not start.
2. `harvest.py`'s `EXIT_MASKED_RE` keeps its own defect — it counts quoted mentions, the two the
   week's divergence turned up. Fixing it means sharing `strip_quoted`/`strip_heredoc` across two
   skills that install independently and cannot import each other, which is
   `2026-09-03-skill-dependencies-and-bundling.md`'s question rather than this one's. Until then the
   divergence is worth stating in both skills, so a reader comparing the two numbers knows why they
   differ.

   **Instance, 2026-09-06**, from the harvest of the session that made the fix: `claims` reported
   **7** masked calls and `audit.py` **4**, over the same transcript at the same moment. The three
   extra were all `2>&1` inside a `python3 - <<'PY'` probe body — the heredoc half of the divergence
   rather than the quoted half, which is the commoner one in practice and was not what the original
   pair of examples showed. Small and harmless here, and it is the shape that makes a reader trust
   whichever number they saw first.

   **Stated in both skills 2026-09-07**, which is all this repo owed: `session-bash-audit`'s
   `SKILL.md` beside the `exit-masked` limitation and `session-harvest`'s step 5 beside the
   gate/listing split, each saying which direction its own number errs in and that neither is the
   other's check.

## Migrated to

- **The behaviour** — `skills/session-bash-audit/scripts/audit.py`: `strip_heredoc` resuming after
  the terminator, `HEREDOC_RE` capturing the delimiter word and excluding `<<<`, with five tests in
  `tests/unit/test_audit.py` (four confirmed failing against the previous script).
- **The reasoning** — that skill's `references/research.md`, "A heredoc hid every command that
  followed it (2026-09-06)": the 1,267 newly-visible hits, the strict-versus-loose terminator
  decision, the single unterminated call in a week, the two-instruments-over-one-corpus lesson, and
  the pitfall that a baseline saved before the fix cannot be compared with one saved after. Extended
  2026-09-07 with the boundary pitfall — a re-score needs the row's own `--until`, or the
  denominator moves and a corrected row can read as an improvement.
- **The divergence between the two instruments** — stated in both `SKILL.md`s (`session-bash-audit`
  beside the `exit-masked` limitation, `session-harvest` in step 5), each naming the direction its
  own number errs in and saying neither is the other's check.
- **The corpus decision and its numbers** — filed for the repo that owns them,
  `2026-09-07-adherence-corpus-rescore-decision-and-boundary-numbers.md`, store commit `2829651`.

Not migrated: the per-session before/after table, whose value was making the case for the fix that
has since landed — the corpus-wide figures and the one published row that was wrong are in
`research.md`, and the other four sessions are not cited anywhere. Nor the earlier filing's text: it
was absorbed into `power-user-linux-setup` and is that repo's file now.
