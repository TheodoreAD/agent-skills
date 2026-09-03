---
status: idea
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

Nothing here is settled and nothing is implemented. The corpus currently has **one** location rule,
written once and never stated as a rule: `plan-docs` resolves its config as `$PLAN_DOCS_CONFIG` →
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

**9. One skill owns a location; the others ask it rather than re-deriving it.** The `harvest.py`
duplication above is the instance. A second copy of a default is a second thing to migrate when a
rule like this one changes.

**10. A skill can say where it resolved to.** `doctor`, `where`, or a line in the output. A
wrong-directory bug is otherwise invisible, which `plan-docs` learned the expensive way.

## Open questions

[NEEDS CLARIFICATION: **whether `~/plans` and `~/research` stay at the top level or move under one
visible root** (`~/agents/`, say). Top level is shortest, is already in muscle memory, and both are
git repos with remotes and config pointing at them — a move is a migration, not a rename. A shared
root is tidier and makes "the agent stuff" one thing to back up or exclude. This is aesthetics
against migration cost, and the rules above hold either way.]

[NEEDS CLARIFICATION: **whether `$PLAN_DOCS_CONFIG` survives rule 4.** `$XDG_CONFIG_HOME` already
lets a user relocate it, so the bespoke variable is a second way to do one thing. Against removing
it: it is the only way to point at a single config file rather than a directory, which is what the
test suite uses.]

[DECISION: **the sensitive tier keeps its own variable rather than becoming a subdirectory of one
root.** A single root makes it easy to sync or back up both tiers with one gesture, and the entire
purpose of that tier is that it must never leave the machine. Two variables is the cheaper mistake.]

[NEEDS CLARIFICATION: **whether the portability audit should read `scripts/` as well as
`SKILL.md`.** The hard-coded checkout path above is invisible to it today. Against: a script's paths
are guarded by code the audit cannot evaluate — `harvest.py`'s fallback is genuinely harmless
because three other resolutions come first — so a naive scan would report every `Path.home()` as a
finding and bury the real ones. A narrower rule, such as flagging only a literal path with two or
more segments under `$HOME`, might carry its weight.]

## Recommended direction

Adopt rules 1–10 as written, with the two open questions left open — none of them blocks the others.
Then the concrete work is small and mostly deletion:

- give baselines a real home (`$XDG_STATE_HOME/<skill>/`), which retires the "save it into the
  installed copy" instruction on its own;
- have `harvest.py` ask `plans.py` for a store path instead of re-deriving it;
- add `mode=0o700` where directories are created;
- write the table into `skill-authoring`, because the next skill needs the answer before it invents
  a seventh destination.
