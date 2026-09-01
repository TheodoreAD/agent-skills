---
status: idea
updated: 2026-09-01
source_repo: github.com-personal/ingesta
source_session: 81ef32cd-7240-48b8-b0a3-4cd53845adad.jsonl
source_moment: 2026-09-01T09:01:27.595Z
---

# The live-state sweep has no bullet for a file the session edited outside every repo

## Context

`session-harvest`'s step 5 sweeps processes, listening sockets, git state in every repo touched,
sibling repos, paths named for other sessions, CI, `$RESEARCH_HOME`, `$PLANS_HOME`, unkept promises,
`depends_on` blockers and handoffs. Every one of those is either a repository, a store with a stated
convention, or a process.

**Nothing covers an ordinary file the session edited that is in none of them** — and the sweep's own
framing is what hides it: each bullet asks "did the session leave this store tidy", so a file that
belongs to no store is not untidy, it is unseen.

Found 2026-09-01 in an `ingesta` session, by noticing at report time that the harvest had nothing to
say about the most consequential edit of the run.

## The instance

The session edited `~/.config/ingesta/catalogue.toml` — the household's live medication catalogue.
That file:

- is deliberately outside every working tree, because it is operational data that changes when a
  prescriber changes it (the repo's `AGENTS.md` says so);
- is under no version control, so there is no diff, no history, and no undo;
- has no backup on this machine that the session could find;
- is a **medical record**, which is the whole subject of the repo that reads it.

The edit was approved by the user and was correct — the repo's own `inv catalogue.check` and a seed
run through it both confirmed the file loads and produces the right catalogue. That is exactly what
makes it a good instance: nothing went wrong, and the sweep still could not see it. A wrong edit
would have been equally invisible.

The near-miss shape is easy to state: an edit to a versioned file is recoverable by anyone who reads
`git status`; an edit to this one is recoverable by nobody, and the harvest's report closed without
naming it.

## Open questions

[NEEDS CLARIFICATION: how the bullet finds the files without becoming a filesystem crawl. The
session knows which paths it edited — they are in its own transcript as `Edit`/`Write` tool calls —
so the cheap version is "list the paths this session wrote, drop the ones inside a git repo or a
known store, report the remainder", which needs no scanning and is exact. The expensive version
watches directories and is not worth it.]

[NEEDS CLARIFICATION: what the bullet should ask once it has the list. "You edited an unversioned
file" is a fact, not a finding. Candidates: whether a copy of the previous content still exists
anywhere; whether the file has a generator or an example in a repo that could regenerate it; and
whether anything validates it, since a validator turns an unrecoverable file into a recoverable
mistake. The `ingesta` case had the third and not the first two.]

[NEEDS CLARIFICATION: whether this is one bullet or two. An unversioned config file and a
**credential** file are different risks — the store sweep already has a credential-adjacent finding
in this repo's history — and a bullet that lumps them will get the tone wrong for one of them.]

## Recommended direction

A step 5 bullet, phrased as the others are: name the failure, then the command. Something close to
"**Files this session edited that no repository and no store covers.** Take the write paths from the
session's own transcript, subtract everything inside a git repo or a known store, and report what is
left with what would recover it — because nothing else in this sweep can see a file that belongs to
no tidy-able place."

Worth writing the "what would recover it" half carefully: for the instance above the honest answer
was "the repo's example file plus the check that validates it", which is a real recovery path and
not an obvious one.
