---
status: idea
updated: 2026-09-26
source_repo: github.com-personal/freshful-polite-mcp
source_session: 0134b98b-f28c-4444-8923-f0c22c667296.jsonl
source_moment: 2026-09-26T00:00:00Z
source_plan: plans/2026-09-26-table-first-reorder-and-bulk-stock.md
---

# polite-mcp-conventions' "don't ask for a typed list" needs the index-table case written into it

## Context

`polite-mcp-conventions`' second rule says:

> **Batch interactive per-item decisions, don't ask for a typed list.** … **Why:** explicit feedback
> during a Freshful reorder-flow session — "suggest some quantities for all those things, and ask me
> one by one, it needs to be interactive, if i have to type all that stuff out it kills the ux."

On 2026-09-26 the same user asked for the opposite surface in that same flow, unprompted and from
experience: "it's actually faster to display a table of 10 products with proposed quantities, and
let the user say which ones they don't want, or which ones they want with different quantities, than
keep asking for each four. The indices should be the basis for that, so there's less typing."

`freshful-polite-mcp` implemented it — `.agents/skills/reorder-suggest/SKILL.md` now draws a table
of 10 with quantities pre-filled and takes exceptions by index (`ok`, `-3,7`, `5x2`, `only 1,2,9`,
`none`). So a skill in another repo currently reads as a deliberate exception to a rule in this one,
with the reasoning recorded there rather than here.

## Evidence

The rule and the new flow do not actually disagree, which is why this is an amendment and not a
reversal:

- **The rule's objection is the cost of typing _every_ answer.** An index-based exception list is
  the opposite shape: `ok` accepts ten items, `-3,7 5x2` handles a page in twelve characters. Both
  the rule and the new flow refuse to make the user type out a full structured reply.
- **The rule already names this exit.** Its own "How to apply" reserves a free-text ask for cases
  "where there are too many items for batching to stay lightweight — at that point, consider whether
  the flow itself needs restructuring." A 20-candidate page under the old flow was five sequential
  `AskUserQuestion` round trips; that is the case the sentence anticipated, met in practice.
- **`AskUserQuestion` did not go away**, which is the part a careless reading would lose. It still
  carries the page-level next/show-all/done step, the first-live-mutation confirmation this same
  skill requires, the out-of-stock alternatives offer, and any reply ambiguous enough that the
  alternative is guessing at a quantity.

The measurement that drove it, for the record: the per-item flow also checked availability for every
candidate it was about to ask about, at one live product-page render each — about 28 renders for a
page where 8 items were wanted. The table draws from the local catalog instead and the live check
runs over the accepted set only. Full reasoning is in that repo's `contributing/design-notes.md`,
"Stock for a reorder page comes from the catalog, not from a live check per candidate".

## Recommended direction

1. Keep the rule's headline and its "why" verbatim — the 2026-08-14 feedback is still true and is
   still the reason the default is a guided ask rather than a form.
2. Add the index-table case as the third bullet of "How to apply", roughly: when a page runs past
   what two `AskUserQuestion` calls can cover, a pre-filled table the user edits by index is the
   lighter shape, provided the common case is one token (`ok`), the parse is echoed back before
   anything irreversible, and `AskUserQuestion` keeps the page-level and confirmation steps. Two
   details learned only by running it (see the live run below) go in the same bullet:
   - **Number rows continuously across pages** (11–20 after 1–10), never 1–10 per page. The previous
     table is still on screen, so a per-page `-5` is ambiguous between two tables.
   - **Echo the parse back in one line before any irreversible call.** It caught nothing in the live
     run because nothing was ambiguous, and it stays: it is the only thing between a mistyped index
     and a wrong item in a real cart, at one line per page.
3. Cite `freshful-polite-mcp`'s `reorder-suggest` as the worked example, since it is the flow both
   the original feedback and the amendment came from.

[NEEDS CLARIFICATION: whether this generalises past a reorder page or should stay scoped to "many
homogeneous items with a sane default per item". Quantities over a product list are unusually
well-suited to defaults; a set of genuinely different either/or decisions is not, and a table would
be a worse surface there. Scoping it narrowly is the safer first version.]

## The flow has run live (2026-09-26)

Merged 2026-09-27 from `2026-09-27-the-index-table-flow-is-now-verified-live.md`, filed from
`freshful-polite-mcp` (session `0134b98b-f28c-4444-8923-f0c22c667296`, 2026-09-26T23:55:28Z) and
absorbed out of the store the same day. It replaces this plan's former `UNVERIFIED` tag on the table
flow never having run against the real account.

- A full reorder ran against the real account: eight pages of ten candidates, 80 shown, 43 more
  dumped as one plain list on request, and 26 items in a real cart.
- **Every reply was an index expression, and none needed clarifying**: `-5,6,7,8,9`,
  `only 22,23,26`, `only 41`, `only 52,53,54,55`, `only 62,63,66`, `only 77,78`, and
  `only 117,98,114,116` against the plain list. Each is two to eleven characters, against five
  sequential `AskUserQuestion` round trips per twenty candidates under the old flow. The user also
  picked out of order (`only 35,31`), which the grammar has to tolerate and did.
- `AskUserQuestion` kept exactly the roles predicted above: the page step, the first-live-mutation
  confirmation, and the out-of-stock alternatives offer. The last fired once, on a genuinely
  unavailable regular, and was answered in one word. It is the clearest argument for this shape: the
  five substitutes the site returned were irrelevant (for rye crispbread it offered peanuts, seeds,
  crisps and popcorn), and a flow that auto-substituted the closest price would have put crisps in
  the cart.
- Nothing from the run argues for widening past "many homogeneous items with a sane default each",
  so the open question above stands as it is.
