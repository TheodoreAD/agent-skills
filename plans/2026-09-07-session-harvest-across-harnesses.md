---
status: idea
updated: 2026-09-07
---

# `session-harvest` beyond Claude Code: detect the harness, then get at the transcript

## Context

Asked for by the user 2026-09-07: users need to work across GitHub Copilot, Windsurf/Devin and
Claude Code, with Antigravity a later concern. A harvest has to know **which harness it is running
on**, and where relevant **whether that harness is an IDE or a CLI**. The user also flagged the
likely blocker up front: transcripts may have to be exported to a central store, especially where a
harness encrypts or does not persist them.

This is scoped as high-level framing. The user's instruction was to plan it and explore in another
session.

### What the skill assumes today

`session-harvest` is one skill with two halves, and only one of them is harness-bound:

- **Judgement** — the significance test, the routing filters, the report's groups, the next-session
  prompt. Entirely portable; nothing in it names a vendor.
- **Mechanism** — `scripts/harvest.py`. Portable except where it reads a transcript, and that is
  four subcommands out of seven: `transcript`, `turns`, `claims`, `filed`, plus the transcript half
  of `sweep`. `boundary` and `skills-state` need none.

The skill's `compatibility:` field already says the transcript half is unavailable elsewhere, so the
degradation is declared rather than silent — but "unavailable" is most of the skill's value: steps
4, 5 and 8 all read the conversation.

Concretely, the Claude Code assumptions in `harvest.py` are narrow and already isolated:

| assumption                                | where                                    |
| ----------------------------------------- | ---------------------------------------- |
| `~/.claude/projects/<slug>/<id>.jsonl`    | `PROJECTS_DIR`, `project_slug`           |
| `$CLAUDE_CODE_SESSION_ID` is the filename | `resolve_transcript`                     |
| `$CLAUDE_JOB_DIR/state.json`              | `job_state`, background jobs             |
| one JSON object per line, typed entries   | `read_entries`, `iter_blocks`, `Turn`    |
| `tool_use` blocks named `Bash`/`Edit`/…   | `bash_calls`, `written_paths`, `answers` |

`session-bash-audit` reads the same store and has the same dependency; anything decided here applies
to it.

### Two anchors already on this machine

Found while writing this, and both change the shape of the answer:

- **`AI_AGENT=claude-code_2-1-260_agent` is exported into every Bash call.** It is set by the
  `skills` CLI ecosystem, not by Claude Code — the installer's own output says
  `claude-code_2-1-260_agent Agent detected`, and it knows 71 agents including Copilot, Windsurf,
  Antigravity and Antigravity CLI. So a **vendor-neutral detection primitive already exists** and is
  maintained by somebody else. That is the "verify the upstream tool rather than reimplement it"
  case: check what `AI_AGENT` actually carries on each harness before writing a detector.
- **`CLAUDE_CODE_ENTRYPOINT=cli`** answers IDE-vs-CLI for this one harness. Whether the other three
  expose an equivalent is unknown and is the second thing to check.

`plan-docs` has already solved a smaller version of this problem and its shape is the precedent
worth copying: a three-tier session anchor — `$PLAN_DOCS_SESSION_REPO` (any harness, if it exports
it), `$CLAUDE_CODE_SESSION_ID` (Claude Code, no setup), then cwd — where `doctor` reports which tier
is in force and lists the weak one as a problem. Nobody is ever silently in the degraded tier.

### What is actually known about the three targets

Very little, and that is the honest state:

- **GitHub Copilot CLI** is installed here. `~/.copilot/` holds `config.json`, a
  `copilot-instructions.md` symlink to `~/AGENTS.md`, and a `logs/` directory of
  `process-<epoch>-<pid>.log` files — **two of them, process logs rather than per-session
  transcripts**. Whether a conversation is recoverable from those, or persisted anywhere else, is
  unestablished.
- **Windsurf / Devin** — nothing on this machine to read. Windsurf is IDE-first, Devin is
  cloud-first, and it is not obvious they share a store at all despite sharing a vendor.
- **Antigravity** — deferred by the user, but named so the design does not have to be reopened.

## Open questions

[NEEDS CLARIFICATION: does each harness persist a conversation transcript locally at all, and in
what shape? This is the question the whole plan turns on, and it has three possible answers per
harness with very different consequences: a readable local store (adapter), a local store that is
encrypted or opaque (export, see below), or nothing persisted (the harvest has to capture as it
goes, which is a different skill). Establish it per harness before designing anything.]

[NEEDS CLARIFICATION: what does `AI_AGENT` carry on Copilot, Windsurf and Devin, and is it present
in a shell the agent spawns or only during install? If it is reliably exported, detection is a
lookup rather than a heuristic and no vendor-sniffing code is needed. Check the `skills` CLI's own
agent registry for the canonical names.]

[NEEDS CLARIFICATION: does IDE-vs-CLI change any harvest behaviour, or is it only reported? It
plausibly changes: whether Bash calls exist to audit at all, whether the process/socket sweep is
meaningful, and whether a "paste this into the next session" prompt has anywhere to be pasted. If it
changes nothing, detect it, print it, and stop.]

[NEEDS CLARIFICATION: if a transcript must be exported to a central store, **who exports it and
when**? An export the user runs by hand at the end of a session is the thing a harvest exists to
stop relying on. An export that runs automatically is a hook, which this skill refuses everywhere
else — see its own "on-demand only, never installs hooks" rule. That tension has to be resolved
deliberately, not discovered.]

[NEEDS CLARIFICATION: where would an exported transcript live, and under what confidentiality rules?
A transcript is the most sensitive artefact this corpus handles — it contains client names,
credentials pasted in error, and file contents. If a central store is the answer it needs the
sensitive tier's treatment (local-only, no remote) at minimum, and probably its own store rather
than a directory inside the plans store, which has a remote on the shareable half.]

[NEEDS CLARIFICATION: one skill with adapters, or one skill per harness? The judgement half is
identical and must not fork — that is most of the skill's value and all of its accumulated evidence.
The reading half is entirely different per harness. A `transcripts/` adapter module inside
`harvest.py`, selected by the detected harness, keeps one skill; separate skills would duplicate
~700 lines of body text with no mechanism keeping them in step.]

[NEEDS CLARIFICATION: what does a harvest do on a harness whose transcript it cannot read — refuse,
or run degraded? Today it errors on `no transcript resolved`. A degraded run that still does step 0,
the live-state sweep, git/CI state and the report is worth a great deal and is most of steps 5
and 8. It must say loudly which steps did not run, since a harvest's report reads identical whether
or not it saw the conversation — the same failure mode as a stale install.]

[NEEDS CLARIFICATION: does `session-bash-audit` follow, and does it have to? It reads the same store
for a different purpose. If the transcript reading becomes a shared adapter, the two skills would
have to import across skill directories — which `harvest.py` deliberately refuses today (the
`EXIT_MASKED_RE` comment says why: they install separately and an import breaks whenever one is
installed without the other). Duplicating the adapter may be the right answer again.]

## Recommended direction

Rough, and deliberately not prescriptive — this is what to test in the exploring session.

1. **Establish the facts before designing.** One session per harness, or one session doing three
   passes: install it, run a short real conversation, and find out what is on disk afterwards. The
   deliverable is a table — store path, format, whether it is readable, whether an id is exported
   into the agent's shell — not a design.
2. **Detection first, because it is cheap and independent.** A `harvest.py harness` subcommand that
   prints the detected harness, how it was detected, and the IDE/CLI answer, following `plan-docs`'
   tiered-anchor shape: an explicit env var, then `AI_AGENT`, then per-harness markers, then unknown
   — reporting which tier answered, so nobody is silently in the weak one. This is useful on its own
   and lands before any transcript work.
3. **Then a transcript adapter seam.** `resolve_transcript` and `read_entries` are already the only
   two doors into the store; everything downstream works on a list of typed entries. The realistic
   shape is a normaliser per harness producing the entry types `turns`/`claims`/`sweep` already
   consume, not a rewrite.
4. **Treat export as a last resort, and design it only for a harness that forces it.** It is the
   expensive option, it carries the worst confidentiality exposure, and it conflicts with the
   skill's no-hooks rule. Two of three harnesses may not need it.
5. **Keep Antigravity out of scope but not out of the seam.** Naming it as a fourth adapter costs
   nothing now; retrofitting a seam that assumed three does.

The honest framing for the exploring session: **this is mostly a research task, not an
implementation one.** The code seam is small and already isolated. What is unknown is what four
vendors put on disk, and no amount of design settles that.
