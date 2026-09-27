---
status: landed
updated: 2026-09-28
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

**Verified 2026-09-28, by running both versions on the session.** The pre-fix `audit.py` reports
`chain 5, chain5 2` for `a953b16f` (194 calls); the fixed one reports 0 and 0. So this was the whole
cause, of every chain hit the session had, not only the two samples. `strip_heredoc` runs first in
both readers, so the order needed no change.

## Open questions

[DECISION: **the POSIX escape rule in `split_chain`, plus an agreement test** (decided with the user
2026-09-28). Rebuilding `split_chain` on `QUOTED_RE` was the other option — one quote model, so no
second drift — and was not taken: it is a rewrite behind four rows for protection a test gives more
cheaply, and it would change behaviour on an unclosed quote, which today swallows the rest of the
command and would then split it. The test asserts that blanking quotes with `strip_quoted` never
changes `split_chain`'s segment count, which holds only while both readers put quote boundaries in
the same places.]

## Recommended direction

1. Add a failing test using the two samples above: each should count as one segment.
2. Make `split_chain` skip `\x` inside double quotes, or derive it from `QUOTED_RE`.
3. Re-run the audit on `a953b16f`. Expect `chain5` 2 → 0 if the unverified item holds.
4. Note the instrument change. A baseline saved before the fix straddles it, so any `--compare`
   across the fix must say that the `chain*` rows moved for this reason (see the harvest skill's
   straddle rule).

## Migrated to

- **The rule, the measurement and the rejected rebuild** — `split_chain`'s docstring in
  `skills/session-bash-audit/scripts/audit.py`, and the agreement test in `tests/unit/test_audit.py`
  (`bda4d44`).
- **The instrument change** — the commit message. Baselines already record the `audit.py` version
  that made them, and `session-harvest`'s straddle rule covers comparing across it, so no new text.
