---
name: plan-docs
description: "Use when capturing an idea, drafting a design, or tracking work-in-progress in a repo's plans/ directory — creating or updating a plans/YYYY-MM-DD-topic.md file (including a bug, idea or risk turned up incidentally), asking what plans exist or what to work on next, here or across every repo, choosing or advancing a status, retiring a landed/abandoned plan once its content has a permanent home elsewhere, migrating a repo's legacy monolithic plan file (PLAN.md, DESIGN.md, ...) onto this convention, or auditing AGENTS.md/README.md/docs for planning/status/future-work content that has drifted in and belongs in plans/ instead. Also owns where a plan file may live and what may be written in it: a work, client or employer repo that cannot take a plans/ directory keeps its plans in the store outside every working tree ($PLANS_HOME), routed per repo by config; an idea with no repo yet is filed unscoped and graduated later; and no plan committed to a repo you publish may name a client, employer or internal project."
---

# Structured, stateful plan files

Convention for `plans/YYYY-MM-DD-topic.md` — one file per idea or design, a YAML frontmatter
`status` field so its lifecycle is visible without opening it, and a firm rule that `plans/` stays a
working set, not a permanent archive.

Rationale, prior art, and worked examples:
[`references/design-rationale.md`](references/design-rationale.md).

## Run the script, don't re-derive it

[`scripts/plans.py`](scripts/plans.py) (stdlib, read-only unless stated) owns every mechanical step
below: which directory a plan goes in, creating it with correct frontmatter, the status index, the
anchored tag greps, the promotion and deletion gates, inbound references. Run it instead of opening
files to work the answer out — the file reads are the expensive part, and each command below is one
of them.

**Write the path out in full on every call.** Shell variables do not survive between an agent's Bash
calls — only the working directory does — so a `P=…` assignment is empty by the next command and
every invocation below is the whole path:

```shell
python3 ~/.agents/skills/plan-docs/scripts/plans.py list
```

**Start here.** Three commands answer most sessions:

| the question                           | the command                        |
| -------------------------------------- | ---------------------------------- |
| what is open? what should I work on?   | `list` — see "Asking what is open" |
| where does a new plan go, and write it | `new <topic>`                      |
| is this machine set up, and how?       | `doctor`                           |

The rest, in the order the lifecycle reaches them:

```shell
python3 <path> tags --tag DEFERRED          # anchored, across every plan this repo can see
python3 <path> set-status <file> planned    # refuses if the gate for that status fails
python3 <path> refs <file>                  # inbound references, before retiring
python3 <path> archive --search <words>     # a retired plan, back out of git history
python3 <path> move <file> --to store       # a repo switching where it keeps plans
python3 <path> scan                         # no private name reaches a repo you publish
python3 <path> repos --search <words>       # what each repo is for, to route a plan by
python3 <path> new <topic> --unscoped       # an idea with no repo yet
python3 <path> graduate <file> --to <repo>  # …once it has one
python3 <path> where                        # which directories this repo reads and writes
python3 <path> install --explain            # set the machine up, one decision at a time
```

## Where a plan file goes

A plan normally lives in the repo it describes. That is unavailable in most employer and client
repos — a `plans/` directory is not yours to add there — so there are three routes, and which one a
repo uses is **configuration, never a judgement call made per session**:

| route     | plans live in                                       | for                                    |
| --------- | --------------------------------------------------- | -------------------------------------- |
| **repo**  | `<repo>/plans/`, committed with the code            | a repo you own                         |
| **store** | `$PLANS_HOME/<repo's path under the projects root>` | a repo that can't hold its own plans   |
| **both**  | reads both, writes one                              | a repo mid-switch, in either direction |

The store mirrors each repo's path at whatever depth it sits, so a `<root>/<project>/<repo>` clone
gets `<store>/<root>/<project>/<repo>` — no slug, no collision between two clients' `api`. The path
is computed from the repo root, not from the working directory.

**`where` exiting 3 is a question, not a failure.** It means no rule covers this repo. Ask the user
which route it should use, then record the answer. Never pick a side silently: guessing "repo"
writes a directory into someone else's repository, and guessing "store" hides the plan somewhere the
user never named.

**Record it with `config set`, never by editing the TOML yourself:**

```shell
python3 <path> config set roots.<root-name> repo         # a whole root
python3 <path> config set repos.<root>/<repo> store      # one repo, beats any root rule
python3 <path> config set default store                  # everything unmatched
python3 <path> config set view.idea_limit 20             # how many ideas a listing shows
```

It preserves every comment in the file — those comments carry the reasoning for each key — replaces
a commented-out example in place, and rejects a value the config's own schema will not accept,
restoring the file rather than leaving it broken. A key's table is whatever precedes its first dot,
so a repo path full of dots stays one key.

```toml
projects_root = "~/projects"
store = "~/plans"
default = "store" # omit it and an unmatched repo asks instead

[roots]
"github.com-personal" = "repo" # longest matching prefix wins

[repos] # an exact repo entry beats any root entry
"github.com-acme/legacy-api" = { mode = "both", write = "store" }
```

### Environment assumptions, and setting them up

`$PLANS_HOME` (default `~/plans`) is the store; `projects_root` (default `~/projects`) is the root
the mirrored paths are relative to; `$PLAN_DOCS_CONFIG` overrides the config location.

**Setting up a machine is a walkthrough, and you run it.** The script never prompts — it has to keep
working when a human runs it by hand, and an interactive prompt inside an agent's Bash call hangs
with nothing to type into. So the decisions are printed as data and **you** are the interactive
surface:

1. `python3 <path> install --explain` — what it would create, then one block per decision, each with
   what it is, what is currently set, what it would suggest, and what it costs to get wrong. Writes
   nothing.
2. Put each decision to the user with `AskUserQuestion`, using the `suggest` line as the recommended
   option and the `cost` line as the description. Do not skip to the defaults: the `default` and
   `public_roots` answers decide whether plans land in repos the user does not own and whether
   `scan` will catch a client's name.
3. Record each answer with `config set` (above). Never edit the TOML by hand.
4. `python3 <path> install` — idempotent: writes the config skeleton if there isn't one (never over
   an existing one), creates the store as a **local git repository with no remote**, creates the
   repo-less area.
5. `python3 <path> doctor` — confirm it took, and that no problem is left.

It asks one question per unrouted root only when no `default` covers them; with a default set, that
answer is already given and the walkthrough stays short.

`python3 <path> uninstall` reverses it: it removes the config but **keeps the store**, because the
store is the only copy of those plans; deleting it takes `--purge-store --force` and a deliberate
decision.

### Is this machine set up, and what is in it

```shell
python3 <path> doctor
```

One call for the whole picture: config and store locations, which roots are enrolled and by which
rule, which repos actually hold plans, a tally by status and open tag, and a **problems** list — a
store that is not a git repository or has lost its git identity, a store with a remote, an unset
`PLANS_HOME`, a repo holding plans that no rule routes. Run it when something behaves oddly and
before trusting `archive`, which retrieves nothing from a store with no git history.

It aggregates by root and names an individual repo only when that repo holds plans — a per-repo
listing is one row per clone on the machine, which is a roster of employers and clients. Its output
is for setting the machine up, never for pasting into a repo you publish.

The no-remote default is the design, not an oversight: local history is the benefit, and one
personal remote accumulating several clients' internal architecture is the outcome to avoid. Adding
a remote is a per-root decision against that employer's actual policy, never a convenience. Never
symlink the store, or a subtree of it, into a work repo — that puts the content back inside the tree
repo-scoped agent reads walk. Treat it as unbacked-up unless something was arranged deliberately.

## Never let a client's identity reach a repo you publish

The store exists because work repos can't hold plans. The mirror image of that is the rule that
matters more: **a plan committed to a repo you publish must not name the client, employer, project
or repo it came from.** Not the org, not the internal project name, not the work email address, not
the ticket prefix. A plan about work for someone else can still be written — describe the shape ("a
work root with a `<project>/<repo>` hierarchy", "a client repo under review pressure") and keep the
specifics in the store, where they belong.

**Run `python3 <path> scan` before committing to any repo that is or might become public**, and
`--mode staged` immediately before the commit itself. It exits non-zero on a hit. The terms come
from the machine — every root, project and repo name under `projects_root` that is not under a
`public_roots` entry, each root name also split into its organisation (so the client behind
`<org>.com-<host>-<team>` is caught in an `@<org>.com` address too), plus `[private] extra` — so a
newly cloned client is covered with nothing to maintain, and the list itself never has to be written
into a public repo.

`[private] extra` is not optional decoration: an employer with no repo on this machine has no
directory to derive from, and is invisible to the scan until someone adds it.

**Never hand-roll the pattern for an audit.** `scan --list-terms` prints the list the scanner
derives; `scan --mode history` is the audit. A regex written by hand is a narrower list whose edges
you cannot see, and it will look like a clean result. Confirmed live 2026-08-29: a repo was surveyed
with a hand-written alternation covering the addresses already known about, declared clean apart
from those, purged — and the scanner then found an employer's name in that repo's first two commits
from 2021, in four branches, because the hand-written pattern omitted one work root the derived list
had all along.

Two failure modes to handle correctly:

- **A generic hit.** A work repo named `tools` or `settings` matches ordinary English. Put that one
  name in the config's `[private] ignore` list — never widen `public_roots`, which silences a whole
  organisation's worth of names to fix one word.
- **Writing about a hit reintroduces it.** A plan explaining what leaked, a rationale page using a
  real name as an example, a commit message quoting the offending line — each puts the term straight
  back into the tree the scan just cleared. Measured three times in one session, 2026-08-29, each
  caught by `--mode staged` before the commit. Reference the thing by where it lives — the commits
  and the `scan --mode history` command that print it — not by quoting it.
- **A hit in pushed history.** `--mode history` scans every commit. Redacting the working tree does
  not remove anything from a published repo; purging history means a force-push and a support
  request, and it is the user's call, not an edit to make quietly. Report it, name the commits,
  stop.

Confirmed live 2026-08-28: this repo had already published a plan whose measurement table listed six
employer/client root directory names, plus one client's internal `<project>/<repo>` path — written
by an agent with no rule telling it not to, into a repo whose own README advertises it as public.

## Plans that belong to no repo yet

An idea, task or exploration that has not earned a repo goes to `$PLANS_HOME/_unscoped/`:

```shell
python3 <path> new <topic> --unscoped     # works anywhere, including outside any git repo
python3 <path> list --scope unscoped      # the repo-less backlog on its own
python3 <path> graduate <file> --to <path inside the new repo>
```

`graduate` routes the file through the destination repo's own rule — into its committed `plans/`, or
into that repo's store directory — and stamps the `repo:` frontmatter when the destination is the
store. Do it the moment the repo appears, not later: an unscoped plan whose work has moved into a
repo is a plan nobody will find again.

## Asking what is open

**Answer "what plans do we have" and "what should I work on" with one `list` call, not by opening
plan files.** The scope is chosen for you:

```shell
python3 <path> list                       # auto: this repo when in one, the machine when not
python3 <path> list --scope family        # every repo, always
python3 <path> list --stale 14            # only what nobody has touched in a fortnight
python3 <path> list --tag DEFERRED        # only plans carrying that open tag
python3 <path> list --all                 # include landed, abandoned and superseded
python3 <path> list --limit 0             # every idea, uncapped
```

`--scope auto` is the default and resolves to `repo` inside a routed repo, `family` outside any repo
and inside the store itself — so a session that has cd'd nowhere in particular gets the machine-wide
answer without asking for it.

**Repo scope reads the repo's `plans/`, its store mirror, _and_ the unscoped area, whatever the
route says.** A route decides where a _write_ lands; letting it decide what a _read_ can see is what
kept unscoped plans invisible from every repo on a machine whose roots are all `mode = "repo"`
(confirmed 2026-08-29) — the plans with no other route back to attention were the ones nothing
surfaced.

**Output is bounded, and only the `idea` tier is capped.** `in-progress`, `blocked` and `planned`
are limited by how much work can actually be in flight; `idea` grows forever, so it is the only
group whose cost is unbounded. The cap is `[view] idea_limit` (default 10), `--limit` overrides per
call, and the footer always says how many rows were elided. **Never read a capped listing as the
whole set** — if you are about to conclude something about every plan, pass `--limit 0` first.

Two things only `--scope family` reports, because no per-repo command can see them:

- **`depends_on` as a blocked-by view**, summarised as counts. The plans themselves print under
  `--scope repo` in the repo being waited on, as "waiting on this repo" — that is where the wait is
  actionable, and printing every edge machine-wide is a section that grows with the corpus exactly
  the way the idea tier does (measured 2026-08-29: 22 of 81 lines).
- **Status drift.** A status outside the vocabulary — `done` where `landed` is defined, or a
  free-form paragraph where an enum belongs — is only visible across repos, since each repo's own
  gate sees one repo. Both were found on this view's first real run, 2026-08-29.

**A terminal-status plan is hidden from the rows but never silently.** `plans/` is a working set
that empties out, so a `landed` plan still sitting in one is a retirement owed; the footer counts
them and `--all` shows them. That count is often the most useful line in the output.

Like `repos`, family output names work repos: use it to decide what to work on, never paste it into
a repo you publish.

## Which repo does a plan belong to?

When content could plausibly belong to more than one repo, don't grep repos to decide, and don't
guess:

```shell
python3 <path> repos --search "<the words the plan is about>"
```

It prints every repo under the projects root with its route and a one-line description — the
config's `[about]` entry, else that repo's README first line — ranked by the search words. Take the
top two or three and put them to the user as `AskUserQuestion` options with those descriptions as
the option text: an informed guess to confirm, not an open question. Record a better description
with `python3 <path> describe <repo> "<what belongs there>"` whenever a README's own line turns out
to be a poor answer. That listing names work repos, so it is for choosing a destination — never
paste it into a repo you publish.

## Creating a plan

`python3 <path> new <topic>` — kebab-case topic, one file per topic. It writes `YYYY-MM-DD-topic.md`
in the route's write directory with the frontmatter already correct:

```yaml
---
status: idea
updated: YYYY-MM-DD
repo: <origin URL> # store-held plans only — location no longer names the repo
---
```

Body: `## Context` → `## Open questions` (each unresolved point marked with an inline
`[NEEDS CLARIFICATION: ...]` tag) → `## Recommended direction` (rough, non-prescriptive).

**This applies to anything turned up incidentally, not only to deliberate design requests.** A bug
worth fixing later, an idea worth brainstorming, a risk worth mitigating — each gets its own file.
Never leave it as future-work prose in `README.md`, `AGENTS.md`, a docs page, or a code comment:
those describe current state, and prose has no status field, so nothing ever prompts anyone back.
(Confirmed live 2026-08-23: a known test-coverage gap sat in a `README.md` as "a real gap… not yet
fixed" instead of a plan file, invisible to anything scanning `plans/` for open work.)

## Committing a plan file

**Run the repo's quality gate before every `plans/*.md` commit** — create, update, or retirement.
"Just markdown" is not an exemption: formatters reflow prose, and doc-only commits that skipped the
gate are the single most common cause of red CI in repos using this convention.

A store-held plan is committed to the **store's** git repository instead, and no work repo's gate
applies to it. Commit it there anyway, in the same session that wrote it: the store's history is the
only record that plan has, and an uncommitted file in a directory nobody browses is the same as no
plan at all.

## Tags

Five inline markers, all `[SHOUTY-WORD: text]`, so the judgment calls below become greps instead of
re-reads, and nothing costly is lost when a file is deleted.

| tag                        | means                                           | at retirement                          |
| -------------------------- | ----------------------------------------------- | -------------------------------------- |
| `[NEEDS CLARIFICATION: …]` | open question                                   | must be zero to leave `idea`           |
| `[DECISION: …]`            | settled choice + why it beat the alternatives   | → design rationale                     |
| `[PITFALL: …]`             | non-obvious trap, confirmed by hitting it       | → design rationale                     |
| `[DEFERRED: …]`            | consciously scoped out, still wanted            | → an open plan; **blocks deletion**    |
| `[UNVERIFIED: …]`          | designed or implemented but not actually proven | → verify or defer; **blocks `landed`** |

**Five is the whole vocabulary.** Don't add a sixth — inconsistently-applied tags are worse than
none, because the greps still return results and get trusted while being incomplete. There is
deliberately no `[VERIFIED:]`; the _absence_ of `[UNVERIFIED:` is the signal.

Not bare `TODO`/`FIXME` — those collide with code comments, making `rg TODO` useless in a repo that
also contains source.

**Tag the claim, not the section.** One tag per discrete, individually-extractable fact. A tag
scoped to "everything below this heading" can't be migrated mechanically, which is the whole point.

**A tag opens its own line**, starting a paragraph or immediately following a list marker. Searches
for it must be anchored the same way — a bare `rg '\[DEFERRED:'` matches every prose _mention_ of a
tag, so any document discussing this convention reports a false backlog. `plans.py tags` is the
anchoring, applied across every directory the repo's route reads:

```shell
python3 <path> tags --tag DEFERRED               # the whole backlog, no file opened
python3 <path> tags --file <file>.md             # one plan, all five tags
```

Tag at status transitions, not while drafting — those are the moments someone is already reading
closely. Retrofit an existing corpus in one pass rather than lazily; half-tagged is the failure mode
above.

## Promoting a plan

**Promote in place, in the same file — never split into a second file for the same topic.** Resolve
every `NEEDS CLARIFICATION` first, then `python3 <path> set-status <file> planned` — it runs that
gate and refuses while any remain, so a refusal is the answer, not an obstacle to route around with
`--force`. Rewrite the body as `## Context` → `## Design` (numbered subsections, one per
file/component touched, rationale inline) → `## Files touched` → `## Verification`.

As work proceeds, bump `status` again with the same command (it also stamps `updated`); the sections
don't change:

- `in-progress` — actively being built.
- `blocked on <reason>` — stalled on something external, with the reason in the status line itself,
  e.g. `blocked on the upstream API adding a /search endpoint`.
- `landed` — implemented and verified. Transient; see "Retiring a plan".
- `abandoned` — killed before landing. Also transient.
- `superseded by plans/<file>.md` — a landed plan whose decision was later reversed by another.

Optional `depends_on: [<repo-name>, ...]` frontmatter names sibling repos this plan can't fully land
without. Omit it for the ordinary single-repo case.

## Where retired content goes

Three destinations, named by **role** rather than by path, because every repo lays them out
differently — and a repo may have no separate directory for the middle two at all:

| role                 | what belongs there                                              |
| -------------------- | --------------------------------------------------------------- |
| **the code itself**  | changes needing no explanation beyond the code and its comments |
| **usage docs**       | anything about how a person or agent uses the result            |
| **design rationale** | settled decisions, rejected alternatives, confirmed pitfalls    |

Map these onto whatever the repo has — a `docs/` tree, a `contributing/` tree, a package's own
`references/`, a section of `AGENTS.md`, a code comment. The requirement is _somewhere durable and
findable_, never a specific directory name. If a repo has no obvious home for design rationale,
picking one is part of the first retirement, not a reason to skip it.

## Retiring a plan

On reaching `landed`, `abandoned`, or an old `superseded by ...`: `plans/` is a working set that
empties out — but nothing genuinely costly to work out gets silently dropped. Deleting the file
takes it off the working set, not out of the repository: the drafting commits, its final state and
the `## Migrated to` commit all stay reachable through git, and `python3 <path> archive` is how they
are read back — see "Getting a retired plan back" below. That is what makes the deletion cheap, and
it is why a plan is only ever kept in version control.

**A store-held plan retires exactly like a repo-held one, and is deleted the same way.** The usage
docs and design rationale still go into the repo the plan is _about_ — updating a repo's own docs is
an ordinary contribution, available even where adding a `plans/` directory is not, and it would be
owed just the same if the planning had happened in a tracker instead. What is left after that
migration is reasoning that belongs to nobody but you, and it stays in the store's git history,
which is why the store is a git repository at all.

**Triage the file's content by lifecycle first.** Split by what each passage _is_, never by how long
the file is: a long file that is all one lifecycle stays one file, while a short one mixing several
gets split.

| kind               | example                                   | destination                         |
| ------------------ | ----------------------------------------- | ----------------------------------- |
| settled decision   | why tool X beat tool Y, with the evidence | design rationale                    |
| pitfall            | a trap confirmed by hitting it            | design rationale                    |
| code contract      | signatures, flags, behavior               | already in code/tests/README — drop |
| verification log   | "ran it, it worked", dry-run transcripts  | drop, except the unverified residue |
| **live open work** | anything still wanted but not done        | **an open plan — see step 2**       |

Code contracts and verification logs are usually the bulk of the deletable volume.

1. **Default: preserve.** Assume debugging, investigation and rejected-alternative reasoning has
   future value unless it is already written down elsewhere. Often it is — check the existing docs
   before assuming new rationale content is needed.
   - **In a repo family, check the sibling repo that owns the concern**, not just this one. A plan
     that designed something later extracted elsewhere describes a decision that repo now owns and
     keeps current; migrating it here ships a second, diverging copy that reads as authoritative.
     Point at the owning repo instead, and migrate only what it genuinely doesn't cover.
2. **A plan carrying live unfinished work is not deletable.** Run the deletion gate and move
   everything it finds into a plan that stays, before going further:
   ```shell
   python3 <path> tags --file <file>.md --tag DEFERRED
   python3 <path> tags --file <file>.md --tag UNVERIFIED
   ```
   Prefer appending to an existing open plan that already owns the concern over spawning a new file.
   On an untagged legacy plan, grep prose instead
   (`deferred|not yet|follow-up|TODO|known
   limitation`) and read what it finds.
3. **Find inbound references before starting, not after** — `python3 <path> refs <file>.md`. The
   count decides whether this is one commit or several. It searches the **whole repo** (code
   comments and docstrings cite plan paths too) plus the store, on the bare filename rather than the
   full `plans/` path, since short-form references are the easy miss.
4. **Add a `## Migrated to` section** naming each destination, and name what you deliberately did
   _not_ migrate and why. **Commit this addition on its own, before deleting the file** —
   add-and-delete in one commit means the section is never recorded in history at all, which defeats
   the point of writing it.
   - Organize the rationale home by **the question a reader arrives with**, not one file per retired
     plan — that just reproduces each plan's lifecycle mixing under a new name. Expect the most
     valuable file to be one that existed in no single plan.
   - Before dropping anything as "already in the code", check that it is. Verify what you migrate
     too: prose written months ago about a module drifts, and a plan is not evidence about current
     behavior.
5. **Fix the references from step 3, then delete the file** — only once step 4 is genuinely covered.
   If there is any doubt whether something worth keeping was captured, ask before deleting; it is a
   one-way door once the commit lands.
   - Don't blindly swap the old path for the new one at every hit. A reference to a specific quoted
     section title needs that title updated to match where the content actually landed — a valid
     path aimed at a renamed heading still dangles. Some cited content is already duplicated at a
     third location; point at that copy rather than migrating a second one. And some references are
     better rewritten than repointed: "X landed in `<plan>`" just becomes "X landed."
   - The finishing grep should return **no live pointers**, which is not the same as zero hits.
     Provenance legitimately survives ("extracted from the now-retired `plans/X.md`") and should —
     but must say _retired_, so a reader knows not to go looking.
6. **Run the repo's gate again before committing the reference fixes.** Editing many
   comments/docstrings in one pass is exactly what quietly trips a line-length rule.

## Getting a retired plan back

Deleting a plan is only cheap because the file is still in the repository, and that is only true in
practice if getting one back is a single command rather than an archaeology session:

```shell
python3 <path> archive                      # every plan deleted from this repo's plans/, newest first
python3 <path> archive --search "<phrase>"  # only the ones whose content ever contained it
python3 <path> archive --show <file>        # print one back, as it stood the moment before deletion
python3 <path> archive --file <file>        # one plan's whole lifecycle: drafting, landing, retirement
python3 <path> archive --all                # every repo on the machine, plus the store's own history
```

Each row carries the plan's final `status` and its `## Migrated to` destinations, which are usually
the real answer — the content is in a doc somewhere, and only the reasoning that had no home is in
the deleted file itself. Nothing is written and no file is restored: a retired plan comes back on
stdout, and if the work is live again it earns a new plan file rather than a resurrected one.

Three things worth knowing before trusting a result:

- **`--search` matches across line breaks**, so a phrase the formatter has since reflowed is still
  found. It also searches every version of every retired plan, not just the final one — so a passage
  cut two commits before the deletion still matches, and `--show` will not contain it. Use `--file`
  to find the commit that did, and read that one with `git show <sha>:<path>`.
- **A plan that moved between the repo and the store is not retired**, though its old location's
  history says it was deleted. Those rows say `still live` and name where it is; go read that file.
- **A store with no git repository archives nothing.** `archive` says so in its header when it finds
  one. Fix it with `python3 <path> install` _before_ retiring anything held there.

## Migrating a legacy single plan file

A repo predating this convention often has one big `PLAN.md`/`DESIGN.md`/`NOTES.md` mixing unrelated
threads at different lifecycle stages. Don't retire it as a unit — split by thread first, then apply
the lifecycle above to each piece:

1. Sort its sections into threads: implemented and verified (→ `landed`), genuinely still undecided
   or stalled (→ its own new plan file, `status: idea` or `blocked on <reason>`), and simply
   inaccurate now (a design later replaced — drop it, it has no destination). One legacy file
   routinely becomes zero, one, or several plans, not one.
2. Run the `landed` threads through "Retiring a plan" immediately, in the same pass — no reason to
   copy them into `plans/` only to retire them a moment later.
3. Give each still-open thread a real plan file with correct frontmatter, reformatted into the
   standard sections — not a leftover fragment of the old file's prose.
4. Only once every thread has a home does the legacy file get its own `## Migrated to` section
   (naming every destination) and go through the normal commit-then-delete sequence.

## Don't stash future work in prose docs

Applies to any narrative doc — `README.md` and docs pages included, not only `AGENTS.md`. Each
should describe the repo as it is right now. A known bug, an unfinished feature or an open risk
belongs in its own plan file, linked from the doc if it is worth a pointer, never spelled out there:
prose future-work rots into a permanently-true-sounding sentence, or worse, an already-fixed problem
still calling itself "not yet fixed".

`AGENTS.md` (or any equivalent instructions file) gets the strictest version: instructions for
developing and deploying the repo only — never planning, ideation, or a status report. Three drifts
worth auditing for:

- **Dated status narrative.** "Status: implemented and exercised live 2026-08-14" is a changelog
  entry, not an instruction — true today, stale tomorrow. Trim to an undated statement of what is
  architecturally true now, and drop the "as of `<date>`, confirmed working, tests pass" framing
  entirely; that belongs in a commit message.
- **Stale implementation claims.** "These functions are stubs", "not yet confirmed" — silently rots
  once the work lands. Don't prose-review these: grep the code for the thing described (e.g.
  `rg NotImplementedError` before trusting a docstring that claims it) before deciding whether a
  passage is accurate, superseded, or safe to cut.
- **Speculative asides.** "This might be cheaper a different way once X is understood" is a musing,
  not an instruction. Either it is a real open question deserving its own plan file, or it is colour
  already captured in the rationale home and can just be dropped.
