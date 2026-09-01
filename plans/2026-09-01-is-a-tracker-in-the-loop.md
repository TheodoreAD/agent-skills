---
status: idea
updated: 2026-09-01
---

# Is a tracker in the loop at all?

## Context

Split out 2026-09-01 from `2026-08-28-cross-repo-plan-store.md`, now **retired** — that plan's
recommendation (keep per-repo ownership, add a discovery layer) shipped as the store plus
`plans.py list --scope family`, and its survey and decisions moved into the skill's own
`references/`. This question is the one part of it the user explicitly held open: "the user wants
more time on it", recorded 2026-08-29.

The user raised continuously mirroring a tracker (GitHub Issues named) down to markdown.
`gh-issue-sync` and git-bug's bridges both prove the mechanism works, and both make the remote
authoritative and the markdown a mirror — which inverts what `plan-docs` is, and fails offline.

Three shapes were named: a tracker is **(a)** not involved, **(b)** an inbox only, or **(c)** the
store. `power-user-linux-setup`'s own `plans/2026-08-23-github-issues-plan-lifecycle.md` already
leans toward (b), which is compatible with everything the convention has settled since.

## What has narrowed it since

**(c) is effectively dead.** The store's "local git, no remote by default" decision exists so that
no single personal remote accumulates several employers' internal architecture, and an issue _is_ a
remote. A tracker could only ever hold the personal family's plans — one of eight project roots on
this machine — so it cannot be the store without either splitting the corpus or breaking the rule
the tier split exists to enforce. The `device` setting since made this sharper: on a work device the
one store is treated as sensitive outright.

**The strongest argument for a tracker is spent.** "One place that answers what is pending across
everything" was the motivation, and `list --scope family` answers it — 121 plans across 8 locations
on this machine, in one command, with no remote involved.

So what is left for (b) is genuinely only the inbox case: something arrives as an issue (a bug
report, a request from someone who is not you) and has to become a plan. That is a much smaller
question than the one this started as, and possibly one `plans.py new` already answers by hand.

## Open questions

[NEEDS CLARIFICATION: is the inbox case real on this machine, or hypothetical? Nothing in the corpus
arrived from a tracker so far. If it stays hypothetical the honest answer is (a), recorded as a
decision so the question stops being reopened — the convention already has a place for "considered
and rejected".]

[NEEDS CLARIFICATION: if (b), what does the boundary look like? An issue that becomes a plan is a
one-way import, not a sync — the moment it is two-way, the remote is authoritative for something and
the offline case breaks. `gh-issue-sync`'s three-way conflict detection is the prior art for doing
it properly, and its existence is also the argument that doing it properly is more machinery than an
inbox needs.]

[UNVERIFIED: reconsidering any surveyed tool means reading it at source depth first. Everything in
`skills/plan-docs/references/prior-art-task-trackers.md` except `tasks.md`, `beads` and `Backlog.md`
was assessed at README depth, and the Planning Repo Pattern article was never readable at all
(medium.com returns 403 to WebFetch on both URL forms; freedium.cfd does not resolve). Per the
`research-library` skill, a README can advertise a feature that was never implemented.]

## Recommended direction

Leave it open until an issue-shaped thing actually arrives, then decide from that case rather than
from the general question — which is what "more time on it" has already produced once, by letting
two of the three options die on their own. If nothing arrives, close it as (a): a decision that a
tracker is not involved is worth recording, and is cheaper than a fourth session re-deriving the
same narrowing.
