---
status: idea
updated: 2026-09-05
---

# `harvest.py --expect` silently fails to match a command containing double quotes

## Context

Found while running `/session-harvest` in `power-user-linux-setup` on 2026-09-05. The SKILL's step-4
guidance is to select the transcript by content when no id is to hand:
`harvest.py transcript --expect '<a command this session ran>'`. A natural choice is to paste a
whole command the session ran. If that command contains double quotes, the match fails and the
subcommand reports `no transcript resolved`, which reads as "wrong command" rather than "the matcher
cannot see this shape".

Reproduced this session:

- `transcript --expect 'git tag -l "SINGLE-LINE-TEST"'` → `no transcript resolved`.
- `transcript --expect 'git tag -l'` → resolved (2 candidates, took the most recent).

The more specific string, which is the one a user is more likely to paste, is the one that fails.

## The cause, confirmed

`_by_content(expect, cwd)` does `expect in path.read_text(...)` against the raw JSONL. The
transcript stores a Bash command as a JSON string, so its double quotes are escaped: the file holds
`git tag -l \"SINGLE-LINE-TEST\"`, not `git tag -l "SINGLE-LINE-TEST"`. A raw-substring search for
the unescaped form therefore misses. Verified:

```shell
rg -c 'git tag -l \\"SINGLE-LINE-TEST\\"' <this session's .jsonl>   # 3
```

So the escaped form is present three times; the unescaped form the user would type is absent. Same
failure for any command with `"`, and for single quotes stored inside a JSON string they are not
escaped, so the asymmetry is itself a trap — some quoted commands match and some do not, with no
signal which.

## Severity

Low. It fails safe: it errors clearly and never selects the wrong transcript, and the fix from the
user's side is to pass a quote-free substring or `--session <id>`. But `--expect` is the SKILL's
recommended robust selector for exactly the case where no id is to hand, and it breaks on the most
natural input to it, so the recommendation and the behaviour disagree.

## Recommended direction

[UNVERIFIED: the shape of the fix, not yet tried.] Match against the parsed command rather than the
raw line: `_by_content` already reads the file, and the loader nearby (`json.loads(line)`) is the
tool. Search the decoded `tool_use` input / command text so the needle is compared against the same
unescaped string the user sees, instead of against JSON-escaped bytes. A cheaper stopgap is to try
both the raw needle and its `json.dumps`-encoded inner form, but decoding is the honest version.

Whatever the fix, add a test with a fixture transcript whose stored command contains `"` and assert
`--expect` on the unescaped command resolves it — a matcher that can only be tested on quote-free
commands is one that passes while broken, which is how this shipped.

Belongs in `agent-skills`, so filed here rather than edited from the `power-user-linux-setup`
session that found it.
