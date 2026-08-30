---
status: in-progress
updated: 2026-08-30
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

All four are settled; each answer is a `[DECISION:]` under "Recommended direction". What is left
open is in "What is still not done", at the end.

## Recommended direction

Six changes. Ordered so each is independently shippable and testable; the sixth was found while
finishing the other five.

### 1. Make the per-repo view read everything about this repo

[DECISION: **the per-repo listing reads the repo's `plans/`, the repo's store mirror, and
`_unscoped/`, regardless of route.** This is the same argument `family_plans` already makes and the
same fix: discovery must not depend on the config being complete. Routing decides where a _write_
lands; it should never decide what a _read_ can see. Measured 2026-08-29: under this machine's
`mode = "repo"` root, no unscoped plan is reachable from any repo, and the unscoped area is where
ideas with no home go — the set most in need of resurfacing is the set nothing surfaces.]

Rows stay labelled by `where` (`repo` / `store` / `unscoped`) so the origin is never ambiguous.

### 2. Merge `list` and `backlog` into one command with a scope axis

[DECISION: **`list` keeps the name, `backlog` is gone, and every citation was fixed in the same
commit.** Settled with the user 2026-08-29 against keeping both as aliases. `list` is the name an
agent guesses cold, and an alias pair is exactly the surface bloat the merge existed to remove. The
citation sweep was smaller than feared: `~/AGENTS.md` cites only `scan`, and `design-rationale.md`
uses "backlog" as a noun rather than as a command.]

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

[DECISION: **the default cap is 10, and staleness is `--stale DAYS` on the listing rather than a
`next` command.** The cap was measured, not guessed: at 10 the whole-machine listing is 64 lines
against 117 before. The staleness shape was settled with the user 2026-08-29 — a `next` command
implies a ranking the script cannot honestly produce beyond status tier and age, and adding a 21st
subcommand to a surface being deliberately shrunk is the wrong trade. The prose tells the agent how
to read the filter.]

[PITFALL: **capping one tier only moves an unbounded cost unless every unbounded section is
bounded.** With the idea tier capped, `depends_on` became the largest section in the family listing
— 22 of 81 lines, measured 2026-08-29, and growing with the corpus exactly as the ideas had. Fixed
by summarising edges as per-repo counts in family scope and printing the actionable list, "waiting
on this repo", in repo scope, where it is bounded by definition and is information no command
produced before. The general lesson: after capping the obvious tier, re-measure and look for what is
now largest, rather than assuming the cap solved the problem.]

[PITFALL: **hiding terminal-status plans silently would have broken the convention it serves.**
Merging the two commands gave repo scope family scope's "hide landed/abandoned" default, which the
pre-merge `list` did not have. But `plans/` is a working set that empties out, so a `landed` plan
still sitting in one is a retirement owed — hiding it with no trace removes the only thing that ever
prompts the retirement. Resolved with a footer counting them, which says the same thing in one line
instead of N. Caught by an existing test failing, not by review.]

### 4. A guided setup, as `install --explain`

[DECISION: **the walkthrough is a flag on `install`, not a new `init` command.** `config init`
already exists and means "write the skeleton", so a top-level `init` would be the third thing in
this tool called some form of "init" and the second naming collision this plan had to resolve. A dry
run of the verb that does the work reads correctly and adds no command.]

[DECISION: **the script stays non-interactive; the agent is the interactive surface.** An
interactive prompt inside a Bash call hangs the session with nothing to type into, and the script
has to keep working when a human runs it by hand. So `install --explain` prints the decisions as
_data_ — for each: what it is, what is currently set, what it would suggest, and what it costs to
get wrong — and `SKILL.md` instructs the agent to walk them with `AskUserQuestion` and write the
answers back.]

The write-back is the piece that did not exist. `SKILL.md` said "record the answer in the config"
and left the agent hand-editing TOML — both the most error-prone thing in the skill and the one step
with no gate behind it. `config set <key> <value>` closes it.

[DECISION: **`config set` edits lines surgically, and the answer was already in the repo.**
`describe` had done exactly this since it was written — find the table header, drop any existing
line for the key, insert — so the open question resolved by reading the code rather than by
prototyping. Generalised to any key: the table is what precedes the first dot and only when that is
a known table name, since a `[repos]` key is a path full of dots. Values are encoded by handing the
argument to `tomllib` and seeing whether it already parses, so `10` stays an integer and a bare
`store` becomes a string with no second encoder able to disagree with the reader. A vendored
`tomlkit` was never needed and would have broken the stdlib-only constraint.]

[PITFALL: **validate-after-write leaves a broken config behind.** The first version wrote the value
and then re-loaded to check it, so a rejected value stayed on disk and every subsequent command
failed on it — a worse failure than the one being reported. The write is now rolled back before the
error is raised. Found by writing the test for the rejection path, not by using it.]

[DECISION: **the walkthrough asks one question per unrouted root only when no `default` covers
them.** With a default set, every such root already has the same answer, and asking anyway turned a
five-question walkthrough into a twelve-question one on this machine — questions the user pays for
whose answers were never in doubt. Measured 2026-08-29 on the first real run.]

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

The "problems" section is what `install` reported only at setup time — a store that lost its git
identity afterwards went unnoticed until `archive` returned nothing and looked like an empty
history.

[PITFALL: **a per-repo enrollment listing is a roster of every employer and client on the machine.**
The first `doctor` printed one row per clone: 80 lines, 71 of them naming a work repo — the exact
artefact this skill's confidentiality rule exists to keep from being produced casually, and the
opposite of the token goal that motivated the command. Routing is a per-root decision, so the root
is the right unit; an individual repo is named only when it actually holds plans. 80 lines to 25.
The general lesson: when a command enumerates repos, ask what the row unit discloses before asking
whether the output is too long — the two problems had the same fix here, but only by luck.]

### Not doing: an MCP server

[DECISION: **this stays a skill; no MCP server, and specifically not both.** Settled with the user
2026-08-29. The reasoning, and what would have to change to revisit it, moved to
`plans/2026-08-29-plan-docs-mcp-wrapper.md` — it is a live question with its own trigger conditions
rather than a footnote to this work, and leaving it here would have kept this plan open on something
deliberately not being worked on.]

### 6. Say so in the description, or none of it triggers

[DECISION: **the skill's `description` now names the question this work was about.** Found while
finishing, 2026-08-29: the description listed capturing, drafting, retiring, migrating and auditing
— and never "what plans do we have" or "what should I work on", which is the request that started
this plan. Every command above could have been perfect and the skill would still not have loaded on
the asking. It cost a trim elsewhere to fit the 1024-char cap, at 1020. The general lesson: a change
that adds a new _reason to invoke a skill_ is not finished until the description says so.]

### Smaller ergonomics found while measuring

[PITFALL: **`SKILL.md`'s `P=~/.agents/skills/plan-docs/scripts/plans.py` is a fiction.** Shell
environment does not persist between Bash tool calls in this harness — only cwd does — so `$P` is
empty on every call after the one that set it. Every real invocation is the full path, and the
documented form has never worked as written. Either document the full path or ship an entry point,
but the latter conflicts with this repo's rule that a skill must work for someone who has only this
repo.]

[DECISION: **the command block is a "start here" of three plus a `<details>` fold, grouped by the
moment each command is needed** — writing a plan down, working on it, retiring it, keeping the
machine right — rather than one flat list of fifteen at equal weight. Lifecycle order was the wrong
axis: an agent does not read the file front to back, it arrives already knowing which moment it is
in.]

[DECISION: **`--json` is on every reading command**, and `SKILL.md` says so once rather than marking
each. `tags`, `refs` and `set-status` were the three that lacked it; a flag available on some
commands and not others costs a retry each time an agent assumes uniformity, which is cheaper to
finish than to document.]

The same non-uniformity exists one level down, on the file argument, and it costs the same retry:
**`tags` takes it as `--file <name>`, `refs` takes it positionally.** Measured 2026-08-30 — a
session ran `refs --file <name>` for seven files in one loop, got `unrecognized arguments: --file`
seven times, and re-ran the whole loop. It had reached for the flag because the command it ran a
minute earlier was `tags --file … --tag DEFERRED`, which is the surrounding usage an agent
pattern-matches off.

Checked before proposing anything, because the split turns out to be principled rather than
accidental: `refs`, `set-status`, `move` and `graduate` **require** a file, and take it
positionally; `tags` and `archive` **default to every plan** and take `--file` as a narrowing
option. That is a defensible rule and the retry still happened, which makes this a documentation
problem rather than a signature one — the rule is discoverable only from `--help` on both commands,
and an agent that has just used one does not run `--help` on the next. Stating it once in the
command block ("the file is positional where it is required, `--file` where it narrows an all-plans
default") is the cheap fix; changing signatures for uniformity would cost more than it buys.

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

## What is still not done

Every change above is implemented, tested and committed, including the three smaller items deferred
on the first pass.

[DECISION: **`--since YYYY-MM-DD` landed as an independent filter, and `--stale`/`--since` treat an
unstamped plan oppositely on purpose.** `--stale` keeps a plan with no `updated` line, `--since`
drops it. That is not an inconsistency: "what has nobody touched" must surface a file with no
evidence of being touched, and "what moved this week" must not claim a file moved when nothing says
it did. Neither bounds default output; the count cap does, because a date window's size is not
predictable, which was settled when the cap was chosen.]

Nothing in this plan's scope is outstanding. Two things it spawned live elsewhere: the MCP wrapper
question in `plans/2026-08-29-plan-docs-mcp-wrapper.md`, and the trigger gate in
`plans/2026-08-22-skill-trigger-quality-review.md`, which now has a concrete first case to test.
