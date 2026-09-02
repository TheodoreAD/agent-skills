---
status: landed
updated: 2026-09-02
---

# `session-harvest`'s mechanical half is re-derived by hand every run, and should be a script

## Context

`session-harvest` is 937 lines and it is the only skill in this repo whose procedure is entirely
prose. `plan-docs` is a comparable 1025 lines but delegates every mechanical step to
`scripts/plans.py`; `session-bash-audit` is 200 lines because `scripts/audit.py` carries the work.
The harvest carries none, so every run re-derives the same dozen commands from prose — differently
each time, because prose does not constrain the spelling.

Two costs, and the second is the expensive one.

**Each run pays a permission prompt for commands that match no allowlist rule.** Raised by the user
2026-09-02: "the harvest skill uses `date` directly, and that creates a security prompt". `date -Is`
is step 0's first instruction and matches nothing, so the very first thing every harvest does is
interrupt the user. The same is true of most of step 5's sweep. A single
`python3 <skill>/scripts/harvest.py …` prefix is one shape to allowlist instead of a dozen.

**The commands are re-invented per run, so the answers are not commensurable.** Measured 2026-09-02
across this machine's whole transcript store — **24,429 Bash calls in 1,134 transcripts**:

| hand-rolled shape                         | calls | distinct sessions |
| ----------------------------------------- | ----: | ----------------: |
| plans-store status/log                    |   568 |                39 |
| `git log origin/<branch>..HEAD`           |   498 |                78 |
| `gh run list`/`view`/`watch`              |   378 |                55 |
| python heredoc over a `.jsonl` transcript |   164 |                46 |
| `plans.py absorb`                         |   126 |                36 |
| installed-vs-checkout `diff -q`           |    94 |                34 |
| `ps -o` for live processes                |    93 |                46 |
| anchored `depends_on` grep                |    91 |                44 |
| `git rev-parse --abbrev-ref @{u}`         |    51 |                22 |
| `audit.py --session`                      |    42 |                12 |
| `docker system df` / `docker images`      |    34 |                 8 |
| `ss -ltnp`                                |    20 |                14 |
| `state.json` / `linkScanPath` resolution  |    12 |                 4 |
| `date -Is`                                |     9 |                 6 |

That is the same argument the dependency-health plan made for `package_health.py` and won on: a
lookup done from scratch every time drifts, and its answers stop being comparable across runs.

**The transcript reader is the worst of them.** Step 4 asks for a heredoc of "a few dozen lines of
Python" — 164 invocations across 46 sessions, no two alike. It has to filter `type == "user"`,
extract text blocks, find `AskUserQuestion` results in tool-result blocks, and resolve a background
job's real transcript. Every one of those has already failed in a documented way, and each failure
was fixed **in prose** rather than in code, so the next run's heredoc reintroduces it:

- an inferred session id read a stranger's transcript (2026-09-01, 386 calls reported as the job's);
- a heuristic `AskUserQuestion` filter returned `Read` outputs alongside real answers (2026-09-02);
- `$CLAUDE_JOB_DIR/../state.json` was simply the wrong path and raised `FileNotFoundError`
  (2026-09-02, fixed in `1a43c3f`).

A prose fix to a heredoc nobody keeps is a fix that has to land again next run.

## What this is not

[DECISION: **the judgement stays in prose, and that is most of the file.** The significance test,
the routing filters, "there is no memory tier", the report's four groups and their ordering, the
next-session prompt's subtraction rule — none of that is mechanical and none of it moves. This plan
proposes extracting the part that is already written as commands, which is roughly step 0's checks,
step 4's transcript extraction, and step 5's sweep. The prose that stays should get _shorter_,
because the paragraphs explaining how to spell a command become a flag with a docstring.]

## Recommended direction

### 1. `skills/session-harvest/scripts/harvest.py`, stdlib only

Same constraints as `plans.py` and `audit.py`: run by path, no install step, `--json` on everything
that reads, and every subcommand read-only unless it says otherwise.

```
harvest.py boundary                 # the step 0 instant, printed once and echoed by every later call
harvest.py skills-state             # installed-vs-checkout diff, checkout dirty/ahead, moved-since-start
harvest.py transcript               # resolve THIS session's transcript, print the path it settled on
harvest.py turns                    # user turns + AskUserQuestion answers, from the resolved transcript
harvest.py sweep                    # processes, sockets, disk, git across every repo touched, CI, stores
harvest.py claims                   # green-gate assertions made to the user, for the exit-masked rule
```

`sweep` is the big one and should print one grouped report plus `--json`, so the agent reads a
result rather than composing twelve commands. It subsumes the `ps`/`ss`/`docker`/`git`/`gh`/store
bullets that step 5 currently spells out one paragraph at a time.

### 2. Fold the accumulated corrections into the code, not the prose

Each of these is currently a paragraph warning the agent not to make a mistake the script can simply
not make:

- resolve the branch with `rev-parse --abbrev-ref @{u}`, never type `main` (measured: 22 of 71
  clones were on `main`, so the substitution is wrong more often than right);
- run the ahead-count and the fetch unpiped, and read the fetch's exit code before trusting either;
- `gh run view --json status,conclusion` rather than a watch whose exit code a pipe can discard;
- anchor the `depends_on` grep at line start, and sort the hits into the tag's two meanings;
- resolve a background job's transcript from `state.json`, wherever that file actually sits;
- take the boundary before anything else and carry it, rather than re-deriving it later.

Six documented failures, each of which recurred at least once _after_ the prose warning existed. The
skill's own rule — "when a rule is observed being missed in practice, strengthen its language rather
than lengthen its explanation" — has been applied to all six and the misses continued. That is the
signal that the fix is not wording.

### 3. Keep two things out of the script deliberately

- **The gate re-run.** `exit-masked` above zero means re-run the repo's own gate — which is the
  repo's command, not this script's, and hard-coding `inv quality.precommit` would be wrong in every
  repo that does not use it.
- **Anything that writes.** The harvest files plans through `plans.py` and edits through the normal
  tools. A script that both measures and writes is one an agent will run without reading.

## Open questions, all four answered by building it

[DECISION: `sweep` takes the repos from the transcript's own write paths (`Edit`/`Write`/
`NotebookEdit`) and its `cd`/`git -C` targets, each resolved to a git root, with `--repo` to add one
by hand. **Reads are excluded**, which is the whole distinction: a session that only read another
repo has not touched it for this purpose, and counting reads is the difference between a sweep
reporting six repos and reporting the two that matter.]

[DECISION: everything is testable except this machine's live state. The parsers take text, every
external command goes through an injected runner, and an autouse fixture replaces `subprocess.run`
with something that fails the test — the same shape `package_health.py` used for the network. That
covers the `ps`/`ss`/`docker` parsers too; what stays untested is only whether this machine's `ps`
prints what the fixture claims, which no unit test could answer anyway.]

[DECISION: no allowlist rule is assumed or proposed here. It belongs to the machine's own repo, as
the question framed it, and the script's value does not depend on it — one prefix to approve instead
of a dozen unrelated commands is worth having either way.]

[DECISION: the 700-line target is reported as missed rather than met by deleting evidence. 967 →
848: every command spelling is gone, and what is left is judgement and dated confirmations that the
plan's own scope note says must stay. The per-section numbers are in "What landed" below.]

## Evidence

- The measurement table above: `24,429` Bash calls, `1,134` transcripts, 2026-09-02.
- Sizes the same day: `session-harvest` 937 lines with no `scripts/`; `plan-docs` 1025 lines with
  `plans.py`; `session-bash-audit` 200 lines with `audit.py`.
- The user's own framing, 2026-09-02: "the harvest skill uses `date` directly, and that creates a
  security prompt, make a plan to revise the whole skill based on session history and absorb into
  python code all the hand-rolled recurring bash and python scripts".
- The three transcript-reader failures listed above, all already written into `SKILL.md` as prose
  corrections, the last of them committed the same day as this plan.

## What landed, 2026-09-02

`skills/session-harvest/scripts/harvest.py` (stdlib only, run by path, `--json` everywhere,
read-only throughout) with the six subcommands as proposed: `boundary`, `transcript`, `turns`,
`skills-state`, `sweep`, `claims`. `tests/unit/test_harvest.py` covers it with 30 tests, one per
documented trap, no test shelling out — asserted by an autouse fixture that replaces
`subprocess.run` with something that fails the test.

The four open questions, answered by building it:

1. **What `sweep` counts as a repo the session touched:** write paths from the transcript's own
   `Edit`/`Write`/`NotebookEdit` inputs, plus `cd` and `git -C` targets from its Bash commands, each
   resolved to a git root; reads are excluded, and `--repo` adds one by hand. As filed.
2. **How much is testable:** all of it except the live machine state. The parsers are fixture-backed
   and every external command goes through an injected runner, the same seam `package_health.py`
   used for the network. `ps`/`ss` output is fed to the tests as text, so even those parsers are
   covered — what is untested is only whether this machine's `ps` prints what the fixture says.
3. **The allowlist rule:** deliberately not assumed here. It is a decision for the machine's own
   repo, exactly as the question framed it.
4. **The line count: 967 → 848, not under 700, and the target is the thing that was wrong.** The
   mechanical prose is gone — step 0's command spellings, step 4's heredoc instructions, and roughly
   a third of step 5's bullets are now a flag with a docstring behind it. What is left is judgement
   and dated evidence, which the plan's own DECISION says must stay. Step 5 fell 270 → 218 and step
   0 127 → 109, while step 2 (129 lines of routing filters) never had a command in it to remove.
   Cutting the remaining 150 lines would mean deleting the evidence that makes the rules survive
   review, so the number is reported rather than met.

**One thing the build found that the plan did not predict:** the `AskUserQuestion` filter did not
need a third string-matching fix at all. `tool_result.tool_use_id` links back to a `tool_use` block
whose `name` is `AskUserQuestion`, which asks the transcript what the tool _was_ rather than what
its output looks like — immune to every failure this rule has had. Measured on the transcript the
answer-extraction plan cites: 7 answers by id, 8 by anchored preamble, the extra being a grep's own
output. The preamble count is still printed beside it as the self-check that plan asked for.

Two more surprises, both caught by running the thing against this machine rather than by reasoning:

- Comparing `scripts/` directories raw reported three skills as differing at once, because the
  checkout accumulates a `__pycache__` the moment a script is imported and the installed copy does
  not. A false "the install is behind" on the exact comparison step 0 exists to get right.
- Reading a listening process's `/proc/<pid>/cwd` as "what it serves" turned a browser started from
  a repository into a finding about that repository. The served directory is now inferred only for
  something that looks like a file server, or that names `--directory` outright.
