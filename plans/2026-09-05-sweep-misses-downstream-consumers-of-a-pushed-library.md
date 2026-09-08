---
status: landed
updated: 2026-09-08
source_repo: github.com-personal/repo-tasks
source_session: 92ffb648-b58c-42c8-a813-bc3782a7be4c.jsonl
source_moment: 2026-09-05T13:39:01+03:00
---

# The sweep clears a session that pushed a library change and left every consumer unswept

## Context

`session-harvest`'s step 5 asks what is true now: processes, sockets, disk, git state per repo, CI,
the stores, the absorb queue, `depends_on`, files outside every repo. Every one of those is about
**this machine**. None asks what a push **obliges elsewhere**.

Confirmed 2026-09-05 in `repo-tasks`. The session changed how every gate step runs — a new
`steps.py` that all of `quality.*`, `test.unit`, `deps.check` and `docs.build` now call — and pushed
it to `main`. The sweep then reported, correctly and in full:

| check     | result                         |
| --------- | ------------------------------ |
| dirty     | 0 paths                        |
| unpushed  | 0 commits                      |
| CI        | both workflows green on `HEAD` |
| processes | 0 surviving children           |
| stores    | nothing owed                   |

By every check the skill runs, that session was finished. It was not. `repo-tasks`'
`contributing/consumer-sweep.md` opens with _"A push to `main` is a deploy"_ — its bootstrap is
unpinned until a `vX.Y.Z` tag exists, so **every consumer's next CI run installs whatever `main` is
at that moment**, with no consumer-side action and no notice. Two named consumers, plus every repo
one of them generates, now run new code in their gate path that nothing has exercised there. That
file's own "When to sweep" lists _"a `quality.*` / `test.*` step that shells out to a binary"_,
which this change is, and it records the cost of missing it: two prior breaks, _"both times the
break was found from the consumer side, hours later, by reading a red CI run"_.

The gap is not that the session ignored a documented procedure. It is that **nothing asked**, and
the harvest is the step whose whole job is asking. The session ended clean, the report would have
said so, and the trigger existed only in a file nobody had reason to open.

## Why it is invisible to every existing check

The obligation lives in a repo the session never touched. `git status` there is clean because
nothing changed there yet — that is precisely the problem. CI there is green for the same reason,
until the next push to it picks up the new tool. No process, no socket, no store, no `depends_on`
edge. **The state is a stale snapshot in another repo, created by an action here**, and it is the
only category in step 5 that a push _creates_ rather than leaves behind.

The skill already recognises this shape once, for exactly one repo — "Sibling repos this skill
itself wrote to", which says a skill edit reaches nothing until pushed **and re-installed**, and
warns that other projects' `~/.agents/skills/` copy is now stale against the source. That is the
same mechanism (an artefact other things install) written as a special case for `agent-skills`.
Nothing generalises it to the other repos on this machine that are installed rather than merely
read: `repo-tasks` as a `uv tool`, `scaffoldapy` as a generator, `invoke-stubs` as a git dependency.

## What landed, 2026-09-08

[DECISION: **both detectors, with the machine-derived one doing the work.** The recommendation was
to ship the bullet first and build a detector only if the doc-based signal proved too rare. Built
now instead, because the answer is deterministic and this repo's own rule sends anything derivable
into a script rather than into prose an agent has to remember on every run.

The machine-derived half is the load-bearing one, exactly as this question guessed: any checkout
under the projects root whose own manifest or bootstrap script names the repo. The doc-based half is
reported beside it, because where a consumer-facing doc exists it is the precise answer and the
derived list is only a candidate.

**The manifest list needed two names that are not universal**, and that is worth recording rather
than discovering: `setup.toml` and `skills-lock.json`, which are what the two installers in play
here actually write. A list of only the standard Python and Node manifests answers "no consumers"
for the skills repo itself — whose sole consumer declares it in a `setup.toml`. The check was
verified against exactly that case.]

[DECISION: **report-only, and not a flag away from anything else.** Sweeping a consumer means
running its tasks in its tree, which a session that does not belong to it must not do. The finding's
home is the report and the next-session prompt, and the printed line says so where a reader will
meet it rather than only here.]

[DECISION: **its own bullet.** The existing "promised but never verified" bullet is about promises
made in the conversation; this obligation was never spoken aloud — it lived in a file the session
had not read, which is precisely why nothing surfaced it. Folding it in would have filed the finding
under a heading whose reader is looking for something else.]

## Evidence

- The unswept change: `repo-tasks` `ba9e8e6`..`4c0bd3a`, pushed 2026-09-05, green on CI.
  `contributing/quality-gate.md`'s "What the gate prints" describes what every consumer's gate now
  prints; `src/repo_tasks/steps.py` is the new module in their gate path.
- The trigger that existed and was not consulted until the harvest: `repo-tasks`
  `contributing/consumer-sweep.md`, "When to sweep", and the two measured breaks in its own preamble
  (2026-08-24/25).
- The consumers, from that file: `power-user-linux-setup` and `scaffoldapy`, the latter also baking
  the configs into every repo it generates, whose e2e tier runs the _generated_ repo's gate — the
  place a `steps.py` problem would actually surface.
- The distinctive phrase to search this session's transcript for is the user's opening instruction,
  _"Before touching quality.py: ls ~/.local/state/session-bash-audit/"_.

## Recommended direction

Add it to step 5 as its own bullet, phrased as a question the session can answer from what it
already knows — "did this session push to a repo other repos install, and does that repo document
what a consumer owes after such a push?" — and leave the action as a report line plus a
next-session-prompt item rather than anything automated, per the second open question. Build the
machine-wide detector only if the doc-based signal proves too rare to fire.

## Migrated to

- **`skills/session-harvest/references/rationale.md`**, "What the step-5 checks owed a reader, and
  what measuring them cost the plans" — retired with eight siblings as one finding: a check has to
  say what it did not measure, and each of the nine was a check that answered instead. That section
  also records what this plan's own recommendation cost when measured.
- **`skills/session-harvest/scripts/harvest.py`** and **`SKILL.md`** carry the mechanism and the
  incident, each beside the code or the bullet it governs.
- Not migrated: the named consumers and the SHAs of the unswept change. The mechanism is derived
  from the machine now, so no list needs maintaining.
