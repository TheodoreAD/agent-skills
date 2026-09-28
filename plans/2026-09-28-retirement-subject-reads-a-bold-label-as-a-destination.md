---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/power-user-linux-setup
source_session: b73129dd-6136-41c3-a026-8e871581bc14.jsonl
source_moment: 2026-09-27T22:24:00Z
source_plan:
---

# A retirement's derived subject reads a bold bullet label as a destination

Relates to `plans/2026-09-22-deterministic-plan-commits-and-migration.md`, which designed derived
subjects; this is a defect in one reader, not a change to that design.

## Context

`plan-conveyor/scripts/plans.py` `migrated_destinations()` builds the retirement subject from a
plan's `## Migrated to` bullets. It reads **only a bullet's first physical line**, and takes the
first backticked span on it or, failing one, the text before `—`. A bullet shaped
`- **Label**: prose …`path`` whose path lands on a wrapped continuation line (dprint wraps at 100)
therefore contributes its bold label verbatim, `**` included.

## Evidence

Pushed commit `5065fea` in `power-user-linux-setup` (2026-09-27, retiring
`2026-09-26-a-removed-export-lives-on-in-the-session-manager.md`) has the subject:

> plans: retire a-removed-export-lives-on-in-the-session-manager, migrated to tasks/zsh.py,
> Deliberately narrower than the "generic form" above**: no machine-wide scan for variables PULSE
> and 1 more

The second bullet began
`- **Deliberately narrower than the "generic form" above**: no machine-wide
scan for variables PULSE`
and its first backticked path sat on a later line.

**A second failure mode, in the same session.** `git log --grep='^plans: retire'` shows four derived
retirement subjects; two are clean, and one besides the above is misleading:

> plans: retire sweep-to-repo-tasks-v0-5-0, migrated to self-repository, plans/ and 3 more

The first backticked span in those bullets was a term the prose mentioned (the zizmor audit's name,
the directory being excluded), while the destination they named was `ci.yml` and `repo-tasks.toml`,
later in the same bullet. "First backtick" and "the destination" coincide only when the bullet leads
with its path.

## Recommended direction

Join each bullet with its indented continuation lines before reading it, and strip `**`/`__` from
the fallback text. Prefer a backticked span that looks like a path (contains `/` or a file
extension) over the first backticked span of any kind, and when a bullet has a bold label and no
path-shaped span, use the label, since that is what the author wrote as the item's name. Tests with
a wrapped bold-label bullet and a bullet mentioning a non-path term before its path pin both.
