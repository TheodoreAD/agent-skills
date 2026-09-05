# Design rationale: session-harvest

## The problem this solves

Claude Code's built-in auto-memory system already defines a complete taxonomy (`user`/`feedback`/
`project`/`reference`) and a save procedure. What it doesn't do is _proactively_ review a session
for what qualifies, and it has no opinion on cases where memory isn't actually the right home —
specifically, plan-specific work-in-progress (which the `plan-docs` skill already tracks with its
own lifecycle) and repo-specific durable knowledge (which belongs in `AGENTS.md`/`docs/` so it's
version-controlled and visible to every contributor and every agent tool, not just this one
harness's private memory store). Left alone, the natural failure mode is either nothing gets saved
(the user has to ask every time) or memory becomes a second, drifting copy of things `plans/` or
`AGENTS.md` already own.

## Prior art considered

**`dhanesh/agent-skills@context-hygiene-kit`** (found via `skills find`) — a heavy always-on system:
three lifecycle hooks (Stop/PreCompact/SessionStart) wired into `settings.json`, a Python
`ContextLedger` with token-budget eviction, marker-line capture conventions (`DECISION:`/
`CONSTRAINT:`/`QUESTION:`/...), a 27-test install gate. Automatic infrastructure installed once, not
something invoked on demand, and with no awareness of this harness's own memory taxonomy or of
`plan-docs`. Rejected: wrong shape for "something I can call easily," and duplicates work the
harness's memory system + `plan-docs` already do, via its own separate marker/ledger convention.

**`melodykoh/learning-loop-skill`** (found via web search) — the closest match in spirit: an
explicitly-invoked Claude Code skill (`/learning-loop scan` / `/learning-loop wrap up`) built around
the same "review a session, route findings to the right file, don't lose things at compaction"
problem. Its documented history is itself informative: earlier versions relied on description-based
auto-triggering and found it "asymmetrically unreliable," so it switched to explicit invocation —
directly adopted here (`/session-harvest` as the primary entry point, natural language as a
secondary match only). Also adopted its inclusion bar essentially verbatim: _"if this were lost,
would a future session go wrong?"_ — a sharper filter than a vaguer "is this worth noting."

What was **not** adopted from it, deliberately:

- **Sub-agent dispatch with hand-off files** (six separate dispatch prompts, each sub-agent
  inheriting no context, coordinating via files on disk). Built to keep a _very_ long-running
  capture process off the main session's context budget. This skill's scope is one on-demand pass
  over one conversation — not enough volume to justify the coordination overhead.
- **Watch-list clustering of recurring failures across sessions**, with a "maturation" threshold (≥5
  sub-incidents) that auto-drafts an execution plan. Solves a scale problem — patterns repeating
  across _many_ sessions — this user hasn't hit. `plan-docs` already gives a lighter-weight path for
  anything that turns out to need real planning.
- **Adversarial persona review** (two critique personas checking every conclusion before it's shown
  to the user) and a separate **Judgment Ledger** for worldview-level shifts. Both are real,
  validated ideas for a system capturing at much higher volume/noise than this one — but they add
  real weight for a case this harness's existing taxonomy already covers well enough.

If the lightweight version here ever proves too noisy in practice — memory or docs filling with
low-value entries, or routing decisions needing constant escalation — `learning-loop-skill`'s
heavier machinery (quality gates, zoned verification detail, persona review) is the documented next
step, not something to reinvent from scratch.

Other hits from the same research pass — `coleam00/claude-memory-compiler`,
`TranHoaiHung/claude-memory-hub`, a Hindsight gist, `mvara-ai/precompact-hook` — are all
`PreCompact`-hook-based auto-capture systems, same "automatic infrastructure" shape as
`context-hygiene-kit` and rejected for the same reason. There's an open Claude Code feature request
for agent-type `PreCompact` hooks (`anthropics/claude-code#36749`) that would let a hook itself
review the conversation before compaction — worth revisiting if/when that ships, since it would let
this skill's procedure run automatically instead of only on demand, but that's a future option, not
something to build around now.

## Why plan-specific content is excluded from memory

It's tempting mid-session: a plan's context and rationale feel exactly like the kind of thing worth
"remembering." But memory has no retirement mechanism — `plan-docs` plans move through
`idea → planned → in-progress → landed/abandoned/superseded` and get pruned once their durable
content has a permanent home (see `plan-docs`' own "Retiring a plan" procedure). A memory entry
covering the same ground would just be a second, unmaintained copy that goes stale the moment the
plan's status changes, since nothing prompts memory to be updated in lockstep. Keeping a hard line —
plan-shaped content never gets a memory entry, full stop — avoids that drift entirely rather than
trying to keep two systems in sync.

## Why memory is now framed as "temporary-only, expect it to be rare"

Originally this skill treated memory as a normal, if secondary, destination — routing filters carve
off plan/`AGENTS.md`-shaped content, and whatever's left still gets saved as memory via the
harness's own procedure. Confirmed directly by the user 2026-08-23 (same day as the cross-repo
routing filter above) that this framing had already been overtaken by events: an earlier session did
a full restructuring pass and moved everything durable that used to live in memory into
`AGENTS.md`/`~/AGENTS.md` instead, on purpose — not an accident to restore. Memory's own `MEMORY.md`
index was found empty on disk afterward, which read at first like data loss; it wasn't. The
corrected mental model: memory holds nothing durable at all now. Step 2's filters were always meant
to catch everything durable _before_ it reached memory — this just makes explicit that what's left
over should be rare and genuinely temporary (a deadline, a hold-off note), not a quieter version of
the same "personal preference" content the cross-repo filter already redirects to `~/AGENTS.md`.

**Superseded 2026-08-29 — see the next section.** The "rare and temporary" framing left a door open,
and it was walked through.

## Why no memory tier at all (2026-08-29)

The user's ruling, on finding a session had written into Claude Code's per-project memory directory:
**no memories, for any harness, for any project, for any reason.** Project data and user-wide
practices must not be vendor-locked, because the work has to be portable across harnesses. The
carve-out is harness **configuration** — `settings.json`, hooks, keybindings — which is expected to
differ per harness because it describes the tool rather than the work.

What makes this worth a rationale entry is _how_ the previous framing failed, because the failure
mode generalises to any rule this skill writes.

The session had been asked to file a next-session handoff "somewhere durable". It considered the
plans store and the repo's `plans/`, rejected both on the design grounds recorded in the now-retired
`agent-skills` plan `2026-08-29-next-session-prompt.md` (a handoff is ordering and immediacy, and a
plan file would give it a status field and a retirement it should never need — the reasoning is in
the next section), and chose the memory directory because it is the one destination loaded
automatically at session start. It then read the governing rule — `~/AGENTS.md` saying that
directory "is a staging area only, never a durable store — it's siloed per project directory" — and
reasoned: the objection is about durable _knowledge_ being siloed; this content is deliberately
perishable and deliberately per-project; therefore a staging area is exactly right. It even wrote
the tension into its own report before proceeding.

Every step of that is defensible against the rule as written, and the outcome was still wrong. The
defect was that the rule explained a **mechanism** rather than stating a **prohibition** — and a
mechanism can be argued around by anyone who accepts it. The corrections were made in two places:
the ban is now absolute here, and `power-user-linux-setup` carries a filed plan
(`2026-08-29-no-harness-memory-stores.md`) to restate the `~/AGENTS.md` section the same way and
move it out of that file's "Claude Code specifics" block, since sitting there was part of why it
read as a note about one vendor's feature rather than a general rule.

The cheap sorting rule that replaces the reasoning: **configuration describes the harness; anything
describing the work is a plain file any agent can open.**

One practical finding, against the fear that a flat ban loses something: it did not. The handoff was
re-filed as an ordinary plan at `status: in-progress`, which `plans.py list` already sorts above
everything else, and the only thing genuinely lost was automatic loading at session start — which is
worth nothing anyway if only one vendor's sessions get it.

## Why the next-session prompt is printed and never stored (2026-09-01)

Step 9 is short and reads as obvious. It was asked for three times across three days and built twice
wrongly first, and the two failed attempts are why each of its constraints is absolute rather than a
preference.

**The design constraint is staleness, and on this machine it is not hypothetical.** Measured inside
the single hour that produced the second request, every row an assertion a handoff would have
carried:

| assertion, when written                   | how it went stale                                                          |
| ----------------------------------------- | -------------------------------------------------------------------------- |
| "`absorb`: silent, nothing waiting"       | a parallel session filed a plan for this repo minutes later                |
| "the plans store is clean"                | went dirty, then clean, then dirty again — twice                           |
| "6 plans await retirement"                | became 9, partly by this session's own subsequent status fix               |
| the store "has no remote, deliberately"   | a two-tier split landed mid-session; the shareable tier may have one       |
| "nothing is filed for `agent-skills` yet" | trusted from a 10-minute-old check; a duplicate plan was filed as a result |

The last row is the one that matters: a stale assertion did not merely mislead, it **caused
duplicated work**. A prompt asserting yesterday's state to a session that trusts it is that same
failure with a longer fuse.

[PITFALL: **the natural implementation — write the report's last zone into a file — produces exactly
the artefact that fails this way, and it fails silently.** A confidently-worded stale prompt and an
accurate one read identically, which is the same silent-by-construction shape the CI-poll and
stale-fetch bullets are about. That is why "printed, never a file" is stated as a constraint and not
as a default, and why each item pairs the command that re-derives its state with the action if it
still holds — the split made structural rather than hedged in a sentence.]

**Both earlier attempts were built and both were argued down by what they became.** The first
re-filed the handoff as an ordinary plan, and it worked: a session opened on it the next day, ran
each item's check, found every item either done or grown, and the plan retired itself through the
normal procedure — which a "prompt" would have had no way to do. That is the finding, not a failure:
**most of a handoff falls on the `plans/` side of the boundary**, and what is left is the part
`plans/` cannot express. The second attempt was the memory-directory filing the section above
records.

**What finally specified it was the user saying why it kept disappointing** — 2026-09-01: _"I keep
asking for this manually and I don't give all the details."_ Step 9 already existed and said only
what to leave out, so every prompt was improvised from whatever the session happened to remember,
which is precisely how it fills with marginal detail. **The feature was never a store; it was a rule
for what earns a slot** — which is why the design that shipped is a subtraction rule rather than a
format.

Three constraints, each closing one of the questions the two attempts raised:

- **Printed, never written.** The user pastes it into the next session within minutes, which is the
  only reason it may assert anything at all. This dissolves append-versus-replace, the storage
  lifecycle and most of the staleness objection in one move. An append-only file would have been a
  second lifecycle store with no retirement mechanism — the objection this skill already makes to
  parking plan content in memory — and replacing loses the trail.
- **Built by subtraction.** The next session's own opening moves — `absorb`, `list`, `git status`
  plus the ahead-count — already print the incoming plans, the open work and the dirty state, so run
  them and include only the delta. That is the mechanical test for "marginal", and it is stronger
  than the prose definition it replaced: the boundary against `plans/` is **subtraction, not a
  definition**. What survives is three kinds — ordering (nothing on the machine says what to do
  first), perishable state with a short fuse, and a decision not yet in any file, the last being a
  self-check rather than a category, since a non-empty one means the routing step failed.
- **Capped at five.** The cap is what keeps the prompt from becoming a plan with no status field.

The cross-repo line is a **test rather than a ban**: another repo earns a line only when the item is
high-risk or irreversible **and** would change what the next session in this repo does. An unpushed
commit or an open plan elsewhere fails the second half, because that repo's own session is handed
those by `absorb` — which is also why a per-machine prompt was rejected outright: it has nowhere
natural to live and reaches sessions it is irrelevant to.

## Why plan lifecycle decisions defer to `plan-docs` instead of a session-harvest judgment call

The plan-specific routing filter's original wording ("check whether the relevant plan file already
captures it") only covered the case of content with no plan file yet — it said nothing about a plan
file that already exists but has drifted stale (marked `planned` when the work has since landed).
Confirmed as a real gap 2026-08-23: mid-harvest, a plan for a just-landed feature was still marked
`status: planned`, and rather than invoking `plan-docs` to apply its own documented retirement
procedure, an ad hoc `AskUserQuestion` was raised asking whether to retire it — duplicating a
decision tree (`plan-docs`'s "Retiring a plan": default preserve, migrate rationale if not already
covered elsewhere, commit-then-delete) that already existed and already had a considered default.
The user's correction — "why isn't the plan docs skill kicking in?" — was exactly right: session-
harvest's job is to _notice_ the drift and route it, not to reinvent `plan-docs`'s own procedure
inline. Any future friction about _how_ a plan should be retired belongs in `plan-docs`'s own
rationale file, not here — this skill only needs to remember to hand off, not to re-derive the
answer.

## Why a mid-restructure destination routes to the plan, not the file

The routing filters answer "which file owns this?" and silently assume that file is in a steady
state. Confirmed as a gap 2026-08-23: two cross-repo rules routed cleanly to `~/AGENTS.md` by the
filters, but `power-user-linux-setup`'s leanness-pass plan (since landed and retired; its admission
criteria are now permanent in that repo's `contributing/global-agents-md.md`) was mid-flight against
that exact file — cutting it from 30 sections on the finding that oversized instruction files
degrade adherence _wholesale_, and adding admission criteria (state a trigger, don't duplicate,
evidence to a tier-3 rationale doc) precisely to control what gets in. Appending two new sections
would have been correctly routed and wrong anyway: it bypasses criteria written to stop that, adds
to a file being measured as it shrinks, and lands in a tree another session is editing.

The resolution generalizes past `~/AGENTS.md`. Any destination can be under an open plan reshaping
it, and in that window the plan — not the file — is what owns admissions. Recording the candidate as
a `[NEEDS CLARIFICATION: ...]` with its trigger stated (the `plan-docs` tag vocabulary) keeps it in
the same backlog grep as everything else that plan must decide, so it is judged in context rather
than discovered later as an anomaly in the diff.

Worth noting what this does _not_ license: parking a candidate in a plan is not a way to avoid
deciding. It applies only when a plan genuinely owns the destination's shape right now. Absent that,
the ordinary filters stand and the content goes in the file.

## Why the self-update mechanism exists

A convention skill that only ever gets read, never revised by what actually happens when it's used,
drifts out of date the same way any unmaintained doc does — except worse, because nobody re-reads a
skill file the way they'd re-read `AGENTS.md`. Routing genuinely ambiguous cases to the user instead
of guessing is necessary but not sufficient: if the resolution isn't captured, the same ambiguity
resurfaces next session, and the user ends up re-explaining the same judgment call indefinitely.
Folding the resolution back into `SKILL.md` — small, additive edits, not a rewrite — is what makes
this genuinely reusable across sessions and projects rather than a one-shot script. The mandatory
step of finding and editing the _source_ repo (not the installed copy) matters because
`inv ai.install-skills`-installed copies are plain file copies, not symlinks — editing one silently
doesn't propagate anywhere and gets overwritten on the next install run.

## Why the canonical source must be read before drafting (2026-08-24)

The skill already said never to edit the deployed `~/AGENTS.md`, which handles the _write_ side. The
missing half was the _read_ side: a session's context carries whatever `~/AGENTS.md` looked like
when the session started, and that file is regenerated from the `config/agents-md/` fragments by
`inv tools.install`. After the leanness pass restructured the source from 30 flat sections to 6
clusters, a running session still held the old shape — so "extend the existing rule's section", the
admission criterion this skill routes candidates through, would have been applied against section
names that no longer existed. The failure would have been silent: an edit landing in a plausible but
wrong place, or a new heading created for a rule that already had a home. One `grep -n '^## '`
against the source avoids it.

## Why the harvest sweeps live state, not just the conversation (2026-08-28)

The skill was built on one assumption: everything worth catching is _in the conversation_, so
re-reading it is sufficient. A single run falsified that. Its most valuable findings came from
places the transcript could not describe:

- **The process table.** Four backgrounded CI-poll loops were alive 36 hours after the turn that
  spawned them, still issuing requests, having made on the order of 26,000 API calls between them.
  They could never exit — `gh run list --commit` matches only the full 40-char SHA and returns `[]`
  with exit 0 for an abbreviation, so the predicate compared `null` to `"completed"` forever.
  Nothing in the conversation could have revealed this: the transcript records the loops being
  _started_, and a loop that cannot fail produces no output to contradict that. Only `ps` shows it,
  and only if someone looks. The tell that separates hung from working is a `sleep` child a few
  seconds old.
- **Git and CI.** Cheap to check, and the failure mode is a session confidently ending with an
  unpushed commit or an unread red run.
- **Unkept promises.** The run's own last pre-compaction message said "CI is running; I'll report
  when it lands." That was already false when written. A harvest that reads only the conversation
  would have copied the claim forward as fact.

Ordering was changed at the same time and for a related reason. The report had judgment calls first,
on the theory that the user reads top-down and should hit decisions early. In practice a long report
is skimmed, and skimming retains the _end_. Urgency now ascends: settled → persisted → decisions →
risks → needs-action-now. Each risk carries its falsifier, so "this should be fine" stays a claim
that can be checked rather than a reassurance.

The step also shifted from reporting to acting. Finding four runaway processes and merely listing
them would be a worse outcome than killing them, and the same holds for a measurement that exists
nowhere but the transcript: write it into the plan that owns it. What stays reserved for the user is
what is genuinely theirs — anything outward-facing, and anything with a real trade-off.

## Why the sweep's checks name a command rather than the mistake (2026-08-30)

Three of step 5's checks now open on the exact command to type — `git fetch origin` alone in its own
call, `gh run view --json`, and an ahead-count against a resolved branch. Each began as prose
describing the mistake to avoid, and each was rewritten only after a run executed the prose version
and made the mistake anyway, with the wording in front of it.

The failure is the same in all three, which is the argument for the shape rather than for three
unrelated warnings: a pipe reports the _filter's_ exit code. `| tail` turns
`gh run watch --exit-status` — a flag whose entire purpose is converting a red run into a non-zero
exit — into a guaranteed `0`. `| wc -l` turns `git log <bad ref>..HEAD`, which exits 128 with
`fatal: ambiguous argument`, into a calm `0` that reads exactly like a clean tree. Each time, the
check meant to catch a silent failure fails silently itself, and the number it prints is
indistinguishable from the true one.

The branch case adds a second layer worth stating separately, because it is a substitution rather
than a syntax error: the bullet is written `origin/<branch>`, and every run has to put something
there. Measured 2026-08-30 across every clone under this machine's projects root — 71 repos, 22 on
`main`, 23 on `master`, the remaining 26 on a feature branch — so `main` is the wrong guess more
often than the right one. That is why the rule is unconditional rather than a caveat about the one
store where it was caught.

The counter-argument, considered and rejected: three "type this exact command" bullets make the step
read as a script rather than as guidance. It loses because the two earlier ones were themselves
rewritten into that shape after prose failed repeatedly, and the third arrived carrying the same
evidence — a session that had the prose in front of it and piped anyway.

One correction belongs here, because the plan that filed the finding stated the cause wrongly: it
recorded `git log` as treating an unknown revision on the left of `..` as empty when the output is
being counted. It does not. Unpiped, the command is loud and exits 128; only the pipe makes it
quiet. A mechanism inferred from an observed symptom is not a measured one, and this wrong mechanism
would have aimed the fix at git's ref resolution rather than at the pipeline — which is the part
that also breaks the two neighbouring checks.

## Why the mechanical half is a script and the judgement half is not (2026-09-02)

The section above is the argument's last prose-only iteration: name the exact command, because prose
describing the mistake was executed wrongly with the wording in front of it. `harvest.py` is what
happens when that argument is followed to its end — **a correction a script can simply not make does
not belong in prose at all.**

The evidence is a census of what every run had been re-deriving. Measured 2026-09-02 across this
machine's whole transcript store, **24,429 Bash calls in 1,134 transcripts**:

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

**The transcript reader was the worst of them** — 164 heredocs across 46 sessions, no two alike, for
a job that has to filter user entries, extract text blocks, find `AskUserQuestion` results in
tool-result blocks and resolve a background job's real transcript. Each of those had already failed
in a documented way and each failure had been fixed **in prose**, so the next run's heredoc
reintroduced it. Six such corrections existed, every one of them recurring at least once after its
warning was written. That is the signal that the fix is not wording.

The second cost was the user's own framing, 2026-09-02: _"the harvest skill uses `date` directly,
and that creates a security prompt"_. `date -Is` is step 0's first instruction and matches no
allowlist rule, so the first thing every harvest did was interrupt the user. One
`python3 <skill>/scripts/harvest.py …` prefix is one shape to approve instead of a dozen — though no
allowlist rule is assumed here, deliberately: that belongs to the machine's own repo, and the
script's value does not depend on it.

**What deliberately stayed in prose is most of the file**: the significance test, the routing
filters, "there is no memory tier", the report's four groups and their ordering, the next-session
prompt's subtraction rule. Two things stayed out of the script for their own reasons — **the gate
re-run**, because that is the repo's command and hard-coding `inv quality.precommit` would be wrong
in every repo that does not use it; and **anything that writes**, because a script that both
measures and writes is one an agent will run without reading.

[PITFALL: **the line-count target was the thing that was wrong, and is reported as missed rather
than met by deleting evidence.** The plan aimed at under 700 lines and the skill went 967 -> 848.
Every command spelling is gone — step 5 fell 270 -> 218 and step 0 127 -> 109, while step 2's 129
lines of routing filters never had a command in them to remove. Cutting the remaining 150 would mean
deleting the dated confirmations that make the rules survive review, which the same plan's own scope
note forbids. A size target set before the split is a target set in ignorance of which half is
which.]

Three things the build found that reasoning had not, all from running it against this machine:

- **The `AskUserQuestion` filter needed no third string-matching fix at all.**
  `tool_result.tool_use_id` links back to a `tool_use` block whose `name` is the tool, which asks
  the transcript what the tool _was_ rather than what its output looks like — immune to every
  failure that rule has had. Measured: 7 answers by id against 8 by anchored preamble, the extra
  being a grep's own output. The preamble count is still printed beside it as a self-check.
- **Comparing `scripts/` directories raw reported three skills as differing at once**, because the
  checkout accumulates a `__pycache__` the moment a script is imported and the installed copy does
  not — a false "the install is behind" on the exact comparison step 0 exists to get right.
- **A listening process's `/proc/<pid>/cwd` is not what it serves.** Reading it that way turned a
  browser started from a repository into a finding about that repository, so the served directory is
  now inferred only for something that looks like a file server or names `--directory` outright.

## Why step 0's own instruments kept reporting clean (2026-09-04/05)

Four defects in step 0 were found and fixed inside two days, and they are worth one section rather
than four notes because they are one failure wearing four faces: **the check that exists to catch a
silent problem was itself silent, and in three of the four the right answer was already in hand.**
The fixes are in `harvest.py`, each with its incident in a comment beside the code; what belongs
here is the shape, because it is what should be suspected first the next time an instrument reads
clean.

- **`skills-state` said "installed copy matches the checkout" while the installed script was an hour
  stale.** The verdict branched on `SKILL.md` identity alone, with `subdirs_differing` naming
  `scripts` in the same payload — computed one line above the branch and never read. Found by
  running the check immediately after fixing two bugs in that same script.
- **`--skill <name>` replaced the default set instead of extending it**, so naming any skill dropped
  `session-harvest` — the one skill step 0 exists to check. A harvest passed two names, got two
  clean rows, and only a second call naming `session-harvest` found its `SKILL.md` had moved after
  session start with two unpushed commits.
- **`transcript --expect` could not match a command containing double quotes**, because the
  transcript stores it as a JSON string and the search was a raw substring. The more specific string
  — the one a person is likelier to paste — is the one that failed.
- **The command block could not be run as written.** `transcript --expect` printed the right session
  and `turns` on the next line exited 1, because each line is a separate process. Three harvests hit
  it identically before it was fixed.

Two things generalise.

**The first two are the dangerous half, and they are the ones with the answer already computed.** A
check that fails loudly gets fixed by whoever hits it; a check that reports clean while wrong is
trusted, and it is trusted specifically at the moment step 0 exists for — a session about to execute
a stale copy of the very script it is fixing. So when an instrument's verdict is narrower than its
wording, the payload beside it is where to look first: in both cases the contradicting field was
already there, in the same output, on the same run.

**The asymmetry between the two mistakes is what settles each fix, and it points the same way every
time.** `--skill` extending the defaults costs three extra rows on a run that names a skill;
`--skill` replacing them costs the check itself. The verdict counting `scripts/` costs a re-install
nobody needed; not counting it costs a run that executes code it never looked at. Neither fix needs
a judgement about likelihood — only about which error is recoverable, which is why none of them
needed a second opinion.

`references/` is the one place the rule deliberately stops: it is read on demand and inert, so a
difference there changes no run, and letting it into the verdict would re-create a defect fixed on
2026-08-30 where a references-only commit fired the most expensive branch in the procedure.
Reporting it in its own wording, outside the verdict, is what keeps both properties.

**And the command block's fix was a third option neither of its two candidates had seen.** The
choices on the table were re-wording the block so each line carries `--session`, or a state file
carrying the resolution between invocations. Claude Code exports `CLAUDE_CODE_SESSION_ID` into every
Bash call and it is the transcript's own filename stem, so the bare lines resolve with nothing typed
and no cross-invocation state at all — the environment is per-call and per-session by construction.
It beat the wording fix because the re-type was never necessary, and it beat the state file because
a state file is a second thing that can be stale. `--session` stays for a harness that exports no
id, and the job check stays ahead of it, because a background job's environment names the parent
session while only its `state.json` knows the job's own transcript.

## Why "the invocation asked for something the skill lacks" is a self-update trigger (2026-08-28)

The original two triggers both assumed the skill did something and it went wrong — an ambiguous
routing, or a correction. They missed the case where the skill is simply _missing a capability_ and
the user supplies it inline: "make sure you also check the running shells / git state / next steps,
not sure if the skill does that today."

That phrasing is a specification, and it is uniquely easy to drop, because following it makes the
current run go _well_. Success is exactly what suppresses the instinct to write anything down. Every
live-state check in step 5 arrived this way, produced the run's best findings, and was still nearly
lost — the fold-back happened only because the user afterwards asked whether the skill had been
updated. By then the signal had already been missed once.

Hence the ordering requirement: fold back _before_ the final report, and name the destination in it.
A skill whose entire subject is "what would be lost when this session ends" has no business losing
its own lesson.

## Why improvement is a standing step, not only a friction response (2026-08-28)

Reacting to friction is not enough while a skill is young and actively dogfooded. Friction triggers
fire only when something visibly goes _wrong_; they are silent on the more common case where the run
succeeds and the procedure is nonetheless mis-aimed — a step that produced nothing, a step skipped
as inapplicable that was merely written too narrowly, or a finding that arrived from outside any
step at all. That last one is the trap: the finding still got made, so nothing feels missed, and the
fact that no step would have produced it goes unrecorded.

The author's instruction was explicit — "it's essential we keep catching the issues and fixing them
right away as I dogfood the skill" — so the check is now unconditional and the default is to edit
the source immediately. A deferred skill fix is a skill fix that does not happen: the context that
justified it is exactly what the next compaction removes. The explicit "no skill changes needed this
run" line exists so the check leaves evidence either way; without it, silence is ambiguous between
"checked, nothing found" and "never checked".

Steps 6 and 7 sit ahead of the report for the same reason, resolving an ordering contradiction the
previous revision introduced: the friction step said "do the fold-back before the final report"
while being numbered after it.

## Why the skill commits its own edits but never pushes them (2026-08-28)

The earlier wording — "tell the user it's worth a commit, don't commit it unasked" — was written to
be cautious and had the opposite effect: it inserted an approval pause exactly where the fix is most
likely to be abandoned, mid-run, with the report still unwritten. Committing locally is reversible
(`git reset --soft HEAD~1`), reviewable as a diff, and reaches nobody, so the caution bought nothing
real.

Pushing and re-installing is where the line belongs, because that is the step that changes what
other sessions and machines load. The installer clones from the remote, so a committed-but-unpushed
edit takes effect nowhere — not even in another project on the same machine, whose
`~/.agents/skills/` copy silently goes stale against the source.

Worth recording alongside: on this machine `Bash(git commit:*)` and `Bash(git push:*)` are both
allowlisted (`~/.claude/settings.json`), so neither ever prompts, in any permission mode. When an
unasked commit happened during this session the natural hypothesis was that a complex command line
(a `cd … && git commit -F - <<'MSG'` heredoc) had slipped past the classifier; checking showed
otherwise — the chain splits per subcommand and `git commit -F -` matches the allow rule cleanly.
There was no guard to evade. That is deliberate, per `~/AGENTS.md`'s "Proposing an enforcement
mechanism for agent behavior", and it means the absence of a prompt carries no information about
whether an action was wanted.
