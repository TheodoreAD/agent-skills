# invoke-task-conventions-taudelta

Naming and wiring rules for invoke tasks, and what a task rename really costs.

A project's `tasks.py` starts tidy and grows by one task at a time. A year later `inv --list` holds
`apt.base` beside `install-fonts` beside `check_ssh`, nobody can guess a name without looking it up,
and renaming anything feels risky because nobody knows where the old name is cited. Agents make it
worse in a specific way: each session names its new task by whatever pattern it saw last.

invoke-task-conventions-taudelta gives the agent a small set of rules for naming and wiring tasks in
[invoke](https://www.pyinvoke.org/), plus the checklist for renaming one safely. It is one author's
rulings. Where you would rule differently, fork it and change the rules.

## Who it fits

It fits any Python project that uses invoke. The naming rules and the wiring traps are about invoke
itself and hold in any `tasks.py`. The examples, and one rule about which task names an agent may
run without asking, come from the author's own repo family, and the skill says so; substitute your
own repos where it names them.

It does not fit a project on `make`, `just`, `nox` or `poe`. The naming advice would transfer, but
most of the skill is about how invoke builds its task list, and none of that applies.

## What you get

- Three naming rules: task names lead with a verb (`apt.install-base`, not `apt.base`), a name a CLI
  convention already owns stays as it is (`status`, `list`, `check`), and a few namespaces are
  themselves the action (`test.unit`, `clean.caches`).
- One verb per meaning across the whole project, and the tip that a task's docstring usually already
  contains its right name.
- A rename checklist: the Python function name changes with the task name, prose far outside the
  module cites it, a scripted rename cannot tell the two spellings apart, and a Markdown heading
  that contains the name changes that page's anchor.
- The wiring traps: how an imported task gets published a second time under a name nobody declared,
  and how a namespace disappears when a consumer repo stops importing it.
- Why a task must never run anything that waits for typed input through invoke. On Python 3.14,
  invoke can't forward keystrokes to the child at all, and before that it echoes them, a password
  included.

## What it looks like

Ask "add a task that installs the fonts" in the `apt` namespace, and the agent names it
`apt.install-fonts`, because the namespace is the subject and the task is the action. Ask it to tidy
`inv --list`, and it sorts every name into one of four piles before changing anything: already
verb-first, a community convention kept on purpose, an action namespace, or a real violation. The
second pile is the one that stops it "fixing" `gnome.status` into `gnome.show-status`, which would
be more consistent and worse.

## What went wrong while writing it

The rules were tried on two real repos on 2026-08-24, and most of the checklist is what that pass
hit. A 24-task rename touched 53 files, including docs, a Dockerfile, CI workflows and another
repo's documentation. The rename script wrote the Python spelling of a task name into user-facing
output labels, and the test suite stayed green throughout, because no test reads label text. The
wiring audit then found four published tasks nobody had declared, one of which another repo had
already documented as the real name.

The skill's own trigger was measured the same way. On 2026-08-31 the request "our automation scripts
have grown messy and inconsistent, where do I start cleaning them up?" selected no skill at all,
three runs out of three, because every trigger word in the description named the tool rather than
the problem. The description was reworded and re-measured before it shipped.

## Why not just grep and rename

A task rename looks like a string substitution and is a code change with a wide blast radius. The
failures it causes are quiet: a stale name in a doc still reads fine, a label with the wrong
spelling still prints, and a task published twice still runs. The checklist is the list of those
quiet failures, each found by hitting it.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill invoke-task-conventions-taudelta
```

Then ask things like "what should I call this task?", "is this rename worth it?", or "our task list
is a mess, where do I start?".

## What it touches

Nothing. It ships no script, so it reads and writes nothing itself; it only guides the agent.

## Read more

- [`SKILL.md`](SKILL.md): the full rules your agent follows.
- [`references/rationale.md`](references/rationale.md): the prior art each rule came from (Azure
  CLI's command guidelines among them), and the evidence behind the rename and wiring sections.
