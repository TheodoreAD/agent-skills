---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: 44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl
source_moment: 2026-09-28T09:32:44Z
source_plan:
---

# `set-status` writes a free-text status unquoted, so a colon-space in it breaks the frontmatter

## Context

`blocked on <reason>` is free text by design, and a reason naming a config key or a syntax contains
`:` naturally. `set-status` writes the value as a plain YAML scalar. A plain scalar cannot contain
`:`, so the line parses as a nested mapping, or not at all. Nothing in `set-status` or the gate it
runs says so. The first to notice is whatever next formats or parses the file as YAML.

## Evidence

repo-tasks session `44be2918-1669-4d16-9f77-56535cc6ddeb`. The command was
`plans.py set-status plans/2026-09-28-upstream-waits-on-actionlint-and-act.md "blocked on actionlint and act accepting uses: $/, checked at every consumer sweep"`.
`set-status` accepted it and printed the transition. The commit (`7f6c8a7`) was pushed, and CI's
`dprint check` failed on it (run `36404159867`, exit 20): dprint's YAML plugin read `status:` as
opening a mapping and wanted `updated:` indented under it. It was fixed in `294d496` by rewording
the reason to have no colon. It surfaced only because this repo's gate formats frontmatter. A repo
that doesn't would carry frontmatter that any real YAML parser either rejects or reads as
`status: {…}`.

One of three misuse shapes: **followed and still produced the wrong outcome**. The rule "status is
set-status' output, never typed" was followed exactly.

## Recommended direction

Have `set-status` refuse, or quote, a value a YAML plain scalar cannot hold: anything containing `:`
or `#`, or starting with an indicator character. Quoting keeps the reason as the user wrote it.
Refusing keeps the frontmatter free of quoting that `list` then has to strip. Check what
`plans.py`'s own frontmatter reader does with a quoted value before choosing, and add a test with a
colon-space reason either way.

## Migrated to

- **The code:** `yaml_scalar` and `unquote_scalar` in `skills/plan-conveyor/scripts/plans.py`, with
  the incident in `yaml_scalar`'s docstring. `set-status`, `new --status` and
  `migrate start --status` all write through it.
- **Tests:** `test_set_status_quotes_a_reason_a_yaml_plain_scalar_cannot_hold` and
  `test_yaml_scalar_leaves_an_ordinary_status_plain` in `tests/unit/test_plan_store.py`.

Quoting beat refusing: the reader already stripped quote characters, so a quoted value reads back
unchanged, and refusing would have made the user reword a reason that was correct. Single quotes
because their one escape, a doubled `'`, is trivially reversible. Not migrated: the evidence
section, which is incident narrative the docstring summarises.
