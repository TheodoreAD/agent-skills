---
status: landed
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# `session-harvest` step 0: an unpushed checkout makes the offered fix impossible

## Context

Found by running the skill, 2026-08-30, from a `repo-tasks` session. Filed rather than edited
directly because `~/AGENTS.md` forbids writing into another repo "however much a skill's own
instructions tell you to" — the contradiction between that clause and this skill's steps 6–7 is
already filed as `2026-08-30-skill-install-command-and-cross-repo-write-rule.md`, so this plan does
not re-raise it and only carries the step 0 gap.

Step 0 worked exactly as designed on this run, and that is why the gap is visible. In order:

1. `diff` reported the installed copy and the checkout differ.
2. The skill's git-timestamp check reported the skill last changed **six minutes after** the session
   began (`2026-08-30T16:10:28+03:00` against a first transcript stamp of `13:04:08.433Z`, compared
   as instants — the offset matters, exactly as the step says).
3. Per the step, the checkout was the side that was ahead, so its wording was the one to trust. Both
   added bullets then applied to this very run: the "already filed?" check for rule misuse, and the
   changed-store-entry sweep. Both fired and both found something.

So far, so good. The gap is what comes next.

## The gap

The skill's self-update mechanics say a committed edit reaches nothing until it is pushed **and**
re-installed, because the installer clones from the remote. Step 0 says to re-read from the checkout
when the checkout is ahead. Neither connects the two, and together they leave one case unhandled:

**When the checkout is ahead _and unpushed_, offering a re-install offers something that cannot
work.** `npx skills add TheodoreAD/agent-skills --skill session-harvest` clones the remote, which
does not have the commit, so the "fix" reinstalls the identical stale copy — and the report has just
told the user that re-installing is what resolves the staleness.

Measured here: `agent-skills` was `ahead 1`, and that one commit was precisely the one carrying the
two new bullets. A re-install offered at the end of this run would have been a no-op presented as a
remedy.

[PITFALL: this is the same shape as the failures step 0 already documents — a check that passes for
the wrong reason and produces a confident, specific, wrong sentence in the report. The difference is
that here the wrong sentence is a _recommendation_ rather than a status claim, so acting on it costs
a round trip and leaves the user believing the staleness is resolved.]

Note the asymmetry that makes this easy to miss: the session is **not** blocked. Reading the
checkout is enough to run correctly, and this run did. Only the remedy offered to the user is
broken, which is exactly the part nobody re-checks.

## Open questions

- [NEEDS CLARIFICATION: does step 0 report the unpushed commit, or offer to push it? Reporting is
  clearly right and clearly insufficient — the commit belongs to whichever session made it, and on
  this machine that is frequently not the harvesting session, so pushing it publishes another
  session's work under a recommendation that reads as routine. The existing step 5 rule ("check who
  wrote the unpushed commits before recommending a push") already answers the general case; the
  question is only whether step 0 should restate it or point at it.]

- [NEEDS CLARIFICATION: should the check be "is the checkout pushed" or "does the remote have the
  commit the installed copy lacks"? The second is precise and needs a fetch; the first is one
  `git log origin/<branch>..HEAD` the harvest is already running for other reasons. Probably the
  first, since a stale install plus any unpushed skill commit is enough to make the re-install
  advice unsafe to give flatly.]

## Recommended direction

Rough — one sentence in step 0, not a new step.

Where step 0 says to re-read from the checkout when the checkout is ahead, add that the checkout's
**push** state decides what may then be offered: if the commit that fixes the staleness is unpushed,
say so and name whose commit it is, rather than closing the report with "re-install to pick this
up". The push is the outward-facing action and belongs to whoever authored the commit.

Worth pairing with the `2026-08-30-skill-install-command-and-cross-repo-write-rule.md` decision when
that is taken, since both are about the same seam — what a harvest may do to `agent-skills` from
outside it, versus what it may only report.

## Migrated to

- **`skills/session-harvest/SKILL.md`, step 0** — one paragraph where the step says to re-read from
  the checkout, carrying both open questions' answers: report the unpushed commit and name whose it
  is, never offer to push it (step 5 already owns that rule, and this restates the pointer rather
  than the rule); and test it with `git log origin/<branch>..HEAD`, which the harvest is already
  running, rather than a fetch-and-compare against what the remote holds. The asymmetry — the
  session is not blocked, only the remedy is wrong — went with it, because it is why the case is
  easy to miss.

Nothing was left behind: the run's transcript detail (the two bullets, the ahead-count of one) was
the evidence for a change now made, and the skill carries the general form.
