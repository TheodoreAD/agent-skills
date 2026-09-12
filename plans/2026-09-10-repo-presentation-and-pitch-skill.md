---
status: idea
updated: 2026-09-12
---

# Making these repos legible to a stranger, and pitching them without writing slop

## Context

The ask, 2026-09-09: a method to make these repos "look awesome on GitHub — attractive, modern,
trustworthy", with elevator pitches "for repos and individual skills alike", so that social posts
and articles become possible once the work is solid. Deep research first, then a plan; a skill is
the suspected shape.

Six parallel research streams ran, preferring clones in `$RESEARCH_HOME` (149 repos now, ~25 cloned
for this) over page fetches: GitHub presentation mechanics, pitch craft, launch channels, visual
assets, article craft, and the agent-skills ecosystem. Everything below is sourced; where a claim is
a page fetch rather than a clone, or was not verified at all, it says so. Several load-bearing
numbers were re-checked here directly rather than taken from a report.

### What is already true, measured rather than assumed

**Adoption already happened, and it is invisible on the page.** `TheodoreAD/agent-skills` is
auto-indexed by skills.sh with no submission of any kind, and carries **~380 installs** across the
corpus — `session-harvest` 40, `plan-docs` 38, `invoke-task-conventions` 36, then a cluster at 34-35
(`skill-authoring`, `session-bash-audit`, `research-library`, `polite-mcp-conventions`,
`db-defaults`, `python-conventions`, `mcp-server-shipping`), `python-testing-conventions` and
`mcp-python-conventions` at 20, `python-refactor-audit` at 15. Verified directly against
`https://skills.sh/api/search?q=…&owner=theodoread` on 2026-09-09, independently of the research
agent that found it.

The same repo has **0 stars**, and was created 2026-08-26. So the problem is not discovery. Roughly
380 people installed something from a repo whose page shows no evidence anyone ever has.

**The cheapest surfaces are entirely untaken, across all 27 personal repos:** zero topics on every
one, zero homepage URLs, no custom social preview anywhere, and `repo-tasks` is public with an empty
description while its README opens with a perfectly good one-liner. All four sibling public READMEs
(`agent-skills`, `power-user-linux-setup`, `repo-tasks`, `scaffoldapy`) contain **zero images** — no
logo, no demo, no diagram.

**`agent-skills` fails the cross-surface rule it would adopt.** Its GitHub description (107 chars)
and its README opening line are different sentences.

**A ghost slug is already stranded.** `mcp-skill-shipping`, the pre-rename name of
`mcp-server-shipping`, still sits in the registry at 2 installs beside the live skill's 34. Verified
directly. Slugs are effectively immutable across this ecosystem, and
`anthropics/claude-plugins-official` documents the same for plugins ("renaming breaks their install
with a `plugin-not-found` error") and ships a `renames` map for the unavoidable case.

[PITFALL: **renaming a published skill is a breaking change, and nothing in this repo currently says
so.** The rename that produced the ghost was ordinary and correct authoring work — `skill-authoring`
even documents the split that caused it. The cost lands entirely outside the repo, which is why no
gate here could have caught it.]

### The constraint that shapes everything

**Three unrelated communities independently forbid what a naive version of this request would
produce.**

- Hacker News' guidelines: _"Don't post generated text or AI-edited text. HN is for conversation
  between humans."_ dang's Show HN guidance, edited 2026-03-28: _"Write your text by hand. Don't use
  an LLM to generate any of it (not even a tiny bit, including to edit or spruce it up)."_
- `matiassingers/awesome-readme`'s own admission criteria: _"The description should be written by a
  person. Not AI."_
- dev.to's AI-assisted article rules: disclosure is mandatory (`#ABotWroteThis`), and an AI-assisted
  article may **not** _"Promote any business, program, or course (including your own)"_ nor aim at
  _"building a personal brand… or gaining clout"_. Enforcement includes retroactive tagging and
  reduced visibility for repeat offenders.

Reddit is stricter still: of 307,543 subreddits crawled (arXiv 2410.11698), those with AI rules
doubled to 2,808 in 16 months and reached 17.1% among the largest 1%; **55.2% of those rules are
unqualified bans**, only 18.0% accept disclosure.

[DECISION: **the agent measures, extracts and checks; the human writes anything that goes to a
community venue.** This is not caution, it is the published rule on three of the four channels that
matter, and breaking it risks the account rather than the post. It inverts the obvious design — the
skill's job is to make writing cheap and verifiable, never to produce the prose.]

## What the research established

### 1. The one-liner is one artifact with three deploy targets, and there is a spec

`RichardLitt/standard-readme` (clone, `spec.md:76-89`) makes the README short description
**Required**, and mandates: no title of its own, on its own line, **under 120 characters**, **must
match the package manager's `description` field**, **must match GitHub's description**.

Compliance in the wild is 25-38%: of 17 well-known projects with an extractable README opener, **4
matched their GitHub description**; of 13 with a registry summary, **5 matched**. Flask, Vite and
`opencode` all carry materially different pitches on different surfaces; `Backlog.md` carries two
unrelated ones.

This is the seed of the design. The pitch is not three strings to draft, it is one string with a
consistency check — and the check is mechanical.

### 2. What a good one-liner looks like, with a control corpus

n=856 top developer-tool repos (three star bands, filtered to real tools). Median description **68
chars**, p25 43, p75 111, hard cap **350** (verified from the API error string). **80.0% are noun
phrases**, 8.1% verb-initial, 16.2% carry emoji, 39.6% contain "for", 27.8% repeat their own repo
name, 7.8% open with `<Name> is a…` at a median cost of 12 wasted characters.

The method is what makes this usable: **85,842 Debian package synopses** — a corpus governed by
written rules and machine-checked by lintian — served as the control, so every proposed check has a
measured false-positive rate.

| check                    | Debian (linted) | GitHub (unlinted) |
| ------------------------ | --------------- | ----------------- |
| ≥2 commas (feature list) | **1.01%**       | **27.0%**         |
| contains emoji           | 0.04%           | 16.2%             |
| starts with A/An/The     | 0.35%           | 26.8%             |
| opens `<Name> is a…`     | 0.02%           | 7.8%              |
| trailing period          | 0.9%            | 41.8%             |
| repeats own name         | 0.7%            | 27.8%             |
| over 80 chars            | 2.3%            | 38.3%             |

**Mechanically-enforced rules hold; prose-only rules leak.** Homebrew's ten-rule `desc` cop has
**zero violations across 8,595 shipped formulae**, while the same project's unlinted prose rule
against marketing adjectives leaks — `fast` 3.0%, `modern` 1.2%. That is the empirical case for
putting these in a script rather than in advice.

[DECISION: **gate only what the Debian control clears, warn on the rest.** Length >100, leading
article, `<Name> is a…`, URL, emoji, superlative, first person and stray whitespace all sit at
≤0.35% false positives and can gate. Length >80 (2.32%), repeats-own-name (1.15%) and ≥2 commas
(1.01%) warn only — they are the interesting signals and the noisy ones, which is exactly why they
must not block.]

[PITFALL: **two style rules must stay configurable, because real registries hold opposite
positions.** Trailing period: Obsidian **mandates** it (90.3% comply), Homebrew **forbids** it,
AppStream flags it, Debian omits it. Leading capital: AppStream requires it, Homebrew requires it
with a three-word allowlist, Debian deliberately lowercases 26.19% of synopses. A checker that picks
a side is wrong on half its targets.]

Reading-level scoring was **measured and rejected**: median Flesch 36 on the corpus and **12% score
below zero**, because a clear noun phrase built from technical nouns reads as "very difficult".

### 3. The honest ceiling on the whole project

Spearman correlation between heuristic-violation count and stars, across the same n=856: **ρ =
+0.056** — none. Median stars are flat across 0-5 violations. The sample is range-restricted to ≥30k
stars, so it cannot see effects below that.

[DECISION: **no artifact produced here may claim that a better pitch drives adoption.** The data
does not support it and the plan should not pretend otherwise. The defensible claims are narrower
and still worth the work: a stranger can tell what the thing is; the same pitch appears on every
surface; the trust signals a scanner reads are present; nothing is broken. Those are all checkable.
"More stars" is not.]

### 4. Trust is mostly mechanical, and partly theatre

Cheap and real, each verified against GitHub's own docs or Scorecard's source: a top-level `LICENSE`
(Scorecard's exact rule: 6/10 for the file, +3 top-level, +1 OSI-listed), a `SECURITY.md` carrying a
contact **and** a disclosure timeline (6/10, 3/10, 1/10 scoring is content-aware and reimplementable
in ~15 lines), `.github/ISSUE_TEMPLATE/` with valid frontmatter, `dependabot.yml`,
`permissions: contents: read` in workflows, topics, and a custom social preview.

Theatre for a solo maintainer: **an OpenSSF Scorecard badge**. Two of its checks are unreachable by
construction — Contributors needs "contributors from at least 3 different companies in the last 30
commits, each with at least 5 commits", and Code-Review deducts 7 points for a single unreviewed
human change. The composite then reads as a verdict on the project when it is a verdict on team
size. The OpenSSF Best Practices badge costs **67 criteria** at passing level alone.

`health_percentage` is a checklist, not a quality signal: `agent-skills` scores 42 — the same as
`standard-readme` and `awesome-readme`, the two repos that define README best practice.

**The trust surface that actually gates these skills is not the README.** An existing open plan,
`plans/2026-09-02-skill-risk-ratings-are-user-facing-and-unwatched.md`, owns it: skills.sh runs
three independent scanners and the `skills` CLI renders `Critical Risk` in bold red at the install
prompt, before a stranger confirms. That plan already holds the audit endpoint, the dispute
template, and the decision that the answer is total transparency rather than quieter wording. **This
plan must not re-cover any of it** — it should link to it and treat install-time presentation as
that plan's territory.

### 5. The visual layer, and one genuine dead end

- **`charmbracelet/vhs`** is the right shape: the `.tape` is committed source, re-rendered on
  demand, and its `.ascii` output is deterministic enough to be a golden file. The GIF is not —
  50fps default, and Charm do not commit their own example GIFs (they are ~0-byte LFS pointers).
- **Animated SVG beats GIF by roughly 35× and works on GitHub**, contradicting github/docs' own
  claim that "SVGs don't currently support inline scripting or animation" — that line is about the
  blob viewer. Header probe: `raw.githubusercontent.com` serves SVG with
  `default-src 'none'; style-src 'unsafe-inline'`, so CSS `@keyframes` run. `sharkdp/fd` ships a
  **127 KB animated terminal SVG** today, repo-relative and not camo-proxied, where `agg`'s
  equivalent demo GIF is **4.45 MB**.
- **The tool that made those SVGs is dead.** `svg-term-cli`'s last npm publish was 2018-01-21. No
  maintained replacement was found. This is the one real gap in the visual toolchain.
- **The social preview has no API.** CI can regenerate the PNG; a human uploads it in Settings,
  permanently. Spec: PNG/JPG/GIF, **under 1 MB**, at least 640×320, **1280×640 recommended** — note
  that is 2:1 while the generic OG convention is 1200×630, so the card is slightly cropped
  elsewhere.
- **Budgets, from GitHub's own numbers:** recommended repo file size 1 MB; github/docs' own image
  standard is 750-1000 px wide and **≤250 KB**; Camo 404s any proxied image over **5 MB**; README
  text truncates at 500 KiB.
- **Emoji in headings break anchors deterministically.** GitHub renders through comrak, whose
  anchorizer drops emoji (category So) but keeps the trailing space, so `## 🚀 Usage` becomes
  `#-usage`. Verified live on a popular generator's rendered README, where its own hand-written TOC
  links are dead.
- **`<picture>` with `prefers-color-scheme` is the only supported theme-aware image mechanism**, and
  the documented form needs all three children with `alt` on the `<img>`. `d2 --dark-theme`
  sidesteps it by emitting the media query inside one SVG.
- **Prior art for a brand file exists**: `posit-dev/brand-yml` — one `_brand.yml` with
  meta/logo(light,dark)/color palette and semantic roles/typography, with a **published JSON
  Schema**, consumed by Quarto and Shiny. Copy that shape rather than inventing one.
- **Static badges should be committed, not fetched** — standard-readme says so outright, and
  `badge-maker` (the renderer shields itself runs, 2 deps) produces them offline. Measured norm in
  the curated corpus is **3 badges**, median.
- **Icon-set licensing traps**: Simple Icons is CC0 on the repo but its own `DISCLAIMER.md` warns
  the icons are brand marks — copyright waived, **trademark not**. Twemoji's graphics are CC-BY 4.0,
  so attribution is mandatory and easy to breach silently. Lucide (ISC) and Noto Emoji (Apache-2.0
  for most image resources) are the clean options.

A 40-line stdlib asset linter written during the research found real defects immediately: VHS's own
two hero images and freeze's hero image **have no `alt` attribute at all**.

### 6. The ecosystem, and what it makes free

`skills.sh` requires **no submission** — it reads the GitHub tree, pulls every `SKILL.md`, and
parses the frontmatter `name`/`description`. That means **the `description` field is doing double
duty**: it is the agent's trigger text (owned by `skill-authoring`) _and_ the public catalogue copy.
The badge `https://skills.sh/b/TheodoreAD/agent-skills` is live, free, and renders the install count
— verified 200 with `content-type: image/svg+xml`.

The README pattern across 10 sampled high-star skill repos: **median 1 badge**, and in both
`anthropics/skills` and `vercel-labs/skills` that one badge is the skills.sh install count as the
literal first line. Install snippet within the first ~35 lines. A per-item table with the
description lifted verbatim from frontmatter.

**Pitching an individual skill is surface-dependent, and this was measured.** The _same_ Obsidian
plugins name "Obsidian" in **90%** of their GitHub repo descriptions but only **9.5%** in the plugin
registry, because the directory supplies the context a standalone repo cannot. Raycast shows the
same gradient within one product: extension descriptions say "Raycast" 20.3%, command descriptions
1.9%. Zed, whose registry index has no description field at all, sits at 38.9%.

[DECISION: **a per-skill `README.md` is not available here** — this repo's layout gate allows only
`references/`, `scripts/` and `evals/` inside a skill directory. The two compatible surfaces for
pitching one skill are the README catalogue row and the free skills.sh page at
`https://skills.sh/theodoread/agent-skills/<skill-id>`.]

Prior art worth reading and not adopting: `thatrebeccarae/claude-marketing` (56 skills, includes a
scored `github-readme` audit) — its frontmatter uses non-spec keys that this repo's
`test_only_known_frontmatter_keys` would reject outright. `todogroup/repolinter` is **archived**,
but its 26-rule default ruleset is the best free inventory of hygiene checks. `readme-md-generator`
has 11k stars and its last commit was 2019.

### 7. Content: the substrate already exists here

Measured on this repo: **200 of the last 200 commits carry a substantial message body** (the repo's
own convention), live plans carry **40 `[DECISION:]` and 27 `[PITFALL:]` tags**, the skills'
`references/` files carry **53 more**, and **40 retired plans** are recoverable from git history via
`plans.py archive`. Every one of those tags is already written in the form "X beat Y because Z" or
"this trap, confirmed by hitting it".

That maps directly onto the two archetypes that measured best: design-decision posts
(`"why we switched"` cleared 150 points 14.0% of the time, median 217) and measurement posts, whose
exemplars all put the number in the title. The best-performing coherent archetype overall was the
workflow post (`"how i use"`, 6.1%, **median 290**) — cheap to write because you already do the
thing.

A measured baseline for what unassisted developer prose looks like, across 267,370 words of
`simonw/til`: **15 em dashes total (0.06 per 1,000 words)**, **zero uses of "delve"**, median post
**323 words**, ~60% of lines inside code fences, 41% opening with a concrete "I was… and I noticed…"
line, 27% carrying any image, and **no H2 headings below ~500 words**.

The LLM-tell vocabulary has real backing (Wikipedia's `WP:AISIGNS`, whose inclusion rule requires
corroboration by a non-pop-science source; behind it sit Kobak et al. _Science Advances_ 2025,
Reinhart et al. _PNAS_ 2025, Liang et al. _Nature Human Behaviour_ 2025, Juzek & Ward ACL 2025).

[PITFALL: **the same source disproves the detector idea.** Human ability to distinguish LLM text is
**no better than chance** (Cheng et al. 2025); detectors have non-trivial error rates and fall to
paraphrasing; and the tells drift — the em-dash section now carries a banner questioning whether it
belongs under historical indicators, citing an Economist July 2026 finding that only Claude exceeded
professional-writer rates. So a _linter against a named list_ is defensible; a _detector_ is not,
and "this reads like AI" must never be an assertion the tooling makes.]

The honest prior art for one-source-many-surfaces is **COPE** (Create Once Publish Everywhere,
Jacobson/NPR 2009), whose load-bearing part is that content is stored as structured
presentation-free data and each destination renders it. Its test, which separates it from spam:
**does each artifact contain something the others do not?** Five paraphrases of one post is what
Google's spam policy names "scaled content abuse".

### 8. Distribution: the rules are per-channel, written, and mostly about restraint

**Show HN has a mechanical qualification test** (page, `news.ycombinator.com/showhn.html`): _"On
topic: things people can run on their computers or hold in their hands."_ A skills repo qualifies; a
blog post about it explicitly does not (_"Off topic: blog posts, sign-up pages, newsletters,
lists"_). Neither does a version bump — _"New features and upgrades ('Foo 1.3.1 is out') generally
aren't substantive enough to be Show HNs. A major overhaul is probably ok."_ And the cadence is
bounded by dang's own comment: a repost as Show HN needs a significantly different version, a link
to the previous thread, and _"should probably only happen once or twice a year — more starts to be
excessive."_

Two mechanisms worth knowing because they point opposite ways. **The second-chance pool is
sanctioned**: moderators re-float overlooked submissions, and _"If you see a submission that didn't
get attention and which you think is particularly good for HN, please tell us at hn@ycombinator.com…
It's fine if it's your own article."_ **Asking anyone to vote is bannable**: _"We penalize or ban
submissions, accounts, and sites"_. So the remedy for bad timing is one polite email, never a nudge
to anyone else.

Timing folklore has no first-party backing; the ranking formula does (_"divides points by a power of
the time since a story was submitted"_, plus flags and moderator action), and karma does not boost
rank. Treat time-of-day advice as unevidenced.

[PITFALL: **Reddit's live rules could not be read from this machine at all**, and that is a planning
constraint rather than a footnote. `reddit.com` and `api.reddit.com` return 403 here, WebSearch
refuses the domain, and mirrors sit behind JS challenges. The only route that worked was a dump API
whose sidebar text is from **2025-02**, roughly nineteen months stale. Anything a skill says about a
subreddit must be re-read on-site before acting, or fetched via OAuth (`PRAW`'s `subreddit.rules`
hits `r/{sub}/about/rules` and needs a registered script app). Also: **r/devtools has 23
subscribers** — not a channel, despite sounding like the obvious one.]

From that stale dump, the useful shape: r/opensource states the ratio rule in its own words
(_"Reddit recommends that <10% of your posts promote your content"_) and bans sensationalised
titles; r/programming says _"If there is no code in your link, it probably doesn't belong here"_;
**r/commandline explicitly welcomes programs "you've found or made yourself"** and is the
friendliest of the set. The 90/10 rule is a norm quoted by subreddits, not a citable sitewide policy
— cite the subreddit, not Reddit.

**Product Hunt is the highest-cost channel and the one with no evidence behind it.** Verified costs:
personal account only, tagline ≤60 chars, at least two gallery images at 1270×760, a 240×240
thumbnail under 3 MB, a day starting 12:01am PST, a written maker's first comment (70% of Product of
the Day winners had one), and a relaunch line of six months plus a significant update. Asking for
upvotes _"may trigger the algorithm to drop the product in the ranks or remove it from the homepage
entirely."_ Its own two pages disagree on the description limit (500 vs 260), so a script must check
the live form. Every "is it worth it for a dev tool" source found was PH's own marketing or SEO
blogspam — so ranking it below HN, one well-chosen subreddit and the newsletters is **judgement, and
should be labelled as such.**

**The "links kill reach on X" claim, resolved as far as it can be.** The open-sourced ranking code
contains no link penalty in the home timeline — zero occurrences of `Url` in `home-mixer`'s ranking
params; the only URL feature is a runtime-weighted term in the _search_ scorer whose sign is not in
the repo. The effect is real in observation: Buffer's analysis of **18.8M posts across 71k
accounts** (Aug 2025) found link posts at ~0% engagement for non-Premium accounts against ~0.40% for
text. Buffer itself stops at correlation. Report it that way — real effect, unproven mechanism, no
code evidence — and put the link in a reply.

**LinkedIn has no findable first-party statement**; link-in-first-comment is folklore and should be
labelled folklore. **Mastodon has no ranking feed at all**: featured hashtags, up to five pinned
posts and an opt-in directory are the entire discovery mechanism, so there is no timing game and no
link penalty. Bluesky was not verified.

**Newsletters are the cheapest real channel and the least polluted by folklore.** Changelog News
takes an open form and says outright _"Submitting your own work is also encouraged"_ while rejecting
tutorials and commercial products; Console.dev takes an email, wants developers as the primary user
and says _"We do not do sponsored reviews"_; PyCoder's Weekly has an open form that accepts
_"projects you are working on"_. **Hacker Newsletter has no submission form — it curates from HN**,
so a good Show HN feeds it automatically. Five minutes each, no ban risk.

**Awesome-list mechanics split in two.** Listing a _tool_ is a PR to the topical list in the house
format — `- [Name](url) - Objective description.`, capitalised, full stop, _"not a tagline or
marketing blurb"_. Getting a _list_ into the root repo is a much heavier gate (30 days old,
`awesome-lint` clean, CC0, review four other PRs, comment `unicorn`) and it states plainly: _"Fully
AI-generated pull requests are not accepted."_ The relevant list here,
`hesreallyhim/awesome-claude-code`, gates on **≥14 days old with continued commits OR ≥100 stars** —
this repo cleared the age half on 2026-09-09.

**Cross-posting, with the SEO caveat that matters.** dev.to's field is `canonical_url` (max 4 tags,
cover 1000×420); Medium's canonical cannot be added after publish. But Google states canonical
preference is _"a hint, not a rule"_ and specifically discourages it for syndication: _"The
canonical link element is not recommended for those who want to avoid duplication by syndication
partners… The most effective solution is for partners to block indexing of your content."_ Practical
consequence: publish on the own domain first, let it index, cross-post after — and accept that the
platform copy may still outrank you as the price of reach.

**A sustainable solo loop, assembled from what each channel actually permits:** tag a release →
CHANGELOG entry → one social post per release → newsletter submissions only on genuine news → an
occasional deep article on the own domain, cross-posted with canonical a few days later → HN only on
a genuinely major version, once or twice a year → Reddit only where the account already has history.
Everything above the HN line is repeatable; HN and Product Hunt are the two channels with a written
cooldown.

## Open questions

[NEEDS CLARIFICATION: **how many skills, and where is the boundary?** The ask contains four jobs —
repo presentation, pitch authoring, distribution, long-form content. This repo's own rule is "prefer
extending the skill that already owns the topic over adding a new one. Skill count is itself a
context tax", and that tax is currently **negative**: `fitness.py budget` measures the 14 existing
skills at 10,981 chars plus 8,656 the harness charges first, against an **8,000-char budget at a
200k-token window** — every skill is already demoted to name-only there. The answer must be
**measured, not argued**: `trigger.py split --proposal` scores how real requests distribute across a
proposed split, and `--dry-run` costs nothing. My prior is **two** skills, not four — one owning the
repo-as-storefront (README, metadata, assets, catalogue) and one owning outward-facing writing
(pitch ladder, post and article material) — but that is a hypothesis to test, not a decision.]

[NEEDS CLARIFICATION: **where does the pitch source-of-truth file live, and does it need to exist at
all?** standard-readme already defines the artifact and the three targets, so a separate file may be
redundant: the README's own short-description line could be the source, with the check comparing it
to GitHub and the registry. The argument for a file (`brand.yml`-shaped, per `posit-dev/brand-yml`)
is that the longer rungs — the 50-word abstract, the paragraph, the audience, the proof points —
have no home today and are re-derived every time. The argument against is that it is a new
convention every consumer of these skills would have to adopt. Decide by writing one for
`agent-skills` by hand first and seeing whether anything reads it.]

[DECISION: **adopt `.claude-plugin/marketplace.json`, and rewrite the stated principle to match** —
user's call, 2026-09-10, taken against the alternatives of holding the line or vendoring the skills
in a second repo. The surface is real and cheap: a skills-only repo qualifies for the official
Anthropic directory using `"strict": false` plus an explicit `skills` array, exactly as `amd/skills`
and `box/skills` do, and self-hosting one costs a single file. What makes this a decision rather
than a convenience is that `AGENTS.md` currently says the opposite — _"A vendor manifest —
`.claude-plugin/`, a harness-specific rules directory — does not belong in this repo even as a
convenience."_ The rule that replaces it has to be the one actually being followed: **the content
stays vendor-neutral, and exactly one vendor manifest is admitted as a distribution shim carrying no
instructions.** Amending the principle is part of the work, not a follow-up — a stated principle the
repo visibly violates is worse than either position held honestly, and this repo's README advertises
the vendor-neutral claim to strangers.]

[DEFERRED: **the manifest itself, and the `AGENTS.md` amendment.** The decision is recorded; neither
file was written, because the session that took the decision was asked to stop at the plan. Whoever
implements it owes three things in one change: the manifest, the amended principle, and a check that
the manifest's `skills` array cannot drift from `skills/` — the same
generate-from-the-repo's-own-code rule that governs the README catalogue table.]

[NEEDS CLARIFICATION: **ClawHub relicenses everything published to MIT-0**, which removes the
attribution requirement this repo's MIT licence carries. That is a licensing decision, not a
distribution one, and should be made deliberately rather than as a side effect of publishing.]

[NEEDS CLARIFICATION: **what replaces `svg-term-cli`?** Animated SVG is measurably the right format
(127 KB vs 4.45 MB) and nothing maintained produces it. Options: accept GIF and pay the bytes,
render an asciicast to SVG with a small script, or skip animation and ship stills from `freeze`. Not
worth solving until a demo is actually wanted.]

[DEFERRED: **applying any of this to the sibling repos.** `power-user-linux-setup`, `repo-tasks`,
`scaffoldapy` and `invoke-stubs` all have the same empty About box and the same absent visual layer,
but writing to another repo from this session is out. Each gets a filed plan once the skill exists
and has been piloted here.]

[DEFERRED: **installing the visual toolchain.** `vhs`, `freeze`, `d2`, `resvg`, `badge-maker`,
`ffmpeg`, `ttyd`, `gifsicle` and `pngquant` are all absent from this machine; only Graphviz is
present. Declaring them belongs in a different repo's `setup.toml`, so it is a filed plan there, not
work done here. A published skill must not require any of them — it declares them in `compatibility`
and degrades when absent.]

[UNVERIFIED: **that an animated SVG actually animates in a rendered README**, as opposed to in the
raw file. The CSP headers and `sharkdp/fd`'s live 127 KB `@keyframes` file both say yes, and
github/docs says no in a sentence that appears to be about a different surface. One person opening
that page settles it, and everything about choosing the demo format depends on the answer.]

[UNVERIFIED: **every subreddit rule quoted in §8 is nineteen months stale**, because live Reddit is
unreachable from this machine — 403 to the API, the domain refused to search, mirrors behind JS
challenges. Before any skill tells anyone to post to a subreddit, its rules must be re-read on-site
or through an OAuth app. Treat the r/opensource ratio and the r/commandline welcome as
probably-still-true rather than as facts.]

[UNVERIFIED: **whether Product Hunt is worth it for a tool of this kind.** Every source found was
Product Hunt's own marketing or SEO blogspam. The costs are measured and real; the return is not
evidenced either way. The plan ranks it last on judgement and says so rather than dressing it as a
finding.]

## Recommended direction

Rough, and deliberately sequenced so the cheap irreversible-to-get-wrong things happen after the
measurable ones.

1. **Settle the skill count by measuring it.** Draft candidate descriptions for the two-skill split
   above, run `trigger.py split --proposal … --dry-run` first, then for real against a case suite
   that includes should-not-trigger cases and cases meant for `skill-authoring`, `skill-fitness`,
   `session-harvest` and `plan-docs`. The boundary to defend is **audience**: `skill-authoring` owns
   the `description:` field as agent-facing trigger text; anything human-facing — tagline, catalogue
   row, social post, article — is new territory. That the same string serves both purposes on
   skills.sh is the sharpest reason to get the boundary explicit rather than plausible.

2. **Write the scripts before the prose**, per this repo's derivable rule. Three are clearly
   deterministic and each has a measured basis:
   - a **metadata and hygiene audit** — one `gh repo view --json` call plus
     `gh api …/community/profile`, checking description presence and length, the cross-surface
     identity against the README opener and the registry summary, topic count and syntax, social
     preview presence via `usesCustomOpenGraphImage`, top-level LICENSE, SECURITY.md content rules,
     issue templates via GraphQL (the REST slot false-negatives on folder-form templates), CI
     freshness. Take the rule inventory from archived `repolinter`'s ruleset.
   - a **pitch linter** with the Debian-calibrated gate/warn split, per-surface length budgets from
     the verified table (HN 80 hard, npm 255 silently truncated, PyPI 512, X 280 weighted with
     URL=23 and emoji=2, Homebrew 80, GitHub 350, Product Hunt tagline 60), and configurable
     house-style axes for trailing period and leading capital.
   - a **README asset linter** — alt text present and 40-150 chars, referenced images exist,
     `<picture>` pairs complete, image dimensions and byte budgets, anchor integrity by
     reimplementing comrak's anchorizer so emoji-broken TOC links are caught.

3. **Generate the skill catalogue table from frontmatter.** It is hand-maintained today and gated by
   `test_listed_in_readme`, so it is the clearest instance of this repo's own "generate from the
   repo's own code" rule — which puts it **in the quality gate, early**, with the output committed.
   Two working precedents to copy rather than invent: `github/awesome-copilot`'s `update-readme.mjs`
   and `hesreallyhim/awesome-claude-code`'s `generate_readme.py`.

4. **Pilot on `agent-skills` itself before the skill is shareable**, per the house rule that
   conventions are applied to one real working repo first. The concrete first pass: add topics, fix
   the description/README mismatch, add the skills.sh badge as the one badge, add a `SECURITY.md`
   that satisfies Scorecard's content rule, and add the `renaming-a-skill-strands-installs` rule to
   `skill-authoring` — which is owed regardless of whether any of the rest happens.

5. **Then the content half, as extraction rather than generation.** A candidate-finder over
   `[DECISION:]` and `[PITFALL:]` tags across live plans, retired plans and `references/`, plus
   commit bodies since the last published piece — Willison's weeknotes mechanic, where the script
   decides what is _new_ and a human decides what is interesting. Pair it with a prose linter (Vale
   with the Google/Microsoft packages, plus a custom rule from the `WP:AISIGNS` list) and the
   structural targets measured above. It never drafts the post.

6. **Distribution last, and as a checklist rather than a copywriter.** What is scriptable is narrow
   and genuinely useful: per-channel length budgets, the HN title lint (no uppercase runs, no
   exclamation marks, strip a trailing site name, require the `[video]`/`[pdf]` suffix), Product
   Hunt asset dimensions, the awesome-list entry format, dev.to front matter with `canonical_url`,
   and **cooldown bookkeeping** — last Show HN per project against the once-or-twice-a-year line,
   last Product Hunt launch against the six-month line, last HN submission per URL against the
   one-year repost line. Start with the newsletters, which are five minutes each and carry no ban
   risk, and treat Show HN as a once-a-year event that the whole rest of the loop feeds.

## Evidence kept in full, because no skill owns it yet

The sections above summarise; these are the measurements behind them. They sit in the plan rather
than in a skill's `references/` for one reason — **which skills this becomes is still open question
one**, so there is no `references/` directory to put them in without pre-deciding it. At retirement
they are routed like any other plan content, and that routing is the moment the question gets
answered. The pitch measurements are not here: `repo-pitch` exists, so they went to its
`references/measurements.md`.

Apparatus for all of it: `$RESEARCH_HOME/measurements/2026-09-12-pitch-and-skill-corpora/`.

### Article archetypes, measured rather than asserted

Method: the Hacker News Algolia API, `tags=story`, title-restricted phrase search, comparing each
phrase's total against the same query filtered to `points>150`. "Rate" is the share clearing 150
points; "med" is the median among those.

| archetype         | phrase                    | rate      | med     | n     |
| ----------------- | ------------------------- | --------- | ------- | ----- |
| workflow post     | `"how i use"`             | 6.1%      | **290** | 311   |
| design decision   | `"why we switched"`       | **14.0%** | 217     | 43    |
| design decision   | `"how we built"`          | 5.3%      | 197     | 655   |
| rewrite narrative | `"we rewrote"`            | 5.8%      | 257     | —     |
| postmortem        | `"postmortem"`            | 4.6%      | 262     | —     |
| incident          | `"outage"`                | 4.8%      | **360** | —     |
| release           | `"announcing"`            | 4.0%      | **365** | 4,281 |
| opinion           | `"stop using"`            | 5.0%      | 277     | —     |
| opinion           | `"you're doing it wrong"` | **2.4%**  | 258     | —     |
| measurement       | `"measured"`              | 3.9%      | 219     | —     |
| deep dive         | `"source code of"`        | 5.2%      | 262     | —     |
| tutorial          | `"getting started"`       | **1.2%**  | 262     | 3,134 |

**What the numbers cannot support**, stated because the temptation is to over-read them:
title-phrase matching catches non-articles (the `outage` bucket contains outage _news_), the search
is typo-tolerant so quoting is not exact, and no absolute base rate was obtainable. Treat every
figure as relative between archetypes and nothing more. The one clean anchor: **16,261 stories in
HN's entire index have over 500 points.**

Two readings that do hold. **The template is not the performance** — the most-used openings are the
worst-differentiated (4,281 "Announcing", 3,134 "Getting started"), while what outperforms carries a
specific claim: a number, a named swap, or a named tool plus a named person. And **the literal
phrasing of the contrarian genre is its worst form** — `"you're doing it wrong"` at 2.4% against
`"stop using"` at 5.0%. The archetype works; the posture does not.

### What unassisted developer prose actually looks like

Measured across **579 posts, 267,370 words** of a well-known developer's TIL corpus — chosen because
it is six years of continuous output by one person, so it is a baseline rather than a sample.

| measure                               | value                                     |
| ------------------------------------- | ----------------------------------------- |
| posts containing a fenced code block  | 88%                                       |
| median share of lines inside fences   | **60%** (mean 58%)                        |
| median prose before the first block   | **80 words** (p25 48, p75 134)            |
| median H2+ headings                   | **0** — sections appear above ~600 words  |
| posts with any image or diagram       | 27%                                       |
| median post length                    | **323 words** (p25 186, min 33)           |
| posts under 200 words                 | 28%                                       |
| first body line starts with "I "      | **41%**                                   |
| uses first person anywhere            | 96%                                       |
| **em dashes, total**                  | **15, in 7 posts — 0.06 per 1,000 words** |
| "AI vocabulary" hits (generous regex) | 11 total — 0.04 per 1,000 words           |
| occurrences of `delve`                | **zero**                                  |

The last three are the useful ones: they are what a linter should be calibrated against, and they
are why "sounds like AI" is not a claim any tool here should make.

### The LLM-tell list, and the honest limits on it

Source is Wikipedia's `WP:AISIGNS`, mirrored to
`$RESEARCH_HOME/pages/wikipedia-signs-of-ai-writing/`. It is usable because it has an inclusion rule
— a word enters only with corroboration from a reliable non-pop-science source — and behind it sit
Kobak et al. (_Science Advances_ 2025, 15M abstracts), Juzek & Ward (ACL 2025), Reinhart et al.
(_PNAS_ 2025) and Liang et al. (_Nature Human Behaviour_ 2025).

**Vocabulary**: _additionally_ (sentence-initial), _align with_, _boasts_, _bolstered_, _crucial_,
_deep dive_, _delve_, _emphasizing_, _enduring_, _enhance_, _fostering_, _garner_, _highlight_
(verb), _interplay_, _intricate_, _key_ (adjective), _landscape_ (abstract), _meticulous_,
_pivotal_, _realm_, _robust_, _showcase_, _tapestry_, _testament_, _underscore_ (verb), _valuable_,
_vibrant_. Density matters more than any single word — where there is one there are usually others.

**Structural tells, which are more mechanizable than the vocabulary**: the participial coda, an
"-ing" phrase bolted to a sentence end to manufacture significance
(`, creating a lively community
within its borders`) — a regex for `, [a-z]+ing` before a sentence
end catches it and it is rare in real developer prose; negative parallelism ("not just X, but also
Y"); the rule of three; vague attribution ("some critics argue"); and inline-header bullet lists.

[PITFALL: **the same source disproves the detector.** Human discrimination of LLM text is **no
better than chance** (Cheng et al. 2025); detectors have non-trivial error rates and fall to
paraphrasing; and the tells drift — the em-dash section now carries a banner questioning whether it
belongs under historical indicators, citing a July 2026 finding that only one model exceeded
professional-writer rates. The page also lists **ineffective indicators** explicitly: perfect
grammar, mixed register, "bland" prose, "fancy" prose, transition words, unsourced content. A linter
against a named list is defensible; "this reads like AI" is not a claim any tool may make.]

### Visual tooling, with maintenance judged from the repos

| tool                            | makes                                | verdict                                                                                          |
| ------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `charmbracelet/vhs`             | GIF/MP4/PNG from a committed `.tape` | **Adopt.** The only one whose demo _source_ is committed                                         |
| `charmbracelet/freeze`          | static SVG/PNG of code or ANSI       | **Adopt** for stills; deterministic, no `time.Now` anywhere                                      |
| `d2lang/d2`                     | SVG/PNG/PDF from `.d2`               | **Adopt.** Native Go rasterizer, no browser; `--dark-theme` emits the media query inside one SVG |
| Mermaid                         | rendered natively by GitHub          | **Adopt as default.** Zero build step, source in the README                                      |
| `asciinema` + `agg`             | cast → GIF                           | Adopt only if you want the cast format                                                           |
| `badge-maker`                   | shields SVG **offline**              | **Adopt** — the same renderer, two dependencies, no network call                                 |
| `resvg`                         | SVG → PNG, deterministic fonts       | **Adopt**; `--skip-system-fonts --use-font-file` is reproducible                                 |
| `terminalizer`                  | GIF                                  | **Dead.** No commits in 12 months; downloads Chromium to record                                  |
| `svg-term-cli`                  | animated SVG                         | **Dead since 2018 — and its output is the best format.** See below                               |
| `vercel/og-image`               | OG cards                             | **Archived** 2023. `satori` is alive but is a library with no CLI                                |
| `kefranabg/readme-md-generator` | README scaffold                      | **Dead.** 11k stars, last commit 2019 — the star count is a trap                                 |
| `todogroup/repolinter`          | repo hygiene                         | **Archived**, but its 26-rule default set is the best free inventory                             |

**Name-collision traps on PyPI**, each an unrelated project: `d2` is an async ORM, `svgo` a Rust SVG
library, `takumi` a 2018 package. Do not `uv tool install` any of them expecting the tool above.

**Licensing traps for a logo**: Simple Icons is CC0 on the repo but its own disclaimer warns the
icons are **brand marks** — copyright waived, trademark not. Twemoji's graphics are CC-BY 4.0, so
attribution is mandatory and easy to breach silently because the SVG carries no notice. Lucide (ISC)
and Noto Emoji (Apache-2.0 for most image resources) are the clean choices. What projects without a
designer actually ship is a typographic wordmark rendered once to a light/dark SVG pair.

**Budgets, from GitHub's own numbers**: recommended repo file size 1 MB; github/docs' own image
standard is 750–1000 px wide and **≤250 KB**; Camo 404s any proxied image over **5 MB**; README text
truncates at 500 KiB; the social preview is PNG/JPG/GIF **under 1 MB**, at least 640×320, 1280×640
recommended — which is 2:1 where the generic OG convention is 1.91:1, so the card is slightly
cropped elsewhere.

[UNVERIFIED: **the animated-SVG gap is the one real hole in the toolchain.** `sharkdp/fd` ships a
**127 KB** CSS-animated terminal SVG where the equivalent GIF is **4.45 MB** — a 35× difference —
and the CSP on `raw.githubusercontent.com` (`style-src 'unsafe-inline'`) allows the `@keyframes`
that make it work, contradicting github/docs' claim that SVGs do not animate. Nothing maintained
produces these. Someone should open that page and confirm it animates in a rendered README before
anything is built on it.]

## Anti-goals

- No badge wall. The measured norm is 3, the top skill repos carry 1.
- No Scorecard or Best-Practices badge on a solo repo — theatre, and two checks are structurally
  unreachable.
- No "more stars" claim anywhere, per ρ = +0.056.
- No AI-written text posted to HN, an awesome-list submission, or dev.to as promotion.
- No detector that asserts text "reads like AI".
- No emoji in headings — it silently breaks anchors.
- No skill that requires this machine's toolchain to be useful.
- **Never ask anyone to upvote, anywhere.** HN penalises or bans submissions, accounts and sites for
  it; Product Hunt drops rank or removes from the homepage and can suspend the account. This is the
  only item on this list whose cost is the account rather than the post, and no tooling here should
  make it easy to get near.
- No Show HN for a version bump, and no more than one or two a year.
- No posting to a subreddit on the strength of a cached rules copy.
