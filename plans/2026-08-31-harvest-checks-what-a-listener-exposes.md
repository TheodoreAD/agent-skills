---
status: landed
updated: 2026-09-01
---

# The harvest's process check asks whether something is running, not what it exposes

## Context

`session-harvest` step 5's first bullet is "Processes this session started", framed around
backgrounded polls and watchers — "loops that outlive the turn that spawned them", with the CI-poll
loops of 2026-08-28 as its evidence. It asks whether a process is still alive and whether its exit
condition can ever be true.

A run on 2026-08-31 found a different failure that the bullet does not reach, and found it only by
accident. The session had been driving a browser harness whose driver starts a static file server:

```
python3 -m http.server 8765 --directory <repository root>
```

`http.server` binds **every interface** unless given `--bind`. So the process was serving that
repository's root — `.env` and `.git` included — to the whole LAN, and had been for 24 hours.
`curl http://127.0.0.1:8765/.env` returned 200. It was caught because the sweep happened to run
`ss -ltnp` alongside `ps`, which nothing in the skill asks for.

Two things make this the bullet's blind spot rather than an instance of it:

- **The process was not "started by this session".** It was already up when the session began — a
  previous session left it, and this one's `ensure_server` reused it because the port answered. The
  bullet's own wording excludes it, and the session that _did_ start it had already ended.
- **Liveness was never the question.** A long-running dev server is supposed to be running. What
  made it a finding is the socket's bind address and what sits under `--directory`, neither of which
  `ps` shows and neither of which the bullet asks about.

## Open questions

[NEEDS CLARIFICATION: Whether this is a new bullet or an extension of the existing one. It shares
the existing bullet's shape — state the session did not create and nothing else reports — but asks a
different question of it, and step 2's own guidance prefers extending a section that already frames
the principle over adding a heading. Leaning toward extending, with the listener case as a second
paragraph, since "what did this session leave running" and "what is it exposing" are one sweep.]

[NEEDS CLARIFICATION: How wide the check should be. `ss -ltnp` lists every listener on the machine,
most of which are nothing to do with any session — a browser's debug port, a database, a dev server
another project owns. Filtering to "listeners a repo's own tooling starts" needs a signal; the
cheapest is probably the ones whose `--directory`, cwd or command line names a path inside a
repository the session touched. Reporting every listener would be noise, and noise is what gets a
check skipped.]

[NEEDS CLARIFICATION: Whether the fix belongs to the harvest at all, or to whatever repo owns the
tooling. The harvest found it; the durable fix was a one-line `--bind 127.0.0.1` in that repo's
task, and a rule about default bind addresses would sit naturally in a conventions skill. The
argument for keeping a check here is that the exposure is invisible to the repo's own gate — the
code is identical either way, and only the running socket differs.]

## Recommended direction

Extend step 5's process bullet with the listener case rather than adding a heading:

- Ask what a surviving process **exposes**, not only whether it is alive — for anything holding a
  listening socket, the bind address and the directory it serves.
- Drop "this session started" for this case: a reused process is the harder one, because the session
  that started it is gone and its own harvest never ran, or ran before the exposure existed.
- Name the command, per the convention the rest of step 5 now follows: `ss -ltnp`, read alongside
  `ps`, rather than a description of what to look for.

The general fact behind it, worth stating once wherever it lands: **a development server's default
bind is usually every interface.** `python -m http.server` does it, and it is the kind of default
that is invisible locally — bound or unbound, every local run behaves identically, and the only
thing that differs is who else can reach it.

## Evidence

- The instance: `python3 -m http.server 8765 --directory <repo root>`, 24 h uptime, `0.0.0.0:8765`
  in `ss -ltnp`, HTTP 200 on `/.env`.
- The repository was a medical-record project, so the served tree also carried a catalogue and a
  `.env`. Fixed in that repo the same session, in its driver and its `serve` task.
- Filed from that session's harvest, which found it while running step 5 and not because step 5
  asked.

## Migrated to

`skills/session-harvest/SKILL.md`, step 5's process bullet — extended rather than given its own
heading, which is what the first open question was leaning toward and what step 2's guidance
prefers. It names `ss -ltnp`, drops "this session started" for the listener case, and carries the
instance and the general fact about default bind addresses.

**The second open question — how wide the check should be — was answered by not answering it.** No
filter is prescribed. `ss -ltnp` is short enough to read whole on a personal machine, and any rule
for "listeners a repo's own tooling started" needs a signal the harvest does not have; a wrong
filter hides the reused process that made this a finding at all. The noise objection stands and is
the thing to watch: if a run reports a browser debug port as a finding, that is the trigger to
revisit.

**The third — whether the fix belongs to the harvest or to the repo owning the tooling — is both,
and they do not compete.** That repo took the one-line `--bind 127.0.0.1`; the harvest keeps the
check because the exposure is invisible to that repo's own gate, the code being identical either
way.
