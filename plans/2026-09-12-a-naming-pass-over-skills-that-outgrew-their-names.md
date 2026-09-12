---
status: idea
updated: 2026-09-12
---

# A naming pass over the skills that outgrew their names

## Context

Raised by the user 2026-09-12: _"plan docs is a name I let happen without much scrutiny, but it's
evolved into so much more, same as research-library and some of the skills and conventions ones,
maybe it would be good to do a pass and see if we can come up with more expressive names."_

Deliberately not executed. The user's call was to write the options down and stop, because a rename
is a one-way door and there is no cost to deciding later except that install counts grow slowly.

Naming _style_ has no evidence behind it — the specification's authoring pages publish none, no eval
anywhere varies skill names, and selection is documented as description-only. That research is in
`skills/skill-authoring/references/naming.md` and is not repeated here. What follows is therefore a
taste exercise with two hard constraints attached, and the constraints are the useful part.

## The reframe: the bland half is the second token

The one regime where a name carries the **entire** trigger signal is the degraded listing —
descriptions stripped, names alone. Codex implements that as a documented tier; on this machine 16
skills have appeared as bare names in real Claude Code listings. So the first token is what a reader
scans, and the corpus already does the right thing by putting the domain there (`python-`, `mcp-`,
`session-`, `skill-`).

[DECISION: **expressiveness goes in the second token, and the domain token stays.** `plan-docs` is
not bland because of `plan-`; it is bland because of `-docs`. This kills the tempting direction of
pure metaphor — `manifold` was floated and rejected, because a name that tells a stranger nothing is
at its worst in exactly the regime where the name is all there is, and "manifold" additionally
carries misleading mathematical and mechanical senses.]

[PITFALL: **a uniform author prefix would make the name-only regime worse, not better.** Measured
over 1,044 skills in 40 repos: of 24 repos with five or more skills, only 4 put half or more behind
one leading token, and 14 are under 20% — so it is a minority practice, but bimodal, near-total
where adopted (`baoyu-` 95%, `caveman-` 86%). It namespaces perfectly and would end the collision
problem outright. It also pushes the distinguishing token later in every single name, at the one
moment a reader has nothing else. Considered and not adopted; if it ever is, adopt it selectively on
the generic names rather than uniformly.]

**Availability was checked, not assumed.** Every candidate below was run through `skill-authoring`'s
`names.py check` against the public index on 2026-09-12. Worth recording that the obvious evocative
choice, `skill-forge`, is already published by **five** repos — distinctiveness and availability
correlate, so checking early is cheap and guessing is not.

## `plan-docs` → `plan-conveyor`

The user's word, and it beats every alternative considered because it is the only one that catches
**both** halves of what the skill became:

- the **status lifecycle** — a plan enters as an idea and moves through stations until it comes off
  the end and is deleted, which is the doctrine the skill states repeatedly ("a working set that
  empties out");
- the **cross-repo transport** — a plan is literally conveyed from the repo that noticed it, through
  the store, to the repo that owns it, where another session absorbs it. Nothing else in the corpus
  does that.

Rejected alternatives, each catching only one half: `plan-turnover` and `plan-lifecycle` (the
emptying, not the transport), `plan-relay` (the transport, not the lifecycle), `plan-ephemera`
(literally accurate — ephemera are transient documents meant to be discarded — but reads precious).

Also rejected: `plan-convertor`, which was a typo for conveyor, and would have been wrong anyway
since the skill converts nothing. And the markdown-wordplay direction the user floated, which
produced only names for details of the format (`plan-frontmatter`, `plan-checkbox`,
`plan-strikethrough`) rather than for what the skill does.

`plan-conveyor` is free in the registry. **Treat this one as settled unless the user says
otherwise.**

## `research-library` → undecided, and "research" stays

[DECISION: **the first token stays `research-`.** The user's framing, which is sharper than the
skill's own description: it is for someone _"researching a library, app docs, articles, packages,
and gathering facts locally to avoid lots of reading html and web search."_ That is a **method**,
not a library — and `-library` is the half that the skill outgrew, because what it grew into is a
doctrine (clone and grep the real source) plus a dependency-vetting procedure, neither of which is a
library. An earlier proposal of `primary-sources` was rejected by the user as not speaking to them,
and it also drops the word that names the activity.]

All free in the registry as of 2026-09-12:

| candidate         | what its second token claims                       | note                                                                 |
| ----------------- | -------------------------------------------------- | -------------------------------------------------------------------- |
| `research-mirror` | a local copy of upstream                           | most precise about the mechanism; every developer knows the term     |
| `research-trove`  | a gathered collection worth having                 | closest to the user's own word, "gathering"; warm and memorable      |
| `research-corpus` | a body of text you search                          | matches the "grep it locally" half exactly; slightly academic        |
| `research-larder` | provisions laid in before they are needed          | captures gather-in-advance-to-avoid-fetching best; unusual word      |
| `research-stacks` | where the volumes are, as opposed to the catalogue | the library metaphor that lands; "stack" hits a data structure first |
| `research-depot`  | a place things are stored and dispatched from      | would echo `plan-conveyor` deliberately                              |
| `research-desk`   | where the work happens                             | human and modest; vague about there being a store                    |

[NEEDS CLARIFICATION: **which of these.** The trade-off is mechanism versus method: `-mirror` and
`-corpus` name what the store _is_, while `-trove` and `-larder` name what it is _for_. The user
leans toward the activity, which argues for the second pair, and `research-trove` is the closest
match to their own phrasing.]

[DEFERRED: **whether the family should echo.** `research-depot` beside `plan-conveyor` would read as
one author's system rather than two unrelated choices. Tempting and worth exactly one echo, not a
scheme — forcing every skill into logistics nouns would produce bad names for the ones that do not
fit, and `skill-smithing` below is already a different metaphor.]

## The two with a reason beyond taste

These collide in the public index, so they have an argument for moving that does not depend on
anyone's ear. The collision mechanism and its evidence are in `skill-authoring`'s `SKILL.md`; in
short, a duplicate name is dropped silently, first-seen-wins, so installing one of these repos would
shadow the local skill with no message anywhere.

| current              | also published by                                                | candidate         | free? |
| -------------------- | ---------------------------------------------------------------- | ----------------- | ----- |
| `skill-authoring`    | 6 repos, including `grafana/skills` and `microsoft/azure-skills` | `skill-smithing`  | yes   |
| `python-conventions` | 6 repos                                                          | `python-defaults` | yes   |

Three more collide and are not proposed for renaming here: `research-library` (2 repos — covered
above), `plan-docs` (1 — covered above), `session-harvest` (1, and it is already a good name).

## The `-conventions` cluster, and an argument that is genuinely balanced

Five skills end in `-conventions`, and all five do the same thing: give **one settled answer per
question** rather than an evaluation. `db-defaults` already in the corpus does exactly that and is
the best-named skill of the set, which suggests harmonising: `python-defaults`,
`python-test-defaults`, `mcp-python-defaults` (all free).

[NEEDS CLARIFICATION: **whether the harmonisation is worth it.** For: "a convention" could be a
survey of practice, while "a default" is a pick, and these skills pick — so `-defaults` is the more
honest word, and `db-defaults` proves it reads well. Against: `-conventions` currently gives five
skills family coherence, and only `python-conventions` has a collision reason, so the other two are
pure taste at the cost of doubling the citation-rot surface to check. Two of the five should not
change either way: `invoke-task-conventions` is rules and traps rather than a defaults table, and
`polite-mcp-conventions` is repo-specific behaviour at personal scope.]

## What a rename actually costs, so the batch is done once

Gathered from `skill-authoring` and from this session's own evidence. **Do the whole set in one
batch** — each item below is paid per batch, not per skill.

1. **Directory and frontmatter `name` move together**, and must match; `test_name_is_spec_valid` and
   `test_name_matches_directory` gate it.
2. **The README catalogue row** is gated by `test_listed_in_readme`.
3. **Cross-skill citations in prose are validated by nothing.** `session-harvest` referring to "the
   plan-docs skill", `~/.agents/AGENTS.md` naming `plans.py` paths, and this repo's own `AGENTS.md`
   all break silently. A `rg` for the old name across the repo **and** the deployed instructions is
   the only check there is.
4. **Script paths change** — `skills/plan-docs/scripts/plans.py` is named in the global instructions
   file, which is a **different repo's** deployed artifact, so that part is a filed plan rather than
   an edit from here.
5. **Installing is additive.** After reinstalling, `skills remove -g --skill <old-name>` or the old
   copy stays loadable and competes for triggers — measured previously at eleven installed skills
   for ten sources.
6. **The old slug is permanent in the public index.** `mcp-skill-shipping` still sits there at 2
   installs beside `mcp-server-shipping` at 34. Renaming does not clean up; it forks.

[PITFALL: **the window is open only because nobody depends on these yet.** ~380 installs, no known
external dependents, no `displayName` and no `renames` map in the skill format — the two affordances
Anthropic shipped for plugins precisely because a slug change breaks installs. The same rename in a
year is a migration; today it is an edit.]

## Recommended direction

1. Settle `research-library`'s second token — the only open naming question, since `plan-conveyor`
   is the user's own and free.
2. Decide the `-conventions` question as a yes/no on the whole cluster rather than per skill, since
   the value of harmonising is coherence and a partial pass has none.
3. Then one batch, in this order: rename directories and frontmatter, regenerate the README row,
   `rg` the old names across the repo and the deployed instructions, run the gate, push, reinstall,
   remove the old slugs locally, and file a plan for the global instructions file's `plans.py` path.
4. Re-run `names.py audit` afterwards — it should report no collisions for the renamed set, which is
   the check that the rename bought what it was meant to.
