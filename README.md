# agent-skills

Personal [Agent Skills](https://github.com/agentskills/agentskills) — plain `SKILL.md` directories,
readable by any agent that speaks the format, with no vendor bundle wrapped around them.

Everything here is authored against the vendor-neutral stack only: `AGENTS.md` for instructions,
Agent Skills for procedural knowledge, MCP for tools. No Claude Code plugin manifest, no
marketplace, no `.claude-plugin/` — a skill in this repo works the same in Codex, Cursor, Copilot,
Gemini CLI, Zed and the rest.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global          # every skill, user-level
npx skills add TheodoreAD/agent-skills --skill plan-docs # just one
```

The [`skills` CLI](https://github.com/vercel-labs/skills) copies the skill into the canonical
`~/.agents/skills/` hub (or the agent-specific directory for the agents that need one) and links
each detected agent at it. Nothing else is required — no manifest to register, no repo to clone.

Or, without installing anything, point your agent at [`skills/<name>/SKILL.md`](skills/) and let it
read the file directly.

## Skills

| Skill                            | Use it when                                                                  | Scope                   |
| -------------------------------- | ---------------------------------------------------------------------------- | ----------------------- |
| [`plan-docs`](skills/plan-docs/) | Capturing an idea, drafting a design, or tracking work-in-progress in a repo | Opinionated but general |

**Scope** says how much of the skill is a convention anyone can adopt versus a personal preference:
_general_ is portable as written, _opinionated but general_ picks one defensible convention out of
several and commits to it, and _personal_ depends on how one particular machine or repo family is
set up. Nothing here reaches outside the repo you are working in.

## Layout

```
skills/<name>/
├── SKILL.md          # the skill itself — YAML frontmatter (name, description) + the instructions
├── references/       # rationale, prior art, evidence — read on demand, not loaded up front
└── scripts/          # anything the skill runs, when it has one
```

Each skill's `references/` is where its reasoning lives — why this convention and not the obvious
alternative, what went wrong the last time, which sources it was checked against. That is
deliberately inside the skill rather than in a repo-level `contributing/` tree, so a skill stays a
self-contained unit that can be read, copied or vendored on its own.

## License

MIT — see [LICENSE](LICENSE).
