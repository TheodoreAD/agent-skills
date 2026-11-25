---
status: idea
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

## Open questions

- [NEEDS CLARIFICATION: the config's shape. One key, for example `sync = "off" | "manual" | "auto"`,
  defaulting to `"off"`, where `"auto"` syncs on every store-writing command and fetches on
  `absorb`. Or does a remote's presence imply `"auto"`, with the key only for opting down? One key
  read on every command is easier to explain than an implied mode.]
- [NEEDS CLARIFICATION: when the user answers "sync" during `install` and gives a URL, does
  `install` add the remote itself? Today the skill never adds a remote anywhere, and `push` refuses
  to. An explicit answer during setup is a recorded decision rather than an inference, which is the
  case for allowing it. It never creates the repository on a host; that stays the user's step, which
  is what keeps the skill host-neutral.]
- Second machine: when the remote already has a store, `install` should clone it rather than create
  an empty store and merge two unrelated histories. Check what `install` does today when `~/plans`
  already exists as a clone.

## Recommended direction

1. **A `sync` subcommand**: fetch the store's remote, merge (not rebase — the store is shared by
   every session on a machine, and rebasing rewrites commits another session may be about to push),
   then run the existing `push` path. Plain git against whatever remote the store has, no host API.
   Same tier rule as `push`: the sensitive store reports "nothing to sync". [PITFALL: **the push
   scan must cover the merge commit's own content.** `git log -p` shows no diff for a merge commit,
   so a conflict resolution that introduces new text is published unscanned. Use `--cc` (or `-m`) in
   the scan's `git log` once merges can be outgoing.]
2. **On a conflict, abort the merge and report** the conflicting paths, leaving the local commits in
   place. Every session on the machine shares the store's working tree, so a store left mid-merge
   blocks every other session. The agent resolves it deliberately with `sync` afterwards.
3. **With `sync = "auto"`**, every store-writing command — `commit`, `absorb --apply`, a filing with
   `new --for` or `--unscoped` once committed — ends by syncing, and says so in its output. A
   `--no-sync` flag keeps one commit local. A refused scan leaves the commit local and names the
   lines, as `push` does today.
4. **With `sync = "auto"`, `absorb` fetches first**, with a short timeout. When offline it warns
   that it read the local copy and carries on, so "nothing waiting" and "could not check" no longer
   print the same nothing.
5. **`doctor` reports the sync mode and staleness**: commits behind the remote after a fetch, and
   the age of the last fetch.
6. **`install --explain` asks the sync question** (decision above), and handles the second-machine
   clone (open question).
7. **Skill text**: a "several machines" section in `plan-conveyor`'s `SKILL.md`, and the matching
   README update. Per machine: `install --explain`, with the config kept per machine and out of git,
   as already documented. Then the sync modes, and the rule that the sensitive store never leaves
   its machine.
