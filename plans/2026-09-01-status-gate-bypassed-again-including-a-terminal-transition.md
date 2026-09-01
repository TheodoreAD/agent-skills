---
status: idea
updated: 2026-09-01
source_repo: github.com-personal/ingesta
source_session: 81ef32cd-7240-48b8-b0a3-4cd53845adad.jsonl
source_moment: 2026-09-01T09:01:27.595Z
---

# The status gate was bypassed again, and this time into a terminal status

## Context

`plans/2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md` in this repo owns the finding
and is the plan this belongs in — filed rather than appended because it was measured from a session
working in `ingesta`. **Merge it there rather than keeping this as a second file.**

Second independent occurrence, different repo, 2026-09-01. Two plans advanced by editing the
frontmatter with the file-editing tool; `set-status` was never called, so its gate never ran:

| plan                                         | transition made by hand |
| -------------------------------------------- | ----------------------- |
| `2026-08-29-local-run-and-manual-testing.md` | `idea` -> `in-progress` |
| `2026-09-01-local-catalogue-drift.md`        | `idea` -> **`landed`**  |

The mechanism matched the owning plan's account exactly: the session was already mid-edit in the
body, converting `NEEDS CLARIFICATION` tags into `DECISION`s, and the frontmatter was four lines
above the cursor. It never weighed the rule, so it never reached the code path that could refuse.

## What is new, and why it is worth a row rather than a nod

**The second transition was terminal.** The owning plan measured `idea -> in-progress` and
`updated:` stamps — non-terminal, where a skipped gate costs a status that might be premature.
`idea -> landed` is the transition that _precedes deletion_: it is the one `set-status` guards with
the `UNVERIFIED`-blocks-`landed` rule and with the refusal to retire a plan still sitting in a
repo-routed repo's store mirror. The session then retired that plan — migration section, reference
fix, `git rm` — in the following three commits.

The outcome was correct by luck twice over, which is the same shape the owning plan's `[PITFALL:]`
already records: the tags had been resolved first, and the plan carried no `UNVERIFIED`, so the gate
would have passed had it run. Nothing in the artifact distinguishes that from a gate that was
consulted.

This bears on the owning plan's first open question — which of the three failure shapes this is. Two
occurrences now, in different repos, with the same proximate cause and no evidence of the rule being
weighed at all. That is "not followed", which the harvest skill's own routing calls a measurement
question rather than a rewording one. The second open question there — whether wording alone can fix
a failure whose moment of temptation is not the moment of reading — is the one worth deciding first.

## Evidence

- Transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/81ef32cd-7240-48b8-b0a3-4cd53845adad.jsonl`,
  session start `2026-09-01T09:01:27.595Z`.
- The commits are in `github.com-personal/ingesta`: `88dda8a` (the `in-progress` bump) and `a4c70dc`
  / `bb76f58` / `898bc07` (the `landed` bump and the retirement that followed it).
- The session had invoked `plan-docs` in its first turn and had the skill in context throughout.

## Recommended direction

Merge into the owning plan as a second measured occurrence, and let the terminal case sharpen the
fix rather than the count: a rule aimed only at "promotion" reads as being about `idea -> planned`,
and neither of the four hand-edits across the two sessions was that transition.
