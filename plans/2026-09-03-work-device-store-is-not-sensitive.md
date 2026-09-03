---
status: idea
updated: 2026-09-03
---

# On a work device the store is not "sensitive", it is just the store

## Context

Stated by the user 2026-09-03: on an employer device everything in `~/plans/` is not sensitive,
because **the corporate context is the entire context**. The company's GitHub sits inside the
corporate security boundary, shielded from the public, and the central store should be committed to
a private repo there — exactly as personal work is committed to a private repo on a personal
machine.

That is a correction to the model, not a request for a flag. **"Sensitive" is a _relative_
classification**: it means "must not go where the other tier goes". On a contractor device the
relation is real — client A's work must not reach client B's remote or a personal one, and the split
is the whole design. On a work device there is nothing to be sensitive relative to. One
organisation, one context, one store.

## What the code does today

- `device = "work"` gives **one store, tiered `sensitive`** (`plans.py`, `_store_field`: the tier is
  `SHAREABLE if device == CONTRACTOR else SENSITIVE`).
- `remote_problems` then applies the sensitive tier's posture to it and **warns on any remote at
  all**: _"one personal remote holding an employer's internal work is the outcome this check exists
  to avoid; a sanctioned destination is fine, a personal one is not."_

It does not refuse, which is better than it first looked. But it warns on the case the user
describes as normal and correct, and it cannot tell a corporate host from a personal one — so on a
work device the warning fires forever, on the right behaviour.

[PITFALL: **a check that fires on correct behaviour is worse than no check**, because it is trained
away rather than read. This one has the shape exactly: the only sensible destination on a work
device is the corporate host, so the first thing a user learns is that this warning is noise — and
the day a genuinely personal remote appears, the message is indistinguishable from the one they have
been ignoring for months. The risk it guards is real and does not go away on a work device; the
check as written cannot see it.]

## What is wrong, in order of how much it matters

1. **The warning fires on the expected shape.** Pushing a work store to a private corporate repo is
   the intended workflow, not a smell.
2. **The check asks the wrong question** — _whether_ there is a remote, when the real question is
   _which_ remote. That distinction is configurable: a work device knows its own sanctioned host.
3. **The tier name leaks.** Calling the single store `sensitive` states an absolute property where
   the vocabulary means a relative one, and it surfaces to the user: `doctor` prints the tier, and
   the store-mode warning added 2026-09-03 prints `this store is sensitive`. On a work device that
   reads as a claim about the material rather than about a split that does not exist there.

## Open questions

[NEEDS CLARIFICATION: **whether a work device's store keeps a tier at all.** Options: keep
`sensitive` and change only what depends on it; rename the single-store tier to something
device-appropriate; or make `tier` meaningless on a work device and have every reader ask
`split_by_sensitivity` first. The last is the most honest and the most invasive — the tier is
threaded through routing, `where`, `new --for`, `archive` and the store-mode message.]

[NEEDS CLARIFICATION: **how a sanctioned remote is declared.** A `sanctioned_remotes` config key
holding hosts or URL prefixes is the obvious shape, and it turns a permanent warning into a real
check: warn only on a remote outside the list. It needs a decision about what a bare list means when
empty — silence, or the current warn-on-everything.]

[NEEDS CLARIFICATION: **whether the contractor device's shareable tier has the same problem in
miniature.** It is allowed a remote and is "usually private", so the same reasoning about corporate
versus personal hosts may apply one level down. Not examined.]

## Recommended direction

Keep the risk, fix the question. A personal remote holding an employer's work is worth catching, and
that does not stop being true because there is one organisation on the machine — but the check
should compare the remote against what the device says is sanctioned, and stay silent when it
matches. On a work device, a private corporate remote is the documented, expected destination and
the skill should say so rather than warn about it.

The tier rename is the larger and less urgent half; the warning is what a user meets on day one.
