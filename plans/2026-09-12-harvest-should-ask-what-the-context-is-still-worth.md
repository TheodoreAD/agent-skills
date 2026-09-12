---
status: idea
updated: 2026-09-12
---

# Harvest asks what to save; nothing asks what the context is still worth

## Context

Proposed by the user 2026-09-12, in their words: a check that runs _"at the beginning"_ of
`session-harvest` so _"we don't miss out on using valuable context we already have, and also
understand first how full the context is. Perhaps a decision should come after that."_

`session-harvest` answers one half of the end-of-session question — what is worth **persisting**,
and where each item goes. It says nothing about the other half: whether the accumulated context is
worth **spending** before it is lost. Those are opposite actions on the same input, and only one has
a mechanism.

**The session that prompted this is the evidence.** Six research agents produced findings across six
streams. Of what they produced: the decisions reached a plan; two skills' worth of rules reached
`SKILL.md` files; and **17 measurement scripts plus ~20 MB of corpora sat in `/tmp/claude-1000/`**,
which is shared between parallel agent jobs and cleared on reboot. Most of the naming research
existed only in the transcript. None of that was caught by any mechanism — it was caught because the
user asked "do we have the research saved somewhere?", and the honest answer was "partially". A
session that had ended ten minutes earlier would have lost it.

## The hard half is derivable, and that is the finding that makes this buildable

Measured 2026-09-12 on this machine. The most recent assistant message in a Claude Code transcript
carries a `usage` object, and its `cache_read_input_tokens` is what was actually sent as context for
that request:

| source                                          | value       |
| ----------------------------------------------- | ----------- |
| `cache_read_input_tokens` (last assistant turn) | 529,415     |
| plus the autocompact buffer                     | 33,000      |
| **derived total**                               | **562,415** |
| what `/context` reported at the same moment     | **564,700** |

**Within 0.4%.** So a stdlib script reading the transcript store can answer "how full is the
context" without any harness-internal API, and without asking the model to estimate — which it
cannot do reliably about itself. `harvest.py` does not read those fields today.

[PITFALL: **the number is per-harness and per-transcript-format, not a fact about agents.** It comes
from Claude Code's own JSONL and its `usage` shape; `session-harvest` already declares that its
transcript reading is a Claude Code artefact and reports **unavailable rather than zero** when the
store is absent. This must do the same. A context-fullness figure of "0%" on a harness whose
transcripts it cannot read is exactly the clean-bill-of-health-from-a-check-that-never-ran failure
the sweep exists to prevent.]

## What the corpus already settles, so this does not relitigate it

- **No automatic trigger.** The obvious design is a hook firing when context crosses a threshold,
  and it is refused by the standing rule that a recurring agent behaviour is corrected by teaching
  the agent what to run, never by a mechanism that fires behind its back. `session-harvest` is
  additionally on-demand by construction and installs no hooks.
- **The prompt shape is already designed.** `plan-docs`' `absorb` solves the identical problem — a
  prompt arriving in a session the user opened for something else — and its rules transfer verbatim:
  one question for the set rather than one per item, the **cost stated inside the question**, and
  "not now" as a real answer. A retirement prompt that reads as "shall I tidy up?" cannot be
  answered honestly; neither can "shall we use the context?".
- **Script measures, model judges.** Context fullness and the inventory of unpersisted artifacts are
  deterministic. Which of them is _worth_ anything is not, and a script that ranked them would be
  inventing the judgement it cannot make.

## The objection worth recording, because it is not fully answered

**The timing is wrong, and the best available shape is still the proposed one.** The value of "do
not waste accumulated context" is highest well before anyone decides to stop; at harvest time the
question competes with a decision already taken. But the trigger that would fire at the right moment
is the automatic one the corpus refuses, which leaves two surfaces and no third: harvest's opening
report, and a session raising it unprompted.

[DECISION: **both, and the second is why this is a skill change rather than only a script change.**
The report is the mechanism; a sentence in `SKILL.md` licensing a session to raise the same question
mid-flight is what covers the case where harvest is never run. Neither alone is sufficient — a
report nobody reaches is inert, and an instruction with no measurement behind it is a hunch about a
number the model cannot see.]

## What the inventory would contain

Deterministic, and each item is a thing this session actually produced and nearly lost:

| signal                                           | why it is a candidate                                           |
| ------------------------------------------------ | --------------------------------------------------------------- |
| context fullness, derived as above               | decides whether spending more is even possible                  |
| scratch files outside any working tree           | `/tmp` is shared between agent jobs and cleared on reboot       |
| research clones created during this session      | cheap to keep, expensive to re-fetch, invisible to `git status` |
| files read but never written                     | reading is the cost already paid; a finding may be unrecorded   |
| subagent reports with no destination in a commit | the largest single body of unpersisted text in this session     |

[NEEDS CLARIFICATION: **how to detect "a finding that reached no file" without reading the whole
transcript back.** The honest signals are weak: a subagent completed and no commit followed, or a
long assistant turn with no subsequent write. Both are heuristics, and a false "you have unsaved
findings" on every session is how a prompt gets ignored. Worth measuring against real transcripts
before shipping any rule, the same way the listing-budget work was.]

[NEEDS CLARIFICATION: **whether the threshold for raising it at all should be context fullness or
inventory size.** A 20%-full session with 17 orphaned scripts wants the prompt; a 90%-full session
with nothing unsaved does not. Fullness alone is the wrong gate, which suggests the report leads
with the inventory and mentions fullness as the constraint on what can still be done about it.]

## Recommended direction

1. **Add the usage read to `harvest.py` and report it as a fact, not a verdict** — the derived
   total, the window if it can be established, and `unavailable` rather than a number when the store
   cannot be read. This is small, testable against a fixture, and useful on its own.
2. **Add the unpersisted-artifact inventory**, starting with the two signals that are unambiguous:
   scratch paths outside any working tree, and research clones newer than the session's first
   timestamp. Leave the heuristic signals out until measured.
3. **Then the prompt**, on `absorb`'s pattern, ordered **before** the existing harvest report — and
   a `SKILL.md` sentence that says a session may raise the same question whenever it notices, rather
   than only here.
4. **Do not** make it a pitch. Harvest's job is saving; this is one short section that a reader can
   dismiss in a line, and its default outcome is "nothing to spend, carry on".
