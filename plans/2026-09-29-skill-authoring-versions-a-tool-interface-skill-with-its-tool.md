---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/repo-tasks
source_session: 0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl
source_moment: 2026-09-28T20:37:04Z
source_plan: plans/2026-09-29-ship-a-skill-for-running-repo-tasks.md
---

# skill-authoring: keeping a tool-interface skill versioned with its tool

## Context

`skill-authoring`'s "Publishing a skill repo" section already says where a skill documenting a
repo's own interface lives: committed in that repo under `.agents/skills/`, while a cross-project
convention skill goes in a dedicated skills repo. A repo-tasks session researching that split for a
repo-tasks skill found the placement right and well supported, and found what the section does not
say: **how such a skill stays matched to the version of the tool it describes**, which is the
failure other projects actually hit.

Research, 2026-09-28/29, full report attached to repo-tasks'
`plans/2026-09-29-ship-a-skill-for-running-repo-tasks/skill-and-mcp-placement-research.md`:

- **Where the skill is installed from decides which version it describes.** A tool installed with
  `uv tool install` or pinned in a consumer's `uv.lock` and a skill installed from the repo's HEAD
  can describe two different releases. graphify #1568 is that case, with a stale `uv tool` CLI
  beside a newer skill; beads #2493 is the reverse, guidance naming a removed command.
- **The skills CLI can pin to a tag, but the README does not say so.**
  `npx skills add
  <owner>/<repo>#<ref>` and `#<ref>@<skill>` are parsed in vercel-labs/skills
  `src/source-parser.ts:284-314`, the lock records `ref` "for ref-aware updates"
  (`src/skill-lock.ts:21,29`), and Prisma's docs use `skills#v<version>`.
  `gh skill install
  owner/repo skill@version` resolves to the latest tagged release by default.
  Whether `npx skills update` respects a pinned `#ref` is unverified.
- **Two designs that avoid drift**, both seen in several tools:
  - discovery-first: the skill names a few entry points and sends the agent to the tool's own help
    for everything version-specific (Backlog.md `backlog instructions`, beads `bd prime`, firecrawl
    `<cmd> --help`);
  - generated: the skill is generated from the command tree, committed, and CI fails on a diff
    (googleworkspace `gws generate-skills`, sentry-cli, gogcli).

  Copying a skill into place with no check is the design that drifts. Every Python tool that does it
  (comfy-cli, graphify, spec-kit) later added a hash or version stamp plus a check command.
- **Python has no package-manager mechanism.** npm has TanStack Intent, antfu's skills-npm, and a
  `skills sync` RFC opened 2026-09-28 (vercel-labs/skills #2323). Nothing equivalent scans
  `site-packages`.

## Evidence

- Transcript `0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl`, 2026-09-28T20:37:04Z, the user: "maybe we
  need to revisit the agent-skill exclusivity rule. look online how other projects or authors do
  this. shipping an agent skill or an mcp with an app/tool seems intuitive, but i'd like data and
  your expert analysis on this."
- The same session filed a companion plan for power-user-linux-setup: its global rule "every skill
  on this machine is authored in `agent-skills`" drops the exception this skill already makes.

## Open questions

[NEEDS CLARIFICATION: **Does it belong in `skill-authoring` or in a `references/` file?** The rule
is two or three sentences. The drift evidence is rationale and fits the "body is what an agent must
follow" split.]

## Recommended direction

1. Extend "Publishing a skill repo" after the paragraph on a repo's own interface: prefer
   discovery-first or generated content over a hand-kept command list; guard a hand-written skill
   with a test that every command it names exists; install it from a release tag with `#<ref>` when
   the tool is itself installed at a pinned version.
2. Put the evidence and the rejected option (copy-install without a check) in
   `references/rationale.md`.
3. Confirm whether `npx skills update` keeps a `#ref` pin before writing it down as the way to pin.
