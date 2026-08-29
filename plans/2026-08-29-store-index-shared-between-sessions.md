---
status: idea
updated: 2026-08-29
---

# The store's git index is shared, so another session's commit ships your staged file

## Context

`SKILL.md` tells a session writing a store plan to stage by explicit path and commit immediately:

```shell
git -C <store> add <the one path> && git -C <store> commit -m "<repo>: <what it is>"
```

and warns "stage by explicit path, never `git add -A` — a parallel session's half-written plan can
land between your write and your commit, and a blanket stage would ship it under your message."

That protects one direction only. The store is **one working tree with one index**, shared by every
session on the machine, so the same race runs the other way and explicit staging does nothing about
it.

[PITFALL: **`git add` in the store, then any parallel session's `git commit`, ships your file under
their message.** Measured twice in one session, 2026-08-29, in `~/plans`:

- `git add -- README.md` (the tier split's rewritten store README) was committed by another session
  as `efba4db "Queue the session-harvest step-0 case a dirty checkout makes"`.
- `git add -- <a plan filed for another repo>` was committed by another session as
  `0c069fb "power-user-linux-setup: absorbed four plans into the repo"`.

Both times the follow-up `git commit` reported `nothing added to commit but untracked files
present`
— which reads like the `add` failed, when in fact it succeeded and someone else's commit had already
taken it. Nothing is lost and no content is wrong; the commit message is simply about a different
change than the diff it carries, and `git log -- <path>` is the only way to find out where a file
actually landed.]

The window is not narrow. The rule that makes it likely is the skill's own: commit the moment the
plan is written, from every session, into one repository. The busier the machine, the more sessions
are inside that window at once.

## Open questions

[PITFALL: **`git commit -- <path>` is not the fix on its own — it refuses an untracked file**, which
is what every newly written plan is. Tried immediately, 2026-08-29:
`git commit -m … -- plans/<new file>.md` →
`error: pathspec … did not match any file(s) known to
git`. It commits named paths from the working
tree, but only paths git already tracks, so it closes the race for an _edit_ and not for the create
that the convention's commit-immediately rule is mostly about.]

[NEEDS CLARIFICATION: what closes the race for a create, then?
`git add <path> && git commit --
<path>` still needs the add, but the trailing pathspec means a
parallel session's staged work cannot ride along on _your_ commit, and their commit taking _your_
staged file is unchanged. Bounding one direction is already better than today. The alternative is a
per-file commit through a temporary index (`GIT_INDEX_FILE`), which closes both directions properly
and is a real mechanism to specify rather than a one-line habit — price it against how benign the
failure actually is.]

[NEEDS CLARIFICATION: how does whatever is chosen handle retirement, which stages a deletion with
`git rm`? That path genuinely wants the index, so a rule phrased as "never stage" would break it.
Test it before wording anything.]

[NEEDS CLARIFICATION: does the same hazard apply to a repo's own `plans/`? Parallel sessions share
every working tree on this machine, not only the store's, so in principle yes. It has not been
observed there, plausibly because two sessions rarely commit to the same repo within seconds of each
other, while the store is the one repository every session writes to. Worth deciding whether the
rule is store-specific or general before wording it.]

[NEEDS CLARIFICATION: should `plans.py` do it rather than telling an agent to? The script already
prints the exact `git -C <store> add … && git -C <store> commit` line after `new --for`. Printing
the safer form costs nothing. Actually running the commit is a bigger change — every other command
is read-only or moves files, and none commits — so it is a separate question from fixing the printed
advice.]

## Recommended direction

Fix the printed advice and the `SKILL.md` line together, since the printed line is what an agent
actually copies. The cheap version is adding the trailing pathspec to the commit —
`git -C <store> add <path> && git -C <store> commit -m … -- <path>` — which stops your commit
carrying someone else's staged work, costs one clause, and needs no new concept. It does **not**
stop the reverse, so the paragraph also has to say what the symptom looks like: a `git commit`
reporting "nothing added to commit" right after a successful `add` means someone else's commit
already took the file, and `git log -- <path>` says which.

Do not add a lock or a retry. The failure is benign — a correct diff under a wrong message — and a
locking scheme around a directory several independent agent sessions write to is far more machinery
than the problem justifies.
