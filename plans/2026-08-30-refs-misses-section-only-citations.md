---
status: idea
updated: 2026-08-30
---

# `plans.py refs` misses citations that name a section but not a file

## Context

Found 2026-08-30 while retiring two landed plans in `repo-tasks` — a real run of the "Retiring a
plan" procedure, following it step by step.

Step 3 says to find inbound references with `refs <file>.md`, and describes it as searching the
whole repo plus the store on the bare filename, "since short-form references are the easy miss". It
did that correctly: 8 hits for one plan, 1 for the other, across seven files.

It also missed two, and the procedure has nothing that would have caught them:

- a `contributing/` page citing "whose §9 decision assumed a family-uniform dependency set", with no
  filename anywhere in the sentence;
- an open plan citing "the same shape as the deferred §11 `deps.audit`", likewise.

Both were written by earlier sessions that had the plan open and referred to its sections the way a
reader in context would. Both dangled the moment the file was deleted, and both were found only
because the retiring session happened to run a separate `grep -rn '§'` over the repo on a hunch.

The failure is quiet in a way the existing tooling cannot close. `docs.link-check` — the gate step
in `repo-tasks` that exists to stop exactly this — checks markdown links, and a bare `§11` is not a
link. So a retirement that trusts `refs` alone leaves live pointers behind, passes the gate, and
reads as complete.

The tag counts make the shape clear: the larger of the two plans carried 16 `[DECISION:` and 3
`[PITFALL:` tags across 15 numbered sections, and sections are what other plans cite. A plan
organised into numbered sections is a plan whose citations will be section-shaped.

## Open questions

[NEEDS CLARIFICATION: is this `refs`' job, or a second command? `refs` answers "who links to this
file", which is well defined and is what the deletion gate needs. "Who mentions a section of it"
cannot be answered from the filename alone — the term is `§` plus a number, which matches every
other plan's own sections too. A `--sections` flag that greps for `§N` near the plan's own heading
numbers is one shape; a blunt "also list every `§` in this repo, for you to eyeball" is another and
is what actually worked here.]

[NEEDS CLARIFICATION: how many false positives does the blunt version produce? Measured once, on one
repo: `grep -rn '§' plans/ contributing/ README.md CONTRIBUTING.md src/` returned 17 lines, of which
2 were the real finding, 2 were the retiring plan's own self-references, and the rest cited plans in
other repos or sections of live plans. Seventeen lines is small enough to read. Whether that holds
on a corpus five times the size is unknown, and it is the number that decides whether this is worth
a flag or just a sentence in the procedure.]

[NEEDS CLARIFICATION: does the fix belong in the tool or in the writing convention? The other
direction is to say in `SKILL.md` that a cross-plan citation names the file every time, never a bare
section number — which makes `refs` sufficient by construction. That is cheaper to implement and
impossible to enforce, and it does nothing about the citations already written.]

## Recommended direction

Rough. Add the section sweep to the retirement procedure first, as a documented second grep beside
`refs` — it is one line in `SKILL.md`, it costs nothing, and it is what actually found the two
misses. Decide afterwards, with a second data point, whether it earns a place in `plans.py` itself.

**The first half landed 2026-08-30**: `plan-docs`' retirement step 3 now carries the sweep, with the
17-lines-of-which-2-were-real measurement as its cost estimate. What stays open is only the second
question — whether it belongs in `plans.py` — and that waits on a second retirement run measuring
the same thing on a different corpus, which is the data point the first `[NEEDS CLARIFICATION:]`
above asks for. Nothing else in this plan is outstanding.

Worth noting what already works and should not change: `refs` searching on the bare filename rather
than the full `plans/` path is exactly right, and it is what caught 7 of the 9 real hits — every one
of which cited the file from a sibling plan as a markdown link whose text and target were both the
bare filename.

Also worth recording from the same run, because it is the reason the misses mattered rather than
being merely untidy: none of the nine references was a blind path swap. Each cited a numbered
section, so the fix was to name the destination heading in the new rationale doc, or — where the
citation was only provenance — to drop the pointer and keep the fact. The procedure's step 5 already
says this ("don't blindly swap the old path for the new one at every hit"), and a real run confirms
it is the common case rather than the exception: 9 of 9.
