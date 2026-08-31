---
status: blocked on power-user-linux-setup writing the ~/AGENTS.md routing rule
updated: 2026-09-01
depends_on: [power-user-linux-setup]
---

## Context

The skills in this repo are read in every other repo the user works in, and that is where their
problems surface — mid-task in `repo-tasks`, `scaffoldapy`, an `*-polite-mcp` repo: a skill fails to
trigger on the request it exists for, an `~/AGENTS.md` rule turns out to be wrong or missing, a
correction the user just gave should have been permanent.

The evidence — the actual prompt, what the agent did, the correction verbatim, the file that tripped
it — lives in _that_ session, in _that_ repo. By the time a session here picks the topic up, that
evidence is gone and what is left is a second-hand paraphrase.

Symptom already on record: the trigger-quality work (now
`plans/2026-08-30-skill-fitness-analyzer.md`, which merged the earlier plan) opened with "Surfaced
2026-08-22 while working in `repo-tasks`" and then re-narrated the failure in prose, because there
was no mechanism to point at the real turns.

Two existing mechanisms touch this and neither closes it:

- The `session-harvest` skill's "Self-update mechanics" already says: from wherever you are, locate
  the repo that owns the skill, edit its `SKILL.md`, re-install. That is the right answer for a
  one-line additive fix and the wrong one for anything needing design, a new reference file, or the
  quality gate — and it drags a foreign session into a second repo. Since the skills moved here it
  also costs a push before the change is visible, because the installer clones from the remote; the
  `skill-authoring` skill owns that sequence.
- The `plan-docs` skill owns plan lifecycle and already has `depends_on:` for _outbound_ cross-repo
  dependency. It has nothing for _inbound_ provenance — a plan that arrived from elsewhere and whose
  evidence lives elsewhere.

**Split 2026-08-28.** This plan was written in `power-user-linux-setup` when the skills lived there
and one repo owned every capture target. It is now two plans: this file holds the convention — what
a capture is, where it lands, and the `plan-docs`/`session-harvest` changes it needs — and
`power-user-linux-setup`'s `plans/2026-08-28-pulse-capture.md` holds the PULSE-side machinery, the
`~/AGENTS.md` routing rule and the `pulse-capture` helper. Its full drafting history is in that repo
up to commit `19a7148`.

### Where a capture lands

The routing has two destinations, and the split is clean because the two halves already answer to
different repos:

| what the friction is about                                  | plan lands in            |
| ----------------------------------------------------------- | ------------------------ |
| a skill — wrong trigger, wrong content, missing case        | this repo's `plans/`     |
| an `~/AGENTS.md` rule, or any PULSE-deployed mechanism      | `power-user-linux-setup` |
| genuinely both (a rule that should have been a skill, or …) | wherever the fix lands   |

### Prior art (web pass, 2026-08-23)

Checked before designing. Nobody has published this loop; the pieces exist separately.

- [AgentPatterns, "Architecting a Central Repo for Shared Agent Standards"](https://agentpatterns.ai/workflows/central-repo-shared-agent-standards/)
  — the closest match to this family's architecture, and explicitly **one-directional**: central →
  downstream via symlink/copy/package, CI checks downstream _compliance_. Fetched and read: no
  upstream-capture story at all. "The document's scope stops at distribution _to_ downstream
  projects, not collection _from_ them."
- [MSicc, "Skills Central"](https://msicc.net/2026-03-19-skills-central-a-pragmatic-setup-for-reusable-ai-skills/)
  — same shape, same gap; has a `skill-source.md` provenance file per installed skill but documents
  only _pulling_ updates, never pushing findings back. (The `skills` CLI's `skills-lock.json` is the
  equivalent here.)
- Self-improving-agent / learning-loop family
  ([learning-loop-skill](https://github.com/melodykoh/learning-loop-skill), already surveyed in the
  `session-harvest` skill's `references/rationale.md`;
  [self-improving-agent](https://borghei.github.io/Claude-Skills/skills/engineering/self-improving-agent.html),
  [MindStudio writeups](https://www.mindstudio.ai/blog/how-to-build-learnings-loop-claude-code-skills))
  — contribute the _capture at the moment of friction_ idea and a `.learnings/` append target. All
  of them capture **into the current repo**, which is precisely the failure mode here: a learning
  about a published skill filed in `olx-polite-mcp/.learnings/` is invisible everywhere else.
- [Dachary Carey, "Agent skill mega repo woes"](https://dacharycarey.com/2026/03/13/agent-skill-mega-repo-woes/)
  — a constraint, not a solution: skill count is a context tax and overlapping descriptions degrade
  trigger selection. Argues against "add a new skill for this".
- Session transcripts as an evidence store —
  [claude-replay](https://news.ycombinator.com/item?id=47276604),
  [transcript format writeups](https://claude-dev.tools/docs/jsonl-format),
  [PromptConduit](https://promptconduit.dev/blog/claude-code-transcripts-location). Established
  practice for retro-analysis of one's own sessions; nobody uses it as a **cross-repo evidence
  pointer**, which is the one genuinely new piece below.

### The evidence pointer is feasible (verified 2026-08-23)

The design rests on a capture being able to cite real turns rather than describe them. That was
checked before being designed around: a session can name its own transcript, the path is
deterministic from the session id and cwd, and a foreign transcript is readable and extractable
afterwards — this recovers real user turns with timestamps out of a 1.5 MB `repo-tasks` transcript:

```shell
jq -r 'select(.type=="user") | (.timestamp // "") + " | " + ((.message.content // "") | if type=="array" then (map(select(.type=="text").text) | join(" ")) else . end)' <transcript>.jsonl
```

Retention is a real dependency and not this repo's to guarantee: a cited transcript only survives if
the harness is configured to keep it (30 days by default). The exact resolution mechanics, and the
open question of whether the session id is available in every session type, belong to the tool —
`power-user-linux-setup`'s `plans/2026-08-28-pulse-capture.md`.

## Recommended direction

**Three lanes and one new artifact shape.** The load-bearing idea: _capture is not fixing, and the
capture carries a pointer to the real evidence rather than a paraphrase of it._

### 1. Three lanes, decided at the moment of friction

- **Fix-in-place** — a single additive edit to an existing `SKILL.md` section, no design decisions,
  no new files. This is what `session-harvest`'s "Self-update mechanics" already describes; keep it,
  but bound it explicitly so it stops being the default for things it cannot carry.
- **Capture** — everything else. Write a plan file into the owning repo's `plans/`, stop there, tell
  the user. Do not design, do not edit the skill, do not run the owning repo's task runner from the
  foreign session.
- **Fallback** — the owning repo's working tree is unreachable: `gh issue create`, same body
  template, converted to a plan file at triage. Fallback-only for now; promoting issues to the
  primary channel is `power-user-linux-setup`'s `plans/2026-08-23-github-issues-plan-lifecycle.md`.

### 2. The capture artifact: a normal plan file with provenance frontmatter

Lands as `plans/YYYY-MM-DD-topic.md`, `status: idea`, plus new optional fields — the inbound mirror
of `depends_on`:

```yaml
---
status: idea
updated: 2026-08-23
source_repo: repo-tasks
source_session: 8f3c…-…jsonl # the harness's transcript for that session
source_moment: 2026-08-22T16:50:15Z # plus a quoted phrase in the body
---
```

Body adds one section above the usual ones: `## Evidence` — the transcript path, the timestamp, a
verbatim quote of the user's correction, and the exact repro (what was asked, what the agent did,
what it should have done). The point of the frontmatter is that a triage session can **re-read the
original turns** instead of trusting the summary.

`plan-docs`' `SKILL.md` gains a short "Plans that arrive from another repo" section defining these
fields, and the rule that a plan carrying `source_repo` is not done until its `## Verification`
names the original repro in that repo — the fix has to be checked against the case that produced it,
after the skill is re-installed.

[NEEDS CLARIFICATION: does the transcript pointer need a turn-range hint, or is a quoted phrase
enough to find the right part of a multi-MB transcript? Lean: record an ISO timestamp _and_ a
distinctive quoted phrase — cheap, and either one alone can miss.]

### 3. Deliberately not doing

- **No new skill.** Trigger reliability argues for putting the routing rule in `~/AGENTS.md`;
  context cost and description overlap (mega-repo woes, above) argue against another skill. The
  procedure extends `session-harvest` (which already owns "route durable knowledge to its right
  home", and already has the self-update section this bounds) and `plan-docs` (which already owns
  plan shape). This also keeps the trigger off the mechanism
  `plans/2026-08-30-skill-fitness-analyzer.md` shows is the weak link.
- **No `.learnings/` file in the consumer repo.** That is the siloing this design exists to avoid.
- **No hook, no automation.** Same call `session-harvest` already made, for the same reason.
- **No second backlog — in this plan.** Issues stay a fallback so this can land without first
  settling issue lifecycle.

## Pilot 1, by hand (2026-08-23)

A `repo-tasks` session hit exactly this friction (`~/AGENTS.md`'s `cd`/chaining guidance turned out
to be wrong) and captured it by hand, without knowing this plan existed. Unprompted evidence rather
than a rehearsal.

**What matched:** the capture lane was chosen unprompted, and the capture was committed in the same
breath as being written — no untracked-file window in a repo that session did not own.

**What it did not do**, i.e. what remains untested: no provenance frontmatter and no `## Evidence`
section. The capture paraphrased the incident instead of pointing at the transcript — the exact
failure mode §2 exists to prevent, reproduced by an agent that had every reason to do better. That
is the strongest argument in this file that the fields must be **prompted for by a tool** rather
than left to an agent's judgment, and it is why the tool plan exists separately. It was also
committed but not pushed, so the report never left the machine.

[PITFALL: **the lane boundary did not survive contact.** Lane 1 is bounded to "a single additive
edit… no design decisions, no new files." That session did far more from a foreign cwd — a
multi-section rewrite of a `SKILL.md` plus its `references/`, and a new task option with 14 tests —
and it went cleanly: tests green, type-checker clean, committed without incident. The bound was not
wrong about risk so much as about _authority_: the user had explicitly said "you should be able to
do your work there" each time. So the real dividing line is whether the user has authorized
foreign-repo work in this session, not how large the edit is. Reconcile this before the lane bound
is written into `session-harvest`, or that rule will be routinely and correctly ignored.]

## Step 1 landed, 2026-09-01 — and the lane question was already settled elsewhere

**The provenance half is built.** `new --for` writes `source_repo` (filled in from where the session
is), `source_session`, `source_moment`, and an `## Evidence` section naming what to put in it. A
plain same-repo `new` is unchanged. `plan-docs`' `SKILL.md` gains "Plans that arrive from another
repo", including §2's rule that a plan carrying `source_repo` is not done until its
`## Verification` names the original repro, checked in the repo where it happened and after the fix
installs there.

[DECISION: **the fields are emitted as blanks in the file, not described in the skill.** §2 left
this open; the pilots closed it. The failure is not that an agent does not know to cite evidence —
it is that it does not do so while writing prose about something else. A template that asks is the
only intervention with evidence behind it, and it costs nothing.]

**Pilot 2, unprompted and negative, 2026-09-01.** This plan's §2 predicted the failure and the
session reading it committed the failure anyway: filing
`2026-08-31-skill-listing-budget-truncates-subagents.md` for `power-user-linux-setup`, it
paraphrased the incident with no transcript pointer, no timestamp and no repro. Two for two now, the
second by an agent with the description of the failure open in front of it. That is the argument for
the template, made twice, and it has since been backfilled with real evidence — transcript path, two
search anchors, and a runnable repro with its present and wanted behaviour.

[DECISION: **the lane bound does not need writing into `session-harvest`, because `~/AGENTS.md` has
since settled it more strictly than §1 proposed.** The global rule is now that writing to another
repo is out entirely — "no edit and no commit, however small, however obviously correct, however
much a skill's own instructions tell you to" — with `plans.py new --for` named as the route, and
`session-harvest`'s step 6 already reflects it. So lane 1 does not survive at all from a foreign
session, and the `[PITFALL:]` below about authority is answered: **authority does not unlock a
foreign edit**, and the sanctioned form of "the user said I could work there" is a session opened in
that repo, not a larger edit from this one. The pitfall stays on the file as the record of why the
size-based bound was the wrong axis.]

1. ~~`plan-docs` provenance fields + `session-harvest` lane bound~~ — **done 2026-09-01**; the lane
   bound turned out to be already settled by `~/AGENTS.md`. See the section above.
2. `power-user-linux-setup` writes the `~/AGENTS.md` routing rule, which is what makes the by-hand
   loop reachable from a repo that has nothing to do with either of these. **This is now the only
   thing standing between the mechanism and daily use** — a session in an unrelated repo still has
   to know that filing is what it does, and nothing it always loads says so.
3. ~~Pilot by hand~~ — piloted twice, both times unprompted, both times failing the same way before
   the template existed. Step 2 is what a third pilot would test.
4. Then the tool, per `power-user-linux-setup`'s `plans/2026-08-28-pulse-capture.md`. **Its scope
   shrank**: the fields the tool was going to prompt for are now in the template, so what is left
   for it is resolving the session id and transcript path, which is the part an agent cannot
   reliably do for itself.

Both remaining steps are in `power-user-linux-setup`, so this plan is blocked on that repo rather
than on a decision here.
