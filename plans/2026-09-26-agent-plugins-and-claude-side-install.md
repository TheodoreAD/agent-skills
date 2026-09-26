---
status: idea
updated: 2026-09-26
---

# Agent plugins, and how this repo's skills reach Claude Code

## Context

A survey on 2026-09-26, done from fresh clones in `$RESEARCH_HOME/repos`, looked at "AI agent
plugins" and how they relate to skills. It found that the plugin layer has split three ways while
the skill itself stayed the one portable unit. This plan records what should be investigated about
that, both here and in `power-user-linux-setup` (PULSE), which installs these skills on this
machine. Nothing has been changed yet.

What the survey established, with the clone to re-check each claim against:

- **Agent Plugins 1.0** (agent-plugins.org, released 2026-08-06; clone
  `github.com--agentplugins--agent-plugins-spec`).
  - A root `plugin.json` with a required `$schema`, plus `skills/` and `mcp.json`. Skills must
    conform to agentskills.io.
  - Hooks, commands, agents, rules and LSP servers are ruled out as too client-specific. They go in
    reverse-domain `extensions` directories.
  - No marketplace format; 1.1.0 is a working draft.
  - Steering committee from `MAINTAINERS.md`: Amazon, Cursor, Microsoft, OpenAI, Vercel. **Not
    Anthropic, not Google.**
- **Who reads Agent Plugins:**
  - In source: Codex, VS Code (Copilot Chat) and Cline. Cline reads it only from
    `~/.agents/plugins`, deliberately, so that opening a repo cannot start its MCP servers.
  - Copilot CLI, per its docs only.
  - Not Claude Code, Gemini CLI, Goose, Kimi, Zed or opencode.
- **Claude Code's `.claude-plugin/` format** (v2.1.283, 2026-09-25) is a de facto second standard,
  read by Codex, VS Code and Copilot CLI and by nobody else.
  - A plain skills repo becomes a Claude plugin with no `plugin.json`: a
    `.claude-plugin/marketplace.json` entry with `strict:false` and a `skills` array is enough.
    `anthropics/skills` ships exactly that, five plugins that contain only skills.
  - Plugin skills are namespaced `plugin:skill`. A bare name still resolves when only one plugin
    skill matches.
  - Skills and plugins enabled on the claude.ai account now sync into terminal sessions (2.1.275).
    The opt-outs are `syncClaudeAiSkills` and `syncClaudeAiPlugins`. On this machine the synced
    `anthropic-skills:*` set already appears in every session's skill listing.
- **Skill directories:** all ten agents surveyed read `.agents/skills`, Crush only at project level.
  Only VS Code/Copilot, opencode, Goose and Crush also read `.claude/skills`. Claude Code reads only
  `.claude/skills`.
- **The vercel `skills` CLI** reads `.claude-plugin/marketplace.json` and `plugin.json`, but only to
  find skill paths. It skips remote sources and never installs hooks, MCP servers or agents
  (`src/plugin-manifest.ts:44-111`). Its README example uses `"source": "my-plugin"`, but the code
  drops any source that does not start with `./` (`plugin-manifest.ts:92`).

The two repos as they stand:

- **This repo's `AGENTS.md`** admits only `SKILL.md`, `AGENTS.md` and MCP, and names
  `.claude-plugin/` and marketplace entries as excluded. It says nothing about Agent Plugins, which
  did not exist when that rule was written.
- **PULSE, on the Claude side:** `inv ai.install-skills` runs the `skills` CLI into
  `~/.agents/skills`. The CLI makes one `~/.claude/skills/<name>` symlink per skill;
  `_ensure_agents_skills` in `tasks/ai.py` deliberately stopped linking the whole directory on
  2026-09-07.
  - `~/.claude/settings.json` is generated from `setup.toml` plus the `cli-allowlist` pipeline, and
    carries no plugin, marketplace or `syncClaudeAi*` keys.
  - PULSE manages no Claude plugins at all.
  - Two docstrings in `tasks/ai.py` disagree with each other: `install_skills` still says
    ".claude/skills symlinked to it". Filed for PULSE on 2026-09-26 as
    `2026-09-26-two-stale-descriptions-after-the-allowlist-and-skills-rework.md`.

## Open questions

[NEEDS CLARIFICATION: Should `AGENTS.md`'s admitted formats include an Agent Plugins root
`plugin.json`? It is vendor-neutral on paper, but its governance excludes the vendor whose harness
this machine mainly runs, and neither Claude Code nor Gemini reads it.]

[NEEDS CLARIFICATION: Does a single versioned plugin install buy consumers anything over
`npx skills add`, given that the `skills` CLI already reaches all of the agents that matter? Measure
what a Codex, VS Code or Cline user actually gets from each route before deciding.]

[NEEDS CLARIFICATION: Should the claude.ai skill/plugin sync be pinned, on or off, through
`setup.toml` in PULSE? It is exactly the "on by default, reaches the machine from elsewhere"
behaviour the global rules ask to be decided rather than accepted. It also affects `skill-fitness`:
synced skills compete in the listing and cost context.]

[NEEDS CLARIFICATION: If Claude plugins are ever used on this machine (someone else's plugin, say),
is installing them PULSE's job? That would mean a `setup.toml` package kind that runs
`claude plugin install` at user scope. The alternative is to leave plugins out of the machine setup
entirely.]

[NEEDS CLARIFICATION: Does a `plugin:skill` namespace matter to `skill-fitness`? Its listing-cost
and competition measurements read skill names from frontmatter, and plugin skills show up under a
prefixed name.]

## Recommended direction

Investigate before changing anything, in this order:

1. **Re-verify the survey's claims against the clones**, updated first with `library.py update`. Pay
   particular attention to the Agent Plugins spec's 1.1.0 draft, and to whether Claude Code has
   started reading a root `plugin.json`: grep its CHANGELOG for `agent-plugins`, and grep for
   `$schema` handling.
2. **Prototype outside the repo**, in a scratch copy of this repo:
   - Add a root Agent Plugins `plugin.json` and install it into Codex, VS Code and Cline. Compare
     the result with `npx skills add --global`: what gets installed, where, under which names, and
     how updates happen.
   - Do the same with a `strict:false` `.claude-plugin/marketplace.json` for Claude Code.
   - The prototype is what answers the second question above. The first question is a policy call
     informed by it.
3. **In PULSE, file a plan rather than edit.** Writing to another repo is out for this session, so
   file with `plans.py new <topic> --for github.com-personal/power-user-linux-setup` covering:
   - Deciding the `syncClaudeAiSkills` and `syncClaudeAiPlugins` settings.
   - Whether a plugin install mechanism belongs in `setup.toml`.

   The stale `install_skills` docstring is already filed, separately.
4. **Only then** amend this repo's admitted-formats rule in `AGENTS.md` and the README's "No Claude
   Code plugin manifest" line, if the outcome warrants it. Both are rules other sessions rely on, so
   the change goes in its own commit with a body saying what the measurement showed.

[DEFERRED: Report the vercel `skills` README/code mismatch on marketplace `source` paths upstream,
once step 1 re-confirms it against the current release.]
