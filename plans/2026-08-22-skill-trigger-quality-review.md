---
status: idea
updated: 2026-08-29
---

## Context

Surfaced 2026-08-22 while working in `repo-tasks`: the `python-conventions` skill's `description`
frontmatter under-triggers on exactly the requests it's meant to cover. Its testing-conventions
clause reads `test structure (DAMP vs DRY, fixture scope)` — internal vocabulary the skill uses
about itself — rather than the words a real request contains (`pytest`, `fixtures`, `parametrize`,
`write
tests`). Claude Code decides whether to invoke a skill by matching the request against that
description text before ever loading the file, so a description built from a topic's own jargon
instead of the request-side vocabulary a user/agent would actually type is a structural miss, not a
one-off fluke — it happened mid-session even with the skill's own author present in the
conversation.

This is a repo-wide risk, not a one-file problem: all ten skills here have exactly the same single
point of failure — one dense `description` string, hand-written once, never mechanically checked
against the vocabulary real requests would use. No current process re-reads a skill's description
from the "cold request" side after it's written, and `tests/unit/test_skill_layout.py` deliberately
does not try to: it checks that a `description` exists and fits the 1024-char cap, which is a
structural check, not a behavioural one.

The risk grew with the repo. When this was written there were six skills in
`power-user-linux-setup`'s `skills/`; there are now ten published here, and the more descriptions
share a corpus the more likely two of them plausibly match the same request.

**Before building anything custom: Claude Code already ships at least two things aimed at this exact
problem space, unconfirmed whether either actually covers this repo's skills.** `claude plugin eval`
(writing/running plugin eval suites, JSON/report output, sandbox, CI, early-access enablement) and a
`/skill-doctor` report — both referenced by the `claude-code-guide` subagent's own description in a
live session, meaning they're real, documented, current features, not something half-remembered.
Neither has been read in detail yet. Open question below: do either apply to a plain
`skills/<name>/SKILL.md` published from a bare GitHub repo and installed with
`npx skills add TheodoreAD/agent-skills`, or are they scoped specifically to skills packaged and
distributed as a Claude Code "plugin" — a vendor manifest format this repo's `AGENTS.md` rules out
on principle? If they apply as-is, this plan is mostly "go read the docs and run the tool," not
"build something."

## Research findings (2026-08-22, second pass)

**`claude plugin eval`**: confirmed real (embedded early-access reference, corroborated by
independent third-party write-ups — Scott Spence, Medium, pasqualepillitteri.it) but **absent from
public docs** (`plugins-reference.md`, the docs map) and **gated early-access, not enabled for this
account**. What it actually checks: full scenario runs in sandboxed sessions, graded by `regex`,
`tool_used`, `tool_order`, `file_exists`, an `llm` judge (2-of-3 vote), and a `baseline`
with/without comparison — i.e. it's built to test a plugin's _behavior once invoked_, not
specifically description-only cold-trigger matching. `skill-creator` (a separate, related
early-access feature) is the one that's actually purpose-built for this repo's exact problem: it
analyzes a skill's `description` against sample prompts, flags false positives/negatives, and
suggests description rewrites — recommended pattern is **3 eval cases per skill: positive, negative,
edge case**. One third-party source states trigger evals commonly score only ~50% _because
descriptions summarize behavior instead of listing trigger conditions_ — this is exactly the
python-conventions failure mode from Context above, independently confirmed as a common, named
failure pattern, not a one-off.

**`/skill-doctor`**: also gated/undocumented — reports per-skill 7-day token usage, invocation
count, context cost, and never-invoked warnings. Usage-monitoring, not trigger-testing; doesn't
address this plan's problem directly.

**Scoping question (does either apply to this repo's bare `skills/<name>/` layout, not a packaged
plugin)**: still not fully confirmed, but `claude plugin init` can reportedly scaffold a lightweight
`plugin.json` directly into an _existing_ skill directory with no marketplace step — suggesting
conversion cost is low if it turns out to be required. Not verified hands-on.

**Community comparison** (real popularity data, not vibes): **promptfoo** (24,464★, actively
maintained) and **DeepEval** (17,779★, pytest-native, active) are both far more popular than
anything Claude-Code-specific, but neither is built for _cold_ trigger-routing — both test whether a
model calls the right tool correctly _once given full tool definitions in context_ during a live run
(DeepEval's `ToolCorrectnessMetric`/`ArgumentCorrectnessMetric`), which is an adjacent but different
problem from "does the bare description text alone cause selection." Either could be adapted to
simulate cold routing (feed only the description + a battery of prompts, assert the expected
selection), but that means building the harness ourselves on top of a general eval library, not
using an off-the-shelf feature. Anthropic's own "Writing effective tools for AI agents"
engineering-blog guidance is qualitative prose only (avoid jargon, avoid ambiguous parameter names)
— no automated methodology of its own; `skill-creator` is where Anthropic operationalized that
advice into something testable.

## Read hands-on from the CLI (2026-08-29)

The 2026-08-22 pass was desk research against write-ups. `claude plugin eval --help` on this machine
(Claude Code 2.1.251) is the primary source, and it revises two conclusions above.

[DECISION: **the scoping question is answered — a bare `skills/<name>/SKILL.md` layout resolves, and
no `plugin.json` conversion is needed.** The help states a target "is a path, a plugin name, or a
`plugin@marketplace` id — installed and **skills-dir plugins** both resolve (and add a no-plugin
baseline arm)". That removes the concern that Anthropic's own tooling would force this repo into a
vendor manifest format its `AGENTS.md` rules out.]

[DECISION: **`plugin eval` does test cold triggering, contrary to the earlier pass.** The
characterization above — "built to test a plugin's behavior once invoked, not description-only
cold-trigger matching" — was wrong. `--ablation with-without` runs a no-plugin baseline arm and
reports the score delta, and graders marked with-only, **`tool_used: Skill` explicitly named among
them**, are described as "a plugin-fired indicator rather than part of the score". A case whose
grader asserts `tool_used: Skill` is precisely the positive trigger test this plan wants, and the
ablation arm gives the with/without comparison that says what the skill actually changed.]

Also relevant to the cadence question: `--runs` defaults to 3 per case, so non-determinism is
handled by the tool rather than by us; `--threshold <0..1>` exits 1 below the bar, which makes it
CI-gateable; and `--judge-model` defaults to haiku, which bounds the per-run cost.

[PITFALL: **the HTML report publishes to claude.ai by default, and the sensitive material would be
generated at runtime rather than authored by us.** `--report` writes "scores, prompts, grader
verdicts"; `--no-publish` keeps it local; `--publish-report` is "already the default when your
account supports it".

The first version of this note called the exposure low-risk because we author the prompts. That was
the wrong end of the problem, and is corrected here. A trigger test for `plan-docs` has to invoke
`plan-docs`; the first thing the skill instructs is to run `plans.py`; and `list --scope family`,
`doctor` and `repos` all print employer and client names read live from the real projects root.
`--scaffold` is documented as running author-supplied bash **as you**, so these runs are not
isolated from this machine. The material at risk is therefore produced at runtime, by the one skill
in this repo whose commands enumerate every client directory by name — not by anything written into
a case file.

The mitigation is not only `--no-publish`, which treats the symptom. Cases must be written so the
run never reaches the enumerating commands: assert the skill fired and stop. A trigger test needs to
prove selection happened, not that the skill did its job — so the risky output need never exist.]

[NEEDS CLARIFICATION: three things to verify before adopting, none knowable from `--help`. Whether
run transcripts and tool output appear in the report at all or only scores and verdicts (`--verbose`
sends per-message traces to a _debug log_, which hints at the latter but proves nothing). What
visibility a published report has — private to the account, or linkable. And whether the run sandbox
constrains filesystem reads despite scaffold running as the user.]

**The general rule this sits under: data flowing outward to a vendor is a cost, not a neutral
default.** Stated by the user 2026-08-29 while reviewing the above. It applies wider than this tool
— any feature whose default is to upload, publish, or phone home gets the flag pinned to off
deliberately and recorded as a decision, rather than accepted because it was the default. That is
the same stance the store takes by having no remote, and the reason `plans.py` is stdlib-only and
reads nothing off the network.

[UNVERIFIED: **still gated.** `claude plugin eval .` in this repo returns exactly
`` `plugin eval` is currently in early access `` and exits without running, on 2026-08-29 with CLI
2.1.251. So none of the above is usable here yet, and the hand-built harness below remains the live
plan. Re-check on a CLI upgrade before building anything custom: what changed today was the argument
for waiting, not the availability.]

## Recommended direction

**Adopt the trigger-eval methodology `skill-creator` uses — 3 cases per skill (positive, negative,
edge case), checked cold (description text only, fresh context, no prior conversation) — as this
repo's actual testing convention**, independent of whether Anthropic's own gated CLI ends up being
the thing that runs it. This is the only candidate actually purpose-built for the specific failure
already observed (python-conventions under-triggering on jargon-only description text), it has
independent third-party validation of that exact failure mode, and it's cheap to implement as a
small in-repo mechanism rather than adopting a general eval framework as a dependency — consistent
with this repo's existing low-boilerplate bias.

Concretely: for each `skills/<name>/SKILL.md`, author 3 short natural-language prompts (one that
should trigger it, one plausible-but-shouldn't, one boundary/edge case) and check — via a fresh
subagent/API call given _only_ the skill's `description` frontmatter, not its body — whether it
would correctly decide to invoke that skill for each. Where exactly the prompts live (inline in each
`SKILL.md`'s frontmatter? a sibling `<name>.evals.yaml`? one shared file?), how the cold check is
actually invoked (spawn a bare Task/Agent call with just the description text and the full list of
other skill descriptions, matching real trigger conditions; or a direct Anthropic API call from a
script/pytest test — has a real per-run token cost either way, worth deciding budget/cadence for),
and how it is run are all still open — implementation-level design, not resolved by this research
pass.

On that last point, the answer narrowed when the skills moved here. There is no `inv ai.*` in this
repo to wire a check into, and the family convention for skill automation is now a standard-library
Python script inside the skill that owns the concern — so the plausible homes are a script under
`skills/skill-authoring/scripts/` (the skill that owns authoring, including description quality) or
a marked, opt-in test alongside `tests/unit/test_skill_layout.py`. A cold check costs real tokens
per run, so it cannot join the default `pytest` path either way; that is the same
never-auto-triggered-cost stance the rest of the family takes.

**Fallback**, only if the custom in-repo version proves too heavy or the description-only cold-check
harness turns out non-trivial to build well: **promptfoo** over DeepEval — more stars, more mature,
already has function/tool-calling eval primitives to build the cold-routing simulation on top of,
and its YAML test-matrix format is lower-boilerplate than DeepEval's pytest classes even though
DeepEval is pytest-native and this repo already uses pytest.

[NEEDS CLARIFICATION: mechanism for the cold check — a live Agent/Task call each run vs. a direct
Anthropic API call from a plain script or test (same token cost, different plumbing) vs. getting
`claude plugin eval`/`skill-creator` access and using Anthropic's own gated tool once available.
Cadence is the other half and is nearly settled by the cost: on demand, never on install and never
on every CI run, matching the family's stated aversion to auto-triggered spend. "Every install" was
an option when PULSE's `inv ai.install-skills` was the deploy path for skills authored in the same
repo; it is not one now that installs happen through the `skills` CLI from a published remote.]

[NEEDS CLARIFICATION: where do the 3 positive/negative/edge prompts per skill live — inline
frontmatter, a sibling eval file per skill, or one shared corpus file?]

**Resolved 2026-08-26 (user), the cross-skill half of that question: yes, non-contention is a
requirement, not a nice-to-have.** Stated while scoping this repo (`power-user-linux-setup`'s
`plans/2026-08-26-agent-artifact-authoring-decoupling.md`): "skills must be built, as a rule of
thumb, around a clear responsibility and effective trigger conditions that don't contend with
triggers from other skills." That makes the isolated binary check insufficient by design — a skill
whose description wins against a prompt meant for a sibling is a failure even when its own positive
case passes, so any eval harness has to score selection _among_ the installed set, not one
description at a time. It also makes the constraint an authoring rule and not only a testing one,
which is why it now leads this repo's `AGENTS.md` "Authoring a skill" section and the
`skill-authoring` skill, rather than living only here.

That rule has since been exercised on this repo's own contents: `mcp-skill-shipping` was split into
`mcp-server-shipping` and `skill-authoring` precisely because the skill preaching one responsibility
per description was itself two. So the failure mode is confirmed present in authored-in-good-faith
skills, not only hypothetical — which is the argument for a check rather than a convention alone.

The `claude plugin init` conversion question that used to sit here is closed by the 2026-08-29
section above: skills-dir targets resolve directly, so no conversion is needed.

## A first case to test, whenever the harness exists

`plan-docs` gained a new reason to be invoked on 2026-08-29 — "what plans do we have", "what should
I work on next" — and its description was edited to name it
(`plans/2026-08-29-plan-docs-ergonomics.md` records why). That is a concrete, dated positive case
whose before/after is known: the same prompt against the old description should not have selected
the skill, and against the new one should. It is worth being the first case authored here, because
it is the rare one where the expected answer is known independently of the harness being trusted.

The negative case it needs pairing with is `session-harvest`, whose description also covers "what's
worth saving before compacting" — a request about outstanding work that must **not** route to
`plan-docs`. That pair exercises the cross-skill contention requirement stated above, not just the
isolated binary check.
