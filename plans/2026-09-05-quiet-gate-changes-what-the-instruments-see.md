---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 92ffb648-b58c-42c8-a813-bc3782a7be4c.jsonl
source_moment: 2026-09-05T13:39:01+03:00
---

# Layer 2 landed, and it changes what `audit.py` and `claims` can measure

## Context

Layer 2 of `plans/2026-09-05-a-piped-gate-that-cannot-lie.md` landed in `repo-tasks` on 2026-09-05
(commits `ba9e8e6`..`4c0bd3a`, pushed): every gate step's output is folded on success, a failing
step replays its output whole, and both gates end with a verdict line —
`quality.precommit: PASS  15 steps, 592 passed, 4.5s`, or
`FAIL  ruff check . exited 1 (output above)`.

That plan's own `## Verification` schedules the measurement: _"A week after each of layers 1 and 2:
`audit.py --days 7 --compare <that baseline>`."_ Two things stand between that command and a
trustworthy answer, and both were found by running the instruments rather than by reading them.
Neither is a reason to delay the measurement; both change how its output must be read.

## 1. A baseline records no instrument version, and the instrument moved

`~/.local/state/session-bash-audit/2026-09-05-pipefail-live.json` is the anchor the measurement
compares against. Its fields are `saved`, `days`, `note` and `models` — **nothing says which
`audit.py` wrote it.** Between that file being written (02:13 local, 2026-09-05) and this session's
run, two commits changed the script's pattern layer:

- `0165577` "a pipe inside quotes is not a pipe" — 01:51 local, **22 minutes before** the baseline
  was saved. Whether the baseline has it depends entirely on whether that run used the checkout or
  the installed copy, and nothing on disk records which.
- `88bfd42` "slug a project path the way the harness does" — 13:20 local, **after** it. Affects
  `cd-own-repo` and `git-C-own-repo`, both at 0% on either side here, so no practical effect on this
  particular comparison.

The exposure is specific rather than general: `0165577` changes what counts as a pipe, and the pipe
rows are the entire subject of the layers-1-through-3 measurement. A `--compare` that straddles it
attributes a pattern-definition change to the gate change, in the direction that flatters the gate —
and the JSON gives a reader no way to notice.

This is **not** the defect in `2026-09-05-save-baseline-overwrites-silently.md`, which owns the
silent overwrite and the UTC-vs-local naming of `saved`. Same file, adjacent concern: that one is
about which baseline survives, this one about whether two surviving baselines are comparable at all.
Worth deciding together; they touch the same writer.

[DECISION: record, do not refuse. Landed in `c01973d`, folded into the writer this section shares
with `save-baseline-overwrites-silently` per the user's decision 2026-09-05. `save_baseline` now
writes an `instrument` field — the script's own short SHA, `-dirty` when its checkout has
uncommitted changes to `audit.py`, `None` when it did not run from a checkout at all. Refusing was
rejected for the reason this question already names: most pattern commits do not touch most rows, so
it would only have to be overridable.]

**§1 is done; §2 below is not, which is why this plan stays open.** The instrument question landed
the same day it was filed, and it landed larger than it was written: the patterns themselves were
anchored hours later (`2536d38`), so **every baseline written from now on is on a different
instrument than the two already on disk** — which is precisely the confusion this section describes,
now with a field that says so.

[NEEDS CLARIFICATION: whether a baseline written by the installed copy can be identified after the
fact at all. Still open, and now the only thing standing between the two existing files and the
week-later run. The recorded field is prospective; it says nothing about a file written before it
existed. The honest fix for those two remains a hand-written `note` — and both now also predate the
pattern anchoring, so the note has two things to say, not one.]

## 2. `claims` counts the gate's own verdict as a claim, and layer 2 makes that structural

`harvest.py claims` reports "messages that told the user a gate or suite was green". On this session
it returned three, and one of them is this:

```
2026-09-05T10:36:43.042Z  quality.precommit: PASS  15 steps, 592 passed, 4.5s
```

That is not a sentence anyone wrote. It is the gate's own last line, quoted verbatim inside a fenced
code block in a report **demonstrating the new output shape** — evidence being shown, counted as a
conclusion being asserted.

Before layer 2 this would have been a rare accident. After it, it is structural in two compounding
ways. The verdict line now exists at all, it is designed to be the one line worth quoting, and
`PASS` beside a test count is exactly the string the matcher looks for — so **every session that
demonstrates the gate's output inflates its own green-claim count**, in every repo that consumes
`repo-tasks`. The bias has the same direction and the same readership problem as
`2026-09-05-rg-replace-counter-matches-its-own-prose.md`: the number rises when someone works on the
thing the number measures, which is when it is read.

That plan is the pair, and this is a third instance of its shape in a **second script** — its own
open question asks whether to anchor one pattern or all of them, and two rows in `audit.py` plus one
in `harvest.py` is a different answer from two rows in one file. Merge them if they read as one
topic on absorption; they were filed apart only because this one has a cause the other does not (a
downstream tool started emitting the matched string).

[NEEDS CLARIFICATION: can `claims` tell a quotation from an assertion at all? A fenced code block is
the obvious signal and this instance sits inside one. It is not general — a verdict pasted inline
still reads as a claim, and arguably is one.]

[NEEDS CLARIFICATION: whether the count should exclude a verdict line whose own text says which
command produced it. `FAIL  ruff check . exited 1` is self-evidencing in a way "the gate is green"
is not, and the whole point of layer 2 is that the last line carries its own provenance.]

## Evidence

- Layer 2 as landed: `repo-tasks` `contributing/quality-gate.md`, "What the gate prints" — the
  decisions, and the pitfall recording that pipefail and the fold cover different halves of the lie.
- The `claims` false positive, isolated from this session's transcript by re-reading assistant text
  blocks: exactly one `PASS` line, inside a code block, at `2026-09-05T10:36:43.042Z`.
- This session's own rates, from the checkout's `audit.py`: 88 Bash calls, `head/tail` 2%,
  `exit-masked` 2%, 9/11 expectations met against the baseline above. Both masked calls were
  deliberate probes of the new failure shape (`inv quality.check 2>&1 | tail -3` on a red gate,
  verifying the verdict survives the pipe) rather than the habit the row exists to count — a fourth
  instance of the same "working on it inflates it" shape, too narrow to file on its own.
- The distinctive phrase to search this transcript for is the user's opening instruction, _"Before
  touching quality.py: ls ~/.local/state/session-bash-audit/"_.

## Recommended direction

Record the instrument's commit in the baseline before the week-later run, since that run is the
first consumer of the answer and the cheapest moment to make it verifiable. Decide (1) alongside
`save-baseline-overwrites-silently` — one writer, two defects — and fold (2) into
`rg-replace-counter-matches-its-own-prose` if it reads as one topic, which it may.

**The measurement itself should still go ahead on schedule.** Layer 3 had not landed as of
2026-09-05, so layer 2's effect is not yet separable from it either way; these two findings say how
to read the result, not whether to take it.
