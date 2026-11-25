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

## Open questions

- [NEEDS CLARIFICATION: should `absorb` and `list` fetch the shareable store themselves (network on
  a command that today has none, and a slow or offline remote delaying every session start), or only
  warn when the last fetch is older than some threshold (`FETCH_HEAD`'s mtime)? The warning keeps
  the read path offline; the fetch is what actually closes the silent case.]
- [NEEDS CLARIFICATION: when `sync` meets a conflict, stop and leave the store mid-merge for the
  agent to resolve, or abort the merge and report the conflicting paths? Aborting keeps the shared
  store clean for parallel sessions on the same machine, which all commit into one index.]
- Per-machine setup: is `install --explain` enough as written for a second personal machine, or does
  it need a "clone the store from this remote" path rather than creating an empty one? Check what it
  does when `~/plans` already exists as a clone.

## Recommended direction

1. **A `sync` subcommand**: fetch the store's remote, merge (not rebase — the store is shared by
   every session on a machine, and rebasing rewrites commits another session may be about to push),
   then run the existing `push` path. Same tier rule as `push`: only a store that already has a
   remote, never adds one, and the sensitive store reports "nothing to sync". [PITFALL: **the push
   scan must cover the merge commit's own content.** `git log -p` shows no diff for a merge commit,
   so a conflict resolution that introduces new text is published unscanned. Use `--cc` (or `-m`) in
   the scan's `git log` once merges can be outgoing.]
2. **Filing pushes**: `new --for` and `new --unscoped` already print the store commit to run; add
   the `sync` step to that output, so a filing reaches the other machines the moment it is made
   rather than when someone next pushes.
3. **`absorb` reads fresh state**, per whichever answer the first open question gets.
4. **`doctor` reports staleness**: commits behind the remote after a fetch, and the age of the last
   fetch, on the shareable store.
5. **Skill text**: a short "several machines" section in `plan-conveyor`'s `SKILL.md` — clone the
   store, run `install --explain` per machine (config stays per machine and out of git, as already
   documented), `sync` instead of `push`, the sensitive store never leaves its machine — and the
   matching update to the README.
