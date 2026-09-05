---
status: landed
updated: 2026-09-05
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

[DECISION: **the script's, and by a third shape neither option above had seen: the harness already
tells every Bash call which session it is.** Landed 2026-09-05 after a third harvest hit the block
identically (`4e6fc3cc`, this repo). Claude Code exports `CLAUDE_CODE_SESSION_ID` into every call,
and it is the transcript's own filename stem — so `resolve_transcript` reads it after the job check
and before `--expect`, and the bare `turns`/`sweep`/`claims` lines resolve with no state file and
nothing typed. It beat the wording fix because the re-type was never necessary, and it beat the
state file because it adds no cross-invocation state at all: the environment is per-call and
per-session by construction, and a background job's `state.json` still wins, since a job's
environment names the parent. `--session` stays for a harness that exports no id.
`tests/unit/test_harvest.py::test_the_harness_session_id_resolves_a_bare_call` pins both the
resolution and the precedence.]

## Recommended direction

Landed: `harvest.py` resolves from the environment, its docstring and the `SKILL.md` block say so,
and the block now runs as written in Claude Code.

## Migrated to

- **`skills/session-harvest/references/rationale.md`, "Why step 0's own instruments kept reporting
  clean"** — that the fix was a third option neither candidate had seen, and why it beat both: the
  re-type was never necessary, and a state file is a second thing that can go stale.
- **`harvest.py`'s `resolve_transcript` docstring and the comment on the environment branch** — the
  precedence, and why the job check stays ahead of it. Verified present rather than assumed.
- **`tests/unit/test_harvest.py::test_the_harness_session_id_resolves_a_bare_call`** — pins both the
  resolution and the precedence.

Not migrated: the reproduction transcripts for all three occurrences. The count survives in the
rationale section, and the sessions are named in this file's own history.
