---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Two things a `session-harvest` run in another repo could not do as written

## Context

Filed rather than edited straight into `SKILL.md`, which is the second finding below.

Found 2026-08-30 by a harvest run from a `repo-tasks` session that had spent its whole length inside
`plan-docs`' retirement procedure.

### 1. Step 0's mid-session check over-fires on `references/` and `scripts/`

Step 0 asks whether a skill this run leans on moved after the session began, comparing
`git log -1 --format='%cI' -- skills/<name>/` against the transcript's first timestamp. If it did,
the instruction is to re-read `SKILL.md` from disk and audit whatever was already done for having
been done under superseded wording.

That fired correctly here — `plan-docs` had a commit 18 minutes after the session started, from a
parallel session — and then the audit was empty, because the commit touched only
`references/design-rationale.md`. The session's held `SKILL.md` text was current the whole time.

The directory-scoped query cannot tell the three subdirectories apart, and they fail differently:

| what changed   | what the session holds    | consequence                                      |
| -------------- | ------------------------- | ------------------------------------------------ |
| `SKILL.md`     | its full text, in context | held wording is stale — the case step 0 is about |
| `scripts/*`    | nothing; it shells out    | next call already gets the new behaviour         |
| `references/*` | nothing; read on demand   | inert                                            |

So the question step 0 actually wants is `-- skills/<name>/SKILL.md`, and a `scripts/` change is
worth a different note: nothing to re-read, but a command run _earlier_ in the session may have run
the old script, which is the same retroactive-audit question with a different trigger.

[PITFALL: the cheap check is one extra path-scoped `git log`, and skipping it costs a full re-read
plus an audit of everything already done — the most expensive branch in the whole procedure — on
every rationale commit anyone lands in a busy skill repo. On this machine that is a common event:
`references/` edits outnumber `SKILL.md` edits in normal skill maintenance.]

[UNVERIFIED: the frequency claim above is an impression from one repo's recent history, not a count.
Worth one `git log --name-only` tally before writing the split into `SKILL.md` as a justification —
the refinement stands on the correctness argument alone regardless.]

### 2. Step 6 tells the harvest to do something `~/AGENTS.md` forbids

Step 6 says to edit the skill source and "commit it locally without asking", and the Self-update
mechanics section repeats it. But `~/AGENTS.md` says, of any repo that is not the session's own:

> **Writing to another repo is out entirely, not merely discouraged** — no edit and no commit,
> however small, however obviously correct, **however much a skill's own instructions tell you to**.
> File it instead.

The clause is written as if aimed at exactly this situation. So a harvest invoked from any repo
other than `agent-skills` — which is nearly every harvest — cannot perform step 6 as written, and
the skill does not say so.

The skill is not unaware of the mechanism: step 2's routing filter already says "a candidate
belonging to another repo is _filed_ there, not queued here", and names `plans.py new --for`. Step 6
was simply written from the perspective of a session already inside the skills repo.

[NEEDS CLARIFICATION: which way should the split go? The obvious repair is "step 6 edits the source
when the session is in `agent-skills`, and files a plan with `--for` otherwise" — mechanical, and it
keeps the strong "do it now, a deferred skill fix does not happen" pressure by making filing the
immediate action rather than the deferral. The cost is that a filed skill fix waits for someone to
work in `agent-skills`, where an edit landed today; `plans.py absorb` is what makes that survivable,
and it is the same trade the global rule already accepts everywhere else.]

[NEEDS CLARIFICATION: does the same apply to step 0's "offer to re-install first"? Re-installing is
not a write to another repo's tree, so it is allowed — but it is outward-facing and step 6 already
says to ask. Probably no change needed; worth confirming rather than assuming while both steps are
being reworded.]

## Recommended direction

Both are small edits to `SKILL.md` and neither changes the procedure's shape. Do them together: the
second one is what stopped the first one being applied directly, so a session in `agent-skills`
picking this up can fix the routing and then use it.
