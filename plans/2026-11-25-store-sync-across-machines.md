---
status: in-progress
updated: 2026-11-25
---

# Store sync across machines

## Context

The user is starting to develop on several machines, each running agent CLIs from whichever vendor
and subscription is at hand. [DECISION: "remote agents" means **machines the user controls**, any
vendor's CLI on them. Vendor-hosted sandboxes (Claude Code on the web, Codex cloud, Copilot's coding
agent, Cursor background agents, Jules) are out of scope: reaching the store from one would mean a
setup in that vendor's own environment format, which is the vendor lock-in the user ruled out on
2026-11-25. A sandbox that does get used sees the plans inside the repo it cloned, and nothing is
built for it.]

What already travels, measured 2026-11-25 on the primary machine with `plans.py doctor`:

- **221 of 229 plans live in a personal repo's own `plans/`** and move with that repo's git. Nothing
  to do for them.
- **The shareable store (`~/plans`) has a private remote and holds 25 files**: 8 unscoped ideas and
  16 filed against another personal repo, waiting for `absorb` there.
- **The sensitive store has no remote, by design**, and keeps none. Work stays on the machine that
  holds it; a second machine doing the same employer's work keeps its own local sensitive store, or
  uses `sanctioned_remotes` toward the employer's own host on a work device.

The store is a plain git repo and `plans.py` a stdlib script, so nothing about it is tied to a
vendor. The gap is that **`plans.py` has a pushing side and no pulling side**:

- `push` scans `@{upstream}..<tip>` and pushes the pinned tip. It never fetches, so on a second
  machine `@{upstream}` is whatever was last fetched by hand, and a push after the other machine
  pushed is refused as non-fast-forward. `_run_push` prints git's own error, so it fails loudly —
  but there is no command to resolve it, and the next session reaches for a bare `git pull`.
- `absorb`, run at the start of a session, reads the local store only. A plan filed with
  `new --for <repo>` on machine A is invisible to a session in that repo on machine B until someone
  fetches by hand. That failure is silent: `absorb` is documented as silent when nothing is waiting,
  so "nothing waiting" and "never fetched" print the same nothing.
- `absorb --apply` deletes the filed plan from the store. If machine A edited that plan while
  machine B absorbed it, the next merge is a modify/delete conflict.

## Decisions

- [DECISION 2026-11-25: **automate as much as possible, inside the commands.** The user's reason:
  unsynced local commits accumulate into conflicts. Refined in discussion: conflicts come from the
  same file changing on two machines between syncs, not from the commit count, and this store has
  exactly those files. In its last 200 commits, three store-held design plans for one repo were
  edited 16, 15 and 9 times, and several `_unscoped/` plans 6–7 times each. Syncing on every write
  narrows that window; nothing closes it.]
- [DECISION 2026-11-25: **the automation lives in `plans.py` commands, never in a timer or a git
  hook.** A background merge into the store can land while a session is midway through committing
  into the shared index. Inside the commands it is visible in their output, which is the home rule
  that agents should know what runs.]
- [DECISION 2026-11-25: **per-machine config, default no remote, and the setup asks.** In the user's
  words: "the default should be no remote, but the skill should ask the user their preference. the
  goal is to allow new users to set this up without requiring them to set up the remote." A store
  with no remote is a complete, supported setup, and every sync step is a silent no-op there. The
  `install` walkthrough asks whether this machine keeps its plans locally or syncs them through a
  git remote, and records the answer.]
- [DECISION 2026-11-25: **one key, `sync = "off" | "manual" | "auto"`, default `"off"`.** A remote's
  presence implies nothing; the key alone decides, read on every command. The modes:
  - `off`: no network from any command. `sync` and `push` say the machine is set to local-only and
    name the key that changes it.
  - `manual`: nothing syncs on its own. `sync` does it on request, and `absorb` warns when the last
    fetch is older than a threshold (`FETCH_HEAD`'s mtime), without fetching.
  - `auto`: what "Recommended direction" items 3 and 4 describe.]
- [DECISION 2026-11-25: **the skill may add the store's remote, only on a URL the user has
  confirmed.** This reverses "never adds a remote" for this one case. The script never prompts, so
  the confirmation is the agent's: it shows the user the exact store, remote name and URL, asks, and
  only then runs the command, which takes the URL as an explicit argument and has a `--dry-run`. It
  adds a remote only to the shareable store; on the sensitive store it refuses unless the URL is
  covered by `sanctioned_remotes`, the existing rule for a work device. It never creates the
  repository on a host. That stays the user's step, which keeps the skill host-neutral and needs no
  host API or token.]

- [DECISION 2026-11-25: **joining a remote never loses a local plan.** In the user's words: "if
  there is already a plans store that is not tied to a remote, it should offer the user to bring in
  the remote repo and add the extra local contents to that, so no plan info is lost." The skill
  assesses the machine and offers; the user confirms. The cases `install` (and `doctor`) must tell
  apart, read from the store itself:
  - **no store**: clone the remote.
  - **a store holding nothing but what `install` generated** (`README.md`, no plan): replace it with
    a clone of the remote, after saying so.
  - **a store with plans and no remote**: _adopt_ — see "Joining a remote" below.
  - **a store whose remote is a different URL**: refuse and name both URLs. Which one is right is
    the user's call, never inferred.]

## Joining a remote: adopting a local store

Merge the remote's history into the local store with `--allow-unrelated-histories`, keeping both
histories, so every local commit survives and nothing is re-authored. Then resolve the known
conflicts in code before committing the merge, and stop on anything else. Before touching the store,
print what would happen as a dry run: plans only on this machine, plans only on the remote, and
every conflict with how it will be resolved. That report is what the user confirms.

- The push after an adoption publishes the **whole local history**, since every local commit is
  outgoing. `push` already scans `@{upstream}..<tip>`, which covers it, but the report should say
  how many commits are going out for the first time.
- **The branch name can differ.** `TheodoreAD/plans` uses `master`, and a store created by
  `git init` on a machine where `init.defaultBranch = main` is on `main`. Adopt takes the remote's
  default branch name, renaming the local branch before the merge, or the first push creates a
  second branch on the remote.

## What can conflict outside individual plans

Read from the store's tracked files (`README.md`, `repos.toml`, the plan files and the plan
attachment folders) and from what `plans.py` writes there, 2026-11-25.

1. **`repos.toml`, the link table. The main risk, in steady state and in adoption alike.**
   `render_links` writes it sorted, so two machines linking two different repositories that sort
   next to each other edit the same hunk, and git reports a conflict for what is really a union.
   Worse, two machines can link **one identity to two different folders**: a textual conflict on the
   same line, or a clean merge when the two spellings differ in case (`TheodoreAD/x`,
   `theodoread/x`), which git sees as two keys and `identity_key` treats as one — breaking "one name
   never names two folders" with no conflict reported. Resolve it in code, never with git's line
   merge: read both sides (`git show :2:repos.toml`, `:3:`), union by `identity_key`, write with
   `render_links`. The same identity pointing at two folders keeps the remote's folder, and
   `git mv`s the local plans from the other folder into it, reported.
2. **`README.md`, generated by `install` when absent.** On adoption both sides have one: identical
   when the same skill version wrote both, an add/add conflict when the template changed between
   them. It is generated text, so take the remote's.
3. **The `updated:` line in a plan's frontmatter.** Every edit rewrites it, so two machines editing
   _different sections_ of one plan still conflict on line 3. Without handling it, concurrent edits
   to one plan never merge cleanly. Resolve that line to the later date in code, and re-run the
   merge for the rest of the file. A differing `status:` is a real conflict and is reported.
4. **Line endings, and this is where Windows comes in.** `plans.py` writes with `Path.write_text` 22
   times, none passing `newline=`, so on Windows every file it writes has CRLF line endings. Whether
   those reach the commit depends on that machine's `core.autocrlf`. Committed with CRLF, every line
   differs from the Linux copy, and any concurrent edit becomes a whole-file conflict. Fix both
   ends: `plans.py` writes `newline="\n"`, and `install` commits a `.gitattributes`
   (`* text=auto eol=lf`) in each store, so the store's own setting decides rather than the
   machine's. That file is itself a new shared file; identical on both sides, it merges without
   conflict.
5. **One path, two plans.** Two machines filing the same date and topic for one repo create one path
   with two contents, an add/add conflict. Rare. Keep the remote's at its path, and write the local
   one beside it with a suffix, reported. Never pick one.
6. **Delete against edit.** `absorb --apply` on one machine deletes a filed plan that the other
   machine edited: a modify/delete conflict. Keep the edited version in the store and report it as
   still waiting for absorb.
7. **Not a conflict, but lost across machines: `_attachments/`.** An attachment over the commit
   limit goes to `_attachments/`, which `.git/info/exclude` keeps out of git on purpose. A plan
   synced to another machine then names a file that is not there. `doctor` on the receiving machine
   should report the missing attachment rather than leave the reference silently dangling.

Machine-local and therefore safe: the config file, the ledgers in the state directory (attached to a
plan only when it is finished), and `.git/info/exclude`.

## Windows, next

The next machine to join is a Windows one, so these are prerequisites rather than follow-ups:

- the line-ending fix, item 4 above, with a test on the existing Windows CI leg proving a written
  plan has LF bytes;
- every path written into `repos.toml` or a commit pathspec stays POSIX (`as_posix()`), already true
  of the places read on 2026-11-25, and covered by a Windows test of `link`;
- the config at `~/.config/plan-conveyor/config.toml`, the Linux layout aligned on 2026-11-08, with
  the legacy `%APPDATA%` copy read while it is the only one; `install` on that machine says which it
  found;
- a case-insensitive filesystem: two store folders differing only in letter case collapse into one
  on Windows. The link table's `identity_key` already prevents that for one repository; the dry run
  should still flag any pair of paths that are equal under `casefold()`.

[DECISION 2026-11-25: the Windows machine is **personal**. Its shareable store joins the same remote
as this machine's; a sensitive store there, if it has one, stays local. The adoption dry run still
prints the machine's `device` setting before anything else, since the next machine may not be
personal.]

## Progress, 2026-11-25

Built in this repo, all in `skills/plan-conveyor/scripts/plans.py`, tested in
`tests/unit/test_plan_sync.py`, and documented in the skill's "Several machines" section:

- `.gitattributes` at this repo's root, and LF on every `write_text` in `plans.py`; `install` writes
  and commits a `.gitattributes` in each store.
- The `sync` key, `sync`, `join` (with `--dry-run`), auto-sync after a store `commit`, the fetch at
  `absorb`, `doctor`'s mode and staleness, and the `install --explain` question.
- Resolvers for items 1, 2, 3, 5 and 6 below; `--cc` in the push scan. Each resolver and the flag
  were broken once to confirm a test fails.
- Item 7: `doctor` lists local attachments a plan names that are not on this machine, in a section
  of their own rather than as problems. `join` prints the device first, and the dry run flags paths
  equal under `casefold()`. Both were deferred earlier on 2026-11-25 and built the same day.

Where the build differs from the direction below:

- A store holding nothing but generated files is **adopted**, not replaced: the merge keeps its one
  commit and takes the remote's README. Same result, and no special case that deletes anything.
- `save_links` commits the link table without syncing; the plan commit that follows it in the same
  command does, so nothing stays local in practice.

What is left:

- Rollout on this machine, done 2026-11-25: pushed, re-installed through `inv ai.install-skills`,
  `config set sync auto`, `install` committed both stores' `.gitattributes`, `sync` pushed the
  shareable store. On the Windows machine: install the skills, `install --explain`,
  `join <url> --dry-run`, `join`, `config set sync auto`, `sync`.
- [UNVERIFIED: a real Windows machine joining. The Windows CI leg runs the sync tests; nothing has
  run on that machine yet.]

## Recommended direction

1. **A `sync` subcommand**: fetch the store's remote, merge (not rebase — the store is shared by
   every session on a machine, and rebasing rewrites commits another session may be about to push),
   then run the existing `push` path. Plain git against whatever remote the store has, no host API.
   Same tier rule as `push`: the sensitive store reports "nothing to sync". [PITFALL: **the push
   scan must cover the merge commit's own content.** `git log -p` shows no diff for a merge commit,
   so a conflict resolution that introduces new text is published unscanned. Use `--cc` (or `-m`) in
   the scan's `git log` once merges can be outgoing.]
2. **Resolve the known conflicts in code** (items 1, 2, 3, 5 and 6 of "What can conflict outside
   individual plans"). **On any other conflict, abort the merge and report** the conflicting paths,
   leaving the local commits in place. Every session on the machine shares the store's working tree,
   so a store left mid-merge blocks every other session. The agent resolves it deliberately with
   `sync` afterwards.
3. **With `sync = "auto"`**, every store-writing command — `commit`, `absorb --apply`, a filing with
   `new --for` or `--unscoped` once committed — ends by syncing, and says so in its output. A
   `--no-sync` flag keeps one commit local. A refused scan leaves the commit local and names the
   lines, as `push` does today.
4. **With `sync = "auto"`, `absorb` fetches first**, with a short timeout. When offline it warns
   that it read the local copy and carries on, so "nothing waiting" and "could not check" no longer
   print the same nothing.
5. **`doctor` reports the sync mode and staleness**: commits behind the remote after a fetch, and
   the age of the last fetch.
6. **`install --explain` asks the sync question**: local only (`off`), or sync through a git remote,
   then `manual` or `auto` and the URL, confirmed before the remote is added (decisions above). It
   also tells apart the four store states and offers clone, replace or adopt (decisions above).
7. **Skill text**: a "several machines" section in `plan-conveyor`'s `SKILL.md`, and the matching
   README update. Per machine: `install --explain`, with the config kept per machine and out of git,
   as already documented. Then the three modes, the confirmed remote, and the rule that the
   sensitive store never leaves its machine. The "What this skill reads, runs and writes" section
   changes with it: **Runs** gains `git fetch`, `merge` and `remote add`; **Network** changes from
   "only `push`" to the sync modes; the "never adds a remote" wording becomes "adds one only on a
   URL you confirmed".
