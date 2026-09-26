---
status: landed
updated: 2026-09-26
source_repo: github.com-personal/power-user-linux-setup
source_session: 10d0c6cd-12d8-42ff-9048-1da4b65afcc8.jsonl
source_moment: 2026-09-26T14:55:00Z
source_plan:
---

# audit.py's git-C-mutating row matches `git -C` inside quoted text

## Context

`session-bash-audit/scripts/audit.py`, run by a harvest on a 229-call session, reported
`git-C-mutating 4`. Two of the four samples were not git invocations at all:

- `python3 -c "\nimport pathlib\n..."` — a Python splice script whose string body mentions `git -C`
  in the text it writes into a Markdown file.
- `rg -o -N -m1 "Bash\(git -C \* add\) has a wildcard..." <log>` — a search pattern.

The other two were real (a `cd <scratch> && git init … && git -C probe-repo commit …` chain on
throwaway repos). `git-mutating-in-chain` counted the Python splice too. The skill says quoted spans
and heredoc bodies are stripped before matching; for this row, a double-quoted `-c` argument that
spans lines, or a quoted regex, evidently is not.

## Evidence

Transcript above,
`audit.py --session 10d0c6cd-12d8-42ff-9048-1da4b65afcc8 --until
2026-09-26T17:53:53+03:00`, the
`git-C-mutating (4) samples` block. Worth a regression fixture: one multi-line
`python3 -c "…git -C x commit…"` and one `rg "git -C \* add"`, both expected 0.

## Open questions

[DECISION: the stripping was never the problem: `QUOTED_RE` handles multi-line double-quoted
arguments. `git-mutating` and `git-C-mutating` just used `_rx`, which strips heredocs only, instead
of `_rx_unquoted`. Moving them over fixed both, and `git-mutating-in-chain` with them.]

## Recommended direction

Reproduce with the two fixtures, then fix at the stripping step if it is general.

## Verification

- Both fixtures from the Evidence section are regression cases in `tests/unit/test_audit.py`
  (`test_a_tool_name_inside_quotes_is_not_an_invocation`), along with a quoted `-C` path that must
  still count.
- The original repro, re-run after the fix (`9579e9c`):
  `audit.py --session 10d0c6cd-… --until
  2026-09-26T17:53:53+03:00` now reports `git-C-mutating 1`
  rather than 4. Its one sample is the real scratch-repo chain, and the Python splice and the `rg`
  pattern are gone.

## Migrated to

- **The code itself:** a comment above the two git rows in
  `skills/session-bash-audit/scripts/audit.py` records the incident and the quoted-path behaviour,
  and the tests hold the fixtures.
- **Deliberately not migrated:** `_git_c_tag` and `_store_write` still strip heredocs only. Both
  read the path out of `git -C <path>`, and blanking quotes would blank a quoted path. Neither has
  been seen misfiring on quoted text, so this is left as a known limit rather than opened as work.
