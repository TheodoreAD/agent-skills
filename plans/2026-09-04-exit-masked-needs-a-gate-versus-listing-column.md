---
status: landed
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

## Measured at corpus scale, 2026-09-06 — and it breaks the listing decision

Step 1 of the recommended direction, taken. The answers are not the ones the four hand-read samples
suggested, and the difference is scale: the decision above was drawn from a session that was 99%
listings with one masked gate in it, and that session is not typical.

**The `2>&1 | filter` population splits almost exactly in half.** Over the 7 days to 2026-09-06,
2,770 masked calls: **1,389 gate-shaped (50%)**, 1,381 not. **55 of 67 sessions** have at least one
masked gate, and the per-session counts run 83, 74, 74, 63, 56, 54, 52 …

[DECISION: **a name list derives "the gate" well enough, and the weaker general rule is not
needed.** `inv <ns>.(quality|test|check|precommit)`, `pytest`, `basedpyright`, `ruff`, `mypy`,
`npm test`, `cargo test`, `make`, `tox`, `nox`, `pre-commit run` — one regex, no per-repo catalog,
and it classifies 50% of the masked population. The "was its output asserted about" rule was
preferred on generality; it is not needed to answer this question and would couple the row to the
claims matcher, so it stays available for a repo whose gate has an unusual name rather than being
the design.]

[PITFALL: **the "short list, empty for clean sessions" premise is false.** The decision above chose
a listing over a column on the grounds that masked gate calls are few by construction and the list
would be empty for the sessions the column would have scored as clean. At corpus scale it is
neither: 40–80 lines for a busy session, and non-empty for **55 of 67**. Deduplicating does not
rescue it — the distinct command shapes per session run to a median of 14 and a maximum of 77,
because the same gate is typed with different `tail -N` values and different chained prefixes.

So the listing is a report section, not a footnote, and the thing that actually separates the two
populations is the pair of counts: "136 masked, 74 of them a gate". That is one line, it is exactly
the distinction the hand-made column recorded, and the existing `--samples` machinery already prints
examples for anyone who wants them. The list survives as a `--samples`-bounded dump, not as the
row.]

[DECISION: **`harvest.py claims` is not already the answer, and the reason is worth keeping.** It
prints two independent lists — every green claim, then up to `--samples` masked calls — and **pairs
nothing**: no claim is tied to the call it rests on, and the masked list is not gate-filtered. So
the assertion count exists and the correspondence does not. Whether to build the pairing is a
separate question from this row; what is settled is that citing `claims` as the existing answer
would have been wrong.]

[DECISION: **`exit-masked` stays out of `EXPECTATIONS`, 2026-09-06** — and the gate-only rate does
not go in either, which is the part that changed. The hoped-for argument was that a gate-only rate
has a defensible target of zero; the disqualifier is one the corpus question could not see, and
`2026-09-05-exit-masked-measures-a-risk-pipefail-removed.md` supplies it: **whether a masked exit
code cost anything depends on the shell**, a shell setting `pipefail` carries the status through the
pipe, and a transcript records the command and not the shell. So any verdict on this row — raw or
gate-only — is a confident number standing on an assumption about a machine the instrument never
saw. `head/tail` scores the habit instead, from output loss, which holds everywhere. The row is
reported, split into gate and listing, and left unjudged; a test pins the absence so it reads as a
decision.]

## The same question on a second row, inherited 2026-09-06

From `2026-09-05-rg-replace-counter-matches-its-own-prose.md` when that plan was retired, which
scoped this out of itself:

> [DEFERRED: the per-bundle breakdown in the row's own reporting. `-rn` and `-ril` are different
> failures and one count cannot say which is happening; the distribution is in this plan's evidence
> (`-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1, and **zero** bare `-r`) but the script still does
> not print it. Not done because the anchoring was what made the count trustworthy, and the
> breakdown is worth building on a count worth reading.]

**Re-measured 2026-09-06 over 30 days** (31,011 calls, 86 tagged), which changes what the breakdown
is for: `-rn` × 62, **bare `-r` × 13**, `-ril` × 6, `-rln` × 4, `-rl` × 2, `--replace` × 1. The bare
`-r` count moved from zero to 13, and every one of the 13 is the deliberate extraction idiom
(`rg -o -r '' <pattern> <path>`) — correct usage of a real flag, which the row currently counts
alongside the accidents. So the breakdown is not only a reporting nicety: **it is the precondition
for scoring the row at all.** 74 bundle instances against 14 deliberate ones, and `zero` is
defensible on the first and unsatisfiable on the second, which is what
`2026-09-06-audit-session-mode-silently-drops-flags-and-rows.md` concluded when it tried to give
`EXPECTATIONS` an `rg-replace` entry and found it could not.

One live failure in the window, the first on record for this row: `rg -n "…" <path> -r 2>/dev/null`
— the shell took `2>/dev/null` as a redirect, so `-r` reached `rg` with no value, exit 123, and the
same redirect discarded the message that said so.

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

The rejected shape was the same one, for the same reason: a second **column** cannot express it.
Both rows were said to want a short list — the masked gate calls themselves, the bundles actually
used — empty for the sessions that have no problem and one line per distinct shape for the ones that
do. **The measurement above withdraws that for `exit-masked`** (median 14 distinct shapes, up to 77)
and leaves it standing for `rg-replace`, where six bundle spellings is the whole vocabulary. The two
rows turn out not to want the same output after all, which is worth knowing before one design is
built for both.

## Recommended direction

Revised 2026-09-06, after taking steps 1 and 2. What is left is smaller than what was expected.

1. ~~Check what `harvest.py claims` already produces~~ — done: it pairs nothing, so no report-only
   fix was available.
2. ~~Try the general rule before the configurable list~~ — done: the name list classifies half the
   masked population with one regex, and the general rule is not needed to answer this.
3. ~~Build the two counts, not the listing~~ — **done 2026-09-06** (`1cac6e3`): `exit-masked` prints
   `n wrapped a gate, m a listing` from `GATE_RE`, and `rg-replace` prints its flag spellings, both
   in the vertical session view that
   `2026-09-06-audit-session-mode-silently-drops-flags-and-rows.md` settled the shape of.
4. ~~Then `EXPECTATIONS`, on the bundle sub-row only~~ — **done 2026-09-06**. `rg-replace-bundle` is
   a tag (a flag group of two or more letters containing `r`, which always means `-r` swallowed the
   rest as its replacement string), it is in `SESSION_ROWS`, and `EXPECTATIONS` scores it `zero`.
   `rg-replace` itself stays unjudged, the way `grep-r-not-rg` and `find-exempt` do: 13 of its 86
   hits are the deliberate `-o -r ''` idiom. Over 30 days the split is 73 bundle calls of 87 tagged.
5. Re-scoring the seven samples is now a **second** correction rather than a first: the heredoc
   truncation understated several of the same rows, and that is filed against the repo that owns the
   corpus (`~/plans/…/2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md`). Whatever
   lands here should be back-filled in the same pass rather than in two, and three of the seven
   transcripts expire around 2026-10-02.
