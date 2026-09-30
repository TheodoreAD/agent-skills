---
status: idea
updated: 2026-09-30
---

# `new` and `migrate start` take an origin date for an older idea

## Context

Asked for 2026-09-30: a way to create a plan with a custom date, for picking up an older idea that
already has some content — notes in a scratch file, an old unscoped draft, a retired plan whose work
is live again. Today every plan created is stamped with the day it was typed, so the filename claims
the idea was born the day someone finally got round to it.

Where the date comes from now, read from `skills/plan-conveyor/scripts/plans.py`:

- `today()` is the only source. `write_plan` uses it for both the filename prefix and `updated:`,
  and `new`, `new --for` and `new --unscoped` all go through `write_plan`.
- `_migrate_start` builds its own path and frontmatter, and calls `today()` for both as well — a
  second copy of the same stamping that a change to `write_plan` alone would miss.
- `rename` already keeps an existing prefix (`old.stem[:10]`), so a date set at creation survives
  every later rename. Nothing else parses the prefix except the topic-stripping helper, which is
  date-agnostic, and `PLAN_NAME_RE`, which any valid date satisfies.
- `iso_date` already exists as an argparse type (used by `list --since`), so parse-time validation
  is one keyword.

What the convention says the prefix means: `references/design-rationale.md` — "No `created:` field:
the filename's date already is the creation date". A backdated prefix changes that sentence, so this
is a small definitional change as well as a flag.

Found reading the code, not by hitting it: `test_new_refuses_a_second_file_for_the_same_topic` is
named for a topic but tests a path. The refusal in `write_plan` is `path.exists()`, so a live plan
on the same topic under a different date is not caught — true today across two days, and the
ordinary case once a date can be chosen, because the older idea is exactly the one likeliest to have
a file already.

## Open questions

[NEEDS CLARIFICATION: flag name. `--date YYYY-MM-DD` is the plain reading and matches `--since`'s
metavar; `--dated` or `--origin` say what the date means rather than that it is one. Recommendation
below is `--date`, with the help text carrying the meaning.]

[NEEDS CLARIFICATION: does `updated:` follow the custom date or stay today? Recommendation: today.
`updated:` is freshness, the plan is being touched now, and `list --stale`, `list --since` and
`absorb`'s retirement-age throttle all read it — a backdated `updated:` would make a plan revived
this morning show as a month stale.]

[NEEDS CLARIFICATION: future dates — refuse, or allow? A future prefix is almost certainly a typo
(`2026-10-03` for `2026-09-03`); nothing legitimate wants one. Recommendation: refuse.]

[NEEDS CLARIFICATION: should `migrate start` offer a derived date — the earliest first-commit date
among its tracked sources, or the earliest `YYYY-MM-DD` inside them — instead of only an explicit
one? It is the case this request describes most directly: the content already exists, so its age is
on disk. Recommendation: explicit only for the first cut, derived as a follow-up, since the right
source (git add-date, mtime, a date in the text) differs per source kind and a wrong derivation is
silent.]

[NEEDS CLARIFICATION: same-topic, different-date collision — warn, or refuse? Refusing matches the
existing "update it in place rather than opening a second file" message and the absorb rule that two
plans on one topic are a merge. But a retired plan with the same topic is legitimately revived as a
new file per "Getting a retired plan back", and only live plans are in the directories `new` reads,
so refusing on live plans alone does not block that. Recommendation: refuse on a live plan in any
directory the route reads, naming it.]

## Recommended direction

1. **One `--date` flag, on `new` and `migrate start`**, `type=iso_date`, default today. Help text:
   "the day the idea began, when it predates this file (default: today)".
2. **Thread it through one helper, not two.** Give `write_plan` a `date: str` parameter and have
   `_migrate_start` take the same value, so the prefix has one source per call. `updated:` keeps
   `today()` in both.
3. **Refuse a future date** at parse time, same message shape as `iso_date`.
4. **Topic-level collision check** in `write_plan` and `_migrate_start`: any `*-<topic>.md` in the
   directories the route reads (repo `plans/`, store mirror, and for `--unscoped` the unscoped area)
   refuses, naming the existing file. Fixes the misnamed test's real intent for the today case too.
5. **Rewrite the rationale sentence**: the filename's date is the day the idea began — normally the
   day the file was created, earlier when `--date` says so — and still no `created:` field.
6. **SKILL.md**: one line under "Creating a plan", and one under "Consolidating a session's plans"
   pointing `migrate start --date` at the revive-old-content case. Mention in "Getting a retired
   plan back" that a revived plan may carry the original's date.

Tests, in `tests/unit/test_plan_store.py`: `--date` sets the prefix and leaves `updated:` today, for
`new`, `new --for`, `new --unscoped` and `migrate start`; a future date and a malformed date both
exit non-zero before writing; a live same-topic plan under another date refuses; `rename` of a
backdated plan keeps the prefix (already true, pin it).

Not in scope: re-dating an existing plan. `rename` keeps the prefix by design, and a `rename --date`
is only worth adding if the need shows up after this lands.
