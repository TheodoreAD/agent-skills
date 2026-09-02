---
status: landed
updated: 2026-09-02
source_repo: github.com-personal/power-user-linux-setup
source_session: 361b5d16-284b-4286-8233-45c011924707.jsonl
source_moment: 2026-09-02T17:05:00+03:00
---

# `plans.py list` hides status drift from the sessions best placed to fix it

## Context

`list` reports status drift — a `status:` value outside the vocabulary — **only at
`--scope family`**. A session running `list` inside the repo that owns the drifted plan sees nothing
wrong: repo scope renders whatever string it finds as a group heading, so a drifted status displays
as though it were a deliberate `blocked on …` and looks intentional.

**The asymmetry is the problem.** The session that can see the drift is in a different repo and may
not write to the one that owns it; the session that can fix it cannot see it. On this machine that
is not a corner case — writing into another repo is out, so a family-scope finding has to be filed
as a plan and wait for a session that, by construction, will never be shown the thing it is being
asked to fix.

**And unlike the other family-scope-only sections, this one needs no cross-repo comparison.** The
`depends_on` view genuinely requires the whole corpus — an edge points at another repo. Drift does
not: the vocabulary is a fixed enum, so a single repo has everything needed to check its own plans
against it. Computing it only at family scope looks like an accident of where the code sits rather
than a design constraint.

Filed from `power-user-linux-setup` rather than fixed, because `plan-docs` is authored here.

## Evidence

- Two real instances, both found only via `--scope family` from another repo, both in
  `power-user-linux-setup`, both fixed 2026-09-02:
  - `2026-08-23-git-hooks-for-quality-gate.md` carried a whole paragraph of prose where the enum
    belongs — `idea` followed by an em-dash and two clauses of parked-note.
  - `2026-08-27-docs-site-usability.md` carried `done`.
- Machine-wide count taken the same day: `list --scope family --all --limit 0` over **135 plans**
  returns `idea`, `in-progress`, `planned`, `landed`, `abandoned` and nine distinct `blocked on …`
  strings and nothing else, so those two were the whole population rather than a sample.
- Transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-power-user-linux-setup/361b5d16-284b-4286-8233-45c011924707.jsonl`.
  The originating capture is one session earlier, in `agent-skills` itself
  (`2312636b-3f89-4cb5-95e8-48f986fb9ecb.jsonl`, `2026-09-01T17:20:53.485Z`), on the user asking
  **"anything left to absorb or retire or fix in the plans?"**

[PITFALL: **a drift that reads as a synonym hides more than one that reads as prose, and hides
something specific.** The paragraph-shaped drift was obviously wrong to any reader. `done` is a
single plausible word — it renders as a tidy group heading and reads as a deliberate choice. It was
also the more consequential of the two, because `done` quietly asserts the plan is finished while
`landed`, the vocabulary's real terminal status, is **gated**: `set-status` refused `landed` on that
plan the moment it was asked, on an open `UNVERIFIED` that had never been checked. So the synonym
did not merely mislabel the state, it routed around the check that would have caught the plan was
not actually done.]

[DECISION: **the 2026-08-25 instance is not a third data point for
`2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md`.** Checked rather than assumed: the
string arrived in `ea41fac`, 2026-08-25 01:46, in a commit that also added a `[DECISION:` block to
the body — the exact mid-edit shape that plan describes, so it looked like one. It is not.
`set-status` first appears in `plans.py` on **2026-08-28** (`a6585a2`), three days later. There was
no command to bypass and no gate to skip; hand-editing the frontmatter was the only way to change a
status at the time. That plan still stands at two occurrences.]

## Answered by building it

[DECISION: **report at every scope; `set-status` stays a transition gate.** `_print_status_drift`
now runs for repo, unscoped and family alike, in the same position family scope already used — after
the rows, before the footer. Making `set-status` speak for the plan's _current_ status regardless of
the transition asked for was the louder alternative and was refused: drift is a state to notice, and
a command that answers a question nobody asked is the shape that gets ignored.]

[DECISION: **`absorb` does not carry it.** Its prompt is one question about one decision, and the
listing is already the command a session runs to see what is open. A second class of finding there
is how a prompt becomes a status report nobody reads.]

[DECISION: **drift is read off the unfiltered set, not the displayed rows** — found while writing
the test, not predicted. A drift beginning with a terminal status (`landed by hand`) groups as
terminal, so the default open-work filter drops it before the check would have seen it, and the
early return for a repo with no open plans skipped the check entirely. Both paths now pass
`all_entries`. That is the drift most worth catching, since it is the one asserting a plan is
finished.]

[DECISION: **the valid-looking hand-landed status is not chased here.** The cheap count was taken:
**no plan file in this repo was created before 2026-08-28**, so the population it asks about is
empty here. It is also invisible to any check comparing against the vocabulary, by construction — so
it belongs to `2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md`, which owns
hand-editing, and not to a drift check. Measuring it family-wide would need each repo's own git
history, one repo at a time.]

## Landed

`skills/plan-docs/scripts/plans.py` — drift at every scope, over `all_entries`, both call sites.
Three tests in `tests/unit/test_plan_store.py` (repo scope, the terminal-prefixed drift, the
no-open-plans early return), each confirmed failing against the pre-change script. The reasoning is
in `references/design-rationale.md` ("Why the listing reports status drift"); the PITFALL about a
synonym hiding more than prose is in `SKILL.md`.
