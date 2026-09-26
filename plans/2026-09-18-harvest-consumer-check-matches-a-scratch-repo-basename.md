---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/power-user-linux-setup
source_session: 4296eac1-732f-4827-874f-59063bcf404f.jsonl
source_moment: 2026-09-18T19:28:57+03:00
source_plan:
---

# The harvest sweep's consumer check matches on a repo basename, so a scratch repo named `clone` has consumers

## Context

`sweep`'s "repos on this machine that install a repo this session changed" section reported, in a
session that had never gone near any of it:

```
== repos on this machine that install a repo this session changed ==
    <job scratch dir>/tmp/tagprobe2/clone
      installed by: <a repo under a work root>
      installed by: <this machine's setup repo>
  a push here is a deploy there — report it and file it
```

The "changed repo" is a throwaway git repository the session created inside its own job scratch
directory to probe one question — whether `git pull` works in a `--branch <tag> --depth 1` clone. It
was `git init`-ed, given one commit and a tag, and abandoned. Its working-tree directory is named
`clone`.

Nothing installs it. The two named consumers are repos whose own files contain the word `clone` —
one of them a setup repo with a `git-clone` install method and a `git clone` line in its installer,
which is as ordinary as a string gets.

## Evidence

- Sweep run 2026-09-18 against session `4296eac1`, boundary `2026-09-18T19:28:57+03:00`.
- The scratch repo's full path sits under the harness's own job directory, which is deleted when the
  job is. It has no remote; the same sweep's CI section reported
  `failed to determine base repo: none of the git remotes configured for this repository point to a
  known GitHub host`
  for it, and its git section printed `no upstream for HEAD — nothing to count
  against`. So three
  separate sections each spent output on a directory that is scratch by construction.

[PITFALL: **this is the lesson the neighbouring check already learned, in a section that did not get
it.** "Plans elsewhere naming a source file this session changed" prints
`not searched: __init__.py — every package has its own, so a match names no subject`, and the same
run showed that working correctly. The consumer check has no such exclusion, and a bare English word
as a repo's directory name is exactly the same failure: the match names no subject.]

[PITFALL: **the false positive is not harmless, because of what the section's own line says next.**
It ends `a push here is a deploy there — report it and file it`, which invites the reporting session
to file a cross-repo obligation against two repos that have none. One of the two was under a work
root, so a session that took the line at face value would have been a step away from writing a
client's repo name into a report — and, if it filed the plan the line asks for, into the shareable
plans store.]

## Open questions

[DECISION: **scratch roots only; no common-word stoplist yet.** Settled 2026-09-26, in line with the
user's standing concern that false positives cost analysis on every harvest while this family rarely
has the propagating shape. Excluding the temp directory and the harness's job directories removes
this instance from all three sections at once. The stoplist answers a repo legitimately named `docs`
or `tools`, which has not occurred; add it the first time one does, with a `not searched:` line in
the plans check's shape.]

[DECISION: **a no-remote repo outside a scratch root is still swept.** Settled 2026-09-26: a
no-remote repo elsewhere may be real local-only work, and the scratch-root predicate already covers
the case that was noise. Remote-ness is not used as a signal at all.]

## Recommended direction

Treat the harness's job scratch directory as out of scope for the repo set, since that is one
predicate covering the git, CI and consumer sections together, and add the consumer check's own
`not searched:` line for basenames that are ordinary words — reported rather than silently dropped,
the way the plans check already does it.

Whatever the fix, the section's closing line should not tell the reporting session to file against a
consumer the check is not confident about. That line is what turns a noisy row into an action.

**Kept apart from `2026-09-18-sweep-consumer-warning-does-not-read-its-own-trigger.md` at
absorption, 2026-09-26**, deliberately: same section and same closing line, different cause. That
one is a _real_ consumer whose documented trigger the check never compares against the changed
paths; this one is a consumer that does not exist. Both want the closing line made conditional, so
whichever lands first should word it for both.

## Migrated to

Landed 2026-09-26 in `4301bec`, together with its sibling.

- **The scratch-root exclusion and its instance** — the `_touched_repos` docstring and
  `_scratch_roots` in `skills/session-harvest/scripts/harvest.py`; step 5's consumer bullet in
  `skills/session-harvest/SKILL.md`;
  `test_a_throwaway_repo_under_a_scratch_root_is_set_aside_not_swept`.
- **The conditional closing line** — `_print_consumers`, worded for both plans.
- **Not migrated:** the common-word stoplist, deferred per the first decision.
