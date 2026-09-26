---
status: idea
updated: 2026-09-18
source_repo: github.com-personal/power-user-linux-setup
source_session: 4296eac1-732f-4827-874f-59063bcf404f.jsonl
source_moment: 2026-09-18T19:28:57+03:00
source_plan:
---

# A grep over a transcript counts prose, not calls — and it agreed with the story being formed

## Context

A harvest was writing an adherence row into `power-user-linux-setup`'s sample corpus and needed a
cause for the session's `chain` rate of 46%, the second-worst the corpus holds and a 44-point
inversion against the previous row for the same repo.

The hypothesis was defensible: the harness had printed `Shell cwd was reset to …` **7 times**, and
the natural response to that is to prefix `cd <repo> && …` to every command, which scores as both
`chain` and `cd-own-repo`. To size it:

```shell
rg -o '"command":"cd /home/…/power-user-linux-setup' "$TRANSCRIPT" | wc -l
```

**166.** Against 185 Bash calls, that reads as "nearly every command opened with a `cd`" — a clean,
quantified cause, and it was one edit away from being written into the corpus as fact.

## Evidence

The number is wrong by an order of magnitude. Counting **unique `tool_use` ids** whose `Bash` input
actually starts with `cd`:

| method                                   | calls opening with `cd` | into the session's own repo |
| ---------------------------------------- | ----------------------: | --------------------------: |
| `rg -o '"command":"cd …'` over the JSONL |                       — |                     **166** |
| deduped by `tool_use` id                 |                  **15** |                       **5** |

`audit.py` independently reported `cd-own-repo` at **7**, which is the neighbourhood of 5, not of
166 — and that disagreement was visible on screen for several calls before anyone read it as a
disagreement.

Three things a line-oriented grep over a transcript counts that are not calls:

- the command echoed back inside the **tool result**, not only in the tool call;
- the command quoted in the session's **own assistant messages**, which for a session discussing
  commands is constant;
- every occurrence inside **skill bodies loaded into context** — and this corpus's own skills quote
  `cd <repo> && …` as the sanctioned cross-repo shape, so a session that loaded them counts itself.

The real driver turned out to be unrelated: 21 of the 85 chains were
`git add … && git status
--short` pairs, a read-back the session did before nearly every commit.

## Open questions

[NEEDS CLARIFICATION: is this a `SKILL.md` line or a subcommand? The skills already own the correct
technique — `turns`, `claims` and `audit.py` all resolve by `tool_use` id, and `audit.py` dedupes
replayed calls deliberately. What is missing is the instruction not to reach past them for an ad-hoc
count when the question is one they do not already answer, which is exactly when the temptation
arrives.]

[NEEDS CLARIFICATION: does this belong to `session-harvest`, to `session-bash-audit`, or to both?
The harvest is where the number was being written into a durable file, which is the cost; the audit
is where the correct counting lives and where a "count this predicate for me" subcommand would go.]

## Recommended direction

One line, wherever it lands: **a count taken off a transcript with a line-oriented grep is an upper
bound on a different question.** Resolve by `tool_use` id or use the instrument.

And a generalisation of a rule `session-harvest` already carries one case of. Its existing wording
is about zeros — "a zero that agrees with what you hoped is the one to check". This was a **non-zero
that agreed with the causal story being formed**, which has the same structure and none of the
existing wording's triggers: the number was large, specific, and confirmed a hypothesis that had
independent support (the 7 cwd resets were real). The tell was not the number but that **a second
instrument disagreed with it and the disagreement went unread**.

[PITFALL: **the correction cost two calls and the wrong version would have cost nothing visible.**
The corpus is exactly the kind of durable file nobody re-derives a number out of, and the sample
would have carried a confident causal claim about cwd resets — plausible, mechanical, and traceable
to a real observation — for as long as anyone cared to read it.]
