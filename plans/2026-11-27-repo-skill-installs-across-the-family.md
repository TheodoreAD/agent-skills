---
status: idea
updated: 2026-11-28
---

# Repo skill installs across the family

## Context

The user asked on 2026-11-27 for a plan to run `inv agents.install-skills` in every repo, after
first checking each repo to see whether it was needed. repo-tasks v0.8.0 provides that task. It runs
`skills add ./skills --agent universal claude-code --skill '*' --yes`: one copy per authored skill
in `.agents/skills/`, and a junction per skill in `.claude/skills/`. It does nothing in a repo with
no `skills/<name>/SKILL.md`, and it does not touch `.gitignore`.

**The Windows machine is done (2026-11-28).** A re-survey of the seven repos under
`~/projects/personal` there found every authored skill installed the universal way, every copy
matching its source, and every install target gitignored:

| repo                       | authored skills | installed through           | install targets gitignored |
| -------------------------- | --------------- | --------------------------- | -------------------------- |
| **agent-skills**           | 16              | `inv agents.install-skills` | yes, from 2026-11-28       |
| **ataraxia**               | 3               | AGENTS.md's `npx` line      | yes                        |
| **freshful-polite-mcp**    | 2               | AGENTS.md's `npx` line      | yes                        |
| **nexus**                  | 2               | AGENTS.md's `npx` line      | yes                        |
| **win-configs**            | 2               | AGENTS.md's `npx` line      | yes                        |
| **power-user-linux-setup** | 0               | nothing to install          | no, not needed             |
| **repo-tasks**             | 0               | nothing to install          | yes                        |

ataraxia's `ataraxia-render-verify`, a Claude-only copy on 2026-11-27, was reinstalled from a
session there.

[DECISION: agent-skills installs its own skills into the repo. The question was whether a project
copy beside the user-wide install of the same name would be listed twice. Probed 2026-11-28 with
Claude Code on Windows: a marker put in the installed project copy's description, reached through
the `.claude/skills/` junction, was what a fresh headless session saw, and it saw one entry per
name. So the project copy shadows the user one cleanly, and a session here reads the working tree.
Recorded in AGENTS.md.]

[DECISION: no per-repo bootstrap in the repos that do not use repo-tasks. ataraxia, nexus and
freshful-polite-mcp have their own invoke tasks, and win-configs has none. Their AGENTS.md install
lines already produce the universal layout, and the survey shows they did. Wiring repo-tasks into
them only for this would beat a one-line command that works.]

## Open questions

[NEEDS CLARIFICATION: the Linux machine's state. It has its own clones and its own installs, and
none of the above was checked there. Whether the shadowing result holds on Linux, where
`.claude/skills/` entries are symlinks rather than junctions, is also unprobed.]

## Recommended direction

From a session on the Linux machine, in agent-skills:

1. Pull, so the `.gitignore` entries arrive before anything is installed.
2. Re-run the survey: for each repo, the authored skills against `.agents/skills/`,
   `.claude/skills/` and `skills-lock.json`, whether each copy matches its source, and whether the
   three targets are gitignored.
3. Fix what it finds the way this machine did: `inv agents.install-skills` where repo-tasks is
   present, the repo's AGENTS.md line elsewhere, and a plan filed with `new --for` for any repo
   other than the session's.
4. Repeat the shadowing probe once, then retire this plan.
