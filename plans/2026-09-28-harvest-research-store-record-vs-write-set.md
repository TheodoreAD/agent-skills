---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: 44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl
source_moment: 2026-09-28T09:25:00Z
source_plan:
---

# session-harvest tells a harvest to record a research-store divergence its own write set forbids

## Context

session-harvest's step 5, the shared-stores bullet about `$RESEARCH_HOME`, says that a deliberate
divergence from the store's shape (a deepened `--depth 1` clone, say) should be recorded, "and why,
in whatever file that store uses for per-entry metadata", meaning the entry's `SOURCE.md`. The
procedure's opening paragraph limits a harvest to three write locations: the session repo, its
`plans/`, and the plans store through plan-conveyor. The research store is none of these.

Kind of misuse, per the skill's three shapes: **a contradiction inside the skill**, found while
applying it. The session had to pick one instruction over the other.

## Evidence

repo-tasks session `44be2918-1669-4d16-9f77-56535cc6ddeb`. The session ran
`git fetch --depth 50 origin main` in `$RESEARCH_HOME/repos/github.com--rhysd--actionlint`, to check
whether upstream actionlint knows the `ubuntu-26.04` runner label. HEAD stayed at `011a6d1`,
matching `SOURCE.md`'s `ref`, and the clone's history went from 1 commit to 91. The harvest's sweep
attributed the changed entry correctly, the write set won, and `SOURCE.md` was left untouched. The
divergence is recorded only in the harvest report and here.

## Open questions

[NEEDS CLARIFICATION: widen the write set to include the research store's per-entry metadata, since
it is a store like the plans store, managed by the research-library skill; or change step 5 to say
report the divergence, and record it through research-library's own command if it has one?]

## Recommended direction

Prefer routing through research-library: if `library.py` has, or grows, a way to annotate or
re-normalise an entry, step 5 names that command, and the write set stays as stated. A harvest then
never hand-edits a store another skill owns.
