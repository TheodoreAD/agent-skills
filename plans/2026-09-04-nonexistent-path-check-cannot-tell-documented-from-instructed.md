---
status: landed
updated: 2026-09-08
source_repo: github.com-personal/power-user-linux-setup
source_session: 92f54986-8a19-49a4-b792-8ebb1d5fcf1a.jsonl
source_moment: 2026-09-04T11:57:51+03:00
---

## Context

`session-harvest`'s sweep ends with **"paths this session wrote into files that do not exist"**. Its
stated purpose is sharp and valuable — from the SKILL.md bullet, a rule written into an
always-loaded instructions file or a `SKILL.md` command block "names a path on this machine —
usually an installed copy, not the checkout the session was editing", and the 2026-08-29 instance
was a `~/AGENTS.md` rule pointing at a `scripts/` directory the installed skill did not have, so
every future session was told to run a file that did not exist.

The check finds those by asking whether the path exists. That question cannot distinguish **a path
the session told someone to run** from **a path the session documented as belonging to someone
else** — and the second is not a defect, it is correct content.

## Evidence

Harvest of `power-user-linux-setup` session `92f54986-8a19-49a4-b792-8ebb1d5fcf1a`, 2026-09-04. The
sweep's final section listed ten paths, **all ten false positives**:

```
/home/tdumitrescu/.codex/AGENTS.md      ~/.codex        ~/.codex/       ~/.codex/AGENTS.md
~/.config/AGENTS.md                     ~/.config/amp/AGENTS.md
~/.config/opencode/AGENTS.md            ~/.config/zed/AGENTS.md
~/.gemini/                              ~/.gemini/GEMINI.md
```

That session's whole subject was **where each coding agent reads its instructions from**. Every path
above is one of two things, and neither is actionable:

- a vendor path for an agent **not installed here** (`~/.codex/`, `~/.gemini/`) — which the repo's
  own design treats as the correct state, since the installer skips a link whose parent is absent
  precisely so an absent agent does not look present. The sweep flags exactly the paths the code is
  deliberately not creating.
- a path **belonging to another vendor entirely** (`~/.config/amp/AGENTS.md`,
  `~/.config/opencode/AGENTS.md`, `~/.config/zed/AGENTS.md`) recorded in a docs table saying where
  Amp, opencode and Zed look. Those will never exist on a machine that does not run those agents,
  and the documentation is right anyway.

Ten hits, no signal — and the session that produces them is disproportionately likely to be one
doing agent-tooling work, which is the same population the check's true positive comes from.

[PITFALL: **the failure mode is not noise, it is a check that trains its reader to skim.** A section
that has been all-false-positive once is one a later harvest reads faster, and the true positive it
was built for — a machine-wide rule aimed at a file that does not exist — looks identical in the
list to a docs table entry. The 2026-08-29 instance would have been the eleventh line here.]

## What landed, 2026-09-08

[DECISION: **(c), the containing file — `AGENTS.md`, `CLAUDE.md`, `SKILL.md` and nothing else.**
Recommendations 1 and 2 both, in one change. The filter was the cheapest candidate and it is also
the one the check's own docstring had described from the start: "a rule written into an
always-loaded instructions file, or a `SKILL.md` command block". The code was broader than its own
stated purpose, and the gap between them was the whole defect — which is why this is a narrowing to
the documented behaviour rather than a new rule.

(a) and (b) were not needed and would have cost more. Where the path sits inside a file is a
markdown-parsing question, and command position is the same claim about a shell that has already
failed once in this corpus — a `docker` cross-check counted the word inside a quoted `rg` pattern.]

[DECISION: **spellings collapse by expanded path.** Three of the ten hits were one directory written
three ways, which is noise under every filter, so the row is keyed by the expanded path while the
literal spelling is kept for display and for the still-written re-check, which greps the file for
the text that was actually written.]

[DECISION: **a write naming no destination is kept, not dropped.** The filter exists to drop paths
written into something demonstrably descriptive; an unknown target demonstrates nothing, and
dropping it would be the same silent-degradation defect the sibling plans in this group are about.
The section also prints its own limit now — which files it reads — so an empty result says what it
looked at.]

[DECISION: **"does not exist" stays the test, and the check stays in step 5.** The third question
asked whether the real finding was "the installed copy lacks what the rule assumes", which step 0
owns. It is not: step 0 compares an install against a checkout, and the 2026-08-29 instance was a
path that existed in **neither** — the rule named a `scripts/` directory the skill had not grown
yet. A staleness check cannot see a path that was never anywhere, and this one can.]

## What is deliberately not done

The narrowing is a filter on **where the path was written**, not on what it means, so a genuine
instruction written into a `README.md` or a fenced block in a docs page is now out of scope. That is
the trade taken: the check's stated purpose has always been the always-loaded file, and ten false
positives in one run cost more than a hypothetical miss in a file no agent loads.
