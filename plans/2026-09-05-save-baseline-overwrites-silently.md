---
status: idea
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

[NEEDS CLARIFICATION: refuse, or auto-suffix? Refusing unless `--force` is passed matches how this
corpus treats every other one-way write, and a refusal is readable. Auto-suffixing (`-2`) never
loses anything but quietly accumulates files nobody named, and the whole point of the default path
is that nobody names it.]

[NEEDS CLARIFICATION: whether the default should be local-dated instead of UTC. It would make the
name match the corpus and the plans, but it changes the name of an existing artefact, and a baseline
saved under one scheme compared against one saved under the other is only confusing in its filename,
not in its content. Possibly the honest fix is to keep UTC and put the local timestamp in `saved`.]

[NEEDS CLARIFICATION: whether `--note` should be mandatory for the default path. Both files here
carry a good note only because the caller happened to pass one; a nameless baseline with no note is
almost unusable a week later.]

## Recommended direction

Refuse to overwrite an existing baseline unless `--force`, and name the existing file's `saved` and
`note` in the refusal so the caller can see what they were about to destroy. That alone would have
turned this incident into a one-line prompt. The UTC/local question is worth settling in the same
pass but is cosmetic next to it.
