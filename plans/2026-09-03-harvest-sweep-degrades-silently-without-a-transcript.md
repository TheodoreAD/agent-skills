---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-03T10:16:02+03:00
---

# `harvest.py sweep` reports a clean, incomplete sweep when no transcript resolves

## Context

`SKILL.md`'s command block, and the design plan that specified the script
(`plans/2026-09-02-session-harvest-mechanical-half-becomes-a-script.md`, lines 79–80), both show the
subcommands invoked bare after a one-off `transcript` call:

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

## Open questions

[NEEDS CLARIFICATION: **persist the resolution, or make `sweep` refuse?** Persisting (the
`transcript` call writes the resolved path somewhere the later subcommands read) matches what
`SKILL.md` and the design plan already describe, and keeps the documented command block honest.
Refusing is smaller, needs no state, and follows the script's own principle that nothing should
report a clean result it did not measure — but it makes the documented bare invocations an error
that every run has to route around. A third option is both: refuse by default, with the resolution
cached so the bare form usually works.]

[NEEDS CLARIFICATION: **are there other silent degradations of the same shape?** `sweep` is the
subcommand with the most inputs, so it is the most likely, but the question is whether any other
subcommand answers with data it does not have when an input is missing. Worth one pass over the
script asking, per section, "what does this print when its source is empty — a finding, or a
falsely-clean one?"]

## Recommended direction

1. Fix the reporting first, whichever mechanism wins: **no section may print a definite answer from
   an input it does not have.** `surviving children: 0` becomes `unknown — no transcript`, and the
   sections that cannot run say they did not run. That is correct under either resolution.
2. Then decide persistence versus refusal, and make `SKILL.md`'s command block match whichever wins
   — the block currently documents an invocation that silently under-reports.
3. Add a test that runs `sweep` with no resolvable transcript and asserts the output contains no
   definite per-session claim. It is the shape a unit test can hold and prose cannot.
