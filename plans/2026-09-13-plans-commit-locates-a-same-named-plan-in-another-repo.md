---
status: landed
updated: 2026-09-13
---

# `plans.py commit` can resolve a store path to a same-named plan here, and commit nothing

## Context

Filed from a `power-user-linux-setup` session, 2026-09-12, which had just absorbed a plan and was
following `absorb`'s own closing instruction: _"Commit both: this repo (the additions) and the store
(the removals). The removals are one commit — `plans.py commit <path> <path> ... -m '<message>'`
takes the whole set."_

Run from `cwd = power-user-linux-setup`, with the store-relative path `absorb` had printed:

```shell
python3 .../plans.py commit github.com-personal/power-user-linux-setup/2026-09-12-adopt-the-shared-docs-generator.md \
  -m 'absorbed into power-user-linux-setup'
```

It reported `committed: 075f98407862 in .../power-user-linux-setup` — **the wrong repository**, and
the commit was **empty**: `git show --stat` lists no files. The store's deletion was still
uncommitted afterwards. The caller then committed the removal with a raw `git -C <store> commit`,
which is the `store-write-by-git` anti-pattern `session-bash-audit` scores, reached because the
sanctioned command had appeared to succeed.

## Evidence

The mechanism is visible at `skills/plan-docs/scripts/plans.py:3837-3842`:

```python
candidate = Path(name).expanduser()
if candidate.is_file():
    named.append(candidate.resolve())
else:
    named.append(deleted_plan(candidate) or locate(cfg, routing, name).path)
```

A store-relative path is not a file relative to the session's own repo, so it falls through to
`locate`, which matches on the plan's **basename**. The absorbed copy of that very plan now existed
at `plans/2026-09-12-adopt-the-shared-docs-generator.md` in the current repo — same basename,
already committed — so `locate` resolved to it, `repo_root_for` returned the session's repo, and
`commit_paths` committed an already-clean path.

[PITFALL: **this is the exact failure the command's own docstring says it exists to prevent,
arriving through its fallback.** That docstring reads: _"it is the one step where getting it wrong
is silent — a correct diff under a message about someone else's change."_ Here the diff is empty
rather than someone else's, which is worse in one way: there is no content to notice. The output is
four confident lines naming a commit, a message and a file, and every one of them is true about a
commit that changed nothing in a repo the caller did not name.]

[PITFALL: **the printed `file:` line reported the path as present, not as missing.** It renders
`(removed)` only when `target.exists()` is false; the located target existed, so the line read as an
ordinary success. Nothing in the output distinguished "committed the plan you meant" from "committed
a same-named file somewhere else".]

**The caller's invocation was wrong** — `--path <store>` is the documented way to point the command
at another repository, and it was not used. That is worth stating plainly and does not settle the
finding: a command that cannot find what it was handed should say so, not silently widen the search
to a basename match in a different repository and commit the result.

**`--path` would not have worked either, which is how the caller got here.** The retry
`plans.py commit --path /home/tdumitrescu/plans <store-relative path> -m '...'` exits 3 with
`verdict: needs-decision` — _"/home/tdumitrescu/plans is not under projects_root
(/home/tdumitrescu/projects), so its store path cannot be mirrored"_. That is `require_routable()`
treating the store as a project repo to route rather than as the store.

**An absolute store path does work from another repo, so "no invocation works" overstates it.**
Confirmed 2026-09-13 by the `agent-skills` session that absorbed this plan: from cwd `agent-skills`,
`plans.py commit /home/tdumitrescu/plans/github.com-personal/agent-skills/<four files> -m '...'`
committed `8ee9226` in the store, printed each file as `(removed)`, and added the note saying each
plan was absorbed rather than deleted. The path is missing, so it skips `is_file()` and reaches
`deleted_plan`, which resolves its repository from the absolute path itself; `locate` is never
consulted. The gap is the **store-relative** spelling, and that is the one the caller had to hand.

[PITFALL: **`absorb --apply` never prints the absolute store path it removed.** Its lines read
`absorbed: <basename> -> <destination in this repo>`, and its closing text says only
`plans.py commit <path> <path> ...`. A caller assembling the paths writes them relative to the store
it was just told about — the one spelling that falls through to `locate`. So the smallest fix may be
in `absorb`'s output rather than in `commit`'s resolution: print the exact command, absolute paths
filled in.]

## Open questions, answered 2026-09-13

Decided together, as step 2 below asks, and landed as `d36864d`, `910c71b`, `11d5ac3` and `edc92fb`.
The collision was reproduced as a test first, and it failed exactly as filed:
`committed: … in …/agent-skills`, the absorbed copy's path, and no store change.

- **Scope the basename fallback, refuse a separator, or drop it?** Refuse a separator. A path is
  tried under the working directory and then under each store, as a file and as a deletion `HEAD`
  still holds, and one that resolves nowhere is an error naming where it looked. A bare filename
  still searches.
- **Refuse an empty commit outright?** Yes, and neither fix made the other unnecessary. The question
  was right that something let an empty commit through: `commit_paths` builds the commit with
  `commit-tree`, which records an unchanged tree where `git commit` would refuse. A tree equal to
  `HEAD`'s is now refused. With the resolution fix alone a same-named collision can no longer reach
  it, but a race with another session committing the same change can.
- **What should `commit` do when cwd is not the store and the target is?** Resolve the
  store-relative spelling in the store, from any repo. `absorb --apply` also prints the command with
  those paths filled in. `--path <store>` still exits 3, because the store is not a project to
  route. With both of the above there is no longer a reason to reach for it, so no `--store` flag
  was added.

## Recommended direction

1. Reproduce from a repo that holds an absorbed plan of the same basename — the whole finding rests
   on that collision and it is cheap to stage.
2. Decide the three questions above together. They are one behaviour seen from three sides, and
   fixing the fallback alone would leave the post-absorb case with no working invocation, which is
   what sent this session to raw `git -C`.
3. Whatever lands, make the failure loud. The cost here was not the empty commit, which was reverted
   in one `git reset --soft`; it was that the command reported success and the caller believed it.
