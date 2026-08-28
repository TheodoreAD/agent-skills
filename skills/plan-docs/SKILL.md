---
name: plan-docs
description: "Use when capturing an idea, drafting a design, or tracking work-in-progress in a repo's plans/ directory — creating or updating a plans/YYYY-MM-DD-topic.md file (including for a bug, idea, or risk turned up incidentally by other work, not just a deliberate planning request), choosing or advancing its status, retiring a landed/abandoned plan once its durable content has a permanent home elsewhere in the repo, migrating a repo's legacy monolithic plan file (PLAN.md, DESIGN.md, ...) onto this convention, or auditing AGENTS.md/README.md/docs for planning/status/future-work content that has drifted in and belongs in plans/ instead. Also owns where a plan file is allowed to live: a work, client or employer repo that cannot take a plans/ directory keeps its plans in the store outside every working tree ($PLANS_HOME), routed per repo by config rather than guessed, and a repo can be switched between the two or read both while it moves."
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

```shell
P=~/.agents/skills/plan-docs/scripts/plans.py

python3 $P where                        # which directories this repo reads and writes
python3 $P new <topic>                  # today's file, right directory, frontmatter filled in
python3 $P list                         # status-grouped index + open-tag counts per file
python3 $P tags --tag DEFERRED          # anchored, across every plan this repo can see
python3 $P set-status <file> planned    # refuses if the gate for that status fails
python3 $P refs <file>                  # inbound references, before retiring
python3 $P move <file> --to store       # a repo switching where it keeps plans
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
which route it should use, then record the answer in `~/.config/plan-docs/config.toml` —
`python3 $P config init` writes a commented skeleton. Never pick a side silently: guessing "repo"
writes a directory into someone else's repository, and guessing "store" hides the plan somewhere the
user never named.

```toml
projects_root = "~/projects"
store = "~/plans"
default = "store" # omit it and an unmatched repo asks instead

[roots]
"github.com-personal" = "repo" # longest matching prefix wins

[repos] # an exact repo entry beats any root entry
"github.com-acme/legacy-api" = { mode = "both", write = "store" }
```

### Environment assumptions

`$PLANS_HOME` (default `~/plans`) is the store; `projects_root` (default `~/projects`) is the root
the mirrored paths are relative to; `$PLAN_DOCS_CONFIG` overrides the config location. Nothing
installs any of it — `python3 $P init-store` creates the store as a **local git repository with no
remote**, which is the whole design: local history is the benefit, and one personal remote
accumulating several clients' internal architecture is the outcome to avoid. Adding a remote is a
per-root decision against that employer's actual policy, never a convenience. Never symlink the
store, or a subtree of it, into a work repo — that puts the content back inside the tree repo-scoped
agent reads walk. Treat it as unbacked-up unless something was arranged deliberately.

## Creating a plan

`python3 $P new <topic>` — kebab-case topic, one file per topic. It writes `YYYY-MM-DD-topic.md` in
the route's write directory with the frontmatter already correct:

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
python3 $P tags --tag DEFERRED               # the whole backlog, no file opened
python3 $P tags --file <file>.md             # one plan, all five tags
```

Tag at status transitions, not while drafting — those are the moments someone is already reading
closely. Retrofit an existing corpus in one pass rather than lazily; half-tagged is the failure mode
above.

## Promoting a plan

**Promote in place, in the same file — never split into a second file for the same topic.** Resolve
every `NEEDS CLARIFICATION` first, then `python3 $P set-status <file> planned` — it runs that gate
and refuses while any remain, so a refusal is the answer, not an obstacle to route around with
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
empties out — but nothing genuinely costly to work out gets silently dropped.

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
   python3 $P tags --file <file>.md --tag DEFERRED
   python3 $P tags --file <file>.md --tag UNVERIFIED
   ```
   Prefer appending to an existing open plan that already owns the concern over spawning a new file.
   On an untagged legacy plan, grep prose instead
   (`deferred|not yet|follow-up|TODO|known
   limitation`) and read what it finds.
3. **Find inbound references before starting, not after** — `python3 $P refs <file>.md`. The count
   decides whether this is one commit or several. It searches the **whole repo** (code comments and
   docstrings cite plan paths too) plus the store, on the bare filename rather than the full
   `plans/` path, since short-form references are the easy miss.
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
