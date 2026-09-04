---
status: landed
updated: 2026-09-04
source_repo: github.com-personal/ingesta
source_session: 54d36cb9-ba1c-4a48-8316-6f35ab58f452.jsonl
source_moment: 2026-09-04T11:56:29+03:00
---

# The next-session prompt is opt-in, and nobody asks for it

## Context

`session-harvest` step 9 builds a paste-ready prompt for the next session, and its heading is
**"### 9. The next-session prompt, if one is asked for"**. Steps 0–8 end at the report and the
safe-to-compact verdict, and the skill's own `description` frontmatter stops there too — it names
the report and the verdict and never mentions a prompt. So an agent following the procedure
faithfully stops at step 8, which is what happens on every harvest that does not carry an explicit
request.

That gating is a leftover rather than a decision. `plans/2026-08-29-next-session-prompt.md` (status
`landed`) records the feature being built on 2026-09-01 because the user had asked for it manually
three times — _"I keep asking for this manually and I don't give all the details"_ — and the whole
point of building it was to stop the asking. The heading was never changed from the conditional
wording step 9 had while it was only a list of what to leave out.

## Evidence

- Transcript
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/54d36cb9-ba1c-4a48-8316-6f35ab58f452.jsonl`,
  2026-09-04, opening user turn: _"why doesn't session-harvest produce a prompt for the next session
  as the last item? i thought we did that"_.
- The user's recollection is correct and the skill's behaviour is correct too, which is the tell
  that the defect is in the gate rather than in either. The prior session had run a harvest and
  ended at step 8.
- Not a staleness failure:
  `diff ~/.agents/skills/session-harvest ~/projects/github.com-personal/agent-skills/skills/session-harvest`
  on the same day showed the installed `SKILL.md` and the checkout identical through step 9 — the
  only differences were the de-personalisation pass elsewhere in the file (`$RESEARCH_HOME`,
  `$PLANS_HOME` and the skills-repo bullets). So the installed copy carries the conditional heading
  because the source does.

## Open questions, both answered 2026-09-04

**Whether an unconditional prompt is ever noise, and whether it needs a silent empty case: no, and
no — the second question answers the first.** Ordering is one of the three surviving categories and
it is never empty, because there is always something to do next and no opening command prints it. So
the empty prompt does not exist, there is nothing for a silence convention to cover, and a prompt
that comes out as one opening line is a symptom of a subtraction done badly rather than of a session
with nothing to carry. That is what the body now says, in place of the conditional heading.

## Recommended direction

1. **Change the heading and the run order.** `### 9. The next-session prompt` with no condition, and
   whatever in steps 0/8 describes the procedure's end says the prompt is the last thing printed.
2. **Change the skill's `description` frontmatter**, which is the half that would otherwise keep the
   old behaviour alive: it currently ends at "a report ordered least- to most-urgent and a
   safe-to-compact verdict", which is what a session reads when deciding what the skill does. A
   description that does not mention the prompt is a description of the opt-in version.
3. **Close the loop the plan already documents**: push, re-install
   (`npx skills add TheodoreAD/agent-skills --global --skill session-harvest`), then
   `/reload-skills` and invoke it again — the three-step sequence step 9's own self-update mechanics
   section records, which was confirmed 2026-09-01 on an edit to this exact step.
4. **Fold the answer to the open questions into the body rather than leaving them tagged**, since
   both are one sentence about the empty case and neither blocks the heading change.

`plans/2026-08-29-next-session-prompt.md` is `landed` and this is a defect in what landed, so it
belongs as its own plan rather than as a reopened tag on that one — but it should cite it, because
the design reasoning there is what makes the gate look deliberate to anyone who reads only the
skill.

## Migrated to

- `skills/session-harvest/SKILL.md` step 9 — the unconditional heading, the "verdict is not the end
  of the run" line at the end of step 8, and the paragraph answering both open questions (the prompt
  is never empty, because ordering never is). Commit `359c29e`, 2026-09-04.
- The same file's `description` frontmatter, which now names the prompt — the half that would
  otherwise have kept the opt-in behaviour alive whatever the body said.

Not migrated, deliberately: the transcript path and the user's quoted question. The rule stands on
its own now, and the evidence for it is in this commit message and in this file's history.
