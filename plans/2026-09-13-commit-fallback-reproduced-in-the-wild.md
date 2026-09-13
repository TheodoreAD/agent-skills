---
status: idea
updated: 2026-09-13
---

# The `plans.py commit` basename fallback reproduced itself a day later, unprompted

Evidence for
[`2026-09-13-plans-commit-locates-a-same-named-plan-in-another-repo.md`](2026-09-13-plans-commit-locates-a-same-named-plan-in-another-repo.md),
which already owns the mechanism and needs no re-analysis. Filed separately only because this
session cannot write into `agent-skills`' tree; **merge it into that plan and delete this one.**

## What this adds

That plan's recommended direction opens with _"Reproduce from a repo that holds an absorbed plan of
the same basename — the whole finding rests on that collision and it is cheap to stage."_ **It did
not need staging. It happened again on its own, 2026-09-13, in `repo-tasks`, to a session that had
never read the plan.** That discharges step 1 with a wild instance rather than a contrived one,
which is the stronger form of the same evidence.

The sequence matched the filed analysis at every step:

1. `plans.py absorb --apply` moved `2026-09-12-venv-sync-needs-an-extras-selector.md` into
   `repo-tasks/plans/`, and its closing text prescribed
   `plans.py commit <path> <path> ... -m '<message>'`.
2. That copy was gated and committed here first, so **the same basename now existed in the current
   repo, already clean** — the exact collision the plan names.
3. `plans.py commit github.com-personal/repo-tasks/2026-09-12-venv-sync-needs-an-extras-selector.md`
   reported `committed: 20653a99fec7 in .../repo-tasks`. `git show --stat` listed no files: an empty
   commit in the wrong repository, output indistinguishable from success.
4. The retry with `--path /home/tdumitrescu/plans` exited 3, `verdict: needs-decision`, with the
   `not under projects_root` message the plan quotes verbatim.
5. The session reset the empty commit by SHA and fell through to
   `git -C /home/tdumitrescu/plans commit` — the `store-write-by-git` anti-pattern, reached exactly
   as the plan predicts, because the sanctioned command had appeared to succeed and the documented
   alternative had refused.

`session-bash-audit` then scored that one call as **both** of the session's two misses
(`store-write-by-git` and `git-C-mutating`), against 15/17 met. So the cost of this gap is currently
one anti-pattern per absorption, attributed to the session rather than to the tool.

## What is genuinely new, and it is small

**The absolute-path workaround was found by reading the tool's own `--help`, not by knowing it.**
That output advertises `--path PATH` as "a path inside the repo (default: cwd)" and says nothing
about an absolute argument behaving differently — so the caller tried `--path`, was refused, and
reached for git. The plan's third open question already asks what `commit` should do when cwd is not
the store; this is evidence that **`--help` is where the caller looks first**, and that a fix
landing only in `absorb`'s closing text would miss them.

Later in the same session the absolute form worked first time for four subsequent filings, once it
was known. Nothing about the tool changed in between.

[DEFERRED: merge into the owning plan as a second dated occurrence and delete this file. Nothing
here needs its own lifecycle — it is one plan's evidence section arriving through the store because
the measuring session was in another repo.]
