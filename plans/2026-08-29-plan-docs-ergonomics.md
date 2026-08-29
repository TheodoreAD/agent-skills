---
status: idea
updated: 2026-08-29
---

## Context

`plan-docs` works, and the corpus it now indexes is large enough to expose what it costs to use. On
this machine, 2026-08-29: 68 open plans across 8 repos plus the unscoped area, 49 of them `idea`.
`plans.py backlog` prints 117 lines to answer "what is open"; `plans.py list` prints 12 to answer it
for one repo. Neither answers the question a session actually opens with — "what should I work on
here" — and the cost of the cross-repo one grows with the corpus, without bound.

Three concrete complaints, in the order they were raised:

1. A session asking "what plans do we have" has to know to run two or three commands and merge them
   itself. The consolidated answer does not exist as a command.
2. `backlog` is unbounded. It is the command whose output grows forever, and it is the one a session
   outside any repo has to run.
3. Setup and inspection are underserved. `install` is a one-shot that reports what it could not do;
   nothing walks the user through the decisions, and nothing answers "what is enrolled, where do
   plans live, how many are there" in one call.

A fourth surfaced while measuring: the per-repo view is **wrong**, not merely narrow. `list` reads
the directories this repo's _route_ names, so under a `mode = "repo"` root it never reads the store
mirror or `_unscoped/`. Unscoped ideas are invisible from every repo on the machine — precisely the
plans with no other route back to attention.

The skill's own `family_plans` already made the opposite argument for `backlog` (plans.py:501):
discovery must not depend on the routing config being complete. That argument was never applied to
the per-repo view.

## Open questions

[NEEDS CLARIFICATION: does the staleness view earn its own command, or is it a flag on the unified
listing? An `in-progress` plan untouched for N days is the one genuinely actionable "what's next"
signal a cross-repo view can see that no per-repo command can. But a `next` command implies a
ranking the script cannot honestly produce — status tier, `updated`, `depends_on` and tag counts are
the only signals available, and everything past those is the agent's judgment. Leaning `--stale N`
on the unified listing, and no `next` command at all: the skill's prose tells the agent how to read
the result. Decide before implementing, because it changes the command count.]

[NEEDS CLARIFICATION: what is the default cap on the `idea` tier? 10 keeps the whole-machine listing
near 30 lines, which is the token budget this work exists to fix. 20 shows roughly a month of this
machine's idea intake. Wrong either way costs a flag, so this should not become a long discussion —
but it should be a measured default, not a guess, and the measurement is one run of the finished
command.]

[NEEDS CLARIFICATION: what happens to `list` and `backlog` as names? They are cited in this repo's
`SKILL.md`, in `~/AGENTS.md`, in `references/design-rationale.md`, and possibly in sibling repos'
docs. Merging them into one command with `--scope` is the right surface, but a hard rename breaks
every citation at once, and a permanent alias is the surface bloat the merge exists to remove.
`plans.py refs` does not help here — it finds references to plan _files_, not to commands. Options:
keep both names as thin aliases for one implementation and drop them at a later deliberate pass;
rename and fix every citation in this commit; or keep `list` as the name and make `backlog` the
alias, since `list` is the one an agent guesses.]

[NEEDS CLARIFICATION: how does `config set` write TOML? The stdlib has `tomllib` for reading and
**no writer**. The config file is a commented skeleton whose comments carry the reasoning for every
key — a naive round-trip through a hand-rolled serializer destroys them, and the skill's rule that
routing is configuration rather than a per-session judgement call rests on those comments being
readable. Surgical line editing (find the key's line, replace its value, append under the right
table if absent) preserves them but is fiddly for `[roots]`/`[repos]` table entries. A vendored
`tomlkit` violates the stdlib-only constraint the script has held so far. This is the highest-risk
piece of the whole plan and should be prototyped before the rest is designed around it.]

## Recommended direction

Five changes. Ordered so each is independently shippable and testable.

### 1. Make the per-repo view read everything about this repo

[DECISION: **the per-repo listing reads the repo's `plans/`, the repo's store mirror, and
`_unscoped/`, regardless of route.** This is the same argument `family_plans` already makes and the
same fix: discovery must not depend on the config being complete. Routing decides where a _write_
lands; it should never decide what a _read_ can see. Measured 2026-08-29: under this machine's
`mode = "repo"` root, no unscoped plan is reachable from any repo, and the unscoped area is where
ideas with no home go — the set most in need of resurfacing is the set nothing surfaces.]

Rows stay labelled by `where` (`repo` / `store` / `unscoped`) so the origin is never ambiguous.

### 2. Merge `list` and `backlog` into one command with a scope axis

They differ only in breadth. `~/AGENTS.md`'s rule against a top-level enum branching into
near-duplicate trees applies directly: scope is one axis, filters are others, and they combine.

- `--scope repo` — this repo, per change 1.
- `--scope family` — every repo on the machine, plus unscoped. Today's `backlog`.
- **Default: auto.** `repo` when cwd is inside a routed repo; `family` when outside any repo, or
  inside the store itself. That absorbs "if we're not in a project repo, or we're in the plans repo"
  as scope detection rather than as a special case anyone has to remember.

Existing filters (`--status`, `--tag`, `--all`) apply at either scope, which they do not today.

### 3. Cap the `idea` tier, and only the `idea` tier

[DECISION: **cap by count, not by time.** A `--since 30d` filter returns nothing in a quiet month
and 40 rows in a busy week, so the token cost stops being predictable — and predictable token cost
is the entire motivation. A count cap is deterministic. `--since` may still be added later as an
independent filter; it must not be the mechanism that bounds default output.]

[DECISION: **never cap the live tiers.** `in-progress`, `blocked` and `planned` are bounded by how
much work a person can actually have in flight — 19 rows machine-wide on 2026-08-29 against 49
`idea`. Only `idea` grows without bound. A limit that can hide in-progress work makes the command
unsafe to trust, and a truncated answer to "what's next" is worse than an untruncated long one. The
cap applies to the `idea` group alone, and the footer says how many were elided and with what flag
to see them.]

Configurable, `[view] idea_limit`, overridable per call with `--limit`.

### 4. A guided `init`

[DECISION: **the script stays non-interactive; the agent is the interactive surface.** An
interactive prompt inside a Bash call hangs the session, and the script has to keep working when a
human runs it by hand. So `init --explain` prints the decisions as _data_ — for each: what it is,
what is currently set, what it would default to, and what it costs to get wrong — and `SKILL.md`
instructs the agent to walk them with `AskUserQuestion` and write the answers back.]

The write-back is the piece that does not exist today. `SKILL.md` currently says "record the answer
in the config" and leaves the agent hand-editing TOML — which is both the most error-prone thing in
the skill and the one step with no gate behind it. `config set <key> <value>`, shaped like the
existing `describe`, closes it. See the open question on how it writes.

Decisions the walkthrough covers: `projects_root`; store location and whether `PLANS_HOME` is
exported; a route per root found under `projects_root` (derivable, so this is confirm-not-ask, one
question per root); whether to set a `default`; `public_roots`; the store's git identity; and
`[private] extra` for an employer with no clone on this machine — the one entry nothing can derive
and the one whose absence is silent.

[DECISION: **the walkthrough does not ask about the display cap.** Nobody has an opinion on a row
limit before they have used the tool, and every question added to init is paid by every user who
just wants the defaults. It ships with a default, `doctor` prints it so it is discoverable, and
`config set` changes it. This is the counter-proposal to asking during init, accepted 2026-08-29.]

### 5. `doctor` — enrollment, locations, tally, and what is broken

[DECISION: **not named `status`.** `set-status` already exists and `status:` is a plan's frontmatter
field, so `plans.py status` would read as "the status of a plan" to every future session. This is
the naming-around-a-collision rule: pick the unambiguous name rather than a near-miss.]

One call, because two calls cost more than one output:

- **Enrollment** — each root and repo under `projects_root`, its route, and where that route's rule
  came from (`repos` entry, `roots` prefix, `default`, or nothing).
- **Locations** — config path, `projects_root`, store and where the store path came from, unscoped
  area, and the effective view settings.
- **Tally** — plans per repo per status, and open-tag totals.
- **Problems** — store is not a git repository; store has no git identity; store has a remote;
  `PLANS_HOME` unset; a repo holding plans that no rule routes; status drift.

`config show` folds into it. The "problems" section is what `install` reports today, which means it
is currently visible only at setup time — a store that loses its git identity afterwards goes
unnoticed until `archive` returns nothing.

### Not doing: an MCP server

[DECISION: **this stays a skill; no MCP server, and specifically not both.** Three reasons, in
weight order. An MCP server's tool schemas load into every session in every repo whether or not
anything is planned, which is a permanent context tax against the token-saving motivation that
started this work. The valuable half of this skill is judgment — what may not be published, when a
plan is deletable, how to triage at retirement — and MCP tools carry no prose a model reads before
deciding, so the skill would survive anyway and the MCP would duplicate only the mechanical half,
leaving two artifacts to keep in sync. And `--json` already is the structured interface; MCP would
change the transport, not the contract. Settled with the user 2026-08-29.]

[DEFERRED: an MCP wrapper if a shell-less harness ever matters, or if trigger reliability turns out
to need always-visible tools. It would be a thin wrapper importing `plans.py`, in its own repo per
the `mcp-server-shipping` skill, never a reimplementation — and `SKILL.md` would say "use the MCP
tools if present, else the script". The trigger-reliability worry has a cheaper fix first: the
`description` wording, which `plans/2026-08-22-skill-trigger-quality-review.md` already owns.]

### Smaller ergonomics found while measuring

[PITFALL: **`SKILL.md`'s `P=~/.agents/skills/plan-docs/scripts/plans.py` is a fiction.** Shell
environment does not persist between Bash tool calls in this harness — only cwd does — so `$P` is
empty on every call after the one that set it. Every real invocation is the full path, and the
documented form has never worked as written. Either document the full path or ship an entry point,
but the latter conflicts with this repo's rule that a skill must work for someone who has only this
repo.]

[DEFERRED: the command block in `SKILL.md` lists 15 commands at equal weight, so an agent opening
the file has to pick. It needs a "start here" of two or three — the unified listing, `new`, and
`where` — with the rest below a fold.]

[DEFERRED: `--json` is available on some commands and not others (`tags`, `refs` and `set-status`
lack it). Each gap costs a retry when an agent assumes the flag is uniform.]

## Verification

Layers 1 and 2 of skill testing are the gate here and both already exist:

- `tests/unit/test_skill_layout.py` — frontmatter, naming, layout, README listing.
- `tests/unit/test_plan_store.py` — behavior, against the `ws` fake-machine fixture. Every change
  above lands with tests there: scope auto-detection at each of the three cwd positions, the idea
  cap leaving live tiers untouched, `config set` preserving the skeleton's comments, `doctor`
  reporting each problem class.

[UNVERIFIED: layers 3 and 4 have no gate. Whether the `description` triggers on "what plan is next"
and "what plans do we have" is exactly what changes here, and nothing in this repo tests it —
`plans/2026-08-22-skill-trigger-quality-review.md` owns that gap. Claude Code's `claude plugin eval`
and `/skill-doctor` are leads worth checking against this repo's non-plugin layout; neither has been
tried. Whether an agent _following_ the revised prose does the right thing is testable only by
dogfooding and transcript measurement, the way `session-bash-audit` does it.]
