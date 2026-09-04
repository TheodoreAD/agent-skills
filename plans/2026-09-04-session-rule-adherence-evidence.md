---
status: idea
updated: 2026-09-04
---

# Evidence from one repo-tasks session: three rules broken, two of them measurable

## Context

Filed from `repo-tasks` on 2026-09-04 by a `/session-harvest` run. A five-day session
(`e460705a-5b5b-4d94-ac7b-539af8412078`, 254 Bash calls before the harvest boundary). Nothing in
this repo was touched. Each finding below names the plan or skill it is evidence **for** — none of
them is new, and the point of filing is the counts rather than the observation.

## 1. Frontmatter hand-edited instead of `set-status` — evidence for an existing plan

Belongs in `plans/2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md`, which already
records four instances across two sessions on 2026-08-30 and 2026-09-01. **This session is a third
session and adds four more**, all on 2026-09-04:

| plan edited                                    | what was typed                                       |
| ---------------------------------------------- | ---------------------------------------------------- |
| `2026-08-30-tests-import-layout.md`            | `status: idea` → `in-progress`, `updated:` restamped |
| `2026-08-30-tests-import-layout.md`            | `updated: 2026-08-30` → `2026-08-31`, earlier        |
| `2026-08-30-deps-audit-in-ci.md`               | `updated: 2026-08-31` → `2026-09-04`                 |
| `2026-08-25-release-without-release-branch.md` | `updated: 2026-08-30` → `2026-09-04`                 |

Two through the file-editing tool, two through a `python3 - <<'PY'` string replacement. The gate ran
for none of them.

[PITFALL: **this session could not have known the rule, and that is the finding.** The wording that
states it — "`status:` and `updated:` are `set-status`' output. They are never lines you type" — was
committed to `plan-docs` **after** this session loaded that skill. `skills-state --since` reports
`SKILL.md` moved 39 commits since the session began, none of them this session's. So the existing
plan's framing, which reads as sessions ignoring a rule in front of them, does not fit this
instance: the rule was correct, deployed, and invisible to the session that broke it. That is a
**propagation** failure rather than a wording one, and it takes a different fix — nothing in a
running session re-reads a skill it already holds.]

Worth noting what did work: when the harvest later called `set-status` properly, the gate **refused
twice** — once on two open `NEEDS CLARIFICATION` tags, once on an `UNVERIFIED` — and both refusals
were correct. The mechanism is sound; only its reach into an already-running session is not.

## 2. `uv run <tool>` inside the session's own repo — a candidate for `session-bash-audit`

`~/AGENTS.md` already says to check `which <tool>` before prefixing `uv run`, because direnv puts
`.venv/bin` on `PATH`. This session ran `uv run pytest` anyway and the user corrected it
mid-session:

> "let's not do uv run pytest, we can just run pytest or ruff or the other tools, and if you need a
> complete check go for the invoke tasks."

The rule was in context and unfollowed, which by the misuse taxonomy is the third shape — the
wording is fine and something else is failing. **`session-bash-audit` does not measure this
pattern**, so there is no rate for it: its current set is chain, chain5, head/tail, exit-masked,
redirect-then-filter, sed-n, cat-view, heredoc, cd-own-repo, git-C-own-repo, git-mutating-in-chain,
git-C-mutating, echo-exit, find-not-fd. A `uv-run-own-repo` pattern would make it countable, and
countable is what distinguishes "a session slipped" from "every session does this".

## 3. `$` in a commit message — a second candidate, and it fails loudly

`~/AGENTS.md` says to write commit messages without backticks or `$`, because both are live inside a
double-quoted shell argument. This session wrote a message containing `${{` — GitHub Actions
expression syntax, while documenting a workflow — and the commit died with
`(eval):19: bad
substitution`. One commit in the chain had already landed, so the failure was
mid-sequence.

Cheap to detect and unambiguous: a `git commit -m` argument containing an unescaped `$` or a
backtick. Unlike most patterns in that skill this one has a hard failure attached, so a measured
rate also says how often the session lost a commit to it.

## The session's own numbers, for whatever plan tracks the rates

Measured with `audit.py --until <harvest boundary>`, against the `2026-09-04` baseline (25 main
sessions, 2026-09-01..04):

| pattern               | this session | vs baseline |
| --------------------- | ------------ | ----------- |
| chain                 | 74%          | +29pp MISS  |
| head/tail             | 45%          | +14pp MISS  |
| exit-masked           | 26%          | —           |
| git-mutating-in-chain | 16%          | +10pp MISS  |
| cd-own-repo           | 3%           | +2pp MISS   |

6 of 11 expectations met. The `exit-masked` figure resolved benignly and is recorded here because
the resolution is the interesting part: **82 of 267 calls masked their exit code, and 17 messages
told the user a gate or suite was green** — every one of them from a `| rg | tail` run. The re-run
(`inv quality.check > log 2>&1`) exited 0 with a clean log, so all 17 claims hold. They were true
and unevidenced at the time they were made, which is the distinction the harvest rule exists to
draw.

## A second sample, same day, different repo — and the propagation excuse does not apply

Added 2026-09-04 by a `/session-harvest` run in `agent-skills` itself
(`5554513b-6e49-4d0b-be8f-cba212809203`, 121 Bash calls before the boundary), against the same
`2026-09-04` baseline:

| pattern               | repo-tasks session | this one | baseline delta, this one |
| --------------------- | ------------------ | -------- | ------------------------ |
| chain                 | 74%                | **76%**  | +30pp MISS               |
| head/tail             | 45%                | **50%**  | +20pp MISS               |
| exit-masked           | 26%                | **32%**  | —                        |
| git-mutating-in-chain | 16%                | **19%**  | +14pp MISS               |
| cd-own-repo           | 3%                 | **6%**   | +5pp MISS                |

7 of 11 expectations met, against the other session's 6. Two different repos, two different tasks,
one day apart, and the same four patterns miss in the same direction by roughly the same margin —
which is what turns §2's "a session slipped" into a property of these sessions rather than an
incident.

**What this sample adds is the elimination of §1's explanation.** That finding was a _propagation_
failure: the rule was committed after the session loaded the skill, so it was correct, deployed and
invisible. None of that holds here. Every rule broken in this session — the `head`/`tail`
prohibition, one command per call, no `cd` into the session's own repo — is in the always-loaded
global instructions file, present in context from the first turn, never moved during the session.
And the session's entire subject was authoring worktree rules for four skills, including edits to
`session-bash-audit`, the skill that measures these very patterns. So this is squarely the third
shape in the misuse taxonomy: **the wording is fine, it was in front of the model the whole time,
and something else is failing.**

`exit-masked` resolved the same benign way and is worth recording for the same reason: **41 of 130
calls masked their exit code, and 6 messages told the user a gate or suite was green** — every one
from an `inv quality.precommit 2>&1 | rg … | tail -N` run. The unpiped re-run exited 0, so all six
hold. Two sessions now, 17 claims and 6 claims, both resolving true: the pattern's cost so far is
entirely that the claims were unevidenced when made, not that they were wrong. That is worth stating
plainly, because a finding whose harm never materialises is one the next reader discounts — and the
reason to keep counting it is that nothing about the method would have revealed a false one.

### The correction introduced a second violation, measured an hour later

Same session, re-audited at its second harvest boundary (`00:03`, n=212 against the earlier n=121).
The first harvest told it to stop masking exit codes, and it complied — by switching from
`inv quality.precommit 2>&1 | rg … | tail` to `inv quality.precommit > log 2>&1; echo "EXIT=$?"`.

`~/AGENTS.md` forbids both. The second is the `echo-exit` pattern — "never append `; echo "EXIT=$?"`
— it adds a chain for information the tool already reports" — and the audit saw it appear:

| pattern          | at 23:30 (n=121) | at 00:03 (n=212)   |
| ---------------- | ---------------- | ------------------ |
| echo-exit        | 0% (OK)          | **4% (+3pp MISS)** |
| exit-masked      | 32%              | 33%                |
| head/tail        | 50%              | 51%                |
| expectations met | 7/11             | **5/11**           |

The correct form was neither: run the gate plain. The Bash tool already reports a non-zero exit, so
the redirect and the `echo` both exist to recover something that was never lost — and the redirect
then needs a second call to read the log, which is the chain the first rule was about.

**This is the shape worth having in the corpus**: a session told about one Bash rule satisfied it by
adopting a different banned pattern, within the same hour, with both rules in the same file it was
already holding. It argues against "reword the rule" more strongly than another miss would, because
compliance was not the problem — the session complied, and picked the wrong compliant-looking form.

[NEEDS CLARIFICATION: **is the fix a rule at all?** Three sessions have now broken the `head`/`tail`
rule while holding it in context, one of them while editing the skill that measures it. Rewording is
the reflex and there is no evidence it works. The alternatives are a mechanism the corpus has
already refused for good reasons (a hook that rewrites the command), or accepting the rate and
relying on the audit plus the unpiped re-run to catch what it costs — which is what actually
happened both times. Worth deciding deliberately rather than by another rewording.]

## Open questions

[NEEDS CLARIFICATION: does the propagation failure in §1 belong in the existing hand-editing plan or
in its own? It is a different cause with a different fix, and folding it in risks the existing
plan's "sessions ignore this rule" framing absorbing a case that contradicts it. Against a split:
`plan-docs` prefers one plan per topic, and "the status gate is bypassed" is arguably one topic
whatever the cause.]

[NEEDS CLARIFICATION: is there any fix for a rule landing mid-session at all, short of the harvest
catching it afterwards? `session-harvest`'s `skills-state --since` is the detector and it runs at
the _end_. The available-skills listing changing mid-session is the one free signal, already noted
in that skill — but it fires on install, not on commit, and this session saw no such change.]
