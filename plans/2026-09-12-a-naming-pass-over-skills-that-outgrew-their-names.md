---
status: planned
updated: 2026-09-27
---

# A naming pass over the skills that outgrew their names

## Context

Raised by the user 2026-09-12: _"plan docs is a name I let happen without much scrutiny, but it's
evolved into so much more, same as research-library and some of the skills and conventions ones,
maybe it would be good to do a pass and see if we can come up with more expressive names."_

Deliberately not executed. The user's call was to write the options down and stop, because a rename
is a one-way door and there is no cost to deciding later except that install counts grow slowly.

Naming _style_ has no evidence behind it — the specification's authoring pages publish none, no eval
anywhere varies skill names, and selection is documented as description-only. That research is in
`skills/skill-authoring/references/naming.md` and is not repeated here. What follows is therefore a
taste exercise with two hard constraints attached, and the constraints are the useful part.

**Reopened 2026-09-27** and carried much further than a taste pass. The session that did it
re-measured the corpus for a question the first pass never asked, and reversed three of its own
conclusions. What changed: an **author mark** is adopted as a suffix on the opinionated skills,
which retires the `-conventions`/`-defaults` question entirely, because that question only ever
existed to find a word nobody else had claimed; and `research-library` is **kept**, the 2026-09-12
rename abandoned. Nothing is open now. Still not executed — the batch below is specified and
waiting.

## The reframe: the bland half is the second token

The one regime where a name carries the **entire** trigger signal is the degraded listing —
descriptions stripped, names alone. Codex implements that as a documented tier; on this machine 16
skills have appeared as bare names in real Claude Code listings. So the first token is what a reader
scans, and the corpus already does the right thing by putting the domain there (`python-`, `mcp-`,
`session-`, `skill-`).

[DECISION: **expressiveness goes in the second token, and the domain token stays.** `plan-docs` is
not bland because of `plan-`; it is bland because of `-docs`. This kills the tempting direction of
pure metaphor — `manifold` was floated and rejected, because a name that tells a stranger nothing is
at its worst in exactly the regime where the name is all there is, and "manifold" additionally
carries misleading mathematical and mechanical senses.]

[PITFALL: **a uniform author prefix would make the name-only regime worse, not better.** Measured
over 1,044 skills in 40 repos: of 24 repos with five or more skills, only 4 put half or more behind
one leading token, and 14 are under 20% — so it is a minority practice, but bimodal, near-total
where adopted (`baoyu-` 95%, `caveman-` 86%). It namespaces perfectly and would end the collision
problem outright. It also pushes the distinguishing token later in every single name, at the one
moment a reader has nothing else. Considered and not adopted; if it ever is, adopt it selectively on
the generic names rather than uniformly.]

**Availability was checked, not assumed.** Every candidate below was run through `skill-authoring`'s
`names.py check` against the public index, on 2026-09-12 and again 2026-09-27. Worth recording that
the obvious evocative choice, `skill-forge`, is already published by **five** repos —
distinctiveness and availability correlate, so checking early is cheap and guessing is not.

[PITFALL: **`names.py check` cannot answer the question for a name you already publish.** Run
against `skill-fitness` and `db-defaults` on 2026-09-27 it reported `collides: true` and exited 1
with `theodoread/agent-skills` as the sole owner — your own registry entry read as a competitor.
Harmless once known, and it means a `check` of an existing name has to be read owner by owner rather
than by exit code. Not filed as its own plan yet.]

## The author mark: the corpus splits into tools and opinions

The 2026-09-12 pass rejected an author prefix (above) and did not consider a suffix. The user
proposed one 2026-09-27, with the argument that decided it: **skills divide into two kinds, and only
one kind has an identity problem.**

- A skill that **does a job** — `plan-conveyor`, `research-library`, `skill-fitness`,
  `session-harvest` — is closer to an app than to a rule set. Nobody expects a replica of someone
  else's app, so the name should say what it does and the author's identity is the least valuable
  thing it could carry.
- A skill that **asserts how to work** — the `-conventions` cluster, `db-defaults`,
  `skill-authoring` — predictably clashes with other developers' and corporations' opinionated
  rules. There the author is not decoration: it is the fact a reader most needs, because these are
  one person's rulings and may contradict theirs.

[DECISION: **the opinionated skills carry a personal mark; the tools do not.** Statable as a rule
for the next skill: _a skill carries the mark when it asserts how to work and another author would
plausibly assert differently; a skill that does a job is named for the job._]

**Why the generic name is not worth defending.** Measured 2026-09-27: `python-standards` is
published by **17** repos, `python-guidelines` by **9**, `python-idioms` by 2 — while every
tool-shaped candidate checked was free first time. A generic opinion-set name accretes claimants
forever, because it is the name every developer and every vendor independently reaches for, and
first-seen-wins is by **traversal order** rather than by popularity, so the outcome is arbitrary and
silent in both directions. This is the strongest single argument for the mark and it was missed on
2026-09-12.

[DECISION: **the mark's real payoff is that the accurate category word survives.** A distinctive
second token (`python-rulebook`, `python-canon`) buys collision immunity by sacrificing the word
that describes the content. The mark buys the same immunity and lets `-conventions` stay. That is
why the `-conventions`/`-defaults` question below is closed rather than decided — the word was never
the problem.]

[DECISION: **it also fixes the over-claim defect, which no word-hunt could.** `python-canon` reads
as _Python's_ canon — PEP-level, community-wide — and `-conventions` carries a milder version of the
same. `python-standards` (17 claimants) and `python-guidelines` (9) are the same over-claim plus a
collision. Locally-scoped words (`-rulebook`, `-rulings`, `-house-style`) disclaim authority only by
connotation; a personal mark disclaims it by naming the author. `python-guidelines` additionally
points straight at PEP 8, whose actual title is _Style Guide for Python Code_ — which genuinely
**is** what the Python authors decided.]

### The position: trailing, not leading and not medial

Measured 2026-09-27 over the same corpus (1,044 skills, 40 repos, 24 with five or more), for a
trailing shared token, which the first pass measured only for leading:

| position     | repos sharing it across ≥50% of their skills                             | what the shared token actually is                            |
| ------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| **leading**  | **4 / 24** — `baoyu-` 95%, `caveman-` 71%, `tres-` 71%, `publish-` 50%   | an author, a vendor, or a verb                               |
| **trailing** | **0 / 24** — best is `-conventions` at 44% (`Goldziher/ai-rulez`, 12/27) | a category: `-writer`, `-fetcher`, `-change`, `-development` |

So author-marking does happen, and **every repo that does it puts the mark in front**. A trailing
brand has no prior art in 1,044 skills, and the tail slot is trained as the category slot.

[DECISION: **trailing anyway, for three reasons that beat the corpus habit.**

1. **The mark must be strippable back to the current name.** `python-conventions` and `db-defaults`
   are lexical units, and 130 existing citations in shipped files spell them that way.
   `python-conventions-taudelta` is the old name plus a mark, recoverable by eye;
   `python-taudelta-conventions` is a new string containing the same tokens, so every stale citation
   and every human memory becomes a re-parse.
2. **A mark is legible because its position is fixed.** At the end it sits at the same
   offset-from-right in every name and strips in one glance. Medially it floats with the length of
   the first token — `db-taudelta-defaults` against `invoke-task-taudelta-conventions`.
3. **The ecosystem convention matches the mark's meaning.** An author _namespace_ leads
   (`@scope/pkg`, `owner/repo`, `com.example.*`, Maven `groupId:artifactId`, VS Code
   `publisher.name`). A _variant qualifier_ trails (`libssl-dev`, `python3-doc`, `python:3.12-slim`,
   `settings.local.json`, `app.test.ts`). The user's own framing — "the filter/specializer" — makes
   it a variant: among the many possible sets of Python conventions, this is one flavour.

The cost is real and accepted: English wants modifiers before the head, the corpus is head-final,
and `db-defaults-taudelta` does put a non-head token in the head's slot. It survives because the
mark is not a word — nobody parses `taudelta` as a category — and because five names ending the same
way teach the reader once.]

[PITFALL: **"programmers narrow scope left to right" is not a sound reason for either order**,
though it is the one that feels right. Programming narrows in both directions: reverse-DNS narrows
left-to-right, file variants right-to-left. If narrowing were the principle it would equally license
a prefix. The author-versus-variant split above is what actually decides it.]

[RETRACTED 2026-09-27: **"truncation eats the tail, so the mark is the droppable part."** Argued in
session as a point for the suffix, then checked and found false.
`plans/2026-09-07-listing-budget-truncates-real-sessions.md` is explicit: a truncated listing drops
a description **whole** — the harness keeps or drops, it does not shorten. Names are never
character-truncated, so a long name costs eye-scan and listing bytes, never information. The suffix
still wins on the three reasons above.]

### The string: `-taudelta`

[DECISION: **`-taudelta`**, chosen by the user 2026-09-27. It is already their published mark
(`mkdocs-taudelta`), it is tau + delta — their initials in a script that does not announce them —
and the mark's entire job is to say _mine_, which a second, different mark would defeat. Two
personal marks is the same as none.]

Rejected, with the reason each time:

- **`-tad`** — 3 chars and derivable from the GitHub handle at a glance, but "a tad" means
  _slightly_, so the tail reads as a diminutive: a hedge welded into the primary key of seven skills
  whose whole purpose is to assert that the rules are decided.
- **`-thad`** — not common English vocabulary and reads as a personal name, which is the right
  category for an author mark. But Thad is a real given name that is not the author's, so a reader
  who decodes it confidently decodes it wrong; an opaque mark is fine and a false friend is worse.
  Measured: 846th most common US male given name in the 1990 census (parent `Thaddeus` 611th, ~#798
  today, peak 416 births in 2016). Essentially US-only as a clipped form — no other language clips
  Thaddeus that way (Polish Tadeusz → Tadek, Lithuanian Tadas, Italian Taddeo, Spanish Tadeo,
  Portuguese Tadeu, French Thaddée, Irish Tadhg → Thady), and notably the Slavic/Romanian route goes
  to `Tad-` rather than `Thad-`, so of the two short forms the h is the imported one.
- **`-pulse`** — names the setup repo, while these skills ship from `agent-skills`; misattribution.
  And a real English noun in the tail is exactly what gets read as a category word.
- **A given name spelled out** (`-theodore`, `-theodoread`) — the user's objection is the durable
  one: a consumer sees it in their own skill listing permanently, framed as "this thing is named
  after a person" rather than "I chose this author", which is more conspicuous than a repo path.
  Ecosystem norms would tolerate it (`@sindresorhus/*`, personal VS Code publishers, every
  `owner/plugin` in the Vim world, `baoyu-` at 95%), so there is no reputational risk to avoid in
  either direction — but the structural argument stands on its own: **a given name in a primary key
  ages badly.** Old slugs are permanent, so if the skills are ever co-authored or published under an
  org, `-theodore` becomes false while `-taudelta` stays true.

[PITFALL: **a mark that sounds like a standards body would re-introduce the over-claim defect**,
institutional instead of linguistic. `-iso`, `-labs`, `-foundation` would do it. `taudelta` reads as
one distinct source, which is the disclaimer wanted.]

Lengths, against the corpus (median 17, p90 29, max 57, over-40 2.1%): the marked set's longest is
`python-testing-conventions-taudelta` at **35**, with 4 of 7 names over the p90 and **none** over
40, far inside the spec's 64-char cap. All seven were checked free 2026-09-27, in both the trailing
and the medial order.

### The marked set

| current                      | becomes                               |
| ---------------------------- | ------------------------------------- |
| `python-conventions`         | `python-conventions-taudelta`         |
| `python-testing-conventions` | `python-testing-conventions-taudelta` |
| `mcp-python-conventions`     | `mcp-python-conventions-taudelta`     |
| `invoke-task-conventions`    | `invoke-task-conventions-taudelta`    |
| `polite-mcp-conventions`     | `polite-mcp-conventions-taudelta`     |
| `db-defaults`                | `db-defaults-taudelta`                |
| `skill-authoring`            | `skill-authoring-taudelta`            |

`db-defaults` keeps its good name and gains the mark because its content — a table of picks — is the
most clashable in the corpus. `skill-authoring` qualifies twice over: opinionated process, and a
6-repo collision. `polite-mcp-conventions` is already personal by content, so the mark is redundant
there but consistent.

## `plan-docs` → `plan-conveyor`

The user's word, and it beats every alternative considered because it is the only one that catches
**both** halves of what the skill became:

- the **status lifecycle** — a plan enters as an idea and moves through stations until it comes off
  the end and is deleted, which is the doctrine the skill states repeatedly ("a working set that
  empties out");
- the **cross-repo transport** — a plan is literally conveyed from the repo that noticed it, through
  the store, to the repo that owns it, where another session absorbs it. Nothing else in the corpus
  does that.

Rejected alternatives, each catching only one half: `plan-turnover` and `plan-lifecycle` (the
emptying, not the transport), `plan-relay` (the transport, not the lifecycle), `plan-ephemera`
(literally accurate — ephemera are transient documents meant to be discarded — but reads precious).

Also rejected: `plan-convertor`, which was a typo for conveyor, and would have been wrong anyway
since the skill converts nothing. And the markdown-wordplay direction the user floated, which
produced only names for details of the format (`plan-frontmatter`, `plan-checkbox`,
`plan-strikethrough`) rather than for what the skill does.

`plan-conveyor` is free in the registry. **Treat this one as settled unless the user says
otherwise.** No mark: it is a tool, not a ruling.

## `research-library`: chosen, reopened, and kept

[DECISION 2026-09-27: **`research-library` stays. No rename.** This reverses the 2026-09-12 choice
of `research-trove`, on the user's own observation: _"for most people that would create a mental
image closer than what trove would, since most wouldn't have a clear image of a trove."_ Run the
name-alone test — the criterion the whole plan rests on — and the incumbent scores highest of
everything considered.

- **"Trove" lives almost entirely inside the collocation "treasure trove."** Outside it the word is
  rare, so the image delivered is _a pile of valuable things_, and specifically things **found**,
  since a treasure trove is stumbled upon. This store is deliberately assembled, catalogued and
  pruned — so the imprecision runs in the wrong direction.
- **And a trove is an undifferentiated heap.** The user's second objection, and it is the sharper of
  the two: a trove inspires no image of organisation or filing, while organisation is the store's
  whole value — canonical clone names, a provenance file per entry, and a check command that
  validates every entry against the conventions. "Library" carries the filing; "trove" carries only
  the accumulation.
- **"Library" maps onto the mechanism almost exactly**: material you go and read locally instead of
  fetching it fresh, organized, catalogued, reused across projects. That is ~50 clones plus
  reference PDFs and mirrored docs, with provenance files, a check command and a README of
  conventions.
- **The 2026-09-12 argument for moving does not survive scrutiny.** It held that the skill grew into
  "a doctrine plus a dependency-vetting procedure, neither of which is a library." Both halves are
  library work: the store half is literally a library, and vetting a package before relying on it —
  maintained, who commits, ships `py.typed`, what the version caps hold back — is reference-desk
  work, judging a source before trusting it. The doctrine (clone rather than fetch) is the _reason_
  to keep a library, not a second thing needing another noun.
- **The only remaining reason was the collision, and it is the mildest tier**: 2 aggregators,
  `bighardperson/computer-science-skills-collection` and `skills.volces.com`, re-checked live
  2026-09-27. Silent shadowing only if that specific repo is installed, against 6 for
  `python-conventions` and 17 for `python-standards`.
- **And keeping it deletes the batch's second cross-repo cost.** The deployed home instructions cite
  `research-library` twice — once by skill name in the research-delegation rule, once as
  `~/.agents/skills/research-library/scripts/library.py` — so renaming it would need a filed plan
  into another repo, the only other rename that does. Plus 29 in-repo citations.

The general rule this yields, worth more than the case: **the flavour slot is only free where the
current word is inaccurate.** `-docs` was inaccurate for what `plan-docs` became, so `-conveyor`
buys real information. `-library` is already right, so flavour there would trade accuracy for
register and get nothing back. `research-mirror` was offered as the memorability answer and is
superseded by the same reasoning — the incumbent already was the memorable, accurate word.]

The 2026-09-12 reasoning is kept below, since it is what the reversal argues against.

[DECISION: **the first token stays `research-`.** The user's framing, which is sharper than the
skill's own description: it is for someone _"researching a library, app docs, articles, packages,
and gathering facts locally to avoid lots of reading html and web search."_ That is a **method**,
not a library — and `-library` is the half that the skill outgrew, because what it grew into is a
doctrine (clone and grep the real source) plus a dependency-vetting procedure, neither of which is a
library. An earlier proposal of `primary-sources` was rejected by the user as not speaking to them,
and it also drops the word that names the activity.]

All free in the registry as of 2026-09-12:

| candidate         | what its second token claims                       | note                                                                 |
| ----------------- | -------------------------------------------------- | -------------------------------------------------------------------- |
| `research-mirror` | a local copy of upstream                           | most precise about the mechanism; every developer knows the term     |
| `research-trove`  | a gathered collection worth having                 | closest to the user's own word, "gathering"; warm and memorable      |
| `research-corpus` | a body of text you search                          | matches the "grep it locally" half exactly; slightly academic        |
| `research-larder` | provisions laid in before they are needed          | captures gather-in-advance-to-avoid-fetching best; unusual word      |
| `research-stacks` | where the volumes are, as opposed to the catalogue | the library metaphor that lands; "stack" hits a data structure first |
| `research-depot`  | a place things are stored and dispatched from      | would echo `plan-conveyor` deliberately                              |
| `research-desk`   | where the work happens                             | human and modest; vague about there being a store                    |

[DECISION: **`research-trove`**, chosen by the user 2026-09-12, and the reason given matters more
than the choice: _"sounds better, and is in line with the slightly fantasy or sci fi themes I
favor."_ So the corpus has a house aesthetic, stated for the first time here. The trade-off it
settles is mechanism versus method — `-mirror` and `-corpus` name what the store _is_, `-trove` and
`-larder` name what it is _for_ — and the activity won, consistent with the first token staying
`research-`.]

[RESOLVED 2026-09-27: reopened by the user as _"trove is hard to remember for most people I think"_,
and settled by the keep-`research-library` decision at the top of this section. The intermediate
answer offered here, `research-mirror`, is superseded by it.]

[DECISION: **flavour is admissible exactly while the word still denotes.** This is the line that
already rejected `manifold`, now stated as a rule rather than a one-off. "Trove" passes because it
means a gathered collection of valuable things, so a stranger reading `research-trove` with the
description stripped infers roughly the right thing; "manifold" fails because it means nothing here
and misleads toward mathematics. A theme left unguarded drifts toward opacity, and the guard is the
same name-alone test the whole section rests on — not a judgement about how much whimsy is
tasteful.]

[PITFALL 2026-09-27: **the fantasy register is dense in agent-nouns, and every one of them fails the
name-alone test the same way.** Three were proposed and rejected in one session —
`research-octopus`, `research-guild`, and a round of hoarder animals (`research-magpie`,
`-squirrel`, `-bowerbird`, `-packrat`, `-jackdaw`, `-dragon`, all free). The structural miss: **an
animal or an organisation names a doer, while this skill names a store** — a directory of clones on
disk. And in two cases the metaphor argued for the behaviour the skill exists to prevent: an
octopus's many arms and a guild sending adventurers out to fetch are both page-at-a-time fan-out,
where the doctrine is clone once and grep locally. Git's own _octopus merge_ already means
many-at-once in a dev context. So the passing set is the register's **material** nouns — trove,
hoard, reliquary, codex, atlas, stacks. Of those, `research-vault` is taken (2 repos) and
`research-archive` (1); `research-codex` denotes best but Codex is now a coding-agent brand, which
misleads about what kind of thing the skill is. The per-animal defects, so none is re-proposed:
magpie collects indiscriminately where the skill vets; packrat never discards where the library is
pruned; jackdaw steals where the store records provenance; squirrel is diminutive; bowerbird is
opaque; dragon names the guardian, not the hoard.]

[CLOSED 2026-09-27: **whether the family should echo.** Moot in the way that matters: with
`research-library` kept, there is no second flavoured name to echo `plan-conveyor`, and the question
never recurs, because the rule that settled it is the one above — **the flavour slot is only free
where the current word is inaccurate.** A register is not a scheme, and a theme applied uniformly
would force bad names onto the skills that do not need one. `plan-conveyor` standing alone beside
plainly-named tools is the intended end state, not an inconsistency to fix later.]

## The collisions, and what now answers them

A duplicate name is dropped silently, first-seen-wins, so installing one of these repos shadows the
local skill with no message anywhere. The mechanism was re-read in the CLI's own source on
2026-09-27 rather than taken from the skill: **name is the primary key everywhere** —
`discoverSkills` keys a `seenNames` set and its `includeDuplicateNames` option exists only "so
callers can detect ambiguous locations", `listInstalledSkills` dedupes on `scope:name`, and the
lockfile, removal and relocation all key by name. There is no source-qualified addressing anywhere,
so a collision is the design rather than a bug awaiting a fix, and armour is worth something.

| current              | also published by                                                | answer                     |
| -------------------- | ---------------------------------------------------------------- | -------------------------- |
| `skill-authoring`    | 6 repos, including `grafana/skills` and `microsoft/azure-skills` | the mark                   |
| `python-conventions` | 6 repos                                                          | the mark                   |
| `research-library`   | 2 repos (aggregators — see above)                                | nothing; accepted as-is    |
| `plan-docs`          | 1 repo (`narusenia/skills`)                                      | a distinctive second token |
| `session-harvest`    | 1 repo (`brunofaust/claude-all`)                                 | nothing; the name is good  |

Superseded 2026-09-12 proposals, kept so they are not re-derived: `skill-smithing` for
`skill-authoring` and `python-defaults` for `python-conventions` — both free, both now unnecessary,
because the mark keeps the accurate word instead of trading it for an unclaimed one.

## The `-conventions` cluster: closed, `-conventions` stays

Five skills end in `-conventions`, and the 2026-09-12 pass proposed harmonising them onto
`db-defaults`' suffix: `python-defaults`, `python-test-defaults`, `mcp-python-defaults` (all free).

[DECISION 2026-09-27: **no harmonisation. `-conventions` stays on all five.** The "For" argument did
not survive reading the actual content.

- **`db-defaults` does not generalise.** Its body is one section per storage category, each with a
  `Default:` line and an `Escalate to:` line, opening "pick from this table, don't re-litigate from
  scratch each session." It is a **product-selection** skill, and `-defaults` is right because the
  content is literally a defaults table.
- **The cluster is not mostly selection.** Of `python-conventions`' 13 sections only Data modeling,
  AnyIO and HTTP client are picks-from-a-menu; the rest — guard clauses and EAFP, statelessness and
  immutability, type hygiene, `src/` layout, modules-as-singletons — are _how to write it_, with no
  product to default to. `mcp-python-conventions` is zero selection: stdio logging discipline, what
  an exception becomes at a tool boundary, a docstring as an LLM-facing contract. So
  `mcp-python-defaults` would promise a table and deliver rules — narrowing the name against the
  content, the inverse of the honesty the change was meant to buy.
- **The words differ on authority, not on pick-versus-survey.** A convention is what a community
  does; a default is what you get if you don't choose. These skills do a third thing: they rule,
  with reasons, and `python-testing-conventions` even marks which entries override the model's
  instinct.
- **And `-conventions` has real prior art as a category tail** — `Goldziher/ai-rulez` uses it on 12
  of 27 skills, the highest trailing-token share in the corpus.

The collision on `python-conventions` was the only reason that did not depend on anyone's ear, and
the mark answers it without touching the word.]

## What a rename actually costs, so the batch is done once

Gathered from `skill-authoring` and measured in-repo 2026-09-27. **Do the whole set in one batch** —
most items are paid per batch, but citation sweeping is per name.

1. **Directory and frontmatter `name` move together**, and must match; `test_name_is_spec_valid` and
   `test_name_matches_directory` gate it.
2. **The README catalogue row** is gated by `test_listed_in_readme`.
3. **Cross-skill citations in prose are validated by nothing**, and they are the bulk of the work.
   Measured shipped-file citations: `python-conventions` **82**, `invoke-task-conventions` 17,
   `python-testing-conventions` 16, `mcp-python-conventions` 9, `polite-mcp-conventions` 6 — mostly
   slugs in backticks inside _other_ skills' bodies (`python-refactor-audit` cites two,
   `python-testing-conventions` cites `python-conventions` four times as its override reference,
   `db-defaults` cites it for the don't-double rule). An `rg` per old name is the only check there
   is.
4. **Five `skill-fitness/evals/*.json` files carry `python-conventions` as expected-selection
   data**, up to 11 hits in one file. A rename that does not update them in lockstep reads as a
   trigger regression rather than as stale test data.
5. **The deployed home instructions cite none of the cluster's names** — verified 2026-09-27, zero
   hits across `~/.agents/AGENTS.md` and `~/.claude/CLAUDE.md`. So no filed cross-repo plan is
   needed for the marked set. It **is** needed for any rename of `plan-docs` or `research-library`,
   the only two skills those instructions name: `plan-docs` for its `scripts/plans.py` path, and
   `research-library` twice over — by skill name in the research-delegation rule, and as
   `~/.agents/skills/research-library/scripts/library.py`. Corrected the same day it was written:
   `research-library` had been recorded as costless while its citation sat two lines away in the
   same file.
6. **Installing is additive.** After reinstalling, `skills remove -g --skill <old-name>` or the old
   copy stays loadable and competes for triggers — measured previously at eleven installed skills
   for ten sources.
7. **The old slug is permanent in the public index, and becomes a broken install path.** Renaming
   forks rather than moves, and this repo's own history proves the duration: `mcp-skill-shipping`
   was deleted here on 2026-08-28 (commit `c35f0ff`, the split into `mcp-server-shipping` and
   `skill-authoring`), and on 2026-09-27 it was still returned by `https://skills.sh/api/search` at
   2 installs, beside `mcp-server-shipping` at 36. Thirty days, no pruning. Rows are keyed
   `source/skillId` and carry their own install counter, that endpoint is the site's own search, and
   nothing in the CLI source exposes an unpublish, de-list or delete path — publishing is a crawl
   that adds without retiring. So the consequence is not clutter: the surviving row advertises
   `theodoread/agent-skills/<old name>` for a skill the repo no longer has, so a visitor who acts on
   the listing gets a failed add. Installed copies are the other half of this and are covered by
   item 6; this is about new arrivals.

[DECISION 2026-09-27: **accepted, not mitigated, because nothing on this side can retire a row.**
Two things do help and both are free. **Do the whole batch at once**, so there is one cohort of dead
rows rather than a trickle — already the plan's shape. And **do not let the new names start cold**:
the README and every pointer under this repo's control name the new slug the day it lands, because
the new row begins at zero installs while the dead row keeps whatever ranking weight its count
carries. For scale, the eight renamed skills hold 274 installs between them today — plan-docs 42,
invoke-task-conventions 39, skill-authoring 38, python-conventions / polite-mcp-conventions /
db-defaults 37 each, python-testing-conventions and mcp-python-conventions 22 each — and all eight
successors start at zero.]

[Worth recording against the fear of losing ground: **both names being vacated are already dominated
on their own exact slug.** Measured 2026-09-27 — `python-conventions` has a 75-install rival
(`wyattowalsh/agents`) against 37 here, and `skill-authoring` has `grafana/skills` at **3,072**
against 38. These are not slots being surrendered; they are slots already lost, traded for slugs
nobody can shadow.]

[PITFALL: **the window is open only because nobody depends on these yet.** ~380 installs, no known
external dependents, no `displayName` and no `renames` map in the skill format — the two affordances
Anthropic shipped for plugins precisely because a slug change breaks installs. The same rename in a
year is a migration; today it is an edit.]

## The batch

1. **Settled and ready**: the seven marked names above; `plan-docs` → `plan-conveyor`.
2. **Nothing is open.** `research-library` stays, so the batch is eight renames, not nine, and the
   only cross-repo filed plan it needs is `plan-docs`' `plans.py` path.
3. Then one batch, in this order: rename directories and frontmatter, regenerate the README rows,
   `rg` each old name across the repo, update the five `skill-fitness` eval files, run the gate,
   push, reinstall, remove the old slugs locally, and file a plan for the global instructions file's
   `plans.py` path.
4. Re-run `names.py audit` afterwards — it should report no collisions for the renamed set, which is
   the check that the rename bought what it was meant to. Read it owner by owner, per the `check`
   pitfall above.
