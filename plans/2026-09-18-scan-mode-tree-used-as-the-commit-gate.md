---
status: idea
updated: 2026-09-18
source_repo: github.com-personal/freshful-polite-mcp
source_session: 2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl
source_moment: 2026-09-06T11:07:00Z
source_plan:
---

## Context

A session ran `plans.py scan --mode tree` as its pre-commit confidentiality gate, then committed and
pushed two plan files to a public repo. The correct gate is `--mode staged` before each commit, and
`--mode history` before a first push.

This is the third shape in `session-harvest`'s taxonomy — **a rule that was simply not followed**,
not one that was wrong or reasoned around. The wording is fine and was in front of the session twice
over:

- `plan-docs`' own SKILL.md, loaded into that session's context minutes earlier, says outright:
  "**`--mode tree` is not the pre-push gate, and using it as one is the mistake to avoid.**"
- the machine's always-loaded instructions file gives the two commands with inline comments naming
  exactly when each applies (`--mode staged` "before the commit", `--mode history` "what is already
  published").

So this is a measurement question rather than a rewording one. n=1 — one session, one call — which
is why the ask below is a counter and not an edit to any skill body.

**Re-measured at that session's end, 2026-09-20.** The figure above was taken when the session had
run 35 Bash calls; it finished on 139, having done a whole bug-fixing phase and two retirements
afterwards. Every `plans.py scan` call in the full transcript, by mode:

| mode             | calls |
| ---------------- | ----- |
| `--mode tree`    | **1** |
| `--mode history` | 2     |
| `--mode staged`  | 7     |

So `n=1` holds against the larger denominator, and the shape is clearer than the prefix could show:
the single wrong call is the **first** one, at 2026-09-06T11:08Z, and the nine that follow — across
three separate commit batches on two later days — are all correct. Nothing corrected the session in
between; the wrong call simply was not repeated.

[PITFALL: a first count of the modes said `tree: 1, history: 2, staged: 7, (no --mode): 1`, and the
fourth was the counting script matching **its own source** — the string `plans.py scan` appears in
the Python that greps for it. Any transcript that has loaded a script counts that script. The same
self-counting shape `session-harvest` already documents for its own `AskUserQuestion` markers, met
here in a one-off query rather than in a skill.]

That last row matters for the ask below, because it is evidence about which of the three misuse
shapes this is. A session that gets it wrong once and right nine times is not one that misread the
rule or reasoned around it — it is one that had not read that part of the skill yet when it ran the
first scan, and did afterwards. A counter would catch exactly that first call.

## Evidence

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-freshful-polite-mcp/2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl`

The call, at roughly 2026-09-06T11:07Z, distinctive phrase
`Running the confidentiality scan and the repo's gate before committing`:

```
python3 ~/.agents/skills/plan-docs/scripts/plans.py scan --mode tree
```

followed by `uv run inv check`, `uv run inv fix`, two `git commit` calls and a `git push` to
`origin/main` (`fd3c260..2b4eac9`). No `--mode staged` call anywhere in the session.

No user correction — nobody noticed at the time. The harvest twelve days later re-ran the correct
gates retroactively:

- `scan --mode history` over the repo: **0 hits** against 61 private terms.
- `scan --mode staged` before the harvest's own commit: **0 hits**.

So nothing leaked, and that is the point worth recording rather than the relief: **a wrong-mode scan
returns the same reassuring `0 hit(s)` line as a right one.** The output format is identical, the
exit code is identical, and the mode is one word in the middle of a command nobody re-reads. The
session reported "Running the confidentiality scan" and believed it.

[PITFALL: `--mode tree` is not a no-op, which is what makes it survive review. It really does scan
the working tree, really does derive the 61 private terms, and really does report hits when the
working tree has them. It is wrong only about the thing a commit gate has to be right about —
history — and a session that has just written its files is a session whose tree and index agree, so
the two modes usually return the same answer. They diverge exactly when it matters: a plan that
named a client, was reworded, and was committed again leaves a clean tree and a dirty history.]

## Open questions

[NEEDS CLARIFICATION: is a `session-bash-audit` row the right home? That skill's description already
invites "a newly noticed Bash anti-pattern so the next audit measures it", it already carries a
`store-write-by-git` row for a neighbouring plan-docs misuse, and the pattern is trivially greppable
— `plans.py scan` with `--mode tree`, or with no `--mode` at all if the default is tree. The
counter-argument is that one instance does not justify a row, and every row costs display space in
every audit forever.]

[NEEDS CLARIFICATION: how often does it actually happen? Nothing here establishes a rate. The corpus
is right there — one pass over `~/.claude/projects/*.jsonl` for `plans.py scan` calls, split by
mode, would say whether this is a habit or a one-off, and that answer decides whether anything at
all should change. Run that before adding a row.]

[NEEDS CLARIFICATION: should `scan` itself say something? A `--mode tree` run immediately followed
by a commit is a shape the script could notice — it knows the repo, so it could check whether the
index is non-empty and print one line pointing at `--mode staged`. That is a nudge rather than a
gate, which is the shape the global rules prefer over a mechanism that fires behind the agent's
back. But it also puts advice in a command whose output a session skims for the hit count.]

## Recommended direction

Measure first. A row in `session-bash-audit` is cheap and reversible, but the rate is unknown, and
the honest sequence is the corpus pass in the second open question before either of the other two.

If the rate turns out to be near-zero, the right outcome is to record this instance in that skill's
research notes and add no row — a counter that never fires is a line every future audit reads past.

Filed from a session in `freshful-polite-mcp`, which cannot edit this repo.

## Verification

Not started. The retroactive gates above came back clean, so nothing in `freshful-polite-mcp`'s
published history needs action; this plan is about the instrument, not that repo.
