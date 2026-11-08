# skill-authoring-taudelta

Writing Agent Skills, and getting an edit to actually reach the agent.

Writing a skill is the easy half. The Agent Skills format is a directory with a `SKILL.md` in it,
and any agent can read one. The hard half is what happens after you change it. You edit the skill,
start a new session, and the agent does exactly what it did before, with nothing to tell you why.

The usual reasons are all silent. The copy the agent loads is a file copy made at install time, so
editing it changes one machine until the next install overwrites it. The installer clones from the
remote, so a commit you haven't pushed reaches nobody. It installs from the default branch, so a
pushed feature branch reaches nobody either. And a session that loaded the skill at start keeps the
old text until it reloads.

skill-authoring-taudelta gives the agent the whole loop and the rules for writing a skill that
triggers when it should. It is one author's rulings, drawn from building the fifteen skills in this
repo. Where you would rule differently, fork it.

## What you get

- The update sequence, in order: find the source repo, edit it, run the repo's gate, commit, push,
  re-install, verify, and reload. Each step says what goes wrong when it is skipped.
- The install flag that is not optional. Without `--global`, the `skills` CLI decides the scope from
  your current directory, and run inside a repo it writes a skills directory, a symlink and a
  lockfile into that repo's working tree.
- A name check before you adopt a name. A skill whose name another installed skill already uses is
  dropped from the listing without a message, and a rename reads to the lockfile as a delete.
- How to cut a skill: one responsibility each, and a description written in the words a person would
  type about the problem, not the tool's own vocabulary.
- When something should not be a skill at all, but a rule in the always-loaded `AGENTS.md` instead.
- Where each kind of content goes: the body is what an agent must follow, `references/` holds the
  reasoning, and anything a script could work out goes in a script rather than prose.
- Rules for a skill's scripts and files: standard-library Python by default, no hard-coded paths,
  one fixed place for each kind of data, and a short section saying what the skill reads, runs and
  writes.

## What it looks like

Tell the agent "I fixed the skill, but the agent is still doing the old thing." It doesn't reach for
the file again. It works out which step of the loop is outstanding: is the fix committed, is it
pushed, is it on the default branch, did the install actually land, did this session reload. Then it
says which one is missing rather than reporting "re-installed" as though the loop were closed.

Checking a name before adopting it is one command, and it exits 3, not 0, when the public index
can't be reached, so an unanswered check never reads as a clean one:

```
$ python3 names.py audit --offline --root skills
  no collisions locally for 15 name(s)
```

## What went wrong while writing it

Most of the rules exist because a step failed while every command reported success. On 2026-08-27,
installing for Claude Code alongside another agent printed `symlink → Claude Code` in its plan and
created no link at all, so Claude Code saw no skills while every report looked healthy. On
2026-09-12, a check against the public index found five of this repo's fifteen names already
published by other repos.

The sharpest one was a rename. On 2026-09-27 a skill was renamed, and its config directory was moved
thirty minutes before the change was pushed. A parallel session in another repo, still running the
old installed copy, hit the gap ten minutes in. The fix shipped with the rename couldn't help,
because it lived in the new code and the failure was in the old. So the skill now says: push,
install, and only then move state that lives outside the skill directory.

## Why not just edit the installed copy

Because nothing records it. The next install overwrites it, no other machine or project sees it, and
there is no diff, no commit and no review of what changed. The installed copy looks like the source
and behaves like a cache.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill skill-authoring-taudelta
```

It hands measurement to [skill-fitness](../skill-fitness/), so install that too if you want to test
descriptions rather than read them:

```shell
npx skills add TheodoreAD/agent-skills --global --skill skill-fitness
```

Needs Node for `npx`. The name check needs Python 3.11 or newer.

## What it touches

Its one script, `names.py`, reads the `SKILL.md` of each skill under the directories you give it,
taking only the name and a digest of the file. It sends each name, and nothing else, to the public
skills.sh search, one request per name, unless you pass `--offline`. It writes nothing. The commands
the skill tells you to run are the `skills` CLI's own: installing copies skills into
`~/.agents/skills/` and links each agent's skills directory to it. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/naming.md`](references/naming.md): a corpus of 1,043 published skills across 40
  repos, what the specification says about names, and why a rename is a breaking change.
- [`references/rationale.md`](references/rationale.md): why convention skills should update
  themselves from friction, and why this one describes the portable mechanism rather than one
  author's automation.
