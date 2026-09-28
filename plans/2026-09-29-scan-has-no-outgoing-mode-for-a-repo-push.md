---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/power-user-linux-setup
source_session: 492154bb-2523-43a2-a2e5-9c4029ea5b08.jsonl
source_moment: 2026-09-28T21:15:00Z
source_plan:
---

# Scan has no outgoing mode for a repo push

## Context

`plans.py scan` has three modes: `tree`, `staged` and `history`. `push` already scans exactly the
range a push would publish (`outgoing_range`, `@{upstream}..HEAD`), but only for a plans store. For
an ordinary repo there is no way to ask "does anything I am about to push name private work?".
`staged` covers one commit before it is made. `history` covers everything ever published, so on a
repo with an old, known, already-owned hit it exits 1 on every run and cannot tell new from old.

That second property is what bit. power-user-linux-setup's adherence corpus now has two sessions,
samples 27 and 29 of `plans/2026-09-02-agents-md-adherence-sample-corpus.md`, that made 13 and 14
commits to a public repo without scanning before any of them. Sample 29's harvest then tried to
check retroactively:

- `scan --mode history` exited 1 with **55 hits**, every one from history before the session,
  already owned by that repo's `plans/2026-08-28-published-history-purge.md`. It said nothing about
  the session's own commits.
- The only way to scope it was to print `scan --list-terms`, write `git log -p a6eaa73..HEAD` to a
  file, and match the terms by hand in a `python3 -c` script. That is the hand-rolled pattern
  `plan-conveyor`'s SKILL.md warns against ("Never hand-roll the pattern for an audit"), done
  because the skill offers no scoped alternative. It found 0 hits in 7,830 diff lines, after the
  matcher was checked on a known positive.
- `--list-terms` printed the full private term list into the conversation to get there.

## Evidence

- Transcript `492154bb-2523-43a2-a2e5-9c4029ea5b08.jsonl`, the session's harvest, around
  2026-09-28T21:13Z to 21:16Z. The distinctive commands were `plans.py scan --mode history` (exit 1,
  "55 hit(s) over history") and the `git log -p a6eaa73..HEAD --output=…/session.diff` that followed
  it.
- Rule shape, per session-harvest's three: **not followed, repeatedly** (samples 27 and 29), and the
  instrument that should have checked it afterwards cannot be scoped.

## Open questions

[NEEDS CLARIFICATION: `--mode outgoing` reusing `outgoing_range` for any repo, or a `--range <a..b>`
option on `history`? The first answers the pre-push question with no argument to get wrong. The
second also answers a harvest's retroactive "this session's commits" question, where the range
starts at the session's first commit rather than at the upstream.]

[NEEDS CLARIFICATION: should the pre-push check become the documented gate for repos, as it is for
stores? Two sessions skipping `--mode staged` before every commit suggests one scan per push is the
gate that actually gets run. The global rule currently prescribes both, before and at commit time.]

## Recommended direction

Add `scan --mode outgoing` on top of `outgoing_range`, and consider `--range` for the harvest case.
Then point the public-repo rule and session-harvest's retroactive check at it, so neither needs
`--list-terms` or a hand-written matcher.
