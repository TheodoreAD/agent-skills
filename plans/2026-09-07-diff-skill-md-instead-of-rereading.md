---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/invoke-stubs
source_session: 6450239e-aad5-4861-acda-7eb9e97c15c6.jsonl
source_moment: 2026-09-07T08:07:00Z
---

# Step 0 says re-read `SKILL.md`; diffing it against the checkout answers the same question far cheaper

## Context

`session-harvest` step 0 already prescribes a diff for `scripts/` — "Read the diff before deciding a
note is enough" — and for `SKILL.md` prescribes a re-read: "re-read it from whichever side is
ahead". The asymmetry looks deliberate but costs a lot, and this run suggests it need not.

## Evidence

Harvest of 2026-09-07 from `invoke-stubs`. `skills-state` reported:

> install is stale (SKILL.md and scripts/) against a clean, pushed checkout … SKILL.md moved after
> this session began (6 commit(s))

None of the six were this session's own — it was working in a different repo — so the re-read branch
applied as written. Instead of re-reading, the run did:

```shell
diff -u ~/.agents/skills/session-harvest/SKILL.md <checkout>/skills/session-harvest/SKILL.md
```

Four hunks, all in step 5, ~40 lines: the sweep now reports parentage and
`started after this
session's last activity` itself; docker images are cross-checked against whether
the session ran `docker` at all; and the `pipefail` branch gained a confirmation. Every one of those
changed what the run then did — the docker rule in particular, since this session ran no `docker`
and the sweep listed six images, which under the old wording invited a removal line.

The re-read would have returned the same four facts inside ~700 lines.

## Open questions

[NEEDS CLARIFICATION: is the asymmetry deliberate? A re-read is unconditionally correct and a diff
is correct only when the copy held in context is one side of it. That holds when the skill was
loaded from the installed copy in the current turn, which is the ordinary case — but not if the
installer ran mid-session _after_ the skill was loaded, when the held text is neither side. That
case is detectable: `skills-state` already prints the install's mtime, and it can be compared
against the moment the skill was invoked.]

[DEFERRED: if the diff is admitted, the same argument applies to `references/`, which step 0
currently calls "read on demand and inert". It is inert only until a run actually needs one.]

## Recommended direction

Offer the diff as the default for `SKILL.md` where the held copy is one side of it, keeping the full
re-read for the mid-session-reinstall case, and say which. One sentence in step 0 beside the
existing `scripts/` diff instruction, not a new paragraph — the two are the same technique and
reading them apart is what made this run reach for the expensive one first.
