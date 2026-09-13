---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/power-user-linux-setup
source_session: feea009a-eef1-4312-9967-186504d96db7.jsonl
source_moment: 2026-09-13T17:06:41+03:00
source_plan: plans/2026-09-12-imperative-vs-rationale-in-instruction-files.md
---

## Context

`audit.py --compare <baseline>` scores this run's rows against a saved one and prints `OK`/`MISS`
per row. A baseline records the `--days` it was saved with. **The comparison never checks that the
two agree, and never says so in its output.**

For a rate row this is a distortion. For an **absolute-count** row — `cut-message`, `echo-exit`,
`git-add-all`, `rg-replace-bundle`, `store-write-by-git`, `cd-own-repo`, `git-C-own-repo`,
`git-C-mutating` — it is meaningless outright, because the count scales with the window and nothing
normalises it.

## Evidence

A handoff prompt written 2026-09-13T14:46+03:00 told the next session, in those words:

> `python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --days 3 --compare ~/.local/state/session-bash-audit/2026-09-12.json`
> and look at cut-message, which stood at **6** when that baseline was taken

The baseline's own header:

```json
{ "saved": "2026-09-12T23:11:06+03:00", "days": 6.0, "note": "…", "instrument": null }
```

So the prescribed run compared **3 days against 6**. It printed `cut-message=3(MISS)` with no
remark, which reads as a halving fifteen hours after a wording change landed — and was the number
the whole re-read turned on. The session that ran it nearly reported a rate improvement.

Two further things make the same output worse than a silent mismatch:

- **`--days` selects whole transcript _files_ by mtime, not calls by timestamp** (`load_calls`:
  `cutoff = time.time() - days * 86400`, then `if path.stat().st_mtime < cutoff: continue`). So a
  resumed old session drags its entire history back inside the window whatever the number, and two
  runs with the _same_ `--days` can still cover different spans of calls.
- **The duplication defect filed separately**, fixed the same day in `28099cd` — its plan retired
  after that landed — inflated exactly those absolute-count rows, so the two compounded: an inflated
  count compared over an unstated window. Since the fix a baseline records `replayed_dropped`, and
  `--compare` already says when it reads one taken before; the window check this plan asks for is
  the same kind of line.

The honest read, once the row was given a denominator by hand — message-carrying calls, split at the
wording change — was **7 in 559 before, 0 in 12 after**: expected 0.15 hits at that base rate, so
nothing was readable either way.

## Open questions, answered 2026-09-13

Landed as `26f823b`. Re-run on the case this plan was filed from — `--days 3 --compare` against
`2026-09-12.json` — the header now reads `windows differ: this run --days 3, the baseline --days 6`,
and the row reads `cut-message=3/329(MISS)` rather than a bare `3`.

- **Refuse, warn, or normalise?** Warn. The header names both windows whenever they differ, and a
  single-session run says its counts are that session's alone. Refusing would break the deliberate
  wider-window re-read the skill suggests, and the failure was that the output said nothing.
- **Should the absolute-count rows be scored under `--compare`?** Yes, still. A `zero` verdict is
  absolute: it never used the baseline, so a window mismatch cannot make it wrong. What a mismatch
  destroys is reading the count as a trend, and the header now says so.
- **A denominator for `cut-message`?** Added: hits over calls carrying a commit or `gh` message, in
  the session view and in the comparison cell. It is built as a `DENOMINATORS` map, so another row
  can gain one. None has, because `git-add-all` over staging calls and `rg-replace-bundle` over `rg`
  calls each need a population definition of their own, and a guessed one is a second number to
  distrust.

## Recommended direction

Print both windows on the comparison header line whenever they differ, in the same place the
baseline's `saved` and `note` already appear, and mark the absolute-count rows as uncomparable
rather than scoring them. That is one line of output and one guard, and it turns a number nobody can
falsify into a stated limitation.

The related dedupe (`28099cd`) touches the same subcommand and the fixes compose, but neither
substitutes for the other — dedupe makes a count correct, and this makes two counts comparable.
