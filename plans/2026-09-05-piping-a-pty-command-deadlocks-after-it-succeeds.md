---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/ingesta
source_moment: 2026-09-05T20:45:00Z
source_session: 51a36fd5-b684-4cfb-8848-a1a5937b294c.jsonl
---

# Piping a pty-allocating command through `tail` hangs it after the work is done

## Context

`session-bash-audit` counts `head/tail` as an output-truncation pattern and the rule against it is
about **losing** output — the harness already truncates, so pre-truncating only discards data and
forces a second run. This is a second, worse failure of the same shape, and the counter would score
it identically to a harmless `| tail -3`.

Filed from an `ingesta` session that ran `inv web.parity 2>&1 | tail -16` and lost **1.7 hours of
wall clock** to it.

## Evidence

`inv web.parity` shells out with `invoke`'s `c.run(..., pty=True)`. Piped to `tail`:

- The command was moved to the background at the harness's 420s timeout.
- At 6235 s the `inv` process was still alive, `stat Sl`, **0 seconds of CPU time**, and had **no
  children** — the child that does the work had already exited.
- The output file was **0 bytes**, because `tail` emits nothing until EOF.
- An `until grep -qE 'all agree|disagree|Error'` waiter over that file could therefore never fire —
  a loop that cannot succeed, which is the exact shape `~/AGENTS.md` already warns about, reached
  from a direction that rule does not describe.
- `kill` on the `inv` pid made `tail` flush, and the buffered output read:
  `done — 9 cases, all agree`.

**The work had succeeded. Only the reporting of it was hung.** The 143 exit was the SIGTERM, so the
run also _looks_ failed in the transcript, which is the opposite of what happened.

## Findings

[PITFALL: **This is not the documented `head`/`tail` hazard, and reasoning from that one gets it
wrong.** The documented cost is lost output on a command that finishes. Here the command finishes,
the output is lost _and_ the parent never exits — so the session sits waiting on something already
done, and every diagnostic reads as "still running". The tell is the combination: alive, `Sl`,
**zero CPU time**, no children. A process genuinely working has CPU time; this one had none, and
that is what separates a deadlock from a slow run in one command.]

[PITFALL: **`pty=True` is why, and the caller cannot see it.** Whether a task allocates a pty is a
property of the task's own source — `invoke`'s `run(..., pty=True)`, and this repository's `tasks/`
use it throughout for coloured output. Nothing at the call site says so. So "is it safe to pipe this
command" cannot be answered from the command line being typed, which makes the blanket rule (do not
pipe a gate or a long-running task) more right than it first appears rather than merely tidy.]

[DECISION: **The remedy is the one already in `~/AGENTS.md`, and this is a second reason for it.**
Run it plain, or redirect to a file and read the file as a separate call:
`inv web.parity > log 2>&1` then `Read`/`rg` on the log. A redirect does not deadlock, keeps the
exit code, and leaves the output complete. The existing rule ends on "the harness already truncates
and saves the full text", which is a _convenience_ argument; this adds a correctness one.]

## Open questions

[NEEDS CLARIFICATION: **should `audit.py` score a piped pty-allocating command separately?** It
cannot know about `pty=True` from the command string, but it could special-case the shapes that are
nearly always pty-allocating in these repos — `inv <task> … | head/tail` — and report them apart
from `somecmd | tail -3`. The argument for: the two have different costs and lumping them hides the
expensive one. The argument against: it is a repo-specific heuristic in a machine-wide counter, and
the existing `head/tail` rate already catches every instance, just without ranking them.

A cheaper alternative that needs no new counter: name this failure in the skill's
`references/research.md` under the `head/tail` pattern, so the next reader of that rate knows the
worst case rather than only the common one.]

## Recommended direction

1. **Record the failure where the `head/tail` pattern is explained** — the rate is already measured
   and does not need changing; what is missing is that its worst case is a hang rather than a
   truncation.
2. **Decide the counter question above** only if a second instance appears. One session losing 1.7
   hours is a story; two is a rate.
