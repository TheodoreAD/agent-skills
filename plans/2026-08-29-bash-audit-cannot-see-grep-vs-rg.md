---
status: idea
updated: 2026-08-29
---

## Context

Filed from a `power-user-linux-setup` session. Not written into this repo's tree because the session
did not own it.

`~/AGENTS.md`'s "Viewing, searching, or editing files" rule ends with a tool-preference clause: `rg`
over `grep -r`, `fd` over `find`, with plain `grep`/`find` still fine for non-recursive lookups,
`find -exec`/`-delete`, and portability. The user's standing impression is that agents ignore it.

`session-bash-audit` is the skill that exists to answer exactly that kind of question with evidence
rather than impression. It cannot answer this one. Its `PATTERNS` table has a single row covering
all four tools:

```python
"grep/find": (_rx(r"(?:^|&&|;|\|)\s*(grep|rg|find|fd)\b"), "search via Bash; Grep/Glob have their own gate"),
```

That row measures a different rule — "prefer the Grep/Glob tools over shelling out at all" — and it
fires identically whether the session complied with the tool-preference clause or violated it. The
`rg-replace` row is the only tool-specific one, and it catches a separate trap (`rg -r` meaning
`--replace`). So the audit is blind to the distinction by construction, and the impression it was
built to test has never been measured.

Measured by hand for this plan, 2026-08-29, over **15,171 Bash calls in 415 transcripts** under
`~/.claude/projects/`:

| shape                                             | calls | share of that pair |
| ------------------------------------------------- | ----- | ------------------ |
| `rg`                                              | 2356  | —                  |
| `grep -r` / `grep -R`                             | 213   | **8%**             |
| `fd`                                              | 231   | —                  |
| `find`, plain lookup                              | 175   | **43%**            |
| `find` with `-exec`/`-delete`/`-mtime`/… (exempt) | 62    | —                  |

So the impression is half right, and the halves point opposite ways. `rg` adherence is good — 92% of
recursive text searches already use it, and a rule holding at 92% is not the one to spend effort on.
`fd` adherence is bad: 175 of 406 file-finding calls use `find` for a plain lookup, and the samples
are textbook `fd` cases —

```
find . -name '*.py' -not -path './.venv/*' -not -path './.git/*' | sort
find . -iname "*plan*" -not -path "./.git/*"
find . -path ./.venv -prune -o -name '*.py' -print | sort
```

— each of which is `fd -e py` or `fd plan`, gitignore-aware for free, with the `.venv`/`.git`
exclusions the author wrote by hand supplied by the tool.

This is a gap in the audit first and a rule-wording problem second. Both halves matter, but only the
audit half belongs to this repo: the rule text and the permission allowlist live in
`power-user-linux-setup`, tracked separately there.

## Open questions

[NEEDS CLARIFICATION: one row per tool pair, or one row with a captured group? Two rows —
`grep-r-not-rg`, `find-not-fd` — read better in the per-pattern output and let the routing table
give each its own destination, which they need, since the two now have opposite verdicts. A single
`wrong-search-tool` row is cheaper but re-creates the aggregation that caused the blindness.]

[NEEDS CLARIFICATION: how should the exempt `find` forms be encoded? The hand-measurement used a
negative lookahead for `-exec|-delete|-print0|-newer|-mtime|-size|-perm|-user`, which is a judgement
call baked into a regex, and `PATTERNS` rows are supposed to carry a one-line "why" rather than a
policy. Alternative: count all `find` and report the exempt share as a second row, leaving the
judgement in the reader's hands. That is more honest and slightly noisier.]

[NEEDS CLARIFICATION: is the `grep/find` row worth keeping once the two new rows exist? It answers a
real and different question (shelling out instead of using Grep/Glob), so probably yes — but three
overlapping rows over the same commands need their "why" lines rewritten together, or the next
reader will conflate them exactly as this plan's author initially did.]

## Recommended direction

Rough.

1. **Two new rows**, plus a `DIRECTION` entry for each, so a later run reports whether the number
   moved. `find-not-fd` should be `down`; `grep-r-not-rg` is already low enough that the useful
   direction is "not up".
2. **Re-word the three overlapping rows' "why" lines in one pass**, so the table says plainly that
   one row is about the harness tool and two are about which CLI.
3. **Record the 2026-08-29 numbers as the baseline** in `references/research.md`, with the method,
   so the next run is a comparison rather than a fresh measurement. That file already says it is
   evidence and is deliberately machine-specific; this belongs there.
4. **Do not fix the rule wording from this repo.** The clause is one sentence inside a
   `power-user-linux-setup` fragment, and the allowlist that could price `find` is that repo's too.
   This repo supplies the measurement; that one decides what to do about it.

[DEFERRED: the general lesson — an audit pattern that aggregates a compliant and a non-compliant
form under one tag reports a rate that answers neither question. Worth a sentence in the skill about
adding a row, since the same shape will recur the next time a rule distinguishes two spellings of
the same command.]
