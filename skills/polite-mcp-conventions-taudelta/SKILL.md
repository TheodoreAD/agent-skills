---
name: polite-mcp-conventions-taudelta
description: "Use when working in one of the *-polite-mcp personal automation repos (olx-polite-mcp, emag-polite-mcp, altex-polite-mcp, freshful-polite-mcp, temu-polite-mcp) or product-research-pipeline — implementing a new tool, running a live spike/CDP exploration against a real logged-in site, deciding whether an action needs confirmation before running it, or asking the user for several small per-item decisions (quantities, yes/no per item) during a reorder/shopping flow. Covers: confirming before the first live mutating action against a real personal account, batching interactive AskUserQuestion decisions instead of asking for a typed list, and writing spike/research findings into PLAN.md before or alongside implementing."
---

# Polite-MCP family: agent collaboration conventions

Behavioral conventions for this author's own shopping/classifieds automation family —
`olx-polite-mcp` and its siblings, which exist on this author's machine and nowhere else — distinct
from `mcp-server-shipping` (dev-loop/distribution mechanics for the same repos) and from whatever
always-loaded instructions file the machine carries, which holds the truly universal conventions.
These are specific to the domain: automation against a user's own live, logged-in personal accounts.
Installed elsewhere, the conventions still read; the repo names are the author's.

## Confirm before the first live mutating action

Before performing the _first_ real mutating browser action against the user's live, personal,
logged-in account in a session (e.g. a real add-to-cart click, not a dry read), stop and ask via
`AskUserQuestion` rather than just doing it — even when the action is narrowly scoped, low-cost, and
reversible. Frame it as a one-off scoped test (what will run, and that it'll be undone/reverted
afterward if applicable), not a generic permission request. Once approved and the shape/behavior is
confirmed, subsequent same-kind actions in the same session don't need re-confirming.

**Why:** this family already treats checkout/personal-account actions as a materially higher-stakes
category than plain reads — every repo's own boundary docs say so (e.g. "checkout is never
automated," no-CAPTCHA-solving). A first live mutation test against a real account fits that same
category even when the specific action itself is small. Confirmed live in `freshful-polite-mcp`
(2026-08-14): asking before the first add-to-cart test got a clean, low-friction "yes, test on one
cheap item" — the right default, not overcaution.

## Batch interactive per-item decisions, don't ask for a typed list

When a workflow needs several small independent decisions from the user (e.g. "how many of each of
these 8 items do you want?"), use `AskUserQuestion` in batches of roughly 4, with a recommended
default pre-filled as the first option — don't present a big list and ask the user to type out
answers for all of them in one reply.

**Why:** explicit feedback during a Freshful reorder-flow session — "suggest some quantities for all
those things, and ask me one by one, it needs to be interactive, if i have to type all that stuff
out it kills the ux." Typing a long structured reply is worse UX than a short guided Q&A, even
though both convey the same information.

**How to apply:** reserve a single free-text ask for decisions that aren't decomposable this way, or
where there are too many items for batching to stay lightweight — at that point, consider whether
the flow itself needs restructuring (e.g. splitting "items likely due" from "rarely-touched items"
rather than batching everything flat).

**When the page is many homogeneous items with a sane default each** — quantities over a product
list is the case — and it runs past what two `AskUserQuestion` calls cover, a pre-filled table the
user edits by index is the lighter shape, and it is the same rule rather than an exception to it:
the objection was always to typing _every_ answer, and here the common reply is one token. The user
asked for it unprompted in the same flow (2026-09-26): "it's actually faster to display a table of
10 products with proposed quantities, and let the user say which ones they don't want … The indices
should be the basis for that, so there's less typing." Run live the same day over eight pages, every
reply was an index expression of two to eleven characters and none needed clarifying. Conditions:

- the common case is one token (`ok`), and exceptions are indices (`-3,7`, `5x2`, `only 1,2,9`);
- **number rows continuously across pages** (11–20 after 1–10) — the previous table is still on
  screen, so a per-page `-5` is ambiguous between two tables;
- **echo the parse back in one line before anything irreversible** — the only thing between a
  mistyped index and a wrong item in a real cart;
- `AskUserQuestion` keeps the page-level next/done step, the first-live-mutation confirmation above,
  and any reply ambiguous enough that the alternative is guessing.

Not for a set of genuinely different either/or decisions: with no shared default, a table is a worse
surface than the batched ask. Worked example: `freshful-polite-mcp`'s `reorder-suggest` skill.

## Write spike/research findings into PLAN.md before or alongside implementing

When a research/spike phase (live CDP exploration, API probing, DOM inspection) turns up findings
that change or confirm the plan, write them into the repo's `PLAN.md` first — as their own section,
matching the doc's existing narrative style — before or alongside writing the actual implementation
code. Don't just carry findings in conversation and go straight to code.

**Why:** explicit instruction, `freshful-polite-mcp` (2026-08-14): "it's good to keep everything in
the plan, then implement." Matches the existing pattern across this repo family, where `PLAN.md` (a
single monolithic file — this family predates the `plans/YYYY-MM-DD-topic.md` convention documented
in the `plan-conveyor` skill, and hasn't been migrated onto it) is the durable record of _why_ the
architecture looks the way it does; code comments point back to it rather than re-explaining.

**How to apply:** after any live-spike/research pass in one of these repos, update `PLAN.md`'s
relevant section(s) — mark resolved open questions, add a dated findings section, restate/extend any
boundary decisions the findings touch — before moving on to implementation. Do this even when the
user hasn't explicitly asked for the write-up that round; treat it as the default sequencing.
