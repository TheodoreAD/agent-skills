---
status: idea
updated: 2026-09-27
---

# Audit split chain ignores escaped quotes

## Context

`session-bash-audit`'s `split_chain` (`skills/session-bash-audit/scripts/audit.py:187`) tracks
quotes by character: inside a quote, the next identical quote character closes it. It does not skip
a backslash escape. `QUOTED_RE` at line 176, which `strip_quoted` uses, does handle `\\.`. So the
two disagree on any double-quoted argument containing `\"`.

The effect: after a `\"` inside a double-quoted `rg` pattern, `split_chain` believes the quote has
closed. Every `|` alternation after that point is then read as a pipe, and the call is tagged
`chain5`.

Found by a harvest on 2026-09-27, session `a953b16f-c02c-45d9-99e8-21a7277c781d`. Both of its
`chain5` samples were single `rg` calls with no pipe at all:

- `rg -n "help:\"|gcloud|services enable|Remove|os\.Remove|Stdin|\"-\"" <files>`
- `rg -o --no-filename -N "['\"](gmail|calendar|tasks|…)\.[a-zA-Z]+['\"]" <dir> --glob …`

[UNVERIFIED: that this is the whole cause of those two hits, and whether the session's 4 `chain`
hits share it. Confirmed by reading the code, not by running `split_chain` on the samples. The first
step is a test with these two commands as input.]

## Open questions

[NEEDS CLARIFICATION: fix `split_chain` to honour `\` inside double quotes, which is the POSIX rule;
single quotes have no escapes. Or rebuild it on `strip_quoted` so there is a single quote model. One
model is the durable answer, since the two have already diverged once. Check `strip_heredoc`'s order
too.]

## Recommended direction

1. Add a failing test using the two samples above: each should count as one segment.
2. Make `split_chain` skip `\x` inside double quotes, or derive it from `QUOTED_RE`.
3. Re-run the audit on `a953b16f`. Expect `chain5` 2 → 0 if the unverified item holds.
4. Note the instrument change. A baseline saved before the fix straddles it, so any `--compare`
   across the fix must say that the `chain*` rows moved for this reason (see the harvest skill's
   straddle rule).
