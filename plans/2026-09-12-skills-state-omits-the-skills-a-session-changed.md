---
status: idea
updated: 2026-09-12
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

[NEEDS CLARIFICATION: **whether a write through a subprocess should count.** The write-path signal
reads edit-tool calls only, so a `git mv` or a script that rewrote a skill is invisible to it — the
same tool-call seam every transcript-derived check in this skill carries. Probably acceptable as a
stated limit, since the common authoring path is the edit tool, but say so in the output.]
