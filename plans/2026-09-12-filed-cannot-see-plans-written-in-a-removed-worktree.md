---
status: idea
updated: 2026-09-12
---

# `filed` cannot see a plan written in a worktree that has since been removed

## Context

Found 2026-09-12 by a harvest of a three-day background session in this repo. `filed --until`
reported **"plan files this session wrote (1)"** — the one plan written in the worktree the harvest
was running from. The session had in fact written or edited **at least five** plans, all of them
merged and on `main`:

- `2026-09-10-repo-presentation-and-pitch-skill.md`
- `2026-09-07-five-skills-have-never-fired.md` (appended)
- `2026-09-12-harvest-should-ask-what-the-context-is-still-worth.md`
- `2026-09-12-a-naming-pass-over-skills-that-outgrew-their-names.md`
- `2026-09-12-skills-state-omits-the-skills-a-session-changed.md` — the one it found

**The mechanism.** Each was written inside `.claude/worktrees/<name>/plans/`, a linked worktree the
session created for one change, pushed from, and removed. `filed` resolves a plan by the literal
path the edit tool wrote to, so a path under a deleted worktree resolves to nothing and the plan
drops out of the count — while the file itself sits at `<repo>/plans/<name>` on `main`, exactly
where a reader would look.

**Why it is structural rather than one session's quirk.** A background job cannot edit the shared
checkout; the harness refuses the edit and requires a worktree first. So in this repo **every
background session that writes a plan writes it through a worktree**, and every one that tidies up
after itself afterwards produces this undercount. The case the check undercounts is the default case
for that kind of session.

[PITFALL: **the wrong number is plausible, which is the failure the skill names for this
subcommand.** "1 plan file" is a believable output for a session, and the step-8 guidance that
exists to catch a suspicious `0 this session` does not trip on a `1`. It was caught only because the
harvesting session remembered writing more. A session that did not would have opened its report's
"where everything went" group with a count four short, from the one tool meant to replace
remembering.]

Related but distinct: which **lines** `filed` samples inside a plan it did find was settled in
`6254193`, by matching them against this session's own writes to that path. This is about which
**files** it can find at all — and a normalised write path would have to reach that matching too,
since it compares by path.

## Recommended direction

Normalise a write path before resolving it: a path containing `.claude/worktrees/<name>/` maps to
the repository root it belongs to, and the plan is then looked up at `<root>/plans/<name>`. The
worktree's own `git rev-parse --git-common-dir` names that root while the worktree exists, but it
will not exist at harvest time, so the mapping has to come from the path shape itself.

[NEEDS CLARIFICATION: **whether to key on the Claude Code layout or on any worktree layout.**
`.claude/worktrees/<name>/` is one harness's convention. VS Code's default is a sibling
`<repo>.worktrees/<name>/`, and `skill-authoring` already names both. Handling only the first fixes
this repo's background sessions and leaves the second silent in exactly the same way.]

[NEEDS CLARIFICATION: **what a plan moved or renamed on `main` after the worktree wrote it should
report.** Once the path maps to the root, a plan that was later renamed or retired would resolve to
nothing again — which is the existing `MISSING` case and should say so rather than silently drop.]
