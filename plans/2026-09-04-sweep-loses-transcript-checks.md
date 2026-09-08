---
status: landed
updated: 2026-09-08
---

# `session-harvest`'s command block makes `sweep` skip its transcript-derived checks

## Context

Filed from `repo-tasks` on 2026-09-04 by a `/session-harvest` run that followed the skill's command
block as written. Nothing in this repo was touched.

The block in `SKILL.md` reads:

```shell
python3 $H transcript --expect '<a command this session ran>'
python3 $H sweep --boundary <instant>
```

`transcript` takes the selector; `sweep` does not get one. So `sweep` resolves no transcript and
prints:

```
# transcript: no transcript resolved. Pass --session <id|path>, or --expect '...' to select by
content. Never guess an id: a wrong one names a real file.
```

**Two of the sweep's checks are transcript-derived and are therefore skipped in silence** — "files
written outside every repository" and "paths named in edits that do not exist". Both are named in
step 5 as findings no other check reaches; the first has its own confirmed-2026-09-01 instance about
an unversioned config edited outside every working tree.

[PITFALL: the degradation is honest but reads as inapplicable rather than as skipped. The line says
what to pass, at the **top** of a report whose remaining sections all print normally — processes,
sockets, disk, repos, CI, stores. A reader scanning a full-looking report does not go back to the
header to work out which two sections are missing, and the sections are missing rather than empty,
so there is no "0 findings" line where they would have been. Confirmed on this run: the harvest read
the whole sweep, moved on, and only found the gap when re-reading the skill for step 6.]

`sweep` already accepts `--session`, `--job` and `--expect` — `sweep --help` lists all three. So
this is a documentation defect, not a missing capability: re-running with
`sweep --boundary <instant> --session <id>` produced the missing section immediately.

**The trigger is narrower than "following the block", and that matters for the fix.** Confirmed
2026-09-04 by a second harvest, in `agent-skills`, which ran `sweep --boundary <instant>` with no
selector — exactly the block as written — and resolved a transcript anyway: it ran inside a
background job, so `sweep` found the session through the job's `state.json` (`linkScanPath`) and
reported `resolved by: … (job <id>, linkScanPath)`. Both transcript-derived sections were live.

So the defect fires only where no job-side resolution exists, which is an ordinary interactive
session — the common case, and the one where nothing in the output distinguishes "no findings" from
"never looked". It also means a fix cannot be validated from a background job: a run that resolves
by `state.json` passes whether or not the block carries a selector.

## What landed, and it was neither of the two obvious fixes

The recommendation was to carry the selector through the block. It was overtaken: on 2026-09-05
`sweep` learned to resolve from `$CLAUDE_CODE_SESSION_ID`, so the block as written stopped losing
anything in an ordinary Claude Code session and threading an id by hand would have been ceremony.
The rejected middle option — content-based fallback — stayed rejected for the reason given here,
that `transcript`'s discipline is a deliberate selector and a guess is what "never guess an id"
exists to prevent.

**What was left is this plan's third option, and it is the one that mattered.** Landed 2026-09-08:
both transcript-derived sections always print a heading, with `none` or
`skipped: no transcript — both checks read this session's own writes` in place of nothing at all.
That fixes the reading failure rather than the invocation, which is what the PITFALL above describes
and what no amount of correct invocation would have addressed — a resolved run finding nothing was
just as silent as a run that never looked.

Merged with `2026-09-03-harvest-sweep-degrades-silently-without-a-transcript.md`'s evidence at
implementation time: the two are one defect from opposite ends, that plan holding the measurement of
what a degraded run loses and this one the measurement of when it fires. Neither was filed as a
duplicate of the other, and reading them together is what showed the fix belonged in the printer.

[DECISION: there is no "degrades quietly by design" line to disambiguate. The question assumed a
sentence in the skill body; the wording is a docstring on `_sweep_transcript`, and it is already
narrow — it says an explicit `--session`/`--job`/`--expect` that fails to resolve is an error rather
than a degraded run, precisely so a report never describes somebody else's scope. It was never the
blanket licence this plan feared, so nothing had to be rewritten.]
