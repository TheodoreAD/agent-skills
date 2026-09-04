---
status: planned
updated: 2026-09-05
---

# A piped gate that cannot lie: fix the shell, the gate and the scripts, not the sentence

## Context

`2026-09-04-session-rule-adherence-evidence.md` asked whether the fix for the `head`/`tail` rule is
a rule at all. This plan is the answer worked out: **no**. The rule has been reworded four times
since 2026-08-24, every change was measured afterwards, none moved the rate, and the last sample in
the evidence plan complied with one Bash rule by adopting a second banned form within the hour. The
watch in `power-user-linux-setup` has said "adherence, not wording" since its session 5, and its
newest wording change (deployed 2026-09-04 14:26) has four sessions after it at 50%, 6%, 15% and 25%
— inside the spread sessions already had before it.

The user's framing of the cost, 2026-09-05: _"it's disruptive and can lie about a lot of things."_
Both halves are measured, over the seven days to 2026-09-05 (60 main sessions, 14,611 Bash calls,
`session-bash-audit --days 7 --json` plus two one-off scripts over the dump):

| what                                            | count              |
| ----------------------------------------------- | ------------------ |
| calls with a pipe                               | 6,080 (41%)        |
| … whose last stage is `tail`                    | 2,109              |
| … whose last stage is `head`                    | 1,966              |
| calls tagged `exit-masked`                      | 2,646              |
| `inv quality.*` runs                            | 1,396              |
| … piped through `head`/`tail`                   | **812 (58%)**      |
| … per repo (skills / ingesta / tasks / setup)   | 65 / 64 / 58 / 41% |
| `tail -N` on a gate, N=3..8                     | 466 of 812         |
| re-runs after a truncated first run             | 244                |
| share of `exit-masked` calls that were the gate | 31%                |

**The lie.** `<gate> 2>&1 \| tail -N` returns `tail`'s exit status, which is 0 whatever the gate
did. Every green claim followed to the end so far held (17 + 6 + 3 + 3 claims across four samples),
and one real regression across three repos went unread for a stretch of a session because every
check was `| tail`-ed (`session-bash-audit/references/research.md`, "Reading a command's result").
The claims were true by luck of the run and unevidenced when made.

**The disruption.** 244 re-runs a week of a command whose first run was truncated, and the user
rejecting piped gate runs by hand at the prompt (the denied list has `inv web.parity 2>&1 | tail -4`
and `uv run pytest … | tail -20`, both "user doesn't want to proceed").

**Why no sentence will fix it.** Three findings from the corpus, taken together:

- Rules about _never typing a token_ hold once the token has nothing left to buy: `echo "EXIT=$?"`
  went from 10–11% to 0% the day the rule said the tool already reports the exit code, and own-repo
  `cd` went from 114 to ~0. Rules about _how to compose a call_ do not hold — `| tail` still buys
  something (the verdict line, and ~800 tokens of context per gate run kept out).
- The pull is mostly volume — 466 of 812 piped gate runs asked for the last 3 to 8 lines of a
  ~50-line output, i.e. the pytest summary — but not only volume: `plans.py set-status … | tail`
  occurred 31 times on a command that prints one line. Part of the reflex is pre-emptive, so no
  single lever reaches all of it.
- The mechanism that fires behind the agent's back (a hook that rewrites or blocks the command) is
  refused on principle, and the principle held when re-measured 2026-09-02.

So the design below never asks the model to do anything. It changes what the shell reports, what the
gate prints, and what the scripts do when cut — so the wrong command stops lying, and the right
command stops costing anything.

## Design — four independent layers

### 1. `pipefail` in the agent's shell — the exit code survives the pipe

**Mechanism, read from the live harness 2026-09-05.** Every Bash call is
`/usr/bin/zsh -c 'source ~/.claude/shell-snapshots/<snapshot>.sh … && setopt NO_EXTENDED_GLOB
NO_BARE_GLOB_QUAL … && eval '<cmd>''`.
No `-f`, `norcs` is not set, `login` is — so `~/.zshenv` and `~/.zprofile` are read on every call,
before the snapshot. The snapshot ends with an explicit `setopt <name>` per option captured from the
interactive shell (22 lines), which only adds options; nothing unsets. `PIPE_FAIL` is not among them
today. A `setopt PIPE_FAIL` in `~/.zshenv`, guarded on the harness's own marker (`CLAUDECODE=1` is
exported into every call), reaches every Bash call and no human shell.

**Probed under `setopt PIPE_FAIL`, same machine, same day** (`pipefail-probe.zsh` in the session
scratchpad; the shapes are the ones the dump shows agents typing):

| pipeline                                      | exit under pipefail | today         |
| --------------------------------------------- | ------------------- | ------------- |
| `(exit 3) \| tail -1`                         | **3**               | 0             |
| `pytest <missing file> -q 2>&1 \| tail -1`    | **4**               | 0             |
| `python -c 'print(); exit(4)' \| tail -1`     | **4**               | 0             |
| `inv quality.lint-check 2>&1 \| tail -1`      | 0                   | 0             |
| `rg … \| tail -1`, `git log \| tail -1`       | 0                   | 0             |
| `git log \| head -1`, `ls -R \| head -1`      | 141                 | 0             |
| `cat file \| head -1`, `seq \| head -1`       | 141                 | 0             |
| `rg … \| head -1` (more matches than shown)   | 1                   | 0             |
| `python … \| head -1` (more lines than shown) | 120 + traceback     | 0 + traceback |
| `fd … \| head -1`                             | 0                   | 0             |

Every `| tail` carries the upstream code — the 2,109 `tail` calls a week stop lying at once, the
gate included. Every `| head` that actually cut something returns non-zero (SIGPIPE's 141, `rg`'s 1,
Python's 120), and a `| head` that cut nothing returns 0. That is not noise: **it is the data-loss
event the rule has been trying to describe, reported by the tool that observed it**, in the one
channel the corpus says the model does read (the exit code, per the `echo-exit` finding). The Python
traceback is already there today — pipefail only changes the status.

Framing, so it passes the enforcement-mechanism rule rather than skirting it: a Bash-tool call is a
non-interactive script, and `set -o pipefail` is what every shell style guide and `shellcheck`
already ask of a script. It does not correct, rewrite or block anything the agent typed. It makes
the shell report what happened. Developers get the same treatment in their scripts.

Where it lives: a `zshenv` snippet on `[packages.claude-code]` in `power-user-linux-setup`'s
`setup.toml`, next to `claude_default_mode`, deployed by `inv zsh.configure`. Filed for that repo.

What it changes in `~/AGENTS.md` (same repo): "Reading a command's result" currently says "a pipe
masks the exit code" as the reason not to pipe. Under pipefail that sentence is false and the rule's
stated reason evaporates — which the audit's own routing table says is the case for _rewriting the
rule's source, not restating it louder_. The replacement is a fact, not a composition rule: a
non-zero exit after `| head` means `head` cut the output, so count first (`rg -c`, `wc -l`) or run
it whole. The `| tail` half of "Composing a Bash call" can shrink to its data-loss cost.

[PITFALL: **`| rg`/`| grep` as a last stage returns 1 on no match under pipefail** — grep's
documented status, but a session filtering a gate for `error` and seeing nothing has so far read
"exit 0, empty" as clean and would now see "exit 1, empty". 147 calls a week end in `rg`/`grep`.
Cheap to name in the fact rule; not a reason to hold the change.]

[UNVERIFIED: that the option survives into a live session end to end. The invocation line and the
snapshot's additive `setopt` list both say it does, and the probe ran under a bare `setopt` in a
child zsh, but no session has run with the `~/.zshenv` snippet deployed. First check after deploy:
`setopt` in a Bash call lists `pipefail`; then `(exit 3) | tail -1` reports exit 3 in the tool
result.]

### 2. A quiet gate whose last line is the verdict — nothing left to `tail` for

The gate is 58% piped machine-wide and the largest single `exit-masked` shape. Measured live in this
repo 2026-09-05: `inv quality.precommit` prints ~50 lines on success — every command echoed twice
(`fix` then `check`), zizmor's banner, `uv lock`'s resolution line, pytest's header and 25 lines of
dots — and the one line the session wants is the last. 466 of 812 piped gate runs asked for exactly
that tail.

The shape to adopt is `pre-commit run`'s, the tool this gate replaces: one line per step,
`ruff check . ……… ok (0.4s)`, output captured and printed only for a step that fails, and a final
verdict line —

```
quality.precommit: PASS  12 steps, 465 tests, 14.2s
quality.check:     FAIL  type_check exited 1 (output above)
```

Two properties matter more than the line count. The verdict is the **last line**, so a `| tail -3`
still shows the truth even where layer 1 is absent (CI logs, a machine without the snippet). And the
verdict names the failing step, so a red run's tail no longer looks like invoke's generic
"Encountered a bad command exit code" wrapped around whatever the step printed. A `--verbose` flag
(or an env var, since invoke pre-tasks take no arguments) restores full streaming for a human
watching a long step.

Where it lives: `repo_tasks/quality.py`, `c.run(…, hide=True, warn=True)` per step, the captured
output replayed on failure. Its module docstring's "every command is echoed so both a human and an
agent see exactly what ran" survives — the command line is still printed, only its success output is
folded. Filed for that repo. Applies to every consumer's gate and CI log at once.

### 3. This repo's own scripts: stop printing tracebacks when cut, and print less

- **SIGPIPE.** 318 `python … | head` calls a week; every one that cut output printed a
  `BrokenPipeError` traceback that reads as the script crashing. None of `plans.py`, `audit.py`,
  `fitness.py`, `harvest.py`, `trigger.py` handles it (`rg SIGPIPE skills/` is empty). One line at
  each entry point — `signal.signal(signal.SIGPIPE, signal.SIG_DFL)` — turns it into a clean 141,
  which under layer 1 is the honest "you cut this" and today is silence.
- **`plans.py` is 13% of all `head`/`tail` calls**: `scan | tail` 165, `list` 66, `new | tail` 41,
  `set-status | tail` 31, `archive | head` 28. `list --scope family` printed 30 KB in this session.
  Read what `scan` and `new` print on the common path before deciding; a one-line success and a
  bounded `list` default remove the volume half of the pull for the skill's own commands, and the
  `set-status` count is the pre-emptive half, which only layer 1 addresses.
- **`session-bash-audit`** is the instrument and has to change with the ground truth:
  - `exit-masked`'s "why" ("$? after a pipe is the filter's") becomes false on a machine with
    layer 1. Rename or re-describe it as `piped-gate` — still worth counting as the shape whose
    verdict came through a filter — and add a row that counts **truncation events** rather than
    shapes: a `| head` call whose result carries a non-zero exit. That is a number the audit has
    never had: how often data was actually lost, not how often it could have been.
  - Save a baseline the day layer 1 deploys and `--compare` a week later. The prediction to falsify:
    `head/tail` moves little (the reflex is partly pre-emptive), `exit-masked` no longer lies,
    re-runs after truncation fall.
  - `session-harvest`'s green-claim check keeps its column; under layer 1 a claim from a piped run
    is evidenced, and the column starts distinguishing evidenced from lucky.

### 4. What is not done

- No hook, no wrapper function for `tail`, no rewrite of the command. Same reason as 2026-08-24 and
  2026-09-02.
- No further rewording of the ban. The 2026-09-04 clause stays deployed and gets its measurement,
  which the watch's own `[UNVERIFIED:]` asks for; the expected verdict is "did not move it", and the
  watch should then record that as a finding and stop testing wording.
- Nothing asks the model to run gates plain. If it keeps piping, the pipe is harmless.

## Open questions

[DECISION: **layer 1 is scoped to the agent's shell** — guard on `CLAUDECODE`, not on
`[[ -o interactive ]]`. Settled 2026-09-05 with the user. The narrow form is harness plumbing and
provably reaches every Bash call; the broad form would also change exit statuses for cron, IDE task
runners and every `zsh -c` nobody audited. A second guard per harness is added as harnesses are.]

[DECISION: **the gate is quiet by default, with `--verbose` to stream.** Settled 2026-09-05 with the
user. Opt-in quiet would leave the 58% where it is, because the session that pipes is the one that
never reaches for a flag; the one cost, a human watching a long step see nothing until it ends, is
what the flag is for.]

[DECISION: **order 1, 3, 2**, all four layers adopted 2026-09-05 with the user. Layer 1 is one
snippet and reaches everything today; layer 3 is a one-line change per script plus the audit update;
layer 2 is a real change to a shared package. A baseline is saved after layer 1 lands and again
before layer 2, so each layer's effect is measured on its own rather than as one delta.]

## Files touched

- `power-user-linux-setup`: `setup.toml` (`[packages.claude-code]` gains a `zshenv` snippet),
  `config/agents-md/verification.md` and `bash.md` (the rule rewrite), the evidence page. Filed as
  `2026-09-05-pipefail-in-the-agent-shell.md` in that repo's store mirror.
- `repo-tasks`: `src/repo_tasks/quality.py`, its tests, `contributing/`. Filed as
  `2026-09-05-quiet-gate-with-a-verdict-line.md` in that repo's store mirror.
- Here: `skills/plan-docs/scripts/plans.py`, `skills/session-bash-audit/scripts/audit.py` and
  `references/research.md`, `skills/skill-fitness/scripts/*.py`,
  `skills/session-harvest/scripts/*.py` — SIGPIPE at each entry point, the `plans.py` output pass,
  the audit rows.

## Verification

- After layer 1 deploys: `setopt` in a Bash call lists `pipefail`; `(exit 3) | tail -1` reports exit
  3 in the tool result. Then `audit.py --save-baseline --note "pipefail live"`.
- After layer 3: `plans.py list --scope family | head -1` exits 141 with no traceback.
- A week after each of layers 1 and 2: `audit.py --days 7 --compare <that baseline>`; report the
  truncation-event row and the green-claim column, not only `head/tail`.
