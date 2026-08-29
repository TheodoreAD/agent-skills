---
status: idea
updated: 2026-08-29
---

## Context

The store's sensitive tier — every project root not named in `shareable_roots` — is a local git
repository with no remote and no other copy. That is deliberate: one personal remote accumulating
several employers' internal architecture is the outcome the split exists to avoid, and the reasoning
is in `skills/plan-docs/references/design-rationale.md` under "Why the store is two git repositories
split by sensitivity".

It leaves the durability gap that motivated the split only half closed. The shareable tier got a
remote, which makes the convention's promise true there — retirement deletes a plan file _because_
`archive` reads it back out of git history, and that history now lives somewhere other than one
disk. For the sensitive tier the promise is still unbacked.

Accepted as absent when the split landed 2026-08-29, on the grounds that the tier was **empty**: an
empty tier loses nothing. That is the whole of the argument, and it expires the moment a plan is
written for a store-routed repo.

**The trigger is the first plan filed into `~/plans-sensitive`.** `plans.py doctor` reports the
tally per root, so "0 with plans" against every sensitive root is the check that this is still
deferred rather than overdue.

## Open questions

[NEEDS CLARIFICATION: which destination, and whether one answer covers every employer. A contract
that forbids third-party storage outright is not answered by encrypting — it is answered by never
leaving the machine. If the roots disagree, this becomes the per-root destination the binary split
deliberately postponed, and the tier lookup is already the hook it would use.]

[DEFERRED: a non-vendor destination — external drive, NAS, second machine. It closes the gap with no
disclosure question at all, which is why it is the first thing to try. Carried over from
`2026-08-29-store-sensitivity-tiers.md`, where it was marked "implement it in the same pass as the
split"; the split shipped without it because the tier is empty, so the note travels here rather than
being dropped.]

[DEFERRED: an encrypted remote — `git-remote-gcrypt`, or restic to any host. It changes the
concentration objection materially, since no vendor holds anything readable. Two reasons it is not
the default answer: it does not answer a contract forbidding third-party storage at all, and it adds
a key whose loss is worse than no backup, because it looks like one. Carried over from
`2026-08-29-store-sensitivity-tiers.md`.]

## Recommended direction

Try the non-vendor destination first and stop there if it is enough — a scheduled `git push` to a
bare repository on an external drive or a NAS is a one-line remote and needs no new tooling, no key
to lose, and no policy question answered. Reach for encryption only if the answer has to survive the
machine and its drive being in the same place.

Whatever lands, `plans.py doctor` has to keep flagging a remote on the sensitive tier: a non-vendor
destination is still a remote, so the check either learns which remotes are sanctioned or the rule
becomes "one you configured deliberately", recorded where doctor can read it.
