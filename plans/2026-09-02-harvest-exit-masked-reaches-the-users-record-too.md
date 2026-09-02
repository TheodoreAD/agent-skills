---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/ingesta
source_session: bf19d40e-bb8f-4341-a396-77194e946991.jsonl
source_moment: 2026-09-02T03:05:26+03:00
---

# Two step-5 gaps `session-harvest` showed on a run that otherwise went well

Both found by executing step 5 as written, on a ten-hour `ingesta` session with `exit-masked` at
28%. Filed rather than edited because the session was not in this repo.

## 1. The `exit-masked` rule re-verifies the gate and forgets the user

**What the rule says:** if `exit-masked` is above zero, the session's own green results are
unverified, so re-run the gate before believing any of them. Followed exactly —
`inv quality.check > log 2>&1;` `echo $?` returned `0`, so the greens were real.

**What it does not say:** the session had already told the user "gate green" roughly **fifteen
times** during the conversation, each time on evidence that had been discarded by a `| tail`. The
re-run resolves whether the claims were _true_. It says nothing about the fact that they were
**asserted to a reader** on no evidence, and it gives no instruction for the case where the re-run
comes back non-zero — which is the case that matters, because then fifteen statements in the
transcript are wrong and the user acted on several of them.

**This skill already has the right shape for it one bullet away.** The git-state bullet says: of the
session's own unpushed commits, ask whether any corrects something already pushed, and report that
in "needs action now" rather than flat, because it is "a live inaccuracy with a reader". A
masked-exit green is the same thing aimed at the conversation instead of the remote — and the
conversation is the record the user is actually working from.

Suggested addition to that bullet, small and additive: when `exit-masked` is non-zero, count how
many times the session asserted a green result on a masked call, say so with the re-run's verdict
attached, and put it in "needs action now" if the re-run disagrees. The count is available from the
transcript, which the harvest is already reading.

## 2. `--compare` produced no comparison output, and the prescribed reading was silent about it

Step 5 prescribes:

```shell
audit.py --session … --until … --compare …/baselines/<baseline>.json
```

Run as written, against `2026-08-24-auto-mode.json`, the output was **identical to the run without
`--compare`** — the rates line, then the sample blocks, and no comparison, no `OK`/`MISS` column, no
`n/m expectations met` line. No error either.

The comparison had to be reconstructed by reading the baseline JSON by hand and diffing the numbers
mentally, which is what produced this run's `+14pp` / `+17pp` figures.

Two candidate causes and this session could not distinguish them:

- `skills/session-bash-audit/scripts/audit.py` was **uncommitted-modified in the checkout** at the
  time, so another session is mid-edit on that script; the installed copy is the committed version
  and may predate whatever emits the comparison.
- Or the flag expects something about the baseline's shape that this baseline no longer satisfies —
  the same-day sibling sample records `compare` having recently mis-scored tags absent from a
  baseline, so that code path has been moving.

Either way the step is worth a sentence: **if `--compare` prints no comparison, read the baseline's
own JSON and state the deltas** rather than reporting the bare rates, because a rates line with no
baseline beside it reads as a verdict and is not one. That is what the sibling sample's "9/11
expectations met" line looks like when it works, and its absence here was easy to miss.

[NEEDS CLARIFICATION: whether the silence is the script or the baseline. Cheap to settle from a
session in this repo — run the checkout's copy against the same baseline and compare with the
installed copy's output. Worth doing before another harvest quotes bare rates as a verdict.]
