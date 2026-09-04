---
status: idea
updated: 2026-09-04
source_repo: github.com-personal/ingesta
source_session: 54d36cb9-ba1c-4a48-8316-6f35ab58f452.jsonl
source_moment: 2026-09-04T14:15:25+03:00
---

# Editing a plan already in the store races with absorb, and the commit says nothing

## Context

`session-harvest` step 2 tells a session that finds its topic already owned to put its evidence
**into the existing plan** rather than filing a second one — "a second one splits the corpus the
first is accumulating". When that existing plan is in the store rather than in a repo, the sequence
is Edit, then `plans.py commit <path>`.

Between those two steps another session can absorb the file: `plans.py move --to repo` copies it
into the target repo's tree and **deletes it from the store**. The Edit has already landed, the
delete removes the file it landed in, and `plans.py commit <that path>` then commits the deletion —
under the message written for the addition.

## Evidence

Transcript
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/54d36cb9-ba1c-4a48-8316-6f35ab58f452.jsonl`,
2026-09-04, during a `/session-harvest` run in `ingesta`:

- 14:07 — appended a second measured sample to
  `github.com-personal/power-user-linux-setup/2026-09-04-adherence-watch-sample-ingesta-2026-09-04.md`
  in the store, following step 2's already-owned rule.
- 14:15 —
  `plans.py commit <that path> -m 'power-user-linux-setup: a second ingesta sample for the
  adherence watch'`.
- The result line ended `(removed)`. `git show --stat` on it: **76 deletions, 0 insertions.** The
  store directory was empty.

The content was not lost — the absorbing session had folded the whole file, this session's addition
included, into `power-user-linux-setup/plans/2026-08-23-global-agents-md-adherence-watch.md` and
committed it as `1b15e24 plans: three more adherence samples, and the watch finally has a baseline`.
**That was established by reading the target repo, not by anything either tool said.**

Two artefacts are left behind and neither is visibly wrong:

- A store commit whose message announces an addition and whose diff is a pure deletion. It reads as
  a filing in `git log` and is one of eight unpushed commits on a shared branch.
- No signal at any point that the edit had been carried elsewhere. `(removed)` is one word in a
  result line, in the position where `(new)` or a path normally sits.

## Open questions

[NEEDS CLARIFICATION: **whether `plans.py commit` should refuse a path that no longer exists.** It
committed a deletion it was not asked for, which is defensible — the deletion is real and someone
has to record it — but the message came from a different intent. The cheap fix is to say so:
`commit` already knows the file is absent, so a one-line "this path is gone; it was absorbed at
<sha>, and this commit records the deletion" would have turned eight minutes of checking into
reading one line. Refusing outright is the stronger option and risks leaving a deletion uncommitted
in a store other sessions are reading.]

[NEEDS CLARIFICATION: **whether `session-harvest` step 2 should say "re-read before you commit".**
The already-owned rule sends a session to edit a file it does not own, in a directory several
sessions write to concurrently, and says nothing about the interval. Every other race on this
machine is handled by re-deriving state immediately before acting — the force-push lease, the undo
by SHA, the ahead-count at report time — and this is the same shape with no such instruction.]

## Recommended direction

**Say it in the tool before saying it in the skill.** `plans.py commit` is where the fact is already
known, and a session that reads one line there needs no rule; a rule in `session-harvest` reaches
only harvests, while `commit` is called by every session that files anything.

Then the smaller half in the skill: step 2's already-owned bullet gains a clause that an edit to a
store file should be committed in the same breath, and that a `(removed)` result means the work went
somewhere else and the target repo is what confirms it.

**Not a data-loss bug, and worth being precise about that** — the absorb copied the file whole, so
the addition arrived. What failed is that nothing said so, and the session could equally have
concluded the opposite. The failure mode is a confident wrong report rather than a lost edit, which
is the same class as every other finding this skill's step 0 exists for.
