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

2. **Edit the source — if your session is in the repo that owns it.** Keep it additive and small — a
   bullet under the rule it refines, not a rewrite. Reasoning for _why_ goes in `references/`, not
   the body (see "What goes in the body" below).

   **From a session working in a different repo, this sequence stops here.** Editing and committing
   in a checkout that is not your session's is a commit in someone else's working tree, and on a
   machine running parallel sessions it looks routine in `git log` — the session that owns the repo
   may push it without knowing it was not theirs. File the change instead, against the skill's own
   repo, and let the next session working there apply it. Confirmed 2026-08-30: a run made two
   correct, gate-green edits to a skill from an unrelated project and committed them there, which is
   how this clause came to exist.

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

   [PITFALL: **`-g`/`--global` is not a default — without it the scope depends on where you are
   standing, silently, with a green summary either way.** The flag is documented as "install skill
   globally (user-level) **instead of project-level**"; omitted, the CLI resolves project-level in a
   project and global outside one. Run from inside a repo it therefore writes `.agents/skills/`, a
   `.claude/skills` symlink and `skills-lock.json` into that working tree, while the user-scope copy
   you meant to update stays stale. Worst inside a skills repo itself: it deposits a consumer copy
   of a skill that repo authors, plus a harness-specific directory a vendor-neutral repo may refuse
   on principle, and none of the three is gitignored, so the next `git add` sweeps them in.

   **Standing somewhere else is not the fix; the flag is.** `skills-lock.json` is a _project_
   artifact — `skills experimental_install` restores from it — so a scope-by-cwd run still drops one
   wherever you ran it, listing only the skills that invocation touched. Confirmed 2026-08-30, both
   halves in one session: the first run, from the repo, installed into the repo and updated nothing
   global; the second, from `$HOME`, installed correctly and left a `~/skills-lock.json` naming one
   of the machine's ten skills, which reads as a manifest and is not one. Pass `-g` and the answer
   stops depending on cwd. Check `git status` afterwards if the session's cwd was a repo.]

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

**Request-side means the words for the _problem_, not for the tool that solves it** — the sharper
version of the same rule, and the one a careful author still gets wrong. Measured 2026-08-31: a
skill whose description named `tasks.py`, `inv` and "namespace" fired on every request using those
words and selected **nothing at all**, three runs of three, for "our automation scripts have grown
messy and inconsistent, where do I start cleaning them up?" — the way the problem is actually felt.
It did not lose to a competitor; it lost to silence, which no contention check can see.

**Don't settle any of this by reading. Measure it with `skill-fitness`**, which owns the mechanics
this section only states:

```shell
python3 <skill-fitness>/scripts/fitness.py overlap        # ranked pairs, and directional shadowing
python3 <skill-fitness>/scripts/trigger.py run <cases>    # which skill a real request actually selects
python3 <skill-fitness>/scripts/trigger.py candidate ...  # score a proposed description before adopting it
python3 <skill-fitness>/scripts/trigger.py split ...      # how requests distribute across a proposed split
```

Two results from that tool change how this section should be applied. Its static overlap flag is a
hypothesis generator and **not a verdict** — its one testable prediction was refuted by the live
run, so a redrawn boundary should be justified by `trigger.py`, not by an overlap score. And a
candidate description's score is an **estimate that errs in both directions**: a proposal is
registered as a command file and a real skill is not, so a wording that improves without reaching a
clean pass is still worth adopting — but **the `run` after it ships is the figure, not a
formality.** Called a lower bound here until 2026-09-01, when a skill measured 12/12 as a candidate
and 11/12 once installed, on the same cases.

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
- **Pilot a rule before shipping it, and expect the pilot to _sharpen_ it, not merely pass or fail
  it.** The familiar reason to try a convention on one real repo first is to catch rules that are
  noise or footguns. The more valuable outcome is a rule that comes back decidable. Confirmed
  2026-09-01: the stated position going in was that `NamedTuple` is "very cheap and increases
  readability tremendously"; applying it to one 3,200-line module produced a rule that is neither
  yes nor no — a bare tuple becoming a `NamedTuple` is an upgrade, a frozen dataclass becoming one
  is a downgrade, because the benefit and the hazard are the same property seen from two sides. No
  amount of reading would have produced that, and the version that shipped is a test an author can
  apply rather than a preference. So a pilot that only confirms what you already believed is a pilot
  worth being suspicious of.

## Anything the skill can derive deterministically goes in a script, not in prose

**If a competent script could produce the answer, the skill ships that script and the body says
which flag to run.** A `SKILL.md` is instructions for a model that re-reads them from scratch every
time, so a paragraph explaining how to spell a command is a rule that has to be followed correctly
on every single run, while a script is followed once and then only invoked. The cost of getting it
wrong is not evenly spread either: prose fails silently and plausibly — a wrong branch name, a
dropped flag, a filter that eats an exit code — and the output still looks like an answer.

This is sharpest for the interfaces with real syntax: **a CLI's flags and subcommands, an HTTP API's
request and response shape, a SQL query, a JSON traversal, a parser over some tool's output.** Those
are deterministic, they are non-trivial, and a model gains nothing by re-deriving them. Anything
multi-step is the same case one level up: "run this, read that, then run this other thing depending
on what it said" is a program, and writing it as prose asks the agent to be the interpreter.

The measured case, 2026-09-02: `session-harvest` was 967 lines of prose whose mechanical half was
re-derived per run — 24,429 Bash calls across 1,134 transcripts on this machine included 568
plans-store status calls, 498 hand-written ahead-counts and 164 bespoke Python heredocs over a
transcript, no two alike. Six of its rules existed because a specific mistake kept recurring, each
had already been sharpened as prose, and each recurred anyway. They stopped recurring when they
became code: not because the wording improved, but because there was no longer a wording to follow.

**What legitimately stays in prose**, so this doesn't read as "no commands in a `SKILL.md`":

- a fixed literal a reader runs once, with no parts assembled from context
  (`npx skills add <owner>/<repo> --global`);
- a single call into the skill's own script — that _is_ the delegation, placeholders and all;
- a one-off emergency procedure nobody runs twice a year (a history purge), where the script would
  be read less often than the prose;
- the command that names the consuming repo's own tooling, which a portable script must not
  hard-code — a skill cannot know whether a repo's gate is `inv quality.precommit` or something
  else, so it says "run the repo's gate" and stops there.

**Audit it rather than trusting it, because this is exactly what drifts.** A skill improves one
sentence at a time, and each added command line looks harmless.
`python3 <skill-fitness>/scripts/fitness.py derivable` splits every fenced command in a corpus into
delegated, derivable and fixed, tags what kind of derivation each one is, and diffs against a saved
baseline — a rise in a skill's derivable count is the finding. Save a baseline when a skill is in
good shape; compare after a run of edits.

## A script in `scripts/` declares its own dependencies, or has none

**Standard library only is the default, and it is not a limitation to apologise for.** A skill is
installed by copying files; nothing runs an install step afterwards, so a script that needs anything
resolved before it runs is a script that does not work for whoever installed the skill.

1. **Stdlib only.** `python3 <skill>/scripts/foo.py` works on any machine with Python, with zero
   declaration and zero resolution. Two real tools in this repo are built this way —
   `plan-docs/scripts/plans.py` and `session-bash-audit/scripts/audit.py`, the latter parsing every
   `~/.claude/projects/*.jsonl` — Claude Code's own transcript store, so that one reads nothing on
   another harness — on `argparse`/`json`/`re`/`dataclasses`/`pathlib` alone. Simple YAML
   frontmatter does not justify PyYAML.
2. **PEP 723 + `uv run`** if a dependency becomes genuinely necessary — a `# /// script` TOML block
   inline in the file, which keeps it single-file and portable. This is the documented convention
   for skill scripts, not a local invention.
3. **A venv, a `requirements.txt` or a `pyproject.toml` inside a skill — no.** It makes the skill
   un-runnable until someone performs an install step the `skills` CLI does not perform.

Reference a script by **path relative to the skill directory root**, which is what makes it work
identically for everyone who installed the skill.

**Whatever it is written in, a script here is run by an agent, not by a person at a terminal**: no
interactive prompts (an agent's shell is non-interactive and a TTY prompt hangs forever), a real
`--help` because that is how an agent learns the interface, structured output on stdout with
diagnostics on stderr, documented exit codes, and bounded output because harnesses truncate.

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
