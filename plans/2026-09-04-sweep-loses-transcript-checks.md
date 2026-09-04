---
status: idea
updated: 2026-09-04
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

## Recommended direction

Carry the selector through the block, so following it verbatim cannot lose the checks:

```shell
python3 $H transcript --expect '<a command this session ran>'   # prints the session id
python3 $H sweep --boundary <instant> --session <that id>
```

Two smaller options worth weighing against it:

- Have `sweep` fall back to the same content-selection `transcript` uses, so no id has to be
  threaded. Against: `transcript`'s whole discipline is that a selector is supplied deliberately,
  and a fallback that guesses is what the "never guess an id" warning exists to prevent.
- Have `sweep` print the two skipped sections as explicit `skipped — no transcript` headings rather
  than omitting them. This is the smallest change and fixes the reading failure rather than the
  invocation, so it composes with either of the above.

[NEEDS CLARIFICATION: is the "degrades quietly by design" line in the skill's script section
describing _this_, or something narrower? It currently reads as covering the whole subcommand, which
makes a reader treat the missing sections as intended. If the design intent is only that a missing
`gh`, a non-Linux socket check, or an unreachable remote should not abort the sweep, then the
transcript case is a different thing wearing the same label, and the sentence should say so.]
