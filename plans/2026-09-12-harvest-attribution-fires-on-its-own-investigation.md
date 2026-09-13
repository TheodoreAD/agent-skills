---
status: idea
updated: 2026-09-12
source_repo: github.com-personal/power-user-linux-setup
source_session: 30c6413a-66ed-4f51-b8f5-eb3dddd550cc.jsonl
source_moment: 2026-09-12T12:05:00+03:00
source_plan:
---

# `filed` attributes a commit because the sweep told the session to investigate it

## Context

**Merge this into `2026-09-09-harvest-attributes-another-sessions-absorption.md`** if that plan is
still open — same subcommand, same symptom, and this is a second mechanism reaching it rather than a
second report of the first. Filed separately only because that plan has been absorbed out of the
store and a session in another repo cannot edit it.

`harvest.py filed` attributes a store commit to the session when _"this session wrote or named one
of its files"_. The `named` half has a feedback loop with the sweep that runs immediately before it.

## Evidence

Session `30c6413a-66ed-4f51-b8f5-eb3dddd550cc.jsonl`, 2026-09-12, harvesting in
`power-user-linux-setup`. The distinctive phrase to find the moment is "this session named a file in
a command".

`filed` reported **3 commits this session**, and one of them was not:

```
8d61ea026  2026-09-12T11:57:53+03:00  repo-tasks: absorbed the consumer sweep report,
                                      merged into the consumer-transitions plan
    ^ this session named a file in a command
```

That commit is another session's `absorb --apply` of a plan this session had filed hours earlier.
The session did name the file — twice, in `git -C <store> log --oneline -1 -- <path>` and
`git -C <store> cat-file -e HEAD:<path>` — and it ran both **because the procedure says to**: the
sweep's own instruction is to confirm a filed plan is still there before naming it in the report,
and step 8 adds that a parallel session may have absorbed it, "which is normal and means the work
arrived; say that instead".

**So following the skill correctly is what produced the false attribution.** The commands are the
ones the report step prescribes, they are read-only, and they name exactly the path whose commit is
about to be misattributed.

## Why this is not the plan it should be merged into

`2026-09-09-harvest-attributes-another-sessions-absorption.md` records the **write-path** half —
`absorb --apply` moves a plan out of the store, so the absorbing session writes nothing at that path
and its own removal commit reads as a stranger's. The fix for that was to read the session's
commands as well as its writes.

This is that fix's shadow. Reading commands makes an absorption attributable to whoever absorbed it
**and** to whoever merely looked at it — and the skill guarantees someone looks, every run, at
exactly these paths. The two halves cannot both be satisfied by matching on paths alone.

[PITFALL: **the false positive lands on the row a reader is least able to check.** An unattributed
row is explicitly hedged — "may be another session's live work: report, do not edit" — while an
attributed one carries no such warning, so the one that is wrong is the one presented as settled.
This session caught it only because it had watched that commit appear in real time, twenty minutes
earlier, and knew whose it was.]

## The same root cause reaches `sweep`, and there it is louder

`filed` is the cheap symptom. The expensive one is in the same run's sweep, from the same premise —
a repo named in a read-only command is enrolled as a repo the session touched.

This session read `repo-tasks` three times (`git -C … status`, `git -C … log`, `cat …/plans/…`) and
wrote nothing in that checkout. The sweep enrolled it anyway, which produced two rows:

- **Its unpushed commits, listed as this session's repo state.** Two commits timestamped _during the
  harvest_, both another session's live work. The row is correctly hedged ("check who authored
  these"), so this half costs a sentence in the report and no more.
- **The consumer warning, which is not hedged.** `consumer_candidates(projects_root(), repos)` takes
  the same enrolled set, so the sweep reported `repo-tasks` under **"repos on this machine that
  install a repo this session changed"**, naming five consumers and closing with _"a push here is a
  deploy there"_. This session changed nothing in `repo-tasks` and has nothing to push there.

[PITFALL: **that is the loudest line in the sweep, and the skill's own text says why it has to be.**
The check exists because a push to a shared tool deploys to every consumer's next CI run with no
notice — a genuine, documented, expensive failure. A warning that important firing on a repo the
session only _read_ is the shape that teaches a reader to skim the section, which costs the true
positive it was built for. The skill already makes this argument for a different check, after ten
false positives in the written-paths list: "a section that has been all-false-positive once is one
the next harvest skims, and the true positive would have been the eleventh line."]

Reading a repo is not incidental here either — it is prescribed. The cross-repo rules say reading
another repo "stays fine, and is how a filed plan gets written accurately enough to act on", and
this session read `repo-tasks` for exactly that reason.

## Open questions

[NEEDS CLARIFICATION: can the two be separated at all by static analysis of the transcript? A write
to the path and a `git log`/`cat-file` naming it are both "named in a command". Distinguishing them
means classifying the command — mutating versus read-only — which the audit script already does for
a different purpose (`git-C-mutating`, `git-mutating-in-chain`), so the vocabulary exists.]

[NEEDS CLARIFICATION: or is the honest answer a third bucket rather than a better binary? The
evidence genuinely supports "this session touched this path" and not "this session made this
commit". A row reading `touched the path, authorship unestablished` would be true of both halves and
would stop the attributed column asserting more than it knows.]

[NEEDS CLARIFICATION: does the same loop reach the `research` store attribution, which also matches
"named in this session's own commands"? Not observed — this session's research count was 0 of 5
attributed and it named no research entries — but the mechanism reads identical.]

## Recommended direction

Merge into the 2026-09-09 plan and decide both halves together, because a fix for either one alone
moves the error to the other. The third-bucket option is the one worth costing first: it needs no
command classification, it is honest about what the evidence supports, and the skill's own text
already prefers an explicit gap to a confident wrong answer elsewhere (`holder unknown` on a
process, `unavailable` on a listing that did not run).
