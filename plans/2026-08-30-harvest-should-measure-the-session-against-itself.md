---
status: idea
updated: 2026-08-30
---

# `session-harvest` should have the session measure itself, not just its output

## Context

Filed from a `power-user-linux-setup` session, 2026-08-30. `~/AGENTS.md` forbids writing to another
repo outright — "however much a skill's own instructions tell you to" — which is exactly this case:
`session-harvest`'s own step 6 says to edit its source in `agent-skills`, and the global rule says
to file instead. The global rule wins by its own wording, so this is the fold-back.

**The trigger is step 6's own first-listed signal**: _"the run's best finding came from something no
step asked for. Both mean the procedure is mis-aimed, and the second is the easier to overlook
because the finding still got made."_

That is what happened. The harvest's most valuable output was a count the session took over its own
transcript, and no step asked for it:

| metric                               | the session  | the one it had just measured | baseline (2026-08-21→24) |
| ------------------------------------ | ------------ | ---------------------------- | ------------------------ |
| Bash calls                           | 254          | 232                          | 3,956                    |
| piped through `head`/`tail`          | **86 (33%)** | 67 (28%)                     | 29–32%                   |
| ...of which carried a real exit code | 51           | 21                           | not measured             |
| chained (`&&` / `;`)                 | 103 (40%)    | not measured                 | 64–71%                   |
| `cd` into the session's own repo     | 0            | not measured                 | 114                      |

The session had, hours earlier, authored and committed the `[DECISION:]` about `head`/`tail` piping
discarding exit codes — naming `inv quality.precommit | tail -N` as the canonical instance — and
then produced that shape more than any other. It also used `rg -r` (which is `--replace`, and whose
danger `~/AGENTS.md` states verbatim) and `git stash` on a machine where a plan it had absorbed that
same session says stash is unsafe.

None of that reached the report because a step asked. It reached it because the session happened to
wonder.

## Why this belongs in step 5 specifically

Step 5 is the live-state sweep — "the transcript says what was _intended_; these say what is
actually true now". A session's own rule-adherence is precisely that: not in the conversation's
narrative, not in git, not in CI, and invisible to the session's own impression of how it went. The
session in question would have reported "went well, gate green throughout", which was true and
missed the point.

It is also cheap in exactly the way the other step 5 bullets are. Step 4 already opens
`~/.claude/projects/<slugged-cwd>/<session-id>.jsonl` to extract user turns; counting `tool_use`
blocks where `name == "Bash"` is the same file and about fifteen more lines.

**And it is the only measurement that arrives while the session can still act on it.**
`session-bash-audit` measures across sessions after the fact, which is the right tool for a trend
and the wrong one for "you are doing this right now".

## Open questions

[NEEDS CLARIFICATION: does this belong in `session-harvest` at all, or in `session-bash-audit` with
`session-harvest` merely calling it? The audit skill owns the patterns, the regexes and the research
into why each happens, and duplicating its counters in a second skill is how the two drift. Against:
`session-harvest` is what actually runs at the end of a session, and a check nothing invokes is not
a check. Probable answer: the counter lives in `session-bash-audit` with a single-session mode, and
`session-harvest` step 5 gains one bullet that calls it — which is also
`plans/2026-08-23-global-agents-md-adherence-watch.md`'s deferred item in the other repo, so the two
should land together.]

[NEEDS CLARIFICATION: what does the harvest do with a bad number? Reporting it is the minimum. The
stronger version is that a session measuring itself over some threshold should say so in its own
report rather than only filing it — which turns the harvest into a feedback loop rather than an
archive. Risk: a self-flagellating report that buries the findings the user actually needs. The
adherence numbers belong in the "skill and instruction misuse" section that already exists, not in
the verdict.]

[NEEDS CLARIFICATION: which patterns are worth counting? `head`/`tail` piping, chaining, and
own-repo `cd` are what `~/AGENTS.md` names and what the baseline covers. The exit-code-bearing split
(a piped `inv`/`pytest`/`gh run watch`) is the one that turns a style number into a correctness
number, and it is what neither prior measurement computed. A naive regex over-counts it — a heredoc
whose script merely contains the word `inv` matched in the run above — so the split needs the pipe
and the command to be in the same shell segment.]

## Recommended direction

Add one bullet to `session-harvest`'s step 5, phrased as the other bullets are — the command first,
the failure it prevents second — and put the counter itself in `session-bash-audit` so there is one
implementation. State the two numbers the session already has (its own rate, and whatever baseline
that skill carries) rather than a pass/fail, because the useful signal is the comparison.

Worth adding at the same time: the observation that produced this. **An agent authoring a rule is
not thereby more likely to follow it** — the session that wrote the finding scored worse than the
session it was writing about. That belongs in `session-bash-audit`'s research notes, since it bears
directly on how much any wording change should be expected to buy.

[PITFALL: `session-harvest`'s step 6 tells the harvest to edit its own source in `agent-skills`, and
`~/AGENTS.md`'s cross-repo rule forbids exactly that. The conflict is real and the global rule
resolves it by its own terms, but the skill reads as though the fold-back is always an edit. Worth a
clause in step 6's self-update mechanics naming `plans.py new --for` as the route when the session
is not in `agent-skills` — otherwise every harvest run from another repo hits this and has to
re-derive the resolution, and some will resolve it the other way.]
