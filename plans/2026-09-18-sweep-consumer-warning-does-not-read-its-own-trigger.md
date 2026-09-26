---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/repo-tasks
source_session: 14237e4b-3a66-4207-8a3a-882552c86680.jsonl
source_moment: 2026-09-18T18:35:49+03:00
source_plan:
---

# The sweep finds the doc that says when a push obliges a consumer, and then does not read it

## Context

`session-harvest`'s sweep has a check for **repos on this machine that install a repo this session
changed**. On a `repo-tasks` harvest, 2026-09-18, it printed:

```
== repos on this machine that install a repo this session changed ==
    /home/tdumitrescu/projects/github.com-personal/repo-tasks
      installed by: agent-skills, ingesta, invoke-stubs, power-user-linux-setup, scaffoldapy
      it documents what a consumer owes: contributing/consumer-sweep.md
  a push here is a deploy there — report it and file it
```

Five consumers, and an instruction to report an obligation. **That session's five pushed commits
were a CI workflow, two `contributing/` pages, four plan updates and one test.** Not one of them
touched the shipped configs or the dependency manifest, so not one consumer owed anything.

## The gap

**The trigger is written down, in the very file the check already locates.**
`repo-tasks/contributing/consumer-sweep.md` has a "When to sweep" section:

> After changing any of: the `repo-tasks-quality` manifest in `pyproject.toml`, anything under
> `src/repo_tasks/configs/`, or a `quality.*` / `test.*` step that shells out to a binary.

The check finds that file and names it. It does not read it, and it does not compare this session's
changed paths against it — so a docs-and-plans push and a manifest change produce the identical
line.

[PITFALL: **this is the shape the skill already warns about twice and did not apply here.** The
written-paths check learned it ("a section that has been all-false-positive once is one the next
harvest skims, and the true positive would have been the eleventh line"), and the stale-plan check
learned it as a measured 43%-noise rate. A consumer warning that fires on every push to a
widely-installed repo is the same failure: the reader stops reading it, and the run where a
`configs/` file really did move is the one it is for.]

**The fix is small and needs no new source of truth**, which is what makes it worth doing rather
than documenting around: the check already has this session's changed paths (every other row uses
them) and it already has the path of the doc. Reading that doc's trigger is a glob match. Where a
consumer-facing doc exists but states no machine-readable trigger, the current unconditional line is
the right fallback — say so, rather than silently reporting nothing.

## A second, unrelated wording finding, same run

`plan-docs`' `attach --commit` prints `attached: <file> -> <path>  (committed, 1 KB)` and then, four
lines down, `commit: plans.py commit <plan> -m '...'`. The parenthesis names the **tier** — beside
the plan, in git, as opposed to `--local` — but it reads as a past-tense report of an action, and
the flag is spelled as a verb. `git status` immediately afterwards showed the plan modified and the
attachment directory untracked; nothing had been committed.

Cost is one wasted call and a moment's doubt about whether the store had been left dirty, which on a
shared store is the thing a session is most anxious not to do. `(commit tier, 1 KB)` or
`(in git, 1 KB)` removes it. Filed here rather than separately because both findings are one
harvest's, and both are wording rather than behaviour — split them if the absorbing session prefers.

## Recommended direction

1. Compare the session's changed paths against the consumer doc's stated trigger; fall back to the
   present unconditional line when no trigger can be read, and say which of the two happened.
2. Rename the `--commit` tier in `attach`'s output so it describes a placement rather than an act.

Sibling: `2026-09-18-harvest-consumer-check-matches-a-scratch-repo-basename.md` is the same section
matching a consumer that does not exist at all. Kept apart at absorption, 2026-09-26, because the
causes and fixes differ; both want the closing `a push here is a deploy there` line made
conditional.

[PITFALL: `consumer-sweep.md`'s trigger is the only specimen the implementation generalises from —
the only consumer-facing doc of its kind on this machine, which is the position the
membership-derivation attempts in `repo-tasks/plans/2026-08-25-consumer-transitions.md` were in each
time they were wrong. Checked 2026-09-26 and still true. The implementation answers it by keeping
the fallback loud: a doc with no readable "When to sweep" paths prints "no trigger could be read"
and keeps the unconditional warning, so a second shape shows up rather than going silently
unmatched. A second specimen is when to revisit the parser.]

## Migrated to

Landed 2026-09-26: step 1 in `4301bec`, step 2 in `0d8aed2`.

- **Reading the trigger and the conditional line** — `_consumer_trigger`, `_trigger_matches` and
  `_print_consumers` in `skills/session-harvest/scripts/harvest.py`; step 5's consumer bullet in
  `skills/session-harvest/SKILL.md`;
  `test_a_consumer_doc_trigger_decides_whether_a_push_obliges_anyone`.
- **The `attach` wording** — `_print_attached` in `skills/plan-docs/scripts/plans.py`, now
  `(to commit with the plan, …)`; `test_attach_output_names_a_placement_not_an_action`.
- **Not migrated:** nothing deliberately left behind; the pitfall above lives on in the
  `_consumer_trigger` docstring.
