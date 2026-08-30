---
status: idea
updated: 2026-08-30
---

# A session bumps `status:` with an editor, and `set-status`' gate never runs

## Context

`plan-docs` states the promotion mechanism plainly — `set-status <file> <status>` "runs that gate
and refuses while any remain, so a refusal is the answer, not an obstacle to route around with
`--force`" — and notes the same command stamps `updated`. What it does not anticipate is that a
session changing a plan's status is almost never changing _only_ that: it is already mid-edit in the
file body, resolving `NEEDS CLARIFICATION` tags into `DECISION`s, and the frontmatter is four lines
above the cursor.

Measured in a `repo-tasks` session, 2026-08-30. Two plans were advanced in one sitting:

| plan                                                | frontmatter change made by hand                       |
| --------------------------------------------------- | ----------------------------------------------------- |
| `2026-08-29-pytest-ini-anyio-mode.md`               | `status: idea` -> `in-progress`, `updated:` stamp     |
| `2026-08-29-python-floor-in-the-shipped-configs.md` | `updated:` stamp, `depends_on: [scaffoldapy]` removed |

Every one of those went through the file-editing tool. `set-status` was never called, so its gate
never ran. The session had read the skill in the same sitting and still did this — it did not
override a refusal, it simply never reached the code path that could refuse.

[PITFALL: the bypass leaves no trace, and the result looks exactly like a correct promotion. The
frontmatter is well-formed, `list` renders the new status, and the next reader has no way to tell
whether the gate passed or was never consulted. In this case the gate would have passed — the tags
had been converted first — but that was luck, not process, and nothing in the artifact records which
it was.]

## Open questions

[NEEDS CLARIFICATION: which of the three failure shapes this is. It is not "the rule was followed
and produced a bad outcome", and it is not quite "reasoned around" either — the session never
weighed the rule at all, because the rule lives under a heading (**Promoting a plan**) that reads as
being about the `idea -> planned` transition specifically, while the case here was
`idea ->
in-progress` arriving as a side effect of an edit. Closest to "not followed", which the
skill's own routing calls a measurement question rather than a rewording one. Worth deciding before
choosing a fix, since the three have different ones.]

[NEEDS CLARIFICATION: whether the wording alone can fix this. A stronger sentence in the skill is
the cheap option, but the failure mode is a session that is already holding the file open in an
editor — the moment of temptation is not the moment it reads the skill. Options, roughly by cost:
say explicitly that a status or `updated` line is never hand-edited whatever else in the file is
being changed; have `set-status` accept the transition as part of a normal editing flow so it is not
a second command; or detect it after the fact.]

[NEEDS CLARIFICATION: whether anything should _notice_ a hand-edited status. `git log -p` over
`plans/` can see a `status:` line changing in a commit, and `set-status` could leave a marker the
check reads, but a marker in frontmatter is a new field to maintain and drift. A cheaper version:
have `doctor` or `list` report a plan whose `updated:` disagrees with its file mtime or its last
commit date, which is the same smell from a different angle and needs nothing new stored.]

## Recommended direction

Rough, and deliberately not settled here.

The `updated:` half is the tell worth keeping in view: a session that hand-edits `status:` also
hand-stamps `updated:`, and gets it right only because it happens to know today's date. `set-status`
already does both. So whatever fix is chosen, the argument to make in the skill is not "the gate
matters" — a session that never consulted the rule is not persuaded by a stronger claim about the
gate — but "these two lines are the command's output, not yours to type", which is a rule about the
file rather than about the transition, and so does not depend on the session having classified what
kind of transition it is making.

Related: the skill's command surface was reshaped in the same week, and the reasoning — including
why `set-status` keeps its name and why the inspection command could not be called `status` — is in
`skills/plan-docs/references/design-rationale.md`. Whatever lands here should be checked against
that rather than designed independently. (That work was planned in
`plans/2026-08-29-plan-docs-ergonomics.md`, now retired.)
