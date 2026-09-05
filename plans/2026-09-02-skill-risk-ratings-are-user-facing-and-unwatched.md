---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/power-user-linux-setup
source_session: cd4f9f9e-379a-4bb2-986c-1a99e0f84ac0.jsonl
source_moment: 2026-09-02T20:05:00+03:00
---

# Every published skill carries a public risk rating, and nothing here watches them

## Context

Every skill in this repo is indexed on **skills.sh** and scanned by **three independent scanners**,
and the results are shown to a prospective user **at install time, before they confirm**. The
`skills` CLI renders them in its installation summary — `riskLabel()` prints `Critical Risk` in bold
red, `Med Risk` in yellow, and so on, next to each skill name.

Nothing in this repo knows any of that. The ratings are computed upstream, change when a scanner
re-runs, and are the first thing anyone considering these skills learns about them.

The user's framing, which is what makes this worth a plan rather than a note: _"i want a plan that
checks all my skills for how they are rated, otherwise users will stay away from them."_

## Evidence

Found incidentally on 2026-09-02, from a `power-user-linux-setup` session surveying the `skills` CLI
for a different reason (an agent-support matrix). Reading that CLI's bundle turned up an
undocumented endpoint it calls during `skills add`, which answers for any source repo:

```shell
curl -s 'https://add-skill.vercel.sh/audit?source=TheodoreAD/agent-skills&skills=<comma,separated,names>'
```

All 14 skills came back known and scanned — so ingestion is from the public GitHub repo, with
nothing published or registered from any machine. Verdicts as of that date:

| skill                      | ath    | socket                 | snyk   |
| -------------------------- | ------ | ---------------------- | ------ |
| **session-harvest**        | medium | **critical** (1 alert) | low    |
| **session-bash-audit**     | medium | safe                   | low    |
| research-library           | safe   | safe                   | medium |
| skill-fitness              | safe   | safe                   | medium |
| db-defaults                | safe   | safe                   | low    |
| invoke-task-conventions    | safe   | safe                   | low    |
| mcp-python-conventions     | safe   | safe                   | low    |
| mcp-server-shipping        | safe   | safe                   | low    |
| plan-docs                  | safe   | safe                   | low    |
| polite-mcp-conventions     | safe   | safe                   | low    |
| python-conventions         | safe   | safe                   | low    |
| python-refactor-audit      | safe   | safe                   | low    |
| python-testing-conventions | safe   | safe                   | low    |
| skill-authoring            | safe   | safe                   | low    |

**4 of 14 carry a non-safe verdict from at least one scanner**, and one of those is `critical`.

`analyzedAt` timestamps cluster at 2026-08-31T17:52–17:54Z for most skills and
2026-09-01T22:54–22:56Z for `plan-docs`, `session-harvest` and `skill-authoring` — the three edited
most recently. So **scans follow pushes**, which means a rating is not a one-time verdict: any skill
can acquire one at any time, silently, after a routine edit.

[PITFALL: **the flagged pair is not a random two.** `session-harvest` and `session-bash-audit` are
precisely the skills that read `~/.claude/projects/*.jsonl` transcripts, sweep running processes and
walk git state across several repos. That is exactly the behaviour a supply-chain scanner exists to
flag, and it is also exactly what those skills are _for_. So the likely finding is not a bug to fix
but a genuine capability being correctly described — which is the harder case, because the remedy is
not "fix the code".]

## Who the scanners are, and what they look for

Researched 2026-09-02, same session, after the table above.

**skills.sh is Vercel's official skill directory**, and it runs **three independent audits**, shown
publicly at `www.skills.sh/audits`:

| key in the API | who                     | shown in the CLI as |
| -------------- | ----------------------- | ------------------- |
| `ath`          | **Gen Agent Trust Hub** | `Gen`               |
| `socket`       | **Socket** (socket.dev) | alert count         |
| `snyk`         | **Snyk**                | risk level          |

**Scanning is automatic and repeated.** Installing a skill through the CLI triggers Vercel
infrastructure to call the scanners; nothing is submitted by the author. Snyk states plainly that it
is not a one-time check — skills are re-evaluated as detectors improve and new threat patterns
appear. That matches the `analyzedAt` spread already recorded above, and it is the argument for a
recurring check rather than a one-off look.

**What they detect**, in their own words and from a comparable directory's published methodology:
prompt injection, malicious code patterns, suspicious downloads, exposed secrets, and "toxic flows"
where a benign prompt triggers a malicious action — via LLM judges plus deterministic rules. The
category list a comparable scanner publishes is: execution, network, filesystem, obfuscation,
credentials, persistence, prompt injection, data exfiltration, hidden helpers, supply chain.

**Ecosystem context that sets the bar.** Across the directory, **13.4% of skills carry at least one
critical-level finding**, and Snyk reports its CRITICAL detectors at 90–100% recall with a **0%
false-positive rate against the top 100 legitimate skills**. So a critical is not a label handed out
freely, and "it is obviously a false positive" is not a safe assumption to start from.

## What the two flagged skills actually do

Read from the source rather than assumed, because the whole question is whether the rating is
describing something real.

|                      | `session-harvest`                                                                           | `session-bash-audit` |
| -------------------- | ------------------------------------------------------------------------------------------- | -------------------- |
| reads                | transcripts, `/proc`, listening sockets, git state, **existence** of credential-named files | transcripts only     |
| executes             | `subprocess`, behind one `Runner` seam (git, process/socket listing)                        | **nothing**          |
| network client       | **none** — no `urllib`, `requests`, `httpx`, `socket`                                       | **none**             |
| egress               | `git fetch` to the repo's own upstream, opt-out via `--no-fetch`                            | none                 |
| `eval`/`exec`/base64 | none                                                                                        | none                 |

**The likely trigger is one constant and the code around it:**

```python
SECRET_NAMES = (".env", ".env.local", ".envrc", "secrets.json", ".netrc", "credentials")
...
readable = [n for n in SECRET_NAMES if (directory / n).exists()]
```

Its purpose is defensive: it warns that a forgotten dev server is serving a repository root whose
`.env` is reachable from the LAN — a real finding that skill has made. Its _shape_ is a credential
filename enumeration reported per directory, which is exactly the "credentials / env harvesting"
category. **It never opens those files** — `.exists()` only, and the names are reported, never the
contents.

[PITFALL: **this is dual-use, not a mistake, and that is the uncomfortable part.** A tool that reads
your agent transcripts, enumerates processes and listening sockets, and checks which directories
hold credential files is behaviourally indistinguishable from reconnaissance — the difference is
that it prints a report to your terminal instead of sending it anywhere. A static scanner can see
the first half and not the second. So the honest question is not "how do we get the label removed"
but "is a reader who sees the label given enough to judge us correctly".]

The strongest fact available for that judgement, and it is checkable by anyone in one grep:
**neither skill contains a network client of any kind.** Everything they gather goes to stdout.

## The alert, retrieved (2026-09-03) — and the `critical` is not Socket's word

**There is a per-scanner audit page**, found in a community dispute rather than in any
documentation: `https://www.skills.sh/{owner}/{repo}/{skill}/security/{socket|snyk}` (`ath`/`gen`
404 — Gen's results are not exposed this way). It is server-rendered, so `curl -L` reads it; note
the `www.` host, since bare `skills.sh` 308-redirects and several fetchers stall on that.

Socket's page for `session-harvest`, from the **same scan** the API reports (both stamped 2026-09-01
22:56):

- **one alert**, category **Anomaly**, on `SKILL.md`, labelled **LOW**
- **confidence 85%**, **severity 62%**
- verbatim: _"SUSPICIOUS: the skill's purpose broadly matches its capabilities, but its footprint is
  unusually wide for a harvesting helper: transcript mining, multi-repo inspection, writes to
  always-loaded instruction files, cross-repo plan filing, and some autonomous local commits. The
  main concern is medium supply-chain trust from installing mutable skill content from a personal
  GitHub repo plus medium operational risk from broad read/write authority, **not confirmed malware
  or explicit credential theft**."_

[PITFALL: **the headline severity contradicts the scanner's own.** The audit API returns
`socket: {risk: "critical", alerts: 1, score: 90}` for precisely this scan, while Socket's page for
it says one **LOW** alert at 62% severity. Same skill, same timestamp, two severities — and it is
the API's word that the CLI renders as bold red `Critical Risk` at the install prompt. The likely
mechanism is a mapping from **alert count** rather than alert severity: `session-bash-audit` has 0
alerts and reports `safe`, `session-harvest` has 1 and reports `critical`, and `score` is 90 for
both and for every clean skill checked, so the score is not the discriminator. Not confirmed — no
skill with a non-zero alert count and a non-critical headline was found to test it against, and the
public audits listing's visible rows are all 0-alert.]

**This changes what the problem is.** The `SECRET_NAMES` hypothesis was wrong: Socket says
explicitly it found no credential theft, and the flagged file is `SKILL.md`, not `harvest.py`. The
objection is to the **stated shape of the skill**, in three parts, and each has a different remedy:

| Socket's concern                                                   | what it is                                                          | remedy                |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- | --------------------- |
| footprint wide "for a harvesting helper"                           | a gap between the **stated purpose** and the described capabilities | description, not code |
| "installing **mutable** skill content from a personal GitHub repo" | distribution: the content can change under an installer             | pinning / releases    |
| "broad read/write authority"                                       | genuine, and the skill's actual job                                 | document it           |

The first is the most actionable and the cheapest: the alert is on `SKILL.md`, and the judgement is
that the purpose it states is narrower than the capabilities it then describes. A description that
says up front that this skill reads session transcripts, inspects several repositories, writes to
always-loaded instruction files and commits locally would close that gap by widening the _stated_
purpose to match — the opposite of the instinct to make the description sound safer.

## The user's position, 2026-09-03

Stated once the Socket narrative was in front of them, and it settles the two levers this plan had
been weighing:

[DECISION: **total transparency, without qualification** — _"we want to be one hundred percent
transparent with our skills, no doubt about that."_ So the description-widening is not a tactic for
managing a rating, it is the position: a skill says what it reads, what it runs and what it writes,
and the fact that this also closes Socket's stated-purpose gap is a consequence rather than the
motive. It also settles the earlier worry about how a security section should be worded — there is
no line to walk, because nothing is being minimised.]

[DECISION: **reduce capability where the skill does not need it, keep it where it does** — _"we also
can look into doing less intrusive things if it helps, unless the skill needs them."_ That is a
genuine test rather than a preference, and it has an answer per component. Of the three things
Socket named: writing to always-loaded instruction files and autonomous local commits **are not
needed** and are removed by the write-scope rule, which landed and has since been retired into
`session-harvest`'s `SKILL.md` and its rationale; transcript mining and multi-repo inspection
**are** the skill, and stay. The `SECRET_NAMES` existence check also stays: it produced a real
finding, it never opens the files, and Socket explicitly did not object to it.]

The two decisions pull in the same direction and it is worth saying why, because "be transparent"
and "be less intrusive" can conflict. They do not here: the footprint that survives the second
decision is exactly the footprint the first one asks the description to declare. Widening the stated
purpose is only uncomfortable while the skill is doing things it does not need to do.

## Community lore, and what a successful dispute looks like

- **The venue is GitHub issues on `vercel-labs/skills`.** 20 issues match "false positive": **10
  closed, 10 open.** Related and instructive: #385 "Misleading HIGH-RISK FAIL label on legitimate
  skill", #384 "Opaque moderation, silent install suppression, and lack of due process", #322
  "Silent removal of skills and install counts", #919 "skills.sh is serving stale SKILL.md content
  and Gen audit results are not refreshed".
- **Expect slow and silent.** #1810 (a Snyk E005 false positive on a detector skill whose regex
  markers were mistaken for download URLs) has been **open since 2026-07-29 with zero comments**.
  `snyk/agent-scan` #271 was closed after **2.5 months, also with zero comments**.
- **The template that worked** is #2008, closed 2026-08-24, and it is worth copying exactly:
  disputes **one** finding; explicitly **concedes** the other (_"not a request to remove or
  downgrade W011 — that finding accurately identifies a real, deliberately mitigated exposure"_);
  links the per-scanner audit URL; cites the offending string's source by permalink; and explains
  the semantic gap — a string in a test fixture read as runtime behaviour.
- **The base rate is the strongest argument available.** Across skills.sh, the scanners agree on
  **0.12%** of skills (33 of 27,111), and of 8,402 skills flagged by at least one scanner, **72%
  were flagged by exactly one**. A single-scanner flag is the ecosystem's normal condition, not a
  signal — which is context worth having before spending a session chasing one.

[DECISION: **conceding the true part is what makes the disputable part credible**, and both worked
examples do it. Socket is right that the authority is broad; it is wrong that the purpose is
narrower than the footprint, because the purpose is exactly that footprint. So the dispute is: the
description understated the skill, the description has been widened, and the `Anomaly` at LOW/62% is
a fair reading of the old text — while the **`critical` headline is a separate defect**, since
Socket's own page says LOW.]

## Why the alert text could not be retrieved

Three routes, all closed, so nobody repeats them:

- **The audit API returns counts only** —
  `{"socket": {"risk": "critical", "alerts": 1, "score": 90}}` and no alert name, type or
  description.
- **The public page does not carry it.** `www.skills.sh/TheodoreAD/agent-skills/session-harvest`
  returns 200 to `curl -L` (146 KB, the rendered SKILL.md); the audit block is fetched client-side
  from the same counts-only endpoint, so the detail is in neither the HTML nor any embedded JSON.
  Note the host: bare `skills.sh` 308-redirects to `www.`, and several tools time out on the
  redirect rather than following it.
- **The CLI never shows more than the count either** — `socketLabel()` renders `N alerts`, nothing
  else. So an installing user sees `Critical Risk` and `1 alert` with no way to learn what it is.

That last point is worth stating on its own: **the label is maximally alarming and minimally
informative at the moment of decision.** Whatever is done here, the reader's experience is a red
`Critical Risk` next to a skill and no route to the reason.

`snyk/agent-scan` (Apache-2.0, Python, `uvx snyk-agent-scan@latest <path>`) is the one scanner that
can be run locally, and it needs a `SNYK_TOKEN` — not present on this machine. It would not
reproduce this finding anyway, since Snyk rates both skills `low`; its value would be as a
same-class tool that names what a scanner sees.

## Still unknown

- **The one Socket alert.** All three public routes are closed (above). What remains: Socket's own
  platform, which needs an account, or asking skills.sh / Socket directly as the skill's author.
- **Install counts.** `skills find` sorts on an `installs` field from `/api/search`, which hangs.

## Open questions

[NEEDS CLARIFICATION: **is the `SECRET_NAMES` check worth what it now costs?** It is the clearest
candidate for whatever Socket saw, and it is genuinely useful — it caught a dev server exposing a
repository root to the LAN. Three ways to keep the value at lower cost: derive the names from
`.gitignore` rather than a literal credential list; report only "this directory is a repo root,
check it yourself" and drop the filenames entirely; or keep it and document it. The first two lose
real precision in the report, and none of them is worth doing before the alert is known — it may not
be this at all.]

[NEEDS CLARIFICATION: **which scanner gates, given they disagree?** `session-harvest` is
`ath=medium`, `socket=critical`, `snyk=low` — three verdicts, three answers. Alerting on "any
scanner non-safe" fires on 4 of 14 today and will be ignored within a week; gating only on
`socket=critical` catches this instance and misses `session-bash-audit`. The policy is the design
decision; fetching is the easy half.]

[NEEDS CLARIFICATION: **where does the check live, and is it a gate or a report?** An `inv` task run
on demand, a step in the quality gate, or a scheduled job. Against the gate: a rating changes when
an upstream scanner re-runs, so a commit could fail for something the commit did not cause, which is
the worst kind of red. A report plus a periodic run may be the honest shape.]

[NEEDS CLARIFICATION: **is it safe to build on `add-skill.vercel.sh/audit`?** Undocumented,
unversioned, found by reading a minified bundle. Not a reason to avoid it, but a reason to treat a
failed fetch as **unknown** — never pass, never fail — and to derive the skill names from the repo
rather than hard-code them.]

## Can the scans be run here? One of three (measured 2026-09-03)

Asked directly, and the answer shapes the design: **the two scanners that flag this repo are the two
that cannot be reproduced locally.**

| scanner     | runnable here | how, and what it costs                                                                                                                                                                                                       |
| ----------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Snyk**    | **yes**       | `uvx snyk-agent-scan@latest <path>` — Apache-2.0, Python, `--ci` exits non-zero on findings, `--json`, `--ignore-risks`. Needs a free `SNYK_TOKEN`.                                                                          |
| **Gen ATH** | no            | Its free public Skill Scanner takes **ClawHub** URLs only — probed, and it answers `Skill not found on ClawHub` for a skill of ours. The rating we carry comes from its skills.sh pipeline, which has no public entry point. |
| **Socket**  | no            | The Socket CLI scans package manifests (npm, PyPI, cargo). No skill or `SKILL.md` support documented; skill scanning is their internal pipeline feeding skills.sh.                                                           |

`snyk-agent-scan --help` runs clean via `uvx` on this machine, so the tooling is real and reachable.
Three things to know before adopting it:

- **It uploads.** Its own words: it "sends the component information needed for analysis, including
  … tool names and descriptions, and skill content", with secrets redacted before transmission. For
  a public skills repo that is disclosure of already-public content; pointed at `~/.agents/skills`
  it would send whatever else is installed there, so **scope it to this repo's `skills/` directory**
  and never run the bare whole-machine form.
- **Scanning an MCP config executes it.** Not a risk when the target is a skills directory, but it
  is why the bare form is the wrong default.
- **Its output is explicitly unstable** — "we do not recommend building production workflows that
  depend on specific CLI output fields or risk names" — and it says large-scale use of the standard
  API is abuse. So: a diagnostic to run deliberately, not a per-commit gate.

**Snyk publishes its skill risk taxonomy**, which is the closest thing to a readable rubric anyone
in this ecosystem offers, and it is worth designing against directly. Skill risks:
`prompt_injection_skill_instructions`, `suspicious_download_url`, `malicious_code`,
`insecure_credential_handling`, `secret_detection`, `direct_money_access`,
`third_party_content_exposure`, `unverifiable_dependencies`, `modifying_system_services`,
`missing_skill_md`. Scores are 100 Low / 300 Medium / 600 High / 1000 Critical.

Two of those names — `insecure_credential_handling` and `secret_detection` — are exactly where the
`SECRET_NAMES` block would land if anything catches it. Snyk rates both flagged skills `low`, so
either it does not fire there or it fires below threshold; running it locally would say which, and
that is the single most informative thing available short of the Socket alert itself.

### Packaging the scripts would not reach Socket, and is not how skills.sh does it

Asked directly 2026-09-03: if the skills' Python scripts were packaged locally, could `socket` scan
them? **No, for two independent reasons, either of which is sufficient.**

- **Socket's scan ingests manifests, not source.** `socket scan create` "search[es] your target
  directory for all manifest files" and uploads "metadata about which packages your project depends
  on" — no source code. The archive variant is the same rule one layer in: uploads are extracted
  server-side and "any supported **manifest files** … are ingested". First-party code is never the
  subject.
- **These scripts have no dependencies to declare.** Every import across every skill's `scripts/` is
  standard library — `ast`, `tempfile`, `hashlib`, `itertools`, `select`, `uuid`, `functools`. A
  generated manifest would carry an empty dependency list, so even the manifest path would hand
  Socket nothing to analyse. The property that makes these scripts easy to trust is the same one
  that makes them invisible to this pipeline.

**The one Socket surface that does read source is a different product.** "Socket Basics" is a CI/CD
suite that "runs on your source code" — SAST, secret scanning, container scanning. It would say
something about the Python, but it is not the engine behind the skills.sh verdict, so it cannot
reproduce or explain the `critical`.

**And packaging is not how the directory does it.** Two checks, both negative:

- **`skill` appears nowhere in Socket's documentation** — zero hits, case-insensitive, across their
  93 KB `llms.txt` index covering every product and API endpoint.
- **The Socket CLI has no skill support**: searching `SocketDev/socket-cli` for `skill` returns only
  that repo's own `.claude/skills/` directory and its commit hooks.

Socket's own account is that they scan skills.sh's 60k+ skills "with the same analysis engine that
protects millions of developers across npm, PyPI, and beyond" — the **engine** is reused, the
**ingestion** is a partner pipeline. Snyk describes their half the same way: installing through the
CLI triggers Vercel infrastructure to call the scanners. Neither side is packaging anything, and
neither exposes a public entry point for a skill.

[DECISION: **stop looking for a way to run Socket locally.** Three independent routes are now closed
— no CLI support, no documented API surface, and no packaging trick, the last of which fails twice
over. The Socket verdict is reachable only as a published number through the audit endpoint, which
the monitor already reads. Anything further has to come from Socket as the skill's author, not from
a local scan.]

**Cost and access, checked 2026-09-03 so nobody re-derives it.** Snyk's Free plan is $0/month. Its
published free-tier limits are per product — 200 Open Source, 100 Code, 300 IaC, 100 Container tests
a month — and **Agent Scan appears in none of them**, so its quota on free is undocumented rather
than known to be generous. Fourteen skills scanned occasionally is not near any plausible line; a
per-push CI job is, given their own "large-scale scanning is considered abuse" warning. That is the
second independent reason the recurring monitor should be the audit endpoint rather than the
scanner. Paid tiers, for context only: Team $25/dev/month, Ignite $1,260/dev/year, Enterprise
custom, with the Evo platform as the enterprise path.

**Two ways in, and the cheaper one needs no account at all:**

- **Web** — `labs.snyk.io/experiments/skill-scan/` takes a GitHub or marketplace URL and returns a
  report. Snyk Labs describes it as free and self-service for anyone. Best for the one-off question
  this plan's step 1 asks. It is a UI: an attempt to call it directly stalled at resolving its JS
  chunk URLs, and it was not pursued further, since scripting a tool built for pasting is the wrong
  shape for a single question.
- **CLI** — `uvx snyk-agent-scan@latest <path>`, Apache-2.0, needs a free `SNYK_TOKEN`. Worth it
  only once this becomes repeatable; that is also the point at which the tool wants declaring
  properly (a `[packages.*]` entry on the PULSE side, or this repo's own dependency group) rather
  than an ad-hoc `uvx` inside a task.

[DECISION: **the monitor and the diagnostic are different tools, and conflating them is the trap.**
The `add-skill.vercel.sh/audit` query returns all three verdicts, needs no account, uploads nothing
and costs one request — that is what watches for a regression, and it is a _query of published
verdicts_, not a test. `snyk-agent-scan` names risks against a published taxonomy and explains them
— that is what to run before publishing something new, or when the monitor moves. Building the
recurring check on the scanner instead would need a token in CI, upload the repo on every run,
depend on an output schema its authors ask nobody to depend on, and still not reproduce the one
finding that matters.]

## The three responses, and what each costs

The question this was filed to answer is whether the ratings can be improved or the presentation
changed to get ahead of them. Three levers, and they are not alternatives — the first is owed
regardless.

**1. Say what the skill does, where the reader is standing.** Both flagged skills read broadly and
transmit nothing, and _no reader can currently discover the second half_ — the CLI shows
`Critical Risk` and `1 alert` and offers no route to a reason. A short, specific security section in
each skill's `SKILL.md` (what it reads, what it runs, that there is no network client, that
credential filenames are existence-checked and never opened) is the only lever that acts on the
moment of decision, costs nothing, and stays true whatever the scanners do next. It is also
checkable: a sceptical reader can confirm "no network client" with one grep.

**2. Narrow the genuine surface, if the alert turns out to name something narrowable.** Only worth
considering once the alert is known. The `SECRET_NAMES` options are above. Note what this trades:
`session-harvest` exists to find exactly the things that look alarming, so surface reduction costs
capability rather than cruft.

**3. Contest, with evidence, as the author.** Reasonable given the behavioural facts, and it needs
the alert first. Worth asking in the same message whether authors can see their own findings at all
— the answer is useful to every skill author, not just this repo.

[DECISION: **do not restyle the code to read as less alarming.** Renaming `SECRET_NAMES`, splitting
the constant, or scattering the check to reduce pattern-matchability would lower the signal without
changing one thing the skill does. That is deceiving a security scanner on a public registry, and it
would also make the code worse for the next reader — the constant is well named precisely because
the behaviour is worth noticing. If the behaviour is defensible, defend it in prose; if it is not,
change the behaviour.]

## Recommended direction

1. **Widen `session-harvest`'s stated purpose in `SKILL.md`.** This is now the primary fix, not the
   security-section idea: the alert is _on_ `SKILL.md`, and its substance is that the declared
   purpose is narrower than the capabilities described under it. Say in the description that it
   reads session transcripts, inspects several repositories, writes to always-loaded instruction
   files and commits locally. Counter-intuitive but it is what the finding asks for — the gap closes
   by making the stated purpose wider, not the skill quieter.
2. **Decide whether installs can be pinned.** "Mutable skill content from a personal GitHub repo" is
   the one concern that is about distribution rather than description, and the `skills` CLI already
   writes a `skills-lock.json`. Whether a tag or release changes what Socket sees is untested.
3. **Then dispute, on #2008's template** — one finding, the others conceded, audit URL, permalinks,
   the semantic gap. Two things to raise, and they are separate: the `Anomaly` reading of the old
   description, and the **`critical` headline that Socket's own page contradicts**. The second is
   the stronger report and is not about this skill at all.
4. **Then build the monitor**, on the audit endpoint rather than on a scanner, per the decision
   above. Derive the skill list from the repo; treat an unreachable endpoint as `unknown`; prefer a
   report over a gate until there is evidence a gate would not fire on somebody else's re-scan.
5. Re-run the verdict table at that point and diff it against this one — it is the baseline, and the
   scans move.

## Evidence trail

The originating session was working on `power-user-linux-setup`'s `~/AGENTS.md` plan cluster and hit
this while reading the `skills` CLI bundle for its agent registry. The distinctive phrase to search
its transcript for is **"Definitive answer, and it turned up something you'll want to act on."** The
same session pinned that CLI's usage telemetry off in PULSE (`tasks/ai.py`), which is a separate
matter from these ratings — the audit call that produces them is not gated by that pin and still
runs.

Transcripts expire after 30 days by default, so this one is readable until roughly 2026-10-02.

## The disclosure shipped 2026-09-05, so step 1 is partly done

Every skill that ships a script now carries `## What this skill reads, runs and writes` and a
`compatibility` field — landed, and the plan behind it since retired into `skill-authoring`'s
`SKILL.md` and rationale. For `session-harvest` that is the stated-purpose widening step 1 asks for,
in the body rather than the description — the description is the listing budget, and the section is
what a reader opens.

[UNVERIFIED: **whether the scanners read the disclosure as a wider declared footprint or as
reassurance.** Re-query the audit endpoint for `session-harvest` after the push that publishes it
and diff against the verdict table above. One measurement, taken once; nothing in the disclosure's
design should move on the answer.]
