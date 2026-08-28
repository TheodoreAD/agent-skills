---
name: skill-authoring
description: "Use when writing a new Agent Skill, editing an existing SKILL.md, or getting a skill change actually deployed — where the source lives versus the installed copy, why editing the installed copy silently does nothing, the edit → gate → commit → push → re-install → verify sequence, how to publish a skill repo so `skills add` finds it, how to word a `description` so it triggers on real requests without stealing another skill's, and when something should be an instructions-file rule instead of a skill at all."
---

# Authoring and updating Agent Skills

A skill is a directory with a `SKILL.md` at its root: YAML frontmatter (`name`, `description`) and
markdown instructions. `references/` holds anything read on demand, `scripts/` anything the skill
runs. That is the whole format, and it is read by every agent that speaks the Agent Skills
convention.

This skill covers writing one and — the part that actually goes wrong — getting a change to one to
take effect.

## Updating a skill and redeploying it

**The copy under `~/.agents/skills/<name>/` (or an agent-specific directory, or a project's
`.agents/skills/`) is not the source.** It is a plain file copy made at install time. Editing it
looks like it works, and then: the next install overwrites it, no other project or machine ever sees
it, and there is no diff, no commit, and no review of what changed. Every skill edit starts by
finding the source repo.

1. **Find the source.** Its README or the skill's own footer normally names it. If not, `skills ls`
   shows what is installed and from where, and the repo is a normal `git clone` away. If you cannot
   establish which repo owns a skill, ask rather than editing the installed copy as a fallback.

2. **Edit the source.** Keep it additive and small — a bullet under the rule it refines, not a
   rewrite. Reasoning for _why_ goes in `references/`, not the body (see "What goes in the body"
   below).

3. **Run the repo's quality gate.** Markdown is not exempt: a formatter that reflows prose will
   rewrite a `SKILL.md`, and a doc-only change that skipped the gate is the most common way to
   schedule a red CI run for someone else.

4. **Commit, and ask before you do** unless the repo's own conventions say otherwise. A skill is a
   shared convention; a change to it is a change to how every future session behaves.

5. **Push.** This is the step that gets skipped, and it is the one that matters: the installer
   **clones from the remote**, so an edit that is committed but not pushed is invisible to the
   install. A local commit changes nothing about what any agent loads.

6. **Re-install.** Nothing watches the source:

   ```shell
   npx skills add <owner>/<repo> --global --skill <name>     # one skill
   npx skills add <owner>/<repo> --global                    # the whole repo
   ```

   Where a machine installs skills declaratively (a setup repo, a dotfile manager), run that
   mechanism instead so its own record stays accurate — it will call the same CLI underneath.

7. **Verify, don't assume.** `skills ls -g --json` lists each installed skill with the agents that
   can see it. **If the skill ships a `scripts/` directory, run one of its documented commands from
   the installed path** — the listing says a skill is installed, not that its files arrived.
   Confirmed live 2026-08-29: a skill whose `SKILL.md` (and a rule deployed into the always-loaded
   instructions file) told every session to run `python3 ~/.agents/skills/<name>/scripts/<file>` was
   installed from a commit that predated `scripts/`, so the documented path did not exist on the
   machine while both documents insisted it did. Nothing failed until something ran it.

   [PITFALL: **That listing is not sufficient evidence on its own, and neither is the installer's
   summary.** Measured 2026-08-27: installing for Claude Code alongside any universal agent prints
   `symlink → Claude Code` in the plan and creates no `.claude/skills` at all — the final summary
   quietly drops the line. Claude Code reads `.claude/skills`, not `.agents/skills`, so on a machine
   where that symlink does not already exist Claude Code gets nothing while every report looks
   healthy. Check the link itself (`ls -l ~/.claude/skills`); if it is missing, point it at the hub
   (`ln -s ~/.agents/skills ~/.claude/skills`).]

**Renaming or deleting a skill needs a second step.** Installing is additive: the CLI adds and
updates what the source publishes and never removes what it no longer does, so a renamed skill stays
installed under its old name indefinitely, alongside the new one. Measured 2026-08-28 renaming one
skill — a reinstall of the whole repo reported eleven skills for ten sources, and the stale one was
still loadable, with its old description still competing for triggers. That is worse than clutter:
the duplicate is precisely the trigger contention the section below says to design against. After a
rename or deletion, run `skills remove -g --skill <old-name> -y` and re-check the count.

**Iterating without a push per edit.** The CLI accepts a local path as a first-class source, so
`skills add ../my-skills --skill <name>` installs the working tree as-is. Use it while drafting;
push before treating the change as done, or the next install from the remote silently reverts it.

Installs are copies in both directions — there is no mode where an agent live-reloads from your
checkout. Whatever the loop, an edit takes effect only after an install.

## Publishing a skill repo

Put skills at `skills/<name>/SKILL.md` in a public repo. No manifest, no marketplace entry, no
vendor directory — the CLI discovers skills up to three levels deep in the standard locations, and
anyone can then install them:

```shell
npx skills add <owner>/<repo> --global
```

A skill that documents a repo's _own_ interface belongs committed in that repo under
`.agents/skills/`, where it needs no install step for anyone working there. A cross-project
convention skill belongs in a dedicated skills repo. Both install with the same command.

## Cut a skill by responsibility, with triggers that don't contend

Before writing a new skill, settle two things — the same decision seen from the authoring side and
the retrieval side:

- **One clear responsibility.** Not a theme, not a bundle of things that happen to be needed
  together. A skill covering two responsibilities has to describe both in one `description`, which
  is the field selection actually matches on, so the dilution is paid on every prompt.
- **Trigger conditions that don't contend with any other installed skill's.** Non-contention is a
  requirement, not a nice-to-have. A description that wins against a prompt meant for a sibling
  skill is a defect even when its own cases pass — the failure is invisible, because the wrong skill
  loading looks exactly like the right one loading.

When a new skill's trigger overlaps an existing one, the fix is redrawing the boundary between them,
not wording the description more carefully. Worked example: this skill and `mcp-server-shipping`
were one skill until 2026-08-28, described as "developing or distributing an MCP server or skill
repo" — two responsibilities in one description, and any prompt about editing a skill had to beat a
description half-about MCP servers. Split on the responsibility, and each description got shorter
and sharper.

Write the `description` from the **request side**: the words someone would actually type, not the
topic's own vocabulary. A description built from internal jargon is a structural under-trigger, not
bad luck — a real measured case is a testing-conventions skill whose description said
`test structure (DAMP vs DRY, fixture scope)`, the skill's own words about itself, and so failed to
trigger on "write tests", "pytest", "fixtures", "parametrize".

Corollary when a finding needs a home: prefer extending the skill that already owns the topic over
adding a new one. Skill count is itself a context tax, and each added description is one more thing
for selection to confuse.

## When it should not be a skill at all

A skill loads conditionally, on a trigger. If the behaviour has to apply **unconditionally, in every
session, across every agent tool**, it belongs in `AGENTS.md`, not in a skill — the always-loaded
instructions file is read by every harness with no trigger to miss.

Confirmed by a reversal worth remembering: a terse-communication-style skill was installed, then
also copied into `AGENTS.md` for cross-tool always-on reach. Once both existed the skill was
redundant, and its only remaining distinguishing feature (switchable intensity levels) was more
complexity than the behaviour warranted. The skill was uninstalled and only the `AGENTS.md` copy
kept, trimmed to one always-on mode.

The inverse test is the useful one: a rule whose miss is **silent and expensive** wants the
always-loaded file; a rule with a sharp trigger whose miss is **cheap and recoverable** wants a
skill.

## What goes in the body, and what goes in `references/`

The body is what an agent must follow. Everything else — prior art, measurements, rejected
alternatives, the story behind a rule — goes in `references/`, loaded only when needed.

- Cite evidence with a date when a rule came from something that actually happened ("Confirmed live
  2026-08-23: …"). A rule with a story attached survives review; a bare assertion gets softened by
  the next editor who disagrees with it.
- When a rule is observed being missed in practice, **strengthen its language rather than lengthen
  its explanation.** A longer justification does not raise adherence; a sharper imperative does.
- Keep machine-specific facts out, or declare them. A rule that depends on one machine's setup — a
  particular dotfile, a locally-installed task runner, a repo that exists on one box — either states
  that dependency plainly or does not belong in a published skill.

## Convention skills should self-update on friction

A skill that encodes a convention (rather than performing a one-shot task) should improve itself
from real usage instead of only being read and followed. The default pattern: when using it produces
a genuinely ambiguous call its own rules don't resolve, or the user corrects a decision it made, ask
rather than guessing — then fold the resolution back into the source as a small additive edit and
redeploy it through the sequence above. `session-harvest`'s "On friction, ask" and "Self-update
mechanics" sections are the worked example to copy.

## A skill's follow-up checks are procedures it runs, not chores it hands back

When a skill's own research ends in "re-measure after a week", "verify X live", "compare against the
baseline", that list is the skill's job, not the user's: encode each item as something the skill
executes on the next invocation — a script flag with pass/fail output (`--compare <baseline>` with
per-expectation verdicts), a stored baseline the skill diffs against, a printed probe plan with
expected outcomes the agent walks through. What genuinely cannot be automated (a human watching for
a permission prompt) is reduced to one yes/no question, not left as a numbered to-do. Stated by the
user 2026-08-24 about a skill whose first version closed with a manual "open / to re-measure" list:
"i don't want to do this manually, the skill should do this for me." `session-bash-audit`'s Measure
/ Compare / Probe split is the pattern.

## Full rationale

[`references/rationale.md`](references/rationale.md) — why self-updating generalizes rather than
being one skill's quirk, and why a skill about shipping skills must describe the portable mechanism
rather than its author's automation.
