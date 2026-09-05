---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/ingesta
source_session: 6291d9d1-b8ed-4826-9967-9ae30f70bebf.jsonl
---

# `sweep` should say whether a listener is orphaned

## Context

`session-harvest`'s step 5 gained a rule on 2026-09-05 — commit `a09004d`, "an orphan that comes
back is a different finding" — whose operative check is stated only in prose:

> reparented to `systemd --user` exactly as before — **orphaned again rather than held by a live
> session, which is the check that tells the two apart**.

`sweep` prints the pid, age, and command line of every watcher and server it finds. It does not
print the parent, so the one fact the rule turns on is the one the harvest has to go and get.

## What happened

A harvest on 2026-09-05 found `http.server` on `127.0.0.1:8765` over the `ingesta` repo root, 13.6
hours old, `.env` and `.envrc` readable. Deciding what to report took two further calls that the
sweep had the data to answer:

- `ps -o pid,ppid,etimes,lstart` — to learn it was parented to pid 2376, and that its start time was
  36 minutes _after_ the harvesting session's last activity, so it was **not that session's**;
- `ps -o pid,comm -p 2376` — to learn 2376 is `systemd`, so it is reparented and therefore orphaned
  rather than held by a live session.

Both answers changed the report. Without the second, "orphaned" would have been an assumption; the
skill's own new rule exists because that assumption was wrong once already. Without the first, the
harvest would have reported another session's process as its own leftover — the same misattribution
step 5 already warns about for unpushed commits, arriving through a different door.

## Recommended direction

Have `sweep` print, per listener and per watcher, the **parent pid and its command**, and flag
`reparented to systemd --user` explicitly. Two derived lines are nearly free once the parent is
known and are what the harvest actually reasons about:

- **orphaned** — parent is `systemd`/`init`, so no session holds it;
- **started after this session's last activity** — comparable to the transcript's own last entry,
  which is what separates "my leftover" from "somebody else's process". The sweep already knows the
  session boundary, so this is a comparison rather than new data.

This is the "a correction a script can simply not make belongs in the script" case that `SKILL.md`
names in step 6: the rule was written as prose on 2026-09-05 and the very next harvest paid for it
in two manual calls. Cheap, and it removes the judgement that is easiest to get wrong — a listener
whose parent is a live shell is somebody working, and one whose parent is `systemd` is litter.

**It does not change what the harvest may do about it.** Killing stays the user's call, and the
existing rule that a returning orphan means the lifetime question owns the fix is unaffected.
