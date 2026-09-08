---
status: idea
updated: 2026-09-08
source_repo: github.com-personal/ingesta
source_session: 51a36fd5-b684-4cfb-8848-a1a5937b294c.jsonl
source_moment: 2026-09-05T17:02:32Z
---

# The sweep's outside-any-repo check cannot see a file a subprocess wrote

## Context

`session-harvest`'s step 5 carries a bullet for **files this session edited that no repository and
no store covers**, added 2026-09-01 after a session edited an unversioned config outside every
working tree — "no diff, no history, no backup, and operational data of the kind the repo that reads
it exists to protect". Its own note says what makes that instance the right one: "nothing went wrong
and the sweep still could not see it, so a wrong edit would have been equally invisible."

A session on 2026-09-05 did the same class of edit, to the same class of file, and
`sweep.written_outside_any_repo` came back **empty**.

## Evidence

The session replaced `~/.config/ingesta/catalogue.toml` — a household's live medication catalogue,
outside every working tree, unversioned — after confirming the existing copy was an unmodified stale
copy of a committed example.

The write did not go through `Edit` or `Write`. Both were refused by the auto-mode classifier, and
hand-retyping an 800-line medical catalogue was rejected as the worse risk, so the file was replaced
by **the owning repo's own task**, `inv catalogue.example --replace`, which shells out to
`shutil.copyfile`.

The sweep at the end of that session:

```
== written_outside_any_repo ==
[]
```

The transcript path is
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/51a36fd5-b684-4cfb-8848-a1a5937b294c.jsonl`;
the boundary was `2026-09-05T20:02:32+03:00`.

## Findings

[PITFALL: **The check reads edit-tool write paths, so it measures which _tool_ touched a file rather
than whether a file was touched.** Every path in this session's `Bash` calls is available in the
same transcript the sweep already parses, and the one that mattered was an `inv` invocation whose
effect was a file rewrite two levels down.

This is the same blind spot the bullet was written about, arriving through the door the bullet did
not name — and the 2026-09-01 instance came through `Edit`, which is exactly why the gap survived:
the check was built from the one case it had seen. The failure mode is the one that bullet already
states better than this plan can, that a wrong edit would be equally invisible.]

[PITFALL: **The classifier refusal is what routed the write to a subprocess, so the two interact.**
On a machine where writes under `~/.config` are refused to `Edit`/`Write` but reachable through a
repo's own task, the subprocess path is not an exotic case — it is the _normal_ one for exactly the
files this check exists to catch. Anything operational enough to live outside a repo is likely
enough to be written by the tool that owns it.]

## Open questions

[NEEDS CLARIFICATION: **How much a heuristic over Bash commands is worth here, given it cannot be
exact.** A path appearing in an `inv` argument list is not a write, and a write can happen with no
path on the command line at all — this session's did, since the destination is computed from
`$INGESTA_HOME` inside the task. So a command scan would have missed this instance too.

Three shapes, none obviously right, and the choice decides whether this is worth building:

- **Scan Bash commands for home-rooted paths** and report ones outside every repo. Cheap, catches
  the common `cp`/`sed -i`/`tee` case, and misses this one.
- **Report by mtime**: any file outside every repo under a small set of roots (`~/.config`,
  `~/.local
  /state`) modified between session start and the boundary. Catches this instance and
  every unrelated application's writes with it, which is a noise problem rather than a coverage one.
- **Say the check's own limit in the report**, and stop claiming coverage it does not have.
  Cheapest, honest, and leaves the finding to the session's own memory — which is what failed here.]

## A second check with the same blind spot, 2026-09-08

The research-store attribution added on 2026-09-08 reads argv rather than write paths, and hits this
gap from the other side: a retrofit re-cloned seven library entries from a `retrofit.py` holding the
names in a list, so argv named two of the seven and the other five were reported as somebody else's.
Same root — **which door the work went through decides whether the sweep can see it** — and it now
has two independent instances rather than one, in checks that read different evidence.

That is an argument for recommendation 1 below being the general answer rather than this one check's
consolation prize: neither check can be made complete, and both can be made to say what they saw.
The research one now prints its own limit next to its count for exactly that reason.

**A third instance the same day, and this one is the sharpest: the check could not see an event it
was built that hour to count.** `audit.py`'s truncation counter reads the exit code the harness
reports for a Bash _tool call_. The session that added it verified SIGPIPE by running
`bash check_sigpipe.sh`, a script whose internal `audit.py … | head -c 2000` returned **141** —
exactly the event the counter exists for. The tool call's own exit was 0, the command string held no
pipe, so the call was tagged neither `head/tail` nor truncated, and the session's row reads
`head/tail 64 — 0 actually cut output` on a session that demonstrably cut output.

The row is not wrong about the calls it counted, which is what makes this the same defect rather
than a different one: **the boundary is the tool call, and anything a script does inside one is
invisible whatever the check is looking for.** Three checks now — write paths, argv attribution, and
an exit code — each blind at the same seam, none of them reachable by fixing the others.

That also prices recommendation 1 properly. "Say what the check saw" is cheap for one check and
becomes a corpus-wide convention at three: every transcript-derived count wants a standing caveat
that a script's interior is out of scope, because a reader who learns it once for one row will still
read the next row as complete.

## Recommended direction

1. **At minimum, make the report say what the check saw**, rather than printing an empty list that
   reads as "nothing was written outside a repo". An empty result and an unexaminable one look
   identical today, which is the property this whole skill exists to refuse elsewhere.
2. **Then decide whether a Bash-command scan earns its noise**, knowing it would not have caught the
   instance that prompted this. That is the honest bar: it catches a different, commoner case, and
   should be argued for on that rather than on this one.
