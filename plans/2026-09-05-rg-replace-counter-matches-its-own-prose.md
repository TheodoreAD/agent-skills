---
status: landed
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: 156d723c-4e21-41ef-aac9-bfd6c05b681c.jsonl
source_moment: 2026-09-05T03:05:00+03:00
---

# The tool-name counters match their own prose, and inflate when someone works on the audit

## Context

`session-bash-audit`'s `rg-replace` pattern is

```python
_rx(r"\brg\b[^|;&\n]*?\s-[A-Za-z]*r[A-Za-z]*(?=[\s=])|\brg\b[^|;&\n]*?\s--replace\b")
```

`\brg\b` matches anywhere in the command string, including inside a quoted `-m` message. In the
seven days to 2026-09-05 it tagged **39** calls, of which **3 were not `rg` invocations at all**:
two `git commit -m` messages whose bodies quote the trap, and one `plans.py commit -m` naming the
plan file `2026-09-02-rg-replace-flag-used-twice-in-one-session.md`. All three come from sessions
writing _about_ the anti-pattern.

The over-report is ~8% and one-directional. It matters more than that figure suggests because of
what it is: **the corpus that documents an anti-pattern inflates its own count of it**, so the
number rises exactly when someone is working on the problem, which is exactly when the number is
being read. Every other counter here has the same exposure — `sed-n`, `find-not-fd`, `heredoc` — but
this one is the only pattern whose whole subject is a string agents type into prose.

The 32 real calls this leaves are still a genuine machine-wide rate (21 sessions, 4 repos, 1.2% of
`rg` invocations); the finding is about the instrument, not the conclusion.

**Second instance, found the same day in `find-not-fd`, and it is worse.** That row tagged 41 calls
of which **4 were not `find` invocations**: one commit message, and **three of the form
`audit.py --days 30 --samples 0 | rg 'find-not-fd|grep-r-not-rg|find-exempt|…'`** — a session
grepping the audit's own output for these row names, counted as a violation of the rule the row
measures. So this is not one pattern's regex; it is the shape of every counter keyed on a bare tool
name, and the bias has a direction: **the counts rise exactly when someone is working on the audit,
writing about the anti-pattern, or reading the report.** Two rows measured on the same corpus, both
~8–10% over, both entirely from prose.

A related miss in the other direction, same row: `find tests -name 'test_*.py' -printf '%f\n'` was
tagged `find-not-fd`, though `-printf` is exactly the find-only capability `find-exempt` exists to
recognise. So the exempt row undercounts while the violation row overcounts, and the ratio between
them — which is the number a reader actually uses — is wrong twice over.

## Evidence

- Corpus: `audit.py --days 7`, 13,754 Bash calls, 2026-09-05. 39 tagged, 32 real.
- The three false positives, identified by re-matching each tagged command with an anchored variant
  that requires `rg` to start a command segment:
  `(?:^|[|;&\n]|&&)\s*(?:cd [^&;|]+&&\s*)?rg\s+(-[A-Za-z]*r[A-Za-z]*)(?=[\s=])`.
- Bundle distribution of the 32 real ones, which the anchored match also makes readable: `-rn` × 27,
  `-ril` × 3, `-rln` × 1, `-rl` × 1 — and **zero** bare `-r`. That distribution is the actual
  finding the counter exists to produce, and it is only trustworthy once the mentions are excluded.
- Full write-up of what the flag does to each bundle: `power-user-linux-setup`
  `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`.

## Open questions

[DECISION: all of them, and the published figures restated — the middle option this plan costed,
chosen by the user 2026-09-05 over its own narrower recommendation. Every tool-name row now matches
against `strip_quoted`, and `rg-replace` is anchored at a segment boundary as its neighbours already
were. The argument that carried it is the one this plan makes against itself: two of the two rows
examined were affected, so the unexamined ones were more likely affected than not.]

[DECISION: `find-exempt` needed no precedence rule, because this was not a precedence problem. Both
rows key on the same flag list through opposite lookaheads, so they cannot both match — `-printf`
was simply missing from the list, which put every use of find's own formatter in the violation row
and none in the exempt row. Adding it to both lists is the whole fix, and it moves the ratio twice
as this plan predicted, in the right direction: `find-not-fd` 310 -> 297, `find-exempt` 16 -> 19.]

[DECISION: no special case for `cd <path> && rg …`. The neighbouring rows' boundary class already
contains `&&`, so the blessed cross-repo shape matches for free — the draft regex above carried a
`(?:cd [^&;|]+&&\s*)?` prefix that was redundant against its own boundary class. Nothing has to
re-implement `split_chain`, which was the cost this question was weighing.]

[DEFERRED: the per-bundle breakdown in the row's own reporting. `-rn` and `-ril` are different
failures and one count cannot say which is happening; the distribution is in this plan's evidence
(`-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1, and **zero** bare `-r`) but the script still does
not print it. Not done because the anchoring was what made the count trustworthy, and the breakdown
is worth building on a count worth reading.]

## What landed

`2536d38` (the patterns and their tests) and `d890c10` (the restated figures).

**The restatement is the half that needed measuring rather than deciding.** Old and new patterns
were run over one identical corpus — 29,389 calls in the 30 days to 2026-09-05 — so the only thing
that could move a count was the pattern change:

| row             | before | after | dropped                                      | gained |
| --------------- | -----: | ----: | -------------------------------------------- | -----: |
| `rg-replace`    |     84 |    81 | 10, every one prose                          |      7 |
| `find-not-fd`   |    310 |   297 | 8 prose, 2 now `find-exempt`, 3 in a wrapper |      0 |
| `find-exempt`   |     16 |    19 | —                                            |      3 |
| `grep-r-not-rg` |    397 |   396 | 1, in a wrapper                              |      0 |
| `grep/find`     |   8203 |  8179 | 9 prose, 15 in a wrapper                     |      0 |

**`rg-replace`'s seven gains were not predicted here and are the more interesting half.** The old
pattern scanned forward from `rg` with `[^|;&\n]*?`, so a `|` inside the search pattern stopped it
before it reached the flag: every `rg -n "a|b" -r '' path` — a real, deliberate `--replace` — was
invisible. The row's count therefore barely moved while a fifth of its contents changed, which is
worth keeping as a general caution: a count that holds steady across a fix is not evidence the fix
was unnecessary.

The tool-preference table in `references/research.md` was re-measured on the new patterns rather
than annotated, so `grep -r` reads 7% of its pair against the 10% first published and `find` 50%
against 53%. The earlier `\n`-separator entry's 242 -> 292 figures are deliberately **not**
restated: they record what one change did, not what the rows count today.

[PITFALL: **blanking quotes also hides a real invocation inside a `bash -c '…'` body**, and 19 of
the 24 dropped calls are that shape — mostly `docker run … bash -c '… find /root/.local/bin …'`.
Accepted rather than worked around, on two grounds: those calls already carry the `bash-c` tag, and
`~/AGENTS.md` exempts `find` "running somewhere `fd` is not installed — inside a container, say", so
counting them as misses was itself wrong. Recovering them means the pattern layer re-implementing
`split_chain`, which is exactly what the third decision above declined.]
