---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/power-user-linux-setup
source_session: f7cff2a9-fb4a-4b46-93f5-903a0e24d1a3.jsonl
source_moment: 2026-09-26T08:25:14Z
source_plan:
---

# `session-harvest` step 0: a script-backed skill has a cheaper probe than the full re-read

## Context

Filed from a `power-user-linux-setup` session, so it could not be edited into `session-harvest`
directly. `source_plan` is deliberately blank: this **reports a gap** rather than proposing a
decision somebody else owns, so there is nobody to check with.

`session-harvest`'s step 0 handled this run correctly and its guidance was accurate throughout. The
gap is one branch, and it is the branch that fired.

## What happened

`skills-state` reported, for `plan-docs`:

```
installed copy matches the checkout; SKILL.md moved after this skill entered context (9 commit(s))
… scripts/ moved after this skill entered context (10 commit(s))
```

Ten commits, none of them this session's — another session had been reworking `plan-docs` while this
one was using it, and the installer had already run. So the skill's two cheap remedies were both
unavailable:

- **Diff `SKILL.md` rather than re-reading it** — the step's own prescription, and the right one
  normally. It returns nothing here: installed and checkout are identical. The stale copy is the one
  in **this session's context**, which is neither side of any diff on disk.
- **Read the `scripts/` diff before deciding a note is enough** — same problem, same reason.

The step already names this outcome precisely, and its answer is the expensive one:

> **The one case that needs the full re-read is a re-install that ran mid-session, _after_ the skill
> was loaded**: the diff is only sound when the copy held in context is one side of it, and there
> the held text is neither.

`plan-docs`' `SKILL.md` is roughly 700 lines. A full re-read is a large fraction of a harvest's
remaining budget, spent to answer a question that is usually much narrower.

## What was done instead, and why it was enough

Two `--help` calls, for the two subcommands this session had actually used:

```shell
python3 <plans.py> commit --help
python3 <plans.py> push --help
```

That answered the operative question in about twenty lines:

- **`commit -m` was unchanged**, so all seven of this session's store commits were sound and no
  correction was owed. This is the half the step cares most about — "was anything already done under
  superseded wording".
- **A new `--body` flag** exists, which would have been the idiomatic call. Additive, nothing
  broken.
- **A new `push` subcommand** scans what a push would publish before publishing it — which this
  session had hand-rolled as `scan --mode history` followed by `git -C <store> push`. Right outcome,
  obsolete spelling.

Neither of those would have been visible in a rate table or a status line, and both were worth
knowing.

Checked at absorption, 2026-09-26: both are `plan-docs` changes that shipped here on 2026-09-22 —
`push` in `18b78ea`, `--body` in `6f3e22c` — and are the _content_ the probe found, not part of the
proposal. `session-harvest`'s step 0 last changed in `3aa3c70` (2026-09-13), and no `--help` probe
appears in it, so nothing this plan proposes has landed; the "held text is neither" branch it cites
dates from `5e2d8b5` (2026-09-07).

[DECISION: **`--help` is not a substitute for the re-read in general — it is the right first probe
for a skill whose commands are a script.** It answers "did my calls mean what I assumed, and is
there a better command now" exactly, and it answers nothing about prose guidance, judgement calls or
pitfalls. So the shape of the suggested change is a cheaper first step that can make the full
re-read unnecessary, not a replacement for it: probe the CLI surface for the subcommands the session
actually called; re-read `SKILL.md` when the session leaned on its **prose** rather than on its
commands, or when `--help` shows an interface that moved under a call already made.]

## Open questions

[DECISION: **name the condition, not the skills.** Settled 2026-09-26. Step 0 says "a skill whose
commands are a script", and `skills-state` decides it mechanically — a `*.py` under the installed
copy's `scripts/`. A list of skills would go stale the first time a skill gains or loses a script.]

[DECISION: **`skills-state` prints the probe, the middle option.** Settled 2026-09-26. It fires on
exactly the held-context rows — `SKILL.md` moved after load and install equals checkout — and names
the script with `<subcommand> --help`, leaving which subcommands to the reader, since that needs the
transcript and the check does not read it.]

## Migrated to

Landed 2026-09-26 in `abfe5d3`.

- **The rule and its 2026-09-26 instance** — `skills/session-harvest/SKILL.md` step 0, the paragraph
  on diffing `SKILL.md`, from "For a skill whose commands are a script, probe before re-reading".
- **Why the probe fires where it does and why it names no subcommands** — the `_note_help_probe`
  docstring in `skills/session-harvest/scripts/harvest.py`.
- **The gate** — `test_a_held_skill_md_that_is_neither_side_gets_the_help_probe_first` and
  `test_no_help_probe_when_the_diff_is_still_sound_or_there_is_no_script`.
- **Not migrated:** the Evidence section's transcript pointer. It expires with the transcript in
  late October, and the finding is carried by the docstring without it.

## Evidence

The session is `f7cff2a9-fb4a-4b46-93f5-903a0e24d1a3` in
`-home-tdumitrescu-projects-github-com-personal-power-user-linux-setup`. Search it for the phrase
`the copy frozen in my context is neither side` — the turn immediately after that runs the two
`--help` calls, and `skills-state`'s ten-commit output is the call before it.

A transcript is kept 30 days by default, so this is worth acting on before late October if the turns
themselves matter; the finding above stands without them.
