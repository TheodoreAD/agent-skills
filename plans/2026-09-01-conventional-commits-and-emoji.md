---
status: idea
updated: 2026-09-01
---

## Context

Commits across this repo family carry no category. The ask is to give each one a type — feature,
docs, bugfix, and whatever else community practice has actually settled on — possibly with an emoji
as well as, or instead of, a textual prefix.

The motivation is not changelog generation. **The user works through agents rather than typing git
commands**, so the question is whether a machine-readable category helps the agent that writes the
commit and the agent that later reads `git log` to work out why a change happened. `~/AGENTS.md`
already asserts that second use ("git history is how future agents learn why a change happened") and
already governs message content: single-concern commits, staging by pathspec, `-F <file>` for any
message containing a backtick. A commit convention lands on top of that, not beside it.

The proposed mechanism is a skill triggered from `AGENTS.md`. That is the shape this family already
uses — the instructions file names the rule, the skill carries the procedure — but per
`skill-authoring` it is a real fork rather than a formality, and the alternative (one paragraph in
`~/AGENTS.md`, no skill at all) has to be argued down rather than skipped past.

The research pass is the substance of this plan, and it has to be comprehensive rather than a
single-pass search summary — `~/AGENTS.md`'s "Choosing a tool or library" bar applies: real specs,
real config, real projects, and the dissent, or the depth gets flagged before the choice counts as
final.

### What the research must cover

- **Conventional Commits itself** — the spec as written: the type vocabulary, scopes, the `!` and
  `BREAKING CHANGE` footer, the body/footer grammar. Which large projects actually enforce it, and
  which merely claim it in a `CONTRIBUTING.md` nobody follows.
- **Angular's convention**, which Conventional Commits was extracted from, and the other prior art
  that predates it — the divergences between them are where the vocabulary is genuinely contested
  (`chore` in particular, which several projects have dropped as a catch-all that absorbs
  everything).
- **Gitmoji, emoji-log, and the emoji conventions generally** — the actual mappings, and whether
  anyone at scale uses emoji _in place of_ the textual type rather than decorating it. Emoji-log is
  worth reading specifically because it is the deliberately-tiny alternative (five categories) and
  is the strongest argument against the full type list.
- **The tooling that assumes the format** — commitlint, commitizen/`cz`, semantic-release,
  release-please, git-cliff, changesets. Adopting the format quietly adopts their expectations about
  what a type means; worth knowing which parts are load-bearing for tools this family will never run
  and can therefore be dropped.
- **The dissent, weighted honestly.** Projects that adopted it and reverted, and the standing
  argument that a type prefix on every commit is ceremony for a solo owner with no release
  automation. This is the half a search summary skips, and the half that decides whether the answer
  is "adopt" or "adopt a three-type subset".
- **Whether anyone has measured this for agents.** Commit-message conventions in agent-authored
  history are new enough that the honest answer may be "nobody has"; if so, say that rather than
  inferring a benefit from human-facing arguments.

## Open questions

[NEEDS CLARIFICATION: does a type prefix actually help an _agent_, or only a changelog generator?
This is measurable rather than arguable — the transcript store and this family's own git history are
both available, and `skill-fitness`/`session-bash-audit` are the precedent for settling a question
like this with a script over real data rather than a hunch. Until it is measured, the honest claim
is "helps a human skimming `git log`", which is a weaker case than the one motivating the ask.]

[NEEDS CLARIFICATION: emoji, text, or both? An emoji-only convention has to survive a terminal with
a missing glyph, a `git log --oneline` scan, and — the one that matters here — an agent grepping
history for a category. Text is greppable and emoji is scannable; "both" doubles the prefix length
on every subject line, which is the thing the 50-character convention is already tight on.]

[NEEDS CLARIFICATION: skill, or a paragraph in `~/AGENTS.md`? `skill-authoring` puts the fork
explicitly: a rule that applies to _every_ commit is instructions-file material, since a skill only
helps if it triggers, and the corpus's measured failure mode is misses rather than steals. A skill
earns its place only if there is procedure beyond the vocabulary — choosing a type for an ambiguous
change, handling a commit that spans two types, the interaction with the split-by-concern rule.]

[NEEDS CLARIFICATION: which type vocabulary? The full Conventional Commits list, or a subset. The
family's commit history is the evidence for which types would actually get used — a type nobody
picks is noise in the instructions, and `chore` absorbing everything is the documented failure.]

[NEEDS CLARIFICATION: does this apply to plan-store commits too? The store's messages follow
`<repo>: <what it is>`, a different convention already in `plan-docs`. Either it adopts the type
prefix as well or the two conventions coexist and the skill has to say which applies where.]

[NEEDS CLARIFICATION: existing history — leave it alone. Rewriting published history to add prefixes
is off the table, so the convention starts at a date and `git log` is mixed forever. Worth stating
in the plan so nobody proposes a backfill later.]

## Recommended direction

Research first, decision second, skill last — and per `~/AGENTS.md`, **pilot the convention on one
real repo before writing it into anything shareable.** `agent-skills` or `power-user-linux-setup` is
the pilot; a convention that survives a few weeks of real commits there is the one worth publishing.

A plausible shape to test against the research rather than assume:

- Textual Conventional Commits type as the prefix, because it greps; emoji, if adopted at all, as a
  decoration the tooling ignores rather than as the category itself.
- A deliberately short type list, justified from this family's own history rather than copied whole.
- The rule stated in `~/AGENTS.md` (it applies to every commit, so it has to be always-loaded), with
  a skill only if the research turns up genuine procedure — and if a skill is written, a trigger
  that cannot contend with `plan-docs` or `session-harvest`, both of which also touch committing.
- No commitlint hook, no CI gate. `~/AGENTS.md` is explicit that agent behaviour is corrected by
  teaching the agent what to run, not by a mechanism that fires behind its back; a commit-message
  linter is exactly the mechanism that rule names.
