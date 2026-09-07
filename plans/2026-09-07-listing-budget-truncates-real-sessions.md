---
status: idea
updated: 2026-09-07
---

# The skill listing has already truncated in real sessions, not only in the model

## Context

Measured 2026-09-07 by `fitness.py report --root skills`. Two numbers, and the second is the one
that makes this a finding rather than an arithmetic exercise:

- **The model.** 10,981 chars of descriptions for these fourteen skills, plus 8,656 the harness
  lists and this tool cannot see, against a budget of 8,000 chars at a 200,000-token window. Every
  skill in this corpus is demoted to name-only in that simulation.
- **The observation.** 1,571 listings seen in the transcript store, 719 from real sessions; the
  largest actually sent was **19,669 chars over 33 entries**, and **11 listings were truncated, 2 of
  them from real sessions rather than a probe**.

A truncated listing drops a description **whole** — the harness keeps or drops, it does not shorten
— so a skill in that state is a bare name with nothing to match a request against. Sixteen skills
have been observed in that state at least once, `polite-mcp-conventions` and `python-conventions`
eleven times each.

## Why this is not simply "write shorter descriptions"

[DECISION: a description is measured, not trimmed on a hunch — this corpus's standing rule, and the
reason this is filed rather than fixed. Published measurement (SkillsBench, 47,150 skills) puts
unmeasured model-authored descriptions **below having no skill at all**, so shortening the four
longest by eye is a change whose direction is unknown. `trigger.py candidate` scores a proposed
description against the real installed set before it is adopted, and that is the tool this wants.]

The four longest are `session-harvest` (1,040 listing chars), `plan-docs` (1,033),
`python-conventions` (949) and `python-refactor-audit` (925). The first two are also the two most
used skills on this machine by a wide margin — 140 and 20 explicit invocations — so they are the
worst candidates for a blind trim and the best for a measured one.

## Open questions

[NEEDS CLARIFICATION: **whose budget is it?** Of the ~19.7k chars observed, only 11.0k belongs to
this corpus; the rest is the harness's own entries and other installed skills. Trimming here cannot
recover more than half the overflow, and a corpus that shrinks while the harness's grows has bought
nothing. Worth measuring what the non-corpus half actually is before spending effort on this half.]

[NEEDS CLARIFICATION: **does priority make the overflow harmless in practice?** The listing is
ordered by `skillUsage` priority with a 7-day half-life, so the skills that lose their description
first are the ones nobody has invoked — which is the five in the sibling plan. If the ones that
matter never get dropped, the finding is about idle skills paying rent rather than about lost
triggers. The two truncated real-session listings are the evidence to read: which skills were
name-only in them, and did any request in those sessions want one?]

[NEEDS CLARIFICATION: **is the 8,000-char budget still right?** It was read out of the CLI binary on
2026-08-31 (1% of a 200k window). A larger window moves it, and the model's "everything demoted"
verdict is sensitive to that constant in a way the observed truncations are not.]

## Recommended direction

Answer the second question first, from the two real truncated listings already in the store — it is
free and it decides whether the rest is worth doing. Only then consider a measured trim of the
longest descriptions, and only through `trigger.py candidate`.
