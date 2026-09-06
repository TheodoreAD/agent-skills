---
status: in-progress
updated: 2026-09-06
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

[DECISION: **no split — the harvest asks the shell, 2026-09-06.** The split is not merely the more
expensive option, it is **not derivable at all**: a transcript records the command and the result,
and nothing about the shell that ran it. `audit.py` cannot tell "this shell would have hidden it"
from "`PIPE_FAIL` carried it" for any call, on any machine, and a per-date heuristic would be a
guess dressed as a measurement — worse in a skill that ships to strangers whose machines have no
such snippet at all.

So the counter stays whole and the question moves to where the answer exists: the session's own
shell. `session-harvest` step 5 now runs `setopt | rg pipefail` (`set -o | rg pipefail` under bash)
as a Bash call before re-running anything, and skips the re-run when the option is in force —
`cmd_claims` prints the same instruction with its own output. Two conditions are stated with it,
because both are ways the check could be misread: **ask the shell, not a config file** (the option
is guarded on `CLAUDECODE` here, so the answer differs between an agent's shell and any other on the
same box), and **the guarantee covers the exit code only** — `| head -20` still discards output, so
a claim resting on reading the gate's output is still unverified.]

[DECISION: **the name stays `exit-masked`, since nothing splits.** Recorded rather than dropped
because the reasoning outlives the question: renaming a counter invalidates every stored baseline
carrying the old key, and this row's name is now doing the job the plan worried about — it describes
the **shape**, and the consequence is read from the shell rather than from the name. The row is also
deliberately absent from `EXPECTATIONS`, which is the same decision one level up: a verdict computed
from a transcript cannot know which shell ran the command, so it would be a confident number
standing on an assumption. `head/tail` scores the habit instead, from output loss, which holds
everywhere.]

[PITFALL: **do not simply retire the counter.** The guard is `CLAUDECODE`, so the same piped command
is still status-losing in cron, in CI, in a devcontainer, on any machine this repo has not set up,
and in any harness that is not Claude Code. A session that learns the shape is harmless here writes
it into a script that runs somewhere else. The measurement stays; what has changed is what it
licenses anyone to conclude about _this_ session's own claims.]

## What landed, 2026-09-06

1. ~~Decide the split-or-check question~~ — decided above: check, because the split is not
   derivable. `session-harvest`'s step 5 and `harvest.py`'s `claims` footer both ask the shell first
   and skip the re-run when `pipefail` is in force, which is the cost this plan was filed about.
2. ~~Say in `session-bash-audit` that the counter's consequence is machine-dependent~~ — `SKILL.md`
   carries it as a declared limitation beside the worktree and Windows ones, the `PATTERNS` row's
   own "why" names the check, and `EXPECTATIONS` carries the reason the row is unjudged. A test pins
   that last one, so the absence reads as a decision rather than an oversight.
3. `power-user-linux-setup`'s corpus plan states the general form — `exit-masked` measures a hazard
   rather than a defect rate — and the wording here now agrees with it in those words.

**Verified 2026-09-06, same day, by the next harvest** — which was this session's own, so read it as
a smoke test rather than as an independent one. `claims` printed the new footer, the `setopt` check
ran as a Bash call and returned `pipefail`, and no gate was re-run. What the test did **not**
exercise is the branch that matters most: this session's masked calls were 4 listings and **zero
gates**, so the greens were never at risk and the pipefail answer decided nothing. That turned into
a skill change rather than a pass — step 5 now reads the gate/listing split first, since `m = 0` is
a shorter and stronger answer than any shell state. The pipefail branch itself still awaits a
session that actually pipes its gate.

One measurement worth keeping from the decision: `setopt | rg pipefail` returns `pipefail` in this
machine's agent shells today, confirmed 2026-09-06, and `~/.zshenv` sets it under
`if [ -n "${CLAUDECODE:-}" ]` — so a human's interactive shell on the same box does **not** have it,
which is exactly why the check has to run inside the session being audited.
