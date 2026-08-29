---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

## Context

Filed from a `power-user-linux-setup` session that audited how `~/AGENTS.md` and the installed
skills divide responsibility. Not written into this repo's tree because the session did not own it.

This is the cross-skill, cross-scope half of `plans/2026-08-22-skill-trigger-quality-review.md`,
which owns the per-skill question ("does this description fire on the requests it should?"). That
plan already records the user's 2026-08-26 resolution that non-contention is a requirement, and
notes that an isolated binary check is therefore insufficient by design — a skill whose description
wins a request meant for a sibling has failed even when its own positive case passes. What it does
not have is a mechanism, and it is scoped to one repo's ten skills, while skills now arrive from
three places at once. Read the two together; consolidate if a session prefers one file.

### Vocabulary

Three distinct failures get conflated under "skills competing". Naming them separately is most of
the design, because each has a different detector and a different fix:

| term          | shape                                                 | detector   |
| ------------- | ----------------------------------------------------- | ---------- |
| **overlap**   | two descriptions share trigger vocabulary             | symmetric  |
| **shadowing** | A's trigger set subsumes B's, so B rarely wins        | asymmetric |
| **collision** | the same skill `name` in two scopes; one is invisible | binary     |

"Trigger contention" stays the umbrella term — this repo's `AGENTS.md` and the 2026-08-22 plan
already use it, and the vendor scanner in the prior-art section below calls the same thing
"cross-skill description overlap". "Cannibalization" is borrowed from retail/SEO and implies two
things drawing on one pool of demand, which is not the mechanism; don't adopt it.

### Why it is worth building rather than assuming

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
twice in a repo family that is almost entirely Python, which is the 2026-08-22 prediction, now
measured rather than suspected.

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

### Prior art, checked before proposing anything

- **An AI-security vendor's open-source `skill-scanner`** — searchable by its
  `scan-all --recursive --check-overlap` invocation and its "cross-skill description overlap checks"
  wording, which is enough to find it in one query. The vendor is deliberately not named here: its
  name is also a work root on the authoring machine, so `scan` flags it, and the scanner cannot tell
  a citation of a public project from a disclosure of who someone works for. Evaluate it before
  writing a line. Caveats from the docs pass: it is security-framed (prompt injection, data
  exfiltration, malicious payloads), the overlap mechanic is undocumented — lexical or embedding,
  unstated — and it knows nothing about `AGENTS.md` or about scopes. Expect it to cover item 3 below
  and nothing else, but confirm rather than assume.
- **`claude plugin eval`** — read hands-on 2026-08-29 and recorded in the 2026-08-22 plan: a
  skills-dir layout resolves with no `plugin.json`, and `--ablation with-without` plus a
  `tool_used: Skill` grader is a genuine cold-trigger test. That is the _behavioural_ half. It costs
  tokens per run and publishes a report by default. It does not enumerate scopes, does not read
  `AGENTS.md`, and cannot tell you that two skills have never fired in six weeks.
- **`/skill-doctor`** — gated, undocumented, reports 7-day usage and never-invoked warnings. Item 7
  below is the same signal computed locally from the transcript store, with no gate and no window
  limit.

The split that falls out: **a static analyzer is not competing with either of those.** It is cheap,
deterministic, CI-gateable and answers questions neither one asks. Build it first; reach for the
eval second, for the questions only a live run can answer.

## Open questions

[NEEDS CLARIFICATION: where does it live? `skills/skill-authoring/scripts/` is the strong default —
that skill already owns description quality, and the family convention is a stdlib Python script
inside the skill that owns the concern. Explicitly **not** a new skill: a skill for detecting skill
contention would contend with `skill-authoring` on every request about skill quality, which is the
joke version of the bug it detects. The one argument for a separate home is that it also reads
`AGENTS.md` files, which `skill-authoring` does not otherwise touch.]

[NEEDS CLARIFICATION: which similarity measure, and what threshold? Whole-description cosine is easy
and wrong-ish — descriptions carry both "what it does" prose and "when to use it" triggers, and only
the second should count. Extracting the trigger clause (the "Use when …" span, quoted terms, the
comma-separated topic list) and comparing those sets is more precise and more brittle. A threshold
set by hand on a corpus of ten will not survive twenty. Consider reporting a ranked pair list with
no threshold at all, and letting the reader draw the line — a scanner that ranks is useful at any
corpus size, one that gates needs a calibrated number nobody has yet.]

[NEEDS CLARIFICATION: how are scopes enumerated portably? User scope is `~/.agents/skills` (plus the
Claude Code symlink and Windsurf's own path); repo scope is `<repo>/.agents/skills`; "every repo"
means walking a projects root, which is `plan-docs`' job and not this script's. Taking a list of
roots as an argument keeps the two skills from duplicating discovery, at the cost of the caller
having to supply it.]

[NEEDS CLARIFICATION: does the `AGENTS.md` half belong here at all? Item 5 below compares rule
headings against skill descriptions, which is a genuinely different corpus and a different failure
(duplication and demotion-readiness, not selection). It may deserve its own script. Keeping them
together is what makes the always-loaded budget report (item 6) possible in one call, which is the
number nobody currently has.]

[NEEDS CLARIFICATION: is the invocation counter (item 7) too Claude-Code-specific for this repo?
`session-bash-audit` already reads `~/.claude/projects/*.jsonl` and states plainly that it does, so
precedent exists and the skill declares its assumption rather than hiding it. But a scanner whose
most valuable signal only works on one harness is a scanner that reports less on every other, and
this repo's whole premise is vendor neutrality.]

## Recommended direction

Rough, and contingent on the above. **Static first, zero tokens, deterministic, runnable in CI.**

What it should compute, roughly in order of how much each is worth:

1. **Inventory across scopes** — user, each repo, plus every `AGENTS.md` in scope. Everything else
   is a view over this.
2. **Name collisions across scopes** — binary, cheap, and silent when it happens: one of the two is
   simply never seen.
3. **Pairwise overlap**, ranked, not gated (see the open question). Report the shared trigger terms
   alongside the score, since the terms are what gets rewritten.
4. **Shadowing** — subsumption of one trigger set by another, reported directionally. This is the
   one the current corpus actually exhibits.
5. **`AGENTS.md` rule-heading ↔ skill-description matches.** A hit is either a demotion candidate or
   a two-sources-of-truth risk, and the scanner should not try to guess which.
6. **Always-loaded budget** — total bytes of every in-scope `AGENTS.md` plus the sum of all
   descriptions. Two ceilings worth printing against: Codex CLI's silent 32 KiB `AGENTS.md`
   truncation, and the 1,024-char per-description cap.
7. **Invocation reality**, from the transcript store: never-invoked skills, and explicit-slash
   versus auto-triggered where the transcript distinguishes them. This is the signal that catches
   "published, installed, never triggered" — the exact failure `tests/unit/test_skill_layout.py`
   says it exists for and cannot see.

Then, and only then, the cold-routing evaluation from
`plans/2026-08-22-skill-trigger-quality-review.md`, scored **among the installed set** rather than
one description at a time. The static pass tells you which pairs to write eval cases for, which is
the difference between three cases per skill and three cases per suspicious pair.

[DEFERRED: item 7 distinguishes explicit `/skill-name` invocations from model-chosen ones only if
the transcript records the difference. Unverified — the counts above do not separate them, and
`plan-docs`' 58 is almost certainly dominated by explicit calls, which would mean the auto-trigger
rate across the whole corpus is lower than the table already suggests. Check before quoting these
numbers as trigger rates.]

[UNVERIFIED: the vendor `skill-scanner`'s `--check-overlap` has not been run against this corpus.
Every statement above about its scope comes from its README, not from a run. Run it first — the
outcome could remove items 3 and 4 from this plan entirely.]
