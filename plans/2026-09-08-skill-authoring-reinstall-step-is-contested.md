---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_moment: 2026-09-08
---

# `skill-authoring` step 6 names a command sessions consistently refuse to run

## The measurement, and it was looking for something else

Taken 2026-09-08 in `power-user-linux-setup` while pricing whether that repo should be runnable from
outside its checkout (`plans/2026-09-08-pulse-portability-run-from-anywhere.md` there). The question
was how often a session in another repo reaches for a PULSE task, counted over the harness's ~30-day
transcript window by grepping for a `cd <pulse checkout> && inv …` chain.

**16 occurrences, 6 sessions, 3 repos** — `agent-skills` 12, `repo-tasks` 3, `olx-polite-mcp` 1:

| what was typed          | count | note                                       |
| ----------------------- | ----: | ------------------------------------------ |
| `inv ai.install-skills` |    12 | the skill installer, after editing a skill |
| `inv ai.skills`         |     2 | **no such task**                           |
| `inv --list`            |     1 | looking for the name                       |
| `inv ai.init`           |     1 | **no such task**                           |

Then the cheap fix was checked — name the exact command in `skill-authoring`'s last step, so nobody
has to guess — and it turned out to be unavailable. **Step 6 already names a command, and it is a
different one:**

```shell
npx skills add <owner>/<repo> --global --skill <name>     # one skill
npx skills add <owner>/<repo> --global                    # the whole repo
```

Nothing in the documented sequence mentions `power-user-linux-setup` or `inv ai.install-skills` at
all.

## What that means

Twelve sessions crossed a repo boundary to run a task their own loaded skill does not mention, and
three more guessed at its name rather than running the command the skill does give them. That is not
sessions failing to follow instructions inattentively — it is the same substitution made
consistently, by different sessions, in three repos, over a month.

**They may well be right.** `inv ai.install-skills` does one thing the `skills` CLI does not: it
ensures `~/.agents/skills/` exists with `.claude/skills` symlinked to it. That gap is recorded in
two places already — `~/AGENTS.md`'s "the `skills` CLI announces a Claude Code symlink it does not
create, and PULSE covers exactly that gap instead of taking over skill installation", and
`power-user-linux-setup`'s own `AGENTS.md`. A session that has read either one and then reaches for
the installer that closes the gap is reasoning correctly and diverging from step 6 to do it.

So this is **two commands competing for one step**, and the skill names the one that leaves a gap
the rest of the machine's documentation says matters.

## Why it is worth deciding rather than leaving

- **It decides an unrelated design question.** The portability plan in `power-user-linux-setup` is
  weighing a `pulse` wrapper on PATH, and its whole cost case rests on the sixteen reaches. If
  `npx skills add` turns out to be the correct step, twelve of the sixteen are sessions doing
  something unnecessary and the measured need drops to four — below anything worth building. If
  `inv ai.install-skills` is correct, the need is real, recurring, and concentrated on one command.
- **A quarter of the attempts failed on a guessed name.** `ai.skills` twice and `ai.init` once are
  sessions that knew an installer existed and could not recall what it was called, from outside the
  checkout where `inv --list` does not work. Whichever command wins, the skill naming it removes
  that.
- **The divergence is invisible from inside the skill.** Nothing reports that step 6 was replaced;
  the session runs its substitute, the skill installs, and the transcript looks like compliance.

## Open questions

[NEEDS CLARIFICATION: **which command is the canonical last step?** The case for
`inv ai.install-skills` is the symlink gap, documented in two instruction files. The case for
`npx skills add` is that it is one mechanism deep, needs no checkout of another repo, works on a
machine where PULSE is not installed, and is what the skill already says. A third possibility is
that both are right at different times — the CLI for a re-install where the scaffold already exists,
the task for a first install or a repair — in which case step 6 needs the condition, not just the
command.]

[NEEDS CLARIFICATION: whether a skill in this repo may name a task in `power-user-linux-setup` at
all. It is a cross-repo dependency in the direction the family normally avoids: PULSE installs
skills, so a skill telling its reader to run a PULSE task inverts that. If the answer is no, the fix
is the `skills` CLI's own gap being closed upstream or the step gaining a follow-up that creates the
symlink without naming PULSE.

**Added on absorption 2026-09-08, because this repo already answers most of it.** Its `AGENTS.md`
says: _"Every skill has to work for someone who has only this repo. A rule that depends on one
machine's setup — a specific dotfile, a locally-installed task runner, a repo that exists on one box
— belongs in that machine's own `AGENTS.md`, not in a published skill."_ A task runner in another
checkout is that, exactly.

And it is measured rather than merely stated. Run against a throwaway skill whose body says
"Re-install with `inv ai.install-skills` from the power-user-linux-setup checkout", `fitness.py`'s
portability scan returns `{'refs': 1, 'bare': 1, 'kinds': {'task-runner': 1}}` — a bare, undeclared
finding. So step 6 cannot simply be changed to name the task: it would have to declare the
dependency in `compatibility:`, and `skill-authoring` is then a skill that does not work for a
reader who installed it with `npx skills add` and has no PULSE.

That does not settle the first question, and deliberately so — the symlink gap is real whichever way
it goes. What it does settle is that "just put `inv ai.install-skills` in step 6" is not available
as the cheap fix, which is what the measurement above was reaching for.]

[UNVERIFIED: the 16 is a floor. It is a `cd <path> && inv` grep over ~30 days, so it misses any
cross-repo reach spelled another way and everything the user did outside an agent session. The
transcript window is also younger than the habit.

**Now 17, and the seventeenth is this plan's own absorbing session.** 2026-09-08, working in
`agent-skills`, having just edited `research-library`: it pushed, then ran
`cd <pulse checkout> && inv ai.install-skills`, then verified by running the installed copy's own
`add --dry-run`. It had `skill-authoring`'s step 6 available and did not use it. The reasoning was
the documented symlink gap, which is the same reasoning the section above credits — so the
substitution reproduces on demand, in the repo that owns the skill, by a session that had just read
the surrounding rules.]

## Recommended direction

Decide the first open question, then make step 6 say it — including the condition, if the answer is
"both, at different times". Report the decision back to `power-user-linux-setup`'s portability plan,
which is blocked on it: that plan's step 2 is this question and its steps 3 and 4 do not get priced
until this is answered.
