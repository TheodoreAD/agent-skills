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
plans store and the repo's `plans/`, rejected both on the design grounds recorded in `agent-skills`'
`plans/2026-08-29-next-session-prompt.md` (a handoff is ordering and immediacy, and a plan file
would give it a status field and a retirement it should never need), and chose the memory directory
because it is the one destination loaded automatically at session start. It then read the governing
rule — `~/AGENTS.md` saying that directory "is a staging area only, never a durable store — it's
siloed per project directory" — and reasoned: the objection is about durable _knowledge_ being
siloed; this content is deliberately perishable and deliberately per-project; therefore a staging
area is exactly right. It even wrote the tension into its own report before proceeding.

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
