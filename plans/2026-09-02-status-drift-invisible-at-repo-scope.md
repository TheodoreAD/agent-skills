---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: **whether repo scope should report drift, or whether `set-status` should
refuse to leave one in place.** Reporting is the smaller change and fits `list`'s existing footer
habit — it already prints a terminal-plan count and an absorb hint. The alternative is louder: a
plan whose current status is not in the vocabulary is a plan every `set-status` call could surface
regardless of the transition being asked for. Reporting is probably right, since drift is a state to
notice rather than an error to block on.]

[NEEDS CLARIFICATION: **whether `absorb` should carry it too.** It already speaks for the aged
retirement backlog at the top of a session, which is the same shape of problem — a thing the repo's
own sessions would otherwise never be prompted about. Against: `absorb`'s prompt is deliberately one
question about one decision, and adding a second class of finding is how that becomes a status
report nobody reads.]

[NEEDS CLARIFICATION: **whether a valid-looking hand-landed status is worth chasing at all.** A plan
that was hand-edited to a status the vocabulary contains, before the gate existed, is invisible to
any check that compares against the vocabulary — the count above cannot see it by construction.
Whether that matters depends on how many plans predate 2026-08-28 and have moved status since. Cheap
to count, not counted.]

## Recommended direction

Compute drift at repo scope as well as family scope, and print it in `list`'s footer where the
terminal-plan count already goes. The check needs nothing the repo does not already have, and the
current split means every drift found is found by a session that is not allowed to fix it.

Leave the family-scope section as it is — it is still the only view that catches drift in a repo
nobody is currently working in.
