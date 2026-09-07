---
status: landed
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

[DECISION: **the asymmetry was not deliberate — diff by default, re-read for the reinstall case.
Settled with the user 2026-09-07 and landed the same day.** A re-read is unconditionally correct and
a diff is correct only when the copy held in context is one side of it, which holds whenever the
skill was loaded from the installed copy in this turn — the ordinary case. It fails for an installer
that ran mid-session _after_ the load, when the held text is neither side, and that case is
detectable rather than assumed: `skills-state` prints the install's mtime, and the available-skills
listing changing mid-session is the second tell step 0 already names. Diffing unconditionally was
refused for exactly that case, since it is silently wrong there rather than merely expensive.]

[DECISION: **`references/` gets the same treatment, in one clause rather than a fourth rule** —
2026-09-07, closing this plan's deferral rather than carrying it. It stays out of the **verdict**: a
references-only commit must not fire the expensive branch, which is the 2026-08-30 finding that
split the three subdirectories in the first place. But a page this run actually opened was read from
the stale copy like anything else, so that one file is diffed. The verdict's boundary and the
reader's exposure are different questions and the wording now keeps them visibly apart.]

## Recommended direction

Offer the diff as the default for `SKILL.md` where the held copy is one side of it, keeping the full
re-read for the mid-session-reinstall case, and say which. One sentence in step 0 beside the
existing `scripts/` diff instruction, not a new paragraph — the two are the same technique and
reading them apart is what made this run reach for the expensive one first.

## Migrated to

- **The rule a reader follows** — `SKILL.md` step 0: diff `SKILL.md` rather than re-reading it, with
  the mid-session-reinstall case named as the one that still needs the full re-read, and the
  `references/` clause that closed this plan's deferral.
- **The reasoning** — `references/rationale.md`, "What step 0 owes a reader once it has found a
  difference (2026-09-07)": the forty-against-seven-hundred measurement, the pitfall that a diff is
  only sound when the held copy is one side of it, and why diffing unconditionally was rejected.
- **The deferral** — closed rather than carried. `references/` is diffed when a run actually opened
  a page, and stays out of the verdict.

Not migrated: the four hunks themselves, which were this repo's own sweep changes and are described
in the commits that made them.
