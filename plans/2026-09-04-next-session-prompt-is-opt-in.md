---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: **whether an unconditional prompt has a case where it is noise.** The
subtraction rule already handles the empty case in principle — on a well-harvested session most
candidates fail the three-command delta test — but "most" is not "all", and a prompt that prints an
opening line and nothing else is worse than no prompt, because it reads as "nothing to carry" when
it may mean "the subtraction was done badly". Either it is silent when the delta is empty, the way
`absorb` is silent when it filed nothing, or it says explicitly that the delta was empty. The first
matches the convention's existing precedent.]

[NEEDS CLARIFICATION: **whether the ordering line survives an empty delta.** Ordering — what to do
first, and why this rather than that — is the one category step 9 calls "usually the most valuable
line", and it is never empty: there is always something to do next. So the honest version of the
above may be that the prompt is never empty, and the silent case does not exist.]

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
