---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/invoke-stubs
source_session: 65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl
source_moment: 2026-09-07T12:02:09Z
---

# A skill for writing type stubs for a third-party package

## Context

`invoke-stubs` is a complete worked example of a job with no settled answer anywhere: a PEP 561 stub
distribution for a package whose maintainers ship annotations that are absent in places and wrong in
others. Everything below was learned by getting it wrong first, in that repo, across sessions on
2026-08-30, 09-06 and 09-07. None of it is invoke-specific, and none of it is in a form the next
"can you write stubs for X" session would find.

The trigger for this plan is that the same job is now plausible for other packages in the family,
and the expensive parts were not the stubs — they were the four or five decisions that look free and
are not, each of which cost a session to discover.

**Do not start it until `invoke-stubs` has stabilised.** That is not caution for its own sake: the
`~/AGENTS.md` rule is that conventions are piloted on one real working repo before they are written
into a shareable artifact, and this repo is mid-pilot. As of 2026-09-07 it has just shipped 0.3.0,
whose consumer cleanup has not happened yet, and two of its own verification items are still owed by
other repos. Writing the skill now would freeze guesses about which parts generalise. The start
condition is concrete: 0.3.0 consumed by `repo-tasks` with its casts removed, `ingesta`'s
suppression count measured after taking it, and no open `UNVERIFIED` tag in
`invoke-stubs/plans/2026-08-30-missing-collection-and-context-stubs.md`.

## Evidence

Session `65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-invoke-stubs/`, 2026-09-07, asked
for this with "write a plan to create a skill for making stubs for 3rd party packages based on all
the learnings from the sessions in this repo after we are stablize this". The learnings themselves
are in that repo, not in the transcript:

- `AGENTS.md` — the standing rules, including the four deliberate departures and why the marker
  stays `partial`.
- `plans/2026-08-30-missing-collection-and-context-stubs.md` — the design, four `DECISION` tags,
  seven `PITFALL` tags, and the verification list. The single richest source.
- `plans/2026-09-07-consumer-verification-of-0-2-0.md` — what a consumer actually felt, and the
  `Lexicon` decision.
- `plans/2026-08-30-stub-gaps-and-upstream.md` — the upstream-contribution question, and the "two
  gaps is a stub doing its job, three is a stub becoming a project" trigger that fired.
- `tests/` — the checks, which are the executable form of most of the rules below.

## What the skill would carry

Grouped by the question a session arrives with, not by the order it was learned in.

**Does this package need stubs at all, and how much?**

- The measurement that justifies the work is the consumer's suppression count, not the stub's
  surface. It went 4 → 59 `# pyright: ignore` across five task modules before anyone acted.
- A stub distribution exists to be deleted. Check whether upstream has moved before starting, and
  keep a revisit trigger — invoke shipped typing in 3.0 that made the distribution's case
  _stronger_, not weaker, because what shipped was wrong in a way three users had already reported.

**What shape does the package take?**

- **Never inline a class declaration in `__init__.pyi`.** The same class reached by two import paths
  becomes two nominal types, and the diagnostic names both of them the same thing. Sibling modules
  keep one identity.
- **A sibling stub shadows its whole module.** There is no per-member merging, so a partial
  `collection.pyi` deletes every member it does not name, including ones that worked before it
  existed. "Which members are worth declaring" is not a question.
- **The module set is a transitive closure, not a list** — a return type drags in the module that
  defines it. Compute it rather than picking a consumer-facing subset.
- **`partial` versus a full marker is a decision with a measurement behind it**, and it went the
  opposite way to the plan: the modules are what make stubs authoritative, and emptying the marker
  only removes the fallback that is silently working for everything not shipped.

**Generating them**

- `basedpyright --createstub` drops every attribute a class assigns to `self` — 47 across 13 classes
  — while emitting methods and properties, so the result reads as complete. An AST pass over the
  package's own source is the only way to find them, and it wants to be a standing check rather than
  a one-off, since it also catches the next upstream release adding one.
- Run the generator in a virtualenv holding the target package **and not the stubs**, or it stubs
  the stubs.
- Post-processing that is always wanted: docstrings out, `Optional[X]` to `X | None`, `typing.List`
  to builtins, bare `PathLike` parameterized.

**Departing from upstream deliberately**

- The rule is to mirror, and the exceptions are the reason the distribution exists: an annotation
  that rejects valid code (`DataProxy.__setitem__` typed `str` where the runtime takes anything),
  one that fails a protocol (`__exit__` without `| None`), and a bare container that hands the
  consumer `Any` (`Lexicon`).
- Each departure is commented in place _and_ listed centrally, because a regeneration reverts it and
  the in-place comment is invisible to whoever is deciding whether to add a fifth.
- `Any` reaching a consumer is not a neutral outcome: it produces casts, and casts get copied into
  the next consumer rather than fixed once. No rule flags a redundant cast afterwards.

**Verifying**

- **Two environments, target present and target absent**, are the whole subject rather than
  scaffolding. Most of what a stub gets wrong is invisible in one of them.
- **Type-check the stub package against itself** — cheapest check, and it found a protocol failure
  no consumer probe reaches.
- **A usage probe must `assert_type`, not call.** `Any` satisfies every call and every annotated
  assignment, so a probe written from what consumers do passes against the exact defect it was
  written for.
- **A probe written from what consumers use tests the names you thought of.** Generate the import
  list from the package's own `__init__` rather than hand-listing, or a name upstream re-exports
  from the wrong module ships broken.
- **A check has to be shown failing**, on the defect it was written for. One shipped broken here,
  matching by substring, and three other checks caught the defect it was written to catch.
- **A check that globs is only as good as its glob.** The attribute check was flat and a whole
  subpackage was outside every run for a week — 19 missing attributes.
- **A hand-edited probe venv stops being evidence and says so in no way at all.** Rebuild fresh for
  any run that would change a decision.
- **Run the second type checker.** mypy's handling of a `partial` marker is the thing the marker
  decision rests on, and it went unexercised while the README claimed support.
- The end-to-end test lives in a real consumer repo, and no probe replaces it.

**Shipping**

- Installed by git URL means a push to `main` is a release, and a version bump is what gives
  `uv lock --upgrade-package` something to move to.
- The consumer that most needs the stubs may be unable to install the runtime package at all — here,
  a second `inv` on `PATH` shadows a globally installed tool. That constraint is what the "target
  absent" environment is testing.

## Open questions

[NEEDS CLARIFICATION: one skill or two? The list above splits cleanly into _deciding and designing a
stub distribution_ and _the checks that keep one honest_, and the second half is much closer to
executable code than to prose. A single skill risks being the kind of long document that gets
skimmed past its own most expensive rules.]

[NEEDS CLARIFICATION: how much of it is code rather than instructions? At least four checks —
attribute parity, re-export resolution, stubs-as-source, the two-environment probe — are generic
over any package once the package name is a parameter. `agent-skills` skills can carry `scripts/`,
so the question is whether this ships as a skill with a script that generates a test suite, or as
prose telling the session what to write. The `skill-fitness` skill's rule about repeated one-off
scripts argues for the former.]

[NEEDS CLARIFICATION: does `scaffoldapy` want a stub-distribution template, given the repo layout
here is now settled (stub package, two test tiers, canonical configs, no runtime code)? That is a
different artifact from a skill and might make the skill much shorter — or might be premature at one
instance.]

[NEEDS CLARIFICATION: what triggers it? "Write stubs for X" is the obvious phrasing, but the more
valuable trigger is earlier — a session about to suppress the same diagnostic for the third time in
a consumer repo. Wording that without stealing requests belonging to the Python conventions skill
needs care.]

## Recommended direction

Wait for the start condition above, then harvest from the four documents named in Evidence in one
pass rather than from memory — they are already written and the `DECISION`/`PITFALL` tags mark
exactly the passages worth carrying. Draft as one skill with a `references/` split, decide the
one-versus-two question against the finished draft rather than in advance, and follow the
`skill-authoring` sequence, whose most-skipped step is the push.

One thing to check before drafting: whether typeshed's own contribution guide already documents half
of this. It is the obvious prior art, the `~/AGENTS.md` rule about checking for an actively
maintained external artifact applies, and the skill is worth much less if it restates a document
upstream maintains — it would then be the thin layer of what typeshed does not cover, which is
mostly the two-environment verification and the shipping mechanics.
