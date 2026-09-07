---
status: idea
updated: 2026-09-07
---

# The derivable measure scores a skill clean when the command is missing entirely

## Context

`fitness.py derivable` measures which commands a skill makes an agent compose by hand, against the
rule that anything derivable deterministically belongs in `scripts/`. It reads **command lines in
fenced blocks** and sorts them into delegated, derivable and fixed.

Found 2026-09-07 while planning `research-library`'s clone lifecycle
(`2026-09-07-research-library-clone-size.md`): that skill scores **0 derivable, 6 delegated** — the
cleanest result in the corpus after the ones with no commands at all — while its single most
consequential operation has no script and no command line anywhere in it.

`SKILL.md`'s "Updating" section says, in prose: refresh every clone to its default branch's latest
commit, "a shallow fetch and hard reset", and "where the machine provides a refresher on `PATH` for
this, use it". There is no fenced block, so the measure sees nothing to classify. `library.py` has
no `update` subcommand. The behaviour lives in a script in a different repo that no reader of the
published skill has.

**A prose instruction that never becomes a command line is invisible to a measure that reads command
lines**, and it scores identically to a perfectly delegated skill. That is the worst direction for a
measure to be wrong in: the number agrees with what you hoped, on the row you had a specific reason
to check.

The measurement it hid was substantial. The correct re-shallow sequence turns out to be five
commands including one (`git tag -d $(git tag)`) that no reference material mentions and without
which the whole sequence reclaims nothing — exactly the "prose has to be followed correctly every
run and fails silently when it is not" case the rule exists for.

## Open questions

[NEEDS CLARIFICATION: is this detectable at all, or only reviewable? A heuristic — an imperative
section naming a tool (`git`, `gh`, `docker`) with no fenced block in it — would catch this case and
would also fire on every legitimate paragraph that mentions a tool in passing. A measure whose
output is mostly noise is one that gets switched off after its first run, which this file's own
tests already say about the derivable measure.]

[NEEDS CLARIFICATION: is the right unit a _skill_ rather than a _line_? "Which operations does this
skill name, and which of them have code behind them" is the question that was actually wanted, and
it is not answerable from command lines because the missing ones are, by definition, absent. It may
need the skill's headings — an "Updating" section with no delegated call under it is a specific,
checkable shape.]

[NEEDS CLARIFICATION: does this belong in `derivable` at all, or as a second measure? Conflating
"work an agent has to assemble" with "work nobody wrote down" may make both harder to read. A
separate `uncovered` roll-up beside it would keep each number meaning one thing.]

## Recommended direction

Do not reach for a heuristic first. Establish whether the shape is common: read the corpus's
imperative sections and count how many name an operation with no delegated command under them. If it
is one skill, this is a review finding and the fix is to fix that skill. If it is several, it is a
measure worth building, and the count is the evidence for which shape to detect.

Whatever comes of it, the honest short-term fix is a sentence in `skill-authoring`: **a clean
`derivable` score is evidence about the commands a skill prints, not about the operations it
describes.** That costs nothing and stops the next reader trusting a zero the way this one nearly
did.
