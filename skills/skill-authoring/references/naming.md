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
Confirmed locally: this repo renamed one skill and the pre-rename slug is still listed in the public
index with its own install count, beside the live one.

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
is merely ahead of its install. Confirmed while writing this: the check flagged `skill-authoring`
against its own installed copy, because the file had just been edited.]

## Adjacent ecosystems, and whether their reasons transfer

| ecosystem    | rule                                                                 | problem it solves                           | transfers?                                                                                         |
| ------------ | -------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| MCP registry | reverse-DNS namespace, ownership proved                              | impersonation and squatting in a flat space | **Partly** — skills.sh already namespaces by source, so three `pdf` skills coexist                 |
| Homebrew     | name as the project markets it; avoid too-common words; name → class | uniqueness plus a name↔code coupling        | **Yes, on both counts** — skills have the same flat namespace and the same name↔directory coupling |
| npm          | uniqueness, no confusables                                           | typosquatting on a global install surface   | Weakly — skill installs are `owner/repo`-scoped                                                    |
| VS Code      | `publisher.name`                                                     | publisher-scoped uniqueness                 | In spirit; ~10% of the corpus already emulates it with author prefixes                             |

Homebrew is the closest analogue and its cookbook is worth quoting on the single-token risk: it
rejects "Go" as a formula name because it is "too common and there are too many implementations".

## Unverified

- Whether Claude Code's listing ever degrades to name-only _by design_. It is observed here but not
  documented, and `skillListingMaxDescChars` and its defaults are documentation-sourced only.
- Whether the registry's colon-bearing ids are frontmatter `name` values or composites the registry
  constructs.
- Any claim that changing a name moves selection rates. Nothing public supports it either way.
