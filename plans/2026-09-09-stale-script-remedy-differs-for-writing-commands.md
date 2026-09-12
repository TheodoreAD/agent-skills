---
status: idea
updated: 2026-09-09
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-09T23:47:06+03:00
source_plan:
---

# "Re-run that command from the checkout" is the wrong remedy for a command that writes

## Context

`session-harvest`'s step 0 tells a run what to do when the installed `scripts/` differs from the
checkout and an earlier call in the session already executed the old copy:

> A change that _adds or widens a check_ means the earlier call answered a question the current code
> would have answered differently, and the remedy is to re-run that command from the checkout.

That is right for every example it gives, and all of them are **reads** — `plans.py list` is the
confirmed instance. Re-running a read is free and idempotent.

**It is wrong, and expensive, for a command that writes.** Re-running `plans.py new --for <repo>`
does not correct the earlier call; it creates a **second plan file** for the same topic, in a store
several sessions share, which `absorb` then offers as a pair and whose merge is a judgement call
somebody has to make. The correction that was actually needed is a different shape entirely: **edit
the artifact the old code already produced.**

## Evidence

Session `e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-09, second
harvest. The distinctive phrase to search that transcript for is "the installed copy is behind".

`skills-state` reported `plan-docs`' `scripts/` differing between install and checkout, four commits
since session start, none of them this session's. The diff was 69 lines and was a widening:
`4002efd`, `faf26dd`, `df817d1` and `c5c3da9` added a `source_plan` frontmatter field, taught
`new --for` to emit it, and taught `absorb` to print `decision owned elsewhere` for plans that carry
it.

This session had called `plans.py new --for` **five times** against the installed copy, so five
filed plans exist that the current template would have written differently — each missing a field
whose whole purpose is to be read at absorption time, by a session that will have no idea it is
absent.

The remedy the skill names, applied literally, would have produced five duplicate plans. What the
run did instead: read the diff, decide per plan whether the field applied (two proposed and named
their owning plan; three report facts and correctly stay blank), `Edit` the two, and commit. Nothing
was re-run.

[PITFALL: **the two cases are not distinguishable from the diff alone, only from what the command
does.** A widened check in a read-only subcommand and a widened template in a writing subcommand
look identical in `diff -u` — both add lines, both mean the earlier call behaved differently. The
discriminator is whether the earlier call left an artifact behind, and that is a fact about the
subcommand rather than about the change.]

## Open questions

[NEEDS CLARIFICATION: is the right fix one sentence in step 0, or a list of which `plan-docs`
subcommands write? A sentence generalises and needs no upkeep — "if the stale call **created**
something, correct the artifact rather than re-running the command, which would create a second
one". A list is precise and goes stale, which is the failure this whole corpus keeps re-finding. The
sentence looks right on that argument alone.]

[NEEDS CLARIFICATION: does this reach further than `new --for`? `set-status` writes, but re-running
it is idempotent and harmless. `commit` writes a commit, and re-running it after a template change
is a no-op on a clean tree. So `new` may be the only genuinely destructive re-run in `plan-docs` —
worth checking rather than assuming, because if it is the only one the sentence can name it and stay
concrete.]

[NEEDS CLARIFICATION: should `skills-state` say which of the differing subcommands write? It already
names which subcommands differ between install and checkout, which is most of the way there.
Against: that is the script knowing something about another skill's semantics, which is a coupling
this corpus has avoided elsewhere.]

## Recommended direction

Add the distinction to step 0's `scripts/` paragraph, next to the existing read-shaped remedy rather
than as a new heading — the same "extend the section that already frames it" default the routing
filters use.

The wording that carries it, roughly: a stale call that **answered** a question is re-run; a stale
call that **created** an artifact is not, because re-running it creates a second one — go and
correct what it wrote. Both halves in one sentence, because the reader arrives holding a diff and
needs to sort it, not to look up a category.

Worth stating the concrete instance in the same breath, since it is the one that will recur: five
plans filed through the old template, corrected by editing two of them rather than by re-filing any.
