---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/freshful-polite-mcp
source_session: 2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl
source_moment: 2026-09-18T11:42:00Z
source_plan:
---

## Context

`session-harvest`'s sweep has a check for **files this session edited that no repository and no
store covers**. Its instruction to the reporting session is:

> the work is saying **what would recover it** ... "no copy anywhere" is a finding worth stating
> plainly.

That was the right instruction when it was written, because there was nothing to do about such a
file except describe it. It is now incomplete: `plan-docs` grew an `attach` command, which copies a
named file somewhere stable and writes an `## Attachments` row into the plan recording it. For the
common case — a probe or repro script sitting in the session scratchpad, belonging to a plan this
session just wrote — that turns "say what would recover it" into "here is the command that gives it
a recovery path."

`session-harvest`'s SKILL.md mentions `attach` nowhere; its two hits for the word are the ordinary
English verb. So a harvest following the current text correctly reports the file and stops, one
command short of fixing it.

## Evidence

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-freshful-polite-mcp/2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl`

The sweep output, 2026-09-18, distinctive phrase `no diff, no history — say what would recover it`:

```
== files written outside every repository ==
    /tmp/claude-1000/.../scratchpad/probe_afine.py   (no diff, no history — say what would recover it)
```

That file was the reproducer for a bug the same session had just filed as
`plans/2026-09-06-check-availability-404-vs-parse-error.md` — it probed two product pages and
printed the `__NEXT_DATA__` key shapes that proved the failing one renders `page: /404`. The plan
recorded the _findings_ (a comparison table); it did not record the script, and re-deriving it meant
rewriting ~40 lines plus rediscovering that `chrome_manager.ensure_running()` has to precede
constructing the fetcher — which is the sibling plan's entire subject.

The harvest resolved it with one command the skill never named:

```
plans.py attach plans/2026-09-06-check-availability-404-vs-parse-error.md <the probe> --commit
```

2 KB, committed beside the plan. The finding went from reported to closed.

[PITFALL: the gap is invisible because the current instruction is _satisfiable_. A harvest that
writes "this file has no copy anywhere; recovering it means rewriting the probe" has done exactly
what the skill asks and reads as thorough. Nothing in the output suggests a command was available.
That is the same shape as this skill's own warning about a step that "ran and produced nothing of
value" — except here the step produced something, just less than it could have.]

## Open questions

[DECISION: how far should the bullet go? The minimal edit is one clause naming `attach` as the
remedy when the file is evidence for a plan. A stronger version would have the sweep itself detect
the case — a scratchpad file written by a session that also wrote a plan file — and print the
`attach` line pre-filled, the way `skills-state` already prints the `new --for` command. The
stronger one is better ergonomics and more code in a script whose whole value is that it is read
once and trusted. **Settled 2026-09-26: minimal** — the bullet names the dispositions and the
sweep's per-row hint names all three; no pre-filled command until a harvest reports the finding and
still does not act.]

[DECISION: is "evidence for a plan" the only case worth naming? **Settled 2026-09-26: no, three
dispositions**, as the table below derives. Some unversioned files are not evidence — the confirmed
2026-09-01 instance in the skill's own text is an edited live config outside every working tree,
which `attach` would be wrong for (copying a live config into a plan directory is not a recovery
path, it is a stale duplicate of a file that keeps changing). The bullet needs to separate the two
rather than sending every hit to `attach`.]

**Answered by the same session, two days on: there is a third disposition, and it is the one
`attach` actively gets wrong.** Both probes from that session were attached to their plans. When
those plans were retired, `probe_afine.py` was deleted with its plan and `probe_order_list.py` was
**pulled back out** and committed as `spike_order_shape.py` at the repo root, beside the existing
`spike_cdp.py`. The difference is whether the file has a job after its plan closes:

| the file is                                 | disposition              | why                                         |
| ------------------------------------------- | ------------------------ | ------------------------------------------- |
| evidence for one finding, now in code/tests | `attach`, retire with it | reproduces a question already answered      |
| a diagnostic the next incident will want    | **promote to a script**  | the plan closes; the question recurs        |
| a live config outside every tree            | neither                  | a copy is a stale duplicate, not a recovery |

[PITFALL: an attachment is deleted with its plan, and that is easy to read as "safely kept" because
`attach` files it somewhere stable and `archive` can read it back. Stable is not the same as
present. `probe_order_list.py` would have left the working tree entirely at retirement — the tool
that answers "which field moved?" gone from a repo whose parsers break on exactly that, recoverable
only by someone who already knew to look for it. Nothing in `attach`'s own output says this; the
retirement step is where it surfaces, which is late.]

So the bullet wants three branches rather than two, and the middle one is the interesting addition:
**ask whether the file's question recurs.** If it does, the remedy is not `attach` at all but the
repo's own convention for a script.

[DECISION: does `attach`'s own `--local` vs `--commit` split need restating here, or is pointing at
`plan-docs` enough? A committed attachment goes through the repo's gate and is seen by `scan`; a
local one is the only copy of that file and is invisible to `scan`. A harvest reaching for `attach`
on a file it has not read is exactly the case where that distinction matters. **Settled 2026-09-26:
point at `plan-docs`**, and say to read it before attaching an unread file — the flags are
`plan-docs`' to explain, and restating them is a second copy to drift.]

## Recommended direction

Lean minimal: one clause in the existing bullet, naming `attach` for the evidence-for-a-plan case
and explicitly excluding the live-config case the bullet already describes. That keeps the two
skills' ownership clean — `plan-docs` owns what `attach` does and when each flag applies;
`session-harvest` only needs to know the command exists and which of its own findings it answers.

Revisit the pre-filled-command idea only if a later harvest reports the same finding and still does
not act on it.

Filed from a session in `freshful-polite-mcp`, which cannot edit this repo.

## Verification

Landed 2026-09-26 in `5f4cf54`. Wording only, so there is no new test; the next harvest that meets a
scratchpad probe is the check.

## Migrated to

- **The three dispositions and both dated instances** — `skills/session-harvest/SKILL.md` step 5,
  the files-outside-every-repository bullet, from "Recovering one is often a command".
- **The per-row hint** — the `suffix` of that section in
  `skills/session-harvest/scripts/harvest.py`.
- **Not migrated:** the pre-filled `attach` command, deliberately deferred per the first decision;
  the evidence transcript pointer, which expires with the transcript.
