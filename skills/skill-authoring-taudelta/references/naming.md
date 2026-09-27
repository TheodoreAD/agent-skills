# What is actually known about naming a skill

Researched 2026-09-12, prompted by a direct question: is a formalized naming convention worth
having, or is naming a creative exercise? The short answer is that the creative half has no evidence
behind it and the identity half has plenty, which is why `SKILL.md` carries a check and not a style
rule. Apparatus at `$RESEARCH_HOME/measurements/2026-09-12-pitch-and-skill-corpora/skillnames/`.

## The corpus

1,238 `SKILL.md` files across every clone in the research library → **1,043 skills, 1,027 distinct
names, 40 repos**, deduped per (repo, name). Largest contributors: `github/awesome-copilot` 435,
`sampleXbro/agentsmesh` 247, `phuryn/pm-skills` 68, `thatrebeccarae/claude-marketing` 56.

| measure                                    | result                                                          |
| ------------------------------------------ | --------------------------------------------------------------- |
| conforms to the spec's `name` rules        | **96.9%** (directory mismatch 2.9%, bad characters 0.2%)        |
| ASCII lowercase + hyphen only              | 99.8% (two names contain an underscore)                         |
| token count                                | 1: 8.2% · **2: 41.9%** · **3: 32.0%** · 4: 12.0% · 5+: 5.9%     |
| mean / median tokens                       | 2.67 / 2                                                        |
| length                                     | mean 18.5, median 17, p90 29, max 57; over 40 chars: 2.1%       |
| grammatical head                           | **noun-led 84.7%** · verb-led 11.4% · gerund-led 3.9%           |
| two-token names only (n=437)               | noun-led 85.6% · verb-led 11.0% · gerund-led 3.4%               |
| **modal shape** (2–3 tokens, noun-led)     | **64.1%**                                                       |
| embeds a product, language or vendor token | 14.4%                                                           |
| contains "skill" or "skills"               | 2.6%                                                            |
| single-token names                         | 8.2% — `access, audit, context, review, effect, configure…`     |
| cross-repo name collisions                 | 11 of 1,027 (`skill-creator` ×5, `code-review` ×2, `review` ×2) |
| author or vendor prefix namespacing        | ~10% overall; 95% within one repo, 71% within another           |

**The corpus is not heterogeneous in shape but its convergence is unlegislated**: 64% sit in one
bucket and 99.8% share a character set, with nothing written down anywhere requiring it.

## There is no published style guidance, and that is a finding

- **The specification's four authoring pages contain none.** There is an entire page on optimizing
  descriptions and not one paragraph on choosing a name.
- **Selection is documented as description-only.** Anthropic's own `skill-creator` says Claude
  "decides whether to consult a skill **based on that description**", and their
  `improve_description.py` passes the skill name in as fixed context — it is never a thing to
  change. No name-optimizer exists anywhere.
- **No published eval varies skill names.** SkillsBench looked like it might: its `experiments`
  README documents `BENCHFLOW_SKILL_NUDGE` with `name`/`description`/`full` modes. The benchflow
  changelog records it **removed**, as prompt injection that leaked skill metadata into the task
  instruction; the README documenting it is stale. So this is a confirmed gap, not a failed search.
- **The one community rule is contradicted by the corpus.** `obra/superpowers` advises naming by the
  verb and prefers gerunds (`condition-based-waiting` over `async-test-helpers`). Reality is
  noun-led by roughly 6:1, and gerund-led is 3.9%. That same file's own template shows
  `name: Skill-Name-With-Hyphens`, which the spec's charset forbids.

## What the spec requires, and how little it binds

`name` must be 1–64 characters, lowercase alphanumeric plus hyphens, no leading or trailing hyphen,
**no consecutive hyphens**, and must match the parent directory name.

Two things undercut it. The reference validator is **more permissive than its own prose** — it
NFKC-normalizes then accepts `c.isalnum() or c == "-"`, which admits any Unicode letter, and its
docstring says so. And the spec's client-implementation guide tells loaders to be lenient in a
revealing order:

- Name doesn't match the parent directory name → warn, load anyway
- Name exceeds 64 characters → warn, load anyway
- Description is missing or empty → **skip the skill**

A bad name is cosmetic; a missing description is fatal. That is the spec ranking the two fields.
`vercel-labs/skills` never checks the charset at all — it requires only a non-empty string, strips
terminal escape sequences from it (names are untrusted input rendered to a terminal), and falls back
to the directory basename. Live registry ids include `react:components` and
`stitch::code-to-design`, both spec-illegal.

## Where the name genuinely bites: it is a primary key

All of this is mechanical and all of it fails quietly. `SKILL.md` states the rule; this is the
evidence.

- **Silent deletion on collision.** `vercel-labs/skills`: a skill whose name has already been seen
  is skipped, first-seen-wins by traversal order, no warning.
- **The lockfile is keyed by name** — "map of skill name to its lock entry", and update "ultimately
  selects by skill name". Two discovered skills normalizing to one name makes update **fail
  closed**; a locked name matching nothing is reported as **deleted**.
- **Names are normalized before comparison**, lowercasing and mapping whitespace and underscores to
  hyphens, so `My Skill`, `my_skill` and `my-skill` are one identity.
- **Precedence and shadowing are name-based** — project overrides user, with a warning expected.
- **Names become an enum the model must reproduce** — the spec guide advises constraining the `name`
  parameter to valid names "to prevent the model from hallucinating nonexistent skill names".
- **Names become invocation syntax** (`/name`, `$name`), and for personal or project skills the
  slash command comes from the **directory** while `name` is the display label — a divergence that
  only surfaces when the two differ, which is 2.9% of the corpus.
- **Names are cited inside other skills' prose** (`Use superpowers:test-driven-development`), and
  nothing validates those citations.
- **Names are a security surface**: a scanner flags charset violations, and treats "anthropic" in a
  name as impersonation at MEDIUM and "claude official" at HIGH.

### Renaming, and the affordances skills do not have

Anthropic's plugin marketplace documents the slug as **immutable**: "users have it installed under
that slug, and renaming it breaks their install with a `plugin-not-found` error". It ships two
mitigations — a `displayName` to decouple label from slug, and a top-level `renames` map the loader
reads to auto-migrate, **live with 9 entries across 292 plugins**. Most strip a redundant suffix
(`qodo-skills`→`qodo`, `azure-skills`→`azure`) or disambiguate (`vals`→`valtown`).

**Skills have neither.** No `displayName`, no `renames` map; the name is identifier and label at
once. `skill-creator` accordingly instructs "**Preserve the original name** … use them unchanged."

**So a rename forks rather than moves, and the fork is permanent.** Registry rows are keyed
`source/skillId` and carry their own install counter. This repo deleted `mcp-skill-shipping` on
2026-08-28; on 2026-09-27 `skills.sh/api/search` still returned it at 2 installs, beside
`mcp-server-shipping` at 36. Thirty days, no pruning, and nothing in the CLI exposes an unpublish or
de-list path — publishing is a crawl that adds without retiring. The consequence is not clutter: the
surviving row advertises `source/<old name>` for a skill the repo no longer has, so a visitor who
acts on the listing gets a failed add. When the 2026-09-27 batch renamed eight skills, 274 installs
of history stayed on the dead rows and all eight successors started at zero.

**On the installed side the CLI reads a vanished name as a deletion.** `update.ts` classifies a
locked skill missing from its source as deleted upstream, prints "appear to have been deleted
upstream", and asks whether to remove the local copies; the new name arrives separately as a _new_
skill, so nobody is migrated automatically. In non-interactive mode (`--yes`, or no TTY, so any CI
or scripted setup) it prints "Skipping deletion in non-interactive mode" and **keeps** the old copy,
so those consumers hold both and the two compete for triggers until someone intervenes by hand.

[PITFALL: **pass `--mine <your registry source>` whenever you check a name you already publish**, or
your own row is counted against you. Without it, `check skill-fitness db-defaults-taudelta` reports
`collides: true` and exits 1 with this repo as the sole owner, and the failure text — "Pick a free
name now" — reads as though a stranger holds the slug. With `--mine theodoread` the same call is
clean. `audit` takes the flag too, and is the form to reach for after a rename.

Recorded because the flag was missed in exactly the session that most needed it: a rename batch's
verification run on 2026-09-27 read that exit 1 as a defect in the script, and the wrong conclusion
was written into this file before the argument parser was checked. The script was right. The lesson
is narrower than "tools lie" — read `--help` before calling an unexpected exit code a bug,
especially in a script this repo owns.]

## The name-only regime, which is the one place selection could turn on a name

**Codex implements a four-tier degradation ladder** against a skills-catalog budget (default 8,000
characters, or 2% of the context window, capped at 10,000): full entry → per-skill description
allowances cut mid-string with no ellipsis → **`render_minimum()`, which emits name and path with no
description at all** → skills dropped entirely. Its warning string is explicit: "All skill
descriptions were removed and N additional skills were not included."

With the measured median description of 226 characters, the mean catalog line is ~313 characters, so
that default budget starts truncating at **~26 skills**. Anyone with a normal installed set is
already in tier 2.

Codex is also the one place a name is a documented trigger token: "If the user names a skill (with
`$SkillName` or **plain text**) OR the task clearly matches a skill's description…" — so there, a
name colliding with ordinary English is a live false-trigger surface, which is what the corpus's
8.2% single-token names risk.

**Claude Code has the same architecture and does not document a name-only tier** — but it happens.
`skill-fitness` reads the listings actually sent, and on this machine **16 skills have appeared as a
bare name with no description**, from 2 truncated listings out of 815 real ones. Rare, undocumented,
and real.

[PITFALL: **a local name collision is always across loader scopes.** Two rival skills cannot share
one hub — the second overwrites the first — so the clash is the user hub against a project's
`.agents/skills`. Comparing a source checkout against the hub instead flags every skill whose source
is merely ahead of its install. Confirmed while writing this: the check flagged
`skill-authoring-taudelta` against its own installed copy, because the file had just been edited.]

## Adjacent ecosystems, and whether their reasons transfer

| ecosystem    | rule                                                                 | problem it solves                           | transfers?                                                                                         |
| ------------ | -------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| MCP registry | reverse-DNS namespace, ownership proved                              | impersonation and squatting in a flat space | **Partly** — skills.sh already namespaces by source, so three `pdf` skills coexist                 |
| Homebrew     | name as the project markets it; avoid too-common words; name → class | uniqueness plus a name↔code coupling        | **Yes, on both counts** — skills have the same flat namespace and the same name↔directory coupling |
| npm          | uniqueness, no confusables                                           | typosquatting on a global install surface   | Weakly — skill installs are `owner/repo`-scoped                                                    |
| VS Code      | `publisher.name`                                                     | publisher-scoped uniqueness                 | In spirit; ~10% of the corpus already emulates it with author prefixes                             |

Homebrew is the closest analogue and its cookbook is worth quoting on the single-token risk: it
rejects "Go" as a formula name because it is "too common and there are too many implementations".

## The author mark, and the split it rests on

Adopted 2026-09-27 over eight renames, after a first pass on 2026-09-12 had rejected an author
_prefix_ and never considered a suffix. The rule is in `AGENTS.md`; this is why it holds.

**The corpus divides into two kinds of skill, and only one has an identity problem.** A skill that
**does a job** is closer to an app than to a rule set — nobody expects a replica of someone else's
app, so the name should say what it does and the author is the least valuable thing it could carry.
A skill that **asserts how to work** predictably clashes with other developers' and vendors' rules,
and there the author is the fact a reader most needs, because these are one person's rulings and may
contradict theirs.

Two reasons, and the second is the one that generalises beyond this corpus.

- **Mechanically, an opinion-set name cannot be defended.** Measured 2026-09-27: `python-standards`
  is published by **17** repos, `python-guidelines` by **9**, `python-idioms` by 2 — while every
  tool-shaped candidate checked was free first time. It is the name every developer and every vendor
  independently reaches for, and first-seen-wins is by **traversal order**, not popularity, so the
  outcome is arbitrary and silent in both directions. Both names this repo vacated were already
  losing on their own exact slug: `python-conventions` to a 75-install rival against 37 here, and
  `skill-authoring` to `grafana/skills` at **3,072** against 38.
- **Editorially, the mark is what lets the accurate category word stay.** A distinctive synonym
  (`python-rulebook`, `python-canon`) buys the same collision immunity by sacrificing the word that
  describes the content. The mark buys it and keeps `-conventions`. It also disclaims authority by
  fact rather than by connotation: `python-canon` parses as _Python's_ canon, PEP-level and
  community-wide, and `-conventions` carries a milder version of the same; a personal mark cannot be
  misread that way, where `-rulebook` and `-house-style` only soften it.

### The position: trailing, against the corpus habit

Measured over the same corpus (1,044 skills, 40 repos, 24 with five or more skills), for a shared
**trailing** token — which the 2026-09-12 pass measured only for leading:

| position     | repos sharing it across ≥50% of their skills                           | what the shared token is                                     |
| ------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| **leading**  | **4 / 24** — `baoyu-` 95%, `caveman-` 71%, `tres-` 71%, `publish-` 50% | an author, a vendor, or a verb                               |
| **trailing** | **0 / 24** — highest is `-conventions` at 44% (`Goldziher/ai-rulez`)   | a category: `-writer`, `-fetcher`, `-change`, `-development` |

So author-marking does happen and **every repo that does it marks in front**; a trailing brand has
no prior art here, and the tail slot is trained as the category slot. Three reasons beat that:

1. **The mark must strip back to the current name.** `python-conventions` and `db-defaults` are
   lexical units that existing citations already spell — 155 of them for `plan-docs` alone.
   `python-conventions-taudelta` is the old name plus a mark, recoverable by eye;
   `python-taudelta-conventions` is a new string containing the same tokens.
2. **A mark is legible only where its position is fixed.** At the end it sits at the same
   offset-from-right in every name; medially it floats with the length of the first token.
3. **The ecosystem splits by what the token means.** An author _namespace_ leads (`@scope/pkg`,
   `owner/repo`, `com.example.*`, `publisher.name`); a _variant qualifier_ trails (`libssl-dev`,
   `python3-doc`, `python:3.12-slim`, `settings.local.json`). A house ruling is a variant: among the
   many possible sets of Python conventions, this is one flavour.

The cost is accepted: English wants modifiers before the head, this corpus is head-final, and
`db-defaults-taudelta` does put a non-head token in the head's slot. It survives because the mark is
not a word — nothing parses `taudelta` as a category — and because names ending the same way teach
the reader once.

[PITFALL: **"programmers narrow scope left to right" is not a sound reason for either order.**
Reverse-DNS narrows left to right, file variants right to left. If narrowing were the principle it
would equally license a prefix. The author-versus-variant split above is what decides it.]

[RETRACTED 2026-09-27: **"truncation eats the tail, so the mark is the droppable part."** Argued in
session for the suffix, then checked and found false — a truncated listing drops a description
**whole**; the harness keeps or drops and does not shorten, so names are never character-truncated.
A long name costs eye-scan and listing bytes, never information. The three reasons above are
unaffected.]

### The string, and the four that lost

`-taudelta` was chosen because it was already the author's published mark (`mkdocs-taudelta`) and is
tau + delta, their initials in a script that does not announce them. The mark's whole job is to say
_mine_, which a second, different mark would defeat: two personal marks is the same as none.

- **`-tad`** — shortest, and derivable from the GitHub handle at a glance. But "a tad" means
  _slightly_, so the tail reads as a diminutive: a hedge welded into the primary key of skills whose
  purpose is to assert that the rules are decided.
- **`-thad`** — not common vocabulary and reads as a personal name, the right category for a mark.
  But Thad is a real given name that is not the author's, so a reader who decodes it confidently
  decodes it wrong, and a false friend is worse than an opaque mark. It is also narrowly American:
  846th most common US male given name in the 1990 census (parent `Thaddeus` 611th, ~#798 today,
  peak 416 births in 2016), and no other language clips Thaddeus that way — Polish Tadeusz → Tadek,
  Lithuanian Tadas, Italian Taddeo, Spanish Tadeo, Portuguese Tadeu, French Thaddée, Irish Tadhg →
  Thady. The Slavic and Romanian route goes to `Tad-`, so of the two short forms the h is the
  imported one.
- **`-pulse`** — names a different repo of the author's, and a real English noun in the tail is
  exactly what gets read as a category word.
- **A given name spelled out** (`-theodore`) — ecosystem norms would tolerate it, so there is no
  reputational reason to avoid it. The structural one stands alone: **a given name in a primary key
  ages badly.** Old slugs are permanent, so if the skills are ever co-authored or published under an
  org, `-theodore` becomes false while a brand mark stays true.

[PITFALL: **a mark that sounds like a standards body re-introduces the over-claim defect**,
institutional instead of linguistic. `-iso`, `-labs`, `-foundation` would do it.]

## When a name is already finished

**The flavour slot is only free where the current word is inaccurate.** `-docs` never described what
`plan-conveyor` became — a status lifecycle plus a cross-repo transport — so replacing it bought
real information. `-library` already describes what `research-library` is, which is why a rename
proposed 2026-09-12 and carried as settled for a fortnight was **abandoned** 2026-09-27.

The candidate that lost was `research-trove`, and it lost on the same name-alone test the rest of
this file rests on. "Trove" lives almost entirely inside "treasure trove", so the image is _a pile
of valuable things_, and specifically things **found** — while the store is deliberately assembled,
catalogued and pruned. It also inspires no image of organisation or filing, which is the store's
whole value: canonical clone names, a provenance file per entry, a check command validating entries
against the conventions. "Library" carries the filing; "trove" carries only the accumulation. The
2026-09-12 argument for moving — "a doctrine plus a dependency-vetting procedure, neither of which
is a library" — does not survive either: the store half is literally a library, and vetting a source
before relying on it is reference-desk work.

[PITFALL: **a fantasy or sci-fi register is dense in nouns for a doer, and most skills name a
thing.** Rejected in one session for the same structural reason: `research-octopus`,
`research-guild`, and a round of hoarder animals (`research-magpie`, `-squirrel`, `-bowerbird`,
`-packrat`, `-jackdaw`, `-dragon`, all free). An animal or an organisation names an agent, while
that skill names a store — a directory of clones on disk. In two cases the metaphor argued for the
behaviour the skill exists to prevent: an octopus's many arms and a guild sending adventurers out to
fetch are both page-at-a-time fan-out, where the doctrine is clone once and grep locally, and git's
own _octopus merge_ already means many-at-once in a dev context. The register's **material** nouns
are the set that can pass — trove, hoard, reliquary, codex, atlas, stacks — though `research-vault`
is taken (2 repos), `research-archive` (1), and `research-codex` collides with a coding-agent brand,
which misleads about what kind of thing a skill is. Per-animal defects, so none is re-proposed:
magpie collects indiscriminately where the skill vets, packrat never discards where the library is
pruned, jackdaw steals where the store records provenance, squirrel is diminutive, bowerbird is
opaque, dragon names the guardian rather than the hoard.]

## Why `-conventions` survived and `-defaults` lost

Five skills end in `-conventions`, and a 2026-09-12 proposal would have harmonised them onto
`db-defaults`' suffix. Closed 2026-09-27 against the content:

- **`db-defaults` does not generalise.** Its body is one section per storage category, each with a
  `Default:` line and an `Escalate to:` line, opening "pick from this table, don't re-litigate". It
  is a **product-selection** skill, and `-defaults` is right because the content is a defaults
  table.
- **The cluster is not mostly selection.** Of `python-conventions`' 13 sections only Data modeling,
  AnyIO and HTTP client are picks from a menu; guard clauses and EAFP, statelessness and
  immutability, type hygiene, `src/` layout and modules-as-singletons are _how to write it_, with no
  product to default to. `mcp-python-conventions` is zero selection. So `mcp-python-defaults` would
  promise a table and deliver rules.
- **The words differ on authority, not on pick-versus-survey.** A convention is what a community
  does; a default is what you get if you don't choose. These skills do a third thing: they rule.
- **`-conventions` has the corpus's highest trailing-token share** as a category word, 12 of 27 in
  `Goldziher/ai-rulez`.

The collision on `python-conventions` was the only reason that did not depend on anyone's ear, and
the mark answers it without touching the word.

## Unverified

- Whether Claude Code's listing ever degrades to name-only _by design_. It is observed here but not
  documented, and `skillListingMaxDescChars` and its defaults are documentation-sourced only.
- Whether the registry's colon-bearing ids are frontmatter `name` values or composites the registry
  constructs.
- Any claim that changing a name moves selection rates. Nothing public supports it either way.
