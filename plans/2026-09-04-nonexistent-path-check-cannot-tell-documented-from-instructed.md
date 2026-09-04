---
status: idea
updated: 2026-09-04
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

## Open questions

[NEEDS CLARIFICATION: **what actually separates the two?** Candidates, roughly by cost. (a) Where
the path was written: a fenced shell block or a rule in an instructions file is instructed, a
markdown table cell or prose is descriptive. (b) Whether the path appears as the argument of a
command — `python3 <path>`, `source <path>` — versus standalone. (c) Whether the containing file is
one an agent loads unconditionally (`~/AGENTS.md`, a `SKILL.md`) versus a docs page nobody executes.
(c) is the cheapest and probably catches the real case: the 2026-08-29 instance was in
`~/AGENTS.md`, and every false positive above was in `docs/` or a `plans/` file.]

[NEEDS CLARIFICATION: should a bare directory (`~/.codex`, `~/.codex/`) be reported at all? Three of
the ten are the same directory in three spellings, which suggests the extraction is matching path-
shaped strings rather than references. Deduplicating by resolved path would cut the noise without
answering the question above.]

[NEEDS CLARIFICATION: is "does not exist" even the right test for the true positive? The 2026-08-29
case was a path that did not exist **on this machine** while existing in the checkout — so the
finding was really "the installed copy lacks what the rule assumes", which is a staleness question
step 0 already owns. If so the check may belong there rather than in the sweep.]

## Recommended direction

1. Try (c) first — restrict the check to paths written into files an agent loads unconditionally.
   One filter, and it would have left this session's ten hits out while keeping the instance the
   check exists for.
2. Deduplicate by resolved path regardless of which filter lands; three spellings of one directory
   is noise under every option.
3. If the section still comes back empty on a few real sessions, consider whether the third question
   above means it belongs in step 0 instead of step 5.
