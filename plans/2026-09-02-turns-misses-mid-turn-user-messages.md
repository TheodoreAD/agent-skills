---
status: landed
updated: 2026-09-02
source_repo: github.com-personal/power-user-linux-setup
source_session: 361b5d16-284b-4286-8233-45c011924707.jsonl
source_moment: 2026-09-02T17:12:38+03:00
---

# `harvest.py turns` cannot see a message the user sends mid-turn

## Context

`session-harvest` step 4 exists because "a compacted session hands you someone else's précis" —
`turns` is the answer, printing the real user turns and every `AskUserQuestion` answer so a harvest
reads the brief rather than its own summary of it.

**It misses a third population: a message the user sends while a turn is still running.** Claude
Code surfaces those inside the running turn, usually alongside a tool result. In the transcript they
are not `type: "user"` — they are recorded as `type: "queue-operation"` and `type: "attachment"`, so
a scan built on user turns plus answer-preambles finds neither.

This is the same shape as the `[PITFALL:]` already in step 4 about the answer filter, one population
further out — and it fails the same way, by returning a plausible, complete-looking set.

## Evidence

Session `361b5d16-284b-4286-8233-45c011924707` in `power-user-linux-setup`, 2026-09-02.

- `turns` reported **6 user turns, 8 slash-command wrappers, 5 AskUserQuestion answers**. Of the 6
  user turns, two were `<task-notification>` blocks and one was an interruption marker, leaving
  three real instructions.
- **The single richest instruction of the session appears in none of them.** Mid-turn, the user
  asked for an asciinema-style recording of the install running in a Docker container for the front
  page, and for image-generator prompts, with a full brief on theme: _"the theme should be
  tehcnical, a little playful, but not cutesy, either sci-fi or high fantasy, but no steampunk."_
  That message produced two plan files and six commits — roughly the last third of the session — and
  `turns` shows no trace of it.
- Confirmed in the transcript rather than inferred. `rg -c 'ascii cinema'` returns 3; reading the
  entry types of those lines gives:

  ```text
  line  834: type='queue-operation'
  line  835: type='queue-operation'
  line  845: type='attachment'
  ```

  plus two later `assistant` entries that merely quote it back. No `type: "user"` entry carries it.

- The failure is silent in the direction that matters: a harvest reading only `turns` would have
  concluded the user never asked for the recording or the imagery, and would have harvested against
  its own summary — the exact outcome step 4 exists to prevent.

[PITFALL: **the miss is invisible precisely on the sessions where it costs most.** A mid-turn
message is what a user sends when they think of something while the agent is working, so it is
disproportionately new scope rather than a correction to what is already running — the kind of
instruction with no earlier trace in the transcript to recover it from. A session where the user
waited their turn loses nothing here; a session where they did not can lose a third of the brief
with no indication in the output.]

## Open questions, answered by the transcript they were asked about

[DECISION: **two populations, one source.** `queue-operation` carries the message twice — `enqueue`,
then `remove` on delivery — and only the enqueue is taken. The `attachment` copy
(`attachment.type == "queued_command"`) is counted **beside** the matched set as a cross-check and
never used as a source: on the cited transcript `attachment` holds 230 `total_tokens_reminder`
entries against 2 `queued_command`, so matching the entry type would repeat the over-broad half of
the mistake the answer filter already made.]

[DECISION: **pinned by fixtures rather than by a live transcript.** The tests build all three
populations as dicts, so an upstream rename fails a test instead of silently returning an empty
third population — which reads exactly like a session where nothing was sent mid-turn. Whether other
harnesses have an equivalent is left open deliberately: this is Claude Code's own internal shape and
the honest scope is the harness whose transcripts the script reads.]

[DECISION: **the interruption marker is counted, and so are task notifications, both separately from
user turns.** Neither is an instruction, and both were previously printed as user turns — which is
precisely why the cited session's count read as six when three were real.]

## Recommended direction

Extend `turns` to a third population, printed distinctly rather than merged into the user-turn list,
so a reader can see that a mid-turn message existed and where it landed in the order. Keep step 4's
existing discipline: match by entry type, print a raw count beside the matched set, and let a
disagreement surface instead of resolving it.

Add a fixture-based test alongside the existing answer-filter tests. This is the second time the
same step has shipped a filter that returned a plausible, incomplete set, and both times the
incomplete version looked correct on the session that produced it — a fixture with all three
populations is what makes the third one's absence fail loudly.

Worth a line in step 4's prose as well: the brief can arrive in three ways, and a harvest that finds
only two has not been told so.

## What landed, 2026-09-02

Absorbed and fixed the same day it was filed, by the session that had shipped `turns` an hour
earlier. All three of its questions are answered from the transcript it cites rather than by
judgement:

1. **`queue-operation` and `attachment` are two populations, and only one of them is the source.**
   Each queued message is recorded twice as a `queue-operation` — `operation: "enqueue"`, then
   `operation: "remove"` when it is delivered — so only the enqueue is taken. The same message also
   appears as an `attachment` whose own `type` is `queued_command`, and that count is returned
   **beside** the matched set as the cross-check, never as a second source: `attachment` carries
   mostly harness noise on that transcript (230 `total_tokens_reminder` entries against 2
   `queued_command`), so matching the entry type would have been the over-broad half of the mistake
   this step has already made twice.
2. **The field names are pinned by fixtures, not by a live transcript.**
   `tests/unit/test_harvest.py` builds all three populations as dicts, so a rename upstream fails a
   test rather than silently returning an empty third population — which reads exactly like a
   session where the user sent nothing mid-turn.
3. **The interruption marker is counted, and separately.** So are task notifications, which arrive
   in _both_ populations. Neither is an instruction, and the previous behaviour of printing them as
   user turns is what made this session's count read as six when three were real.

The measurement on the transcript this plan cites, before and after:

| what `turns` reported | before                               | after                                                            |
| --------------------- | ------------------------------------ | ---------------------------------------------------------------- |
| user turns            | 6 (two notifications, one interrupt) | **3**, with the other three labelled and counted separately      |
| mid-turn messages     | 0 — the population did not exist     | **1**, the asciinema-and-imagery brief this plan was filed about |
| answers               | 5                                    | 5                                                                |

`SKILL.md` step 4 now opens on "the brief arrives in three ways, and a run that finds two has not
been told so", with the reason the miss is worst where it matters: a mid-turn message is what a user
sends when they think of something while the agent is working, so it is disproportionately new scope
with no earlier trace in the transcript to recover it from.
