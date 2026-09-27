---
status: idea
updated: 2026-09-27
---

# A reflowed line defeats both a grep and a remembered string, and the gate reflows on every run

## Context

`dprint` reflows markdown prose on every `inv quality.precommit`, which this repo runs before every
commit. Everything durable here is reflowed prose: `SKILL.md` bodies, `references/`, `AGENTS.md`,
the plans. Two tools an agent reaches for constantly are line-oriented or string-exact, and reflow
breaks both — silently in one direction and loudly in the other.

Three instances, all 2026-09-27, all in one session (`21615ec2-5eca-4393-a831-d24275fb2551`) during
the eight-skill rename batch.

**Loud, twice: `Edit` fails because `old_string` spans a line the gate has since rewrapped.** Both
times the text had been written earlier in the same session, gated, and then edited again from a
remembered form:

- an edit to this repo's naming-pass plan, cost item 5, whose `old_string` was four lines copied
  from what had been written minutes before — the gate had rewrapped them and the call returned
  `String to replace not found in file`;
- an edit to `AGENTS.md`'s author-mark bullet, same cause, same message.

Loud is the cheap failure: the tool refuses, one `rg -n` locates the current wrapping, and the edit
goes through. It cost two extra calls each.

**Silent, once: `rg` for a multi-word phrase returns nothing and reads as absence.** Verifying that
a pushed and re-installed skill rule had actually reached the installed copy:

```shell
rg -c 'move state that lives outside' ~/.agents/skills/skill-authoring-taudelta/SKILL.md   # nothing
```

The rule was there. `dprint` had wrapped the sentence between `state` and `that`, and `rg` matches
lines. Read as written, that output says the deploy silently failed — the single most alarming thing
a verification step can report — and the next move would have been to re-install, or to hunt a bug
in the installer.

`diff -q <installed> <checkout>` answered it in one call and is the check `skill-authoring-taudelta`
already prescribes for the staleness case. It was not reached for here because the question felt
different: staleness is "are these two the same", and this was "does this file contain my sentence",
which sounds like a search.

## Why this is worth writing down rather than remembering

The failure mode is the one this corpus keeps re-learning in other forms: **a line-oriented count
over text that is not line-stable is an answer to a different question.** The transcript-grep plan
(`2026-09-18-a-grep-over-a-transcript-counts-prose-not-calls.md`, now retired into
`session-harvest`'s `SKILL.md` beside the suspicious-zero rule) is the over-counting half — 135
against a true 1. This is the under-counting half, and it is more dangerous per occurrence: an
inflated count invites a check, while a zero looks like a finished answer. Both arrived in the same
session, from the same instinct, five hours apart.

[PITFALL: **the gate is what makes this recurrent rather than occasional.** A reflow is not an event
somebody chose; it happens every time the repo's own pre-commit gate runs, which is every commit. So
any string an agent holds from before its last gate run is suspect, and in a session that commits
eight times the window is never open for long. Nothing warns: the file on disk is correct, the diff
is clean, and only the agent's memory is stale.]

## Open questions

**Decided 2026-09-28: the verification half is the skill-side one**, and it is now in
`skill-authoring-taudelta`'s step 7 — diff the installed copy against the checkout, never grep it
for the added sentence, with the false negative above as the evidence. The premise that the skill
already prescribed `diff` for staleness was wrong: step 7 named `skills ls` and running a script,
and no `diff` at all. The 94 installed-vs-checkout `diff -q` calls in `session-harvest`'s 2026-09-02
census were hand-rolled, not prescribed. **The editing half stays out of any skill**: re-reading the
region before an `Edit` whose `old_string` predates the last gate run is a general habit, and its
failure is loud and cheap.

[NEEDS CLARIFICATION: does the general rule belong in the always-loaded instructions file, and if so
does it extend the existing `rg` section or the verification one? `~/.agents/AGENTS.md` already
carries "Searching a tree, by name or by content", whose established shape is exactly this — an `rg`
invocation that is well-formed, exits 0, and silently answers the wrong question, like the
hidden-path descent trap. This would be a third entry in that family. Against: that file is over its
own size reference points, the miss here is cheap and recoverable when loud, and only the silent
half is expensive. The silent half is the one with a sharp trigger — "I am grepping prose to prove a
phrase is present" — which is the profile the tier test assigns to a skill rather than to the
always-loaded file. Filing this in `agent-skills` rather than `--for power-user-linux-setup`
reflects that reading, and the decision is genuinely open: if the answer is the instructions file,
this needs a filing for that repo, since the fragments live there.]

## Recommended direction

Take the verification half first, because it is unambiguous and the silent failure is the expensive
one: `skill-authoring-taudelta`'s verify step says to `diff` the installed copy against the checkout
and names why a phrase grep is not a substitute. One or two sentences, with the false negative as
the evidence.

Then decide the general rule's home against the tier test rather than by where it was noticed.
