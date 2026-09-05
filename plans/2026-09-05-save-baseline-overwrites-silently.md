---
status: landed
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: 156d723c-4e21-41ef-aac9-bfd6c05b681c.jsonl
source_moment: 2026-09-05T02:13:00+03:00
---

# `--save-baseline` silently overwrote the baseline it was meant to be compared against

## Context

`session-bash-audit`'s `audit.py --save-baseline`, with no path, writes
`state_dir() / f"{time.strftime('%Y-%m-%d', time.gmtime())}.json"` — a **UTC** date. This machine
runs at `+03:00`, so a run at 02:13 local on 2026-09-05 wrote `2026-09-04.json`, which was the name
the pre-`bba2ed9` baseline already had from 14:09 the previous afternoon. It was overwritten with no
prompt, no backup and no mention that anything already existed there; the only output is
`baseline written to …` on the last line of a report several hundred lines long, which reads as
success.

The baseline destroyed was the anchor a `[UNVERIFIED:]` in `power-user-linux-setup`'s
`contributing/global-agents-md.md` explicitly named, for measuring whether the 2026-09-04 wording
change moved the `head`/`tail` rate. It was survivable only by luck: that question had already been
answered in prose (four post-deploy sessions at 50%, 6%, 15%, 25%) before the file was lost.

Two distinct defects, and the second is the one that bites hardest at 00:00–03:00 local, which is
when these sessions actually run:

1. **A write that destroys existing state gives no warning.** Every other writer in this corpus that
   can overwrite something asks or diffs first; this one is the sole exception, and the thing it
   overwrites is by construction irreplaceable — a baseline is a measurement of a corpus that has
   since moved on.
2. **The default filename is UTC while everything it describes is local.** The corpus is local-time
   sessions, the plans are local-dated, the user's day is local. `saved` in the JSON has the same
   problem: both files on this machine now record `"saved": "2026-09-04"`, one of them written on
   the 5th.

## Evidence

- The overwriting call, this session: `audit.py --save-baseline --note "pipefail live"`, run 02:13
  local 2026-09-05, immediately after deploying `setopt PIPE_FAIL` (see `power-user-linux-setup`
  `plans/2026-09-05-pipefail-in-the-agent-shell.md`).
- `ls -la ~/.local/state/session-bash-audit/` showed one file, directory ctime `Sep 4 14:09`, file
  mtime `Sep 5 02:13` — the same inode, rewritten.
- The naming line is `audit.py` around the `save_baseline` call in `main()`:
  `default = state_dir() / f"{time.strftime('%Y-%m-%d', time.gmtime())}.json"`.
- Reconstruction used `--days 4.5 --until 2026-09-04T14:27:46+03:00` (the `bba2ed9` commit's own
  timestamp) and is labelled a reconstruction in its `note`, because `--days` counts back from _now_
  rather than from `--until`, so the window approximates the original rather than reproducing it.

## Open questions

[DECISION: refuse, not auto-suffix. It matches how this corpus treats every other one-way write, and
the refusal is readable in a way an accumulating `-2` is not — the whole point of the default path
is that nobody names it, so nobody would notice a second file appearing under a name they never
chose either.]

[DECISION: keep the UTC filename and put the local timestamp in `saved`, the plan's own "possibly
the honest fix", chosen by the user 2026-09-05 over local-dating the file. An artefact already on
disk keeps its scheme, and the collision the local name would have avoided is now a refusal rather
than a loss — so the naming was never the half that cost anything.]

[DEFERRED: `--note` stays optional. It is worth less now than when this was written: `saved` carries
a local timestamp with its offset and `instrument` names the script that wrote the file, so a
note-less baseline is identifiable even if it is not self-explaining. Making it mandatory would also
make the ordinary case — a quick baseline before a change — prompt for prose nobody has yet.]

## What landed

`c01973d`. `save_baseline` raises rather than writes when the path exists, naming the existing
file's `saved`, `days`, `note` and `instrument` so the caller sees what they were about to destroy;
`--force` is the deliberate destroy. `saved` is now `datetime.now().astimezone().isoformat()`.

**Defect 1 from the neighbouring plan is folded in**, per the user's decision 2026-09-05, because it
is the same writer: the payload records `instrument`, the script's own short SHA with `-dirty` when
its checkout has uncommitted changes to it, and `None` when it did not run from a checkout — which
is the useful answer rather than a SHA borrowed from whatever repo the installed copy happens to sit
under. That is three read-only `git` calls in a script whose disclosure said it ran nothing, so
`SKILL.md`'s "What this skill reads, runs and writes" says so and scopes them to the write path.

Four tests: the refusal (asserting it names the note it would have destroyed, and that the file is
still the old one afterwards), `--force`, the recorded instrument, and `saved` parsing with a
tzinfo. A fifth covers `instrument_commit` outside a checkout returning `None`.

## Recommended direction

Done, in the shape recommended: refuse unless `--force`, naming the existing file's fields.
