---
status: idea
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

[NEEDS CLARIFICATION: **which terminator rule?** A real heredoc ends at a line containing only the
delimiter (`<<-` also allows leading tabs). The probe used `^\s*<word>\s*$` under `re.MULTILINE`,
which is close enough to measure with but is looser than the shell's rule for the plain `<<` form
and does not handle a delimiter appearing inside the body's own quoted text. The script is "crude on
purpose — this is a habit audit, not a shell parser", so the question is how much of the real rule
to take.]

[NEEDS CLARIFICATION: **what happens to an unterminated heredoc?** The probe keeps the current
behaviour — cut everything from the marker — because a command whose heredoc never closes has no
meaningful tail. It is worth confirming that against the corpus rather than assuming; a truncated
transcript entry could produce one.]

[NEEDS CLARIFICATION: **does the corpus get re-scored, or annotated?** Three of the seven sample
transcripts expire around 2026-10-02, so a re-score is possible now and not later. Re-scoring
changes published numbers in another repo's plan; annotating leaves them wrong but traceable. This
plan can only fix the instrument — the corpus lives in `power-user-linux-setup` and is that repo's
to change, per the cross-repo rule.]

[UNVERIFIED: the fix itself. Everything above is measured with a probe written for the measurement,
not with a change to `audit.py`. The probe's numbers are the case for fixing it, not evidence that a
fix behaves.]

## Recommended direction

1. Fix `strip_heredoc` to resume after the terminator, with tests over the shapes the corpus
   actually contains: `python3 - <<'PY' … PY` followed by a gate run, two heredocs in one call, an
   unterminated one, and `<<-EOF` with tabs.
2. Re-run the 7-day measurement after the fix and confirm it reproduces the table above — the probe
   and the implementation agreeing is the check that neither invented the number.
3. Only then decide the corpus question, and file it to `power-user-linux-setup` rather than editing
   that repo's plan from here.
4. `harvest.py`'s `EXIT_MASKED_RE` keeps its own defect (it counts quoted mentions). Fixing it means
   sharing `strip_quoted`/`strip_heredoc` across two skills that install independently and cannot
   import each other — which is `2026-09-03-skill-dependencies-and-bundling.md`'s question, not this
   one's. Note the divergence in both skills' bodies meanwhile, so a reader comparing the two
   numbers knows why they differ.
