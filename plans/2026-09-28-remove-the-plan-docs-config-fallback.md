---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/power-user-linux-setup
source_session: b73129dd-6136-41c3-a026-8e871581bc14.jsonl
source_moment: 2026-09-27T21:40:00Z
source_plan:
---

# Remove the plan-docs config fallback

## Context

`plans.py` and `harvest.py` still read `~/.config/plan-docs/config.toml` and honour
`$PLAN_DOCS_CONFIG` when the `plan-conveyor` path holds nothing. The shim existed for one window:
while this machine's deployed instructions told readers to edit the old path, so a reader following
them would otherwise write a file nothing reads.

**That window is closed.** `power-user-linux-setup` `da6da06` (2026-09-28) renamed every live
reference to `plan-conveyor`: the `config/agents-md/` fragments (scan commands, `--for` filing, the
`[private] extra` config location), `setup.toml`'s plans-store description, and the
`home.list-claims` footer. The fragments are redeployed; `~/.agents/AGENTS.md`,
`~/.claude/CLAUDE.md` and `~/.copilot/copilot-instructions.md` contain no `plan-docs` path.

The plan that set this condition — `power-user-linux-setup`'s absorbed
`plans/2026-09-27-plan-docs-paths-after-the-plan-conveyor-rename.md`, filed from this repo — said:
"the fallback comes out once this plan lands … Removing them is a change in `agent-skills`, so it is
that repo's commit". It is retired in `power-user-linux-setup`; `plans.py archive --file` on it
reads it back.

## Recommended direction

Remove the fallback from `plans.py` and the independent one in `harvest.py`, their four tests in
`tests/unit/test_locations.py`, and the SKILL.md paragraph describing the rename fallback.

[DECISION: **removed as a read, kept as a refusal** (2026-09-28). This machine is migrated, but the
skill is published and cannot know every installer's is, so the pitfall below is answered by its own
second option. In `plans.py` a config still at the old directory, or named only by the old variable,
now raises with the move to make; `harvest.py`, which writes nothing, simply stops reading the old
locations. The four tests became refusal tests. `$PLAN_DOCS_SESSION_REPO` and `$PLAN_DOCS_DEVICE`,
renamed only today, still read: neither guards a file a writer would skeletonise over.]

[PITFALL: the fallback guards `[private] extra`. The writers lay down a config skeleton whenever the
current path is absent, so a machine that still keeps its config at the old path would silently get
an empty config and a shorter scan term list. Before removing, confirm no machine you use still
keeps it there — this one was migrated 2026-09-27 — or have the writers refuse, naming the old path,
instead of skeletonising over it.]

## Migrated to

- **The refusal and why it is not a silent removal** — `config_path`'s docstring in
  `skills/plan-conveyor/scripts/plans.py`, and the rename paragraph in its `SKILL.md` (`431ab7d`);
  the four refusal tests in `tests/unit/test_locations.py`.
