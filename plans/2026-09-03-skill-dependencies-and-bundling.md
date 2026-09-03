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

[DECISION: **shared _location_ is a contract, not a call — and this corrects rule 9 of
`2026-09-03-where-skills-put-things-on-disk.md`.** That rule says "one skill owns a location; the
others ask it rather than re-deriving it", which reads as "call the owner" and is wrong for exactly
the reasons above. The right form: **one skill owns the location and publishes it as configuration
the others read.** `$PLANS_HOME` and `~/.config/plan-docs/config.toml` already are that contract, so
`harvest.py` does not need to import `plans.py` — it needs to read the same environment variable and
the same config file. That is not duplicated logic; it is two readers of one source of truth, which
is how independently-installed tools have always shared state.]

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

[NEEDS CLARIFICATION: **whether a documented _suggested set_ is worth having.** Free to write and
carries no install-time cost: a README line saying which skills are commonly used together, and why.
The risk is that it becomes a bundle by convention, which is the thing being refused. Leaning yes,
as prose in the README's scope table rather than as anything a tool reads.]

[NEEDS CLARIFICATION: **whether `metadata: family:` should be used for this.** `skill-fitness`
already carries `family: meta`, so a grouping concept exists in the frontmatter without a stated
meaning. Either give it one — a hint for humans, never a resolver input — or drop it as an
unmaintained field.]

## Recommended direction

Refuse dependency detection. Duplicate the resolver. Fix rule 9 to say **config, not call**. Keep
agent-mediated optional invocation, with the skip stated out loud. Ship no bundles, and consider one
README sentence naming sets that work well together.
