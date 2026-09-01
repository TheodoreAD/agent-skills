---
status: landed
updated: 2026-09-02
---

# session-harvest step 5 sweeps processes but not the disk they left behind

## Context

`session-harvest`'s live-state sweep asks whether a process is still running, what it exposes, what
git and CI think, and what the shared stores hold. Nothing in it asks what the session wrote to disk
**outside any repository** — and a session that builds container images leaves multi-gigabyte
artifacts that every existing bullet is blind to.

Measured at harvest, 2026-09-01, on a session that spent the day verifying a WSL/container first-run
fix in containers:

| artifact                               | size    | visible to which existing bullet |
| -------------------------------------- | ------- | -------------------------------- |
| `pulse-devcontainer-test` image        | 4.11 GB | none                             |
| `pulse-wsl-sim-2404` + `pulse-wsl-sim` | 445 MB  | none                             |
| docker build cache (machine-wide)      | ~58 GB  | none                             |

The processes bullet found nothing, correctly: every container had already been removed, and
`docker ps` was empty. That is exactly the failure mode — the sweep came back clean while 4.5 GB of
this session's artifacts sat on the disk, and the build cache it contributed to was larger than the
sum of everything else the machine's `git status` could see.

Two properties make this the harvest's problem rather than the user's:

- **It is invisible to every other check.** Not a process, not a socket, not tracked by git, not in
  a store, not a promise. `docker images` is the only thing that reports it, and nothing runs it.
- **The session is the only party that knows which artifacts were throwaway.** `pulse-wsl-sim` is
  named in a committed README and is meant to persist; `pulse-devcontainer-test` was a one-off
  verification build of the same Dockerfile the repo already ships. Nobody reading the machine a
  week later can tell those apart, which is precisely the argument for reporting it at the end of
  the run that made them.

## Open questions

[NEEDS CLARIFICATION: how wide the bullet should be. Docker is the case with evidence, but the same
shape covers anything a session leaves outside a repo and outside the two stores — a
`uv python
install` of a version installed only to test a floor (this session added 3.10, ~34 MB,
now unreferenced), `~/.cache` growth from a large dependency resolution, a `docker volume` from a
throwaway service. A bullet naming only images risks reading as docker-specific; one naming "disk
artifacts" risks being too vague to run. The concrete commands are cheap and few — `docker images`,
`docker system df`, `uv python list --only-installed` — so listing them may be better than
generalising.]

[NEEDS CLARIFICATION: whether the bullet reports or offers to clean. Step 8 says to fix what is
cheap and unambiguous, but "unambiguous" is doing real work here: deleting an image another
session's harness is about to reuse costs a rebuild, and the build cache is shared with every other
project on the machine. Reporting the sizes with a proposed `docker rmi` line the user can approve
is the conservative reading, and matches how the push is handled.]

## Recommended direction

A bullet in step 5, after the processes/sockets one, since it is the same "what did this session
leave running or lying about" question one layer down:

> **Disk artifacts outside any repo.** Container images and build caches, throwaway interpreters,
> volumes — none of which `ps`, `ss`, `git status` or either store can see, and which a session that
> verified anything in containers will have several gigabytes of. `docker images`, and
> `docker system df` for the cache. Report the sizes and say which were one-off verification
> artifacts versus the ones a committed README names; the session is the only party that can still
> tell those apart.

## Verification

- Reproduce by running any harvest after a session that built images: the processes bullet reports
  clean, and nothing else mentions them.
- The evidence above is from `docker images --filter reference='pulse-*'` and `docker system df` on
  2026-09-01, in a session where every container had already been cleaned up by hand.

## Outcome, 2026-09-02

Landed as a step 5 bullet, placed after the processes one as the recommended direction says.

Both open questions were settled by writing it:

- **How wide the bullet should be.** Named commands rather than a general "disk artifacts", because
  the plan's own reasoning holds — a bullet naming only images reads as docker-specific, one naming
  the category is too vague to run. It lists `docker images`, `docker system df` and
  `uv python list --only-installed`, which covers the case with evidence plus the throwaway
  interpreter this plan also recorded.
- **Report or clean.** Report, with a proposed removal line to approve. The conservative reading won
  on the plan's own argument: the build cache is shared with every project on the machine, and an
  image another session is about to reuse costs a rebuild.

## Migrated to

- `skills/session-harvest/SKILL.md`, step 5 — the bullet, with the 4.11 GB / 445 MB / ~58 GB
  measurement as its dated evidence and the "only the session can tell throwaway from named"
  argument, which is the part that makes it worth reporting at the end of the run that made them.

Nothing else migrated: the plan's Verification section describes how to reproduce a gap that no
longer exists.
