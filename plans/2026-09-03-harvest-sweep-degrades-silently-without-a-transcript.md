---
status: landed
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-03T10:16:02+03:00
---

# `harvest.py sweep` reports a clean, incomplete sweep when no transcript resolves

## Context

`SKILL.md`'s command block, and the now-retired design plan that specified the script
(`plans.py archive --show 2026-09-02-session-harvest-mechanical-half-becomes-a-script.md`, in its
proposed subcommand listing), both show the subcommands invoked bare after a one-off `transcript`
call:

```shell
python3 $H transcript --expect '<a command this session ran>'
python3 $H turns                       # step 4
python3 $H sweep --boundary <instant>  # step 5
```

**Nothing carries the resolution between them.** Each subcommand is its own process with no shared
state, so `turns`, `sweep` and `claims` each re-resolve from scratch and, in a session the automatic
resolution does not match, each gets nothing.

`turns` and `claims` handle that correctly — they exit with the documented error naming `--session`
and `--expect`. **`sweep` does not: it prints one comment line and carries on.**

## Evidence

Measured 2026-09-03, this repo, both runs minutes apart on the same session and the same boundary.

Bare (as `SKILL.md` shows it), the header read `# transcript: no transcript resolved …` and
`# session started: None`, and the body then reported:

- `this session's surviving children: 0` — **a claim it cannot make.** With no transcript there is
  no set of this session's children to be empty; the honest answer is "unknown", and `0` is
  indistinguishable from a clean result.
- **one repo** — the working directory's — where the resolved run covered **three**
  (`power-user-linux-setup`, `plans`, `agent-skills`), because the repo set comes from the
  transcript's own write paths.
- **no `CORRECTION?` lines at all.** The resolved run produced two, both true positives, one of them
  a comment correction the remote was already serving — precisely the finding `SKILL.md` routes into
  "needs action now".
- **no `paths this session wrote into files that do not exist` section**, which simply did not
  appear.

Same session, same boundary, same machine: the bare run's output is a subset that reads exactly like
a complete one.

[PITFALL: **this is the failure mode the skill's own step 0 is written against, one layer down.**
Step 0 exists because "a stale harvest is worse than no harvest, because its report reads
identical". A degraded sweep is the same defect in the same run — the section headers are all
present, every line under them is true, and the missing findings leave no gap a reader could notice.
The check that catches a stale skill does not catch a blind sweep.]

[PITFALL: **the neighbouring subcommands' correct behaviour hides it.** A run that calls `turns`
first gets a loud error, supplies `--session`, and never learns that `sweep` would have failed
quietly — because by then the habit of passing `--session` has been established by the subcommand
that insisted. This run hit it in the other order.]

## Resolved questions

[DECISION: **neither persistence nor refusal — automatic resolution, which landed first and made the
question moot.** Since 2026-09-05 `turns`, `sweep` and `claims` resolve the transcript from
`$CLAUDE_CODE_SESSION_ID`, which Claude Code exports into every Bash call and which is the
transcript's own filename stem. So the documented bare block is honest in an ordinary session, and
neither a cache nor an error was needed. What survives the change is the reporting half below, which
is what happens on a harness that exports no id — the case that used to be indistinguishable from a
clean run and is now the only case left.]

[DECISION: **the per-section pass was run 2026-09-08, and the shape was already handled in two of
the five places it could occur.** `stores` prints "no transcript: nothing here is attributable,
whatever the timestamps say", and `disk` carries a three-valued `images_attribution` that
distinguishes "this session ran docker" from "no transcript to check against". The three that did
not: the two loose-file checks, the repo set, and the process section. All three are fixed below,
and the two that were already right are the reason the fix took the shape it did rather than
inventing a convention.]

## What landed, 2026-09-08

The reporting rule, which is recommendation 1 and is correct whatever the resolution does:

- **Both loose-file checks always print a heading** — the findings, `none`, or
  `skipped: no transcript`. They used to be absent rather than empty, which is the whole defect: a
  section that is missing leaves no gap a reader can see. Two tests pin `none` and `skipped` apart,
  because a fix that printed only `skipped` would have left the resolved-but-empty run just as
  silent as before.
- **The header says when the repo set collapsed to the working directory**, which is the second
  bullet of the evidence above — the one-repo-against-three narrowing, now stated rather than
  inferred.
- **The process section stops printing `0` surviving children when no harness process is in its own
  ancestry.** This is a correction to this plan's own headline example: `session_children` is
  derived by walking the process tree, not from the transcript, so a transcript-less run's `0` is
  genuinely measured and the plan was wrong to call it a claim the sweep could not make. The
  unmeasured case is the narrower one — the listing ran and the harness walk found nothing — and
  that is what now prints `unknown`.

**Not done, and correctly so:** `SKILL.md`'s command block needed no change, because the invocation
it documents stopped under-reporting when automatic resolution landed. The skill body gained the
`none`-versus-`skipped` rule instead, next to the check it governs.

## Migrated to

- **`skills/session-harvest/references/rationale.md`**, "What the step-5 checks owed a reader, and
  what measuring them cost the plans" — retired with eight siblings as one finding: a check has to
  say what it did not measure, and each of the nine was a check that answered instead. That section
  also records what this plan's own recommendation cost when measured.
- **`skills/session-harvest/scripts/harvest.py`** and **`SKILL.md`** carry the mechanism and the
  incident, each beside the code or the bullet it governs.
- Not migrated: the bare-versus-resolved output comparison, which is a verification log. The
  headline example was wrong (see above) and the correction is kept rather than the example.
