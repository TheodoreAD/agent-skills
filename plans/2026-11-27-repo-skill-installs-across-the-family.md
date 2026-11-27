---
status: idea
updated: 2026-11-27
---

# Repo skill installs across the family

## Context

The user asked on 2026-11-27 for a plan to run `inv agents.install-skills` in every repo, after
first checking each repo to see whether it was needed. repo-tasks v0.8.0, which this machine got the
same day, provides that task. It runs
`skills add ./skills --agent universal claude-code --skill '*' --yes`: one copy per authored skill
in `.agents/skills/`, and a junction per skill in `.claude/skills/`. It does nothing in a repo with
no `skills/<name>/SKILL.md`. It does not touch `.gitignore`.

Survey of the seven repos under `~/projects/personal` on the Windows machine, 2026-11-27. Every repo
was level with its remote and had no local changes. The survey compared each authored skill's
directory with its installed copy:

| repo                       | authored skills | task available  | installed now                 | install targets gitignored |
| -------------------------- | --------------- | --------------- | ----------------------------- | -------------------------- |
| **agent-skills**           | 16              | yes             | nothing                       | **no**                     |
| **ataraxia**               | 3               | no (own tasks/) | 2 current; 1 Claude-only copy | yes                        |
| **freshful-polite-mcp**    | 2               | no (own tasks)  | both current, universal       | yes                        |
| **nexus**                  | 1               | no (own tasks/) | current, universal            | yes                        |
| **win-configs**            | 1               | no (no invoke)  | current, universal            | yes                        |
| **power-user-linux-setup** | 0               | yes             | nothing to install            | no                         |
| **repo-tasks**             | 0               | yes             | nothing to install            | yes                        |

What that means for "run it in every repo":

- **Five repos need nothing.** freshful-polite-mcp, nexus and win-configs are already installed the
  universal way, and every copy matches its source. power-user-linux-setup and repo-tasks author no
  skills, so the task would be a no-op there.
- **ataraxia needs one reinstall, and not through this task.** `ataraxia-render-verify` is a
  Claude-only real directory in `.claude/skills/`, with no copy in `.agents/skills/`. ataraxia's
  tasks do not import repo-tasks, so it uses its AGENTS.md `npx skills add` line instead. Filed for
  ataraxia in the plans store as `2026-11-27-reinstall-render-verify-as-universal.md`, because the
  change is in that repo's tree.
- **agent-skills is the only repo where the task would do anything**, and it should not run as
  things stand. None of `.agents/skills/`, `.claude/skills/` or `skills-lock.json` is gitignored
  here, so the run would leave 16 untracked skill copies and a lock file in the working tree. The
  first `git add` of a directory would publish them. The global rule says every install target is
  gitignored, and this repo is the one that never did it.

## Open questions

[NEEDS CLARIFICATION: whether agent-skills should have a repo-level install at all. All 16 skills
are already installed user-wide from the published repo (`~/.agents/skills/`, with junctions in
`~/.claude/skills/`). A repo-level install would give a session here the working-tree version, which
helps while authoring. It would also list every skill twice, once as a project skill and once as a
user skill with the same name. How Claude Code ranks a project skill against a user skill of the
same name is not established. Probe it before choosing, with one skill whose description differs
between the two copies.]

[DECISION: no per-repo bootstrap in the repos that do not use repo-tasks. ataraxia, nexus and
freshful-polite-mcp have their own invoke tasks, and win-configs has none. Their AGENTS.md install
lines already produce the universal layout, and the survey shows they did. Wiring repo-tasks into
them only for this would beat a one-line command that works.]

## Recommended direction

1. Add `.agents/skills/`, `.claude/skills/` and `skills-lock.json` to agent-skills' `.gitignore`
   whatever the answer to the question above. That is the global rule, and it makes a stray
   `skills add` here harmless. It is one commit, through the gate.
2. Answer the duplicate-listing question with the probe. If the project copy wins cleanly, run
   `inv agents.install-skills` here and record in AGENTS.md that a session here reads the working
   tree. If it does not, leave agent-skills on the user-wide install and say so in AGENTS.md. The
   authoring loop is then edit, push and `skills update -g`, as skill-authoring-taudelta already
   says.
3. A session in ataraxia takes its filed plan.
4. Re-run the survey on the Linux machine, which has its own clones and installs.
