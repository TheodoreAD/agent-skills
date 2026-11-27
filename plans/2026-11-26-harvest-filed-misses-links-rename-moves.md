---
status: landed
updated: 2026-11-27
source_repo: github.com-personal/hekate
source_session: 5f84bc91-7291-42b4-9474-846d42d45b23.jsonl
source_moment: 2026-11-26T11:24:00Z
source_plan:
---

# session-harvest's `filed` reports plans a `links rename` moved as MISSING, cause not determined

## Context

`harvest.py filed` names three causes for a plan this session wrote that is no longer at its path:
retired by this session, absorbed, and renamed by this session's own `plans.py rename`. It has no
case for a store folder moved by `plans.py links rename`, which another session can run at any time
and which moves every plan under a repo's folder at once.

## Evidence

- Session `5f84bc91…`, harvest #4 at boundary 2026-11-26T13:22:36+02:00, in the hekate repo. `filed`
  listed 20 plan files this session wrote; 15 were `MISSING (cause not determined)`.
- Every one of those 15 still exists, moved from `~/plans/github.com-personal/<repo>/` to
  `~/plans/github.com/TheodoreAD/<repo>/` by another session's store commits of 2026-11-26 12:42,
  subjects
  `links: github.com/TheodoreAD/<repo> -> github.com/TheodoreAD/<repo>, named by
  repository`
  (a838fe6, 970655a, 10d4597, 1e44ec0). `git log --diff-filter=D` on the old paths returns exactly
  those commits.
- The cost: the step's own instruction for `cause not determined` is "find where it went before
  naming it", so a harvest after any folder rename spends a lookup per plan for a cause one commit
  explains. Here, three calls; on a session that filed more, more.

## Recommended direction

- When the deleting commit is a `links` commit (its subject starts `links:` or it renames a whole
  store folder), follow the rename to the new folder and print
  `moved by links rename to <new path>`, then report that path's state, the way
  `renamed by this session to <new>` already does.
- Attribute it as another session's move unless the session's own output shows the commit.

## Migrated to

- **The fix**: `a884e1b`. `missing_cause` treats a deleting commit with a `links:` subject as a
  move, reads the rename from that commit's file list, and reports
  `moved by links rename (<sha>) to <new>`, following the new path to `then absorbed` or whatever
  else became of it. SKILL.md step 8 names the cause; the test is
  `test_a_plan_a_links_rename_moved_is_followed_to_its_new_folder` in `tests/unit/test_harvest.py`.
- **A second sample**, 2026-11-27 in the agent-skills session `65662eda-…`: four undetermined rows,
  every one moved by the 2026-11-26 `links` commits and three then absorbed; all four resolve with
  the fix against the real store.
- Not built: the attribution line. The cause names the commit, and `filed` already says whose a
  commit is by its receipt, so a second attribution rule would duplicate it.
