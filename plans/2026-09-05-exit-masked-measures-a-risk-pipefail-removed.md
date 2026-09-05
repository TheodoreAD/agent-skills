---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: 25ea8788-b99d-43a2-9611-2d0c1f207694.jsonl
source_moment: 2026-09-05T19:00:00Z
---

# `exit-masked` counts a hazard `PIPE_FAIL` has removed, and the harvest still bills for it

## Context

`session-bash-audit`'s `exit-masked` counter and `session-harvest`'s step 5 both live here, and both
were written for a shell where a pipe returned its last stage's status. **That shell no longer
exists on this machine.** `power-user-linux-setup`'s `[packages.claude-code]` sets `PIPE_FAIL` in
every Bash call the harness makes, guarded on `CLAUDECODE`, so a pipeline now reports the rightmost
non-zero status — `inv quality.precommit 2>&1 | tail -3` fails when the gate fails.

The counter and the instruction have not moved with it, and neither is wrong on its own:

- **`exit-masked` still counts the shape.** A piped gate is still a piped gate, and counting it is
  still meaningful as a style measurement and as a portability one — the guard is `CLAUDECODE`, so
  the same command in cron, in CI or on a machine without this setup still loses the status.
- **`session-harvest` step 5 still reads a non-zero `exit-masked` as "this session's own green
  results are unverified"** and asks for an unpiped re-run of the gate. On this machine that re-run
  confirms something the shell already guarantees.

Together they cost a full gate re-run per harvest for a hazard that has been designed out, and the
counter's name asserts a risk it no longer measures.

## Evidence

Two independent samples, both post-deploy, both from `ingesta`:

- **233 calls, `exit-masked` 21%, ten green claims to the user, every one from a piped run.** The
  unpiped re-run exited 0; all ten held. Filed to `power-user-linux-setup` as
  `2026-09-05-piped-gate-rate-after-pipefail-one-session.md` and merged into
  `plans/2026-09-05-pipefail-in-the-agent-shell.md`, which is where the sample now lives.
- **228 calls, `exit-masked` 7%, nine green claims, all from piped runs.** Unpiped re-run exit 0,
  1020 passed. Now row 11 of `power-user-linux-setup`'s
  `plans/2026-09-02-agents-md-adherence-sample-corpus.md`.

That corpus's own conclusion, drawn from seven samples carrying a claims count: **every green held,
at masked rates from 7% to 32%, and it has yet to find a case where any of it was wrong.** The
counter measures how much of a session's evidence _could_ have been unsound. Post-`PIPE_FAIL`, on
this machine, it cannot be.

## Open questions

[NEEDS CLARIFICATION: whether `exit-masked` should **split** — "masked, and this shell would have
hidden it" against "masked, but `PIPE_FAIL` carries it" — or whether the harvest step should read
the shell's own state (`setopt | rg pipefail`) and skip the re-run when the guarantee is in force.
The split keeps one honest number per shape and makes the baseline comparison across the deploy
meaningful; the harvest check is one line and fixes the cost without touching the instrument. They
are not exclusive.]

[NEEDS CLARIFICATION: what the counter should be **called** if it splits. `exit-masked` asserts the
consequence, and the consequence is now conditional on the machine — a name that survives the
condition is worth a minute's thought, and renaming a counter invalidates every stored baseline that
carries the old key.]

[PITFALL: **do not simply retire the counter.** The guard is `CLAUDECODE`, so the same piped command
is still status-losing in cron, in CI, in a devcontainer, on any machine this repo has not set up,
and in any harness that is not Claude Code. A session that learns the shape is harmless here writes
it into a script that runs somewhere else. The measurement stays; what has changed is what it
licenses anyone to conclude about _this_ session's own claims.]

## Recommended direction

1. Decide the split-or-check question above; the harvest half is the one costing time today.
2. Whatever is decided, **say in `session-bash-audit` that the counter's consequence is
   machine-dependent** and name the guard, so the next reader of a high `exit-masked` does not
   re-derive this.
3. `power-user-linux-setup`'s corpus plan already states the general form — that `exit-masked`
   measures a hazard rather than a defect rate — and that sentence is the thing this repo's own
   wording should agree with rather than contradict.
