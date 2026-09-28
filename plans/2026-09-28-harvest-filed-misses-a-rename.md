---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/ingesta
source_session: 20a2d59c-46f5-4aba-af3d-967f7ac699d9.jsonl
source_moment: 2026-09-28T18:52:06Z
source_plan:
---

# `harvest.py filed` reports a plan this session renamed as `MISSING (cause not determined)`

## Context

`filed` names two causes for a plan this session wrote that is now gone —
`retired by this session
(<sha>)` and `absorbed (<sha>)` — added 2026-09-28 so a well-run session is
not handed rows to re-derive. A third ordinary cause is missing: `plans.py rename`, which
`plan-conveyor` prescribes over `git mv` precisely so attachments and citations move with the file.

## Evidence

The ingesta session named above absorbed a store plan, merged a second into it, then ran
`plans.py rename plans/2026-09-18-pin-the-application-tier-at-3-14.md pin-python-version-3-14`
(between 18:23:30Z and 18:26:55Z, before its first ingesta commit). The file was never committed
under its old name in ingesta — `absorb --apply` wrote it untracked, and the rename happened before
the first commit.

Its harvest at the moment above printed, from `filed --until`:

```
/home/tdumitrescu/projects/github.com-personal/ingesta/plans/2026-09-18-pin-the-application-tier-at-3-14.md  MISSING (cause not determined)
/home/tdumitrescu/projects/github.com-personal/ingesta/plans/2026-09-18-pin-python-version-3-14.md  MISSING (retired by this session (dbb956b92))
```

Both rows are one plan. The second is correctly classified; the first sends the reader to "find
where it went", which the session's own output already said: the `rename` call printed
`renamed: … to: 2026-09-18-pin-python-version-3-14.md`.

The case is not rare in the shape it arose from: absorbing and merging filed plans is where a rename
is most likely, since `plan-conveyor` says to keep the name that describes the merged subject.

## Recommended direction

Treat a `plans.py rename <old> <new-topic>` call in the transcript as a cause, the same way the
retirement cause reads the session's own commit output: print `renamed by this session to <new>` and
follow the new path, so its retirement (or presence) is what the row reports. Because the old name
may never have been committed, the cause has to come from the command, not from git.

## Migrated to

- **The code:** `plan_renames`, `rename_cause` and `_cause` in
  `skills/session-harvest/scripts/harvest.py`, the incident in `rename_cause`'s docstring.
- **Usage docs:** the `filed` causes paragraph in `skills/session-harvest/SKILL.md`.
- **Tests:** `test_a_plan_this_session_renamed_is_reported_as_renamed_not_missing` and
  `test_a_rename_flag_is_never_read_as_the_new_topic` in `tests/unit/test_harvest.py`.

The new name is derived from the command (date prefix kept, per `plans.py rename`) rather than from
the command's printed output, since the transcript's tool results are not paired with calls anywhere
else in `harvest.py`. A chain of renames is followed. Not migrated: the evidence section.
