---
status: idea
updated: 2026-09-10
source_repo: github.com-personal/power-user-linux-setup
source_session: b494b3ef-0114-4463-b5c6-c73187080e11.jsonl
source_moment: 2026-09-09T21:05:00Z
---

# The outside-every-repository check reports the session's own scratchpad, which is ephemeral by design

## Context

`sweep`'s **files written outside every repository** step exists for a real and sharp failure: a
file the session edited that no store covers, so nothing would recover it. The bullet's own instance
is an unversioned config outside every working tree — no diff, no history, no backup.

Every row it produced on 2026-09-09 in `power-user-linux-setup` was instead the session's own
harness scratchpad:

```
/tmp/claude-1000/<project-slug>/<session-id>/scratchpad/upgrade-probe/src/pyproject.toml
/tmp/claude-1000/<project-slug>/<session-id>/scratchpad/upgrade-probe/probe.sh
… 9 rows, all under that one directory
```

**9 of 9 rows, and all 9 are correct as ephemera.** Claude Code names that directory in the
session's own environment block as session-specific, isolated from the project, and the place
temporary files are supposed to go. A harvest asking "what would recover it" about a deliberate
scratch file has asked a question with no useful answer — the answer is "nothing, and that is the
point".

## Why this is worth a filter rather than a reader's judgement

The skill already made exactly this fix one check over, for the same reason. Its **paths written
into files that do not exist** step was narrowed to `AGENTS.md`, `CLAUDE.md` and `SKILL.md` after a
run produced ten rows and **all ten were false positives**, with the recorded reason:

> The cost was never the noise: a section that has been all-false-positive once is one the next
> harvest skims, and the true positive above would have been the eleventh line.

That argument transfers without modification. A scratch probe is the single most likely thing a
session writes outside a repo — this session wrote a whole throwaway package there to probe
`uv tool install --editable` — so the section fills with guaranteed-benign rows precisely in the
sessions that do the most verification work, which are the sessions most likely to have also touched
something real.

## What the filter is

The scratchpad path is not guessed: the harness states it in the session's environment, and it is
structurally identifiable — `<tmp>/claude-<uid>/<project-slug>/<session-id>/scratchpad/`. The
session id in that path is the transcript id `harvest.py` has already resolved, so the check can
match on **this session's own** scratchpad rather than on a general `/tmp` pattern.

Keep the rows rather than dropping them silently, as a count under their own line —
`9 file(s) in this session's scratchpad (ephemeral by design, not reported individually)` — for the
same reason `sweep` prints `none`/`skipped` instead of vanishing: an absent section reads as "not
checked" and a zero reads as "checked".

[NEEDS CLARIFICATION: should another session's scratchpad be treated the same way? A path under
`claude-<uid>/` with a **different** session id is still ephemeral by the harness's own definition,
but it is also not this session's to reason about, and the sweep already has the parallel-session
caveat elsewhere. Leaning: collapse it to a count too, under a separate label, since the recovery
question is equally meaningless there.]

[NEEDS CLARIFICATION: is `/tmp` in general safe to collapse? No — a session that writes to `/tmp`
directly, outside the scratchpad, has written somewhere with no recovery path _and_ no guarantee of
being cleaned up on the session's terms, which is the original finding. Only the harness-declared
scratchpad has the "ephemeral by design" property that makes the row uninformative.]

## Recommended direction

Match this session's own scratchpad prefix in `sweep`'s outside-every-repository step, collapse
those rows to a labelled count, and leave every other path reported individually as now. Small and
additive, in the script rather than in the skill's prose — the skill's own rule that a correction a
script can simply not make belongs in the script.
