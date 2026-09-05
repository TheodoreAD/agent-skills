---
status: idea
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

[NEEDS CLARIFICATION: whether to anchor this one pattern or all of them. The second instance argues
for all — two of the two tool-name rows examined were affected, so the untested ones are more likely
affected than not. Against it: anchoring everything changes counts already published in
`references/research.md` and in several `power-user-linux-setup` plans, so old and new figures stop
being comparable, which is the thing baselines exist to prevent. A middle option worth costing:
anchor everything, and re-run the old windows once with the new code to restate the published
figures rather than leaving two scales in circulation.]

[NEEDS CLARIFICATION: whether `find-exempt` should win over `find-not-fd` when both could match. It
currently does not — a `-printf` call was tagged only as a violation — and the two rows are read as
a ratio, so a call landing in the wrong one moves the number twice.]

[NEEDS CLARIFICATION: whether the anchored regex should also tolerate the `cd <path> && rg …` form.
The draft above does, because that shape is explicitly blessed for a cross-repo read and did occur
in the corpus. It is the only chain prefix worth special-casing; anything more general starts
re-implementing `split_chain`, which the script already has and which the pattern layer deliberately
does not use.]

## Recommended direction

Anchor `rg-replace` at a command-segment boundary, note in `references/research.md` that counts
before 2026-09-05 include prose mentions, and leave the other patterns alone until someone has a
reason. Add the bundle breakdown to the row's own reporting if that is cheap — `-rn` versus `-ril`
are different failures (see the linked plan) and one count cannot say which is happening.
