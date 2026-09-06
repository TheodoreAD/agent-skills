---
status: landed
updated: 2026-09-06
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

## Migrated to

- **The behaviour** — `skills/session-harvest/scripts/harvest.py`: `parentage()` and
  `started_after()`, called from `processes()` and `sockets()`, printed by `_holder()`. Their
  docstrings carry the 2026-09-05 incident this plan describes.
- **The rule a reader follows** — `SKILL.md` step 5's processes bullet: read the sweep's own line
  rather than re-deriving it, and what each of the three `orphaned` verdicts means.
- **The reasoning** — `references/rationale.md`, "Why the sweep now says who owns a process and an
  image (2026-09-05/06)", which merges this plan with
  `2026-09-06-sweep-attributes-another-sessions-docker-images-to-this-one.md`: both are the same
  finding, that a timestamp inside the session window is not an attribution on a machine running
  parallel sessions.
- **Tests** — `tests/unit/test_harvest.py`: `test_a_listener_says_whether_a_session_still_holds_it`,
  `test_a_parent_missing_from_the_listing_is_unknown_rather_than_orphaned`,
  `test_a_process_started_after_the_sessions_last_activity_is_not_that_sessions`.

Not migrated: the two `ps -o` command lines this plan quotes, which are now what the sweep does
rather than what a reader types, and the closing note that killing stays the user's call —
`SKILL.md` and the skill's write-set section already say so, in more places than this plan did.
