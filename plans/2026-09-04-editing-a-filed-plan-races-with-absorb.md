---
status: landed
updated: 2026-09-09
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

[DECISION: **say so, do not refuse.** Shipped 2026-09-09. `commit` still records the deletion —
refusing would leave it uncommitted in a store other sessions are reading, which is worse — and now
prints where the file went and the commit that added it. The destination is derived rather than
guessed: a store path is `<store>/<rel>/<name>` and `<rel>` is the repo's own path under
`projects_root`, so the file's parent directory names exactly where to look. It prints only when a
destination resolves, so a plain retirement is not told its plan was absorbed — which is the
difference between a useful note and a second confident wrong report.

The `<sha>` the question asked for is there too, read from the target repo's own
`log --diff-filter=A` rather than inferred.]

[DECISION: **yes, and as "commit it in the same breath" rather than "re-read before you commit".**
The rule that creates the exposure is the one that should mention it. Re-reading would only narrow
the window and would need a second instruction about what to do with the answer; keeping the
interval short removes it, and the tool now handles the case where it happens anyway.]

## What landed, 2026-09-09

Both halves, in the order this plan asked for: the tool first, the skill second.

## Migrated to

- **The race, and why the note prints only on a resolved destination** -> `absorbed_to`'s docstring
  in `plans.py`, plus `plan-docs`' "Commit a store plan the moment it is written" section.
- **The instruction that creates the exposure** -> `session-harvest` step 2's already-owned bullet,
  which now says to commit that edit in the same breath and what a `(removed)` result means.
- **Both halves of the distinction as tests** ->
  `test_commit_says_a_path_is_gone_because_absorb_took_it_not_because_you_deleted_it` and
  `test_a_plain_retirement_gets_no_absorbed_note`.

**Not a data-loss bug, and the migrated text keeps saying so** — the absorb copied the file whole,
so the addition arrived. What failed is that nothing said so, and the session could equally have
concluded the opposite. The failure mode is a confident wrong report rather than a lost edit, which
is the same class as every other finding this skill's step 0 exists for.
