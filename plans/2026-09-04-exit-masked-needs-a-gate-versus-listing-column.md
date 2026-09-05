---
status: idea
updated: 2026-09-06
source_repo: github.com-personal/power-user-linux-setup
source_session: 92f54986-8a19-49a4-b792-8ebb1d5fcf1a.jsonl
source_moment: 2026-09-04T00:07:14+03:00
---

## Context

`session-bash-audit`'s `audit.py` reports `exit-masked` as one rate over all Bash calls. Seven
samples in, that number has stopped being able to distinguish outcomes that are not comparable, and
two samples merged into the corpus on 2026-09-03 are what make the gap concrete rather than
suspected.

The corpus is `power-user-linux-setup`'s `plans/2026-09-02-agents-md-adherence-sample-corpus.md`.
Three of its rows carry a high `exit-masked` rate and nothing else in common:

| sample | rate | what was masked    | consequence                                                                       |
| ------ | ---: | ------------------ | --------------------------------------------------------------------------------- |
| 6      |  27% | read-only listings | damage structurally impossible — no exit code carried anything                    |
| 2      |  28% | the gate           | the session **pushed five times** on evidence it could not distinguish from false |
| 7      |  22% | the gate           | seven green claims to the user; the unpiped re-run held, so all seven were true   |
| 8      |  25% | **both**           | listings throughout, **one** masked gate run; five green claims, re-run held      |

[DECISION: **sample 8 is a fourth kind and it breaks the two-column proposal, 2026-09-04.** Added
from this repo's own session `c23aaf97`: 372 calls, 25% masked, and the masked set is overwhelmingly
read-only — `plans.py list | head`, `fitness.py portability | head`, `sweep | head`, pytest runs
through `| tail`. Sample 6's shape, and by its logic harmless. But **one** call in it was
`inv quality.precommit 2>&1 | tail -30`, and five green claims were made across the session. The
unpiped re-run exited 0, so all five held.

A gate-versus-listing **column** cannot express that: the session is 99% column A and the 1% is what
the reader needs. So the useful output is not a second rate but **the masked gate calls themselves,
listed** — one line each, which is a short list by construction and empty for the sessions the
proposal would have scored as clean. The rate stays as context; the list is the finding.]

**The lowest of the three is the one with the most riding on it.** A reader ranking sessions by the
headline number ranks them exactly backwards on consequence. Sample 6 is the cleanest possible case
of a high rate that means nothing: its masked calls were `plans.py list 2>&1 | head -60` and
`--help | head -30`, its repo's gate was run unpiped throughout, and the harvest's own re-run exited
0.

The corpus records a `what was masked` column by hand for exactly this reason, and says so:
"recorded by hand; whether `audit.py` should derive it is the open question below." That question is
an `audit.py` change, so it belongs here rather than there.

## Evidence

The corpus plan is the durable citation and is committed in `power-user-linux-setup` (`da4945a`,
2026-09-03) — read it rather than this summary; it carries all seven samples' tables and the two
merged-away sample plans' original text is recoverable from the same repo's history (`e11f124`, then
the deletion in `da4945a`).

The two samples this plan comes from were themselves filed cross-repo, and their own transcripts
carry the raw calls:

| sample | source repo    | transcript                                   | `--until` boundary          |
| ------ | -------------- | -------------------------------------------- | --------------------------- |
| 6      | `agent-skills` | `13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl` | `2026-09-02T20:32:51+03:00` |
| 7      | `ingesta`      | `7dab6dae-7c67-454f-bba1-981fe3845089.jsonl` | `2026-09-03T13:47:32+03:00` |

The harness keeps a transcript for 30 days by default, so both expire around 2026-10-02. Sample 6's
is the one worth re-reading first: it is an `agent-skills` session, so its calls are against this
repo, and its subject was this rule — it shipped `harvest.py` with "nothing runs through a shell, so
no pipe can eat an exit code" as a design principle while producing `2>&1 | head` in 36% of its own
calls.

Distinctive phrase to find the merged discussion in this session's transcript: "the lower number is
the one with consequences riding on it".

No user correction prompted this — it came out of merging two filed samples into the corpus, and
both filed plans raised it themselves, each naming `agent-skills` as where it belongs.

## Open questions

[NEEDS CLARIFICATION: **what counts as "the gate", and can it be derived at all?** The hand-made
column was easy because a human reading the calls knows `inv quality.precommit` and `pytest` from
`plans.py list` and `--help`. A derivation needs a rule. Candidates: a configurable list of
gate-shaped commands; anything the repo's own task runner exposes; or the weaker but fully general
"was the masked command's output ever asserted about", which needs no list. The last one shades into
the assertions question below rather than being independent of it.]

[NEEDS CLARIFICATION: **calls or assertions — and is `harvest.py claims` already the answer?**
Sample 7 masked 22% of calls and made seven green claims, and it is the claims that reach the user:
a run that masks forty listings and asserts nothing has no reader, while one that masks a single
gate and says "green" once does. `harvest.py claims` already counts assertions, so the number
exists. The question is whether `audit.py` should surface it as a column, or whether it belongs only
in the harvest report where it already is — in which case the fix is a cross-reference in the skill,
not code.]

[NEEDS CLARIFICATION: **does this change `EXPECTATIONS`?** The corpus separately asks whether
`exit-masked` should be scored at all, arguing against on the grounds that it is a symptom of
`head/tail` rather than an independent habit. A gate-only rate is a much better scoring candidate
than the raw one — it has a defensible target of zero — so the two questions are coupled and the
second should not be settled before the first.]

## The same question on a second row, inherited 2026-09-06

From `2026-09-05-rg-replace-counter-matches-its-own-prose.md` when that plan was retired, which
scoped this out of itself:

> [DEFERRED: the per-bundle breakdown in the row's own reporting. `-rn` and `-ril` are different
> failures and one count cannot say which is happening; the distribution is in this plan's evidence
> (`-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1, and **zero** bare `-r`) but the script still does
> not print it. Not done because the anchoring was what made the count trustworthy, and the
> breakdown is worth building on a count worth reading.]

**It is this plan's question with a different row in front of it**, which is the reason for merging
rather than filing it separately: one rate covering outcomes that are not comparable, where the fix
is a breakdown rather than a second number. `exit-masked` mixes a masked listing with a masked gate;
`rg-replace` mixes `-rn` — which loses line numbers and rewrites the matched text — with `-ril`,
which silently turns a case-insensitive file-list search into a case-sensitive line search. A reader
told "81 calls" cannot tell which failure the corpus is actually having.

Two things it adds rather than repeats. **Its distribution is already measured** (the numbers above,
over the 30 days to 2026-09-05), so unlike the gate-versus-listing split this one needs no new
analysis to know what the output would say — only somewhere to print it. And **the anchoring
precondition generalises**: the breakdown was deliberately not built until the count itself was
trustworthy, which is the same ordering this plan should follow, since a per-shape split of a number
that includes prose mentions would split the noise too.

The rejected shape is the same one, for the same reason: a second **column** cannot express it. Both
rows want a short list — the masked gate calls themselves, the bundles actually used — which is
empty for the sessions that have no problem and one line per distinct shape for the ones that do.

## Recommended direction

Rough. The cheap end first, because the expensive end may turn out not to be needed.

1. **Check what `harvest.py claims` already produces** before adding anything to `audit.py`. If its
   output already pairs an assertion with the call it rests on, the column may be a report change
   rather than an analysis one.
2. **Try the general rule before the configurable list** — "was this masked command's output
   asserted about" needs no per-repo gate catalog and degrades sensibly on a repo whose gate has an
   unusual name. A list is the fallback, not the design.
3. **Re-score the seven existing samples with whatever lands**, since the corpus's whole value is
   that the rows are comparable. A column that cannot be back-filled from the surviving transcripts
   is worth less than one that can, and three of the seven transcripts expire around 2026-10-02.
4. Leave `EXPECTATIONS` alone until 1–3 answer the third question above.
