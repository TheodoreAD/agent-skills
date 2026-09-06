---
status: idea
updated: 2026-09-06
source_repo: github.com-personal/ingesta
---

# The sweep called twenty of another session's docker images "new this session"

## Context

Filed from `ingesta` on 2026-09-06 by a `/session-harvest` run, as that run's step-6 fold-back.
Nothing in this repo was touched.

`sweep`'s disk-artifacts section printed twenty lines of `new this session:` — about 2.4 GB of
images — for a session that **ran no docker command at all.** Six hours, 183 Bash calls, every one
of them `git`, `inv`, `rg`, `ss`, `sed` or `plans.py`. The images are `sample-service`,
`clean-os-test` and `scratch-test` on registry ports 32812–32824, which is container-testing work
from a parallel session in `repo-tasks` or `scaffoldapy` — repos whose plans were being committed to
the store throughout the same window.

## What is wrong

[DECISION: **"New this session" is computed from a timestamp inside the session window, and on this
machine that is not an attribution.** The user runs parallel sessions as a matter of course —
`~/AGENTS.md` says so outright, and this skill's own git bullet already builds on it, warning that
an ahead-count "is not necessarily this session's work" and that recommending a push may publish
another session's history. The disk-artifacts bullet inherited none of that reasoning: it filters by
time alone, so any artifact any session creates during the window is reported as this one's.

The git bullet is the proof the mental model exists in the skill already. It simply was not carried
across to the check where the same machine fact applies just as hard.]

[PITFALL: **The failure is worse than a mislabel, because of what the bullet tells the reader to do
next.** It says to "report the sizes with a proposed removal line the user can approve". So the
report proposes deleting images this session did not create, attributed to it, while a live session
may be mid-run against them — and the bullet's own stated reason for not deleting unasked is
precisely that "an image another session is about to reuse costs a rebuild". The caution is present
and the attribution that would make it fire is not.

It also reads as authoritative in the one direction nobody checks. A harvest saying "your session
left 2.4 GB" is a specific, plausible number, and the session that reads it has no cheap way to know
it ran no docker at all.]

## Recommended direction

1. **Cross-check the artifact against this session's own commands before calling it this
   session's.** The transcript is already parsed for other steps, so "did this session invoke
   `docker` at all" costs nothing and settles the whole class: zero docker calls means zero
   attributable images. That is a stronger filter than any timestamp and it fails safe.
2. **Where an artifact cannot be attributed, report it as machine-wide rather than dropping it.**
   The totals line is genuinely useful — 977 MB of build cache is worth seeing whoever made it — so
   the fix is a second heading, not a narrower filter. Something like
   `new during the window (not
   attributable to this session)` keeps the finding and loses the
   false claim.
3. **Carry the parallel-sessions caveat into the bullet's prose**, the way the git bullet already
   carries it, so the next reader of the checklist does not have to rediscover that the same machine
   fact applies here.

## Where this came from

The run that found it: session `88f860c9` in `ingesta`, 2026-09-05 21:03 to 2026-09-06 03:12. Its
`processes` section was correct and clean, which is what made the docker section stand out — a
session with no surviving children and no watchers does not usually have twenty fresh images.
