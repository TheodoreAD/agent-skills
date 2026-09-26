---
status: idea
updated: 2026-09-26
source_repo: github.com-personal/power-user-linux-setup
source_session: 10d0c6cd-12d8-42ff-9048-1da4b65afcc8.jsonl
source_moment: 2026-09-26T14:30:00Z
source_plan: plans/2026-09-26-allowlist-mid-pattern-wildcard-rules-are-dead.md
---

# Command rules moved to cli-allowlist; two skills cite the old home

## Context

On 2026-09-26 power-user-linux-setup reworked its permission allowlist (commits dc3d1a1 through
5933514 there). Two facts two installed skills state are now wrong:

1. **The `inv` read-only-by-name grant no longer lives in `setup.toml`.** It moved from
   `[packages.repo-tasks]` `claude_permissions_allow` to `cli-allowlist/tools.toml`'s `[inv]` entry
   (`overrides_only`, `allow_overrides`), rendered per harness by `inv allowlist.apply`. The same
   entry now carries ask guards for invoke's code-loading options (`-c/--collection`,
   `-r/--search-root`, `-f/--config`), because Claude's `*` in `inv *.status` spans arguments. Cited
   at `invoke-task-conventions/SKILL.md` rule 2 ("`[packages.repo-tasks]` `claude_permissions_allow`
   in `power-user-linux-setup`'s `setup.toml`").
2. **`global_option_prefixes` is gone, and no `git -C` rule is rendered for Claude at all.** Its
   `Bash(git -C * status:*)` rules never matched anything (Claude Code reads a mid-pattern `*` with
   a trailing `:*` literally since 2.1.282, and warns since 2.1.283). The replacement,
   `repo_dir_options`, renders only for Copilot; cross-repo `git -C` reads on Claude are left to its
   Bash sandbox. Cited at `session-bash-audit/SKILL.md` (the table row pointing `git -C`-style
   shapes at `global_option_prefixes`) and `session-bash-audit/scripts/audit.py` (a simulated "no
   prompt — the Bash(git -C * status:*) allow rule from global_option_prefixes" outcome, which was
   never true).

## Evidence

The measurements and the reasoning are in power-user-linux-setup's `contributing/cli-allowlist.md`,
sections "How each harness matches" and "`mode_covered` and `repo_dir_options`". The audit script's
simulation is the item most worth checking: it models `git -C x status` as allowed, which misreports
every `git -C` call it classifies.

## Open questions

[NEEDS CLARIFICATION: whether `audit.py` should model `git -C` as prompting (true today) or read the
live rule set instead of hard-coding what the allowlist does.]

## Recommended direction

Update the three citations to point at `cli-allowlist/tools.toml` and the contributing page by
section, and fix the audit script's `git -C` simulation to prompt.
