---
status: landed
updated: 2026-09-07
source_repo: github.com-personal/invoke-stubs
source_session: 6450239e-aad5-4861-acda-7eb9e97c15c6.jsonl
source_moment: 2026-09-07T10:55:00Z
---

# A second harvest reports the delta, but the first harvest's _filed plans_ still hold its numbers

## Context

Step 8 says a second harvest in one session "re-runs the whole sweep and reports only the delta",
which is right about the **report**. It says nothing about the artifacts the first harvest already
wrote, and those are the ones that outlive the terminal.

An adherence row filed by a mid-session harvest is a **prefix** of the session, and a prefix of a
session whose phases differ is not a smaller version of the whole.

## Evidence

Two harvests of one session in `invoke-stubs`, 2026-09-07, ~2h40m apart. The first filed
`2026-09-07-auto-mode-announcing-session-row.md` for `power-user-linux-setup`, carrying:

```
n=211  chain=36%  head/tail=20%  exit-masked=20% (34 gate, 8 listing)  sed-n=0%(1)
```

The second measured the same session at the boundary:

```
n=306  chain=44%  head/tail=27%  exit-masked=23% (49 gate, 20 listing)  sed-n=2%(7)
```

Every rate moved the wrong way, and `sed -n` went 1 → 7. The cause is ordinary and will recur: the
session's last third was a different kind of work — converting a bespoke script to the family's
pytest-and-tasks layout, so mostly reading five sibling repos' configs — and it chained and
`sed -n`'d far more than the stub-writing phase before it.

Nothing prompted the correction. The second harvest happened to remember it had filed the row, and
edited it by hand; had the user asked for one harvest instead of two, or had the same agent not been
holding that memory, the corpus would have taken the prefix as the session's row and nobody would
re-derive it.

## Resolved

[DECISION: the fix is "correct the filed row", not "do not file until the session ends". A harvest
is invoked precisely because a session might end, so a row filed at the first one is better than no
row if the session stops there — which makes the correction the second harvest's job, and makes
knowing what the first filed a prerequisite rather than a nicety.]

[DECISION: the finding is mechanical and lives in `harvest.py`, as the second question guessed.
`filed` counts this session's own step-0 `boundary` calls, so being the second harvest is read
rather than recalled; lists the plan files the session wrote with the lines in them carrying a
number; and lists each store commit since session start, attributed by the transcript's own write
paths. Attribution rather than a bare `--since` listing is the part the question did not anticipate:
the store is shared, so a commit inside the window is not this session's by virtue of being there —
the same trap the sweep's docker rows fell into on 2026-09-06.]

[PITFALL: the separator carrying `--name-only`'s file list off its commit header must be asked for
as git's own `%xNN` escape, never passed as a byte. An argv element may not contain a NUL, and the
`ValueError` raises inside `subprocess`, so no test with a fake runner reaches it — found on the
first live run of the new subcommand, after a green suite.]

## Recommended direction

Extend step 8's second-harvest paragraph: a second harvest re-reads what the first one wrote into
the store during this session and updates any measurement that has moved, before writing its delta
report. Say plainly that the report is the cheap half and the filed artifact is the durable one, so
the correction matters more than the delta does.

If it becomes a script step, `harvest.py` already knows the session start and the store path;
listing this session's own store commits is a few lines and removes the remembering entirely.

## Migrated to

- **The rule** — `skills/session-harvest/SKILL.md`, step 8, the two paragraphs following "A second
  harvest in one session re-runs the whole sweep". They carry this plan's evidence (both rate rows,
  and why the last third of that session differed), state that the filed artifact matters more than
  the delta, and name the two boundaries this plan did not reach: correcting a store plan is inside
  the procedure's write set, and one already absorbed into the repo that owns it takes a new filing
  rather than an edit.
- **The mechanism** — `skills/session-harvest/scripts/harvest.py`, the `filed` subcommand, whose
  docstring keeps the 2026-09-07 evidence next to the code it justifies. Both `[DECISION:]` items
  above landed there.
- **The corrections made permanent** — `tests/unit/test_harvest.py`, section "what an earlier
  harvest in this session already filed": the harvest count read from the transcript, attribution of
  a store commit, a failing `git log` reported rather than read as "nothing was filed", and the
  `[PITFALL:]` above.

Not migrated: the plan's framing of both items as open questions, which the change answers, and its
suggested `--format=%H%x09%s` command line, which the subcommand supersedes.
