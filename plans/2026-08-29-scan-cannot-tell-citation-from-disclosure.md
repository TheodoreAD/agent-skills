---
status: idea
updated: 2026-08-29
---

# `scan` cannot tell a citation of a public project from a disclosure of who you work for

## Context

Found 2026-08-29 while running the shareable store's first push gate, which is the first time the
scanner was pointed at a corpus written by several sessions rather than one.

A plan in this repo cited an AI-security vendor's open-source skill scanner as prior art — the
ordinary, correct thing for a prior-art section to do, and the vendor's tool is public on GitHub.
`scan` flagged it three times, because that vendor is also one of this machine's work roots and the
derivation therefore holds its name as private.

Both facts are true at once, and the scanner sees only one of them:

- naming that org **is** a disclosure, if the sentence is about who the author works for;
- naming that org is **not** a disclosure, if the sentence is about a repository anyone can clone.

The derivation cannot distinguish them, and it should not try to guess — a scanner that decided
"this looks like prior art, allow it" would be a gate that silently permits the one sentence that
mattered.

[PITFALL: **the documented escape hatch does not fit this case.** `SKILL.md` sends a false positive
to `[private] ignore`, but that list is specified for names "too generic to gate on — a work repo
called `tools` would otherwise flag every mention of the word", and explicitly for a name "whose
leaking would tell a reader nothing". A well-known company name is neither generic nor harmless to
leak, so putting it there would be using the mechanism against its own stated rule, and would
silence every genuine hit on that org at the same time.]

Worked around for now by rewording the citation to describe the tool without the vendor — searchable
by its CLI invocation and its documented phrase, which finds it in one query. That is the
convention's own "describe the shape" advice, and it costs a little findability every time.

## Open questions

[NEEDS CLARIFICATION: is the workaround actually the answer? "Describe the tool, not the vendor" is
cheap, needs no new mechanism, and is already what the confidentiality section tells you to do for
work content. The cost is that prior-art sections get progressively less useful in exactly the repos
where a vendor happens to collide, and the reader cannot tell an omission-for-privacy from an
omission-for-sloppiness. A one-line convention — say why the name is missing, as the reworded plan
now does — may be the whole fix.]

[NEEDS CLARIFICATION: would a scoped allow-list be better than an ignore-list? Something like a
`[private] allow_in` mapping a term to the paths where it is a legitimate citation, so the org stays
gated everywhere except a named prior-art file. It is precise, and it is also a second list to
maintain and a new way to punch a hole in the gate — price that against how often this collides.
Once, so far.]

[NEEDS CLARIFICATION: how often does this actually happen? One occurrence is not a pattern, and the
answer may be "reword it each time". Worth counting before building anything: the trigger is a work
root whose org publishes open-source software an agent would plausibly cite, which is common for
large employers and rare for clients.]

## Recommended direction

Do nothing mechanical yet. Record the shape, keep rewording, and revisit if a second collision turns
up — the failure is loud (the gate blocks, nothing leaks) and the workaround is a sentence, which
together is the profile of something that should not earn a new config key.

If it does earn one, prefer the scoped allow-list over widening `ignore`: `ignore` removes a term
from the whole corpus, which is precisely the over-broad move `SKILL.md` already warns about for
`public_roots`.
