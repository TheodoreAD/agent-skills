---
status: landed
updated: 2026-09-05
---

# `harvest.py --expect` silently fails to match a command containing double quotes

## Context

Found while running `/session-harvest` in `power-user-linux-setup` on 2026-09-05. The SKILL's step-4
guidance is to select the transcript by content when no id is to hand:
`harvest.py transcript --expect '<a command this session ran>'`. A natural choice is to paste a
whole command the session ran. If that command contains double quotes, the match fails and the
subcommand reports `no transcript resolved`, which reads as "wrong command" rather than "the matcher
cannot see this shape".

Reproduced this session:

- `transcript --expect 'git tag -l "SINGLE-LINE-TEST"'` → `no transcript resolved`.
- `transcript --expect 'git tag -l'` → resolved (2 candidates, took the most recent).

The more specific string, which is the one a user is more likely to paste, is the one that fails.

## The cause, confirmed

`_by_content(expect, cwd)` does `expect in path.read_text(...)` against the raw JSONL. The
transcript stores a Bash command as a JSON string, so its double quotes are escaped: the file holds
`git tag -l \"SINGLE-LINE-TEST\"`, not `git tag -l "SINGLE-LINE-TEST"`. A raw-substring search for
the unescaped form therefore misses. Verified:

```shell
rg -c 'git tag -l \\"SINGLE-LINE-TEST\\"' <this session's .jsonl>   # 3
```

So the escaped form is present three times; the unescaped form the user would type is absent. Same
failure for any command with `"`, and for single quotes stored inside a JSON string they are not
escaped, so the asymmetry is itself a trap — some quoted commands match and some do not, with no
signal which.

## Severity

Low. It fails safe: it errors clearly and never selects the wrong transcript, and the fix from the
user's side is to pass a quote-free substring or `--session <id>`. But `--expect` is the SKILL's
recommended robust selector for exactly the case where no id is to hand, and it breaks on the most
natural input to it, so the recommendation and the behaviour disagree.

## What landed

`b804ede`. A `_contains(expect, text)` helper compares the raw needle **and** its JSON-escaped inner
form, in both encoders — `json.dumps(..., ensure_ascii=False)` and the ASCII-escaping default —
because this script does not write the transcript and `JSON.stringify` leaves non-ASCII alone where
Python escapes it to `\uXXXX`. `_by_content` and the self-check on an explicitly-passed `--session`
both go through it; the self-check had the same defect and would have reported `NOT FOUND` for a
command the transcript holds.

**The stopgap was taken over decoding, and the reason is the cost rather than the effort.**
`_by_content` scans every transcript in the project and those run to megabytes each, so decoding
turns a substring scan into a JSON parse of the whole pool. Comparing escaped forms is exact for
this failure — any string inside a decoded JSON value appears in escaped form in the raw line — and
costs nothing.

Both tests the plan asked for, and the second is the one that matters: a matcher that had become a
matcher for anything would satisfy a positive case alone, so one test asserts the escaped form is
what is actually on disk before asserting the match, and the other keeps a genuinely absent quoted
needle missing.

Belonged in `agent-skills`, so filed here rather than edited from the `power-user-linux-setup`
session that found it.

## Migrated to

- **`skills/session-harvest/references/rationale.md`, "Why step 0's own instruments kept reporting
  clean"** — this as one of the four, and the half of the shape it belongs to: a check that fails
  loudly but misleadingly, where the message names the wrong cause.
- **`harvest.py`'s `_contains` docstring** — the escaped-form comparison, both encoders, the
  single-versus-double-quote asymmetry, and why comparing escaped forms beat decoding (a substring
  scan over a pool of megabyte transcripts becomes a JSON parse of all of them). Verified present.
- **`tests/unit/test_harvest.py`** — including the test that asserts the escaped form is what is
  actually on disk before asserting the match, which is what keeps a matcher for anything from
  passing.

Not migrated: the reproduction commands and the `rg -c` count. They are evidence for a fix that is
now pinned by tests.
