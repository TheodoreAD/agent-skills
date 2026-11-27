---
status: idea
updated: 2026-11-27
---

# Private content flow detection

## Context

plan-conveyor classifies a machine by activity (`public`, `private`, `contractor`, `corporate`) and
each root by ownership (`own`, `shared`). The flow rules that follow are in
`skills/plan-conveyor/references/design-rationale.md`, under "Why a machine is classified by
activity and ownership". Under those rules a `private` repo's **names** may appear in your other
plans, but its **contents** may not leave that repo.

`scan` enforces the half about names: it derives the forbidden terms for each destination from the
machine's own directory names and each client's `[private_terms]`. Nothing enforces the half about
contents. A paragraph copied from a private repo's plan into a public repo contains none of those
names, so the scan passes it.

What guards private content today:

- plan-conveyor's cross-repo write rules: `new` refuses a plan in another repo, and `--for` files
  into the store instead;
- the transcript readers' compartment filter (session-harvest, session-bash-audit, skill-fitness),
  which quotes only transcripts whose content may reach the destination;
- the home AGENTS.md rule for working under a client's root.

Carried from the retired `plans/2026-11-25-plan-conveyor-ownership-and-activity-classification.md`
on 2026-11-27, where the user chose to keep it as an idea.

## Open questions

[UNVERIFIED: whether fingerprinting a private plan's distinctive lines catches a quote without
drowning in false positives. Until that is measured, private-content flow is guarded by the
cross-repo write rules and by an agent rule, not by the scan.]

[DEFERRED: per-repo visibility inside an `own` root. One account holds public and private repos side
by side, so the root implies `private`, the cautious one, for all of them. The original design
defaulted each repo's visibility from its remote and had the user confirm it. That was never built.
The cost is that a public repo of yours is treated as private: the transcript readers never quote it
into another repo, even though its content is public anyway. It is safe, but it withholds more than
it needs to.]

[NEEDS CLARIFICATION: what a fingerprint would be. Candidates are a hash of each line above some
length, shingled n-grams, or the plan's tagged lines only. Each trades recall against the number of
ordinary sentences that two plans share by chance.]

## Recommended direction

Measure before building. Take the plans in this machine's private repos and the plans and docs in
its public ones, fingerprint the private side, and count matches on the public side. A match rate
near zero on content known not to be copied is the bar a gate has to clear, since a scan that cries
wolf gets switched off. If it clears, wire the fingerprints into `scan` as one more source of
forbidden content per destination, beside the derived terms. If it doesn't, record the measurement
and keep the guard procedural.

Per-repo visibility is independent of this and cheaper. The remote API answers it, so it is one
suggested question per own repo, asked when that repo is first quoted from rather than at setup.
