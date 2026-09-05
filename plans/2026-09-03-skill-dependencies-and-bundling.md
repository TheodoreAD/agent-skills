---
status: idea
updated: 2026-09-03
---

# Whether a skill may depend on another, and whether skills come in bundles

## Context

Raised by the user 2026-09-03, with an explicit invitation to push back: some skills might depend on
others and should look for the dependency and use it if present. Which raises whether a skill should
ever be installed without its neighbours, and whether skills should ship as a bundle.

The invitation is taken. **Optional runtime dependency detection between skills is a bad idea, and
the need behind it is real but splits into two halves that want opposite answers.**

## Why "use it if it is installed" should be refused

**1. It makes behaviour depend on what else is installed — the failure already measured here.** On
2026-09-02, under a fake `HOME` with two of fourteen skills present, `plan-docs`' portability
finding count fell from 1 to 0. Nothing about `plan-docs` changed; the repo name that produced the
finding left the derived vocabulary because the skill that linked it was absent. That was called
indefensible in a reader-facing report and it is the same defect here, promoted from a number to a
behaviour. Two installs, two behaviours, and a bug report nobody can reproduce.

**2. Importing a sibling means hard-coding the hub path** — `~/.agents/skills/<name>/scripts/…` —
the exact assumption deleted from `harvest.py` on 2026-09-03 under the rule that no script
hard-codes a local path. It also breaks for every non-hub corpus: a checkout, a `--root`, a fork,
the `tests/fixtures` tree. A rule cannot be enforced in one file and re-introduced in the next.

**3. Version skew, with nothing to detect it.** Skills are **copied**, never symlinked, installed
individually, and a `--global` install writes no lockfile (verified 2026-09-02: none under `~`,
`~/.agents`, `~/.claude`). So `session-harvest` from January would call `plans.py` from June across
an unversioned boundary with no declared contract — a distributed monolith assembled by a file
copier.

**4. The ecosystem does not model it.** There is no dependency field in the skill format, no
resolver, no lockfile for the global case. Building detection means inventing a package manager on
top of a copier, and owning it forever.

## The need is real, and it is two different needs

[DECISION: **shared _code_ is duplicated, not depended on.** The XDG path resolver is about ten
lines of stdlib against a specification that has not changed in a decade. Copying it into each skill
that needs it costs almost nothing and preserves the property the whole corpus is built on — a skill
is a self-contained unit that can be read, copied or vendored on its own. A little copying is
cheaper than a little dependency, and this is the cheapest copying available.]

[DECISION: **shared _location_ is a contract, not a call — and this corrected rule 9 of the
now-retired `plans/2026-09-03-where-skills-put-things-on-disk.md`.** That rule said "one skill owns
a location; the others ask it rather than re-deriving it", which reads as "call the owner" and is
wrong for exactly the reasons above; the correction is what `skill-authoring`'s "share a
**location** as configuration both read" now says. The right form: **one skill owns the location and
publishes it as configuration the others read.** `$PLANS_HOME` and `~/.config/plan-docs/config.toml`
already are that contract, so `harvest.py` does not need to import `plans.py` — it needs to read the
same environment variable and the same config file. That is not duplicated logic; it is two readers
of one source of truth, which is how independently-installed tools have always shared state.]

[DECISION: **optional _invocation_ stays, because the agent is the integration layer.** A skill's
prose may tell the agent to run a sibling's script when it is present — `session-harvest` already
does this for `session-bash-audit`'s `audit.py`. This is safe where an import is not: the agent
checks, and says "not installed, skipping" rather than silently producing a different answer. The
requirement is that the skipping is **stated**, never silent, so the reader knows which sections
they did not get.]

## Should a skill ever be installed without its neighbours — and should there be bundles

[DECISION: **no forced bundles, and the reason is measured rather than aesthetic.** The skill
listing is a character budget: this corpus's fourteen skills cost **10,957 characters** against the
**8,000** a 200k-context model gets, before the harness's own exempt entries are charged. So
installing skills a reader did not ask for is a direct, permanent context tax on every session they
run, and it pushes their own skills toward description-truncation — the death spiral `budget` exists
to report. Published measurement points the same way: two to three skills applied to one task beat
four or more (+18.6pp against +5.9pp). Someone who wants `db-defaults` should get `db-defaults`.]

[NEEDS CLARIFICATION: **a documented _suggested set_ is a claim of the kind this corpus measures,
and the measurement does not exist yet.** "These skills work well together" is a statement about
which skills co-fire on one task — and the governing rule here is that nothing ships unmeasured,
which is what separates a curated skill (+16.2pp) from an unaided one (−1.3pp). Writing the sentence
from intuition is the failure mode, not the wording.

It is cheap to measure and currently impossible: `Usage` keeps `tool_calls`, `explicit`,
`last_seen`, a session **count** and an availability flag — no per-session set of names, so
co-occurrence cannot be computed from what the scanner retains. The scanner already walks each
transcript and records every skill it sees, so keeping a set per session is a few lines.

The measurement has a purpose beyond the README line, which is what makes it worth taking: published
work puts **two to three skills on one task at +18.6pp against +5.9pp for four or more**. So the
question is not "which skills are related" — the names answer that — but **which sets actually fire
together, and whether any task is pulling in four**. A task that routinely does is an argument for
sharpening a boundary, and that finding is unreachable without the same data.

[PITFALL: co-occurrence measured from `tool_calls` alone **undercounts**. `explicit` is a person
typing `/name`, which often injects the body directly and produces no tool call at all — measured
2026-08-30, one skill ran 11 auto against 84 explicit. A co-firing set built from the auto column
would describe the sessions where nobody typed a slash command.]

So: leaning yes on the sentence, but only after the measure exists. If it turns out there are no
natural sets, that is also an answer and a better one than a guess.]

[DECISION: **`metadata: family:` is half a taxonomy and should be completed or dropped — recommend
dropped.** The state of it, read 2026-09-04 rather than recalled:

- **5 of 14 skills carry it**: `python` on four, `meta` on one. The other nine have no `metadata`
  block at all, and there is no answer to what family `db-defaults` or `plan-docs` belongs to.
- **Nothing reads it.** Every `family` hit across the scripts is `plan-docs`' unrelated
  `--scope family`, and `tests/unit/test_skill_layout.py` does not validate it — so it cannot even
  drift, because nothing would notice.
- **It is not a spec field being honoured.** The reference corpus in the research library
  (`anthropics/skills`) uses no such key; `metadata` appears there only in a benchmark schema and in
  MCP prose. This is a local invention.
- **The word already means something else here.** `family` in this corpus means "every repo on the
  machine". Two meanings of one word inside one corpus is a cost paid by every future reader.

It costs no listing budget — the listing is name plus description — so the only cost is a reader
believing it means something. That is enough. A half-covered taxonomy is worse than none: it implies
a scheme that was never finished. Completing it is the other coherent option, but the README's scope
table already does the human-hint job better, and the decision above forbids any tool reading it,
which leaves the field with no job to do.]

## Recommended direction

Refuse dependency detection. Duplicate the resolver. Fix rule 9 to say **config, not call**. Keep
agent-mediated optional invocation, with the skip stated out loud. Ship no bundles, and consider one
README sentence naming sets that work well together.
