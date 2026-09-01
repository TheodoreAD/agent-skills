---
status: landed
updated: 2026-09-02
---

# In a background job, the session id is not the transcript id — and the harvest audits a stranger

Found by `/session-harvest` running inside a background job, 2026-09-01, at step 5's self-adherence
check. The check ran exactly as written, returned a plausible report, and the report was about a
different session.

## Context

Step 5 says to measure the session's own Bash discipline:

```shell
python3 <session-bash-audit>/scripts/audit.py --session <session-id> --compare <baseline>
```

The step does not say where `<session-id>` comes from, and in a background job the obvious sources
are wrong. What this run reached for was the UUID in the background task's output path
(`/tmp/claude-1000/<slugged-cwd>/<uuid>/tasks/<id>.output`), which is the job's **session id**. That
resolved to a real, current, same-cwd transcript — so nothing failed:

| audited                                   | n   | verdict          |
| ----------------------------------------- | --- | ---------------- |
| `c9a20dab-…` (the session id)             | 386 | 8/11, three MISS |
| `9502c71c-…` (this job's real transcript) | 101 | 8/11, three MISS |

Same headline score, different sessions, and **not one of this job's own commands appears in the
first file** — `npx skills add`, the commit-message files, the `trigger.py run` invocations are all
absent from it, while the calls it does hold (`; echo "exit=$?"`, a `for` loop over two diffs) were
never issued here. The rates disagree on every axis that matters: `chain` 45% against 10%,
`head`/`tail` 24% against 6%, `git-C-own-repo` 0% against 22%. A harvest that reported the first set
would have congratulated this job for discipline it did not have and hidden the one shape it
actually broke.

**The failure is silent by construction, which is what makes it worth a plan.** A wrong session id
that names no file errors out; one that names the wrong file returns a well-formed report. There is
no signal in the output distinguishing them, and the reader of a harvest report is the one person
who cannot check.

## Where the right id actually is

`~/.claude/jobs/<daemonShort>/state.json` names it, and names it twice:

```
sessionId       = c9a20dab-783f-4112-9761-f5d4722e86e8   # the job's identity — NOT the transcript
resumeSessionId = 9502c71c-8787-4663-83be-286a31258b6d   # the transcript this job writes into
linkScanPath    = ~/.claude/projects/<slugged-cwd>/9502c71c-….jsonl
```

`linkScanPath` is the unambiguous one: a path rather than an id, so it needs no reconstruction and
no assumption about the slugging rule. `daemonShort` is the first 8 characters of `sessionId`, which
is also the name of `$CLAUDE_JOB_DIR`, so a job can find its own state file from an environment
variable it already has.

## Open questions

[NEEDS CLARIFICATION: whether the fix belongs in `session-harvest`'s step 5 or in
`session-bash-audit`'s script. Arguments both ways. The skill is where the id is chosen, so a
sentence there ("in a background job read `linkScanPath` from `$CLAUDE_JOB_DIR/../state.json`; the
session id is not the transcript id") fixes the caller. The script is where the mistake is
detectable: it could take `--transcript <path>` alongside `--session`, or resolve a job id itself,
and either would make the right thing the easy thing rather than something to remember. Leaning
toward both — the script gains the option, the skill's step 5 names it — since the skill's own rule
is that a rule missed in practice wants sharper language, and here the language does not exist yet.]

[NEEDS CLARIFICATION: whether `--session` should refuse an id whose transcript contains none of the
calling session's recent commands, or at least print the file it resolved to. Printing the resolved
path costs one line and would have surfaced this immediately; refusing is stronger but needs a
notion of "the calling session" the script does not have. The cheap half is clearly worth it.]

## Also worth recording

The same confusion reaches step 4, which tells the harvest to read the real user turns from
`~/.claude/projects/<slugged-cwd>/<session-id>.jsonl`. That path is wrong in a background job for
exactly the same reason, and the failure there is worse than a wrong number: the harvest would
re-read **another session's brief** and harvest against it, which is precisely the failure step 4
exists to prevent, reached by a third route after the summary-reading one and the
`AskUserQuestion`-answers one.

Related, and since **landed and retired**:
`2026-09-01-harvest-sweep-inflates-the-adherence-number-it-reports.md` was about the same number
being wrong for a different reason — the sweep's own calls counted in it. That shipped on 2026-09-02
as `audit.py --until` plus a boundary recorded by step 0, so step 5 now excludes the sweep. Both
were about step 5's figure not describing what the reader thinks; they stayed separate because the
causes and the fixes did not overlap, and **this one is still open**: excluding the sweep from the
wrong transcript still measures the wrong session.

## Outcome, 2026-09-02

Both open questions went the way the plan leaned, and the mechanism was re-confirmed on a second
background job before anything was written.

- **Script or skill? Both**, as the first tag suspected. `audit.py` resolves a job id to that job's
  `linkScanPath` and says it is doing so; `session-harvest` step 4 already carried the rule for its
  own transcript read, and now says the script closes step 5's half by construction while this step
  still has no script in the loop.
- **Refuse, or print the resolved path? Print — the cheap half, and it is unconditional.** Every
  `--session` run now prints the transcript it settled on, whichever id it was given. Refusing was
  rejected on the plan's own reasoning: it needs a notion of "the calling session" the script does
  not have, and the redirect makes the refusal case moot for the one id that was actually dangerous.

Verified 2026-09-02 on a different job (`c9a20dab`), which reproduced the mechanism exactly:
`sessionId` named a real transcript in the same project directory, `linkScanPath` named the true
one, and the two ids now converge — the job id prints the redirect line and both report the same
215/216 calls, the one-call difference being the measurement's own commands landing between runs.

## Migrated to

- `skills/session-bash-audit/scripts/audit.py` — `_job_transcript`, whose docstring carries the
  386-against-101 evidence and the reason this belongs in the script: a wrong id that names nothing
  errors out, while one that names the wrong file cannot be told from a right one by reading the
  output.
- `skills/session-harvest/SKILL.md`, step 4 — the note that the script now resolves it, and that
  this step's own transcript read is still unassisted.

Not migrated: the "also worth recording" note about step 4, because step 4 had already been fixed by
the time this plan was absorbed — the passage naming this plan is the one now rewritten to describe
the script instead.
