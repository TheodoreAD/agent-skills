---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: b418c54c-c032-4559-9cf3-6370d926625b.jsonl
source_moment: 2026-09-28T19:53:30Z
source_plan:
---

# `skills-state` warns about calls running commits the install never received

Rule shape: **followed, and still produced the wrong outcome.** The harvest ran step 0 as written,
and the row told it that earlier calls might have run stale code, when they could not have.

## Evidence

`harvest.py skills-state` in the invoke-stubs session named above, for `plan-conveyor`:

```
checkout DIRTY (elsewhere in the skill) — ...; scripts/ moved after this skill entered context
(2 commit(s)) — a call made earlier in this session ran it as it was then, so read the diff before
trusting it
unpushed: a3e713b ...
unpushed: 92e8fca ...
unpushed: 68317d8 ...
moved since start: a3e713b ... (scripts/)
moved since start: 92e8fca ... (scripts/)
```

Both "moved" commits are also listed as **unpushed**, so no install ran from them. The installed
`plans.py` mtime was 2026-09-28 15:29 +03:00, hours before `plan-conveyor` loaded in that session
(~22:40 +03:00), and every call the session made went to the installed copy. So every call ran one
unchanged file, and "a call made earlier ran it as it was then" describes a change that never
reached anything the session executed.

The data needed to see that was already in the row, in two lines the verdict did not connect.

## Recommended direction

When the session's calls went to the installed copy (the transcript says which path they used), the
moved-since check for `scripts/` should compare against the **install's** history, not the
checkout's: a moved commit counts only if the install's mtime is after this skill's load instant.
Commits that are unpushed, or newer than the install, get one line saying they have not reached the
install, and no re-read prescription. The checkout-side reading stays right for a session calling
the checkout's scripts directly, which is the skills-repo case step 0 already carves out.
