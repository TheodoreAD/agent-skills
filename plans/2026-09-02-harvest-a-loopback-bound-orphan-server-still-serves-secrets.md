---
status: landed
updated: 2026-09-02
---

# The listening-socket bullet closes too early on a loopback bind

## Context

`session-harvest` step 5's process bullet was extended on 2026-08-31 after a
`python3 -m http.server` bound to `0.0.0.0` was found serving a repository root — `.env` and `.git`
included — to the whole LAN. The extension is good and it fires. This is about the sentence it ends
on.

It closes:

> **a development server's default bind is usually every interface**, and that default is invisible
> locally, since bound or unbound every local run behaves identically and only the reachable
> audience differs.

That is true, and it frames the entire finding as **reachability**. Which means a loopback-bound
server reads as the safe branch, and the check terminates there.

## What happened

An `ingesta` harvest on 2026-09-02 found:

```
LISTEN 127.0.0.1:8765  users:(("python3",pid=271662,fd=3))
uv run python -m http.server 8765 --bind 127.0.0.1 --directory <repo root>   # etimes 12862 ≈ 3h34m
```

Bound to loopback — deliberately, by the repo's own task, which documents the choice: _"The static
server stays bound to 127.0.0.1 — a real LAN address would mean serving this repository root, `.env`
included, to the network."_ So the 2026-08-31 hazard was designed out, and the bullet's question was
answered "safe".

The run nearly stopped there. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/.env`
returns **200**, and the process had been up three and a half hours with the session that started it
having long since moved on — started by a one-shot `inv web.read` that was never expected to leave
anything behind.

## Why it is still a finding

Three properties survive a loopback bind, and none of them is about reachability:

- **It is an orphan.** Nothing owns it, nothing will stop it, and it outlives the session by however
  long that session runs. The 2026-08-31 case was 24 hours; this one was heading the same way.
- **It serves the repository root**, so every untracked and gitignored file under it is readable —
  which on this machine is exactly where the secrets are, by design, because `.env` is gitignored
  precisely so it stays out of the tree's history.
- **Loopback is not a boundary against everything.** It is a boundary against the LAN. It is not one
  against anything else running as this user, which on a machine running several agent sessions plus
  a browser is not a small set.

The general shape, and the thing the bullet is one clause short of saying: **liveness and bind
address are two of three questions, and the third is what it serves.** The bullet already names the
directory as part of the finding, so the fix is not new material — it is that the closing sentence
re-frames everything as audience and undoes it.

## Recommended direction

A short addition to the same bullet rather than a new one, since the material is already there:

> **A loopback bind narrows the audience; it does not close the finding.** An orphaned server is
> still an orphan, and the directory it serves is still readable to everything running as this user.
> Report an unowned listener over a repository root whatever its bind address, and say what is under
> it — `curl` one gitignored path and quote the status code, which is one call and turns "serves the
> repo root" from an inference into a measurement.

Worth keeping the confirming example that already exists — a loopback case and a `0.0.0.0` case
recorded side by side is what stops the next reader learning "check the bind address" as the whole
rule.

## What landed, 2026-09-02

Absorbed into this repo the same day it was filed, and taken further than "a short addition to the
same bullet" because the bullet stopped being where the check lives.

- `skills/session-harvest/SKILL.md` step 5 carries the recommended wording, with the loopback case
  and the `0.0.0.0` case recorded side by side, exactly as the plan asked: an unowned listener over
  a repository root is reported whatever its bind address, and the closing sentence no longer frames
  the finding as reachability.
- `scripts/harvest.py`'s `sockets` resolves what each listener actually serves — its `--directory`,
  else its working directory — and reports the repository root and any secret-shaped file under it
  as a separate axis from `exposed`. So "serves the repo root" arrives as a measurement rather than
  as something the agent has to think to ask, and the `curl` the plan suggests is now confirmation
  rather than discovery.
- `tests/unit/test_harvest.py::test_a_loopback_bind_does_not_close_the_finding` pins it: a listener
  on `127.0.0.1` whose served directory holds a `.git` and a `.env` is `exposed == False` and still
  in the findings.

[PITFALL: the first version inferred the served directory from `/proc/<pid>/cwd` for _any_ listening
process, and a browser that happened to have been started from a repository was reported as serving
it — a false positive in the most alarming section of the report. The directory is now inferred only
for something that looks like a file server, or that names `--directory` outright. Pinned by
`test_a_browsers_working_directory_is_not_what_it_serves`.]

**Still true and still open:** the `ingesta` server this plan was filed from is up. Measured during
this run at 13,859 seconds (≈3h50m), pid 271662, `127.0.0.1:8765`, serving that repository root,
which holds `.env` and `.envrc`. It belongs to no live session and is the plan's own instance.
