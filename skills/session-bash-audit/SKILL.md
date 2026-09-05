---
name: session-bash-audit
description: "Use when asked to audit, measure, or re-check how agent sessions are using the Bash tool — command chaining (&&, ;, |), cd into the session's own repo, head/tail truncation, sed -n/cat/heredoc instead of Read/Edit, git commit/push inside chains or behind git -C — or when deciding whether a permission prompt, an allowlist rule, a ~/AGENTS.md Bash rule, or the permission mode (acceptEdits vs auto) needs changing and wants evidence from real transcripts rather than a hunch. Runs a stdlib script over ~/.claude/projects/*.jsonl, prints per-model and per-session rates plus samples, and carries the dated research that explains why each pattern happens and where the fix belongs. Also the place to record a newly noticed Bash anti-pattern so the next audit measures it."
---

# Session Bash audit

Measures how Claude Code sessions actually use the Bash tool, against whatever Bash rules the
always-loaded instructions file states, and turns the numbers into a decision about _where_ a fix
belongs. The first run (2026-08-24, 3,956 calls over four days) is written up in
[`references/research.md`](references/research.md) — read its "Root causes" and "Mode comparison"
sections before interpreting a new run; most of the reasoning transfers and doesn't need
re-deriving.

Reads `~/.claude/` — the transcript store at `~/.claude/projects/*.jsonl` and, for the permission
replay, `~/.claude/settings.json`. Both are Claude Code's own, read-only and never written, so this
works on any machine running Claude Code and needs nothing installed. On any other harness there is
nothing to read and the script says so rather than reporting zeros. The measured numbers and
baselines shipped here are one author's machine under one set of rules — treat them as a reference
point to compare against, not as your own baseline; save your own on the first run.

**Every pattern here is a POSIX-shell idiom** — `&&`, `;`, `|`, `cd`, `sed -n`, a heredoc — so the
audit describes a session whose Bash tool runs a POSIX shell. On Windows that is a Git Bash or WSL
session, where it applies unchanged; a PowerShell session generates commands none of these patterns
match, and the report then reads as "no problems found" when it means "wrong tool for this
transcript". Until someone runs it against a real PowerShell transcript, read a suspiciously clean
run on Windows as the second, not the first.

**`cd-own-repo` and `git-C-own-repo` decide "own repo" by slugging the command's target the way
Claude Code slugs a project directory**, and until 2026-09-05 they got that wrong on every platform:
they replaced `/` and `.` while the harness replaces _every_ character that is not an ASCII letter
or digit (read from the CLI binary that day, with a 200-character cap and a hash suffix past it). A
repo path holding an underscore therefore never matched and both rows reported zero, which reads as
perfect adherence. The script now uses the harness's own rule, so a Windows path (`\`, `:`) slugs
the same way a Linux one does; a zero on those rows is still only as good as the transcript being a
POSIX-shell one, per the paragraph above.

**The same two rows go quietly wrong for a session run from a git worktree, on any platform, and
that is the harder one because nothing about the transcript looks unusual.** Both tags compare the
command's target against the project slug by **exact equality**, and a worktree session's slug is
the worktree's path, not the repository's. So a `git -C <the main checkout>` call — the single most
likely own-repo shape from a worktree, since the main checkout is where the branch is merged and
where a sibling worktree's tooling still points — slugs to something else and is tagged nothing at
all; the `cd` equivalent is tagged `cd-other`, which is the name for the recommended _cross-repo_
form. The rule goes unmeasured for exactly the sessions most likely to break it, and reports zero.

This is a **declared limitation, not a fix**, because the data cannot support one: the script reads
transcripts offline, long after the directory may be gone, so it cannot ask git which checkout a
slug was. The only signal is the slug's own shape, and it exists for one layout out of several —
Claude Code's `<repo>/.claude/worktrees/<name>` leaves a `--claude-worktrees-` segment (derived from
the harness's slug rule, not observed: none of the 211 project directories on this author's machine
is a worktree), while VS Code's default `<repo>.worktrees/<name>` and the flat `<repo>-<branch>`
beside a checkout are indistinguishable from an ordinary repo name. Half a fix across one layout
would make the other layouts read as verified. Treat a zero on those two rows as unverified whenever
the session may have run from a worktree, the same as for Windows.

## Four procedures — the skill runs them, the user only reads results

Which one applies:

| Ask                                                        | Procedure                          |
| ---------------------------------------------------------- | ---------------------------------- |
| "how are sessions using Bash", a new pattern to measure    | **Measure** (below)                |
| "did the change work", "re-check", a week after a change   | **Compare** against baseline       |
| "does the permission setup behave", after a mode/rule edit | **Probe** the live permissions     |
| "why so many prompts", "what's still prompting"            | **Prompts** — replay the rules     |
| "how is _this_ session doing", from a harvest              | **`--session`** against a baseline |

The first three use `scripts/audit.py`, the fourth `scripts/prompts.py`;
`S=~/.agents/skills/session-bash-audit` below.

**Measure**

```shell
python3 $S/scripts/audit.py --days 4 --samples 5
python3 $S/scripts/audit.py --days 7 --project <repo> --json <scratch-dir>/calls.json
```

Read-only, stdlib only, ~10 s for a week of transcripts. `--samples 0` for just the tables. The
`--json` dump is the input for any ad-hoc follow-up question (`python3 -c` over it is fine here —
the data is a one-off snapshot, not repo code). Put the dump in the job/session scratch dir, not
`/tmp` directly.

**One session, against the baseline** — the only mode whose answer arrives while the session can
still act on it. `session-harvest`'s step 5 calls this; run it directly when a session wants to know
how it is doing rather than how sessions in general are doing:

```shell
python3 $S/scripts/audit.py --session <session-id> --compare ~/.local/state/session-bash-audit/<file>.json
```

The id is the transcript's filename stem, and a unique prefix is enough. Everything else in this
script measures a trend after the fact; this measures the run you are in.

**Compare against a baseline you saved**, not the one shipped here. `$S/references/baselines/` holds
one file measured on the author's machine under that machine's rules; it is a reference point, and
`--compare`-ing a session against it reports how your session differs from somebody else's setup.
Save your own on the first run (`--save-baseline`) and use that — **including from a run whose
numbers are bad**, which is the case people hesitate over. A baseline is never read as a target:
`EXPECTATIONS` is directional (`down` or `zero`), so the verdict is computed against the delta and a
bad first baseline simply sets a bar the next run has to beat. Saving only from runs you are happy
with is what would corrupt the series, by making the reference a selection rather than a
measurement.

[PITFALL: **run it unpiped — every mode, every time.** The output is a few dozen lines and the
harness keeps it whole; `| head -N` on a report whose own subject is `head/tail` truncation is the
one place the habit costs a wrong conclusion rather than a re-run. Confirmed 2026-09-02: a harvest
ran this command as `… --compare … | head -12`, saw the rates line and the first sample blocks, and
concluded `--compare` had produced no comparison at all — no error, no `OK`/`MISS` column, no
`n/m expectations met` line. It then reconstructed the deltas by reading the baseline JSON by hand
and filed a plan naming the script and the baseline as the two candidate causes. Neither was it: the
comparison had printed, forty lines below the cut. The same session measured **45% `head/tail`**,
which is how the finding and its cause arrived in one run.

The comparison now prints **above** the sample blocks in both modes so a truncated run loses the
bulk rather than the verdict — but that is a second line of defence, not permission to pipe.]

[PITFALL: **an agent that just authored a rule is not more likely to follow it**, so this number can
never be replaced by asking the session how it went. Confirmed twice. 2026-08-30: a session that had
spent the day writing the rule against piping a gate through `head`/`tail` produced that shape in
33% of its own calls — worse than the session it had been measuring — and self-reported "went well".
2026-09-01: the session that _implemented this mode_ measured itself at **47% `head/tail`, +17pp
against the pre-rewrite baseline**, plus three other misses, having quoted the rule in its own
commit messages. Two for two, and in both cases the session's own impression was that the run had
gone cleanly.]

[PITFALL: **`heredoc` used to over-count for a commit-heavy session, and stopped on 2026-09-01.**
`git commit -F -` with a heredoc body was the recommended way to write a multi-line message here, so
it tagged on every commit and the column had to be read against the session's commit count.
`~/AGENTS.md` inverted that rule: the message now goes inline in `-m`, written without backticks or
`$`, because `-m` puts it in the approval prompt while `-F <file>` hides it behind a path. So a
`heredoc` hit on a commit-heavy session is a finding again rather than an artefact — and a sample
taken across the change measures adherence to whichever version that session held. **Stamp a sample
with the `~/AGENTS.md` commit it was taken against**, or a rate that looks like drift may be a
session correctly following an earlier rule.]

**Compare** — the "did it work" check, no manual table-reading:

```shell
python3 $S/scripts/audit.py --days 7 --samples 0 --compare $S/references/baselines/2026-08-24-auto-mode.json
```

Prints each model's current rates next to the baseline as percentage-point deltas, with `OK`/`MISS`
per expectation (`EXPECTATIONS` in the script: chaining, head/tail, sed -n, cat, heredoc and
git-in-chain should be _down_; own-repo `cd` and `git -C` mutations at zero). Models with fewer than
50 calls in either run are shown as `?`, not judged. Report the verdict line and the misses to the
user; then route each miss with the table in "Decide where the fix goes". After a rule or mode
change, save a new baseline for the next comparison — `--save-baseline --note "<mode in force>"` —
and keep the old file; the deltas are the point.

**A baseline you save goes to `$XDG_STATE_HOME/session-bash-audit/`** (`~/.local/state/…` by
default, `%LOCALAPPDATA%\session-bash-audit\` on Windows), which is what a bare `--save-baseline`
now writes. Until 2026-09-03 this line named `$S/references/baselines/…` instead — **inside the
installed skill**, which is the artefact a re-install replaces and which this corpus elsewhere calls
drift to edit. The one piece of genuinely per-machine state the skill asks you to keep was being
kept in the one place designed to be overwritten. Pass an explicit path if you want it somewhere
else; anywhere but the install is fine.

**Probe** — live permission behaviour, which no transcript can show:

```shell
python3 $S/scripts/audit.py --probe
```

Prints six commands with the outcome each should have (prompt / no prompt) under `acceptEdits` with
this machine's rules. Run each as its **own Bash tool call** — running them from a script would
bypass the harness's permission check, which is the thing being tested — with `<scratch>` =
`$CLAUDE_JOB_DIR/tmp` if your harness sets one, or any scratch directory outside the repo. The agent
cannot observe prompts: after the run, list which steps were expected to prompt and ask the user
whether that matched what they saw. A mismatch is a real finding (a rule shadowing a mode grant, a
prefix rule not matching) — record it in `references/research.md` "Harness facts" with the date, and
route the fix.

**Prompts** — which calls prompted, and why, when the user reports "too many confirmations":

```shell
python3 $S/scripts/prompts.py --days 2
python3 $S/scripts/prompts.py --since 2026-08-24T19:13:00Z --project <repo>
```

An approved prompt leaves no trace in a transcript, so this replays the harness's matching (split on
the separators, `ask` beats `allow`, built-in read-only set, `acceptEdits`' in-scope grant) against
the _current_ `~/.claude/settings.json` and prints the estimated prompting share per session and the
first prompting reason per call, ranked with samples. Run it before and after a rule change: the
"after" run is the check that the change actually removed the shape, not just a shape. Route each
reason with the table below — most land in whatever generates the permission rules, not in prose.
The 2026-08-25 run that introduced it is in `references/research.md` ("Prompt audit").

Reading the **Measure** output, in order:

1. **per model** — the baseline. Compare against the table in `references/research.md` ("Baseline
   2026-08-24"). Chaining and head/tail rates are the headline; `cd-own-repo`,
   `git-mutating-in-chain`, and `git-C-mutating` should be near zero after the 2026-08-24 changes.
2. **per session** — outliers, not averages. One session at 90% chaining with the same rules as a
   session at 15% is disposition or a task shape, not a wording problem; read a few of its samples
   before touching any rule.
3. **pattern totals** — each row carries its cost ("why"). A pattern with a high count whose cost is
   "prompt friction" only matters in a mode that prompts; check the mode in force during the window
   (`permissions.defaultMode` in `~/.claude/settings.json`, and whether sessions overrode it).
4. **re-runs after truncation** — the direct cost of `| head`/`| tail`: the same command issued
   again with a bigger limit. Each one is a wasted call plus whatever was decided on the truncated
   view in between.
5. **denied** — classifier denials (`Blocked by classifier`) mean auto mode was active for that
   session; "user doesn't want to proceed" is a human decline. Both are worth a look for what shape
   of command drew them.

## Decide where the fix goes

The audit exists to prevent the reflex of "add a sentence to the instructions file". Route by
mechanism. The right-hand column names the _kind_ of place a fix belongs; the parenthetical is where
that is on the author's machine, as one concrete example of each:

| Finding                                                                                            | Fix lives in                                                                                                                                                                             |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A rule's stated _reason_ no longer holds (e.g. "prompt friction" under a mode that doesn't prompt) | The rule's own source, rewritten — not restated louder. Wording alone won't move a rate when the rationale is what's wrong. (An `agents-md` fragment, with the evidence page beside it.) |
| A command shape prompts but is read-only and common                                                | The permission allowlist, as a prefix rule (a generated `tools.toml` entry, `global_option_prefixes` for `git -C`-style shapes)                                                          |
| A verb is honestly `write` but can't lose code, and the instructions make it frequent              | An allow-override on that tool, paired with ask-overrides for its genuinely code-losing flag shapes (`git add` vs `git reset --hard`, 2026-08-25)                                        |
| A read-only task-runner invocation prompts                                                         | An explicit per-task allow rule. A task runner's whole surface can't be blanket-allowed — it runs arbitrary per-repo code — so only named tasks get listed                               |
| A command shape is gated by the permission mode more precisely than a prefix rule                  | The allowlist's own mode-awareness, never a hand edit of the harness's `settings.json`                                                                                                   |
| Writes to a harness scratch dir prompt                                                             | The harness's additional-directories setting, declared where the rest of the harness config is                                                                                           |
| The harness itself instructs the opposite (auto mode's "prefer Bash" reminder)                     | The mode, not the wording. Don't write rules that fight a live system reminder                                                                                                           |
| Only `Plan`/`Explore`-style subagents misbehave                                                    | Their spawn prompt — built-in subagents never load `AGENTS.md`/`CLAUDE.md` at any level, so every rule has to be restated inline                                                         |
| One model's disposition (rates differ by model under identical rules)                              | Nothing to write; note it in `references/research.md` and pick the model for the task                                                                                                    |

Prefer teaching over enforcement: no `PreToolUse` nudge hooks. Agents get the same standard as
developers — they should know what to run, not be silently corrected behind their back. The rejected
hook design is in `references/research.md`.

## Record what you learned

- A new pattern worth measuring → add a `PATTERNS` row in `scripts/audit.py` with an honest "why",
  run once, and add a dated paragraph to `references/research.md` with the count and what it means.
  Rows with no stated cost teach nothing; leave them out.
  - **One row per question, and never one row spanning a compliant and a non-compliant form of the
    same command.** Such a row reports a rate that answers neither question while looking like
    coverage, so the gap is invisible precisely because something is being measured. Confirmed
    2026-09-02: a single `grep/find` row matched `grep`, `rg`, `find` and `fd` alike, so the rule
    preferring `rg` over `grep -r` and `fd` over `find` had never been measured at all — and when it
    was, the two halves came back 90% adherent and 47% adherent, which one number could not have
    said. If a rule distinguishes two spellings of the same command, that is two rows.
  - **Test the regex against hand-written cases before trusting its count**, including a multi-line
    command. Both bugs found on 2026-09-02 flattered the number: `.*` in a lookahead stops at a
    newline, and the separator anchor omitted `\n` even though `split_chain` has always split on it,
    hiding every command that sat on a call's second line.
- A new baseline after a rule/mode change → append a dated row to the baseline table in
  `references/research.md`; don't overwrite the old one — the point is the delta.
- Harness facts (what auto mode does, what a mode auto-approves, rule precedence) → the "Harness
  facts" section of `references/research.md`, with the docs URL and date checked. Those change
  between Claude Code versions; a dated entry is the difference between evidence and folklore.
- A one-off finding that is really a repo bug or a design decision → that repo's `plans/` (see the
  `plan-docs` skill), linked from here.

Every one of those writes goes in this skill's own source, not the installed copy under
`~/.agents/skills/` — that copy is overwritten by the next install and reaches nothing else. The
`skill-authoring` skill has the edit → gate → commit → push → re-install → verify sequence.
