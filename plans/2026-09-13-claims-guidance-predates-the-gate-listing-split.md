---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/power-user-linux-setup
source_session: feea009a-eef1-4312-9967-186504d96db7.jsonl
source_moment: 2026-09-13T17:06:41+03:00
source_plan:
---

## Context

`harvest.py claims` ends with a guidance block telling the reader what to do about masked exit
codes. It opens **"Ask the shell first: `setopt | rg pipefail`"**. `SKILL.md` says the opposite
ordering, and says it explicitly:

> **Read the gate/listing split before reasoning about any of this.** … **when `m` is zero the
> greens were never at risk**, whatever the shell does … That is a shorter and stronger answer than
> the pipefail check below, it needs no extra command

So the script's own printed advice is one revision behind the body it belongs to. A reader who
follows the output runs a command the body says is unnecessary; a reader who follows the body does
not. Neither is harmed, which is why this has survived — the `setopt` call is cheap and its answer
is usually the same.

## Evidence

Harvest of session `feea009a-…`, 2026-09-13. `claims` reported:

```
# 1 of 150 Bash calls masked their exit code behind a filter
# 4 message(s) told the user a gate or suite was green
    masked: python3 …/audit.py --days 7 --samples 0 --json … 2>&1 | tail -5
```

The one masked call is an audit dump, not a gate, and `audit.py` independently printed
`exit-masked 1 1% 0 wrapped a gate, 1 a listing`. So `m = 0` and the four green claims were never at
risk — the body's cheap exit, reached without running `setopt` at all. The run followed `SKILL.md`
and ignored the block the script printed underneath, which is the tell.

## Open questions

[NEEDS CLARIFICATION: can `claims` compute the split itself, or should it only point at it? It
matches raw commands and `audit.py` strips quoted spans and heredoc bodies, and `SKILL.md` already
warns the two counts differ by design and must not be read as each other's check. Duplicating
`GATE_RE` into `claims` would create a third number over the same population. Pointing at
`audit.py`'s line costs nothing and keeps one owner for the classification.]

[NEEDS CLARIFICATION: the same block's `setopt` advice is still correct and still needed when `m` is
above zero, so this is a reordering rather than a deletion — but the block is printed
unconditionally, before the reader knows which branch they are on. Whether it should be conditional
on anything `claims` can see is the open part.]

## Recommended direction

Reorder the printed block to match the body: name the gate/listing split as the first check and say
it comes from `audit.py`'s `exit-masked` line, then keep the `setopt` paragraph as the branch for
when a masked call did wrap a gate. No new computation, one block of text.

Worth doing because the block is the part a reader actually sees — `SKILL.md`'s ordering only
reaches a run that consults the body at that moment, and the whole reason the guidance is printed is
that many do not.
