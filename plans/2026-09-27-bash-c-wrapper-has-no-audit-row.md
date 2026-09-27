---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: bcf810d6-38c7-48d3-adfe-2ff30399d4c9.jsonl
source_moment: 2026-09-26
source_plan:
---

# `session-bash-audit` has no row for an agent typing `bash -c`

## Context

`~/AGENTS.md`, "The permission model in force", names it: a `bash -c` wrapper changes the command
prefix and matches no allowlist rule, so it prompts every time. `audit.py` measures none of it.
`references/research.md` mentions `bash -c` only as a body the other patterns blank or exempt (line
~672, the `docker run … bash -c` drops), and line 533 is about the harness's own `zsh -c` wrapper, a
different thing. So an adherence line reports 0% on every row for a session that used the shape the
user corrected, and no row says the shape was not looked for.

Shape of the misuse, per `session-harvest` step 2's three: **not followed, repeatedly** — the rule
is written plainly, the session used the shape anyway, and once more after the user flagged it.

## Evidence

`repo-tasks` session `bcf810d6-38c7-48d3-adfe-2ff30399d4c9.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-26.

- Two calls
  `bash -c 'cd "$RESEARCH_HOME/repos/github.com--encode--starlette" && git fetch … && git show … | rg …'`,
  to run commands inside a research clone without moving the session's cwd. `git -C <path>` was the
  right shape.
- The user, mid-turn, then again as a turn: _"why are you using bash -c?"_ The session answered both
  times, correctly, that it was a mistake.
- About six hours later the same session ran
  `bash -c 'time (env -u VIRTUAL_ENV uv venv … && uv pip install … && … python -c "import pkg_api")'`
  to time a chain, and said so in the reply as it did it.

The harvest's audit line read `chain 4%`, `cd-own-repo 1%`, every other row 0%, over 398 calls. The
three calls appear in no row. Count: `rg -o '"command":"bash -c '` over the transcript, halved
because each call is also echoed once.

## Open questions

[DECISION: **one row, leading word only** (decided with the user 2026-09-28). It counts `bash`/`sh`/
`zsh` with a `-c` flag at a command-segment boundary, quotes blanked, so `docker run … bash -c` and
a `bash -c` named inside a message or search are not counted.

The premise that no row existed was half right. A `bash-c` pattern was already in `PATTERNS`, but it
matched anywhere, quotes included, and it was missing from `SESSION_ROWS` and `SAMPLE_TAGS`, so no
session view ever printed it. It is now in both, and on `bcf810d6` it reads 3, the count above. It
stays out of `EXPECTATIONS`: reported, not judged, because nobody has decided a verdict for it.
There was no SKILL.md row table to add a line to; the row's own description in `audit.py` names both
replacements.]

## Recommended direction

Add a `bash-c-wrapper` row matching a command whose first word is `bash`/`sh`/`zsh` followed by `-c`
(after the harness's own wrapper is stripped), with a sample block, and a line in the SKILL.md table
pointing at the `~/AGENTS.md` rule. The case this session shows is worth naming in the row's note:
the wrapper was used to keep a `cd` from persisting and to give `time` a whole chain, and each has a
replacement (`git -C`/the tool's own directory flag; a script file under the scratchpad).

## Migrated to

- **The row, its scope and both replacements** — the `bash-c` entry and its comment in
  `skills/session-bash-audit/scripts/audit.py`, now in `SESSION_ROWS` and `SAMPLE_TAGS`, with tests
  in `tests/unit/test_audit.py` (`2cd8c2c`).
- **Not migrated**: the SKILL.md table line — there is no such table; each row documents itself.
