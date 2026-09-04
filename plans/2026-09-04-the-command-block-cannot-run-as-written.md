---
status: idea
updated: 2026-09-04
source_repo: github.com-personal/ingesta
source_session: c83364a4-8f1d-42f2-bb27-aba9b6feb970.jsonl
source_moment: 2026-09-04T15:07:41+03:00
---

# session-harvest: the command block cannot be run as written

## Context

`session-harvest`'s SKILL.md opens with a six-line block a harvest is told to run rather than
compose by hand, and three of the six lines fail on any session whose transcript does not
auto-resolve:

```shell
python3 $H transcript --expect '<a command this session ran>'
python3 $H turns                                        # step 4
python3 $H sweep --boundary <instant>                   # step 5
python3 $H claims --until <instant>                     # step 5
```

`transcript --expect …` resolves by content and prints the path and the session id. Nothing carries
that to the next call — each is a separate process — so `turns` on its own exits 1 with
`no transcript resolved. Pass --session <id|path>, or --expect …`. Confirmed 2026-09-04 running the
block verbatim: `transcript --expect` succeeded and named the session, `turns` immediately after it
failed, and the run continued only by passing `--session <id>` to `turns`, `sweep` and `claims` by
hand.

**The block reads as a sequence and behaves as four independent invocations**, which is the whole of
the defect. It is small, it costs one failed call and a re-type, and it will do so on every session
where auto-resolution misses — which is exactly the case `--expect` exists for, so the failure is
guaranteed for the runs that need the flag most.

It is adjacent to, and not the same as, the pitfall the skill already records about background jobs:
that one is about landing on a **wrong** transcript, and it is well handled. This is about landing
on **none** after the tool has just printed the right one.

**A second harvest hit it identically four and a half hours later**, from another session in the
same repo (`29e5d6d9-e575-4a5a-87ee-92d31f3408b0`, 2026-09-04T19:35+03:00): `transcript --expect`
resolved and printed the path, `turns` on the next line exited 1, and the run continued by passing
`--session <path>` to `turns`, `sweep` and `claims`. Two sessions, two identical failures, neither
harvest having read the other's finding first — which is what "guaranteed for the runs that need the
flag most" looks like once it has happened twice rather than once.

## Open questions

[NEEDS CLARIFICATION: **Whether the fix is the script's or the wording's.** Two shapes, and they are
not equivalent:

- **The wording.** Say in the block that `transcript` prints an id to pass to every later call, and
  show `--session <id>` on the three lines that need it. Cheapest, honest, and leaves the reader
  doing the copying — which is fine, since they are reading the id off the previous output anyway.
- **The script.** Have `transcript` write the resolved path to a small state file that later
  subcommands read when no `--session`/`--expect` is given. Removes the re-type, and adds a piece of
  cross-invocation state to a tool whose every subcommand is currently pure — including the failure
  mode where a stale state file silently answers for a different session, which is the exact hazard
  the background-job pitfall was written about.

The skill's own rule says a correction a script can simply not make belongs in the script. That
argues for the second and the hazard argues against it, which is why this is a question rather than
a recommendation.]

## Recommended direction

Whichever shape wins, the block at the top of the file is the artefact to fix — a reader who runs it
verbatim is doing what the skill asked.
