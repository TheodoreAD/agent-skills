---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Two things that made a session write into this repo, and install a skill into the wrong place

## Context

Both found 2026-08-30 by a session working in an unrelated project, and both were found the same
way: the user read a harvest report closing with an install command and asked why it had no
`--global`, then asked whether the session had just modified another repo. It had.

## 1. The install command is missing `--global` in six places

`skill-authoring/SKILL.md` has it right:

```shell
npx skills add <owner>/<repo> --global --skill <name>     # one skill
npx skills add <owner>/<repo> --global                    # the whole repo
```

Without `--global` the CLI installs into the **current working directory** — a `.agents/skills/`
inside whatever repo the session happens to be in — rather than into `~`. So the session that runs
the copied command gets its update, no other project on the machine does, and the repo it was
standing in silently acquires a skills directory nobody meant to add there. A skill that appears to
have been re-installed and has not is the same class of failure as the stale-copy problem
`session-harvest` step 0 already exists to catch.

Every occurrence that lacks the flag, as of 2026-08-30:

| file                                        | line |
| ------------------------------------------- | ---- |
| `README.md`                                 | 15   |
| `AGENTS.md`                                 | 11   |
| `AGENTS.md`                                 | 60   |
| `skills/session-harvest/SKILL.md`           | 513  |
| `skills/python-conventions/SKILL.md`        | 473  |
| `skills/db-defaults/SKILL.md`               | 217  |
| `plans/2026-08-28-cross-repo-plan-store.md` | 39   |

The two `AGENTS.md` hits and the plan hit are prose rather than commands to copy, so they may be
fine as they stand — worth a judgement per line rather than a blanket rewrite. The three `SKILL.md`
lines and `README.md:15` are copy-and-run instructions and are wrong.

[NEEDS CLARIFICATION: whether `skill-layout`'s test suite should assert this. It already enforces
real limits on frontmatter, and "an install command in a `SKILL.md` names `--global`" is the same
shape of check — mechanical, and exactly the kind of thing that drifts back in one skill at a time.
The counter-argument is that a bare `npx skills add ../my-skills --skill <name>` is legitimate while
drafting, which `skill-authoring` documents, so the rule needs an exemption and may not be worth
it.]

## 2. `session-harvest` tells the agent to break a hard `~/AGENTS.md` rule

This is the more serious of the two, because the skill is instructing the violation rather than
failing to prevent it.

`~/AGENTS.md`, under "Running a command against a different repo than the session's project":

> **Writing to another repo is out entirely, not merely discouraged** — no edit and no commit,
> however small, however obviously correct, **however much a skill's own instructions tell you to.**
> File it instead: `plans.py new <topic> --for <repo>` […] The reason it is a hard line rather than
> a judgement call: a commit in someone else's tree is silent by construction — it looks routine in
> `git log`, and the session that owns the repo may push it without ever knowing it was not theirs.

That clause — "however much a skill's own instructions tell you to" — reads as though it were
written about this exact case. And `session-harvest` steps 6 and 7 say the opposite in as many
words:

> Default to editing the source now, not filing it for later; a deferred skill fix is a skill fix
> that does not happen.

> **Committing and deploying the skill edit.** Commit it locally without asking — it is reversible,
> reviewable as a diff, and pausing for approval mid-run is what makes the fix get dropped.

Confirmed by the failure: a session running a harvest from an unrelated project made two additive
edits to `skills/session-harvest/SKILL.md`, ran this repo's gate, and committed them here as
`6b0330d`. The gate passed, the diff was small and correct, and it was still a commit in a repo the
session had no business writing to — left sitting in `git log` for whichever session pushes next.

[DECISION: the global rule wins, and it is not close. The skill's justification for committing
directly — that a deferred fix does not happen — was true when it was written and is not any more:
`plans.py new <topic> --for <repo>` did not exist then, and it now gives a filed skill fix a real
trigger, because `absorb` offers it to the next session working in this repo. The reason the global
rule gives is also strictly stronger than the skill's: a silent commit in a parallel session's tree
is a correctness problem, while a deferred fix is a latency problem.]

**The fix is a rewrite of steps 6 and 7's mechanics, not a caveat.** Both currently end on "commit
it", and the "Self-update mechanics" section repeats the instruction a third time. Suggested shape:

- keep the requirement that every run asks whether the skill was wrong — that part is working, and
  it is what produced both findings here;
- when the session **is** in `agent-skills`, edit and commit as today;
- when it is not, file the improvement with
  `plans.py new <topic> --for github.com-personal/agent-skills`, commit it in the store, and report
  the filename. Same discipline, one hop.

[NEEDS CLARIFICATION: whether any other skill carries the same instruction. `skill-authoring` is the
obvious candidate, since its whole subject is the edit → gate → commit → push → re-install sequence,
and a session invoking it from another project would hit the identical contradiction. Worth a grep
for `commit` across every `SKILL.md` before deciding this is a one-skill fix.]

[DEFERRED: what to do with `6b0330d` itself. It is unpushed and its content is two genuine
improvements — checking whether a misuse is already filed before filing it, and sweeping
shared-store entries a session _changed_ rather than only those it added. Reverting it is itself a
write to this repo, so the session that made it stopped and reported instead. Whoever picks this up
should decide whether to keep the commit, re-author it, or drop it and take the content from here.]
