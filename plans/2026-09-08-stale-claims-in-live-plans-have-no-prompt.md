---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-08T00:00:00Z
---

# `plan-docs` prompts about plans that are finished, never about plans that went stale

## Context

`plan-docs` has a trigger for a plan whose lifecycle has ended: `absorb` raises terminal plans
awaiting retirement, and stalled mid-retirement ones, at the top of a session. That was added
2026-09-02 on the finding that the convention "was never missing the mechanism, it was missing a
trigger".

**The same gap exists one stage earlier and nothing covers it.** A live plan's claims about the code
go stale silently. A session closes a gap, and nothing sends it back to the `[DEFERRED:]`,
`[UNVERIFIED:]` or measurement block that described that gap — so the plan goes on advertising work
that is done, or naming a mechanism that no longer exists.

The failure is worse than a merely outdated file, for two reasons the evidence below shows
repeatedly:

- **A stale `[DEFERRED:]` usually mis-prices the work as well as mis-stating it.** It is written
  when the work looks expensive; when it turns out cheap, the entry is not revisited. So the backlog
  advertises the wrong cost, and the cheap items are the ones that sit longest.
- **A stale entry looks exactly like a live one.** There is no signal to distinguish "nobody has
  done this" from "somebody did this and did not come back", so the next reader spends the triage
  cost before discovering there is nothing to do.

## Evidence

Session `e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-08. The
distinctive phrase to search that transcript for is "what can we work on next that can be done
without complex decision making" — the request that started it, which is what makes the sample
unbiased: it was a search for easy work, not an audit for staleness.

**One repo, 22 open plans, one session.** Nine of them carried something wrong. Five were stale
claims:

| plan                                   | claimed                                     | actually                                  |
| -------------------------------------- | ------------------------------------------- | ----------------------------------------- |
| `2026-08-28-node20-action-deprecation` | README missing one namespace                | four missing, plus six drifted task lists |
| `2026-08-29-link-check-indented-…`     | anchors uncovered, would need a real parser | shipped four days earlier, no dependency  |
| `2026-08-30-deferred-gate-tools`       | three named `S60x` findings                 | still three, **none the same finding**    |
| `2026-08-22-pypi-publish-integration`  | `publish.yml` fires on a tag push           | `workflow_dispatch:` only for four days   |
| `2026-08-25-consumer-transitions`      | a complete sweep checklist                  | one of four real items                    |

Four more had evidence that was wrong rather than merely old, and these are the ones that argue the
prompt has to be about _re-measuring_, not just re-reading:

- A plan's headline example had been **fixed 26 minutes before that plan's own `source_moment`**, by
  the very session that filed it.
- The same plan drew "two repos, two versions" from a **two-repo sample of a three-repo family**,
  and the omitted repo was the one still carrying the drift.
- A plan gated on "wait for a second instance" had one available the whole time; finding it took
  writing the twelve-line check the plan itself proposed.
- That same measurement **falsified the objection** that had kept the plan parked.

[PITFALL: **a stable measurement is not evidence that it is current, and a changed one is not
evidence that a sibling changed.** Two re-measurements in this session: a
`ruff --select S602,S603,S607` count was 3 before and after while every individual finding had
turned over, and a `deptry` count was 4 before and after and genuinely unchanged. Both plans
recorded a number; only re-running told them apart. So the prompt cannot be "does the number still
match" — it has to send someone to re-run the command, which means **a plan recording a measurement
should record the command that produced it**, and several did not.]

## What landed the same day, independently — read this before the questions below

Absorbed 2026-09-08, hours after filing, into a repo where a neighbouring plan had just been retired
on the same subject from the other end. Recorded here so the questions below are answered against
what now exists rather than against what did when this was written.

**The narrow half of this has a trigger now.** `2026-09-05-landed-code-leaves-plans-open.md` —
retired 2026-09-08, readable through `plans.py archive --show` — covered the sub-case where a
session lands what a plan designed and never bumps it. `session-harvest`'s sweep now lists this
repo's open plans that name a source file the session wrote, three times or more, and were last
touched before the session began, and asks whether the session landed what any of them designed.
That is the third open question's rule ("the session that closes a gap must revisit the plan") built
as a prompt for the closing session rather than left as a rule nobody can tell they are breaking —
which is the objection that question raises against itself.

**This plan's warning against a `plans.py` symbol check was measured, and it holds.** Across 8 repos
and 167 open plans: **43% name a source file that moved after the plan's `updated:`**, and requiring
the name to look like the plan's subject only brings it to 14%. So the false positive rate really is
the noise floor that gets a check switched off, exactly as this plan predicted from a different
direction. What is left is structural — a session that edits a file makes every plan about that file
look stale — which is why the surviving mechanism is a prompt printing its own measured rate, not a
detector.

**What that leaves this plan owning, and it is the larger half:** stale `[DEFERRED:]` entries and
stale _measurements_, neither of which the new prompt reaches. The prompt keys on source basenames a
session wrote; a `[DEFERRED:]` that has become cheap, or a number whose command nobody re-ran, moves
no file and names no symbol. The writing rule this plan recommends — the command beside the number,
the cost of checking beside the deferral — is untouched by anything that landed and is still the
cheapest thing here.

[PITFALL: **the two plans reached the same conclusion from opposite ends within one day and neither
knew of the other**, which is the corpus's own filing race rather than a coincidence: both sessions
were in `repo-tasks`, both filed `--for` this repo, and the second was written while the first was
already being implemented here. The measurement above is the shared answer; without this section a
reader would find only one of the two halves.]

## Open questions

[NEEDS CLARIFICATION: what is the trigger? `absorb`'s retirement prompt keys on `status` plus age,
both of which are in the frontmatter and free to read. Staleness has no such field. The candidates
are all more expensive: a plan's `updated:` being older than the last commit touching the paths it
cites; an explicit `verified:` date per measurement block; or nothing automatic at all, with the
answer being a rule in the skill rather than a prompt in the script. The last is cheapest and is
what this corpus's other hard-won rules look like.]

[NEEDS CLARIFICATION: does this want to be a tag? There is deliberately no sixth tag — "five is the
whole vocabulary" — and this would be the obvious sixth, something like
`[MEASURED: <date>, <command>]`. Against: the same argument that keeps the vocabulary closed, and
`[UNVERIFIED:]` already carries half of it. For: the evidence above says the rot is specifically in
_dated measurements_ and in `[DEFERRED:]` entries, which is narrower than "plans go stale" and might
be addressable without a new tag at all — by requiring the command beside the number, which is a
writing rule.]

[NEEDS CLARIFICATION: is the honest scope "the session that closes a gap must revisit the plan that
described it"? That is a rule about the _closing_ session rather than a prompt for a later one, and
it is where the cost is lowest — that session has the context. But it is also exactly the rule that
was already being broken in every case above, silently, by sessions that had no reason to know a
plan mentioned their change. A rule nobody can tell they are breaking is the shape this corpus
usually rejects.]

## Recommended direction

Rough, and the first question above decides most of it.

The cheapest change that would have caught the largest share of this evidence is a **writing rule,
not a mechanism**: a plan that records a measurement records the command beside it, and a
`[DEFERRED:]` entry states what it would cost to check whether it is still deferred. Both are free
at writing time and turn a re-read into a re-run. Neither needs a new tag, a new field, or anything
in `plans.py`.

Do not reach for a `plans.py` check that greps plans for code symbols and reports the ones that no
longer resolve. It is the obvious mechanism and it is the wrong one for this corpus: plans
legitimately name retired functions, other repos' symbols and historical states, so the false
positive rate would be the noise floor that gets a check switched off — the same reason `refs`'s
section-citation grep stayed a documented grep rather than a flag.

**Do not generalise from this one repo without a second.** The sample is 22 plans in the repo with
by far the most plan churn in the family, measured on a day when several of its own changes had just
landed. That is where the rot should be worst, and one repo is one repo.
