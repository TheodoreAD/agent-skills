---
status: planned
updated: 2026-08-29
depends_on: [power-user-linux-setup]
---

## Context

Both of this user's public repos had employer/client identities committed and pushed. On 2026-08-28
the histories were rewritten and force-pushed, and both branches are now clean. That is only half
the job: **a force-push does not delete anything.** The old commits stop being reachable from a
branch, but GitHub keeps serving them by SHA until it garbage-collects, which it does not do on its
own schedule for this purpose.

Measured, minutes after each force-push:

| repo                     | old commit                                 | still served?                 |
| ------------------------ | ------------------------------------------ | ----------------------------- |
| `agent-skills`           | `d3bc2f82c6057d4fd40b05c72d049889a0e5d663` | yes — 10 matches in its patch |
| `power-user-linux-setup` | `3c0b606e341984bdbeaff0e6a004fd9011d72809` | yes — 4 matches in its patch  |

Both via `gh api repos/<owner>/<repo>/commits/<sha> --jq '.files[].patch'`, HTTP 200. Anyone holding
one of those SHAs — an old link, a stale clone, a scraper, a search index — reads the original
content today. Closing that is a support request, which is why this is a plan and not a command
someone runs in passing.

[DECISION: purge rather than leave the history standing. Settled with the user 2026-08-28: the
content is other people's identities, not the author's own, and a public repo's history is as
readable as its tip.]

## Design

### 1. What is already done

- `agent-skills`: full-history rewrite, force-pushed. `origin/main` = `96999fd`. Tip content
  byte-identical (tree `09488ff`), 29 commits, `scan --mode history` returns 0. Local backup ref
  deleted and the objects gc'd, so the pre-rewrite commits no longer exist on this machine.
- `power-user-linux-setup`: full-history rewrite of `master` (417 of 448 commits renumbered),
  force-pushed. `origin/master` = `e86fe4d`. Tip tree `52d8522`, unchanged. Its `gh-pages` branch
  was deleted and rebuilt from the clean `docs/` as a single commit.

### 2. The requests to send

One per repo, at [support.github.com](https://support.github.com). They can go in either order and
neither depends on anything else. Text to paste:

> **Subject: Purge cached views after a history rewrite — TheodoreAD/agent-skills**
>
> I rewrote the history of `TheodoreAD/agent-skills` and force-pushed `main` to remove sensitive
> data that had been committed by mistake. The current history is clean, but the pre-rewrite commits
> are still served by SHA — for example `d3bc2f82c6057d4fd40b05c72d049889a0e5d663`, which the API
> and the web UI still return.
>
> Please garbage-collect the repository and purge cached views and any stale references to the
> pre-rewrite commits. The repository has no forks.

> **Subject: Purge cached views after a history rewrite — TheodoreAD/power-user-linux-setup**
>
> I rewrote the history of `TheodoreAD/power-user-linux-setup` and force-pushed `master` to remove
> sensitive data that had been committed by mistake. I also deleted and rebuilt the `gh-pages`
> branch, which had the same data in its older build commits. The current history of both branches
> is clean, but the pre-rewrite commits are still served by SHA.
>
> Commits that carried the data and should no longer be reachable:
> `3c0b606e341984bdbeaff0e6a004fd9011d72809`, `660b202`, `5445a6a`, `32e73f0` on the old `master`,
> and the old `gh-pages` build commits `ce8a522`, `6d21ada`, `aead191`, `8e5abf6`, `42940e0`,
> `023b225`, `ee17602`, `32377f6`, `4cfffd5`, `8910809`, `898e52f`, `119d792`, `c43f0a5`.
>
> Please garbage-collect the repository and purge cached views and any stale references to the
> pre-rewrite commits. The repository has no forks.

### 3. What a support request cannot reach

Worth knowing before treating this as closed, and worth not chasing without a reason:

- **Clones already taken.** Nothing recovers those. `power-user-linux-setup` has 6 stars, so someone
  finding it is plausible; `agent-skills` has none.
- **Forks.** A fork shares object storage with its parent, so a purged commit can survive in one,
  and support cannot remove it from someone else's fork. Both repos have **0 forks** — checked
  2026-08-28 — which is the single luckiest fact in this whole episode.
- **Third-party archives.** Software Heritage crawls public GitHub repos on its own schedule, and
  GitHub's code search index is a separate cache. Neither is covered by a request to purge a
  repository.

[DEFERRED: checking Software Heritage for a snapshot of either repo. It is a lookup by origin URL
and a takedown request if there is a hit — worth doing once the support requests are answered, not
before.]

## Files touched

None in this repo. The work is two support tickets and, if it turns anything up, a follow-up on the
archives above.

## Verification

After support confirms, for each repo:

```shell
gh api repos/TheodoreAD/agent-skills/commits/d3bc2f82c6057d4fd40b05c72d049889a0e5d663
gh api repos/TheodoreAD/power-user-linux-setup/commits/3c0b606e341984bdbeaff0e6a004fd9011d72809
```

Both must return **404**, not a commit. That is the whole test, and it is the only evidence that the
purge actually happened — a successful force-push proves nothing about it, as the table above shows.

[UNVERIFIED: neither request has been sent. Until they are, both old commits are live.]
