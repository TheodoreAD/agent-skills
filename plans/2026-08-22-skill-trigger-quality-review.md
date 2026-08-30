---
status: idea
updated: 2026-08-30
---

# Skill triggers: whether a description fires, and whether it steals a sibling's request

Merged 2026-08-30 from three plans on one subject:
`2026-08-29-skill-description-cap-gate-blind-to-wrapped-yaml.md` (the mechanical gate that cannot
see its own violation) and `2026-08-29-trigger-contention-scanner.md` (the cross-skill half), folded
into this one, which owns the per-skill question and holds the research. Both are **merged away and
deleted** — `plans.py archive --show <name>` reads either back.

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
structural check, not a behavioural one — and the next section shows that even that check does not
work.

The risk grew with the repo. When this was written there were six skills in
`power-user-linux-setup`'s `skills/`; there are now ten published here, and the more descriptions
share a corpus the more likely two of them plausibly match the same request.

## The structural gate is blind to the one violation it exists for

`tests/unit/test_skill_layout.py` exists to catch the failure nothing else in the pipeline notices —
a skill that installs cleanly and then never triggers. Its own docstring says so. One of its three
checks does not work.

`parse_frontmatter` scans the frontmatter line by line and skips any line that is indented:

```python
if line.startswith((" ", "\t")) or ":" not in line:
    continue
```

A YAML double-quoted scalar wrapped across several lines therefore contributes only its first
physical line. Every continuation is discarded, and `test_description_is_present_and_within_limit`
measures a fragment rather than the value an agent actually matches on.

Measured 2026-08-29 across all ten skills — the gate's view against the real joined value:

| skill                | gate sees | actual   |
| -------------------- | --------- | -------- |
| `python-conventions` | 611       | **1304** |
| `session-harvest`    | 1000      | 1002     |
| `plan-docs`          | 996       | 998      |
| every other skill    | ≈ actual  | ≈ actual |

`python-conventions` is **280 characters over the documented 1,024-char cap** the test claims to
enforce, and it is the only skill that breaches it. The gate cannot see the one violation it was
written for, and the reason it cannot is that the violation is large enough to have needed wrapping.
Still present on 2026-08-30.

The cap is not this repo's invention: Anthropic's skill-authoring reference states `description`
must be non-empty and at most 1,024 characters, and the file's own comment already records it as the
tightest limit among the agents that read this format.

## The cross-skill half: contention

**Resolved 2026-08-26 (user): non-contention is a requirement, not a nice-to-have.** Stated while
scoping this repo (`power-user-linux-setup`'s
`plans/2026-08-26-agent-artifact-authoring-
decoupling.md`): "skills must be built, as a rule of
thumb, around a clear responsibility and effective trigger conditions that don't contend with
triggers from other skills." That makes an isolated binary check insufficient by design — a skill
whose description wins against a prompt meant for a sibling is a failure even when its own positive
case passes, so any eval harness has to score selection _among_ the installed set, not one
description at a time. It also makes the constraint an authoring rule and not only a testing one,
which is why it leads this repo's `AGENTS.md` "Authoring a skill" section and the `skill-authoring`
skill.

That rule has since been exercised on this repo's own contents: `mcp-skill-shipping` was split into
`mcp-server-shipping` and `skill-authoring` precisely because the skill preaching one responsibility
per description was itself two. So the failure mode is confirmed present in authored-in-good-faith
skills, not only hypothetical — which is the argument for a check rather than a convention alone.

### Vocabulary

Three distinct failures get conflated under "skills competing". Naming them separately is most of
the design, because each has a different detector and a different fix:

| term          | shape                                                 | detector   |
| ------------- | ----------------------------------------------------- | ---------- |
| **overlap**   | two descriptions share trigger vocabulary             | symmetric  |
| **shadowing** | A's trigger set subsumes B's, so B rarely wins        | asymmetric |
| **collision** | the same skill `name` in two scopes; one is invisible | binary     |

"Trigger contention" stays the umbrella term — this repo's `AGENTS.md` already uses it, and the
vendor scanner below calls the same thing "cross-skill description overlap". "Cannibalization" is
borrowed from retail/SEO and implies two things drawing on one pool of demand, which is not the
mechanism; don't adopt it.

### The numbers that make it worth building rather than assuming

Measured 2026-08-29 across 415 Claude Code transcripts on this machine — every `Skill` tool
invocation, all time:

```
58  plan-docs            (largely explicit /plan-docs)
 8  session-harvest
 7  research-library
 5  update-config
 2  invoke-task-conventions
 2  python-conventions
 2  reorder-suggest      (repo-local, freshful-polite-mcp)
 1  session-bash-audit / skill-authoring / db-defaults
 0  mcp-server-shipping
 0  polite-mcp-conventions
```

87 invocations against 15,171 Bash calls. Two skills have never fired. `python-conventions` fired
twice in a repo family that is almost entirely Python, which is the 2026-08-22 prediction above, now
measured rather than suspected — and the over-cap description is the one mechanical defect
measurable today, not proven to be the cause.

Two structural reads of that table, both of which a scanner should surface automatically:

- **Shadowing is visible in the numbers.** `python-conventions` triggers on "writing, reviewing, or
  refactoring Python code", which subsumes adding an invoke task and adding local persistence —
  `invoke-task-conventions` and `db-defaults` sit inside its trigger set. All three are at ≈2.
  Whatever is happening, the narrow skills are not winning their own requests, and the broad one is
  not winning them either.
- **The consequence for the always-loaded file.** `power-user-linux-setup`'s
  `plans/2026-08-26-agents-md-leanness-pass.md` proposes demoting rules out of `~/AGENTS.md` into
  skills to reduce its size. At current trigger rates, demotion is closer to deletion than to
  relocation. That plan needs this one to land first; the dependency runs in that direction and is
  recorded there too.

## Prior art, checked before proposing anything

**`claude plugin eval`**: confirmed real (embedded early-access reference, corroborated by
independent third-party write-ups — Scott Spence, Medium, pasqualepillitteri.it) but **absent from
public docs** and **gated early-access, not enabled for this account**. Read hands-on from `--help`
on 2026-08-29 (Claude Code 2.1.251), which revised two conclusions from the desk-research pass:

[DECISION: **the scoping question is answered — a bare `skills/<name>/SKILL.md` layout resolves, and
no `plugin.json` conversion is needed.** The help states a target "is a path, a plugin name, or a
`plugin@marketplace` id — installed and **skills-dir plugins** both resolve (and add a no-plugin
baseline arm)". That removes the concern that Anthropic's own tooling would force this repo into a
vendor manifest format its `AGENTS.md` rules out.]

[DECISION: **`plugin eval` does test cold triggering, contrary to the earlier pass.** The earlier
characterization — "built to test a plugin's behavior once invoked, not description-only cold-
trigger matching" — was wrong. `--ablation with-without` runs a no-plugin baseline arm and reports
the score delta, and graders marked with-only, **`tool_used: Skill` explicitly named among them**,
are described as "a plugin-fired indicator rather than part of the score". A case whose grader
asserts `tool_used: Skill` is precisely the positive trigger test this plan wants, and the ablation
arm gives the with/without comparison that says what the skill actually changed.]

Also relevant to the cadence question: `--runs` defaults to 3 per case, so non-determinism is
handled by the tool rather than by us; `--threshold <0..1>` exits 1 below the bar, which makes it
CI-gateable; and `--judge-model` defaults to haiku, which bounds the per-run cost.

[PITFALL: **the HTML report publishes to claude.ai by default, and the sensitive material would be
generated at runtime rather than authored by us.** `--report` writes "scores, prompts, grader
verdicts"; `--no-publish` keeps it local; `--publish-report` is "already the default when your
account supports it".

The first version of this note called the exposure low-risk because we author the prompts. That was
the wrong end of the problem. A trigger test for `plan-docs` has to invoke `plan-docs`; the first
thing the skill instructs is to run `plans.py`; and `list --scope family`, `doctor` and `repos` all
print employer and client names read live from the real projects root. `--scaffold` is documented as
running author-supplied bash **as you**, so these runs are not isolated from this machine. The
material at risk is therefore produced at runtime, by the one skill in this repo whose commands
enumerate every client directory by name — not by anything written into a case file.

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
the same stance the store takes with its sensitive tier, and the reason `plans.py` is stdlib-only
and reads nothing off the network.

[UNVERIFIED: **still gated.** `claude plugin eval .` in this repo returns exactly
`` `plugin eval` is currently in early access `` and exits without running, on 2026-08-29 with CLI
2.1.251. So none of it is usable here yet. Re-check on a CLI upgrade before building anything
custom: what changed that day was the argument for waiting, not the availability.]

**`skill-creator`** (a separate, related early-access feature) is the one purpose-built for the
per-skill question: it analyzes a skill's `description` against sample prompts, flags false
positives/negatives, and suggests rewrites — recommended pattern is **3 eval cases per skill:
positive, negative, edge case**. One third-party source states trigger evals commonly score only
~50% _because descriptions summarize behavior instead of listing trigger conditions_, which is
exactly the `python-conventions` failure mode above, independently confirmed as a common named
pattern rather than a one-off.

**`/skill-doctor`**: gated, undocumented — reports per-skill 7-day token usage, invocation count,
context cost, and never-invoked warnings. Usage-monitoring, not trigger-testing. Item 7 below is the
same signal computed locally from the transcript store, with no gate and no window limit.

**An AI-security vendor's open-source `skill-scanner`** — searchable by its
`scan-all --recursive --check-overlap` invocation and its "cross-skill description overlap checks"
wording, which is enough to find it in one query. The vendor is deliberately not named here: its
name is also a work root on the authoring machine, so `scan` flags it, and the scanner cannot tell a
citation of a public project from a disclosure of who someone works for. Evaluate it before writing
a line. Caveats from the docs pass: it is security-framed (prompt injection, data exfiltration,
malicious payloads), the overlap mechanic is undocumented — lexical or embedding, unstated — and it
knows nothing about `AGENTS.md` or about scopes. Expect it to cover item 3 below and nothing else,
but confirm rather than assume.

**Community eval frameworks**: **promptfoo** (24,464★, actively maintained) and **DeepEval**
(17,779★, pytest-native, active) are both far more popular than anything Claude-Code-specific, but
neither is built for _cold_ trigger-routing — both test whether a model calls the right tool
correctly _once given full tool definitions in context_ during a live run (DeepEval's
`ToolCorrectnessMetric`/`ArgumentCorrectnessMetric`). Either could be adapted to simulate cold
routing, but that means building the harness ourselves on top of a general eval library. Anthropic's
own "Writing effective tools for AI agents" engineering-blog guidance is qualitative prose only;
`skill-creator` is where Anthropic operationalized it into something testable.

The split that falls out: **a static analyzer is not competing with any of those.** It is cheap,
deterministic, CI-gateable and answers questions none of them asks. Build it first; reach for the
eval second, for the questions only a live run can answer.

## Open questions

[NEEDS CLARIFICATION: fix the frontmatter parser, or take the YAML dependency? The module's
docstring argues against PyYAML — "it is a flat `key: value` block by the format's own spec, and
adding PyYAML to a repo whose only Python is this file buys nothing". That reasoning is what the bug
disproves: the block is not flat, because a value long enough to matter gets wrapped. A ~10-line
continuation-aware scan keeps the no-dependency stance; PyYAML makes the parser correct by
construction and would also catch a malformed block the scan silently tolerates. The no-dependency
version is probably right, but the docstring's justification has to be rewritten either way, since
it is now on record as the cause.]

[NEEDS CLARIFICATION: what happens to `python-conventions` once the gate can see it? The description
does not shrink to 1,024 by trimming filler — it is a list of covered topics, and cutting topics off
the end removes trigger vocabulary, which is the opposite of what this plan wants. The likelier
answer is that the skill is over-scoped rather than over-described, and the fix is a split. Do not
let the gate turn green by deleting trigger terms.]

[NEEDS CLARIFICATION: does any agent actually truncate at 1,024, and where? Claude Code was observed
loading the full 1,304-character description into a session's skill listing, so it does not enforce
the cap at read time. Whether the `skills` CLI, the API skill upload path, or another agent silently
truncates is unverified. It changes the severity — a hard truncation means the tail of
`python-conventions`' trigger vocabulary is already invisible in some places — but not the fix.]

[NEEDS CLARIFICATION: where does the scanner live? `skills/skill-authoring/scripts/` is the strong
default — that skill already owns description quality, and the family convention is a stdlib Python
script inside the skill that owns the concern. Explicitly **not** a new skill: a skill for detecting
skill contention would contend with `skill-authoring` on every request about skill quality, which is
the joke version of the bug it detects. The one argument for a separate home is that it also reads
`AGENTS.md` files, which `skill-authoring` does not otherwise touch.]

[NEEDS CLARIFICATION: which similarity measure, and what threshold? Whole-description cosine is easy
and wrong-ish — descriptions carry both "what it does" prose and "when to use it" triggers, and only
the second should count. Extracting the trigger clause (the "Use when …" span, quoted terms, the
comma-separated topic list) and comparing those sets is more precise and more brittle. A threshold
set by hand on a corpus of ten will not survive twenty. Consider reporting a ranked pair list with
no threshold at all — a scanner that ranks is useful at any corpus size, one that gates needs a
calibrated number nobody has yet.]

[NEEDS CLARIFICATION: how are scopes enumerated portably? User scope is `~/.agents/skills` (plus the
Claude Code symlink and Windsurf's own path); repo scope is `<repo>/.agents/skills`; "every repo"
means walking a projects root, which is `plan-docs`' job and not this script's. Taking a list of
roots as an argument keeps the two skills from duplicating discovery, at the cost of the caller
having to supply it.]

[NEEDS CLARIFICATION: does the `AGENTS.md` half belong in the same script? Item 5 below compares
rule headings against skill descriptions, which is a genuinely different corpus and a different
failure (duplication and demotion-readiness, not selection). Keeping them together is what makes the
always-loaded budget report (item 6) possible in one call, which is the number nobody currently
has.]

[NEEDS CLARIFICATION: is the invocation counter (item 7) too Claude-Code-specific for this repo?
`session-bash-audit` already reads `~/.claude/projects/*.jsonl` and states plainly that it does, so
precedent exists and the skill declares its assumption rather than hiding it. But a scanner whose
most valuable signal only works on one harness reports less on every other, and this repo's whole
premise is vendor neutrality.]

[NEEDS CLARIFICATION: where do the 3 positive/negative/edge prompts per skill live — inline
frontmatter, a sibling eval file per skill, or one shared corpus file? And the mechanism for the
cold check: a live Agent/Task call each run, a direct Anthropic API call from a plain script or
test, or Anthropic's own gated tool once available. Cadence is nearly settled by the cost: on
demand, never on install and never on every CI run, matching the family's aversion to auto-triggered
spend.]

## Recommended direction

In this order — cheapest and most certain first.

1. **Make the structural gate honest.** Continuation-aware frontmatter parse, plus a regression case
   asserting a wrapped value is measured whole, so the bug does not return the next time someone
   simplifies the scanner. Test the parser, not just the skills, so the case survives a corpus where
   nothing happens to be wrapped. Then look at the failure it exposes, which is item 2's territory,
   not the gate's.

2. **Build the static analyzer: zero tokens, deterministic, runnable in CI.** What it should
   compute, roughly in order of worth:

   1. **Inventory across scopes** — user, each repo, plus every `AGENTS.md` in scope. Everything
      else is a view over this.
   2. **Name collisions across scopes** — binary, cheap, and silent when it happens: one of the two
      is simply never seen.
   3. **Pairwise overlap**, ranked, not gated. Report the shared trigger terms alongside the score,
      since the terms are what gets rewritten.
   4. **Shadowing** — subsumption of one trigger set by another, reported directionally. This is the
      one the current corpus actually exhibits.
   5. **`AGENTS.md` rule-heading ↔ skill-description matches.** A hit is either a demotion candidate
      or a two-sources-of-truth risk, and the scanner should not guess which.
   6. **Always-loaded budget** — total bytes of every in-scope `AGENTS.md` plus the sum of all
      descriptions. Two ceilings worth printing against: Codex CLI's silent 32 KiB `AGENTS.md`
      truncation, and the 1,024-char per-description cap.
   7. **Invocation reality**, from the transcript store: never-invoked skills, and explicit-slash
      versus auto-triggered where the transcript distinguishes them. This is the signal that catches
      "published, installed, never triggered" — the exact failure `test_skill_layout.py` says it
      exists for and cannot see.

3. **Then the cold-routing evaluation**, adopting the methodology `skill-creator` uses — 3 cases per
   skill (positive, negative, edge), checked cold against description text only in fresh context —
   but scored **among the installed set** rather than one description at a time. The static pass
   tells you which pairs to write cases for, which is the difference between three cases per skill
   and three cases per suspicious pair. Homes: a script under `skills/skill-authoring/scripts/`, or
   a marked opt-in test alongside `tests/unit/test_skill_layout.py`. A cold check costs real tokens
   per run, so it cannot join the default `pytest` path either way.

   **Fallback**, only if the custom harness proves too heavy: **promptfoo** over DeepEval — more
   mature, already has function/tool-calling eval primitives to build cold-routing on, and its YAML
   test-matrix format is lower-boilerplate than DeepEval's pytest classes.

[DEFERRED: item 2.7 distinguishes explicit `/skill-name` invocations from model-chosen ones only if
the transcript records the difference. Unverified — the counts above do not separate them, and
`plan-docs`' 58 is almost certainly dominated by explicit calls, which would mean the auto-trigger
rate across the whole corpus is lower than the table already suggests. Check before quoting these
numbers as trigger rates.]

[UNVERIFIED: the vendor `skill-scanner`'s `--check-overlap` has not been run against this corpus.
Every statement above about its scope comes from its README, not from a run. Run it first — the
outcome could remove items 2.3 and 2.4 from this plan entirely.]

## A first case to test, whenever the harness exists

`plan-docs` gained a new reason to be invoked on 2026-08-29 — "what plans do we have", "what should
I work on next" — and its description was edited to name it
(`plans/2026-08-29-plan-docs-ergonomics.md` records why). That is a concrete, dated positive case
whose before/after is known: the same prompt against the old description should not have selected
the skill, and against the new one should. It is worth being the first case authored here, because
it is the rare one where the expected answer is known independently of the harness being trusted.

The negative case it needs pairing with is `session-harvest`, whose description also covers "what's
worth saving before compacting" — a request about outstanding work that must **not** route to
`plan-docs`. That pair exercises the cross-skill contention requirement, not just the isolated
binary check.
