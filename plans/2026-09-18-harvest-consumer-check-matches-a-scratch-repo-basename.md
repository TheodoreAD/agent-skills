---
status: idea
updated: 2026-09-18
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

[NEEDS CLARIFICATION: is the right fix to exclude scratch roots, to exclude common-word basenames,
or both? They answer different halves. Excluding the harness's own job directory and other scratch
roots removes this instance and every future one of its kind from all three sections at once, which
is the larger win; a basename stop-list in the consumer check alone still leaves a repo legitimately
named `docs` or `tools` matching everything. The `not searched:` line the plans check already prints
is the precedent for the second and shows the reporting shape.]

[NEEDS CLARIFICATION: should a repo with no remote be swept as a "repo this session touched" at all?
Every section that handled this one degraded — no upstream to count against, no GitHub host for CI —
and none of that is informative for a directory the harness deletes with the job. A no-remote repo
inside a known scratch root is a strong signal; a no-remote repo elsewhere may be somebody's real
local-only work and must still be swept.]

## Recommended direction

Treat the harness's job scratch directory as out of scope for the repo set, since that is one
predicate covering the git, CI and consumer sections together, and add the consumer check's own
`not searched:` line for basenames that are ordinary words — reported rather than silently dropped,
the way the plans check already does it.

Whatever the fix, the section's closing line should not tell the reporting session to file against a
consumer the check is not confident about. That line is what turns a noisy row into an action.
