# session-bash-audit

Measures how your agent really uses the shell, from its own session records.

Most instructions files carry rules about the shell: don't chain commands with `&&`, don't pipe
output through `head`, don't `cd` into the repo you're already in, read files with the read tool
rather than `cat`. Whether the agent follows them is usually a matter of impression. And the
impression is unreliable in a specific way: the agent's own account of how a session went is not
evidence, even for a rule it wrote that same day.

Those habits have real costs. A chain hands back one blob of output and only the last command's exit
code. A `| tail -3` on a test run throws away the lines saying what failed, and can hide a red gate
behind a green exit. A command wrapped in `cd` or `git -C` stops matching the permission rules meant
for it.

session-bash-audit reads Claude Code's own session records and counts each pattern, so a rule change
is judged by whether the numbers moved.

## What you get

- Per-model and per-session rates for about two dozen patterns, including chaining, `head`/`tail`
  truncation, pipelines that mask a failing exit code, `sed -n` and `cat` used as a file viewer,
  heredocs, `cd` into the session's own repo, `git` writes inside chains, and `grep -r` or `find`
  where `rg` or `fd` was preferred.
- Real examples of each pattern with the command text, so you can see what a count is made of before
  acting on it.
- A comparison against a baseline you saved earlier, with a verdict per rule, to answer "did the
  change work?".
- A view of one session against that baseline, which is the only answer that arrives while the
  session can still act on it. A session compacted part way through is shown both before and after
  the compaction, because the two halves often behave nothing alike.
- A replay of your permission rules against past commands, to find which command shapes are behind a
  pile of confirmation prompts.
- A table that routes each finding to the mechanism that owns it: the permission allowlist, the
  permission mode, a subagent's prompt, or the rule's own wording. Adding another sentence to the
  instructions file is the reflex this is meant to prevent.

## What it looks like

The one-session view, run on the session that wrote this page. Every row prints, zeros included,
with the count first, because at session scale one real instance rounds to `0%`:

```
== this session, 71 calls ==
  chain                        1    1%
  chain5                       0    0%
  head/tail                    0    0%
  exit-masked                  0    0%
  sed-n                        0    0%
  cat-view                     0    0%
  heredoc                      0    0%
  cd-own-repo                  0    0%
  git-C-own-repo               0    0%
  …
  cut-message                  0    0%   of 10 message-carrying calls
  bash-c                       0    0%
```

The first full run, over four days and 3,956 calls ending 2026-08-24, looked very different. Two of
the three main models chained 64% and 71% of their calls and piped roughly three in ten through
`head` or `tail`. 662 pipelines masked an exit code, 364 of them around a quality gate or a test
run. The instructions file already had a rule against that last one; the habit and the rule had
never connected.

## Why not ask the session how it went

Because it doesn't know. On 2026-08-30 a session that had spent the day writing the rule against
piping a gate through `head` or `tail` did it in 33% of its own calls, and reported that the run had
gone well. On 2026-09-01 the session that built the one-session view measured itself at 47%
`head`/`tail`, 17 points worse than the baseline, having quoted the rule in its own commit messages.

The research behind the first run also found causes that no rewording could fix. Auto mode's system
prompt tells the agent to do the opposite of the usual rules: read files with `cat`, `head` or
`sed -n`, and edit with `sed` and heredocs. And a rule justified only by permission prompts stops
being followed in a mode where nothing prompts. Those are fixed in the mode and in the rule's
rationale, not in louder wording, which is why the audit ends in a routing table.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill session-bash-audit
```

Then ask: "how are my sessions using Bash this week?", "did last week's rule change work?", "why am
I getting so many permission prompts?".

It is specific to Claude Code, since that is whose session records it reads. On another harness
there is nothing to read, and it says so rather than reporting zeros. The patterns are POSIX-shell
idioms, so on Windows it measures a Git Bash or WSL session and not a PowerShell one. The rules it
scores against by default are one author's. Write your own as a small JSON file and it scores
against those instead.

Needs Python 3.11 or newer. No packages, no network.

## What it touches

It reads Claude Code's session records under `~/.claude/projects/` and its `settings.json`,
read-only, plus your own expectations file if you have one. It runs `git` only while saving a
baseline, and only read-only commands against its own script, to record which version produced the
measurement. It writes a baseline only when you ask, under `~/.local/state/session-bash-audit/`, and
refuses to overwrite one that is already there. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the procedures your agent follows, and how to read each row.
- [`references/research.md`](references/research.md): the first baseline, the root causes behind
  each pattern, how the permission modes behave, and why a hook that corrects the agent silently was
  rejected.
