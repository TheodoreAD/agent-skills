---
status: landed
updated: 2026-09-02
source_repo: /home/tdumitrescu/projects/github.com-personal/power-user-linux-setup
source_session: c79dac94-39d6-4b25-92de-0c373ee5cfe5.jsonl
source_moment: 2026-09-02T14:42:06+03:00
---

# `session-harvest`'s answer filter misses exactly the answers that carry the brief

## Context

`session-harvest` step 4 tells a run to extract `AskUserQuestion` answers as well as user turns,
because on a tool-driven session the answers carry the instructions. It then names the filter:

> Match the literal marker, not a heuristic. Every answer's tool result opens
> `Your questions have been answered:` and then quotes each question and the chosen option, so that
> string alone is an exact filter.

**That string is not an exact filter, and the answers it misses are the substantive ones.** When the
user picks a listed option, the result opens `Your questions have been answered:`. When the user
types custom text — the "Other" path, or an option plus notes — the result opens
`The user answered:` instead, and ends with a different trailer
(`Read the answers carefully — they
may request clarification, changes, or that you not proceed — and follow what they actually say.`).

The failure is worse than a miscount because the two populations differ in content. A listed option
is a word or two the harvest can infer from what the session then did; a custom answer is the user
writing prose about what they want, which is exactly what a harvest exists to recover.

## Evidence

Measured on this session (`power-user-linux-setup`, 2026-09-01→02, 350 Bash calls, 11 user turns):

| filter                               | answers found |
| ------------------------------------ | ------------- |
| `Your questions have been answered:` | 5             |
| `The user answered:`                 | **2**         |

The two under the second preamble were the session's whole brief for its second half:

- the four routing decisions for a docs revamp — catalog grouping, what happens to machine-specific
  pages, `ai.md`'s fate, `shortcuts.md` — including the user's own reasoning (_"'this machines' is
  meaningless. this points to nothing and varies by observer"_, _"the site shows what pulse does,
  the research goes to contributing"_, _"the user should have a list of shortcuts that are
  pulse-modified from defaults"_);
- the nav choice, whose answer carried the selected ASCII preview, plus `"everything on the list"` —
  the instruction that produced the next four hours of work.

A harvest following the skill as written would have found five answers of one to four words each and
concluded the user gave almost no direction, on a session where they gave a great deal.

[PITFALL: the marker rule was itself added to fix an over-broad filter, and its own confirming note
records the near-miss — "harmless here because both real ones were found, and precisely the shape
that returns a plausible, incomplete set on a session with more of them". This is that session. The
narrowing was right about heuristics and wrong about there being one literal marker.]

[PITFALL: three of the eight raw hits for the marker in this transcript are **false positives** — a
run that greps the transcript for the string finds the skill's own text quoting it, the harvest's
own extraction script, and that script's output. Any fix should filter on the tool-result block
rather than on the raw line, or the count is inflated by the harvest itself. Both preambles have the
same problem once `session-harvest` names them.]

## Recommended direction

1. In `skills/session-harvest/SKILL.md` step 4, replace the single-marker sentence with both
   preambles, and say which shape produces which — a listed option gives the first, a typed or
   annotated answer the first or the second. The reason to name the cause rather than just the two
   strings: a third preamble for a future answer shape would otherwise reintroduce this silently.
2. Say that the match belongs on the tool-result content, not on a raw transcript line, and why (the
   skill's own text contains both markers, so a line-level grep over a session that loaded the skill
   counts itself).
3. Worth considering: a one-line self-check to sit alongside the existing "grep for a command this
   session definitely ran" — compare the extracted answer count against a raw count of both markers,
   and say so when they disagree. It is the same shape as the exit-masked consequence check: cheap,
   and it converts a silent undercount into a visible one.

## What landed, 2026-09-02

Absorbed and applied the same day it was filed, by the session that had written the broken rule an
hour earlier. All three recommendations are in `skills/session-harvest/SKILL.md` step 4: both
preambles in a two-row table with the reason to match on the cause rather than the strings, the
anchoring rule with its numbers, and the self-check as its own sentence.

**Re-measured before writing it, on the transcript this plan cites, and the anchored count is not
what the plan reported.** Matching anywhere in a tool-result block gives 7 listed-option and 4
custom-text hits; matching only where the block _begins_ with a preamble gives **5 and 3**. The plan
said 5 and 2. So the finding is a little stronger than filed — three typed answers were being
missed, not two — and recommendation 2's anchoring is confirmed with its own figures rather than
asserted: it removes 2 false positives from one marker and 1 from the other, on a single transcript.

[DECISION: recommendation 3 was taken rather than left as "worth considering". This rule has now
been wrong twice in one day in opposite directions — a heuristic that over-matched, then a literal
marker that under-matched — and the second was shipped with a confirming note that described its own
successor's failure without recognising it. A third tightening of the match is not what that history
argues for; a check that makes an undercount visible is. It costs one sentence.]
