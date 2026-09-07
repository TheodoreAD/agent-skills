---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: is the fix "correct the filed row" or "do not file adherence rows until the
session ends"? The second is cleaner and probably wrong — a harvest is invoked precisely because a
session might end, so a row filed at the first one is better than no row if the session stops there.
That argues for correcting, and therefore for the second harvest knowing what the first filed.]

[NEEDS CLARIFICATION: how does a second harvest _find_ what the first filed, rather than
remembering? The store is a git repository, so
`git -C $PLANS_HOME log --since=<session start>
--format=%H%x09%s` plus the session's own transcript
would name them mechanically. That is `harvest.py`'s kind of job — the "a correction a script can
simply not make belongs in the script" case — rather than another paragraph asking the agent to
remember.]

## Recommended direction

Extend step 8's second-harvest paragraph: a second harvest re-reads what the first one wrote into
the store during this session and updates any measurement that has moved, before writing its delta
report. Say plainly that the report is the cheap half and the filed artifact is the durable one, so
the correction matters more than the delta does.

If it becomes a script step, `harvest.py` already knows the session start and the store path;
listing this session's own store commits is a few lines and removes the remembering entirely.
