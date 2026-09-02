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

Two candidate causes were offered and this session could not distinguish them: that the checkout's
`audit.py` was uncommitted-modified so the installed copy predated whatever emits the comparison, or
that the flag expects something about the baseline's shape this baseline no longer satisfies.

[DECISION: **neither. The comparison printed; `| head -12` cut it off.** Settled 2026-09-02 from the
transcript itself, which stores the command as issued:

```shell
python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --session bf19d40e… \
  --until 2026-09-02T03:05:26+03:00 --compare …/2026-08-24-auto-mode.json 2>&1 | head -12
```

`report_session` printed the rates line, the "compare with `--compare`" hint and then the sample
blocks; the comparison came after all of it. Twelve lines reach the fourth sample block. Reproduced
exactly, then re-run unpiped: `9/11 expectations met`, `head/tail=45%(+14pp,MISS)`,
`heredoc=19%(+3pp,MISS)` — the same figures the session had reconstructed by hand, so the
reconstruction was right and only its account of why was wrong.

The finding and its cause arrived in one run: the session measured **45% `head/tail`**, and the
truncation habit the audit exists to measure is what hid the audit's own verdict. It is also the
cheaper half of section 1's lesson — an inferred cause written as fact, published in a filed plan,
and disprovable in one grep of the transcript.]

## What landed, 2026-09-02

Two changes in `session-bash-audit`, both from the section above.

`audit.py` now prints the baseline comparison **above** the sample blocks in both modes — the
one-block verdict ahead of the dozens of lines of bulk — so a truncated run loses the samples rather
than the answer. `main` passes `--compare` into `report` instead of calling `compare` after it.

`SKILL.md` gains a `[PITFALL:]` on the `--session` mode saying to run it unpiped in every mode, with
this incident as its evidence, and stating that the reordering is a second line of defence rather
than permission to pipe.

What the plan asked for — "if `--compare` prints no comparison, read the baseline's own JSON and
state the deltas" — is deliberately **not** written down. It is a workaround for a failure that
cannot happen unpiped, and a step telling a harvest what to do when the comparison is missing would
have made the truncation survivable instead of visible.
