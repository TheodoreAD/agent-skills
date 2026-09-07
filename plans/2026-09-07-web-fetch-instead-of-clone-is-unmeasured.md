---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/power-user-linux-setup
source_session: 9164dacd-2813-4087-a593-14dc24c44782.jsonl
source_moment: 2026-09-07T19:05:00+03:00
---

# Fetching the web instead of cloning is a 116:1 habit that no instrument counts

## Context

The user stopped a research task mid-run on 2026-09-07: _"we need a clear rule to clone all these
things instead of curling files, what is that all about? we have research library and we need to
start measuring this nonsense, it's a clear failure. we want grep locally, not reading the internet
all the time for bits and pieces. your capabilities are far better on full clones anyway."_

The rule half landed in `power-user-linux-setup` the same day — a new `~/AGENTS.md` rule, "About to
fetch a page or file to learn how something works", with its evidence in
`contributing/global-agents-md.md`. **The two halves that belong to this repo are the instrument and
the skill's own trigger**, and neither is done.

## The measurement, taken 2026-09-07

Counted from the transcript store over 30 days — `WebFetch`/`WebSearch` `tool_use` blocks against
tool calls that add a `research-library` entry:

| counter                         | 30 days |
| ------------------------------- | ------: |
| `WebSearch`                     |     619 |
| `WebFetch`                      |     426 |
| library entries **added**       |   **9** |
| library entries **read**        |     485 |
| sessions fetching from the web  |      89 |
| sessions adding a library entry |       6 |

**116 web calls per entry added.** The 485 reads are the important row: the library is used freely
once material is in it, so this is not reluctance to grep and not a problem with the store. **The
failure is at acquisition only** — a session needing material it does not have reaches for a page,
and the next session needing the same material pays again. The heaviest fetcher in the window made
78 web calls and touched the library zero times.

[PITFALL: **that ratio was measured mid-session and is already 3.4x out of date — and the reason it
moved is the finding, not an error.** Re-derived at the same 30-day window five hours later: **1,047
web calls against 31 adds, a ratio of 34:1**, from 10 adding sessions rather than 6. Web calls moved
by two; every bit of the change is adds. The session that filed this plan then spent its remaining
hours cloning — the rule it had just written taking effect inside its own measurement window.

Two things follow, and the second is the one that matters for whatever instrument gets built:

- **116:1 is the pre-rule baseline and 34:1 is not a correction of it.** They are the same window
  measured before and after one session changed its behaviour. Quote 116:1 as what the habit looked
  like unaddressed; quote 34:1 as what one compliant session does to a 30-day corpus.
- **A 30-day window that one session can move by 3.4x is not a stable denominator.** Twenty-two adds
  from a single session swamped a month of everyone else's. Whatever row lands in `audit.py` should
  report per-session counts, not a corpus ratio, or it will read as a trend when it is one
  afternoon.]

[PITFALL: **the first cut of this measurement said 456 adds and a 2:1 ratio — a comfortable
non-finding — because the add-marker matched any tool input naming a path under the library.** Every
`rg` over an existing clone counted as an acquisition. The store holds ~50 entries, so "456 adds in
a month" was refuted by `ls`, which is the sanity check a rate has to survive before being quoted.
Separating add from read is the whole finding. Whatever lands in `audit.py` needs the same split and
the same check, or it will report health.]

## What is missing here

### 1. No instrument counts it

`session-bash-audit`'s `audit.py` classifies **Bash commands**. This is a tool-choice pattern living
in `WebFetch`/`WebSearch` `tool_use` blocks, which no row can see. The skill already says it is "the
place to record a newly noticed Bash anti-pattern so the next audit measures it" — this is the first
noticed anti-pattern that is not a Bash one, so the question is whether the instrument's scope
widens or a sibling row set appears.

A working prototype exists (~60 lines, stdlib, read-only) and the counters it needs are:

- `WebFetch` and `WebSearch` counts per session
- library **adds** — a `library.py add`/`provenance` call, or a `git clone` whose destination is
  under `$RESEARCH_HOME`
- library **reads** — any tool input naming a path under `$RESEARCH_HOME`, counted separately and
  never merged into adds

[NEEDS CLARIFICATION: **is the honest row a rate, and over what denominator?** Bash rows are a share
of Bash calls. This one has no natural denominator — a session doing no research should score
nothing rather than 0%, and a session with one legitimate vendor-docs fetch should not read as a
miss. A count with a companion (`n web calls, of which m had a repo behind them`) is the shape the
`exit-masked` gate/listing split settled on, and it may be right here too — but "had a repo behind
it" is not derivable from a transcript the way "wrapped a gate" was.]

[NEEDS CLARIFICATION: **can the instrument tell a legitimate fetch from a lazy one at all?** A
closed vendor's docs and a registry's metadata are both correct fetches. If it cannot, the row
measures a hazard rather than a defect — the same conclusion `exit-masked` reached, and it should be
stated the same way rather than scored.]

### 2. `research-library`'s description triggers one moment too late

`skill-fitness usage`, 2026-09-07: **14 auto-invocations across 1,188 transcripts, 0 explicit**,
most recent that morning. So the skill is not dead — it fires when a session frames the task as
working on the library. Its description opens on "working with, adding to, or updating the shared
cross-project research library", and the phrase that would have caught this session is buried mid-
sentence: "before fetching the same material from the web".

A request framed as _"do some deep research on community practices"_ matches none of that. The
decision to fetch has already been made by the time anything in the description could apply.

[NEEDS CLARIFICATION: **should the description claim the research-framed request outright** — "use
when about to research how a tool, library or spec works, before fetching anything from the web" —
or does that steal triggers from other skills? `trigger.py` can score it: write the cases in the
words a request actually uses ("research X", "how does Y handle Z", "find out what the community
does about W") and measure, rather than rewording by taste. Note the rule now lives in `~/AGENTS.md`
too, so the skill no longer has to carry the whole burden — it may be that the description should
stay narrow and the always-loaded rule does the catching.]

### 3. Delegated research is a second surface, and it is where this failure happened

`~/AGENTS.md` does not reach subagents. The session that prompted this dispatched three research
subagents whose prompts explicitly said "find from PRIMARY documentation", named doc pages, and told
one to read registry JSON — page-at-a-time retrieval, prescribed by the prompt. The subagents
complied correctly.

Five of the sources those prompts sent agents to the web for were **already cloned** in
`$RESEARCH_HOME`: `python--cpython`, `openai--codex`, `google-gemini--gemini-cli`, `cline--cline`,
`anthropics--skills`.

So a research prompt has to carry the clone instruction the way it already carries the Bash rules.
That clause landed in `~/AGENTS.md`'s "Which sessions load this file". What is open here is whether
anything can **check** it — a lint over a session's own `Agent` tool calls asking whether a research
prompt named `$RESEARCH_HOME`, which is the kind of thing `fitness.py derivable` already does for
`SKILL.md` bodies.

## Evidence

Session `9164dacd-2813-4087-a593-14dc24c44782.jsonl` in `power-user-linux-setup`, 2026-09-07 from
roughly 18:30+03:00. Distinctive phrase: _"Three of the sources I sent agents to fetch are already
cloned locally"_.

The rule and its full evidence write-up (measurement table, the over-counting pitfall, the live
failure) are in that repo's `contributing/global-agents-md.md` under "About to fetch a page or file
to learn how something works". This plan deliberately does not copy the rationale — it records what
`agent-skills` owns and has to decide.

## Recommended direction

Take the instrument first and the description second. The instrument is the thing the user asked for
("start measuring this"), it needs no wording judgement, and a measured baseline is what would make
a description change checkable instead of a matter of taste. Expect the row to end up reported and
unscored, for the reason `exit-masked` is.
