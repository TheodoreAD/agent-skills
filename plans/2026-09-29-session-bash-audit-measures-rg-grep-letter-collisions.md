---
status: idea
updated: 2026-09-29
---

# session-bash-audit should measure the other grep letters that change meaning in rg

## Context

`rg-replace` and `rg-replace-bundle` measure the `-r` carried over from `grep -r`. Three more
letters survive the same translation with a different meaning: `-L` (grep: files without a match;
rg: follow symlinks), `-h` (grep: no filename; rg: help) and `-I` (grep: skip binaries; rg: no
filename). Each fails silently: `rg -L` prints the matching lines, the opposite set, and `rg -h`
prints the help text and exits 0.

Confirmed 2026-09-28 in this repo, session `c7d58945`: an `rg -L "pip install" …` call, meant to
list the snippets that name no dependency, returned the ones that do. Caught only because the output
printed matched lines where a file list was expected; a second call reproduced it on purpose. The
always-loaded rule that produced it is filed for power-user-linux-setup as
`2026-09-29-rg-translation-keeps-three-letters-that-change-meaning.md`.

## Open questions

[NEEDS CLARIFICATION: one row or three. `-h` is always an accident inside a search (help ignores the
pattern), so it can carry a `zero` expectation like `rg-replace-bundle`; `-L` and `-I` have
legitimate uses in rg (following symlinks, dropping filenames), so they are unjudged rows that print
samples, the way `rg-replace` is.]

## Recommended direction

Add the rows to `audit.py`'s pattern table beside `rg-replace`, anchored the same way (command
segment start, short flag group), with tests from real samples. Then run it over the corpus to give
the power-user-linux-setup plan a rate before the rule's wording changes.
