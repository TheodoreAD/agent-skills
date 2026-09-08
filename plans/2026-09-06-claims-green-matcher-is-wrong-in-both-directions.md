---
status: idea
updated: 2026-09-06
---

# `claims`' green-claim matcher is wrong in both directions

Merged 2026-09-06 from two plans written the same day about the same regex from opposite ends:
`2026-09-06-claims-matcher-has-no-term-for-ci.md` (the under-count) and
`2026-09-06-claims-matcher-counts-sentences-that-deny-a-gate-ran.md` (the over-count), the latter
filed from a `repo-tasks` session — transcript `a3c12c26-55b9-4ed1-941f-42898b4bf565.jsonl`, moment
`2026-09-06T00:05:00Z`, where editing this plan directly was out.

Merged again 2026-09-08 from `2026-09-08-claims-counts-prose-about-exit-codes.md`, filed from a
`power-user-linux-setup` session, which measured a **second over-count shape** on a different
session and asked to be merged rather than kept apart. The file was renamed then, from
`2026-09-06-claims-matcher-misses-ci-and-counts-denials.md`, because three shapes no longer fit a
title naming two. All four names are what `archive --search` needs.

## Context

`harvest.py claims` reports two numbers together: how many Bash calls masked their exit code behind
a filter, and how many messages told the user a gate or suite was green. The pairing is the point —
a green claim resting on a masked exit is the inaccuracy the check exists to surface. Two harvests
on 2026-09-06 measured the second number, and it was wrong in both directions.

### It counts no green claim about CI, which is the one the sweep asks you to make

Found by a harvest running step 5 on itself. `harvest.py claims` reported:

```
# 0 of 201 Bash calls masked their exit code behind a filter
# 0 message(s) told the user a gate or suite was green
```

The first number is right and makes the run benign. **The second is wrong.** The same session had
told the user CI was green six times, including:

- "Both CI legs green (CI 23s, Windows 1m42s)."
- "Done — batch 3 retired, pushed, both CI legs green."
- "Final state: working tree clean, `main` level with `origin`, both CI legs green on every push."

**This run is the benign instance, and that is why it is worth recording.** `exit_masked` was 0, so
no claim rested on filtered evidence and nothing was actually mis-reported. The failure needs both
halves — masked exits **and** CI-phrased claims — and on that session the count would silently
under-report the live inaccuracy the check exists to surface.

### And it counts three sentences that say a gate was never run

`harvest.py claims --until 2026-09-06T03:00:01+03:00`, session
`a3c12c26-55b9-4ed1-941f-42898b4bf565`, reported:

```
# 27 of 286 Bash calls masked their exit code behind a filter
# 3 message(s) told the user a gate or suite was green
    The headline: no test anywhere runs the gate on a clean machine. …
    ## 3. Nothing runs the gate on a clean machine
    **3. Nothing ran the gate on a clean machine.** New `test_clean_os_gate_integration.py`: …
```

All three are the session's own finding that **no test ran the gate on a clean machine** — the
opposite of a green claim. Meanwhile the session did assert green repeatedly ("Gate green, unpiped,
exit 0", "All green, tree clean", "CI green on all six jobs including macOS"), and none of those was
counted.

So on one session the matcher scored **three false positives and every true positive missed** — and
the count that reaches the report is indistinguishable from a correct one. That is the merged
finding neither half had on its own: this is not a pattern that is broad in one direction and narrow
in another, it is a pattern matching on subject-word proximity with no notion of who the sentence is
about or whether it affirms anything.

### And it counts prose _about_ an exit code, on a session that ran no gate claim near it

Measured 2026-09-08 on session `2f0fa965-60a4-4478-bcba-5097aff65801` (`power-user-linux-setup`, 212
Bash calls), harvested at boundary `2026-09-08T12:05:54+03:00`. `claims` reported **6 messages
telling the user a gate or suite was green**, and read against the transcript **3 of the 6 are not
about a gate at all**:

| counted text (truncated)                                                       | what it actually is           |
| ------------------------------------------------------------------------------ | ----------------------------- |
| "Non-editable fails _silently_ — exit 0, found nothing."                       | describing a probe's result   |
| "The plain install _succeeds_, exits 0, and silently finds nothing."           | the same probe, in the report |
| "**Verified end to end** … both shims report a version, the listing excludes…" | a manual verification         |

The other three are ordinary and correctly matched ("Gate green, 9 new tests pass", "Gate green. Now
proving the install actually works", "Gate re-run after the install is green — 671 tests"). A 50%
false-positive rate, and every false positive from one cause: **the session's subject was a probe
whose whole finding was that a command exits 0 and does nothing useful**, so it wrote "exit 0" and
"succeeds" repeatedly, in prose, about something that was never a gate.

**It is a distinct shape from the denials above, and the filing's account of why was wrong in a way
that strengthens its own argument.** The filing said both shapes land on the same first alternation.
Checked against the live pattern 2026-09-08, they do not: the denials hit the first
(`gate on a clean`), and the two exit-code sentences hit the **fourth**,
`\b(0 errors|exits? 0|exit
code 0)\b`, matching on `exit 0` and `exits 0` with no subject term
anywhere in the alternation. So this is not a second symptom of one over-broad rule — it is the one
alternation that anchors on no subject at all, and a negation fix aimed at the first cannot reach
it. Neither sentence negates anything, and "exits 0" is exactly the phrase a true positive would
use.

The third row could not be reproduced: the counted text is truncated in the filing, and the visible
part matches nothing in the pattern. Whatever matched is in the untruncated message, so the 3-of-6
figure stands on the filing's reading of the transcript and two of the three are confirmed here.

The harvest procedure branches on this number: `claims` answers "how many green results did this
session assert on evidence a filter had discarded", and the answer decides whether the gate gets
re-run. On this session the split (`0 gate, 12 listing`) and `pipefail` both said no re-run was
owed, so nothing followed — but the two checks disagreed, and only reading the transcript resolved
which was right.

[PITFALL: **a matcher whose vocabulary is a topic over-counts on any session whose topic it is**,
and this corpus writes about its own instruments constantly. The same failure is recorded for a
different instrument in
`power-user-linux-setup/plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`: that counter
over-reports by ~8% because it anchors on `\brg\b` anywhere in a command, so a corpus that writes
about the trap inflates its own count of it. Both instruments are used to audit sessions that write
about auditing, which is the condition that makes the shape systematic rather than unlucky.]

## The cause, confirmed

`GREEN_CLAIM_RE` (`skills/session-harvest/scripts/harvest.py:105`) has four alternatives, and **none
of them contains a term for CI**:

```python
r"gate[^.\n]{0,40}\b(green|clean|pass(?:es|ed)?)\b"

r"|\b(precommit|pre-commit|quality\.(?:check|precommit)|pytest|test suite|suite)\b[^.\n]{0,40}\b(green|clean|pass(?:es|ed)?|all good)\b"
r"|\ball (?:tests|checks)\b[^.\n]{0,20}\bpass(?:es|ed)?\b"
r"|\b(0 errors|exits? 0|exit code 0)\b"
```

"Both CI legs green" matches nothing: `green` is there, but the word within 40 characters is `legs`,
and `CI`, `run`, `workflow` and `check run` appear in no alternation. The vocabulary it has is the
**local gate's** — `precommit`, `pytest`, `quality.check`.

**The over-count comes out of two different alternations, which is why one fix will not do.** The
denials are the first: `no test anywhere runs the gate on a clean machine` puts `clean` fourteen
characters after `gate`, inside the window. Nothing there looks at whether the sentence **negates**
the claim, and "on a clean machine" is a phrase this corpus generates constantly — the clean-OS tier
is a whole section of `session-harvest`'s own step 5.

The exit-code prose is the **fourth**, and it is the alternation with no subject term in it at all:
`\b(0 errors|exits? 0|exit code 0)\b` matches any sentence containing those words, about anything.
Verified 2026-09-08 by running the live pattern over both sets of sentences. That makes it the
broadest of the four by construction, and the one a session writing about exit codes — which is what
this corpus is largely about — will trip on its own subject matter.

**The gap is against the check's own stated design.** The comment above the pattern reads:
_"Sentences that tell the user a gate passed. Deliberately broad: an over-count is a footnote the
agent reads and discards, while a miss is the failure this whole check exists to prevent."_ It is
broad within one vocabulary and empty in another.

[PITFALL: **the missing vocabulary is the one this skill's own procedure generates.** Step 5 devotes
a bullet to checking CI for anything the session pushed, and the sweep prints `completed/success`
rows per run — so a harvest that follows the procedure is _led_ to write "CI green", which is
exactly the sentence `claims` cannot see. The two halves of the same step disagree: one tells you to
report CI, the other does not count you having reported it.]

[PITFALL: **the over-count is not harmless in the way the design comment assumes.** The comment
tolerates over-counting because a human discards a wrong row on sight. The three rows above are not
obviously wrong on sight — each contains "the gate" and reads as gate-related — so a report saying
"3 green-gate claims against 27 masked calls" looks exactly like a real finding and sends the reader
to re-run a gate for reasons that do not exist. The tolerance was priced against noise, and this is
plausible noise.]

## Open questions

[NEEDS CLARIFICATION: **widen the alternation, or match on the claim rather than the subject?**
Adding `ci|workflow|run|check run|actions` to the second group is one line and covers the observed
phrasing. Against it: the pattern is already four alternations of subject-plus-adjective, and each
new subject is another guess at how a sentence will be worded. The alternative is to invert it —
match a green adjective near any of a small set of _result_ words — which is broader in the
direction the comment says it wants, at the cost of more over-counting. The comment already says an
over-count is a footnote, so the trade is pre-decided if anyone applies it — but the denial
false-positives above are the case that says it is not, so decide this one against both directions
rather than against the miss alone.]

[NEEDS CLARIFICATION: **should a CI claim count the same as a gate claim at all?** They fail
differently. A masked local gate means the session could not see the result it reported. A CI claim
is read from `gh run list --json`, which the sweep deliberately reads as JSON precisely so no pipe
can eat the exit code — so a CI green claim is not usually resting on masked evidence even in a
session with a high `exit-masked`. Counting them together would inflate the number that pairs with
the masked count and weaken the sentence it exists to produce. Possibly two counts, reported
separately.]

[NEEDS CLARIFICATION: is negation worth detecting at all, or is `clean machine` simply the wrong
noun to match near `gate`? A stop-list (`clean machine`, `clean checkout`, `clean tree`) is one line
and is aimed at the observed collision. General negation handling in a regex is not, and the second
question above may make the whole pattern narrower anyway.]

[NEEDS CLARIFICATION: **does the fourth alternation earn its place at all?** It is the only one with
no subject term, it produced two of the three confirmed false positives, and every true positive in
both samples was caught by one of the other three. The candidate the filing proposed is to require a
gate-shaped subject near the exit-code words — a gate, a suite, a test count, CI — which keeps every
true positive in its sample and drops both confirmed false ones. Deleting the alternation outright
is the cheaper version of the same idea and needs one counter-example to rule out: a real green
claim phrased only as a bare exit code. Independent of the negation work above, and narrower.]

[UNVERIFIED: whether the over-count rate generalises. Two sessions now sit at a similar rate from
unrelated causes — three false positives each — but neither is a corpus-wide count, and the
2026-09-08 session's subject was unusually exit-code-heavy: a packaging probe whose finding was
literally that a command exits 0 and does nothing. The corpus is greppable; a count over every
transcript would settle it before any pattern is touched.]

The corpus's rule is that a regex is tested against hand-written cases, and **the test's cases are
no longer hypothetical** — one real transcript supplies both directions. A test here wants the
phrasings that must match and at least one that must not, since a matcher that becomes a matcher for
anything would pass a positive-only suite, the same failure already recorded for `--expect`'s quote
handling.

## Recommended direction

Decide the second question first: it determines whether this is a one-line widening or two counters.
Then write the test before the pattern change, using all four sentences from the
`a3c12c26-55b9-4ed1-941f-42898b4bf565` transcript — the three denials that wrongly matched and one
of the green assertions that wrongly did not — plus "Both CI legs green" as the case that currently
fails, and the two confirmed exit-code sentences from `2f0fa965-60a4-4478-bcba-5097aff65801` as the
must-not-match cases for the fourth alternation. A positive-only suite would pass for a matcher that
matches everything, which is the failure already recorded for `--expect`'s quote handling.

**Decide the three shapes together, because they are not three fixes.** The fourth alternation may
simply go, which resolves one over-count with no new machinery; the CI vocabulary question decides
whether the pattern grows a subject or loses the concept of one; and the negation question only
matters if the first alternation survives in its current form. Taking them one at a time risks
adding a stop-list to an alternation that a later decision deletes.

Worth doing before the next session that runs a piped gate, since that is the run where the
under-count would matter — and the phrasing is generated by this skill's own procedure, so it is not
a rare shape.
