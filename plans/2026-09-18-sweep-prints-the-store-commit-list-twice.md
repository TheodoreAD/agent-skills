---
status: idea
updated: 2026-09-18
source_repo: github.com-personal/power-user-linux-setup
source_session: 81f41ac7-aec7-45e2-8d84-aad642024a13.jsonl
source_moment: 2026-09-18T10:23:11Z
source_plan:
---

# `harvest.py sweep` prints the plans store's unpushed commits twice

## Context

Measured 2026-09-18 in a harvest of a `power-user-linux-setup` session. The store held **32 unpushed
commits**, and one `sweep` run printed all 32 twice, about 64 lines of one report:

- `== repo /home/tdumitrescu/plans ==` lists them under `unpushed: 32 commit(s)`, each row
  `<sha> <iso timestamp> <author>: <subject>`, closed by the note that the ahead-count on a machine
  running parallel sessions is not necessarily this session's work.
- `== store plans /home/tdumitrescu/plans ==` lists the same 32 again, each row
  `unpushed: <sha> <author> <subject>`, closed by the different note that the cost is off-machine
  backup and nothing else, and that `absorb` reads the directory locally.

Both sections are load-bearing and neither note is redundant — they answer different questions, and
`SKILL.md` argues at length for keeping the store's bullet separate from the git bullet precisely
because each framing hands the finding to the other. **It is only the commit list that is
duplicated**, and it is the longest thing in either section.

The cost is small and worth stating as small: the report is read once, in a terminal, by a session
that has just spent its context on the work being harvested. It scales with the store's backlog
rather than with the session, so it is worst exactly when the store has been left unpushed for a
while — 32 commits here, and nothing bounds it.

## Evidence

Session `81f41ac7-aec7-45e2-8d84-aad642024a13.jsonl`, `sweep --boundary 2026-09-18T13:23:11+03:00`,
one run, the two sections adjacent in its output. The store was clean; only the ahead-count was
long.

## Open questions

[NEEDS CLARIFICATION: **which section keeps the list.** The git section already prints richer rows
(timestamps) and is where a reader looks for commit state; the store section is where the two
authorship and backup notes live. Printing the rows once in the git section and having the store
section carry its notes plus a count would keep both meanings. The alternative — cap the list and
print `… and N more` in whichever section repeats — costs less thought and fixes less.]

## Recommended direction

Print the commit rows in one section, keep both notes where they are, and have the other section
name the count and point at the rows. Whichever way round, a test over a fixture store with a
double-digit ahead-count is what stops it coming back, since the duplication is invisible on the
empty and one-commit cases every other fixture uses.
