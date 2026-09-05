# Why this skill says what it says

## Why "self-update on friction" is a convention, not one skill's quirk

Surfaced while designing `session-harvest`: a routing decision it made mid-design was genuinely
ambiguous (should "new skills should default to self-update mechanics" be a personal preference, or
a documented convention?) — asked rather than guessed, and the answer was "a convention, stated
somewhere shared." That is itself an instance of the pattern.

The underlying reason it needs stating: a convention skill that never revises itself from what
actually happens when it is used goes stale the way any unmaintained doc does, except worse, because
nobody re-reads a `SKILL.md` the way they would re-read `AGENTS.md`. It is loaded, followed, and
never looked at again. Building the revision step into the skill is the only thing that closes that
loop.

## Why a skill about shipping skills must describe the portable mechanism

Until 2026-08-27 this content lived in a skill that said skills ship by declaring them in one
particular machine-setup repo's config file and running that repo's own task runner. That was
accurate, and it was the exact problem: the skill telling people how to ship a skill described a
mechanism only its author could run. A reader without that repo had a path they did not have and a
command they could not run.

The general form is worth keeping: **a skill about a workflow must describe the workflow's portable
mechanism, not the author's automation around it.** Automation is the right place for "and here is
how my machine does it"; the skill is not. Where a machine-specific example genuinely helps, label
it as one example rather than as the procedure.

## Why the split from `mcp-server-shipping` (2026-08-28)

One skill covered both "ship a personal MCP server" and "ship an Agent Skill", with a `description`
naming both. That violated the rule the skill itself stated: two responsibilities in one
description, so every prompt about editing a skill had to win against text half-about
`uv tool
install` and `claude mcp add`, and vice versa.

The trigger test settles it. "I want to register an MCP server for Claude Code" and "I edited a
SKILL.md, how do I deploy it" are different requests with no overlap in vocabulary; nothing about
one should have to compete with the other. After the split each description covers one request
shape, and both got shorter.

What stayed together deliberately: the MCP repo dev loop (`repo-tasks`, `inv dev-env.setup`,
`uv run inv` in automation) stayed with `mcp-server-shipping`, because those repos _are_ the MCP
servers — it is that skill's subject matter, not general authoring advice.

## Why a bundled script gets stdlib-or-PEP-723 and never a venv (2026-08-28)

Researched when a plan put a real script inside a skill for the first time and "does it need a
venv?" was raised as an open worry. It does not, and a venv per skill is not the convention — it is
the thing the convention exists to avoid.

[agentskills.io's "Using scripts in skills"](https://agentskills.io/skill-creation/using-scripts) is
the spec-level guidance and describes exactly two tiers, neither of which is a virtual environment:
a **one-off command** referenced straight from `SKILL.md` through a runner that resolves at
invocation (`uvx`, `pipx run`, `npx`, `bunx`, `deno run`, `go run`), pinned to a version and with no
`scripts/` directory at all; or a **self-contained script** in `scripts/` declaring its dependencies
**inline** — PEP 723 for Python, run with `uv run`, verbatim "no separate manifest file or install
step required". Every other language on the page gets the same treatment (Deno `npm:` specifiers,
Bun auto-install, Ruby's `bundler/inline`).

Where venv-per-skill does appear is
[anthropics/skills discussion #117](https://github.com/anthropics/skills/discussions/117), and the
problem there is not ours: **cloud skills from different vendors sharing one sandbox**, where skill
A needs `pandas==2.1` and skill B needs `2.2`. The debated answers are venv-per-skill,
container-per- skill for untrusted code, and — rejected as fragile — `sys.path` namespacing. The one
point of consensus worth carrying is that dependencies should be _declared_ even before isolation is
enforced, so a conflict is detectable rather than silent; PEP 723 is that declaration. A single
user's own skills on their own machine have no multi-tenant conflict to isolate.

Extracted 2026-09-01 from the now-retired `plans/2026-08-28-cross-repo-plan-store.md`, which
researched it while deciding where `plan-docs`' own script would live.

## Why "editing the installed copy" gets its own emphasis

It is the failure that produces no error. A copy under `~/.agents/skills/<name>/` is writable, the
edit appears to work, and the skill visibly behaves differently in the current session. Everything
after that is silent: the next install overwrites it, no other machine sees it, and there is no
commit to review. Compare with the alternative failures in this workflow — a missing push produces
"my change didn't take effect", which at least prompts investigation.

The same asymmetry is why the redeploy sequence spells out the push step rather than assuming it.
The installer clones from the remote, so "committed" and "deployed" are separated by a step that
produces no symptom when skipped except the change quietly not existing.

## Why a skill's directories are keyed by its bare `name` (2026-09-03)

The question asked was whether to derive a per-skill config directory from the unique parts of a git
remote — org or user, plus repo — so that two authors publishing a `plan-docs` cannot collide in
`~/.config/plan-docs/`. The collision is real; the URL is not the answer, for three independent
reasons, and the first is fatal on its own.

**The input does not exist at runtime.** An installed skill is not a checkout. Verified 2026-09-02:
`~/.agents/skills/<name>/` holds `SKILL.md`, `references/` and `scripts/` and nothing else — no
`.git`, no remote, and a `--global` install writes no `skills-lock.json` anywhere under `~`,
`~/.agents` or `~/.claude`. A scheme whose input is absent on every machine that would run it is not
a scheme.

**Flat application names are the Linux convention, and that is measurable rather than arguable.**
`platformdirs` is the de-facto answer to this exact question — pip, poetry and black all depend on
it — and it takes an `appauthor` argument precisely so it can build `%APPDATA%\Author\App` on
Windows and `~/Library/Application Support/Author/App` on macOS. On this machine, platformdirs
4.11.7:

```text
user_config_dir("plan-docs", "TheodoreAD")  ->  ~/.config/plan-docs
user_config_dir("plan-docs")                ->  ~/.config/plan-docs
```

The author segment is **discarded on Linux**, deliberately, by the library that encodes the
convention. Putting an org in the path would be importing a Windows shape.

**And it would key the config more finely than the thing it configures.** `~/.agents/skills/<name>/`
is already a flat name-keyed namespace — two same-named skills cannot coexist installed, and
`fitness.py inventory` reports that as a collision — so a URL key solves a conflict the installer
already refuses to create, while breaking the case that does happen: a **fork or a repo rename**
silently orphans the user's existing config although the skill behaves identically. The name is
stable across both; the URL is not. It is also already gated (`test_name_matches_directory`,
`NAME_PATTERN`) and is the identity the rest of the toolchain uses.

Two follow-ons worth keeping so neither is rediscovered:

- **`platformdirs`' semantics are copied, the dependency is not.** These scripts run under a bare
  `python3` with nothing installed; the XDG lookup is about ten lines. Cite the library as the
  reason the semantics are what they are.
- **No escape hatch is built.** If a skill ever genuinely must disambiguate, the ecosystem-native
  option is a key in its own frontmatter `metadata:` — cheap, explicit, no URL. It is not built now
  because no collision exists, the installer refuses to create one, and an **optional** frontmatter
  key is backward-compatible, so adding it the day it is needed costs nothing that adding it today
  saves. Building it now ships an untested path for a hypothetical; recording the shape is the whole
  of the preparation required.

The one Linux precedent for an organisation in the path is reverse-DNS application IDs — Flatpak's
`~/.var/app/<app-id>/config`, GNOME's `org.gnome.Foo`. It does not transfer: those are desktop
applications with a registered app ID, and a skill's ecosystem key is its bare name.

## Why a guarded dev-environment path is a defect, with no severity tier (2026-09-04)

`harvest.py` carried `Path.home() / "projects" / "github.com-personal" / "agent-skills"` — the
author's own checkout — as a last-resort fallback, reached only after an explicit argument and a
walk up from the script. It misled nobody, and it was first recorded as a note rather than a finding
for exactly that reason.

The rule it breaks has no carve-out for harmless instances, and the remedy is `delete it` either
way, so a severity tier would buy nothing and cost something real: **it invites every instance to be
argued down into the lower bucket, which is how a rule stops being one.** The guard is also what
makes such a path survive review — it only ever helps one machine and is invisible everywhere else,
right up until someone else's directory happens to match.

**The `bare`/`declared` split elsewhere in the portability audit is not the precedent it looks
like.** That split exists because a declared assumption is _legitimately_ declared: the skill told
its reader, and the finding is genuinely closed. A guarded dev-environment path is neither
legitimate nor closed, merely not currently hurting anyone. Same word, opposite situations.

The related lesson is where the class of defect was hiding: the portability audit read `SKILL.md`
and nothing else, so every machine assumption in `scripts/` was outside its view. Teaching it to
read scripts needed a rule narrow enough not to bury real findings under correct ones — a literal
path of **two or more segments** under `$HOME`, which catches
`~/projects/github.com-personal/agent-skills` and ignores `Path.home() / ".claude"`, a
single-segment reference to another tool's directory that a different rule already governs.

## Why the `0700` check was built and then deleted (2026-09-03 → 2026-09-04)

Worth recording because the finished rule — set the mode at creation, never check it afterwards —
reads like an obvious half-measure to anyone who did not watch the other half be removed.

The gap was real and total. No `mkdir` anywhere in the corpus passed a mode, so every directory took
the default masked by the process umask; measured under umask `002`, `~/plans-sensitive` was **775**
— world-readable and group-writable, for the tier whose entire purpose is holding work that must not
leave the machine — with `~` at 755 gating nothing above it. Neither the skill body nor any
rationale page mentioned permissions, a mode or `chmod` anywhere: the dimension had never been
considered, as opposed to considered and dismissed.

What was verified before calling it an exposure, and is the reason severity stayed low: the controls
the design actually leans on were all intact. The sensitive tier is a git repo with **no remote
configured**, and the shareable tier's remote was confirmed private through `gh api`. The design was
holding at the layer it was designed at; what was unset was the layer below.

So `install` gained `mode=0o700` and `doctor` gained a warning — and the warning was deleted the
next day, when the user simplified the premise to **assume the Linux machine is single-user**. That
removes the population the severity argument turned on, which the finding's own caveat had already
named: the low severity was a property of this machine, not of the design. On Windows the check was
worse than useless, since `st_mode` is synthesised from file attributes, so a directory reads as
world-accessible and the warning fires forever on a concept that does not exist there, naming a
remedy the reader cannot run.

**The asymmetry is the durable part: a free default is worth keeping, a warning nobody can act on is
not.** Passing the mode costs nothing — a umask can only narrow it, Windows ignores it, so there is
no branch and no capability test — while checking it costs a permanent false positive on one
platform.
