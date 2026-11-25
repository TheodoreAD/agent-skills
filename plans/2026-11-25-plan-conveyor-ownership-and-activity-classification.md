---
status: idea
updated: 2026-11-25
---

# Plan conveyor ownership and activity classification

## Context

Setting up plan-conveyor on a second machine (Windows, 2026-11-25) exposed four problems with how a
machine is configured:

- **Nothing was asked.** An earlier session ran `install` with the defaults (`device = contractor`,
  one public root routed `repo`), and nothing enforces the walkthrough, so the machine looked set up
  while no decision had been made by the user.
- **The classification is too coarse.** The only per-machine question is which roots are public or
  shareable; everything else is assumed sensitive. There is no question about what a root _is_.
- **Nothing records that onboarding finished.** `install` writes a skeleton and every later command
  treats the skeleton as a decision.
- **The shared store carries one machine's layout.** Store folders are named after the projects root
  of whichever machine filed first (`github.com-personal/<repo>` from the Linux machine, where this
  one calls the same directory `personal`). `61cd844` made `doctor` tolerate that; it did not remove
  it. Two machines must never be forced to share directory names.

The configuration itself is already per machine and outside every repo:
`~/.config/plan-conveyor/config.toml` and `~/.local/state/plan-conveyor/`, XDG paths on every OS.
That stays. What changes is what it records and how it is filled in.

## The classification

The user's classification, restated as two independent axes plus one universal rule.

### Axis 1: ownership, per root (decided by the remote's owner)

- **`own`** — an organisation or account the user owns: their GitHub user, or on a corporate machine
  their user on the corporate GitHub instance. A repo here **may** keep its plans in its own
  `plans/` directory, but that is an explicit choice per repo, never a root-wide default.
- **`shared`** — an organisation the user contributes to or maintains but does not own. Work there
  is usually tracked in that organisation's own tracker, so plans never go into the repo; they go to
  the store.

The remote's owner decides ownership, matched against `own_accounts` as today; the directory a clone
sits in is only the fallback when there is no remote.

### Axis 2: activity, per machine (one or several)

- **`public`** — the user's own public work. No redaction beyond secrets.
- **`private`** — the user's own private work. Repo names and file paths may appear in other plans,
  but contents are not copied or quoted outside the repo they belong to.
- **`corporate`** — everything on the machine belongs to one organisation, which owns all of the
  work. No redaction beyond secrets. **Exclusive**: if present, it is the machine's only activity.
- **`contractor`** — client work. Each client root is fully insulated from every other root, while
  repos inside the same root are not isolated from each other.

A machine holds a set of activities (`public` + `private` + `contractor` is a normal personal laptop
with client work; `corporate` stands alone). Each root then carries one activity, except an `own`
root, where `public` versus `private` is a property of each repo: one GitHub account holds both
kinds. The default for a repo comes from its remote's visibility and is confirmed, not assumed.

### Universal: secrets

Secrets are never published from any activity, so secret detection is not a feature of any one of
them. It applies to every write and every push, on every machine.

### How the axes combine

| Ownership  | Activity     | Typical repos                                  | Where plans go                         |
| ---------- | ------------ | ---------------------------------------------- | -------------------------------------- |
| **own**    | `public`     | the user's public GitHub repos                 | the repo or the store, chosen per repo |
| **own**    | `private`    | the user's private GitHub repos                | the repo or the store, chosen per repo |
| **own**    | `corporate`  | the user's own repos on the corporate instance | the repo or the store, chosen per repo |
| **shared** | `public`     | an open-source organisation the user maintains | the store                              |
| **shared** | `corporate`  | the employer's organisation                    | the store                              |
| **shared** | `contractor` | a client's organisation                        | that client's store                    |

[NEEDS CLARIFICATION: two combinations are not covered by the classification. `own` + `contractor`
(an account the user created for one client) and `shared` + `private` (someone else's private repo
the user collaborates on personally). The working assumption is that the first behaves as
`contractor` for that client's root, and the second as `private` with plans in the store.]

## What the classification means for plan-conveyor

### Compartments: the unit every check reasons about

Ownership decides **where** a plan lives; activity decides **what may flow** between repos. The flow
rules reduce to compartments:

- **public** — one compartment, readable from anywhere.
- **private** — names are global, contents are per repo.
- **each contractor root** — its own compartment; nothing leaves it, names included.
- **corporate** — one compartment holding the whole machine.

| From             | Names may reach                    | Contents may reach                 |
| ---------------- | ---------------------------------- | ---------------------------------- |
| **public**       | anywhere                           | anywhere                           |
| **private**      | any `own` or `public` plan         | only the repo it belongs to        |
| **contractor R** | only repos and plans inside root R | only repos and plans inside root R |
| **corporate**    | anywhere on the machine            | anywhere on the machine            |

[NEEDS CLARIFICATION: may a client repo's plans name the user's private repos? The definition of
`private` allows names in "other plans", but a client repo is read by the client. Working default:
no — names of private repos do not flow into a contractor compartment.]

### Configuration (per machine, XDG, never synced)

A sketch of the shape, not the final keys:

```toml
[machine]
activities = ["public", "private", "contractor"] # `corporate` must be alone
onboarded = "2026-11-25" # absent until every decision is answered

[roots.personal] # names are this machine's own; nothing assumes another machine's
ownership = "own"

[roots.acme]
ownership = "shared"
activity = "contractor" # a compartment of its own

[repos."personal/agent-skills"]
plans = "repo" # explicit, asked when the repo's first plan is written
visibility = "public" # defaulted from the remote, confirmed
```

`device`, `public_roots`, `shareable_roots` and `[tiers]` are derived from this and retire.
`device = "work"` becomes `activities = ["corporate"]`; `device = "contractor"` becomes the
activities the user names.

### Onboarding is recorded, and incomplete onboarding blocks publishing

- Every decision is marked answered when the user answers it, including an answer equal to the
  default. An unanswered decision is visibly different from an answered one.
- `onboarded` is written only when every decision is answered: the machine's activities, each root's
  ownership and activity, the user's accounts, and the private terms the scan cannot derive.
- Until then `doctor` lists what is open, and everything that can publish (`sync`, `push`, the
  pre-commit scan) refuses with the next question to ask.
- A root that appears later reopens onboarding for that root only.
- `install --explain` stays the agent's script for asking, with `AskUserQuestion` per decision.

[DECISION: per-repo `plans = repo | store` is asked lazily, when an `own` repo's first plan is
written, not up front. Asking for every clone at setup is one question per repo on the machine,
which the 2026-09-07 report against the flat layout already rejected.]

### Stores follow compartments

The shareable/sensitive tier split is replaced by one store per compartment group:

- **The personal store** holds plans for `public` and `private` work and for `shared` + `public`
  organisations. It may have a remote, and syncs across the user's personal machines.
- **Each contractor root gets its own store**, local-only unless the user sanctions a remote for
  that client. The isolation is then physical: a session in client A has no store path that reaches
  client B's plans.
- **A corporate machine has one store**, which may push only to a sanctioned remote.

Store folders are named by repository identity (`github.com/TheodoreAD/agent-skills/`), not by any
machine's root names, so the store carries no machine's layout. `repos.toml` shrinks to aliases for
renamed repos and forks.

### The scan becomes a flow check

Today's scan asks one question: does a public repo name a non-public root? It becomes: does this
write move anything out of the compartment it came from?

- Forbidden names for a destination are the names of every contractor compartment except its own,
  plus private repo names when the destination is a contractor compartment.
- Content from a private repo leaking into another repo cannot be found by matching names.
  [UNVERIFIED: whether fingerprinting a private plan's distinctive lines catches a quote without
  drowning in false positives. Until that is measured, private-content flow is guarded by the
  cross-repo write rules below and by an agent rule, not by the scan.]
- Secret detection runs on every write regardless of compartment.

### Routing and cross-repo writes

- `own` repos: plans in the repo or the store, as recorded per repo. No root-wide `repo` default.
- `shared` repos: always the store of their compartment. `where` refuses a `plans/` directory there.
- `new --for`, `absorb` and every other cross-repo write are allowed only where the flow table
  allows the session's compartment to reach the target's. The session anchor (`db5ff45` fixed it on
  Windows) is what names the session's compartment.

## What it means beyond plan-conveyor

- **session-harvest** reads transcripts from every project on the machine. A harvest run in a
  personal repo must skip transcripts from contractor compartments, or it quotes client sessions
  into personal plans.
- **research-library** is one shared `$RESEARCH_HOME`. A client's repository cloned there crosses
  compartments; client material belongs in a per-client library or in that client's root.
- **skill-fitness** and **session-bash-audit** read transcripts too, and need the same filter.
- **Claude Code's own state** is not compartmented: `~/.claude/projects/` holds every session's
  transcript in one tree. That is the harness, and an agent rule in `~/.agents/AGENTS.md` is the
  available control: a session in a contractor compartment reads nothing outside its root.

## How repos are organised on disk

- **One root per compartment-and-owner**: one per account the user owns, one per client, and on a
  corporate machine one per corporate host. Mixed public and private repos may share an `own` root,
  because that distinction is per repo.
- **Root names are local.** The config maps each root to its classification on this machine, and the
  store names folders by repository identity, so no two machines have to agree on a directory name.

## Open questions

- [NEEDS CLARIFICATION: the two uncovered combinations above, and whether private names may enter a
  contractor compartment.]
- [NEEDS CLARIFICATION: does a contractor compartment get its own `private.extra` (its ticket
  prefix, its domain), or is that list machine-wide?]
- [DEFERRED: migrating an existing synced store from tier folders named by machine roots to
  identity-named compartment stores needs every machine on the new version first; it is the last
  phase, not the first.]

## Recommended direction

Implement in phases, each committed on its own and passing the gate:

1. **Config schema and onboarding record**, with no change to where plans go: the two axes in the
   config, answered decisions recorded, `onboarded` set, `doctor` reporting what is open, publishing
   refused until complete. Old keys are read and translated.
2. **Routing by ownership**: per-repo `plans = repo | store` for `own`, store only for `shared`.
3. **Scan as a flow check**, plus universal secret detection.
4. **Stores per compartment, folders named by identity**, with a migration both machines run.
5. **The other skills honour compartments**: session-harvest, research-library, skill-fitness,
   session-bash-audit, plus the `~/.agents/AGENTS.md` rule.

Before phase 1: re-run this machine's onboarding by hand with the current tool, asking every
decision, so `sync` can run in the meantime.
