---
status: idea
updated: 2026-11-27
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
- **The rate, measured 2026-09-28** for the scan-mode plan over 60 days of deduped Bash calls: in
  sessions that ran `plans.py scan` at least once, **1,201 commits had no scan of any mode since the
  previous commit**, across 116 sessions, against 1,236 preceded by a staged scan. Not filtered to
  publishable repos, so an upper bound — commits to the sensitive store and to work repos need no
  scan — but it says the gap is routine rather than rare. Deciding publishability is the part this
  row needs that `harvest.py` does not have yet: `scan` cannot tell, and `plans.py` derives it from
  `public_roots` or the roots routed `repo`.
- **A second sample, 2026-11-25**, filed from a hekate session (`5f84bc91-…`, at 18:29:44Z) and
  absorbed here. That session pushed the shareable store seven times in about an hour, every time
  with `git -C ~/plans push` and never with `plans.py push`, while it did use `plans.py commit` and
  `plans.py new`. So the skill was loaded; the rule that carries the scan was what it didn't follow,
  and no message weighed `plans.py push` and set it aside. The first push was denied by the
  auto-mode classifier; the user then approved a push through `AskUserQuestion`, and the session
  took that as approval for its own command rather than switching to the one the skill names.
  `session-bash-audit` over its last 427 Bash calls: `git-C-mutating` 8 (seven store pushes, one
  store commit), while `store-write-by-git` read 3 and caught none of the pushes. **That answers the
  question below: the row covers writes, not `push`.** `harvest.py sweep` again reported the store
  clean, and a retroactive `scan --mode history --path ~/plans` returned 0 hits against 61 terms.
  The plans store's `push` now runs the scan from `sync` too, so `plans.py sync` is a second
  sanctioned route that the row should accept alongside `plans.py push`.

## Recommended direction

Add a sweep row: for each touched repo that `plan-docs` classes as publishable, report this
session's commits and pushes, and the number of `scan` calls that preceded them. When it is zero,
the row names the retroactive command (`plans.py scan --mode history --path <repo>`) for the harvest
to run.

That retroactive command is unscopable on a repo with old, already-owned hits:
`2026-09-29-scan-has-no-outgoing-mode-for-a-repo-push.md` records it returning 55 pre-session hits
and saying nothing about the session's commits, and proposes `scan --mode outgoing` or `--range`.
This row should name whichever of those lands, not `--mode history`.

Also, a push to a plans store by any means other than `plans.py push` is itself a finding.
`audit.py` has a `store-write-by-git` row, and it covers writes only: it read 0 here and 3 in the
2026-11-25 sample while `git-C-mutating` caught every push. Extend it to match `push` too, so the
audit's own summary surfaces a bare-git store push rather than one sample line.

[NEEDS CLARIFICATION: should the row prompt the retroactive scan, or run it? Running it is read-only
and cheap. But `sweep` deliberately runs no repo's own commands, and `scan` belongs to `plan-docs`,
not to the repo.]
