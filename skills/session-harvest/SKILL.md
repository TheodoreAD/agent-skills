---
name: session-harvest
description: "Use when invoked explicitly as /session-harvest, or when the user asks what's worth saving before compacting/ending a session, or says something like 'harvest this session', 'anything to remember here', 'anything dangling before I stop', or 'is it safe to compact'. Reviews the conversation for anything worth keeping and routes each item to a plain file every agent can read: plan-specific content to plans/*.md (per the plan-docs skill), repo-specific durable knowledge to that repo's AGENTS.md/docs/contributing, and cross-repo/personal preference to ~/AGENTS.md. Never a harness's own memory store, for any project or any reason — that vendor-locks the work. Then sweeps live state the conversation can't show: processes the session left running, unpushed commits in every repo it touched, CI on what it pushed, and work it promised but never verified. Ends with a report ordered least- to most-urgent, a safe-to-compact verdict, and a next-session prompt. On-demand only — never installs hooks or runs automatically."
---

# Session harvest

Reviews a conversation for what's worth persisting before it's compacted or ends, and makes sure
each candidate lands in the _right_ place — not just memory by default because memory is the easiest
tool at hand. Primary invocation is explicit (`/session-harvest`); the description above also
matches natural-language phrasing, but explicit invocation is the one to rely on — description
matching for something this consequential (it writes files) has been reported unreliable by prior
art (see `references/rationale.md`).

On-demand only. Installing hooks, wiring `settings.json`, or running on any schedule is explicitly
out of scope — that's a different, heavier tool (see `references/rationale.md` for the prior art
considered and rejected).

## The script

`scripts/harvest.py` carries every mechanical step: the boundary, the installed-vs-checkout
comparison, resolving this session's transcript, extracting the turns and answers, the live-state
sweep, and the green-claim count. **Run it rather than composing the commands by hand** — measured
2026-09-02 across 24,429 Bash calls in 1,134 transcripts, those commands were re-invented every run
and drifted, so answers that ought to be comparable across harvests were not. Six documented
failures are now code the script cannot repeat (the upstream branch is read rather than typed,
nothing runs through a shell so no pipe can eat an exit code, CI is read as JSON, `depends_on` is
anchored, a job's transcript comes from its `state.json`, answers are matched by tool-use id).

```shell
H=~/.agents/skills/session-harvest/scripts/harvest.py   # or <checkout>/skills/session-harvest/scripts/harvest.py
python3 $H boundary                                     # step 0, first command of the run
python3 $H transcript --expect '<a command this session ran>'
python3 $H turns                                        # step 4
python3 $H skills-state --since <session start>         # step 0 — needs a checkout, see below
python3 $H sweep --boundary <instant>                   # step 5
python3 $H claims --until <instant>                     # step 5, the exit-masked rule
```

**`skills-state` is the one subcommand `$H` from the install cannot answer**, because it compares
the install _against a checkout_ and an installed copy has no repo above it: run from there it exits
1 with `no skills checkout found — pass --checkout <path>`. That is the correct answer and it reads
like a broken install, which is the wrong impression to form during the step about install state.
Point it at the checkout — the checkout's own copy of this script, or `--checkout <path>` — and if
you have no checkout at all, say the comparison was unavailable rather than that nothing had moved.
Confirmed 2026-09-04 by a harvest that ran the block above verbatim and got the error on its first
step-0 command. Every other subcommand works from either copy; `sweep` degrades quietly by design.

Every subcommand is read-only and takes `--json`. Two things are deliberately **not** in it: the
gate re-run (that is the repo's own command, and hard-coding one would be wrong in every repo that
spells it differently) and anything that writes — a script that both measures and writes is one an
agent runs without reading. The judgement below is the rest of the skill, and none of it moves.

## Procedure

### 0. Check the copy you are running is the current one

**`python3 $H boundary` is the harvest's first command, before anything else this run does.** Keep
the value; step 5 passes it to `--until` so the adherence figure describes the session's work rather
than this harvest's own sweep. Every step below adds Bash calls of a different character to the
transcript, so a boundary taken later has already lost some of them.

The running skill is a file copy dropped at install time, so a harvest can silently execute a
version older than the source — skipping exactly the checks most recently added, and reporting a
clean run because it never looked. `python3 $H skills-state --since <session start>` compares the
installed copy against the checkout for this skill and the others a harvest leans on; add
`--skill <name>` for anything else this run used. If they differ, say so; a stale harvest is worse
than no harvest, because its report reads identical. Added 2026-08-29 after the user asked for a
harvest "with the latest versions" — behaviour the skill did not have, and could not have confirmed
if asked.

**A difference has four causes, and only one of them is the stale install this step assumes.** The
subcommand prints the verdict; what matters is that you act on the right one:

| the checkout is              | what it means        | what to offer                       |
| ---------------------------- | -------------------- | ----------------------------------- |
| clean, level with the remote | the install is stale | a re-install — the assumed case     |
| clean, ahead by commits      | unpushed skill work  | see the push-state paragraph below  |
| **dirty**                    | work in progress     | nothing; report it and move on      |
| **a linked worktree**        | edits on a branch    | a merge first; a push installs none |

The last row is the one that reads as the first. `skills-state` prints a `worktree:` line naming the
checkout it belongs to, because nothing else in its output distinguishes them: the checkout is
clean, it is ahead by commits, and the natural remedy — push, then re-install — succeeds at every
step and installs nothing. `skills add <owner>/<repo>` takes the remote's **default branch**, so
until the worktree's branch is merged there is nothing new to install, and the verify step compares
the installed copy against a checkout that was never published. Offer the merge, or the local-path
install `skills add <path>` that `skill-authoring` documents for drafting.

**Say plainly that a re-install cannot fix either of the last two**, because the natural mental
model — "re-installing syncs them" — is wrong in both: the installer's source is the remote, not the
working tree. Offering one against a dirty checkout is a no-op dressed as a remedy, and worse, it
reframes another session's live restructure as an install-hygiene problem and invites exactly the
cross-repo interference the global rules forbid. Confirmed 2026-08-29 on `plan-docs`, mid
two-tier-store-split: 672 uncommitted insertions, nothing ahead of the remote — `git log` showed a
settled history, and only `status --short` saw it. Confirmed in the other direction 2026-08-30: same
non-empty diff, clean checkout level with the remote, two commits pushed minutes earlier — row one
exactly as written, and a re-install was the right answer. The same diff meant opposite things a day
apart.

A dirty checkout does **not** block the run. Both sessions above harvested correctly, because every
command they ran was against the committed version. Confirm in passing that the commands this run
needs are not themselves inside the uncommitted diff, and — **only if this session is working in the
skills repo** — treat it as a finding about step 6's fold-back, since that is the one case where the
fold-back is an edit into a checkout another session may be holding. From anywhere else it blocks
nothing: step 6 files a plan rather than editing, and a filing needs nothing from that checkout.

**A clean diff is not the whole answer, and this is the outcome it cannot see.** The comparison
comes back identical whenever the installer has already run — while the copy frozen in _this
session's context_ at load time is still the old one. No filesystem comparison reaches that. The
consequence is worse than running stale code: it produces confident, specific, wrong statements
about the very skills the harvest is auditing, in the report nobody re-checks. That is what
`--since <session start>` answers: it compares the skill's last commit against the instant this
session began, as instants rather than as strings. If the skill moved after the session started,
**re-read the `SKILL.md` from disk before relying on it**, whatever the diff said — **from the
checkout when the checkout is the one that is ahead.** Re-reading the installed copy is the fix for
a stale _context_ against a current install; when the install is itself behind, it hands back the
same superseded text the session already holds, and the instruction reads as satisfied. Confirmed
2026-08-30: a harvest ran fourteen minutes after a commit to this very skill, re-read the installed
copy as written, and got its own stale wording back; the checkout was clean, pushed, and two
paragraphs ahead.

**One case makes the whole branch a no-op, and it is the common one in this repo: the commits that
moved the skill are _this session's own_.** The subcommand lists them; when every one of them is
this run, the context holding the newest text on the machine is not stale — nothing was superseded,
because nothing was written by anyone else. Say so in one line and move on; do not re-read four
files to confirm that the session remembers what it just wrote. The re-read exists for a _different_
session's commit landing under this one's feet, and treating the two alike is how the most expensive
step in this procedure fires on the case it was never about. Confirmed 2026-09-02: a harvest in this
repo found all four skills it leaned on moved after session start, all four by its own commits. What
still pays is the second half — checking whether anything already done ran under superseded wording
— because a script committed mid-session does change what an earlier call returned.

**And that half has its own carve-out, in the same case: a session working _in_ the skills repo
usually called the checkout all along.** The `scripts/` line warns that an earlier call may have run
the installed copy, which is true from anywhere else and near-impossible here — a repo-relative
`skills/<name>/scripts/<file>` is what a session in that repo naturally types, and it is current by
construction. Confirm it from the transcript rather than assuming either way; the question is only
which path the calls used. Confirmed 2026-09-04 in this repo: three skills' `scripts/` all differed
between install and checkout, all three were reported as possible stale execution, and every call in
the session had gone to the checkout — the whole branch was moot.

**The cheapest trigger for all of this is free and arrives unprompted: the available-skills listing
changing mid-session.** A skill present that was not there before, or a description reworded, is
direct evidence that the installer has run since the session began — which is exactly when the
timestamp check is worth paying for on the skills this run leans on. It costs nothing, it needs no
command, and it covers a case the diff cannot reach: a re-install that touched skills this run was
not using still tells you the install state moved. Confirmed 2026-08-31, and it is what triggered a
re-check that the prescribed checks would not have: both changed skills' installed copies matched
the checkout, so the diff said "same" for everything and would have prompted nothing.

The three subdirectories fail differently, which is why the subcommand reports `SKILL.md` and the
rest apart. Only `SKILL.md` is held in this session's context, so only it can go stale there.
`scripts/` is shelled out to, so the next call already runs the new code — but a call made _earlier_
in the session ran the old one, which is worth its own one-line note. `references/` is read on
demand and is inert. Confirmed 2026-08-30: a directory-scoped query fired the re-read-and-audit
branch on a commit that touched only a `references/` page, and the audit was empty because the held
wording had never changed.

**When the checkout is ahead, its push state decides what may be offered as the remedy.** The
installer clones from the remote, so a re-install cannot deliver a commit that has not been pushed —
it reinstalls the identical stale copy, in a report that has just told the user re-installing is
what resolves the staleness. If the commit that closes the staleness is unpushed, say so and name
whose commit it is rather than closing on "re-install to pick this up": the push is outward-facing
and belongs to whoever authored it, per step 5's rule about unpushed commits. Confirmed 2026-08-30:
the checkout was `ahead 1`, and that one commit was exactly the one carrying the wording the run had
just re-read. Note the asymmetry that makes this easy to miss — the session is not blocked, since
reading the checkout is enough to run correctly. Only the remedy is broken, which is the part nobody
re-checks.

**And when the session has already _acted_ on that skill, re-reading is only half the fix.** Ask
whether anything already done was done under superseded wording. Re-reading corrects the next call;
it does nothing about the pushes already made. Confirmed 2026-08-30: a session had run `plan-docs`'
`scan --mode tree` before pushing a store, while a commit landing four hours after it loaded that
skill had changed the pre-push gate to `--mode history`. Re-reading would have left the pushed
history unchecked; running the superseding command retroactively is what closed it, and it came back
clean.

The failure this whole branch exists for, confirmed 2026-08-29: a session held `plan-docs` from load
time, was told by a later commit that the store's pre-push gate is `scan --mode history` rather than
`--mode tree`, never saw it, and filed the opposite claim into a plan — a confidentiality gate,
reasoned about from stale wording.

### 1. Significance test first

Re-read the conversation for candidates. For each one, before anything else: _if this were lost,
would a future session go wrong?_ Anything that fails this is dropped (optionally noted in the
report as "considered, not worth persisting"), not proposed. This is the actual noise filter — apply
it upstream of routing, not after.

**Then, for anything shaped like a convention — "always do X", "never do Y" — check it is actually
true before proposing it.** Every filter below assumes the candidate is correct and only decides
where it goes. A convention inferred from what this session happened to do, or from a sample of one
or two sibling repos, is a hypothesis: check it against the tool's own documentation and real
community practice first, and say which you checked. Losing a candidate costs one rediscovery;
writing a wrong one into a shared doc costs every future reader, and the shared doc is exactly where
nobody re-derives it. Confirmed 2026-08-27: a harvest proposed recording "don't make `tests/` a
package" from two sibling repos that happen not to — pytest's own docs say the opposite for the
default `prepend` import mode ("highly recommended to arrange your test modules as packages"), and
the session had actually backed out of `__init__.py` to satisfy a shared type-checker config. The
true finding was a different claim with a different destination, and only the user pushing back
surfaced it.

### 2. Routing filters

For what survives the significance test:

- **Plan-specific content → `plans/*.md`, never memory.** If the session touched or produced work
  that the `plan-docs` skill would track — a design, an idea, in-progress implementation — it does
  not get a memory entry. Check whether the relevant `plans/YYYY-MM-DD-*.md` already captures it; if
  the repo uses `plan-docs` and it doesn't, say so and offer to create/update the plan file instead
  of saving to memory. Memory has no retirement mechanism, so a plan snapshot parked there would
  just rot silently — `plans/` already owns that lifecycle. **If a plan file already exists but its
  `status` is now stale** (e.g. `planned`/`in-progress` when the session just finished landing and
  verifying the work), invoke the `plan-docs` skill directly to apply its own status-bump/retirement
  procedure — don't improvise an `AskUserQuestion` about whether to retire it. Confirmed as friction
  2026-08-23: asked the user a retirement judgment call that `plan-docs`'s own "Retiring a plan"
  section already answers (default: preserve unless the rationale is already covered elsewhere in
  the repo); the user's correction was "why isn't the plan docs skill kicking in?"
- **Repo-specific durable knowledge → `AGENTS.md`/`docs/`/`contributing/`, never memory.** Use this
  split, not a flat "put it in AGENTS.md":
  - `AGENTS.md` (or equivalent instructions file) — only operating instructions an agent needs on
    _every_ task in that repo (commands, conventions, gotchas that change behavior). Keep it
    minimal: it's loaded into every session unconditionally, so this is the actual bloat-avoidance
    lever, not a place to write everything learned.
  - `docs/*.md` — usage-facing reference material, linked from `AGENTS.md`, read on demand.
  - `contributing/*.md` (or a skill's own `references/*.md`, if the knowledge is about a skill
    itself rather than the repo) — design rationale, prior art, implementation gotchas, also on
    demand.
- **Cross-repo/personal preference (not tied to one project) → `~/AGENTS.md`, never memory either.**
  Same logic as the repo-specific split above, one level up — version-controlled via its real
  source. If `~/AGENTS.md` is generated (assembled from fragments, deployed by a dotfile manager,
  symlinked out of a repo), find and edit that source; a deployed file is silently overwritten on
  the next run, so an edit there is lost and reaches no other machine. On this author's machine it
  is assembled from fragments under `power-user-linux-setup/config/agents-md/`, whose `README.md`
  says which fragment owns what. **Read the canonical source before drafting an addition — the
  deployed copy loaded into a session's context can be structurally stale against it.** Confirmed
  2026-08-24: a session held a ~20 flat-section `~/AGENTS.md` while the source had been restructured
  to 7 clustered ones, so an addition drafted against the section names in context would have
  targeted headings that no longer existed. `grep -n '^## ' <source>` first. **A candidate that's a
  _variant_ of a rule already there extends that rule's existing section — it doesn't get a new
  one.** "Already covered → skip" (below) is for an exact duplicate; this is the near-miss case,
  where the principle is written down but this particular shape of it isn't. Default to appending a
  short paragraph to the section that already frames it, because that file is loaded into every
  session in every repo, so a new heading costs context everywhere and a reader who sees three
  instances under one principle generalizes better than one holding three unrelated rules. Reach for
  a new section only when the trigger and the detection signal are both genuinely different from
  anything already there. Resolved 2026-08-23: "don't characterize a multi-file diff from one
  sampled file" was folded into "Verify what actually happened, not what output looks like" — which
  already covered clean-stdout-vs-exit-code and test-suite-vs-throwaway-script, both the same "the
  convenient surface signal isn't the real signal" shape.
- **A skill that already owns the topic beats a new always-loaded rule.** `~/AGENTS.md` is not the
  default home for every cross-repo finding. Whatever document states that file's admission criteria
  is the gate (on this author's machine, `power-user-linux-setup/contributing/global-agents-md.md`'s
  "Admitting a new rule"); where no such document exists, the tier test below still applies — a rule
  whose miss is _silent and expensive_ belongs in the always-loaded file, while one with a sharp
  trigger whose miss is _cheap and recoverable_ belongs in a skill. Check the file's current size
  against its own reference points (`grep -c '^### '`, `wc -l`; ≤15 rules / ≤200 lines) before
  proposing, and say the numbers out loud when asking — admission is a real cost once it is over
  them, and the user should decide with that in view. Resolved 2026-08-25: `pgrep -f` matching the
  harness's own `zsh -c … eval` wrapper (a false positive that reads as a real process) went to
  `session-bash-audit` — which already invites newly noticed Bash anti-patterns and can _measure_
  the rate — rather than becoming a 34th rule in a file already at 33 rules / 390 lines.
  Counter-example, resolved 2026-08-28 the other way: a non-terminating CI-poll loop went to the
  always-loaded file _despite_ it standing at 37 rules / 446 lines, because the tier test is decided
  by the miss, not by the budget — this miss is silent by construction (a loop that cannot fail
  emits nothing, so "still waiting" and "will never finish" look identical) and it had already made
  a session report a result it could never observe. Size pressure argues for a skill; it does not
  overrule "silent and expensive". Two levers keep the cost honest when the always-loaded file wins:
  extend an existing section instead of adding a heading (rule count unchanged), and end the rule on
  the command that replaces the habit rather than on the warning. Report the before/after line count
  either way.
- **Destination mid-restructure → the plan reshaping it, not the file.** When a candidate's correct
  home is currently the subject of an open `plans/*.md` that is reshaping it — especially one that
  defines its own criteria for what may be added — record the candidate _in that plan_, as a
  `[NEEDS CLARIFICATION: ...]` item stating its trigger, rather than appending to the file.
  Appending bypasses the criteria that plan exists to enforce, risks the addition being restructured
  away unread, and conflicts with whatever session is doing the restructuring. Applies to any
  destination with an open plan owning its shape, not just `~/AGENTS.md`. Resolved 2026-08-23: two
  cross-repo rules routed to `~/AGENTS.md` while the (since retired) leanness pass was actively
  cutting it from 30 sections and adding admission rules of its own; both candidates were parked in
  that plan instead of appended, and were decided at its close.
- **A candidate belonging to another repo is _filed_ there, not queued here.** As of 2026-08-29
  `plan-docs` has `plans.py new <topic> --for <repo>`, which writes the plan into that repo's store
  mirror outside every working tree: no commit crosses, and the session that next works in that repo
  is offered it by `plans.py absorb`. Prefer it over a `depends_on` plan in the current repo, which
  was the workaround before the mechanism existed and leaves the candidate somewhere the owning repo
  never looks. Commit the filed plan in the store immediately — a dirty store forces every other
  session into the add-a-new-file fallback for as long as it lasts. `depends_on` keeps its own,
  different meaning: **this** work cannot land until that repo changes, which is a dependency rather
  than a delivery.
- **A skill or an instructions file that was misused, misread or ignored → filed immediately,
  against the repo that owns it.** Not held for the report, not described in prose at the end: use
  `plan-docs`' own routing — `plans.py new <topic>` when this repo owns the skill,
  `plans.py new <topic> --for <repo>` when another does, committed in the store straight away — and
  then have the report name the finding and the plan filename. The rule is "file first, report
  second", because a finding that exists only in the report dies with the terminal.

  This covers three shapes, and all three are easy to mistake for narration rather than findings:
  - a rule that was **followed and still produced the wrong outcome** — the rule is wrong or aimed
    at the wrong case;
  - a rule that was **reasoned around** — the wording explains a mechanism rather than stating a
    constraint, and a mechanism can be argued with;
  - a rule that was simply **not followed**, repeatedly — the wording is fine and something else is
    failing, which is a measurement question rather than a rewording one.

  Say which of the three it is, since each has a different fix, and attach whatever the session can
  count. Confirmed 2026-08-30: one session produced all three — a `~/AGENTS.md` memory rule reasoned
  around, a status gate bypassed by editing frontmatter instead of calling `set-status`, and a
  `head`/`tail` prohibition violated in 28% of the session's own Bash calls. Each became a filed
  plan against the repo owning the rule; none would have survived as a paragraph.

  **Check whether the misuse is already filed before filing it, and search the store as well as the
  repo.** On a machine running parallel sessions the likeliest explanation for a rule being broken
  is that somebody has already noticed — the same reasoning as step 5's already-owned bullet, which
  is written for the live-state sweep and is easy not to apply here. When it is owned, the session's
  numbers are _evidence for that plan_, so they go into it rather than into a new file; `plan-docs`
  prefers one plan per topic, and a second one splits the corpus the first is accumulating.
  Confirmed 2026-08-30: a session measured its own Bash calls, found 36% piped through `head`/`tail`
  and was about to file it — two plans already owned the contradiction, one of them citing "25–36%
  for two other sessions the same day". What survived as genuinely new was one row nobody had
  measured, and it landed in the existing plan as a fourth sample.
- **Already covered → skip.** If an existing doc already says this, don't write a duplicate — check
  first.
- **Meta-conventions about how to build things in this ecosystem (e.g. "skills should do X by
  default") → the relevant existing skill's own docs, not a feedback memory** — even though on the
  surface "how to approach work" sounds like the `feedback` bucket. Resolved via `AskUserQuestion`
  during this skill's own design: a preference about how _new skills_ should be authored belongs in
  the skill-authoring skill (durable, version-controlled, visible to every contributor/tool), not
  this harness's private memory store. Use that as the default for similar cases rather than
  re-asking each time.

### 3. There is no memory tier

**Every survivor lands in a plain file, and step 2 is the whole of the routing.** A harness's own
memory store is never a destination — not for durable content, not for perishable content, not as a
staging area, not "just this once".

[DECISION: stated by the user 2026-08-29 — no memories, for any harness, for any project, for any
reason, because project data and user-wide practices must not be vendor-locked. The carve-out is
harness **configuration** (`settings.json`, hooks, keybindings), which is expected to differ per
harness because it describes the tool rather than the work. The sorting rule: configuration
describes the harness; anything describing the work is a plain file any agent can open.]

**State the ban, not the mechanism.** Earlier versions of this step sent "genuinely temporary"
survivors to the harness's memory store, and explaining _why_ that store is a poor home is precisely
what let a session reason its way to an exception — see
[`references/rationale.md`](references/rationale.md), "Why no memory tier at all".

If a candidate fits no filter in step 2, that is a signal to add a filter there (step 6's
self-update) — never a reason to reach for a harness feature. The gap is usually smaller than it
looks: an `in-progress` plan is already sorted above everything else by `plans.py list`.

### 4. Loose-ends pass

Separate from the memory scan: is there in-progress state in _this_ conversation that isn't
memory-worthy (failed step 1) and isn't covered by a plan file either, that compaction would still
lose track of? Surface it explicitly — recommend a `plans/*.md` entry if it's real design/idea work
worth resuming, or say plainly that it's fine to let go if it's genuinely ephemeral task state.

**Read the conversation, not only the summary.** A compacted session hands you someone else's
précis: intermediate summaries drop exactly the loose ends this step exists to catch, and their
confident tone reads as completeness. `python3 $H turns` prints the real user turns and every
`AskUserQuestion` answer from the transcript, in order — re-read the original instructions rather
than the recap of them. Confirmed 2026-08-28: the brief's own "this needs a full tier run
afterwards, only one common cause was established" survived into no summary, and neither did an
explicitly-declined consumer sweep.

**Confirm the transcript is yours before reading anything into it.** In a background job the session
id is not the transcript id, and every guess at it lands on a real file belonging to someone else —
confirmed 2026-09-01, when a harvest read a stranger's session and reported 386 calls, none of them
the job's, without a single sign anything was wrong. The script resolves this from the job's
`state.json` and prints the path it settled on; `--expect '<a command this session definitely ran>'`
is the check that costs nothing, selecting the transcript by content when no id is to hand and
verifying it when one is. **Never reconstruct a path from an id you inferred** — a wrong id that
names nothing errors out, while one that names the wrong file cannot be told from a right one by
reading the output.

**The brief arrives in three ways, and a run that finds two has not been told so.** A user turn is
one; an `AskUserQuestion` answer is the second; the third is a message the user sends **while a turn
is still running**, which the harness records as a `queue-operation` rather than as a user turn.
`turns` prints all three, labelled, with the harness's own noise (task notifications, interruption
markers, slash-command wrappers) counted separately so "six user turns" cannot mean three. Confirmed
2026-09-02: a session's richest instruction — new scope, roughly its last third, two plans and six
commits — was sent mid-turn and appeared in none of the six turns the extraction reported. **The
miss is invisible exactly where it costs most**, because a mid-turn message is what a user sends
when they think of something while the agent is working, so it is disproportionately new scope with
no earlier trace to recover it from.

**The answers are half the brief, and on a tool-driven session they are most of it.** A user turn is
`type == "user"` with text; an answer to an `AskUserQuestion` is not, so a scan written for the
first finds none of the second. Confirmed 2026-08-31: a five-hour session's extraction returned ten
"user turns", of which most were slash-command wrappers and one was `/clear` — while every
substantive instruction in the session had arrived as an answer and appeared in none of them. A
harvest reading only the turns would have concluded the user said almost nothing and harvested
against its own summary. The two populations differ in content, which is why an incomplete filter is
worse than a miscount: a listed option is a word or two a harvest could infer from what the session
then did, while a typed answer is the user writing prose about what they want, which is exactly what
this step exists to recover.

[PITFALL: **this filter has been wrong in both directions, and both times the wrong version looked
right.** First a heuristic looking for "question" and "answers" anywhere in a tool result, which
returned `Read` outputs alongside real answers. Then a narrowing that named
`Your questions have been answered:` as _the_ marker and missed every typed answer — those open
`The user answered:` — on a session where three typed answers carried the whole second half of the
brief. The narrowing's own confirming note predicted its successor's failure without recognising it:
"harmless here because both real ones were found, and precisely the shape that returns a plausible,
incomplete set on a session with more of them". `turns` now matches by **tool-use id** — it asks the
transcript what the tool was, rather than what its output looks like — and prints a raw preamble
count beside it so a disagreement is visible rather than silently resolved. A disagreement is
normal: this skill's own text quotes both markers, so any transcript that loaded it counts itself.]

### 5. Live-state sweep

The parts of "dangling" that are not in the conversation at all. The transcript says what was
_intended_; these say what is actually true now. `python3 $H sweep --boundary <instant>` runs them —
processes, listening sockets, disk artifacts, git state for every repo the session wrote to, CI,
both stores, the absorb queue, `depends_on` plans, files written outside every repository, and paths
named in edits that do not exist. Add `--repo <path>` for a repo the transcript cannot show. Run it
even when the session felt tidy, because every one of these has been wrong at least once.

**Two of those steps assume a POSIX machine**: processes come from `ps -eo` and listeners from
`ss -ltnp`, which is Linux-only — on macOS or Windows the socket step reports itself unavailable
with the reason, which is the honest answer and not a clean bill of health. Everything else in the
sweep is `git`, the harness's own files, and Python, and works anywhere.

What the script cannot do is decide what a finding means. That is this list:

- **Processes and what they serve.** A backgrounded poll outlives the turn that spawned it —
  confirmed 2026-08-28, four CI-poll loops 36 hours old, still polling, whose exit condition could
  never be true; the harvest was the only thing that would ever have found them. For anything
  holding a listening socket the bind address and the directory it serves are the finding, not
  liveness: a long-running dev server is _supposed_ to be running. **A development server's default
  bind is usually every interface**, and that default is invisible locally, since bound or unbound
  every local run behaves identically and only the reachable audience differs. Confirmed 2026-08-31:
  `python3 -m http.server --directory <repo root>`, 24 hours up, on `0.0.0.0`, serving that
  repository's `.env` and `.git` to the whole LAN.

  **A loopback bind narrows the audience; it does not close the finding.** An orphaned server is
  still an orphan, and the directory it serves is still readable to everything running as this user
  — which on a machine with several agent sessions and a browser is not a small set. Report an
  unowned listener over a repository root whatever its bind address, and say what is under it; the
  sweep names the served directory and any secret-shaped file in it, and `curl` on one gitignored
  path turns that into a status code. Confirmed 2026-09-02: an `http.server` deliberately bound to
  `127.0.0.1` by the repo's own task — the 2026-08-31 hazard designed out — three and a half hours
  old, orphaned by a one-shot command, whose gitignored `.env` answered 200. The run nearly stopped
  at "bound to loopback, safe". Both cases belong in the report side by side, so the next reader
  does not learn "check the bind address" as the whole rule.

  **An orphan that comes back is a different finding, and killing it again is not the answer.**
  Re-check the pid before reporting a kill as done: a fresh pid over the same port and directory
  means something restarts it, so the kill closed one instance and nothing else, and a report saying
  "killed" describes a state that no longer holds. Confirmed 2026-09-05: the same `http.server` over
  the same repo root was killed at the user's request, and a sweep half an hour later found it back
  under a new pid, sixteen minutes old, reparented to `systemd --user` exactly as before — orphaned
  again rather than held by a live session, which is the check that tells the two apart. Say that
  the kill did not hold and let the lifetime question own the fix; killing on a loop inside one
  session is the shape this skill refuses everywhere else.
- **Disk artifacts outside any repo.** Container images and build caches, throwaway interpreters,
  volumes — none of which `ps`, `git status` or either store can see. Report the sizes with a
  proposed removal line the user can approve; do not delete unasked, because the build cache is
  shared with every other project on the machine and an image another session is about to reuse
  costs a rebuild. **Say which were one-off verification artifacts and which a committed README
  names — the session is the only party that can still tell those apart.** Confirmed 2026-09-01: a
  run that had verified a container fix left a 4.11 GB image, 445 MB of others and a ~58 GB
  machine-wide build cache, while the processes check reported clean and correctly so.
- **Files this session edited that no repository and no store covers.** The sweep subtracts every
  write path inside a git repo and reports what is left; the work is saying **what would recover
  it**. Every other check here asks whether a store was left tidy, and a file belonging to no store
  is not untidy, it is unseen. An example file in a repo plus a validator that rejects a bad one is
  a real recovery path and not an obvious one; "no copy anywhere" is a finding worth stating
  plainly. Confirmed 2026-09-01: a session edited an unversioned config outside every working tree —
  no diff, no history, no backup, and operational data of the kind the repo that reads it exists to
  protect. The edit was correct and user-approved, which is what makes it the right instance:
  nothing went wrong and the sweep still could not see it, so a wrong edit would have been equally
  invisible.
- **This session's own rule adherence**, which nothing else in the sweep reaches:

  ```shell
  python3 ~/.agents/skills/session-bash-audit/scripts/audit.py --session <session-id> \
    --until <the step 0 boundary> \
    --compare ~/.local/state/session-bash-audit/<baseline>.json
  ```

  The baseline is one **you** saved with that skill's `--save-baseline`, which writes to
  `~/.local/state/session-bash-audit/` by default. **Without one, run the audit anyway and drop
  `--compare`** — the rates and `exit-masked` stand on their own, and only the comparison needs a
  baseline. Never compare against a baseline measured on somebody else's machine: that reports how
  your session differs from their setup rather than from your rules.

  [PITFALL: the first wording of this said "skip this step", which reads as skip the **audit** — and
  the step is the audit. Filed by a session that took the narrow reading on 2026-09-04, ran it
  anyway, and got its most useful number that way: **23% `exit-masked` across 189 calls**, with five
  messages telling the user a gate was green, every one from a `| tail`-ed run. All five held on
  re-run, which is what makes the wording easy to dismiss — the session could not have known that
  without running the audit the skip would have cancelled.]

  **Get `<session-id>` from the transcript the script resolved**, not from a path you happen to have
  — in a background job the id in the task-output path names a different transcript, the audit runs
  clean against it, and the verdict describes a session that is not yours.

  **`--until` is not optional, and the reason is not that the sweep looks bad.** A figure that
  includes this sweep measures the sweep: its calls are inspections, a different population from the
  session's working commands, and they drag the rate toward their own shape in whichever direction
  that happens to lean. Measured 2026-09-01 on two runs the same day — one rose 37% → 40% on
  `head`/`tail`, the other **fell** 22% → 17% on `git -C`. "The harvest inflates its own number" is
  the wrong claim and would have made the second run look like a refutation. **Report both
  numbers**, one line: "6% during the work, 14% including this sweep." The first is the session; the
  second is the honesty.

  **If `exit-masked` is above zero, this session's own green results are unverified — re-run the
  gate before believing any of them.** A masked exit code is not a style finding: it means a command
  reported success through a filter that discarded the real answer. Confirmed 2026-08-31: a session
  ran `inv quality.precommit 2>&1 | grep -Ei "…" | tail -3` perhaps twenty times, read the absence
  of a match as success, and pushed three red commits — `basedpyright` printed
  `0 errors, 6 warnings` and the gate exited 1, but the pipe reported `grep`'s exit code. Re-run it
  unpiped — `inv quality.check > log 2>&1`, then read the log — and make the gate conditional on the
  number so a slow gate is not re-run for nothing. This is the one command the script deliberately
  does not run for you: it is the repo's, not this skill's.

  **The re-run settles whether the greens were true. It does not touch the fact that they were
  asserted.** A session with a non-zero `exit-masked` has usually told the user "gate green" several
  times over the run, each time on evidence a filter had already discarded, and those sentences
  stand in the conversation whatever the re-run comes back with.
  `python3 $H claims --until <the
  boundary>` counts them against the masked calls. Report the
  count with the re-run's verdict attached. "Said the gate was green 15 times on masked calls;
  re-run exits 0, so the claims hold" is a footnote. The same sentence ending "re-run exits 1" is a
  **live inaccuracy with a reader**: the same shape as an unpushed commit correcting something
  already pushed, and it goes in "needs action now" for the same reason. The conversation is the
  record the user is actually working from, and it is the one artefact a later commit cannot amend —
  only a later message corrects it, and only if someone writes one. Confirmed 2026-09-02: a ten-hour
  session at 28% `exit-masked` had reported the gate green roughly fifteen times, every one from a
  `| tail`-ed run. The re-run exited 0 and all fifteen held — which is the outcome that makes this
  rule easy to skip, and the reason it is written as a count rather than as a warning.

  Report the two numbers and the comparison in the skill-and-instruction-misuse group rather than in
  the verdict; a self-flagellating report buries the findings the user needs. Confirmed 2026-08-30:
  a session that had spent the day authoring the rule against piping a gate through `head`/`tail`
  then produced that shape in a third of its own calls, and reported "went well, gate green
  throughout" — true, and beside the point. **Authoring a rule is not evidence of following it**,
  which is exactly why the number has to come from the transcript.
- **Git state, every repo the session touched** — not just the primary one. An unpushed commit is
  the most common real loose end, and a session that ends with one usually believes it pushed. The
  sweep reads the upstream branch rather than typing `main` (measured 2026-08-30: 22 of 71 clones
  were on `main`, fewer than were on `master`), runs the count unpiped so a wrong branch exits 128
  rather than printing a calm `0`, and checks the `git fetch` succeeded before trusting either
  answer — on this machine a fetch needs the Zenity SSH-passphrase dialog and fails with
  `Permission denied (publickey)` when nobody is at the keyboard, leaving `origin/<branch>` exactly
  where it was so the ahead-count still prints a plausible number against a stale ref. When that
  happens the machine's own diagnostic names the fix (`inv ssh.check` here) — do not reach for
  `ssh-add`, and apply the fix as a per-call environment prefix rather than an `export`, which does
  not survive to the next Bash call.

  Three judgements the count does not make for you:
  - **Who wrote the unpushed commits.** Where sessions run in parallel the ahead-count is not
    necessarily this session's work, and "you have two unpushed commits, push them" publishes
    another session's unfinished history under a recommendation that reads as routine. Name which
    are this session's and which are not, and let the user decide. Confirmed 2026-08-29: two commits
    from a parallel session appeared in the ahead-count between one push and the next, and asking
    rather than pushing was the only thing that surfaced them.
  - **Whether any of them corrects something already pushed.** That is not deferred work — it is a
    live inaccuracy with a reader — and reported flat it is indistinguishable from three plan
    updates in an ahead-count. The sweep lists paths that are both unpushed now and published
    earlier in this session; an overlap is not proof, but it is a short list to read and empty for
    most sessions. Name it in "needs action now", with what the remote currently claims. Confirmed
    2026-08-30: a session pushed a package description arguing why the package existed, learned an
    hour later that the argument was false, and committed the correction without pushing — so the
    remote served a justification known to be wrong while its fix sat in the ahead-count alongside
    ordinary tidying. Keep it to the same-session case; "is anything this repo currently publishes
    known-wrong" is a different question no harvest can answer in bounded time.
  - **That the count is from now.** Re-read it at report time; one taken earlier in the session is
    the session's memory wearing a measurement's clothes. Confirmed 2026-08-30: a session reported
    the plans store as "7 unpushed commits, 4 of them other sessions'", correct when counted; at
    harvest it was 27, of which 25 were other sessions'. On a machine this parallel the count moves
    fastest in the repositories several sessions share, which are the ones a harvest is most likely
    to be asked about.
- **Sibling repos this skill itself wrote to.** A skill self-update (step 6) commits locally and
  reaches nothing until it is pushed and re-installed, so **your skills repo** — whichever one these
  skills were installed from — is a repo the session touched and the one most likely to be
  forgotten, because the edit felt done when it was committed.
- **Paths this session told other sessions to run.** A rule written into an always-loaded
  instructions file, or a `SKILL.md` command block, names a path on this machine — usually an
  installed copy, not the checkout the session was editing. The sweep reports home-rooted paths
  written into files that do not exist; run one of the ones that do. Confirmed 2026-08-29: a session
  deployed a `~/AGENTS.md` rule pointing at `~/.agents/skills/<name>/scripts/<file>` while the
  installed skill still had no `scripts/` directory, so a machine-wide rule instructed every future
  session to run a file that did not exist. The checkout worked perfectly throughout, which is why
  nothing surfaced it.
- **CI, for anything this session pushed.** A green local gate is not a green CI run. The sweep
  reads `gh run list --json`, and reading the conclusion as JSON is the point: `--json` has no exit
  code to lose, so there is nothing for a pipe to take away. Never hand-roll an `until` loop, and
  never watch through a filter — confirmed three times, each by a harvest executing this checklist
  with the warning in front of it, reporting `tail`'s `0` as the run's.
- **Shared stores outside any repo**, if you keep any. `$RESEARCH_HOME` — set it only if you use the
  `research-library` skill — holds clones, caches, anything the session added to a location no
  `git status` covers. The failure is a half-finished convention rather than a missing file — a
  clone without its `SOURCE.md`, or one that failed partway — and it is invisible to every other
  check here precisely because _this_ store is not version-controlled. **Also check the entries the
  session _changed_, not only the ones it added**: a deliberate divergence from the store's shape
  reads as conformant, because the entry is present and its metadata is intact. Confirmed
  2026-08-30: a session deepened a `--depth 1` reference clone to ~436 commits to read a
  dependency's constraint history, which was the right call and left the store holding one entry
  that silently no longer matched its own convention. Record the divergence and why, in whatever
  file that store uses for per-entry metadata.
- **The plans store, `$PLANS_HOME` — a separate bullet, for a different reason.** Set by the
  `plan-docs` skill and absent if you do not use it, in which case the sweep skips this and says so.
  The sweep reports its dirty state and its unpushed commits, and runs `plans.py absorb` read-only.
  Two failures with separate owners: an uncommitted plan is this session's own mess, and a plan
  filed _for_ this repo is another session's gift. **The reason this went unnoticed in a skill whose
  whole subject is unswept state is that both neighbouring bullets appear to own it**: the store is
  a git repository (so the git bullet seems to cover it) and it sits outside every working tree (so
  the shared-stores bullet seems to). Each framing hands it to the other. What the git bullet
  actually misses is **uncommitted** work: an uncommitted plan is not a commit, so no ahead-count
  sees it. Do not write "the store has no remote" — the shareable tier has one and the sensitive
  tier deliberately does not, so committed-but-unpushed plans are a real second finding on the
  shareable half, gated by that skill's content scan before any push. **`absorb` runs here even
  though `plan-docs` already tells every session to run it first**: the queue refills for as long as
  the session runs, because the sessions filing into it run concurrently. Measured 2026-08-30 in a
  session that followed the first-call rule correctly — 4 plans at session start, 4 more two hours
  in, and 1 at five hours, that last one a credential exposure that sat unread for half an hour.
  Report a mid-transaction store — uncommitted changes that are not yours — rather than working
  around it; it means another session is actively holding that directory.
- **`depends_on` plans whose blocker may have lifted.** The routing filter above parks work owed to
  a mid-restructure repo in a `depends_on`-tagged plan — which stores it safely and gives it no
  trigger. Nothing watches the named repo, so a plan waiting on a repo that has been ready for days
  is indistinguishable from one waiting on a repo that is still busy. The sweep lists the tagged
  plans and their targets; **sorting them is yours**, because the tag carries two meanings that take
  opposite answers. Work parked because that repo was mid-restructure (this bullet's case, and a
  deprecated one now that `new --for <repo>` exists) is answered by that repo's current state.
  `plan-docs`' own documented meaning — "sibling repos this plan can't fully land without" — is not:
  the named repo being idle says nothing, because the blocker is a change that repo has not made
  yet, and only reading the plan answers whether it has. Report readiness only for the first kind;
  "seven plans ready" assembled from clean `git status` output is a claim the check never made.
  Confirmed 2026-08-29: eight tagged plans, three sibling repos all clean, and exactly one of the
  eight was queue-shaped. And verify against the working tree rather than the plan's prose — the
  same check that day read "surgery finished" from a clean `git status` and a landed plan, then
  found two modified files a few minutes later.
- **Work the session promised but never verified** — a test tier it added to but never ran, a
  consumer it changed but never swept. "I'll report when it lands" in the last message is a promise
  the harvest has to either keep or retract.
- **Work handed off to another session, and what it blocks here.** This user runs parallel sessions,
  so "another session is doing X, don't touch it" is a routine instruction — and it creates state no
  other check finds: not a process, not git state, not CI, not an unkept promise, but a dependency
  this session is stopped on and deliberately not solving. Name it in the report with what it
  blocks, so the handoff cannot fall between the two sessions. Do **not** re-probe the handed-off
  thing to report its status; that is the instruction being violated one call at a time. Confirmed
  2026-08-28: a session finished its work, could not push because the ssh agent was empty after a
  reboot, was told another session owned that — and the only remaining record of the blocked push
  was the harvest report.
- **Whether a finding is already owned, before reporting it as new.** A sweep that reaches back
  through history or across repos surfaces things this session did not cause, and on a machine
  running parallel sessions the likeliest explanation for a real finding is that someone else
  already found it. Check before escalating: the sibling repos' recent commits and their open plans.
  Report an already-owned finding as _confirmed still open_ and name the plan that owns it — never
  as a discovery, and never by acting on it. Confirmed 2026-08-29: a confidentiality scan returned
  55 hits in published history and was minutes from being reported as urgent, when another session
  had already rewritten both histories, force-pushed, opened a support request for the residue, and
  written all of it into a plan. Several probing calls, and nearly a duplicate alarm, for work that
  was done.

### 6. Improve the skill on every run

**This is not optional, and not only for friction.** The skill is actively dogfooded: each
invocation is also a test of it, and the author has said catching and fixing issues immediately is
the point. So before writing the report, ask explicitly: _did this run show the skill to be wrong,
incomplete, or unhelpful anywhere?_ Signals, in rough order of how often they are missed:

- The user's invocation supplied behavior the skill lacks (see the third trigger below).
- A step ran and produced nothing of value, or the run's best finding came from something no step
  asked for. Both mean the procedure is mis-aimed, and the second is the easier to overlook because
  the finding still got made.
- A step was skipped as inapplicable — was that judgment right, or is the step written too narrowly?
- Anything the user had to say twice, or ask about after the fact.
- The skill contradicted itself, or an instruction turned out ambiguous when applied.

Act on it now rather than filing it for later; a deferred skill fix is a skill fix that does not
happen. Keep the change small and additive. **A correction that a script can simply not make belongs
in the script, not in a new paragraph** — six of them are already there, each one having been
written as prose first and then recurred anyway. If a run genuinely surfaces nothing, say so in the
report in one line — an explicit "no skill changes needed this run" is the evidence the check
happened.

**Where the session is decides whether "act on it now" means an edit or a filing**, and this is not
a preference:

- **In the skills repo** (`agent-skills`, wherever this skill's source lives): edit the source and
  commit it locally without asking — it is reversible, reviewable as a diff, and pausing for
  approval mid-run is what makes the fix get dropped.
- **Anywhere else**, which is nearly every harvest: **do not edit and do not commit.** File it —
  `plans.py new <topic> --for github.com-personal/agent-skills` — commit the plan in the store, and
  name the filename in the report. Filing is the immediate action, not the deferral, so the "do it
  now" pressure is unchanged.

[DECISION: the global rule wins over this skill's own instruction, and it is not close.
`~/AGENTS.md` says writing to another repo is out entirely, "however much a skill's own instructions
tell you to" — a clause that reads as though written about this exact step. The skill's
justification for committing directly was that a deferred fix does not happen; that was true when it
was written and is not now, because `plans.py new --for` did not exist then and `absorb` gives a
filed skill fix a real trigger in the next session working there. The reasons are also asymmetric: a
silent commit in a parallel session's tree is a correctness problem, a deferred fix is a latency
problem. Confirmed 2026-08-30 by the failure — a harvest run from an unrelated project made two
correct, gate-green edits to this file and committed them in a repo it had no business writing to,
left sitting in `git log` for whichever session pushed next.]

**Deploying the skill edit.** Pushing and re-installing is outward-facing and always asked, because
that is the step that changes what other sessions and machines load. Confirmed 2026-08-28:
`Bash(git commit:*)` and `Bash(git push:*)` are both allowlisted on this machine, so no permission
prompt guards either — the discipline is entirely instruction-side, deliberately (see `~/AGENTS.md`,
"Proposing an enforcement mechanism for agent behavior"). Do not read the absence of a prompt as
permission.

### 7. On friction, ask — then self-update the skill

**Not just this session.** Three triggers:

- A candidate doesn't clearly fit any routing filter in step 2 (e.g. arguably both plan-specific
  _and_ a durable cross-repo preference), or the significance test itself is a genuine toss-up.
- The user corrects a routing decision this skill just made.
- **The user's own invocation asks for behavior this skill doesn't have.** Arguments like "make sure
  you also check X, not sure the skill does that today" are a spec, not a one-off request. Applying
  them to the current run and stopping there is the failure this step exists to prevent — and it is
  easy to miss, because the run itself goes well. Confirmed 2026-08-28: every live-state check in
  step 5 arrived that way, was executed, produced the session's most valuable findings, and was
  nearly lost because nothing prompted writing it down. If the user has to ask "did you update the
  skill?", this trigger already fired and was missed.

In the first two cases use `AskUserQuestion` to resolve it for _this_ item — never silently pick a
side on a real ambiguity. In the third the user has already told you what they want; just fold it
in. Either way the resolution goes back into this skill's source (see below) so the same friction
doesn't recur. Resolving it for one session only defeats the point of a shared convention skill.

**Do the fold-back before the final report**, not after — which is why both skill steps sit ahead of
it — and say in that report which destination was updated (this skill's source, or the always-loaded
instructions file). A harvest whose whole subject is "what would be lost" should not end by losing
its own lesson.

### 8. Harvest report

Last. **Bullets throughout, indented into groups — never prose paragraphs.** A harvest report is
scanned, not read, and an indented list is what survives scanning.

**A second harvest in one session re-runs the whole sweep and reports only the delta.** Those pull
in opposite directions and both are right: step 5 has to run again because live state moves between
the two — confirmed 2026-08-30, twenty minutes apart, a parallel session had committed to the store
in the gap and only the re-run saw it — while re-listing the findings the user read twenty minutes
ago buries the two lines that are new. Say what changed since the last report and name the earlier
one, rather than restating it.

**Open with where everything went**, as four groups, because "did this land somewhere durable, or is
it still only in the chat?" is the question the whole report exists to answer:

- **To code** — edits to source, tests, config that are committed.
- **To a plan in this repo** — `plans/*.md` here, by filename.
- **To a plan in another repo** — filed via `plans.py new <topic> --for <repo>` and committed in the
  store, by filename and target repo. **Say only that it was filed.** Do not restate what it asks
  for; the owning repo's session gets the whole thing from `plans.py absorb`.

  **Confirm the file is still there before naming it**, and check whether your store commit was
  pushed by someone else — `ls` the store directory, and
  `git -C $PLANS_HOME branch -r --contains <sha>`. A parallel session may have absorbed it into the
  target repo, which is normal and means the work arrived; say that instead. Confirmed 2026-08-30: a
  plan filed early in a session had been absorbed, merged into an existing plan there, and its
  store-side deletion committed and pushed hours before the harvest ran. A report written from the
  session's own memory would have named a path that no longer existed and called a published commit
  unpushed — two ordinary-looking status lines, neither of which reads as a guess.
- **Only in this conversation** — everything not written to a file anywhere. This group is the point
  of the list: it is exactly what the user must either decide now or carry into the next session's
  prompt, and it disappears when the window closes. Keep it short by writing things down, not by
  leaving them out.

Then, least urgent first, because the final lines are what a skimmed report retains:

- **Settled** — verified green/clean, no action. Say what was checked, so "fine" is a measurement
  and not an impression.
- **Skill and instruction misuse found** — see the routing filter in step 2; each one is already
  filed by the time the report is written, so this section names the finding, the repo it was filed
  against, and the plan filename. Never a list of things to file later.
- **Skill changes** — what step 6 changed to this skill, or one line saying it found nothing.
- **Decisions waiting** — documented, not urgent. Name plans that must be decided _together_.
- **Risks carried** — known and written down. For each, the falsifier: what observation would show
  the reasoning was wrong.
- **Needs action now** — dangling state, and anything the user alone can decide (a push, a
  re-install, a destructive cleanup). Last, and specific.
- Ends with a one-line verdict: "safe to compact" or "not yet — needs a decision on X."

**The verdict is not the end of the run — step 9 is, and it runs every time.** The report is what
this session leaves behind; the prompt is what the next one starts from, and a harvest that stops at
the verdict has done the expensive half and withheld the cheap one.

Fix what is cheap and unambiguous rather than only reporting it — kill the orphaned loops, write the
lost measurement into the plan that owns it — and report it as done. Reserve the report's last zone
for what genuinely needs the user. Anything outward-facing (a push) still gets asked.

### 9. The next-session prompt

**Print it on every harvest, asked for or not.** The heading said "if one is asked for" until
2026-09-04, which was a leftover from when this step was only a list of what to leave out — and it
worked exactly as written: harvests ended at step 8, and the user asked _"why doesn't
session-harvest produce a prompt for the next session as the last item? i thought we did that"_. The
feature had been built on 2026-09-01 precisely because they kept asking for it by hand.

**It is never empty**, so there is no silent case to design. The subtraction below removes most
candidates on a well-harvested session, but ordering — what to do first, and why this rather than
that — is not something any opening command prints, and there is always something to do next. A
prompt that comes out with nothing but its opening line means the subtraction was done badly, not
that the session had nothing to carry.

**It is the next session's first move, not a summary of this one.** Print it as a paste-ready block
at the very end — never a file. The user pastes it into the next session within minutes, which is
the only reason it may assert anything at all; a prompt written to a file rots on a shelf and reads
identically when it does.

**Build it by subtraction, and the subtraction is the whole design.** The next session's own opening
moves already print most of what a prompt is tempted to carry:

| it already runs                               | so it already knows                                     |
| --------------------------------------------- | ------------------------------------------------------- |
| `plans.py absorb`                             | every plan filed for this repo, incoming from elsewhere |
| `plans.py list`                               | what is open here, grouped by status, retirements owed  |
| `git status`, `git log origin/<branch>..HEAD` | dirty tree, unpushed commits                            |

**Run those three, and include only the delta.** Anything they print is not prompt content — it is
noise that costs the reader attention and buys nothing. This is the mechanical test for "is this a
marginal detail", and it is why the prompt is short: on a session that harvested properly, most
candidates fail it.

What survives is three kinds, and only three:

- **Ordering.** `list` says what is open; nothing on the machine says what to do first, or why this
  rather than that. Usually one sentence, and usually the most valuable line in the prompt.
- **Perishable state with a short fuse** — a background process still running, a CI run in flight, a
  skill edited but not re-installed so the next session would run the old copy. Things that will be
  false in an hour and that no opening command reveals.
- **A decision made in this session that is not yet in any file.** This one is a self-check: if it
  is not empty, step 2's routing failed and the fix is to write the thing down, not to carry it in a
  prompt.

**Every item is verify-then-act, never an assertion**: the command that re-derives the state, then
what to do if it still holds. "Push `103b0b6`" is a claim that may be false by morning;
"`git log origin/main..HEAD` — if it still shows one commit, push it" cannot be. Stamp the block
with the time it was written and say in it that anything older than a few hours should be re-derived
rather than trusted.

**Cap it at five items and one opening line.** The opening line names the single next action and the
file that carries its detail — a good prompt hands the next session one file to open, not a
briefing. Past five it has become a plan without a status field, which is the shape this convention
exists to prevent.

**Never in the prompt**, however tempting: anything the three commands print; anything already
written into a plan (name the plan, never restate it); the reasoning behind a decision (that is plan
content by step 2's routing); a narrative of what this session did (the report above already did
that, and the next session does not need it).

**It covers this repo only.** Work filed for another repo is already routed — it sits in the store
and `plans.py absorb` hands it to the session that can act on it, which is the first call that
session makes. Repeating it here creates a second copy that goes stale independently and aims a
reminder at the one session that cannot act on it. Confirmed 2026-08-30: a prompt carried two
cross-repo items that were already filed and absorbable, which is duplication rather than a handoff.
Same rule for a working-list plan in this repo — record that cross-repo work was filed, not what it
says.

[PITFALL: **the one carve-out, and it is narrow enough to state as a test.** Another repo earns a
line only when both hold: it is **high-risk or irreversible** (a history rewrite, a force-push, a
destructive cleanup, a published credential), **and** it would change what the next session in
_this_ repo does. A pending history rewrite in a repo whose plans this repo's store mirrors is the
shape that passes. An unpushed commit, an open plan, a failing test in another repo all fail the
second half — that repo's own next session is handed those, and this one cannot act on them. When
something does pass, one line: the risk, and the check that says whether it still stands.]

Everything this harvest writes into a repo — a `plans/*.md` entry, an `AGENTS.md` addition, a
`docs/`/`contributing/` page, a skill's own source — goes through that repo's quality gate
(`inv quality.precommit`, or the repo's equivalent) before committing, same as code. Markdown is not
exempt: dprint reformats prose line-wrapping, and doc-only commits that skipped the gate were the
one recurring CI-failure cause across these repos (confirmed 2026-08-23).

## Self-update mechanics

Resolving friction (steps 6–7) means editing the skill's _source_, not whatever copy is in front of
the current session:

- The running copy — `~/.agents/skills/session-harvest/` (or a project-local
  `.agents/skills/session-harvest/`) — is a plain file copy dropped there at install time.
  Hand-editing it is silently clobbered by the next install and never reaches any other project or
  machine anyway. Never edit it directly.
- The canonical source is the repo these skills were installed from — for this author,
  [`agent-skills`](https://github.com/TheodoreAD/agent-skills); for you, your own checkout or fork.
  `harvest.py` finds it by walking up from its own location and asks with `--checkout <path>` rather
  than guessing when it cannot.
- **Only a session already working in that repo edits it.** From anywhere else the fold-back is a
  filing, per step 6 — `plans.py new <topic> --for github.com-personal/agent-skills`, committed in
  the store. Do not locate the checkout in order to write to it: an edit there is a commit in
  another session's working tree, which is what the global rule forbids outright. The filing is not
  a weaker outcome; `absorb` hands it to the next session that works there.
- When you _are_ in that repo, edit `skills/session-harvest/SKILL.md` (or `scripts/harvest.py`, and
  its tests in `tests/unit/test_harvest.py`): a small, additive change. Rationale for _why_ a
  resolution was made a particular way goes in `references/rationale.md` instead.
- Run that repo's quality gate, then commit — locally, without asking, per step 7. Its own
  `tests/unit/test_skill_layout.py` is part of that gate and enforces real limits (the description
  cap among them), so run it rather than eyeballing the frontmatter. Then tell the user what
  changed.
- **A `scripts/` edit does not reach this session either, and that bites during the run rather than
  after it.** Every `python3 ~/.agents/skills/<name>/scripts/<file>` call keeps executing the
  installed copy until a re-install, so between committing a script change and re-installing, the
  session is reading output from the code it just replaced. Confirmed 2026-08-30: a session renamed
  `absorb`'s pairing output, committed it, then ran `absorb --apply` and got the old wording back —
  harmless there, and it would not have been if the change had altered behaviour rather than a
  string. Either call the checkout's copy for the rest of the run, or note which results predate the
  re-install; do not re-derive the results from the new source and assume they match.
- **Re-installing is not the last step when the edit is meant to take effect _in this session_.**
  The install fixes the file on disk; the copy this session loaded at start is still the old one, so
  a harvest that edits itself and then runs cannot use what it just wrote. Push, re-install, then
  have the harness reload the skill — in Claude Code, `/reload-skills`, after which the skill has to
  be invoked again to pick the new body up. Confirmed 2026-09-01: a session rewrote step 9, pushed,
  re-installed, verified the installed copy matched the checkout, and still held the superseded
  wording; the user supplied the missing move (`/reload-skills`, then "use it"). Say which of the
  three is outstanding rather than reporting "re-installed" as though the loop were closed.
- **Say plainly that a committed edit still reaches nothing.** The installer clones from the remote,
  so the change takes effect only once it is pushed _and_ re-installed
  (`npx skills add TheodoreAD/agent-skills --global --skill session-harvest`) — including for other
  projects on the same machine, whose `~/.agents/skills/` copy is now stale against the source. **If
  the user declines the re-install, that is not a licence to state what the machine is now running**
  — on a machine with parallel sessions the installer may already have been run by one of them, so
  the install state is shared and has to be measured before it is reported. Diff it (that is what
  `skills-state` is for). Confirmed 2026-08-30: a harvest closed with "this one keeps running the
  old copy", the user asked, and the installed copy already carried the fix, re-installed by another
  session twenty minutes earlier — a confident, specific, wrong sentence in the zone of the report
  reserved for what needs action.

## Full rationale

[`references/rationale.md`](references/rationale.md) has the prior-art survey (why this isn't a
`PreCompact` hook, what was borrowed from `learning-loop-skill` and what was deliberately left out,
why plan-specific content is excluded from memory even though it's tempting mid-session) and the
reasoning behind the self-update mechanism.
