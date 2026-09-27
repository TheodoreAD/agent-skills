---
status: landed
updated: 2026-09-28
---

# `skills-state` checks the skills a harvest leans on, not the skills a session changed

## Context

Found 2026-09-12 by a harvest of a three-day session in this repo that created one skill
(`repo-pitch`), gave another its first script (`skill-authoring`), and fixed a third
(`session-harvest`).

`skills-state`'s default set is the three skills a harvest itself relies on — `session-harvest`,
`plan-docs`, `session-bash-audit`. All three came back matching the checkout. The two skills this
session had actually **written** were not in the set, and adding them by hand with `--skill` turned
up the real finding: `repo-pitch`'s installed copy was stale on both `SKILL.md` and `scripts/`
against a clean, pushed checkout, four commits behind.

The gap is structural, not incidental. **The skills a session modifies are the ones most likely to
be stale-installed**, because modifying a source is precisely what makes an install fall behind —
and they are exactly the set the default omits. A harvest that runs the documented command verbatim
reports every skill it checked as current, in a session whose main output was skills that are not.

[PITFALL: **the documented escape hatch names the wrong population.** `SKILL.md` says to "add
`--skill <name>` for anything else this run used". A skill this session _changed_ is not the same as
one it _used_, and a session that authored `repo-pitch` without ever invoking it would not think to
name it. The run that found this only did because it had written the skill minutes earlier and
remembered.]

## Recommended direction

Derive the extra set from the transcript rather than asking the reader to remember it: any write
path under `skills/<name>/` in the session's own edit-tool calls adds `<name>` to the default set.
`harvest.py` already extracts write paths for the "files written outside every repository" section,
so the input exists.

[DECISION: **edit-tool writes only, as a stated limit** (2026-09-28), which is this plan's own
suggestion. `skills-state` adds every skill with a write path under `skills/<name>/` to the set,
prints `changed this session:`, and says on the next line that a shell-command change is not seen
and takes `--skill`. Parsing shell commands for writes would be the one check in this skill to leave
the tool-call seam every other one stays on.]

## Migrated to

- **The rule, the incident and the stated limit** — `_skills_written`'s docstring in
  `skills/session-harvest/scripts/harvest.py`, and step 0 of its `SKILL.md`, whose escape-hatch
  sentence the pitfall above faulted and which now names both populations (`509f856`).
