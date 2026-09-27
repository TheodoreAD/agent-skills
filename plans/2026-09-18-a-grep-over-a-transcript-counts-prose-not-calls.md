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

### Second occurrence, 2026-09-27, with a fourth contamination source

An `agent-skills` harvest reached for the same count on the same hypothesis nine days later, session
`21615ec2-5eca-4393-a831-d24275fb2551`:

```shell
rg -c 'cd /home/tdumitrescu/projects/github.com-personal/agent-skills &&' "$TRANSCRIPT"
```

**135**, against 171 Bash calls, read as "two-thirds of this session's calls opened with a `cd` into
its own repo" — and `audit.py` reported `cd-own-repo` at **1**. Deduped by `tool_use` id: exactly
**1** call opened that way, 8 of 171 contained `&&` at all, and 4 contained `cd` anywhere. The grep
was wrong by two orders of magnitude.

**The fourth source, which the three above do not cover:** the matching entries were `assistant`
records carrying a `serverClassifierRequest` field, a per-entry metadata payload that embeds prior
context. The first matched line's own `tool_use` command was
`rg -l -i 'renam' --hidden --glob '!.git' .` — no `cd` in it anywhere. This source is worse than the
listed three because it needs no help from the session: a session that never quotes a command and
loads no skill body still accumulates these, so the inflation is a property of the transcript format
rather than of the conversation's subject.

**And this is the first recorded case where the disagreement was read rather than missed**, which is
the rule below working as written. The audit's `1` was on screen beside the grep's `135`; the run
checked the low count instead of reporting a detector bug, traced it to `slug_matches` and
`load_session`, then dumped `--json` and counted tags. Four calls, and the alternative was a filed
plan against `session-bash-audit` alleging a pattern gap that does not exist. Worth noting what
triggered the check: **the existing wording about a suspicious zero generalised to a suspicious
_one_** — a count far lower than the session remembered, on a row it had specific reason to expect a
hit on.

## Open questions

[DECISION (2026-09-28): **a `SKILL.md` line, in `session-harvest` only.** The instruments that count
correctly already exist, so a subcommand would duplicate them; what was missing was the instruction
not to reach past them. It sits beside the existing "a zero that agrees with what you hoped" and "a
count lower than you remember" rules as their third case — a count _higher_ than the instrument's —
because the harvest is where the number becomes a durable file, which is the cost. Both occurrences
and all four contamination sources are in it.]

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
