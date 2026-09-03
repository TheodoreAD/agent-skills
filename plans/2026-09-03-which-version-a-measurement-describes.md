---
status: planned
updated: 2026-09-03
---

# Which version of a skill a measurement is actually describing

## Context

Asked by the user 2026-09-03: should the audits compare against the source code, or only against the
pushed versions already on GitHub?

It is not a choice between two, because there are **four** populations and they disagree routinely.
The gap is not that the wrong one was picked — it is that only some of them are askable at all, and
that a number's meaning silently changes depending on which one a command happened to read.

| population            | the question it answers                         | askable today           |
| --------------------- | ----------------------------------------------- | ----------------------- |
| the working tree      | is the change I am making right?                | yes — `--root skills`   |
| `HEAD`, local commits | (almost nothing; it is a staging artefact)      | no                      |
| **`origin/main`**     | **what does a reader actually get?**            | **no**                  |
| `~/.agents/skills`    | what is this machine's agent loading right now? | yes — the default roots |

`skills add TheodoreAD/agent-skills` clones the remote, so **`origin/main` is the product.** Nothing
in the corpus can currently measure it, which means no number this corpus produces has ever been a
statement about what readers have.

## Evidence

**Measured on this machine, 2026-09-03, mid-session:**

- working tree == `HEAD` (clean)
- `HEAD` is **2 commits ahead** of `origin/main`
- `origin/main` differs from `~/.agents/skills` in **4 files** — `plan-docs`'s `SKILL.md`,
  `design-rationale.md` and `plans.py`, and `skill-fitness`'s `fitness.py`

Three of the four populations disagree right now, in a repo with a clean working tree and nothing
unusual going on. This is the ordinary state, not a bad moment.

**And this session produced the failure it describes.** The portability audit reported "34 bare
references across 14 skills" while eleven commits sat unpushed. The number was true of the working
tree and true of nothing a reader could install. Nothing in the output said which.

[PITFALL: **`origin/main` is a remote-tracking ref, so reading it without fetching measures the last
fetch rather than the remote.** `~/AGENTS.md` already carries this rule for branch state and it
applies unchanged here: a plain `git fetch` never prunes and a stale `origin/<branch>` will answer
confidently. Any measurement claiming to describe the product has to fetch first or say that it did
not.]

## The rules this suggests

**1. A gate runs against the working tree, always.** A CI check that measured `origin` would be
measuring the past and could never fail on the change under review. `tests/unit/test_derivable.py`
is correct exactly as it is, and the same will hold for a portability gate.

**2. The authoring loop runs against the working tree.** You audit what you can edit; that is the
whole point of the opt-in decision in `2026-09-02-skill-output-must-be-actionable-by-its-runner.md`.

**3. Any claim about readers must name `origin` explicitly, and must never get it by default.** A
default that changes meaning depending on whether the author has pushed is worse than having no
default: it is a number that is sometimes about the product and sometimes about a draft, with
nothing in the output distinguishing the two.

**4. The installed hub is a third question and is already answered.** `fitness.py inventory`'s
`stale_copies` reports same-name-different-content across roots, which is precisely
install-versus-source drift. Nothing new is needed there.

**5. The implementation is nearly free — no clone, no network beyond a fetch, no new machinery.**
`--root` already exists to score a corpus that is not installed:

```shell
git archive origin/main skills | tar -x -C <tmp>
python3 <this skill>/scripts/fitness.py portability --root <tmp>/skills
```

Verified working 2026-09-03. By this repo's own rule that anything derivable belongs in a script,
this should be a flag — `--ref origin/main` — rather than prose asking an agent to compose the
pipeline correctly on every run.

## The same gap one level up, which is the more valuable half

**`set-status landed` gates on open tags and never on whether the work is published.**
`STATUS_GATES` blocks `landed` on `UNVERIFIED` and `NEEDS CLARIFICATION`, and on nothing else. But
`landed` is the status that _precedes deletion_ — retirement removes the file — so a plan can be
marked landed and retired while the change it describes sits in an unpushed commit. The change is
not in the product, and the record of why it was made is gone.

`~/AGENTS.md` already states that a local commit is not a private holding state and that any
parallel session's push publishes it. The plan lifecycle does not know this: it treats "committed"
and "shipped" as the same event, and they were not the same event for most of this session.

[DECISION: **this is a different finding from
`2026-08-30-plan-docs-status-gate-bypassed-by-hand-editing.md`**, which is about the gate being
skipped by hand-editing frontmatter. This one is about what the gate checks when it does run. They
share a file and nothing else.]

## Decisions

[DECISION: **report unpushed commits at retirement, never gate `landed` on being pushed.** Gating
has a failure mode with no way out: a plan describing work in a repo with no remote — and
`~/plans-sensitive` is deliberately one, permanently — could never reach `landed`, so the gate would
be teaching people to `--force` past it, which is worse than not having it. Retirement is where the
check earns its place, because deletion is the irreversible step and the loss is specific: the
explanation of a change that never shipped. Concretely, `git log origin/<branch>..HEAD` for the repo
the plan describes, and warn before deleting.]

[DECISION: **`--ref` never fetches. It prints the sha and the fetch age, and refuses only when there
is no remote-tracking ref at all.** Every script in this corpus is documented read-only, stdlib and
network-free; a silent fetch breaks that property for a convenience. No staleness threshold either —
a threshold is a number nobody can defend and it turns a clear fact into a policy argument. Print
`origin/main @ abc1234, fetched 3h ago` and let the reader judge, which is the same shape as
reporting a drift rather than gating on it.]

[DECISION: **name the population once at the top of every report, not per section.**
`corpus:
working tree` / `corpus: origin/main @ <sha>, fetched <age>` /
`corpus: installed (~/.agents/skills) — deployed copies, not yours to edit`. Once, because a
per-section repeat is noise for a value that cannot change within a run. This also closes the
residual "authorable" question in `2026-09-02-skill-output-must-be-actionable-by-its-runner.md`: an
explicit run against the hub needs to say what it is looking at, and that is the same line.]

## Recommended direction

Add `--ref` to `fitness.py`, print the population in the report header, and leave the gates reading
the working tree. Then, separately, make retirement — not `landed` — report whether the plan's repo
has unpushed commits, because deleting the explanation of a change that never shipped is the
expensive version of this mistake.
