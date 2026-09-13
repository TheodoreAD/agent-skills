---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/power-user-linux-setup
source_session: feea009a-eef1-4312-9967-186504d96db7.jsonl
source_moment: 2026-09-13T14:52:15+03:00
source_plan: plans/2026-09-12-imperative-vs-rationale-in-instruction-files.md
---

## Context

`session-bash-audit`'s `load_calls()` reads every `~/.claude/projects/*/*.jsonl` whose mtime falls
inside `--days` and concatenates their Bash calls. It never deduplicates. A resumed or forked
session writes a **new** transcript file that replays the parent's history, so every call the parent
made is loaded once per descendant transcript that is still inside the window.

Found while reading the `cut-message` row to settle an UNVERIFIED tag in the filing repo's
instruction-shape plan — the row's samples printed two commands twice, which is what exposed it.

## Evidence

Over `--days 7` on 2026-09-13, dumped with `audit.py --days 7 --samples 0 --json <path>`:

```
total calls:                            9012
distinct (timestamp, cmd) keys:         8363
keys appearing in >1 transcript:          649   (7.2% of the corpus)
```

The `cut-message` row is the sharp case because it is small: **7 tag hits, 5 distinct calls.** Two
pairs share a timestamp _and_ a byte-identical command across two session ids:

```
2026-09-09T20:07:12.806Z  70e28d42-…  git commit -m "plan-docs: commit takes a whole absorption, …
2026-09-09T20:07:12.806Z  519cf236-…  git commit -m "plan-docs: commit takes a whole absorption, …
2026-09-09T20:32:40.564Z  b494b3ef-…  git add -A && git commit -m "deploy: prune, so a retired des…
2026-09-09T20:32:40.564Z  6794e240-…  git add -A && git commit -m "deploy: prune, so a retired des…
```

`6794e240` is a background job whose `state.json` records `resumeSessionId: feea009a-…`, and
`b494b3ef` is earlier in the same lineage — so the mechanism is resume, not two sessions running the
same command.

### Why this is not cosmetic

Three consequences, in order of how much they cost:

- **Every absolute-count row is inflated by an unknown factor.** `cut-message`, `echo-exit`,
  `git-add-all`, `rg-replace-bundle`, `store-write-by-git`, `cd-own-repo`, `git-C-own-repo` are
  scored as counts against a baseline, and `compare` prints `n(MISS)` on a count. A row that reads 7
  is 5. A baseline saved while a long-lived session was being resumed daily carries more inflation
  than one saved after a quiet week, and nothing in the output says which.
- **Rates survive better but are not safe.** `count / n` inflates on both sides, so a rate is
  roughly right _if_ duplication is uniform across patterns. It is not: the duplicated calls are
  whatever a resumed session did, which is a specific session's habits, not the corpus's.
- **Per-session rows double-count the same work under two ids**, which is how a single session's
  behaviour can appear as two data points in the per-session table.

[PITFALL: **`rg` for the command text finds a third file, and it is not a third copy.** Grepping the
`deploy: prune` message across the project directory returns `feea009a` as well, because that
session's _harvest report_ quoted the command as prose. The audit does not count it, correctly.
Counting transcript hits rather than parsed tool-call records would over-correct in the other
direction.]

## Open questions, answered 2026-09-13

Landed as `28099cd` (the dedupe) and `692a391` (the research note), as the recommended direction
below describes, with the key the first question left open.

- **What is the dedupe key?** The `tool_use` id. Measured before choosing, over the same seven-day
  window: every one of the 649 replayed calls kept its id, and id and `(timestamp, cmd)` agreed on
  all of them. The copy kept is the one in the smallest transcript, since a descendant holds its
  parent's calls plus its own.
- **Does deduplication change a conclusion in `references/research.md`?** Not at the precision the
  file states rates to: on this window no rate moved more than 0.43pp. Counts did, most on the small
  rows (`git-add-all` 19 → 12). The earlier corpora cannot be re-taken, so the file now says its
  counts are upper bounds and its rates stand.
- **Should `--save-baseline` record the duplication?** Yes, as `replayed_dropped`. Its absence marks
  a baseline taken before the fix, and `--compare` says so when reading one.

## Recommended direction

Deduplicate inside `load_calls()`, before tagging, and print the number dropped on the corpus line
so the figure is visible rather than silently applied. Same reasoning as the `--until` line that
already prints `excluding N at or after …`: a filter that changes the denominator says so.

Do not backfill the saved baselines. They measure a corpus that has moved on, which is the rule the
script already enforces — the fix makes future comparisons sound, and a baseline taken before it
should be re-taken rather than adjusted.
