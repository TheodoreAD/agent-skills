# Where every number in this skill came from

Measured 2026-09-09. The apparatus is parked at
`$RESEARCH_HOME/measurements/2026-09-12-pitch-and-skill-corpora/pitch-research/` (`analyze.py`,
`calibrate.py`, `dump.tsv`); the raw API dumps were ~19 MB and deliberately not kept, because the
scripts re-derive them from public endpoints.

## The method, which is the transferable part

**A threshold is taste until it has a false-positive rate.** The rules in `SKILL.md` were run twice:
once over a corpus of what people actually write, and once over a corpus that is already governed by
written rules and machine-checked. The second run is the only thing that says whether a rule may
_block_.

| corpus                      | n          | what it is                                              |
| --------------------------- | ---------- | ------------------------------------------------------- |
| GitHub developer-tool repos | **856**    | what people write when nothing checks them              |
| Debian package synopses     | **85,842** | governed by Debian's synopsis rules, checked by lintian |

The GitHub sample was drawn from three star bands (`stars:>=100000`, `50000..99999`, `30000..49999`)
→ 1,191 repos deduped, then filtered to real developer tools: a description must exist; the primary
language must not be a documentation or notebook language; the repo name and description must not
match a curation regex (`awesome|roadmap|tutorial|course|cheat|handbook|…`); and non-Latin
characters must be under 5%, because character counts are not comparable across scripts. That leaves
856 repos and 49.6M combined stars.

The Debian corpus was parsed from this machine's own `/var/lib/apt/lists/*_Packages` — 40 source
files, 85,842 unique synopses. Nothing was fetched.

**Why a second corpus rather than a bigger first one.** A rule that fires often on GitHub tells you
only that the habit is common. The same rule fired on a _linted_ corpus tells you it is a matter of
style rather than a defect — because a corpus under a rule which still contains the pattern is a
corpus whose maintainers decided the pattern was fine. That is the whole basis of the gate/warn
split, and there is no way to get it from one sample.

**The gap does the work, not the threshold.** Every rule lands at or below 0.35% or at or above
1.01%, nothing in between, so 0.35% sits in empty space and moving it slightly reclassifies nothing.
`tests/unit/test_pitch.py` asserts that emptiness, so a future rule landing in the gap fails the
suite instead of quietly inheriting a number nobody can defend.

## The distributions

Length in characters: min 3 · p10 29 · **p25 43** · **p50 68** · **p75 111** · p90 167 · p95 223 ·
max 350 · mean 86.5. In words: p25 7 · **p50 10** · p75 16 · max 53. Topics per repo: p25 4 · **p50
8** · p75 14 · max 20 · **13.8% have none at all**.

Histogram: 0–39 21.6% · 40–59 21.0% · 60–79 17.9% · 80–99 10.9% · 100–119 7.1% · 120–149 7.7% ·
150–199 6.7% · 200–249 4.2% · 250–350 2.9%. So ≤60 chars is 43.6%, ≤100 is 71.6%, >200 is 6.9%.

Form: bare noun phrase 63.7% · article + noun 26.8% · imperative verb 7.7% · gerund 1.5% ·
third-person verb 0.4%. **Verb-initial totals 8.1%**; hand-checking 30 random items from the
bare-noun bucket found 2 misclassified, so the true rate is ~8–10%. By the finite-verb test, **80.0%
are noun phrases and 20.0% are sentences.**

| feature                                | GitHub (n=856)                                 |
| -------------------------------------- | ---------------------------------------------- |
| contains "for"                         | 39.6%                                          |
| …where the object of "for" is a person | **2.5%** (9 of 353 — the rest name a platform) |
| names an audience noun                 | 11.3%                                          |
| says "your"                            | 10.9%                                          |
| names a category noun                  | 53.4%                                          |
| emoji                                  | **16.2%** (13.4% Unicode + 2.8% shortcode)     |
| names a competitor or analogy          | **2.1%** (10 of 18 are "alternative to X")     |
| repeats its own name                   | 27.8% strict / 39.8% any name token            |
| opens `<Name> is a…`                   | 7.8%, median cost **12 characters**            |
| starts with A/An/The                   | 26.8%                                          |
| ends with a period                     | 41.8%                                          |
| superlative or hype word               | 5.3%                                           |
| "framework/library for building"       | 1.8%                                           |
| first person                           | 2.0%                                           |
| names its mechanism                    | 4.4%                                           |

### The control, side by side

|                        | Debian (linted) | GitHub (unlinted) |
| ---------------------- | --------------- | ----------------- |
| median / p90 chars     | **49** / 66     | **68** / 167      |
| over 80 chars          | 2.3%            | 38.3%             |
| verb-initial           | 2.6%            | 8.1%              |
| starts with an article | **0.3%**        | 26.8%             |
| ends with a period     | **0.9%**        | 41.8%             |
| repeats own name       | **0.7%**        | 27.8%             |
| emoji                  | **0.01%**       | 16.2%             |
| any comma              | 4.4%            | 39.0%             |
| **two or more commas** | **1.01%**       | **27.0%**         |

## Two negative results, kept because they bound what this skill may claim

**Length does not vary with success.** 30k–50k★ median 67 · 50k–100k★ median 69 · 100k+★ median 72.

**Violations do not predict stars.** Spearman ρ between violation count and stars = **+0.056**
(n=856). Median stars are flat across 0–5 violations: 43.0k / 42.6k / 46.3k / 47.1k / 43.1k / 52.1k.
The sample is range-restricted to ≥30k stars, so it cannot see effects below that — but within it,
there is nothing. No artifact of this skill may imply otherwise.

**Reading level was measured and rejected**, not omitted: median Flesch 36 across the corpus, and
**12% score below zero**, because a clear noun phrase built from technical nouns reads as "very
difficult". It measures readability, never quality, and the published guidance on AI-detection
explicitly lists "fancy or academic prose" as an _ineffective_ indicator.

## Platform limits, and how each was established

Verified from the enforcing code wherever the code is public, because documentation and
implementation disagreed twice in this research.

| surface               | limit            | established from                                                                                                                                                                   |
| --------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub description    | **350**          | API error string; of 2,160 repos sampled, 2 exceed it, both legacy                                                                                                                 |
| standard-readme       | 120              | the spec's own Short Description section                                                                                                                                           |
| **Show HN title**     | **80, exactly**  | `news.arc` `title-limit*`; the test is `len>`, so 80 passes though the message says "less than 80". 1,000 titles sampled: 39 sit at 80, none above. `Show HN:` costs 9, leaving 71 |
| npm `description`     | **255**          | registry API — **truncated silently, mid-word, no error**                                                                                                                          |
| PyPI `Summary`        | 512              | warehouse `_LENGTH_LIMITS`; the only length-limited metadata field                                                                                                                 |
| X                     | 280 **weighted** | `twitter/twitter-text` `config/v3.json`: non-Latin costs 2, any URL a flat 23                                                                                                      |
| Homebrew `desc`       | 80               | `MAX_DESC_LENGTH` in the desc cop                                                                                                                                                  |
| Product Hunt tagline  | 60               | its launch guide; its help centre says 260 for the description — check the live form                                                                                               |
| AppStream `<summary>` | warn above 90    | `summary-too-long` validator tag                                                                                                                                                   |
| crates.io             | no cap observed  | 500 top crates, max seen 639                                                                                                                                                       |

## The mechanical-versus-prose finding

**Homebrew's ten-rule description cop has zero violations across 8,595 shipped formulae.** The same
project's unlinted prose rule — "vendors' descriptions tend to be filled with generic adjectives
such as 'modern' and 'lightweight' … meaningless marketing fluff which must be deleted" — leaks:
`fast` 3.0%, `modern` 1.2%, `simple` 1.5%.

That is the argument for putting a rule in code rather than in a paragraph, measured on one project
that did both.

## The gallery

Real descriptions, kept because a rule list does not teach the shape and a worked example does.
Drawn from `dump.tsv` in the parked apparatus.

**Clean against every rule here:**

| description                                                                   | chars | why it works                                                        |
| ----------------------------------------------------------------------------- | ----: | ------------------------------------------------------------------- |
| `Command-line JSON processor` — jq                                            |    27 | three words, complete                                               |
| `A cat(1) clone with wings.` — bat                                            |    26 | analogy to a tool the reader already has; "wings" carries the delta |
| `Lint your Python architecture.` — import-linter                              |    30 | verb-initial and right, because the verb _is_ the product           |
| `The Kubernetes Package Manager` — helm                                       |    30 | category plus substrate; the definite article earns its place       |
| `Presentation Slides for Developers` — slidev                                 |    34 | the rare case where the audience is named                           |
| `Get your documents ready for gen AI` — docling                               |    35 | outcome not mechanism; "your" does the audience work                |
| `macOS system monitor in your menu bar` — stats                               |    37 | category plus exactly where it lives                                |
| `Display and control your Android device` — scrcpy                            |    39 | two verbs, one object, no adjectives at all                         |
| `Data validation using Python type hints` — pydantic                          |    39 | mechanism _is_ the differentiator here, so naming it is correct     |
| `Lightweight coding agent that runs in your terminal` — codex                 |    51 | category plus the one difference that matters                       |
| `Developer-first error tracking and performance monitoring` — sentry          |    57 | a positioning adjective doing real work                             |
| `Send push notifications to your phone or desktop using PUT/POST` — ntfy      |    63 | names the interface, because here the interface is the pitch        |
| `An extremely fast Python package and project manager, written in Rust.` — uv |    70 | family template, and identical on GitHub and PyPI                   |

**Instructive failures:**

| description                                                                                                                                                         | the lesson                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `Stable Diffusion web UI`                                                                                                                                           | the repo name respaced; zero information added                                                   |
| `Agents that use the browser.` — browser-use                                                                                                                        | same problem, sentence-shaped                                                                    |
| `tmux source code`                                                                                                                                                  | describes the _repository_, not the tool; 16 characters all wasted                               |
| `This is the repo for Vue 2. For Vue 3, go to …`                                                                                                                    | the field repurposed as a redirect notice                                                        |
| `⚡ Serverless Framework – Effortlessly build apps that auto-scale, incur zero costs when idle…` (176)                                                              | **worst scoring, 9 flags**: emoji, own name, superlative, 3 commas, trailing period, over length |
| `Gin is a high-performance HTTP web framework written in Go. It provides a Martini-like API but with significantly better performance—up to 40 times faster…` (253) | three sentences and a benchmark in a field that renders as one line                              |
| `Ansible is a radically simple IT automation platform that makes your applications…` (338)                                                                          | near the 350 ceiling; a README paragraph in the wrong field                                      |
| `🤗 Transformers: the model-definition framework for state-of-the-art machine learning models…` (172)                                                               | restates the name, four commas, trailing space, superlative                                      |
| `A Python tool to visualize + enforce dependencies… 🌎 Open source 🐍 Installable via pip…` (249) — tach                                                            | emoji-bulleted feature list; its own README says it in 78 chars                                  |

**Failure modes with their measured frequency**, so effort goes where the problem is:

- **A feature list instead of a pitch** — ≥2 commas, 27.0% against Debian's 1.01%. The sharpest
  single discriminator found.
- **The self-restating opener**, `<Name> is a…` — 7.8%, median 12 characters spent repeating what
  the interface renders directly above.
- **The description that is the repo name respaced** — no clean count; obvious on sight.
- **"Framework for building `<abstraction>`"** — only 1.8%, and its users are React Native, Flask,
  Vue, Hugo, Nest. It fails only when the object is generic: "for building rich text editors" is
  fine, "for building modern applications" is not.
- **Buzzword stack** — 3+ generic adjectives is 2.5%, 4+ is 0.1%. A long-tail problem, not a
  top-repo one.
- **Mechanism where the outcome belongs** — 4.4%, and legitimate when the mechanism is the
  differentiator (pydantic, uv). Vite carries the outcome on GitHub and the mechanism on npm.
- **Marketing register** — superlatives 5.3%. On Hacker News specifically, a moderator's standing
  advice is to "drop any language that sounds like marketing or sales… that is an instant turnoff".

## Naming a parent product is surface-dependent

The same Obsidian plugins name "Obsidian" in **90%** of their GitHub repo descriptions (n=58) and
**9.5%** in the plugin registry (n=7,449) — the directory supplies context a standalone repo cannot.
Raycast shows the same gradient inside one product: extension descriptions 20.3%, command
descriptions **1.9%**, and Raycast documents why (the subtitle carries the service name). Zed, whose
registry index has no description field at all, sits at 38.9%.

[PITFALL: **a registry can append text to what the author wrote, and the raw read then measures the
registry.** Obsidian's index appends a 62-character review disclaimer to 65.2% of entries. The
uncorrected numbers were p50 134 chars and 65.9% naming Obsidian; stripped, the author-written text
is p50 **81** and **9.5%**. Both figures look plausible and only one is about authors.]

Registry rules for sub-components, where they exist at all: Homebrew linted (10 rules, 0 violations,
p50 44 chars); Obsidian documented but unlinted (p50 81, **mandates** a trailing period, 90.3%
comply); VS Code has no `description` validator in `vsce` at all and truncates server-side near 300;
Raycast and Zed neither require nor lint one. **Unlinted fields drift**: Obsidian's oldest 500
entries are p50 55 chars with 3% self-referential, its newest 500 are p50 **98** with **15%**.
