---
status: idea
updated: 2026-09-26
source_repo: github.com-personal/repo-tasks
source_session: 86d02b45-c393-4ecd-96a7-75d16974465d.jsonl
source_moment: 2026-09-26T14:07:42Z
source_plan:
---

# session-harvest's sweep has no row for commits to a public repo made without a scan

## Context

Filed from a `repo-tasks` session's own harvest on 2026-09-26. The session made 13 commits and 8
pushes to `repo-tasks`, which is public, and pushed the shareable plans store with bare `git push`
rather than `plans.py push`. It never ran `plans.py scan`. That is the confidentiality gate, and a
miss there is irreversible.

**The harvest found this by accident.** `sweep` reported everything clean: nothing unpushed, CI
green, stores clean. `claims` reported 0 masked exits. The only trace was one `git-C-mutating`
sample line in `audit.py`'s output, `git -C /home/tdumitrescu/plans push`. Reading it prompted the
question "did a scan run before that?", and from there the question widened to the repo. Nothing in
the procedure asks it.

## Evidence

- `sweep` already knows which repos the session wrote to and pushed. `plans.py` already derives
  which roots are public (`public_roots`, or a remote on a personal account).
- The session's own transcript answers the rest: count `git commit` and `git push` calls per repo
  against `plans.py scan` calls before them.
- The retroactive `scan --mode history` over both repos came back 0 hits. That is the case that
  makes the row easy to drop, because it looks the same whether or not the gate ran. The adherence
  corpus in `power-user-linux-setup` has this shape at least twice, and this session is filed there
  as a sample.

## Recommended direction

Add a sweep row: for each touched repo that `plan-docs` classes as publishable, report this
session's commits and pushes, and the number of `scan` calls that preceded them. When it is zero,
the row names the retroactive command (`plans.py scan --mode history --path <repo>`) for the harvest
to run.

Also, a push to a plans store by any means other than `plans.py push` is itself a finding.
`audit.py` has a `store-write-by-git` row; check whether it covers `push` or only writes. It read 0
here while `git-C-mutating` caught the push.

[NEEDS CLARIFICATION: should the row prompt the retroactive scan, or run it? Running it is read-only
and cheap. But `sweep` deliberately runs no repo's own commands, and `scan` belongs to `plan-docs`,
not to the repo.]
