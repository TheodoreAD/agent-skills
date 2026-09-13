---
status: in-progress
updated: 2026-09-13
---

# `skills-state` says the skill moved, never which part of it moved

## Context

Filed from a `power-user-linux-setup` harvest, 2026-09-13. `SKILL.md` already reports apart from
`scripts/` and `references/` in the skill's prose — _"The three subdirectories fail differently,
which is why the subcommand reports `SKILL.md` and the rest apart"_ — but the **moved-since-start**
list does not inherit that split. It is one list of commits per skill.

What the run printed for `plan-docs`:

```
== plan-docs ==
  installed copy matches the checkout; SKILL.md moved after this session began (7 commit(s)) —
  re-read it from whichever side is ahead, unless every one of those commits is this session's own
  moved since start: 15ab22d plan-docs: say what the first call does in a repo that keeps no plans…
  … six more …
```

Every remedy in that line is about `SKILL.md`. This session never loaded `plan-docs`' `SKILL.md` at
all — no `Skill` call — and used the skill exclusively by shelling out to `plans.py`, eight times,
across `absorb`, `absorb --apply`, `list`, `new`, `commit` and `set-status`.

## Evidence

The question the session actually needed answering was whether **`scripts/plans.py`** moved, because
that is the code its calls executed and an earlier call may have run an older installed copy. The
answer was not in the output. It took a hand-written command against another repo to get it:

```shell
git -C <checkout> log --oneline --name-only 6b0e71d~1..15ab22d -- skills/plan-docs/scripts/
```

— which returned **4 of the 7 commits**, all touching `plans.py`. So the actionable half was a
subset of the reported set, and nothing said so.

[PITFALL: **the wrong half was the loud one.** The line names `SKILL.md`, gives the `SKILL.md`
remedy (re-read it), and lists seven commits under it. A reader who follows it exactly re-reads a
file this session never held, and never asks the question that mattered. The skill's prose does
carry the `scripts/` rule — _"a call made earlier in the session ran the old one … Read the diff
before deciding a note is enough"_ — but it fires on a reader who already knows `scripts/` moved,
and the subcommand is what would have told them.]

**The split already exists for the verdict and not for the history.** `skills-state` compares
install against checkout per subdirectory; it is only the moved-since-start commit list that is
flattened to the skill. So this is a reporting granularity gap rather than a missing comparison, and
the data to fix it is already being read.

**A session that never loads a skill's `SKILL.md` is not the unusual case.** Four of this machine's
skills are invoked overwhelmingly through their scripts — `plan-docs`, `session-bash-audit`,
`research-library`, `session-harvest` itself — and a harvest is the run most likely to touch several
of them without a single `Skill` call. The existing fallback ("a skill with no such call falls back
to session start") handles the _baseline_ correctly and says nothing about which part moved.

## Step 1 landed, and its first real run found the trigger has the same flaw (2026-09-13)

Annotation landed as `307262d`: each moved commit ends `(SKILL.md)`, `(scripts/)`,
`(SKILL.md, scripts/)`. The flattened list stays, as step 3 asks. Read live in the same session, it
showed `plan-docs` as three `(scripts/)` commits and one `(SKILL.md)` under the unchanged
`SKILL.md moved` sentence — the shape this plan describes, now readable from the output alone.

[PITFALL: **a skill whose `SKILL.md` did not move gets no moved note at all, however much else
moved.** The move check compares the baseline against `skill_md_last_commit`, the last commit
touching `SKILL.md`, and only then lists every commit under the skill. The same run showed
`session-bash-audit` with two commits since session start — `28099cd` to `scripts/audit.py`,
`692a391` to `references/research.md` — and `moved_since_session_start: false`, because its
`SKILL.md` last changed 2026-09-07. So the list's flattening was the visible half. The trigger is
the silent half: a scripts-only change, the case this plan says matters most, is never reported as a
move. `subdirs_differing` does name `scripts/` there, but only as install-against-checkout, which
says nothing about whether an earlier call in this session ran the old code.]

The trigger and the sentence are one decision, so neither was changed alone. Firing on any part
while the sentence still says `SKILL.md moved` would make it wrong on exactly the new rows. That is
the second question below, which now has the real run that step 2 was waiting for.

## Open questions

- **Split the list, or annotate?** Annotated — answered by step 1.

[NEEDS CLARIFICATION: should the remedy sentence key on what this session actually used? It already
knows, from the same `Skill`-call scan that sets the baseline: no `Skill` call plus N `scripts/`
calls in the transcript means the `scripts/` remedy is the relevant one and the re-read is not. That
would make the line right rather than merely complete, but it couples the subcommand to transcript
resolution it does not currently need.]

[NEEDS CLARIFICATION: does `references/` need the same treatment? The prose says it is inert for the
verdict and stops being inert for a page this run opened. Same shape as the above, and the same scan
answers it.]

## Recommended direction

1. Annotate first — it is the small change, it uses data already being read, and it cannot be wrong
   the way a keyed remedy can.
2. Leave the remedy sentence alone until the annotation has been read in a real run or two. The
   second question above proposes making the subcommand smarter about this session specifically, and
   this skill's own history is full of narrowings that were right about the evidence in front of
   them and moved the error somewhere else.
3. Whatever lands, keep the flattened list available. A skill that moved seven times is worth seeing
   whole, and the annotation is what makes the subset findable rather than a replacement for it.
