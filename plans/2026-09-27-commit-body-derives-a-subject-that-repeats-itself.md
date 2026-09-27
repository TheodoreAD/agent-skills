---
status: idea
updated: 2026-09-27
source_repo: github.com-personal/freshful-polite-mcp
source_session: 0134b98b-f28c-4444-8923-f0c22c667296.jsonl
source_moment: 2026-09-26T23:58:00Z
source_plan:
---

# plans.py commit --body derives a subject that repeats the topic and stacks "adds Added"

Reports a fact about output, not a design proposal, which is why `source_plan` is blank.

## Context

`commit --body` is new (this store's `6f3e22c`, `32aac90`). First use from outside the authoring
repo, 2026-09-26: two plans in two different store mirrors, same topic filename, one shared heading
added to each. The derived subject came out as

```
temu-polite-mcp: robots-wildcards-are-inert-below-3-14 and robots-wildcards-are-inert-below-3-14: adds Added 2026-09-26: rebuilding the venv will break this repo's running MCP server
```

Three things compound in one line:

- **the identical topic is listed twice** — the two files are `.../temu-polite-mcp/<topic>.md` and
  `.../olx-polite-mcp/<topic>.md`, so the topic is the same and only the mirror differs, while the
  subject names one repo and then both topics;
- **`adds Added`** — the new section's heading begins with "Added 2026-09-26:", a natural way to
  head an addition to an existing plan, and the derivation prefixes "adds";
- the result is ~180 characters, where the `-m` form this replaced produced a subject the author
  chose.

The commit itself is correct and its body is exactly right; this is the subject line only. It is
permanent in the store's history, which is what makes it worth a filing rather than a shrug.

## Recommended direction

Rough — the derivation is this repo's to design:

1. **Collapse identical topics**: one topic, listed once, however many mirrors it spans. The repo
   prefix already says which store paths were touched, or could say "temu-polite-mcp and
   olx-polite-mcp: <topic>".
2. **Strip a leading date-stamped verb from the heading** before prefixing "adds" — "Added",
   "Update", "Fixed" and a date are how these headings read by convention, so "adds Added
   2026-09-26:" will recur rather than being a one-off.
3. Consider a length cap with an ellipsis, since a derived subject is the one part of the message
   nobody reviews before it lands.

[DECISION: **tidy, no cap** (decided with the user 2026-09-28). Items 1 and 2 above are done: a
topic is listed once however many mirrors it spans, and a leading "Added/Updated/Fixed <date>:" is
stripped from a new heading before `adds` (a bare verb without its colon is left alone, since "Fixed
point iteration" is a heading). Item 3 and the refusal were both declined. The derivation's own
retirement subjects routinely pass 100 characters — both retirements committed the evening this was
decided did — so refusing above ~70 would send every retirement back to `-m`, the one flow the skill
documents as needing no message. Truncating would cut the destination list, the part of a retirement
subject that says where to look.]
