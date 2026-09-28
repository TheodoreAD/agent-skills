---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/power-user-linux-setup
source_session: b73129dd-6136-41c3-a026-8e871581bc14.jsonl
source_moment: 2026-09-27T22:24:00Z
source_plan:
---

# A retirement's derived subject misreads its `## Migrated to` bullets

Relates to `plans/2026-09-22-deterministic-plan-commits-and-migration.md`, which designed derived
subjects; this is a defect in one reader, not a change to that design.

Merged on absorption, 2026-09-29, from three filings of the same defect: this plan (from
power-user-linux-setup), `2026-09-29-retirement-subject-two-more-samples-from-repo-tasks.md` (from
repo-tasks, which asked to be merged here) and
`2026-09-29-retire-subject-garbled-by-bold-migrated-to-bullets.md` (from ingesta, filed without
knowing this one existed). Their sources are under "Evidence".

## Context

`plan-conveyor/scripts/plans.py` `migrated_destinations()` builds the retirement subject from a
plan's `## Migrated to` bullets. It reads **only a bullet's first physical line**, and takes the
first backticked span on it or, failing one, the text before `—`. Three failure modes follow, seen
in three repos within two days:

1. **A bold label taken as the destination, `**` included.** A bullet shaped
   `- **Label**: prose …`path`` or `- **Label** — prose …` contributes its label verbatim. A
   bold-label bullet is the common shape for that section — the skill's own retirement examples and
   ingesta's sixteen retirements mostly used it — so this is not a corner.
2. **A path on a wrapped continuation line.** dprint wraps at 100, so a bullet whose path lands on
   line two contributes whatever its first line holds: a bold label, or plain prose up to the first
   dash.
3. **A first backticked span that is not the destination.** "First backtick" and "the destination"
   coincide only when the bullet leads with its path; a bullet that mentions a term first (an
   audit's name, a command, a directory being excluded) contributes that term.

## Evidence

**power-user-linux-setup**, session `b73129dd-6136-41c3-a026-8e871581bc14.jsonl`, 2026-09-27T22:24Z.
Pushed commit `5065fea` (2026-09-27, retiring
`2026-09-26-a-removed-export-lives-on-in-the-session-manager.md`) has the subject:

> plans: retire a-removed-export-lives-on-in-the-session-manager, migrated to tasks/zsh.py,
> Deliberately narrower than the "generic form" above**: no machine-wide scan for variables PULSE
> and 1 more

The second bullet began
`- **Deliberately narrower than the "generic form" above**: no machine-wide
scan for variables PULSE`
and its first backticked path sat on a later line (modes 1 and 2).

In the same session, `git log --grep='^plans: retire'` shows four derived retirement subjects; two
are clean, and one besides the above is misleading (mode 3):

> plans: retire sweep-to-repo-tasks-v0-5-0, migrated to self-repository, plans/ and 3 more

The first backticked span in those bullets was a term the prose mentioned (the zizmor audit's name,
the directory being excluded), while the destination they named was `ci.yml` and `repo-tasks.toml`,
later in the same bullet.

**ingesta**, session `e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl`, 2026-09-28T22:25:37+03:00. The
calcium research plan's deletion derived (mode 1):

```
plans: retire calcium-magnesium-phosphate-and-when-a-dose-is-given, migrated to The research body**, Prescriber questions** and 3 more
```

from bullets opening `- **The research body** — every section …`. Amended by hand to
`…, migrated to the driving case` (now `e4385bf`). Every earlier retirement in that session passed
`-m` and never saw the derived subject.

**repo-tasks**, session `0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl`, 2026-09-28T21:50:00Z. Retiring
`plans/2026-08-29-pytest-ini-anyio-mode.md`, whose `## Migrated to` opened (mode 2):

```markdown
- The two decisions, the in-process-predicate pitfall, the rejected AnyIO-in-the-manifest option,
  and verification on both sides of the predicate: `contributing/test-tiers.md`, "`anyio_mode`: the
```

`plans.py commit` derived:

> plans: retire pytest-ini-anyio-mode, migrated to The two decisions, the in-process-predicate
> pitfall, the rejected AnyIO-in-the-manifest option,, uv run --with and 4 more

The second bullet led with a mention of `` `uv run --with` `` and named `~/.agents/AGENTS.md` as
where it lives, which is where `uv run --with` in the same subject comes from (mode 3). The commit
(`766cc2e`) was amended by hand to a readable subject before the push, so neither sample is in
published history. Repo-tasks' earlier retirements that session derived clean subjects, because
their bullets led with a path.

**A shape to keep, possibly by design:** two repo-tasks retirements whose `## Migrated to` said only
"Nothing needed a new home" derived `plans: remove <topic>` rather than `retire … migrated to …`.
That reads correctly, since nothing migrated. Recorded so the fix does not change it by accident.

## Recommended direction

Join each bullet with its indented continuation lines before reading it, and strip inline markdown
(`**`, `__`, `_`, backticks) from each destination before joining. Prefer a backticked span that
looks like a path (contains `/` or a file extension) over the first backticked span of any kind, and
when a bullet has a bold label and no path-shaped span, use the label, since that is what the author
wrote as the item's name. Take a plain-text label before `—` rather than at the first space-dash.

Tests, one fixture each: a wrapped bold-label bullet (the power-user-linux-setup sample), a one-line
bold-label bullet with `—` (the ingesta sample), a plain wrapped bullet whose path is on line two
and a bullet mentioning a non-path term before its path (the two repo-tasks samples), and a "Nothing
needed a new home" section still deriving `remove <topic>`.
