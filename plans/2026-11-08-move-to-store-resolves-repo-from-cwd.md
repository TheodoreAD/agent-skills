---
status: idea
updated: 2026-11-08
---

# `move --to store` resolves the repo from cwd, not from the file

## Context

Confirmed live 2026-11-08, from a session in agent-skills. A plan sat in another repo's `plans/`
(the new `hekate` clone, just routed to the store with `config set repos.<root>/hekate store`). Ran:

```shell
python3 plans.py move <hekate clone>/plans/2026-11-08-hekate-tilt-kind-monorepo.md --to store
```

It moved the file into **agent-skills'** store mirror and stamped
`repo: github.com/TheodoreAD/agent-skills` into its frontmatter. `--path` defaults to cwd, and the
repo is taken from `--path` alone, even when the positional file is an absolute path inside a
different repository. It printed no warning, unlike `graduate`, which warns when it touches a repo
other than the session's.

Recovered with `graduate <misplaced file> --to <hekate clone>`, which routed it to hekate's store
folder and recorded the link — but `graduate` kept the wrong `repo:` line, which had to be fixed by
hand.

## Open questions

[NEEDS CLARIFICATION: should `move` derive the repo from the file's own location when the file is
inside a repo's `plans/` and `--path` was not given, or refuse when the two disagree? Refusing is
the least surprising; deriving is the more convenient.]

[NEEDS CLARIFICATION: should `graduate` rewrite an existing `repo:` line to the destination's
identity, rather than only stamping one where none exists?]

## Recommended direction

- When the positional file resolves inside a git repository different from the one `--path` names,
  `move` refuses and names both, rather than silently using `--path`.
- `graduate` overwrites `repo:` with the destination's identity whenever it routes to the store.
- A regression test for each, from a cwd in one repo acting on a file in another.
