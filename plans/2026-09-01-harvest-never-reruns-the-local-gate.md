---
status: landed
updated: 2026-09-02
source_repo: github.com-personal/ingesta
source_session: f489b075-6f46-4814-a71b-57f5879ef27e.jsonl
source_moment: 2026-08-31T18:41:11.778Z
---

# The harvest checks CI but never re-runs the repo's own gate

## Context

`session-harvest`'s live-state sweep checks CI for anything pushed, and it caught a real failure on
the run that filed this. But CI is the _second_ place the answer appears. The first is the repo's
own quality gate, which the session ran perhaps twenty times and read wrong every time — and the
sweep has no bullet that re-runs it.

The asymmetry is what makes this worth a check rather than a note: a session that pushes gets caught
by the CI bullet, and a session that does not push carries a false "gate green" into its own report,
into its commit messages, and into the next session's starting assumptions, with nothing in the
harvest looking at it. The failing case is the quieter one.

This is **adjacent to but not the same as**
`plans/2026-08-30-inferred-cause-published-before-audit.md`, which is about the truth of causal
claims written into files. This one is mechanical: a command was run, it exited non-zero, and its
result was misread because of how it was invoked. No inference involved.

## Evidence

- Transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/f489b075-6f46-4814-a71b-57f5879ef27e.jsonl`,
  session start `2026-08-31T18:41:11.778Z`.
- The session ran the gate as, verbatim and repeatedly:

  ```shell
  inv quality.precommit 2>&1 | grep -Ei "^error|failed|passed|All checks" | tail -3
  ```

  and read the absence of a match as success. `basedpyright` prints `0 errors, 6 warnings, 0 notes`
  and the gate exits **1** on a warning; the pipe reported `grep`'s exit code, so the string to
  search the transcript for is the session saying **"All checks passed!"** while the command it was
  quoting had failed.
- Confirmed by running it unpiped at harvest time — `EXIT=1` — and again after the fix, `EXIT=0`.
- Three commits reached `origin/main` red before anything noticed: `5629985`, `61d8d05`, `bffc9e9`.
  `gh run list --branch main` shows the transition precisely: green through `740c4e7`, failure from
  the first push carrying `src/ingesta/bot/middleware.py`.
- The session's own `~/AGENTS.md` states the rule it broke — "Clean-looking stdout is not proof of
  success — the exit code is… What loses it is a pipe" — and that file was in context throughout.
- The `session-bash-audit` run in the same harvest measured `exit-masked=28%` across 306 calls, so
  the behaviour was systematic rather than a slip. The audit **reports the rate but draws no
  conclusion from it**, which is the gap: 28% exit-masking is precisely the signal that the
  session's own green results need re-checking.

## Open questions

[NEEDS CLARIFICATION: whether this is its own bullet in step 5 or a consequence drawn from the
existing bash-audit bullet. The audit already produces the number that predicts the failure; the
cheapest version may be one sentence there — "an `exit-masked` rate above zero means this session's
own green results are unverified; re-run the gate unpiped" — rather than a new check that runs a
possibly slow gate on every harvest.]

[NEEDS CLARIFICATION: what to do when the gate is expensive. `inv quality.precommit` is ~20s here
and some repos' gates are minutes. If the rule is unconditional it will be skipped; if it is
conditional on the audit's `exit-masked` rate it is cheap and self-triggering, which argues for the
second shape.]

## Recommended direction

Prefer the conditional version, wired to the number the sweep already computes. Whichever shape, the
instruction should end on the command that replaces the habit —
`inv quality.check > log 2>&1; echo
$?`, then read the log — because the prose warning against pipes
demonstrably did not work on a session that had it in context.

## Outcome, 2026-09-02

Landed as the conditional version the plan recommended, and as a sentence on the existing bash-audit
bullet rather than a new check — which answers both open questions at once.

- **Own bullet, or a consequence of the audit bullet?** The latter. The audit already produces the
  number that predicts the failure, and the gap was never a missing measurement — it was that the
  run measured `exit-masked` at 28% and drew no conclusion from it.
- **What to do when the gate is expensive.** Conditional on that rate, so it is self-triggering: a
  zero costs nothing, and a non-zero is precisely the evidence that this session's own green results
  need re-checking. An unconditional rule would have been skipped on the repos whose gates take
  minutes, which is where it matters most.

The instruction ends on the command that replaces the habit, as the plan asked, because the prose
warning against pipes demonstrably did not work on a session that had it in context.

## Migrated to

- `skills/session-harvest/SKILL.md`, step 5, on the adherence bullet — the rule, the 2026-08-31
  incident that produced it (three red commits pushed behind a `grep`/`tail` pipe reporting the
  filter's exit code), and the unpiped re-run command.

The plan's distinction from `2026-08-30-inferred-cause-published-before-audit.md` needed no
migrating: that plan is about the truth of causal claims, this one about a misread exit code, and
both stay separate as this plan's Context argued.
