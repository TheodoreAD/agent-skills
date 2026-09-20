---
status: idea
updated: 2026-09-20
source_repo: github.com-personal/power-user-linux-setup
source_session: 81f41ac7-aec7-45e2-8d84-aad642024a13.jsonl
source_moment: 2026-09-13T16:14:15Z
source_plan: plans/2026-09-02-project-imagery-prompts.md
---

# A process for a repo's images: what it needs, the prompts, and which image was kept

## Context

Asked 2026-09-13, from a power-user-linux-setup session that had just rewritten that repo's image
prompts for NightCafe and audited the licences of the tool logos it wanted to show. In the user's
words: _"think of an agentic solution to creating the prompts and linking the planned images to the
ones we are happy with, which i would give manually to an agent, within some process. maybe a skill
that could govern how we create visual assets for our repos? … we need something easy to use and
that can track the images and the needs we define for each repo, like having a hero, logo, banner
and so on, i'm not familiar with the marketing terminology"_.

**Read this with `plans/2026-09-10-repo-presentation-and-pitch-skill.md`, which it extends and must
not re-decide.** That plan owns how a repo presents itself to a stranger; its §5 already holds the
visual layer's measured specs and tooling, and its first open question is how many skills the whole
storefront becomes. This plan proposes the **image-making process** inside that storefront — the
part the user named — and is input to that plan's skill-count measurement, not a competing answer to
it. `repo-pitch` is the one skill that plan has produced so far, and it is the text half of the same
job.

### Three repos have already met this problem separately

- **power-user-linux-setup**, `plans/2026-09-02-project-imagery-prompts.md`: three visual
  directions, about twenty prompts, a measured palette, NightCafe-specific prompt rules, and a
  licence audit in which **only four marks** clear a zero-risk bar (Git, tmux, Tux, the Go gopher),
  out of its twenty original candidates and eleven more installed tools it checked, while fifteen of
  the original twenty's owners require written permission.
- **scaffoldapy**, `plans/2026-08-19-logo-banner.md`: a README banner, seven candidate prompts, one
  NightCafe batch rejected on 2026-08-21 — and, in its own words, _"No specific failure mode written
  down yet"_, followed by a note that writing down what was wrong _"turns the next prompt iteration
  into a correction instead of a re-roll"_.
- **agent-skills**, the presentation plan above: social preview spec, README image budgets,
  `brand.yml` as prior art, icon-set licensing traps.

Each re-derived the same things — surface sizes, the no-text rule, generator quirks, what may be
shown of other people's marks, where the finished file goes. **None records which generated image
was kept, from which prompt, on which model, or why the others were rejected.** That record is what
the user asked for, and it is the one thing no existing plan or skill holds.

### What the design inherits rather than decides

- **Generation stays manual.** The user generates on NightCafe, which has no public API according to
  the scaffoldapy plan's research of 2026-08-21, and hands the files to an agent. API generators
  that plan names (fal.ai, Replicate) would make generation scriptable; nothing here should depend
  on that.
- **Generator rules** — NightCafe gives a negative-prompt field only to Stable Diffusion-family
  models, transfers the rights in an output to its maker, and keeps a perpetual licence to display
  creations. Source: the power-user-linux-setup plan's "Running the prompts on NightCafe".
- **Third-party marks** — the tier rule and its table in that plan's "Which marks may be used". The
  same tools recur across these repos, so the table is reusable nearly as it stands.
- **Surface specs** — the presentation plan's §5: social preview 1280×640 under 1 MB with no upload
  API, README images at most 250 KB, Camo's 5 MB ceiling, `<picture>` as the only theme-aware image
  mechanism.
- **Anything that goes to a community venue as text is written by a person** — the presentation
  plan's decision. Whether the same venues have rules about AI-generated _images_ was not
  researched.

### Prior art

- **`posit-dev/brand-yml`** (clone): one file for identity — `logo` as small/medium/large, each
  optionally light/dark, `color.palette`, typography — with a published JSON Schema and real
  consumers. It covers identity and nothing about needs, candidates or provenance. Copy its shape
  for identity rather than inventing one; the presentation plan already says so. **Whose it is,
  asked 2026-09-18:** it is Posit's — the company behind RStudio — published on PyPI as `brand-yml`,
  with the stated goal of "unified, branded theming for all of Posit's open source tools". **Quarto
  reads it natively from v1.6**, Shiny for Python and Shiny for R (through `bslib`) theme from it.
  So it is a real community artifact with consumers rather than a proposal. **It is YAML, and that
  settles how much of it to take**: this family ships stdlib-only skills and the standard library
  has no YAML reader, so the file itself cannot be parsed without a dependency. Take its
  **vocabulary** — logo sizes, light/dark pairs, palette — into the TOML tracker if identity is ever
  needed, and leave the file to the tools that already read it.
- **`thatrebeccarae/claude-marketing`'s `social-preview` skill** (clone): renders one surface, the
  1280×640 card, from HTML templates, with an audit mode. One surface, no candidates, no record.
- **`JimLiu/baoyu-skills`' `baoyu-cover-image`** (clone): writes each prompt to its own file, with
  frontmatter for palette, rendering and reference images. **Prompt-as-a-file is the idea worth
  taking.** Generation there is API-driven, and nothing records which output was accepted.
- **Favicon generators** turn one source image into the standard icon set. A step in the process,
  not a tracker.
- Two web searches for a tool tracking per-repo image needs with provenance found prompt libraries
  and generators, and no tracker. **That negative is search-summary depth**; the global rule asks
  for a real prior-art pass before a new skill is finalised, and this is not one yet. Done
  2026-09-18 over the local clones — see "The prior-art pass, done over clones" below, which
  sustains the negative and adds one finding the searches missed.

## Design sketch

### 1. A vocabulary of surfaces, in plain words

The user does not know the marketing names, and should not have to. The skill carries a catalogue
that maps what a person says to a surface with a spec, and says which tool makes it — because
several surfaces must never be generated at all.

| surface          | what someone might call it       | what it is                                       | made by                        |
| ---------------- | -------------------------------- | ------------------------------------------------ | ------------------------------ |
| `social-preview` | link preview, the card           | the picture shown when a repo link is pasted     | generated or rendered          |
| `readme-banner`  | banner, header image             | the wide image at the top of a README            | generated                      |
| `docs-hero`      | hero, the big picture            | the large image at the top of a docs front page  | generated                      |
| `logomark`       | logo, icon, symbol               | the project's symbol, without its name           | generated to explore, then SVG |
| `wordmark`       | the name in nice letters         | the project name set in type                     | real type, never generated     |
| `favicon`        | tab icon                         | the tiny icon in a browser tab                   | derived from the logomark      |
| `card-icons`     | card pictures                    | small illustrations on feature or use-case cards | generated, as one sheet        |
| `demo`           | screenshot, recording, GIF       | the real tool, running                           | captured, never generated      |
| `diagram`        | diagram, chart of how it works   | a mechanism                                      | mermaid or d2, never generated |
| `listing`        | Product Hunt gallery, store icon | the images a directory asks for when you submit  | per directory                  |

Specs come from the presentation plan where it measured them, and are marked unverified where it did
not.

**Where a reader learns this vocabulary, asked 2026-09-20.** The skill should point at worked
examples rather than define the words twice:

- **`matiassingers/awesome-readme`** (already in the research library) is the best match for these
  surfaces, because **every entry names the visual elements it is being praised for** — "project
  banner with informative badges", "project logo, clear description, screenshot", "banner with
  GIFs", "screenshot gallery of the docs site". The vocabulary arrives attached to a real page a
  reader can open, which is what a glossary cannot do.
- **`metatags.io`** renders any URL's link card as Google, Facebook, X, LinkedIn, Pinterest and
  Slack each show it — free, no signup, verified 2026-09-20. One paste is a faster explanation of
  `social-preview` and `og:image` than any prose, and pasting one of this family's own repos shows
  the default grey card that the whole surface exists to replace.
- **The logo words are three and worth stating once**: a **logomark** is the symbol alone, a
  **wordmark** is the name set in type, and a **combination mark** locks the two together. Only the
  first is generated here; the catalogue already says a wordmark is real type and never generated.

### 1b. The same surfaces in pixels, each number with where it came from

Asked for directly 2026-09-18. **Every row says whether the number is verified, a convention, or a
guess**, because three of them were wrong in the first draft of this plan and one contradicted a
primary source.

| surface          | where it renders                             | pixels                                                                                                                                        | source                                                                                    |
| ---------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `social-preview` | the card when a repo link is pasted anywhere | **1280×640**, minimum 640×320, **under 1 MB**, PNG/JPG/GIF                                                                                    | **verified** at GitHub's own docs page, 2026-09-18                                        |
| site `og:image`  | the card when a _docs site_ link is pasted   | **1200×630** (1.91:1)                                                                                                                         | convention, not a protocol rule — `og:image` mandates no size                             |
| `readme-banner`  | top of `README.md`, on github.com            | ship 1280–1600 wide, display at ~900 via `<img width>`; ≤250 KB                                                                               | **no official spec exists**; the README column is ~894 px, search-summary depth           |
| `docs-hero`      | top of the docs front page                   | 1600–2000 wide                                                                                                                                | guess — depends on a site generator nobody has chosen                                     |
| `logomark`       | README, docs nav, favicon source             | SVG, square; 512 PNG fallback                                                                                                                 | convention                                                                                |
| `favicon`        | browser tab, home-screen icon                | `.ico` packing **16, 24, 32, 48, 64**; PNG **16, 32, 48**; optional SVG; `apple-touch-icon.png` **180**; `android-chrome` **192** and **512** | **verified** from `itgalaxy/favicons` source, `master@44c80b6`                            |
| `card-icons`     | feature or use-case cards in README or docs  | square, 256 or 512 each, generated as one sheet                                                                                               | design choice, unverified                                                                 |
| `demo`           | README, docs page                            | 1000–1200 wide                                                                                                                                | width is convention; **the format is measured** — animated SVG 127 KB against GIF 4.45 MB |
| `diagram`        | README, docs page                            | none — mermaid or d2 text, rendered natively by GitHub                                                                                        | **verified**: GitHub renders mermaid in markdown                                          |
| `listing`        | a directory's own submission form            | per directory, and not researched                                                                                                             | unverified                                                                                |

[PITFALL: **the search summary contradicted the primary source on the one number that matters
most.** An SEO page put GitHub's social preview at a 1.91:1 aspect ratio, which is the Open Graph
convention; GitHub's own documentation says 1280×640, which is 2:1. The two surfaces genuinely take
different shapes, and a skill that states one number for both would be wrong on one of them every
time.]

### 1c. Resolutions: generate once per aspect ratio, derive every surface

Asked 2026-09-18. **The pilot repo's brief already fixes this, and the skill should carry the rule
rather than restate its numbers**, since the numbers are per repo and the rule is not:

- **Generate at an aspect ratio, never at a surface.** That brief's table keeps a `generate at`
  column separate from `final size` — 16:9 for heroes and slot grids, 21:9 for wide heroes, 1:1 for
  marks and for the card sheet, and the 2:1 social card cropped from a 16:9 generation. Four
  generations cover ten surfaces.
- **One sheet, then slice.** A four-icon card set is generated as a single two-by-two 1:1 sheet and
  cut into 4 × 800×800, because four separate generations drift in angle, scale and lighting.
- **Upscale before cropping, never after**, and only where a generation came out under its final
  size.

The sizes that brief plans for: hero and slot grid **1920×1080**, wide hero **2520×1080**, drift
banner **2400×800**, social card **1280×640**, card set **4 × 800×800** from a 1600×1600 sheet, mark
square.

**Those pixel sizes have never been checked against the byte budget, and the budget binds first.**
GitHub's own image standard, which the presentation plan measured, is **750–1000 px wide and ≤250
KB** — and a 1920×1080 photorealistic render is nowhere near 250 KB as a PNG. Two consequences the
design has to state rather than leave to whoever exports:

- **Display width and asset width are different numbers.** Display is 750–1000 px, so a crisp asset
  on a 2× screen is 1500–2000 px wide, held to the display size in markup with `<img width>`. The
  brief's 1920 is already right for that. What it is not is a PNG.
- **Format is forced, and differently per surface.** README and docs images have to be JPEG or WebP
  to reach 250 KB at those dimensions. The **social preview cannot be WebP** — GitHub takes PNG, JPG
  or GIF only, under 1 MB, which is comfortable at 1280×640 as JPEG. A `<picture>` light/dark pair
  doubles the bytes of whichever surface uses it.

[NEEDS CLARIFICATION: **the export step is unowned.** Something has to take a 1920-wide master to a
≤250 KB deliverable, and this machine has no Pillow, no ImageMagick and no `cwebp` (verified
2026-09-18). Options: declare export a manual step beside generation, declare an optional dependency
and check for it, or accept larger files and drop the budget. The byte check in §6 catches a
violation either way, and that is the part that must not be optional.]

[UNVERIFIED: **what resolutions NightCafe actually offers, and at what credit cost.** The brief's
own `[UNVERIFIED:]` says its 21:9 and its model list are search-summary depth, unchecked in the app.
Generation is manual, so this is the user's to confirm once — and it decides whether the upscale
step is needed at all.]

### 1d. The one image tool, researched 2026-09-18

**No PyPI wrapper ships either candidate's CLI**, checked against PyPI's own metadata rather than a
search summary, so the house preference for `uv-tool` cannot be satisfied and `apt` is the install
method. `magick` on PyPI is a dead 2013-era binding, one release, no wheels; `imagemagick-binary`,
`imagemagick-cli`, `vips`, `oxipng` and `cwebp` do not exist there at all; `wand` and `pyvips` are
**bindings that need the real library installed**, and `pyvips-binary` ships the shared library in 8
MB wheels but no command-line tool. A Python binding is also the wrong shape here for a second
reason: these skills are stdlib-only, so the script must **shell out to a CLI** rather than import
anything.

What this machine's distro actually offers, read from `apt-cache policy`:

| package                  | version    | gives                                                          |
| ------------------------ | ---------- | -------------------------------------------------------------- |
| `imagemagick`            | **6.9.12** | `convert`, `identify`, `mogrify`, `montage` — **not `magick`** |
| `libvips-tools`          | 8.15.1     | `vips`, `vipsthumbnail`, `vipsheader`                          |
| `webp`                   | 1.3.2      | `cwebp`, `dwebp` — exact byte targeting via `-size`            |
| `libimage-exiftool-perl` | 12.76      | the metadata specialist, including copy-across-conversion      |
| `potrace`                | 1.16       | raster → SVG tracing                                           |

[DECISION: **ImageMagick is the single tool, and the version is part of the decision.** One binary
covers every operation this design needs — resize, crop to an aspect, slice the 2×2 card sheet,
convert with a byte target (`-define webp:target-size`), and read a PNG's text chunks at intake with
`identify -verbose`. It is also the tool with by far the deepest presence in model training data,
which matters for the improvised command the script does not own.

**The trap is that Ubuntu ships ImageMagick 6, where `magick` does not exist.** Every command an
agent writes from memory is IM7-shaped (`magick input.png -resize …`), and on this machine that is a
command-not-found. So: prefer installing IM7 where PULSE can, and either way the skill's script
**detects which binary is present and spells its own commands accordingly**, rather than trusting
either habit.]

**What one tool does not cover, stated so "single tool" is not read as more than it is.** Raster
manipulation is ImageMagick's; **vectorising a logomark is `potrace`'s** (the catalogue already says
a mark is generated to explore and then redrawn as SVG), and **a terminal demo is `vhs`'s**. Those
are different jobs, not missing features.

[NEEDS CLARIFICATION: **whether `exiftool` is a second install or an avoided one.** It matters only
if a credential has to survive export — see the metadata pitfall below. `cwebp -metadata all` is the
alternative and comes with the `webp` package; doing neither is also a position, as long as it is
taken deliberately.]

[PITFALL: **the export step destroys exactly the provenance this design plans to read.** A
PNG-to-WebP or JPEG conversion drops the PNG `tEXt` chunk, which is where SD-family pipelines write
the prompt, seed and sampler — recent ImageMagick preserves ICC, EXIF and XMP, and a PNG text chunk
is none of those. C2PA is not in that preserved list either, and nothing in ImageMagick's
documentation claims to carry a manifest across a conversion. **So intake must read the metadata
before anything converts the file**, and the record has to hold what was read rather than a promise
that the file still holds it.]

### 1e. Where the exploratory images live

[DECISION: **a content-addressed store under `$XDG_DATA_HOME`, with an env override, following this
family's own pattern.** User's first pick was the `.local` convention and it is the right one.
`$REPO_ASSETS_HOME`, defaulting to `$XDG_DATA_HOME/repo-assets` (so `~/.local/share/repo-assets`),
laid out as `<host>--<owner>--<repo>/<sha256>.<ext>` — the same entry-naming rule `research-library`
already uses, so two stores on one machine do not invent two conventions.

**Data rather than state or cache**, deliberately: `~/.local/state` is for what a tool can lose
without harm and `~/.cache` is for what anything may delete, while these files are **the referents
of a committed record** — the manifest stores a hash, and a missing blob turns a rejection with a
reason into a rejection with a dangling pointer. Hash-named because the same image handed over twice
is then recognisably the same image, which is the cheapest possible defence against a multi-day
handoff.]

**Superseded the same day by a better answer, kept because the reasoning still bounds it.** Asked
2026-09-18: _"do we agree that nightcafe stays the store for all of the images and we just download
them when processing and deciding if we actually keep them?"_

[DECISION: **the generator is the archive; the local directory is a cache.** The bytes of a rejected
candidate have no value the repo needs — the **reason** is the valuable part and it is committed —
and the generator already holds every image it made, beside the prompt that made it. So the manifest
records the **URL, the hash and the reason**, a candidate is downloaded when somebody is deciding,
and the local copy may be dropped the moment the slot is settled. That dissolves the retention
question above rather than answering it: nothing accumulates, and nothing that matters is only in a
directory no backup covers.

**This reclassifies the directory**: something re-fetchable is a cache by definition, so
`$XDG_CACHE_HOME/repo-assets` is the correct home and `$XDG_DATA_HOME` was the wrong reading. The
layout and the hash-naming stand. **`$REPO_ASSETS_HOME` still overrides**, and is what a machine
without durable access to the generator would point at a real directory.]

**The property it rests on was checked 2026-09-20 and holds** — see §1g: the image host serves a
plain unauthenticated request, and a three-year-old creation is still there with its prompt. The
caution the earlier draft carried, that an expiring URL would fail silently months later, is
answered for this generator and stays true as a rule for any other. **What is not covered by that
evidence** is an account that lapses or is closed, which no external check can test, and which is
the reason the accepted image and the prompt files are committed to the repo regardless.

[PITFALL: **a re-download that does not match the recorded hash is the expected case, not
corruption.** If the generator re-encodes, resizes or re-compresses what it serves, the same
creation yields a different sha256. So a mismatch means "this is a re-encoding of that candidate",
and the tool must say that rather than reporting a tampered file — while a **matching** hash is what
makes a re-fetched reject provably the one the reason was written about.]

**What this does not move.** The accepted image is committed to the repo, the prompt files are
committed to the repo, and the metadata read at intake is written into the manifest, because all
three have to survive the generator entirely. Relying on it for the rejects is a small, bounded
dependency; relying on it for the kept work would not be.

**One property of the archive worth naming**, since the design now leans on it: NightCafe holds a
perpetual, royalty-free licence to show creations on its own site and social media, recorded in the
pilot repo's own decision. So the archive's operator may display its contents — which is already
true of every image generated there, and is not a new cost of using it as the store, but it does
mean an unreleased mark is not private while it sits there.

### 1f. Handing over a URL instead of a file

Asked 2026-09-18: the user wants to paste one or more URLs and have the skill do the rest, rather
than download and move files by hand. The shape, stdlib-only:

`assets.py fetch <url>… --slot <name>` — download with a timeout and a size cap, **sniff the magic
bytes rather than trusting the extension or the `Content-Type`**, compute the sha256, store it in
the blob store above under that name, and **skip the write when the hash is already there**, so
pasting the same URL twice is free rather than duplicated. Then, in the same pass and **before any
conversion**, read the intake metadata and append a `tried` row carrying the source URL, the fetch
timestamp, and whatever the file itself yielded — prompt, seed, model — leaving `verdict` and `why`
empty, because those are the two fields no download can supply.

### 1g. Measured against the real generator, 2026-09-20

The user supplied three of their own creations — one recent, two three years old — and every open
question about NightCafe above is now answered from the artifacts rather than from a search summary.

**Durability holds, which is what the archive decision rests on.** A three-year-old creation page
still resolves and still shows its prompt (_"A stat in a forest. A creek is in the center.
Impressionist."_) and its model (DreamShaper v8), alongside the user's own report of creations
surviving more than a year untouched.

**Two hosts, two access rules, and this decides how the fetch command is written.**

| host                       | what it serves                       | plain `curl`                                         |
| -------------------------- | ------------------------------------ | ---------------------------------------------------- |
| `images.nightcafe.studio`  | the image bytes, no auth, no cookie  | **200** — stdlib `urllib` is enough                  |
| `creator.nightcafe.studio` | the creation page and its parameters | **403** on both old URLs — blocked as a naive client |

So the script downloads bytes happily and **must not plan to scrape the page**; a browser-shaped
fetch reads it, a stdlib one does not.

[DECISION: **the file carries no provenance, so the page is the only metadata source and the batch
record is mandatory.** Walked the delivered JPEG byte by byte: `FF D8 FF DB` — straight from
start-of-image to a quantisation table, **no EXIF, no XMP, no JUMBF/C2PA, no text segment**.
Requesting the untransformed original with `?tr=orig-true` returns a larger file (627,995 bytes
against 310,931) whose only additional segments are a JFIF header and a comment reading
`CREATOR: gd-jpeg v1.0 (using IJG JPEG v6…)` — **the delivered file is a GD re-encode**, which is
exactly where any generator metadata was lost.

This kills the branch §1c and the prior-art section were hoping for. Prompt, seed and model are
**not** readable from the download for this generator, so the manifest cannot derive them, and the
**batch has to be recorded when the prompt is handed out** rather than reconstructed at triage. The
`seed` field stays in the schema because other generators write it; for NightCafe it will be empty,
since the creation page does not show a seed either.]

**What the creation page does show, publicly:** the full prompt, the model name ("Muse Image" on the
recent one), the aspect ratio, an `Initial Resolution: High` label with no pixel figure, and a
relative date. Not the seed.

[PITFALL: **the same creation has two byte streams, and the hash depends on which URL you used.**
Default delivery is 310,931 bytes; `?tr=orig-true` is 627,995 — **both 1600×1600**. The `tr=` query
is an image-CDN transform, so a recorded hash is a hash _of one URL form_. The manifest must record
which form it fetched, or a later re-download will disagree with a hash that was never wrong.]

### 1h. 1600 is enough, and the oversized targets were for a site that does not exist

Asked 2026-09-20, after the 1600 ceiling turned up: can the generator go higher, and if that is
hard, should the sizes come down instead. **The sizes come down.**

**What the generator offers, from its own pages rather than a summary.** The FAQ states the cap
plainly — _"The resolution limits are to do with the amount of memory required by the different
algorithms. There's no paid tier that will enable higher resolutions than what's displayed in the
options"_ — and an `Enhance` button upscales after generation, with the Clarity Upscaler advertising
_"up to 4x"_. **No pixel figures or credit costs are published anywhere public**; they are visible
only inside the app, so the exact options remain the user's to read. What that establishes is enough
for the decision: a path to 3200 or 6400 exists and costs credits, and nothing suggests a bigger
native generation.

**The arithmetic says none of that is needed.** Every surface that renders today fits inside 1600 on
the long edge, with no upscale at all:

| surface        | from a 1600 source                                 | upscale needed |
| -------------- | -------------------------------------------------- | -------------- |
| social preview | crop 1600×800 (2:1), scale to 1280×640             | no             |
| README banner  | crop to 3:1 or 21:9, ship ≤1600 wide, display ~900 | no             |
| card icons     | a 1600×1600 two-by-two sheet slices to 4 × 800×800 | no, exactly    |
| logomark       | square, redrawn as SVG anyway                      | no             |
| favicon set    | every size from 16 to 512, down-scaled             | no             |

**The three targets that do not fit — the 1920×1080 hero, the 2520×1080 wide hero and the 2400×800
banner — are all docs-site surfaces, and no repo in this family has a docs site.** They were sized
for a site that has never been built, against a generator nobody had measured.

[DECISION: **cut the size table to what renders, and defer the rest to the day a site exists.** The
shipped catalogue states 1600 as the working source size, and a docs hero is marked as needing
either an upscale pass or a lower target **at the time somebody builds the site** — not now, and not
as a blocker. This is the cheap half of the user's own framing: the effort has to stay
proportionate, and the expensive half of the table was buying resolution for pages that do not
exist.]

[PITFALL: **1600×1600 is what came back even as the original, and the size table assumes more.** For
a 1:1 creation at the account's "High" resolution, both URL forms are 1600 on the long edge — so a
1920×1080 hero, a 2520×1080 wide hero and a 2400×800 banner **cannot be filled from a source like
this without upscaling**, and a 21:9 crop of a 1600 square is 1600×686. What a 16:9 generation
returns, and what the account's upscale step produces, is the one thing still unmeasured — and it is
now the pilot's first question rather than the metadata dump, which is answered.]

### 2. One file per repo that says what it needs and what it has

The tracking the user asked for. Shape below; four things about it were decided 2026-09-18.

[DECISION: **its own file, never a section inside `pyproject.toml` or `setup.toml`.** User's call.
Those files belong to the packaging and machine-setup tools that read them, and a tracker that
borrows one inherits its lifecycle, its schema arguments and its audience for no gain.]

[DECISION: **it lives at the repo root**, in the shape of `mkdocs.yml` and every other root-level
project config. User's call, and one measured argument reinforces it: a site generator publishes
what sits under its source directory — `mkdocs` walks `docs_dir` and nothing else — so a tracker
placed in `docs/` would be **copied into the built site** unless something excluded it. A progress
file is not site content, and the root is where it cannot accidentally become some.]

[DECISION: **it tracks the process and is never an input to rendering.** User's call. The images are
referenced by ordinary markdown links in `README.md` and in whatever the site's source turns out to
be, so both surfaces work with the file absent, deleted or never written. That keeps it an
**auditable record rather than a dependency**, and means a repo can adopt or drop the process
without touching a single image reference.]

[DECISION: **TOML, and the cost is named rather than discovered.** User's call, for the reason that
`tomllib` is in the standard library from 3.11 and this family's skills ship stdlib-only. **The
catch, verified here: `tomllib` reads and cannot write** — it has `load`/`loads` and no `dump`. The
skill writes this file on every accept and every reject, so TOML means a **small hand-rolled writer
for this one schema** (strings, integers, string arrays, arrays of tables, one nested table),
somewhere near a hundred lines with tests, and not a general TOML serializer. The alternative that
needs no writer is JSON, which costs comments and hand-editability — the two things this file is
most likely to want. Take the writer.]

Illustrative shape:

```toml
brand = "_brand.yml" # identity, in brand-yml's shape
brief = "plans/2026-09-02-project-imagery-prompts.md"

[slots.social-preview]
surface = "social-preview"
purpose = "the card every link to the repo renders"
status = "choosing" # wanted → prompted → choosing → accepted → published
path = "docs/assets/social-preview.png"

[[slots.social-preview.tried]]
image = "sha256:…" # the file itself lives outside the repo
prompt = "prompts/social-preview-c3.md"
model = "Flux PRO v1.1"
generated = "2026-09-14"
verdict = "rejected"
why = "lens flare along the top edge; reads as stock art"

[slots.social-preview.accepted]
image = "sha256:…"
prompt = "prompts/social-preview-c3.md"
model = "Flux PRO v1.1"
size = "1280x640"
bytes = 412000
credits = ["Git Logo by Jason Long is licensed under CC BY 3.0"]
pending = ["upload in GitHub Settings: the social preview has no API"]
```

**Four fields the sketch is missing, found 2026-09-18 by asking what the design does not cover.**
Each is a hole in the schema rather than a preference:

- **`alt` per slot, and it is content rather than decoration.** Every image needs alt text, a human
  writes it, and nothing in the sketch has a place to put it — while the presentation plan's own
  40-line linter found that VHS's two hero images and freeze's hero have **no `alt` attribute at
  all**, which is the state this design would otherwise reproduce with a tracker on top.
- **`path` cannot be a single string once `<picture>` is involved.** Theme-aware images need a light
  file and a dark file for one surface, and `<picture>` is the only supported mechanism. The slot
  needs a pair, and the byte budget applies to each half.
- **`seed` belongs beside `model`.** A prompt and a model do not reproduce an image; the seed does,
  and SD-family pipelines write it into the same text chunk the intake step already reads. Recording
  the two that do not reproduce anything, while dropping the one that does, would be an odd record
  to keep on purpose.
- **The accepted file needs a stable name, not its hash.** `README.md` and the site link to a path,
  so a hash-named file in the repo churns every link on every re-accept. Hash-named blobs belong in
  the exploratory store; the repo gets `docs/assets/social-preview.png` and the manifest carries the
  hash.

**Rejections are recorded with a reason, because that is what turns a re-roll into a correction** —
scaffoldapy's plan states the lesson and its rejected batch is the counterexample. **`published` is
checkable**: a README or docs reference for most surfaces, and for the social preview the
presentation plan found `usesCustomOpenGraphImage` in `gh repo view --json`.

### 2b. Where the kept images live, and why the corpus cannot answer it

**There is no convention to follow, measured rather than assumed.** Across the research library's
143 clones with a README, 43 reference a local image file, and they scatter: `docs/` 12, `assets/`
6, the repo root 4, `images/` 4, `.github/` 3, `img/` 3, then singletons (`public/`, `artwork/`,
`screenshots/`, `.docs/`). So imitation gives no answer, and the decision has to come from a
constraint instead.

**The constraint is that one path has to satisfy two renderers.** GitHub renders `README.md` from
the repo, resolving a relative path against the repo tree. A site generator serves only what sits
under its own source root — read from `mkdocs`'s source, `get_files()` is
`os.walk(config['docs_dir'])` and nothing outside it exists as far as the build is concerned. So:

- **images under the site's source directory** (`docs/assets/` for a `docs/`-rooted site) satisfy
  both with one copy and no configuration: the site serves them, and `README.md` reaches them at
  `docs/assets/…` because that path is real in the repo.
- **images at a root-level `assets/`** satisfy GitHub and are invisible to the site until something
  copies them in. One detail makes this cheaper than it sounds: mkdocs walks with
  `followlinks=True`, so `docs/assets` as a **symlink** to `../assets` is served correctly, and
  costs one line rather than a build step.
- `.github/assets/` keeps images out of both the package and the site, and is the option 3 of 43
  repos took. It is also a **vendor directory**, which this family admits only as a distribution
  shim, so it loses on the repo's own stated principle rather than on ergonomics.

[DECISION: **the rule, not the directory, because the site's source is not chosen yet.** Kept images
go **under whatever directory will be the site's source root**, and `README.md` links them through
the path that exists in the repo. Where no site exists or the choice is still open, that is
`docs/assets/` — the plurality of the corpus, the zero-config answer for a `docs/`-rooted generator,
and recoverable by symlink if the site later roots somewhere else. The tracker records `path` per
slot, so a move is a recorded change rather than a hunt.]

[NEEDS CLARIFICATION: **the rejects are a different question and stay open.** They are not repo
assets and should not be binary churn in git, which is what the sketch above means by storing a
hash. The candidates remain `plans.py attach --local` (already copies outside every repo and records
a sha256, but binds to a plan that will retire), an XDG data directory keyed by repo, or keeping
only the reason. The pilot decides, because it is the first run that will actually hold rejects.]

### 3. Prompts are files

One file per prompt, frontmatter naming its slot, direction, generator and aspect ratio, body
holding the **assembled, paste-ready text**. The power-user-linux-setup rewrite composes each prompt
from three parts — the prompt, a direction's look, a shared tail — which is right for authoring and
tedious to paste twenty times; the file carries the joined text. A prompt that produced an accepted
image stays beside it permanently, which is what that plan already asks: _"a prompt that produced a
committed image is the only way that image can be regenerated or varied consistently later"_. Plans
retire; the prompt file must not retire with them.

### 4. The handoff: the user gives images to the agent

What the user does, in plain language: _"these three are for the link card, from C3 on Flux; keep
the second — the first has lens flare and the third is cramped"_. What the agent does, through the
script:

- maps "the link card" to `social-preview` through the catalogue;
- **accepts** one image: records its hash, dimensions, bytes, prompt and model, crops or scales it
  to the surface's spec when a tool is available, copies it to the slot's path, and prints what is
  still owed — credit lines, a manual upload;
- **rejects** the others with the user's reason, and keeps the files outside the repo;
- refuses an image that breaks the surface's budget, or composites a mark outside the clear tier.

### 5. One status view across every repo

`status --all` over every repo with a manifest, in the shape of `plans.py list --scope family`: each
slot's state, and the manual steps nobody has done. This is "track the needs we define for each
repo".

**The state has to survive days and several sessions, because generating is a human errand run at
human pace.** Asked 2026-09-18: _"where does the status of the image generation progress live? it
might take a few days to generate all those images"_. The manifest is the answer and already holds
it — it is committed, so the per-slot ladder `wanted → prompted → choosing → accepted → published`
and the `pending` list of manual steps are ordinary repo state that no session owns and none can
lose. Nothing perishable is involved, which is the whole reason the record is a file in the repo
rather than a conversation.

Two things a multi-day run exposes that the sketch above does not cover, both about the **waiting**
half rather than the finished half:

- **Nothing surfaces a stalled slot.** `status --all` answers when it is asked, and a slot sitting
  at `prompted` for a week is invisible until someone thinks to ask. The machine that surfaces
  dangling work in these repos is `session-harvest`'s sweep — unpushed commits, CI, plans filed and
  not taken — and a half-finished slot is the same class of thing with no check looking at it. The
  cheap version is the sweep reading a manifest where one exists and naming slots that have not
  moved; that is a `session-harvest` change, so it is a filing rather than something this skill can
  do to itself.
- **An untriaged batch has no slot to belong to, and that is the part that decays.** Generate thirty
  images over three days from six prompts and the downloads are thirty filenames that say nothing.
  The manifest binds a file to a slot **at triage**, so between generating and handing over, the
  association lives only in the user's memory — exactly what a few days erodes, and exactly what the
  handoff sentence _"these three are for the link card, from C3 on Flux"_ is reconstructing by hand.

**This is what makes the embedded-metadata question load-bearing rather than a nicety.** If a
download carries its prompt text, routing is mechanical at any distance in time: match the embedded
prompt against the prompt files and every image knows its own slot, however long the folder sat. If
it does not, the manifest has to record the batch **when the prompt is handed out** —
`status =
"prompted"`, the prompt file, the expected count, the date — so that a later handoff has
something to attach candidates to rather than a memory to interrogate.

[NEEDS CLARIFICATION: **does a stalled slot deserve a prompt, and from what?** The options are the
sweep reading manifests (one more thing for `session-harvest` to own, and it already declines to
carry other skills' checks), `status --all` growing an age column so the answer is there whenever it
is asked, or nothing at all on the argument that image work is not urgent and a nagging check is the
alarm-fatigue shape this family keeps rejecting. Decide after the pilot, which is the first run that
will actually have a slot sit for days.]

### 6. Checks a gate can run

Accepted files exist and match their recorded hash; sizes and bytes are within the surface's spec;
every composited mark has its credit line and sits in the clear tier. **Alt text, `<picture>` pairs
and image budgets in the README are already the presentation plan's asset linter** — reuse it rather
than write a second one.

### 7. Generators and marks as references, not code

A `references/` file per generator (NightCafe first, from the power-user-linux-setup plan) and one
for third-party marks (that plan's tier rule and table). The skill stays vendor-neutral and gains a
generator by gaining a file.

## Evidence

- The ask: session `81f41ac7-aec7-45e2-8d84-aad642024a13.jsonl`, user turn at 2026-09-13T16:14:15Z,
  containing _"i'm not familiar with the marketing terminology"_.
- The logo audit it builds on: power-user-linux-setup commit `7d555ce`, "four of the twenty tool
  logos clear a zero-licence-risk bar".
- The NightCafe prompt rules: power-user-linux-setup commit `437e347`.
- The unrecorded rejected batch: `scaffoldapy/plans/2026-08-19-logo-banner.md`, "Progress so far".

## The prior-art pass, done over clones 2026-09-18

**The negative holds, and it is now a measurement rather than a search summary.** Scanned every
`SKILL.md` in the research library's clones — the four skill corpora (`anthropics/skills`,
`anthropics/claude-plugins-official` and `-community`, `github/awesome-copilot`,
`VoltAgent/awesome-agent-skills`, `agentskills/agentskills`, `vercel-labs/skills`,
`softaworks/agent-toolkit`, `phuryn/pm-skills`, `JimLiu/baoyu-skills`,
`thatrebeccarae/claude-marketing`, `openai/codex`'s bundled samples) for files naming a visual
surface **and** a tracking word. **27 files match, and none of them tracks a repo's image needs or
records which candidate was kept.**

The two that come closest both confirm the gap from the inside:

- **`openai/codex`'s `imagegen` sample** is the most developed image skill in the corpus, and it
  states the opposite policy outright: _"Discarded variants do not need to be kept unless
  requested."_ It is built for generating and iterating, and the reject is garbage to it. That is
  the sentence this plan exists to disagree with.
- **`softaworks/agent-toolkit`'s `gepetto`** matched on `manifest` and is a false positive — a
  section-manifest planning skill with no image in it. Recorded so the next pass does not re-read
  it.

**What the searches missed: the file the user hands over may already carry half the record.** Major
generators now embed a C2PA manifest — tool, model and timestamp, cryptographically signed — and
Stable-Diffusion-family pipelines write the prompt, negative prompt, seed, sampler and model into a
PNG text chunk. NightCafe runs SD-family models. If that holds for the user's own downloads, then
`model`, `generated` and possibly `prompt` in the `[[slots.*.tried]]` block are **read from the
file** rather than typed at handoff, and what the user actually has to supply is the one thing no
file can carry: **why this one and not that one.**

**Answered 2026-09-20, and the answer is none** — see §1g. A real download was walked segment by
segment: no EXIF, no XMP, no C2PA, no text chunk, and a comment identifying the file as a GD
re-encode. **So the paragraph above is wrong about this generator and right as a general claim**,
and the distinction matters for the skill: other pipelines do write a prompt into the file, and the
intake reader is still worth having, but nothing in this design may _depend_ on it.

The machine fact that shaped the check stands: **no `exiftool`, no `c2patool` and no Pillow are
installed here**, so a stdlib reader is the only zero-install route. It was enough — walking JPEG
segments and PNG chunks needs `struct` and nothing else, which is also the argument for keeping that
reader in the skill rather than reaching for a dependency the moment metadata is mentioned.

[DEFERRED: **the disclosure question has a regulatory half the plan did not have.** EU AI Act
Article 50 and California SB 942 both push machine-readable disclosure of AI-generated content, and
C2PA is the layer the ecosystem settled on — Facebook, Instagram, LinkedIn and YouTube read it and
label on it. Whether any of that binds a personal repo's README banner is a different question and
almost certainly no. What it changes here is the default direction: **stripping the credential is
now the action that needs a reason**, where the plan had treated embedding one as the step needing
justification. Search-summary depth, flagged as such, and not a rule until someone reads the actual
text of either law.]

## Open questions

[DECISION: **an assets skill of its own, measured 2026-09-18 rather than argued.**
`trigger.py split` over 19 cases at 3 runs each — the suite is
`skills/repo-pitch/evals/storefront-boundary.json`, which ships and can be re-run — scored a
proposed `repo-assets` against the whole installed set with `repo-pitch` still present. **18 of 19
cases passed; `repo-assets` took 21 of its 24 runs at precision 1.0, and the boundary with
`repo-pitch` was never once contested.** Not a single false positive anywhere: every one of the four
should-not-trigger cases returned nothing, including the two written as traps — "resize this
screenshot to 800px so I can attach it to a bug report", which a greedy image description would
take, and "write the release notes for v2.1", which a greedy storefront one would.
`session-bash-audit`, `plan-docs` and `session-harvest` each held their own case 3 of 3, so the new
description costs no contention elsewhere.

The drafted description, kept here because the proposal file was scratch:

> Use when a repo needs an image and somebody has to decide what it needs, what to prompt for, or
> which generated candidate to keep — a README banner, a social or link-preview card, a docs hero, a
> logomark or favicon, feature-card icons, a demo screenshot or recording. Use when handing
> generated images to an agent ('here are three for the link card, keep the second'), when asking
> what a repo is still missing, what size or byte budget a surface takes, what may legally be shown
> of another project's logo, or which prompt and model produced the image already in use. Tracks
> each surface's state and keeps the reason a candidate was rejected, so the next attempt is a
> correction rather than a re-roll. Does not generate images, and does not write the repo's words.]

**What the measurement does not settle**, stated because the aggregate reads as more than it is: it
cut `repo-pitch` against `repo-assets`, which is two of the four jobs the presentation plan's open
question 1 lists. Whether distribution and long-form content are a third skill, or belong to the
pitch one, is untested and still that plan's question.

[NEEDS CLARIFICATION: **two situations the description names and still loses.** "Make a favicon set
from the logo" went to nothing in 1 run of 3, and "add a screenshot of the CLI running to the
README" in 2 of 3 — the only failing case. Both are named in the description, so this is not an
omission: the request reads as a mechanical conversion rather than as a question about what the repo
shows, and no skill looks necessary. Worth one `candidate`-mode re-measure of a wording that names
the _act_ ("derive the favicon set", "capture a terminal demo for the README") rather than the
artifact, before either is treated as out of scope. Selection is non-deterministic and this is 3
runs, so a 1-of-3 miss is weak evidence on its own.]

[NEEDS CLARIFICATION: **the manifest's format and path.** TOML matches this family (`setup.toml`,
`pyproject.toml`); YAML sits beside `_brand.yml`, which has a schema and consumers. The path could
be `assets/`, `docs/assets/` or `.github/assets/`. Decide by writing one by hand for the pilot repo
and seeing what reads it.]

[NEEDS CLARIFICATION: **where tried-but-not-kept images live.** Not in git: they are binary churn
and not assets. Candidates are `plans.py attach --local`, which already copies a file outside every
repo and records a sha256 but ties it to a plan that will retire; an XDG data directory keyed by
repo; or not keeping them at all and recording only the reason. The reason is the valuable part
either way.]

[UNVERIFIED: **that NightCafe has no public API.** From the scaffoldapy plan, 2026-08-21, which
cites a third-party roundup. The design assumes manual generation regardless, so this changes only
whether a later API step is possible on the user's current generator.]

**The favicon set's sizes, read from a maintained generator's source 2026-09-18** —
`itgalaxy/favicons`, `master@44c80b6`, `src/platforms/`. The guess above them was close and wrong in
three details, which is the argument for reading a generator rather than a summary:

| file                    | sizes it emits                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `favicon.ico`           | **16, 24, 32, 48, 64 packed into the one file**                                       |
| `favicon-*.png`         | 16, 32, **48**                                                                        |
| `favicon.svg`           | optional, source rendered at 1024                                                     |
| `apple-touch-icon*.png` | 57, 60, 72, 76, 114, 120, 144, 152, 167, 180, 1024; the unsuffixed default is **180** |
| `android-chrome-*.png`  | 36, 48, 72, 96, 144, 192, 256, 384, 512                                               |

The guessed set named one ICO rather than five packed sizes, dropped 48 from the base PNGs, and read
180 as a standalone entry rather than as the Apple default among eleven. The catalogue should state
the base row — `favicon.ico`, 16/32/48 PNG, an optional SVG, `apple-touch-icon.png` at 180 — and
name the generator as the source for anything wider, rather than restating a list that will drift.

[DEFERRED: **disclosure of AI-generated images.** Whether to embed IPTC's digital-source-type
metadata, and whether any venue in the presentation plan's §8 has rules for generated images as
opposed to generated text, was not researched.]

## Is this worth doing at all, scoped 2026-09-20

The user's own framing, and it deserves a number rather than a reassurance: _"we are not planning to
use this for commercial gain for now, so if the effort to get each skill and repo fitted with images
becomes very large, this whole effort is not worth it."_

**The minimum that changes anything is two images per public repo** — a social preview, because it
is what every pasted link renders and every repo here currently shows GitHub's default grey card,
and one README banner. Four public repos is **eight images**, or roughly thirty generations at four
candidates each: one evening of generating, and the triage is minutes per slot once the tracker
exists.

**The version that is not worth it is per-skill imagery.** Fifteen skills with a card each is
fifteen more surfaces, none of which anyone has asked for and none of which appears on a page a
stranger reaches. The catalogue keeps `card-icons` as a surface because the vocabulary should be
complete; **nothing should generate one until a page exists that shows them.**

[DECISION: **scope the production to two images per public repo, and let everything else wait for a
page that needs it.** The process is still worth building because it is cheap — a tracker file, a
fetch command and a check — and because its real product is the **reason a candidate lost**, which
is what makes the second attempt a correction. The expensive half was never the tracker; it was the
image count, and the image count is now eight.]

**And the honest comparison, since the effort question is really about payoff.** The presentation
plan measured this family's actual state: **~380 installs against 0 stars**, zero topics on all 27
repos, no homepage URL anywhere, a public repo with an empty description, and every README carrying
no images at all. Of those, the **text and metadata fixes are free and measurably absent** — topics
and a description are minutes of work with no generation step. Images are the expensive half with
the least evidence of payoff. **If only one half gets done, do the text half**, which is also the
half that still has no deterministic checker.

## Recommended direction

0. **Do the free text-side fixes first** — topics, homepage, description, the README opener — since
   they cost minutes, are measurably missing, and need no generator at all.
1. **Absorb this beside the presentation plan**, and let its skill-count measurement decide whether
   this becomes part of the storefront skill or its own.
2. **Pilot by hand on power-user-linux-setup first**, per the house rule that a convention is
   applied to one real repo before it becomes shareable. That repo has the most-developed brief,
   real slots (social preview, docs hero, card set, logomark, drift banner), a licence table and a
   generator. Write its manifest and prompt files by hand in a session there, run one real handoff —
   generate, accept one, reject the rest with reasons — and note every step that was tedious.
3. **Only then script it**, stdlib and in `repo-pitch`'s shape — the script owns every rule and the
   `SKILL.md` explains it: `surfaces`, `init`, `prompt`, `accept`, `reject`, `status --all`,
   `check`. Script only what the pilot actually needed.
4. **Take the references out of the power-user-linux-setup plan when it retires**: the marks tier
   rule and table, and the NightCafe notes, become this skill's `references/`. That plan's session
   should know it has somewhere to send them.
5. **Second pilot: scaffoldapy's banner.** It already has seven prompts and a rejected batch with no
   recorded reason — the exact case the rejection record exists for.
