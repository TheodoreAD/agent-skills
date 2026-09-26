---
status: idea
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

[DECISION: **`--help` is not a substitute for the re-read in general — it is the right first probe
for a skill whose commands are a script.** It answers "did my calls mean what I assumed, and is
there a better command now" exactly, and it answers nothing about prose guidance, judgement calls or
pitfalls. So the shape of the suggested change is a cheaper first step that can make the full
re-read unnecessary, not a replacement for it: probe the CLI surface for the subcommands the session
actually called; re-read `SKILL.md` when the session leaned on its **prose** rather than on its
commands, or when `--help` shows an interface that moved under a call already made.]

## Open questions

[NEEDS CLARIFICATION: **which skills does this apply to?** It works for `plan-docs`,
`research-library`, `session-bash-audit` and `session-harvest` itself — every skill in this repo
whose operative surface is a `scripts/` CLI with `argparse` behind it. It does nothing for a
prose-only skill. Whether the step should name the condition ("a skill whose commands come from a
script") or name the skills is a wording choice this repo's own conventions should decide.]

[NEEDS CLARIFICATION: **should `skills-state` print the probe itself?** It already prints the
`--for` filing command, so it has the precedent for emitting a command rather than describing one —
and it knows which subcommands exist. Against: it does not know which ones **this session called**,
which is the part that makes the probe cheap, and that needs the transcript. A middle option is for
it to say "this skill is script-backed, so probe `--help` for the subcommands you used" on exactly
the rows where the held-context branch fires. Per this repo's standing preference, a correction a
script can simply make belongs in the script.]

## Evidence

The session is `f7cff2a9-fb4a-4b46-93f5-903a0e24d1a3` in
`-home-tdumitrescu-projects-github-com-personal-power-user-linux-setup`. Search it for the phrase
`the copy frozen in my context is neither side` — the turn immediately after that runs the two
`--help` calls, and `skills-state`'s ten-commit output is the call before it.

A transcript is kept 30 days by default, so this is worth acting on before late October if the turns
themselves matter; the finding above stands without them.
