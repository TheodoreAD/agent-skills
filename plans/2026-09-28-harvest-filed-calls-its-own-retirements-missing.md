---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 76d98521-8e7c-4524-bb4f-4caeb36e8cb0.jsonl
source_moment: 2026-09-27T22:10:29Z
source_plan:
---

# `harvest.py filed` marks a plan this session retired as "MISSING (cause not determined)"

## Evidence

The first harvest of an invoke-stubs session that landed and retired eight plans. `filed` listed 15
plan files. Nine were `MISSING (cause not determined)`: eight retired by this session's own
`git commit -- plans/<file>` deletions, and one absorbed out of the store by repo-tasks (`510d5e1`,
which `filed` itself lists under the store as authorship unestablished). SKILL.md's step 8 already
says the cause decides the remedy, and that a retirement needs nothing. The script left all nine to
be re-derived by reading the session.

This is the common case for a well-run session, as step 8 itself says: "a well-run session hits this
more often than a sloppy one".

## Recommended direction

Two causes the script can establish without judgement, using the same receipt rule `filed` already
applies to store commits:

- **Retired here.** A deletion of that path in a commit whose receipt appears in this session's own
  output: print `retired by this session (<sha>)`.
- **Absorbed.** A store commit that removed the path and whose subject says "absorbed": print
  `absorbed (<sha>)`, attributed or not, since absorption is the landing.

Keep `cause not determined` for everything else. A negative test belongs beside it: a path deleted
by a commit that is not this session's must not read as retired.

## Migrated to

- **Both causes, the receipt rule and the negative case** — `missing_cause` in
  `skills/session-harvest/scripts/harvest.py`, the `MISSING` paragraph in its `SKILL.md`, and the
  parametrized test (`6cb8852`). Built as recommended, nothing declined.
