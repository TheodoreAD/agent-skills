---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: a2333e68-f91a-4b94-845c-ec78a74cfc3a.jsonl
source_moment: 2026-09-27T22:34:30Z
source_plan:
---

# The sweep's fetch failure keeps only the line that does not name the cause

## Context

`session-harvest`'s sweep reports a failed `git fetch` as
`FAILED ({ran.err.strip().splitlines()[-1:] or ran.code})` — `scripts/harvest.py:943`, the last
stderr line only. For the failure the skill itself documents as the common one on this machine, that
line is the useless half of git's two-line message:

```
fetch: FAILED (['and the repository exists.'])
```

`Permission denied (publickey).` is on an earlier line and is dropped. SKILL.md's git bullet makes
exactly that phrase the trigger for `inv ssh.check` and the per-call `SSH_AUTH_SOCK` prefix, so the
diagnosis the prose prescribes is keyed to text the script discards.

## Evidence

This session, a harvest run 2026-09-28 on a session resumed after a 20-day idle gap. Both touched
repos reported the line above. The shell's `SSH_AUTH_SOCK` still named a terminal emulator's agent
from the session's first day, no longer reachable; `ssh.check` (run from the setup repo, since the
session repo has no `ssh` namespace) named the keyring agent, and a prefixed `git fetch` then
succeeded in both repos. The ahead-counts the sweep had printed were against refs 21 minutes and
three weeks old, flagged correctly by its own `note:` line.

A resumed session is the likely shape for this, since the socket was captured at session start.

## Open questions

[NEEDS CLARIFICATION: print the first line containing `Permission denied`, or the whole stderr? The
whole thing is two or three lines and loses nothing; matching one known phrase fixes this case and
the next unfamiliar failure is truncated the same way.]

## Recommended direction

Keep all of stderr, joined, and when it contains `Permission denied (publickey)` add one line naming
the machine's diagnostic — the script already knows the rule, since SKILL.md carries it.
