# Skill fitness — what was measured, and what it cost to learn

Dated findings behind `SKILL.md`. Append; don't rewrite history — the value is in the deltas.
External prior art and published research live in [`research.md`](research.md).

**These are one machine's measurements**, taken on the author's setup: thirteen installed skills, a
Claude Code transcript store going back to 2026-07, and CLI 2.1.251. Read the harness facts as
things to re-check after an upgrade, the method as reusable, and the specific numbers as a worked
example rather than as your own baseline.

The single most useful thing in this file is the **ledger of things that did not work**. Five free
heuristics over prose have failed here, and every one of them looked obviously correct before it was
run.

## Contents

- [The trigger-run ledger: 119 runs, 0 steals](#the-trigger-run-ledger-119-runs-0-steals)
- [Everything this tool prints is a hypothesis](#everything-this-tool-prints-is-a-hypothesis)
- [The ledger of failed heuristics](#the-ledger-of-failed-heuristics)
- [The listing budget, read from the binary (2026-08-31)](#the-listing-budget-read-from-the-binary-2026-08-31)
- [Reading listings the harness actually sent](#reading-listings-the-harness-actually-sent)
- [Two invocation mechanisms, and why neither is the rate](#two-invocation-mechanisms-and-why-neither-is-the-rate)
- [The absorption miner's design, with the numbers](#the-absorption-miners-design-with-the-numbers)
- [Harness facts to re-check after a CLI upgrade](#harness-facts-to-re-check-after-a-cli-upgrade)

## The trigger-run ledger: 119 runs, 0 steals

Six suites, three runs per case, all against the installed set on 2026-08-31.

| suite                            | cases | what it tested                            | result                   |
| -------------------------------- | ----- | ----------------------------------------- | ------------------------ |
| `contention-python-family`       | 8     | the python family, easy phrasings         | 24/24                    |
| `contention-python-family-hard`  | 6     | the same, phrased in the contested region | 5/6                      |
| `python-conventions-split`       | 11    | the three-way split, full regression      | 33/33                    |
| `never-fired-mcp-skills`         | 7     | the two skills with zero invocations      | 7/7                      |
| `contention-skill-meta-pair`     | 10    | the corpus's top-ranked pair              | 9/10 → 10/10 after a fix |
| `explicit-heavy-session-harvest` | 10    | the one explicit-heavy skill              | 10/10                    |

**Zero cross-steals in 119 runs.** Both failures were the same shape and it is not contention:

| the request                                                                      | fired        | why                                                  |
| -------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------- |
| "Our automation scripts have grown messy. Where do I start cleaning them up?"    | nothing, 3/3 | the description spoke `tasks.py`, `inv`, "namespace" |
| "This skill has grown to cover three different things. Is it worth breaking up?" | nothing, 3/3 | the description said "over-scoped" and "split"       |

Both were fixed by a candidate description carrying the request's own vocabulary, and both fixes
were scored before adoption. **A description built from the tool's vocabulary rather than the
request's does not lose to a competitor; it loses to silence.**

[PITFALL: **vocabulary is not the only cause of a miss to silence, and 2026-09-01 is the case that
proves it.** `python-refactor-audit`'s flagship prompt — "this module is 3,000 lines … nobody has
ever reviewed it as a whole … how do I restructure it without breaking anything?" — fired **1 time
in 6** across two full runs, while its three other positives went 3/3 in both. The description
already carries that sentence's own words nearly verbatim ("auditing a file nobody has reviewed as a
whole", "how to restructure it safely"), and the same prompt also selected nothing for the rejected
extend-`python-conventions` wording. So the fix for the two 2026-08-31 misses does not generalise
into a diagnosis, and reaching for closer wording is a guess until something measures the cause.

**Corrected 2026-09-02.** This entry used to end by naming the cause — "a broad _how do I go about
X_ request can select nothing even when the vocabulary matches" — and that explanation is now
refuted; see item 6 in the ledger of failed heuristics. The miss is real and still unexplained. What
changed is that it is no longer attributable to the request's breadth, which makes it a fact about
one pair of skills rather than about the corpus.]

[PITFALL: **an easy suite cannot tell "no contention" from "cases too easy".** The first suite
passed 24/24 and every prompt in it named something only one skill claims. It was the second,
phrased in the region a broad skill's description actually claims, that produced a finding. This is
the same warning `skill-creator` gives about negative cases, and it applies just as hard to
positives.]

[PITFALL: **a candidate competes with its own installed twin.** Both names satisfy the same case, so
scoring them as separate skills reports a failure every time the incumbent wins. The first candidate
run reported two such failures while the case the candidate was written to fix passed 3/3 — the
proposal was working and the scoreboard said otherwise.]

[PITFALL: **a candidate score errs in both directions.** Measured twice on 2026-08-31: one request
went 0/3 → 1/3 as a candidate → **3/3** shipped; another went 0/3 → 2/3 as a candidate → **2/3**
shipped. An earlier version of this file generalised an uplift from the first observation alone; the
version after it called the candidate figure a **lower bound**, which held for those two and was
refuted on 2026-09-01 by `python-refactor-audit` — 12/12 as a candidate, **11/12** installed on the
same twelve cases, its flagship case dropping **3/3 → 1/3** with truncation ruled out by `budget`.
Two generalisations from small samples, in opposite directions, from the same measurement. Quote the
`run` figure.]

[PITFALL: **three runs is a floor.** A case that scored 3/3 twice came back 2/3 with nothing
relevant changed. Read one dropped run as variance, and do not compare a 3/3 against a 2/3 as though
the difference were signal.]

## Everything this tool prints is a hypothesis

The pattern across the whole of 2026-08-31, and the thing that should govern how the tool is read.
Every signal it produces generated a hypothesis that a live run then refuted:

| signal                                         | predicted                               | live result                               |
| ---------------------------------------------- | --------------------------------------- | ----------------------------------------- |
| static overlap + directional shadowing         | a broad skill shadowing two narrow ones | **0 steals in 14 cases**                  |
| a new skill next to its two closest neighbours | it would take their requests            | **0 steals in 15**                        |
| the corpus's top-ranked pair by similarity     | contention across a deliberate boundary | **0 steals in 30**                        |
| two skills with zero invocations               | broken descriptions                     | **7/7 — there had been no demand**        |
| an inverted `auto`/`explicit` split (13 vs 87) | the description fails on real phrasings | **10/10, controls and paraphrases alike** |

Three "defects" that were not defects, against two real failures — both misses, both found only by a
should-trigger case phrased in a stranger's words.

So the tool's honest job is **generating questions cheaply and ranking which are worth paying to
answer**. Nothing it prints is a verdict on its own.

## The ledger of failed heuristics

Every one of these looked obviously correct before it was measured. Recorded so they are not
rebuilt.

1. **The vendor scanner's Jaccard > 0.7** (see `research.md`) — on prose descriptions, close to
   never fires.
2. **This tool's own first shadow cut**, an absolute containment threshold of 0.5 — flagged nothing.
   Replaced by a corpus-relative cut, which is why shadowing is judged against the corpus's own
   distribution.
3. **A demand proxy, first construction** — counting sessions whose user turns contained 3+ of a
   skill's distinctive terms. Gave 370–430 for all eleven skills across 593 transcripts, including
   one skill written that day.
4. **A demand proxy, second construction** — per-turn matches on terms claimed by at most two
   skills. Made the numbers larger rather than sharper.
5. **Gap detection, three constructions** (2026-08-31), all against 165 real opening requests:
   - terms frequent in requests but absent from every description → `look`, `need`, `don`, `let`,
     `get`, `make`;
   - the discriminative version, terms over-represented in sessions where nothing fired versus
     sessions where something did → ratios resting on counts like 5-against-1, winners `previous`,
     `latest`, `either`, `lot`;
   - the non-lexical one, harvesting the user's own words from just before an explicitly typed
     `/name` — of ~130 typed invocations nearly every preceding turn was harness boilerplate, and
     the two genuine finds were spotted by reading the output, not by any rule in it.

**The common cause**: skill descriptions and real requests share too much ordinary technical English
for a bag-of-words measure to separate them, and a column that cannot discriminate is worse than no
column because it still gets read as a finding. The fix each time was either a corpus-relative
measure or paying for a real run.

Two structural no-ops found the same way:

- **The trigger-clause extraction.** `Skill.trigger_text` took the span from a `Use when` lead-in
  onward, on the reasoning that only the trigger half decides selection. It stripped **nothing from
  12 of 13 descriptions** and three characters from the thirteenth — because this repo's convention
  puts the trigger clause first, so the lead-in matches at position zero. The prose it meant to
  exclude _trails_ the clause. Deleted.
- **The corpus-derived stop list drops exactly one term** (`instead`) on a 13-skill corpus, because
  its cut needs a term in half the corpus. It is a real weighting, not a real filter, and it
  strengthens as the corpus grows. This is why `overlap`'s shared-term lists are full of `working`,
  `writing`, `rather`, `before`.

And one measurement that closed a question by showing it did not matter: **IDF-weighted and
unweighted rankings agree on seven of the top eight pairs**, by similarity and by containment alike.
The choice of similarity measure is not what limits the signal; corpus size is.

6. **"A broad _how do I go about X_ request is answered directly rather than routed"** (2026-09-02).
   The best available explanation for `python-refactor-audit`'s flagship case missing five of six
   live probes, once truncation and vocabulary had both been ruled out for it — and it is wrong.
   Tested with three matched pairs differing only in breadth, one per high-usage skill, at three
   runs each (`evals/broad-request-shape.json`): the broad halves for `plan-docs` and
   `session-bash-audit` fired **3/3 each**, as did their narrow halves. Breadth is not the variable.

   **What the same run did find is the opposite shape**: "Should this return a bare tuple or a
   `NamedTuple`?" — as narrow and as in-vocabulary as a prompt can be, against a description that
   contains the word `NamedTuple` — selected **nothing in two of three runs**. Not truncation:
   `budget` reported no new truncated listing and no new bare-name observation after the run, so all
   24 probes saw the full description.

   Two lessons, and the second is about writing suites rather than about selection. The measured
   claim is now "one skill's own selection is unreliable", which is a narrower and less satisfying
   finding than a corpus-wide rule about request shape — and that is the point: the corpus-wide rule
   was the attractive one and it did not survive contact. And the suite's first case expected
   `python-conventions` for "this module has grown for weeks … how do I clean up how its data is
   shaped", which `python-refactor-audit` took 3/3 — **correctly**, on reflection. An `expect` set
   by the suite's author is a hypothesis too, and a "failure" against a wrong expectation is not
   evidence of anything.

## The listing budget, read from the binary (2026-08-31)

Read out of the Claude Code 2.1.251 binary and confirmed against the CLI's own overflow warning,
because the documented account ("descriptions are shortened to fit") is not what the code does.

| the question         | the answer                                                                                          |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| units                | **characters**: `context_window_tokens × 4 × skillListingBudgetFraction` (default 0.01)             |
| the number           | **8,000 on a 200k-token model**; `SLASH_COMMAND_TOOL_CHAR_BUDGET` overrides absolutely              |
| an entry costs       | `- <name>: <description>`, description capped at `skillListingMaxDescChars` (1536), plus 1 per gap  |
| who can be truncated | **only user and project skills** — most of the harness's own entries are exempt                     |
| what truncation does | drops the description **whole**; the entry becomes `- <name>`                                       |
| the order            | descending `usageCount × max(0.5^(days_since_use / 7), 0.1)`, from `~/.claude.json`                 |
| and it is greedy     | each entry keeps its description if the room left allows, so a long one is dropped past a short one |

**The budget is model-dependent, and that is the headline.** The same corpus is comfortable on a
large-window model and truncated on a 200k one. Measured the same hour: this machine's listing drew
the overflow warning under `--model claude-haiku-4-5-20251001` (8,000 budget) and no warning at all
on the session's own model, which puts that window above 387,150 tokens.

[PITFALL: **the exempt set is narrower than "the harness shipped it" and is not derivable from
origin.** In a real listing, `security-review` was demoted while `code-review`, `run` and `init`
kept their descriptions. Read an observed listing rather than reasoning about which entries
qualify.]

[PITFALL: **priority is decayed usage, not the invocation count.** Recency dominates at a 7-day
half-life — thirty uses two months ago scores 3, below four uses yesterday — and the 0.1 floor is
the only thing keeping a long-unused favourite ahead of a never-used skill. A ranking built from raw
transcript counts puts the wrong skills at the top of the at-risk table.]

**The levers**, all Claude-Code-specific: `skillListingBudgetFraction` and
`skillListingMaxDescChars` raise the two caps; `disableBundledSkills` (or
`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS`) removes the exempt entries taking the top off the budget; and
`skillOverrides` takes four values per skill — `on`, `name-only` (listed without its description, to
free budget for the rest), `user-invocable-only` (still typable as `/name`, hidden from the model)
and `off`.

**How to read the real number by hand.** The warning only exists on overflow and only reaches the
debug file — a plain `--debug` prints nothing:

```shell
SLASH_COMMAND_TOOL_CHAR_BUDGET=1 claude -p ok --debug-file /tmp/probe.log
rg 'over budget' /tmp/probe.log
# Skill listing over budget: N skills, C chars > 1 budget
```

[PITFALL: **a headless run lists fewer entries than an interactive one** — 42 bundled skills loaded,
25 listed, the difference being skills conditional on a capability or flag a `-p` run lacks. So a
headless measurement is a floor: 15,486 chars over 25 entries against an interactive 18,109 over 30.
A budget setting sized to just clear the headless number does not fit.]

[DECISION: **a live probe doing this automatically was built and removed the same day.** It worked,
and it was worse than reading a recorded listing on three counts at once: it was the only part of
`fitness.py` that spent tokens; it under-reported by ~2,600 characters for the reason above; and
each run entered the transcript store as a truncated listing, so the tool contaminated the corpus it
reads. Do not reintroduce it.]

## Reading listings the harness actually sent

The transcript store keeps every `skill_listing` attachment verbatim — rendered text, entry count
and names — so the listing the harness really sent is readable, free and retrospective. A demoted
entry is visible as a bare `- name`.

**This outranks every model of the budget, including this tool's own**, and it immediately corrected
two things stated as settled: the exempt set above, and the interactive listing size.

Measured 2026-08-31: 1,086 listings recorded, of which **541 came from `trigger.py`'s own scratch
directories**. Truncation had occurred in real work exactly **twice**, both `agent-*` sessions on
2026-08-22 under CLI 2.1.237; the other nine truncated listings were probes and pipeline runs.

[PITFALL: **this tool measuring itself is the dominant signal in the raw counts**, and it is the
third form that problem has taken — after a synthetic probe skill appearing in the usage counts, and
a `zorbnak-ledger` entry landing in the harness's own `skillUsage` map. Listings from a temporary
working directory are counted separately rather than dropped, because that bucket also holds real
headless pipeline runs.]

[PITFALL: **"unavailable" and "zero" are different findings, and stating that as a design property
did not make it true.** Run under a fake `HOME`, the report printed thirteen skills at zero
invocations with `never` last-seen and forecast which two would lose their descriptions — all from
no data, in a tool whose headline rule is that a zero is not a verdict. `Usage.available` now
carries it and a test pins it, because the failure is invisible on the one machine that has the
data.]

## Two invocation mechanisms, and why neither is the rate

An explicit `/skill-name` invocation **does not necessarily produce a `Skill` tool call** — the
harness can inject the skill body directly as a command message instead. Measured across the store:

| skill              | `Skill` tool calls | `<command-name>` markers |
| ------------------ | ------------------ | ------------------------ |
| `plan-docs`        | 70                 | 15                       |
| `session-harvest`  | 13                 | **87**                   |
| `research-library` | 12                 | 0                        |

Opposite stories, and either column read alone gives the wrong one. The `Skill` counter
under-reports total usage and over-reports the auto-trigger share for any skill a person mostly
types by hand.

[PITFALL: **a high explicit count is a hypothesis, not a diagnosis.** "The person keeps having to
ask for it by name" is the obvious reading, and it was tested on the corpus's one inverted skill
with a suite built as a controlled comparison — the description's own trigger phrasings as control,
the same needs in a person's words as the test, two lifted from real transcripts. **10/10**,
controls and paraphrases alike. The description opens "Use when invoked explicitly as `/name`" and
every auto-trigger phrasing it lists works; the split was the skill behaving as designed plus a
habit.]

## The absorption miner's design, with the numbers

1,067 `python -c` payloads extracted, 1,039 parseable, across 112 sessions.

[DECISION: **cluster on the import set first**, not on AST shape or edit distance. The shell string
is useless as a signature — every call normalises to `python3 -c S` because the payload is quoted —
so clustering must run on the parsed payload. Exact AST shape gave 681 distinct shapes, mostly
singletons; the import set gave human-legible clusters on the first run. AST shape stays as a second
pass _within_ an import cluster, for deciding whether several calls are really the same operation.]

[DECISION: **mine `.py` payloads, not `.py` files.** 3,268 `Write`/`Edit` calls touched `.py` paths
but 3,195 were inside a repo — real source, not throwaway — and only 66 went to a scratchpad. The
throwaway script mostly never becomes a file, which is why a file-based detector would have found
almost nothing.]

The archetypal finding, and the one that proves the concept: **seven ad-hoc readers of the
transcript store across six sessions**, hand-rolling in a one-liner what `session-bash-audit`
already ships as `scripts/audit.py`. Two more of the same shape:
`import copier; print(copier.__file__)` (15 calls, 11 sessions, 6 projects — a "where is this
installed" probe with no home), and a `tomllib` validation one-liner for a setup file (19 calls, 7
sessions) that belongs in that repo's task runner.

## Harness facts to re-check after a CLI upgrade

Everything below was true on **CLI 2.1.251, 2026-08-31**, and none of it is documented behaviour.

- **`claude -p` does trigger skills.** A GitHub issue reports the opposite on 2.1.80 — a
  description-optimisation loop scoring 0% recall because `-p` never consults the skill registry,
  closed as not planned. Probed directly: a synthetic command whose description covered an invented
  domain, one `claude -p` query in a scratch project, and the stream carried
  `"name":"Skill","input":{"skill":"<the synthetic name>",...}`. **This is the assumption the whole
  cold-trigger half rests on** — re-probe before trusting it after an upgrade.
- The listing arithmetic and its constants, above.
- `skill_listing` attachments are recorded in the transcript store; older CLI versions may not.
- `~/.claude.json` holds the `skillUsage` map that decides listing priority.
- `~/.claude/settings.json` is **merged, not generated wholesale**, by this machine's setup repo — a
  hand-added top-level key survives a deploy, though it does not reach the next machine.
