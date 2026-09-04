---
status: landed
updated: 2026-09-02
---

# A session bumps `status:` with an editor, and `set-status`' gate never runs

Merged 2026-09-01 from `2026-09-01-status-gate-bypassed-again-including-a-terminal-transition.md`,
which recorded the second occurrence and is **merged away and deleted** —
`plans.py archive --show 2026-09-01-status-gate-bypassed-again-including-a-terminal-transition.md`
reads it back. It asked for this merge in its own body rather than standing as a second file.

## Context

`plan-docs` states the promotion mechanism plainly — `set-status <file> <status>` "runs that gate
and refuses while any remain, so a refusal is the answer, not an obstacle to route around with
`--force`" — and notes the same command stamps `updated`. What it does not anticipate is that a
session changing a plan's status is almost never changing _only_ that: it is already mid-edit in the
file body, resolving `NEEDS CLARIFICATION` tags into `DECISION`s, and the frontmatter is four lines
above the cursor.

Two occurrences now, in two repos, with the same proximate cause.

**Occurrence 1** — a `repo-tasks` session, 2026-08-30. Two plans advanced in one sitting:

| plan                                                | frontmatter change made by hand                       |
| --------------------------------------------------- | ----------------------------------------------------- |
| `2026-08-29-pytest-ini-anyio-mode.md`               | `status: idea` -> `in-progress`, `updated:` stamp     |
| `2026-08-29-python-floor-in-the-shipped-configs.md` | `updated:` stamp, `depends_on: [scaffoldapy]` removed |

**Occurrence 2** — a `github.com-personal/ingesta` session, 2026-09-01. Two more:

| plan                                         | transition made by hand |
| -------------------------------------------- | ----------------------- |
| `2026-08-29-local-run-and-manual-testing.md` | `idea` -> `in-progress` |
| `2026-09-01-local-catalogue-drift.md`        | `idea` -> **`landed`**  |

Every one of those went through the file-editing tool. `set-status` was never called, so its gate
never ran. Both sessions had the skill in context in the same sitting and still did this — neither
overrode a refusal, both simply never reached the code path that could refuse.

[PITFALL: the bypass leaves no trace, and the result looks exactly like a correct promotion. The
frontmatter is well-formed, `list` renders the new status, and the next reader has no way to tell
whether the gate passed or was never consulted. In both sessions the gate would have passed — the
tags had been converted first — but that was luck, not process, and nothing in the artifact records
which it was.]

## What the terminal case adds

The second occurrence's second transition was **terminal**. Occurrence 1 measured
`idea -> in-progress` and `updated:` stamps — non-terminal, where a skipped gate costs a status that
might be premature. `idea -> landed` is the transition that _precedes deletion_: it is the one
`set-status` guards with the `UNVERIFIED`-blocks-`landed` rule and with the refusal to retire a plan
still sitting in a repo-routed repo's store mirror. That session then retired the plan — migration
section, reference fix, `git rm` — in the following three commits.

So the gate that was skipped is not only the promotion gate. The same hand-edit reaches a status
whose next step is a one-way door, and the two guards that exist specifically to stand in front of
that door were both bypassed by an edit that looked like ordinary body work.

## Evidence

- Occurrence 1: measured in a `repo-tasks` session, 2026-08-30.
- Occurrence 2 transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/81ef32cd-7240-48b8-b0a3-4cd53845adad.jsonl`,
  session start `2026-09-01T09:01:27.595Z`. That session had invoked `plan-docs` in its first turn
  and held the skill in context throughout.
- Occurrence 2 commits, in `github.com-personal/ingesta`: `88dda8a` (the `in-progress` bump), and
  `a4c70dc` / `bb76f58` / `898bc07` (the `landed` bump and the retirement that followed it).

## Open questions

[DECISION: this is the "not followed" failure shape, which the harvest skill's own routing calls a
measurement question rather than a rewording one. Settled by the second occurrence rather than by
argument: two sessions, two repos, the same proximate cause, and no evidence in either transcript of
the rule being weighed at all. It beat "reasoned around" because neither session overrode anything,
and it beat "followed and produced a bad outcome" because the gate never ran.]

[DECISION: **wording first, and the cheapest of the three options.** Settled 2026-09-02, taking the
first option — say explicitly that a status or `updated` line is never hand-edited whatever else in
the file is being changed. The two rejected options were both more expensive than the evidence
supports: folding the transition into a normal editing flow means `set-status` grows a mode that
edits the body, and after-the-fact detection is the question below, which this decision does not
foreclose. Four occurrences is enough to justify a sentence and not enough to justify a mechanism —
and the sentence has to be tried first anyway, or a detector's hit rate is measured against a rule
nobody was told.]

[DEFERRED: whether anything should _notice_ a hand-edited status. `git log -p` over `plans/` can see
a `status:` line changing in a commit, and `set-status` could leave a marker the check reads, but a
marker in frontmatter is a new field to maintain and drift. A cheaper version — have `doctor` or
`list` report a plan whose `updated:` disagrees with its file mtime or its last commit date — was
looked at on 2026-09-02 and is **not** as clean as it reads: an ordinary body edit that changes no
status legitimately leaves `updated:` behind, so the check fires on the common case and the backlog
it prints is mostly noise. That is the alarm-fatigue shape the retirement-prompt work already argues
against. Revisit only if the wording above is measured to have failed — a fifth occurrence after
2026-09-02 is the trigger, and it is a cheap grep of the corpus to look for.]

## What landed, 2026-09-02

The rule is in `plan-docs`' **"Run the script, don't re-derive it"** section — the first section of
the file, alongside the command surface — and not under **Promoting a plan**, for the reason the
recommendation below gives: none of the four measured hand-edits was `idea -> planned`, so a rule
scoped to promotion would have been invisible to every case.

It is stated as the recommendation asked: "`status:` and `updated:` are `set-status`' output. They
are never lines you type", followed by the four-hand-edit measurement and the `[PITFALL:]` about the
bypass leaving no trace. **Promoting a plan** keeps one clause pointing at it, so a reader who
arrives there is sent to the measurement rather than given a second copy of the rule.

## The trigger fired on 2026-09-04, and it is not a fair test

The `[DEFERRED:]` above names its own trigger — "a fifth occurrence after 2026-09-02". Four more
arrived on 2026-09-04, in a `repo-tasks` session, recorded in
`2026-09-04-session-rule-adherence-evidence.md` §1: two `idea -> in-progress` bumps and two bare
`updated:` restamps, two through the file-editing tool and two through a `python3 - <<'PY'` string
replacement. On the count alone the condition is met twice over.

**It does not fire the revisit, and the reason is the whole point of recording it.** That session
could not have known the rule: the wording — "`status:` and `updated:` are `set-status`' output.
They are never lines you type" — was committed to `plan-docs` **after** the session loaded the
skill, and `skills-state --since` put `SKILL.md` 39 commits ahead of it, none of them the session's
own. The 2026-09-02 decision was that wording is tried first and a detector's hit rate is otherwise
"measured against a rule nobody was told" — and this is precisely a session nobody told.

So the deferred question stays deferred, with its trigger **re-armed rather than spent**: the next
occurrence that counts is one by a session that held the current wording from the start. What these
four do establish is a different defect, which is not this plan's: nothing in a running session
re-reads a skill it already holds, so a rule can be correct, deployed and invisible at once. That
belongs with the propagation question in the evidence plan, and it is why the two files stay apart
rather than merging — they share four rows of evidence and disagree about what those rows are
evidence _of_.

Kept separate deliberately, 2026-09-04, when `absorb` paired them.

## Recommended direction

Rough, and deliberately not settled here.

The `updated:` half is the tell worth keeping in view: a session that hand-edits `status:` also
hand-stamps `updated:`, and gets it right only because it happens to know today's date. `set-status`
already does both. So whatever fix is chosen, the argument to make in the skill is not "the gate
matters" — a session that never consulted the rule is not persuaded by a stronger claim about the
gate — but "these two lines are the command's output, not yours to type", which is a rule about the
file rather than about the transition, and so does not depend on the session having classified what
kind of transition it is making.

**Do not aim the rule at "promotion".** The heading it currently lives under (**Promoting a plan**)
reads as being about `idea -> planned` specifically, and none of the four hand-edits across the two
sessions was that transition — two were `idea -> in-progress`, one was `idea -> landed`, one was a
bare `updated:` stamp. A rule scoped to promotion is invisible to every case actually measured.

Related: the skill's command surface was reshaped in the same week, and the reasoning — including
why `set-status` keeps its name and why the inspection command could not be called `status` — is in
`skills/plan-docs/references/design-rationale.md`. Whatever lands here should be checked against
that rather than designed independently. (That work was planned in
`plans/2026-08-29-plan-docs-ergonomics.md`, now retired.)
