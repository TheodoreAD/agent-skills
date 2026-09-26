---
status: idea
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

[NEEDS CLARIFICATION: whether the quoted-span stripping misses multi-line double-quoted arguments in
general (then every row is affected) or only this row's pattern bypasses it.]

## Recommended direction

Reproduce with the two fixtures, then fix at the stripping step if it is general.
