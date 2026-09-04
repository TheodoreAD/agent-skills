---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-03T11:40:00+03:00
---

# Every skill discloses where it keeps config and what it mutates

## Context

Stated by the user 2026-09-03:

> the skills should contain information about where they keep configs and what mutations they are
> allowed to make. we want to be fully transparent. the authoring skill shouldn't completely
> restrict mutations, but it should heavily scrutinize them, because outside of configuration they
> are dangerous even without bad intentions.

Two requirements, and they are separate: a **disclosure** in every skill, and a **scrutiny test** in
`skill-authoring`. The first is the artifact; the second is the review that decides what the
artifact is allowed to say.

## Read with the location plan — they are two halves of one subject

A parallel session committed `plans/2026-09-03-where-skills-put-things-on-disk.md` in `agent-skills`
within hours of this being filed, and **nothing links them**: different names, neither cites the
other, so `absorb` will not pair them and the next session there gets both without being told they
interlock.

**It is the further-along half.** Re-read 2026-09-03 at 23:43: that plan is pushed and already at
`planned`, with its twelve open questions answered, while this one is still `idea`. Treat its
answers as settled input rather than as a peer draft — which is the opposite of how two same-day
plans on one subject normally read.

They do not overlap, they compose. That plan answers **where** a skill may put things — XDG config
versus data versus state, `$PLANS_HOME`, `$RESEARCH_HOME`, and the fact that `$XDG_DATA_HOME` and
`$XDG_STATE_HOME` appear nowhere in the corpus, which is why two skills have baselines with no home
at all. This plan answers **what a skill says about that, and how authoring scrutinises it**.

**The dependency runs one way and it matters for sequencing: a disclosure names locations, so the
format cannot be finalised before the locations are.** Writing the disclosure for `session-harvest`
first (step 1 below) is still right — it discloses what is true today — but the _shape_ of the
section should be settled against that plan rather than in front of it.

Two facts from it that this plan had assumed settled and are not: `harvest.py` re-implements
`plans.py`'s `PLANS_HOME`/`RESEARCH_HOME` defaults rather than sharing them, and `harvest.py:800`
carries the author's own checkout path as a hard-coded fallback in shipped code. Both are that
plan's to fix; noted here only because a disclosure that named those locations would be describing a
duplicated default as though it were a single one.

## Prior art

Researched 2026-09-03, because this is not a new problem and the ecosystem has moved on it.

**OWASP Agentic Skills Top 10** has it as **AST03 – Over-Privileged Skills**, and it names this
exact file: _"Never request write access to SOUL.md, MEMORY.md, or AGENTS.md unless your skill's
core function requires it — and document why."_ Its guidance is a declared minimal permission
manifest with strictly-listed scopes (`api:github:repo:read`, never open-ended) and risk tiers
L0–L3. Adjacent entries that also apply: **AST04 Insecure Metadata**, **AST07 Update Drift**. A
**Universal Agentic Skill Format v1.0** carries a manifest proposal across Claude Code, Cursor/Codex
and VS Code.

**MCP** already ships the idea as tool annotations — `readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint` — and carries the caveat that decides this plan's shape: _"clients
MUST consider tool annotations to be untrusted unless they come from trusted servers."_

[DECISION: **it is a disclosure, not a permission manifest, and the word matters.** A statement a
skill writes about itself is not a control — nothing checks it, and nothing can. Calling it a
manifest or a permission invites a reader, a reviewer or a future scanner to treat it as
enforcement, which is exactly the failure MCP's caveat is written against. The user's phrasing was
"what mutations they are _allowed_ to make"; the honest form is **what this skill writes, and
where**. Real enforcement is the harness allowlist, which exists, is separate, and is not
self-declared.]

## What a skill discloses

A fixed section, two categories, because they behave differently under the scrutiny test below:

- **Config it owns** — its own file, typically per-machine and unversioned, written through its own
  command. `plan-docs`' `~/.config/plan-docs/config.toml` is the model: the skill tells you never to
  hand-edit it and gives you `config set`.
- **Content it mutates** — repositories, the plans stores, anything else. Named by _kind_, not by a
  path list that will drift.

Four carve-outs, agreed 2026-09-03 with the user, that the disclosure and the scrutiny both assume:

1. The rule is about **file writes and commits**. Non-file side effects — killing an orphaned
   process, pruning a cache — are governed elsewhere and are not what this is aimed at.
2. **A skill may write its own config through its own command**, and says so.
3. **A skill's declared purpose may name another destination** — `scaffoldapy` stamping a new repo,
   `research-library` cloning into `$RESEARCH_HOME`. Stated as a criterion rather than a named
   exception, because there are already two and the second was found by looking.
4. **Both plans stores**, shareable and sensitive — and `plan-docs`' own condition survives: when
   the store is dirty, add a plan rather than editing one another session may be holding.

## The scrutiny test: recoverability, not permission

[DECISION: **the axis `skill-authoring` should apply is what recovers the write, not whether it is
allowed.** "Heavily scrutinize" needs something to scrutinise _against_, and permission is the wrong
question because nobody is granting it. Recoverability is the right one, and it is exactly what
separates "dangerous even without bad intentions" from routine: a write inside a git repo has a
diff, a revert and a history; a write to an unversioned file outside every repository has none. That
is already the class `session-harvest`'s own sweep flags as "files this session edited that no
repository and no store covers" — the same distinction, arrived at from the other end.

So the authoring question per mutation is: **what recovers this?** A mutation with no answer is the
one to justify explicitly or drop. This lets a skill mutate freely inside a repo, which is safe and
common, while putting real weight on the single write to `~/.config` — which is the proportionality
the user asked for and a blanket restriction would not give.]

## Enforcement, and its honest limit

A test in this repo can assert the disclosure **exists** and is well-formed;
`tests/unit/
test_skill_layout.py` already enforces limits of this kind, so there is precedent and a
home.

It cannot assert the disclosure is **true**. That is the MCP caveat applied to ourselves, and it
should be written down rather than discovered later: the disclosure is for a reader deciding whether
to trust the skill, and its value is that it is checkable _by hand_ against the code, not that it is
verified automatically.

## Open questions

[NEEDS CLARIFICATION: **frontmatter or a body section?** Frontmatter is machine-readable, keeps the
test trivial, and is where a future cross-tool format (the Universal Skill Format above) would
expect it. A body section is readable by the agent that loads the skill, which is the audience that
matters at run time, and does not risk the description budget. Possibly both — a short structured
field and a prose section — but that is two things to keep in sync, which is its own failure.]

[NEEDS CLARIFICATION: **does every skill need one, or only mutating ones?** A read-only skill
declaring "writes nothing" is the most useful line in the file for a reader deciding to trust it,
and makes the test uniform. Against: it is noise in a dozen skills that plainly write nothing, and
noise is how a convention stops being read.]

[NEEDS CLARIFICATION: how should this interact with skills.sh's scanners? This disclosure widens the
_stated_ purpose, which is precisely what Socket's `Anomaly` finding on `session-harvest` says is
too narrow (`2026-09-02-skill-risk-ratings-are-user-facing-and-unwatched.md`). Whether a scanner
reads it as reassurance or as a larger declared footprint is unknown and probably unknowable in
advance — worth checking the rating after the first skill discloses, as a one-off measurement rather
than a design input.]

## Recommended direction

1. **Write the disclosure for `session-harvest` first**, since its footprint is the widest, its
   rating is the live question, and it is the skill whose write scope has already been specified —
   `2026-09-03-harvest-writes-only-to-the-session-repo-and-plans.md` is this plan's first instance
   and the two should be absorbed together.
2. **Then the `skill-authoring` section**, stating the recoverability test and the four carve-outs.
   It is short: one question per mutation, and what to do when the answer is nothing.
3. **Then the layout test**, once two or three skills have disclosures and the shape has stopped
   moving. Writing the test first would freeze a format chosen from one example.
4. Do **not** add a rule to `~/AGENTS.md` for this. The disclosure is loaded exactly when the skill
   is, which is a more reliable trigger than an always-loaded sentence; the always-loaded file is at
   39 rules against reference points of ≤15 and its own leanness pass closed by concluding the
   intake gate is the only lever left.
