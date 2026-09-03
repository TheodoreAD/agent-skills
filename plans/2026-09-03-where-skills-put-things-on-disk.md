---
status: planned
updated: 2026-09-03
---

# Where a skill is allowed to put things on disk

## Context

Asked by the user 2026-09-03, before deciding anything else: revisit where all the skills do
business. `~/research` and `~/plans` are short and readable but may not be conventional; `projects/`
is not a convention either, so "it's not XDG" may not be a hard rule. Configuration probably belongs
in the standard config directory, and performance history or stats in the standard data one. Then:
reason about whatever else needs a general rule, so there are rules rather than a decision per
script.

Settled below and not yet implemented. The corpus currently has **one** location rule, written once
and never stated as a rule: `plan-docs` resolves its config as `$PLAN_DOCS_CONFIG` →
`$XDG_CONFIG_HOME` → `~/.config/plan-docs/`. Everything else was decided per-script.

## What is actually on disk today

Read out of the five scripts 2026-09-03, not from the docs:

| location                                | who                | kind                          |
| --------------------------------------- | ------------------ | ----------------------------- |
| `$PLANS_HOME` → `~/plans`               | `plan-docs`        | user's material, a git repo   |
| `$PLANS_SENSITIVE_HOME` → sibling of it | `plan-docs`        | user's material, a git repo   |
| `$RESEARCH_HOME` → `~/research`         | `research-library` | user's material, holds clones |
| `$PLAN_DOCS_CONFIG` → `~/.config/…`     | `plan-docs`        | configuration                 |
| `~/.claude/**`, `~/.agents/skills`      | four skills        | **another tool's**, read-only |
| baselines                               | two skills         | **no home at all**            |

Two facts worth pulling out:

- **`$XDG_DATA_HOME` and `$XDG_STATE_HOME` appear nowhere in the corpus.** There is no place for a
  tool's own bookkeeping, which is exactly why `session-bash-audit` ended up telling readers to save
  their baseline inside the installed skill — the destination it should have used does not exist.
- **`harvest.py` re-implements `plans.py`'s defaults.** Lines 1379–1381 carry their own
  `os.environ.get("PLANS_HOME", ~/plans)` and `RESEARCH_HOME` fallbacks. Two copies of a default
  that must agree, in two skills, with nothing keeping them in step.

[PITFALL: **the portability audit cannot see any of this, because it reads `SKILL.md` and nothing
else.** `harvest.py:800` carries `Path.home() / "projects" / "github.com-personal" / "agent-skills"`
as a hard-coded fallback — the author's own checkout path, in shipped code. It is guarded (explicit
argument first, then walking up from the script, then this, then an error), so it helps the author
and harms nobody, which is why it is a note and not a defect. The defect is that a whole class of
machine assumption lives in `scripts/` where the audit has never looked.]

## The axis that decides everything else

**Is this the user's material, or the tool's bookkeeping?** Every other question falls out of that
one, and it is what justifies `~/plans` against XDG orthodoxy rather than merely excusing it.

- **The user's material** is opened, grepped, edited, and version-controlled by a human. Plans and
  the research library are documents; `~/plans` has a remote and gets `git log` run on it. XDG's
  base directories are for what an _application_ manages on the user's behalf — and the companion
  **xdg-user-dirs** spec exists precisely because user-facing content does not belong in them.
  Nobody puts `~/Documents` under `~/.local/share`. On that reading `~/plans`, `~/research` and
  `~/projects` are all the same category and none of them is a convention violation.
- **The tool's bookkeeping** — config, history, stats, baselines — is never browsed, so a short path
  buys nothing and the standard locations cost nothing.

## The proposed rules

**1. Six destinations, and each has one meaning.**

| destination                                   | what goes there                                      | in this corpus              |
| --------------------------------------------- | ---------------------------------------------------- | --------------------------- |
| `$HOME/<name>`                                | the user's own material: browsable, often a git repo | `plans`, `research`         |
| `$XDG_CONFIG_HOME` → `~/.config/<skill>/`     | configuration a human edits; no data                 | `plan-docs` already         |
| `$XDG_STATE_HOME` → `~/.local/state/<skill>/` | history, stats, baselines, last-run records          | **the missing one**         |
| `$XDG_DATA_HOME` → `~/.local/share/<skill>/`  | data the tool needs and cannot regenerate            | nothing yet                 |
| `$XDG_CACHE_HOME` → `~/.cache/<skill>/`       | regenerable, safe to delete at any moment            | nothing yet                 |
| `tempfile.mkdtemp()`                          | transient work                                       | never a fixed `/tmp/<name>` |

Two corrections to the sketch this came from, both worth stating because they are easy to get
backwards. Configuration is **`~/.config`**, not `~/.local/config` — `.local` holds `share`, `state`
and `bin`, and config sits beside `.local`, not inside it. And performance history or stats are
**state**, not data: "history" is the specification's own example for `$XDG_STATE_HOME`, and the
distinction is whether losing the file costs the user anything (`share`) or merely a re-measurement
(`state`). Every baseline in this corpus is the second.

**2. A git working tree never goes under an XDG base directory.** You `cd` into it, read its log and
push it; backup and sync tools treat `~/.local/share` as application internals. This is the concrete
reason `~/plans` is right and `~/.local/share/plan-docs/plans` would be wrong, and it generalises:
if the answer to "would a human ever `cd` here" is yes, it is not bookkeeping.

**3. One precedence order, everywhere:** explicit argument → the skill's own environment variable →
`$XDG_*` → default. `plan-docs` already does exactly this for its config; the rule is to stop it
being one function's private habit.

**4. An XDG destination needs no new environment variable — that is the point.** It inherits
`$XDG_*`, which the user already controls. So moving bookkeeping to XDG **removes** variables rather
than adding them, which reverses the caution recorded in
`2026-09-02-skill-output-must-be-actionable-by-its-runner.md` ("a fifth variable is hard to
justify"): that objection applies to inventing `$SKILL_FITNESS_HOME`, not to using
`$XDG_STATE_HOME`. Only a `$HOME`-visible location earns its own variable, because a user may
genuinely want their plans somewhere else.

**5. One directory per skill, named for the skill.** Not per corpus and not per script — skills
install individually and a reader may have one of fourteen.

**6. A skill never writes inside its own installed directory.** The install hub is read-only to
everything, the skill itself included. This follows from "editing the deployed copy is drift" but
nobody had connected that rule to _data_, which is how `--save-baseline $S/references/baselines/…`
got written.

**7. Another tool's directory is read-only, always.** `~/.claude/**` is a harness's private store:
read it, never write it, and report **unavailable** rather than zeros when it is absent — which
`skill-fitness` already does and which is the behaviour to copy.

**8. Permissions are a property of the content, not of the path.** `0700` for anything confidential;
XDG directories get `0700` on creation, which the specification asks for anyway. See
`2026-09-03-sensitive-store-is-world-readable.md`.

**9. One skill owns a location and publishes it as configuration the others read.** The `harvest.py`
duplication above is the instance: two copies of a default that must agree, with nothing keeping
them in step.

[DECISION: **amended 2026-09-04 — "the others _ask_ it" was wrong**, and the wording invited exactly
the mistake `2026-09-03-skill-dependencies-and-bundling.md` refuses. Skills install individually, so
one cannot import another without hard-coding the hub path this very document bans, and a behaviour
that changes with what else is installed is the defect measured on 2026-09-02. The contract is the
**config**, not a call: `$PLANS_HOME` and `~/.config/plan-docs/config.toml` already are the shared
source of truth, and `harvest.py` should read them rather than reach into `plans.py`. Two readers of
one source of truth is not duplication; two hard-coded defaults is.]

**10. A skill can say where it resolved to.** `doctor`, `where`, or a line in the output. A
wrong-directory bug is otherwise invisible, which `plan-docs` learned the expensive way.

## What keys the per-skill directory

Asked by the user 2026-09-03: an automatic way to derive a skill's config directory from unique git
SCM URL components — org/user plus repo — or a better suggestion from community practice.

The motivation is real. Two authors can both publish a skill called `plan-docs`, and if both write
to `~/.config/plan-docs/` they collide. But three separate checks all point away from the URL, and
the first one is fatal on its own.

[DECISION: **the key is the skill's own `name`, and nothing else.** Three independent reasons:

**The input does not exist at runtime.** An installed skill is not a git checkout. Verified
2026-09-02: `~/.agents/skills/plan-docs/` contains `SKILL.md`, `references/` and `scripts/` and
nothing else — no `.git`, no remote, and a `--global` install writes no `skills-lock.json` anywhere
under `~`, `~/.agents` or `~/.claude`. There is no URL on the machine to derive anything from. A
scheme whose input is missing on every machine that would run it is not a scheme.

**Community practice on Linux is a flat application name, and this is measurable rather than
arguable.** `platformdirs` is the de-facto answer to this exact question — pip, poetry and black all
depend on it — and it takes an `appauthor` argument specifically so it can build
`%APPDATA%\Author\App` on Windows and `~/Library/Application Support/Author/App` on macOS. Run on
this machine, 2026-09-03, platformdirs 4.11.7:

```text
user_config_dir("plan-docs", "TheodoreAD")  ->  ~/.config/plan-docs
user_config_dir("plan-docs")                ->  ~/.config/plan-docs
```

**The author segment is discarded on Linux**, deliberately, by the library that encodes the
convention. Adding org/user to the path would be importing a Windows shape.

**The config would be keyed more finely than the thing it configures.** `~/.agents/skills/<name>/`
is already a flat, name-keyed namespace: two same-named skills cannot coexist installed, and
`fitness.py inventory` reports exactly that as a collision. Keying config by URL solves a conflict
the installer already refuses to create, and would break the case that does happen — a **fork**, or
a repo rename, silently orphans the user's existing config while the skill still behaves the same.
The name is stable across both; the URL is not.]

The name is also already the right kind of key, and already gated:
`tests/unit/test_skill_layout.py::test_name_matches_directory` enforces that the frontmatter `name`
equals the directory name, and `NAME_PATTERN` constrains it to filesystem-safe characters. So
`~/.config/<name>/`, `~/.local/state/<name>/` are unique-within-an-install and CI-verified by a test
that already exists. It is also the identity the rest of the toolchain uses — what the harness
matches on, and what `skills add --skill <name>` takes.

[DECISION: **follow `platformdirs`' semantics, do not take the dependency.** These scripts are
stdlib-only on purpose, so they run under a bare `python3` with nothing installed; the XDG lookup is
about ten lines. Copy the semantics, cite the library as the reason they are what they are.]

[DECISION: **no escape hatch is built.** If a skill ever genuinely needs to disambiguate, the
ecosystem-native option is a key in its own frontmatter `metadata:`, which this corpus already uses
(`metadata: family: meta` in `skill-fitness`) — cheap, explicit, needs no URL. It is not built now,
for three reasons: no collision exists, the installer refuses to create one (two same-named skills
cannot both occupy `~/.agents/skills/<name>/`), and an **optional** frontmatter key is
backward-compatible, so adding it the day it is needed costs nothing that adding it today saves.
Building it now ships an untested code path for a hypothetical. Recording the shape here is the
whole of the preparation required.]

The one Linux precedent for putting an organisation in the path is worth naming so it is not
rediscovered: reverse-DNS application IDs, as Flatpak uses for `~/.var/app/<app-id>/config` and
GNOME for `org.gnome.Foo`. It does not transfer — those are desktop applications with a registered
app ID, and a skill has no such identifier; its ecosystem key is the bare name.

## Decisions

[DECISION: **`~/plans`, `~/plans-sensitive` and `~/research` stay exactly where they are**, for
parity with `~/projects` — settled by the user 2026-09-03. They are the user's material by the axis
above, and a move would be a migration touching git remotes and config for aesthetics.]

[DECISION: **no hard-coded local path in a script, and least of all one tied to the author's dev
environment** — stated by the user 2026-09-03 alongside the rules above. That makes
`harvest.py:800`'s fallback to `~/projects/github.com-personal/agent-skills` a defect rather than
the harmless note it was recorded as, and it answers the open question below about whether the
portability audit should read `scripts/`: it has to, because this decision is unenforceable
otherwise.]

[DECISION: **`$PLAN_DOCS_CONFIG` stays, and it is not an exception to rule 4.** Checked rather than
argued from the rule: it names a **file**, `$XDG_CONFIG_HOME` can only redirect a **directory**, and
`tests/unit/test_plan_store.py:85` depends on exactly that — every test points the whole config at
one path under `tmp_path` and would otherwise have to build an XDG tree. So it is not a second way
to do one thing; it does something XDG cannot express. Rule 4 is therefore stated precisely as **no
new variable for a location XDG already addresses**, which puts this outside its scope rather than
against it.]

[DECISION: **the sensitive tier keeps its own variable rather than becoming a subdirectory of one
root.** A single root makes it easy to sync or back up both tiers with one gesture, and the entire
purpose of that tier is that it must never leave the machine. Two variables is the cheaper mistake.]

[DECISION: **the portability audit reads `scripts/` as well as `SKILL.md`** — forced by the
no-hard-coded-paths decision above, which nothing would otherwise enforce. The objection stands and
shapes the rule rather than blocking it: a script's paths are guarded by code the audit cannot
evaluate, so a naive scan reporting every `Path.home()` would bury the real findings under the
correct ones. The narrow rule is what to build — **a literal path of two or more segments under
`$HOME`**, which catches `~/projects/github.com-personal/agent-skills` and ignores
`Path.home() / ".claude"`, a single-segment reference to another tool's directory that rule 7
already governs.]

[DECISION: **a guarded last-resort path is the same finding, with no severity tier.** `harvest.py`'s
fallback is reached only after an explicit argument and a walk up from the script, so it misleads
nobody — but the decision above is "no hard-coded local path, least of all a dev-environment one",
without a carve-out for harmless ones, and the remedy is `delete it` either way. A tier would buy
nothing and cost something real: it invites every instance to be argued down into the lower bucket,
which is how a rule stops being one.

**And the `bare`/`declared` split is not the precedent it looks like.** That split exists because a
declared assumption is _legitimately_ declared — the skill told its reader, and the finding is
genuinely closed. A guarded dev-environment path is not legitimate and not closed; it is merely not
currently hurting anyone. Same word, opposite situations.]

## Recommended direction

Rules 1–10 are adopted, the visible stores stay where they are, and the per-skill key is the skill's
own `name`. The concrete work is small and mostly deletion:

- **a shared stdlib path resolver**, ten lines with `platformdirs`' semantics, so
  `~/.config/<name>/` and `~/.local/state/<name>/` are computed once rather than per script;
- **give baselines a real home** (`$XDG_STATE_HOME/<name>/`), which retires the "save it into the
  installed copy" instruction on its own;
- **delete `harvest.py:800`'s dev-environment fallback**, and have `harvest.py` ask `plans.py` for a
  store path instead of re-deriving it;
- **`mode=0o700`** where directories are created;
- **teach the portability audit to read `scripts/`** with the two-segment rule, so the
  no-hard-coded-paths decision is enforced rather than remembered;
- **write the destination table into `skill-authoring`**, because the next skill needs the answer
  before it invents a seventh destination.

The resolver comes first and everything else consumes it, which is also what keeps rule 9 honest:
one owner per location has to mean one implementation, not one per skill.
