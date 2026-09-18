---
status: idea
updated: 2026-09-13
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
  for identity rather than inventing one; the presentation plan already says so.
- **`thatrebeccarae/claude-marketing`'s `social-preview` skill** (clone): renders one surface, the
  1280×640 card, from HTML templates, with an audit mode. One surface, no candidates, no record.
- **`JimLiu/baoyu-skills`' `baoyu-cover-image`** (clone): writes each prompt to its own file, with
  frontmatter for palette, rendering and reference images. **Prompt-as-a-file is the idea worth
  taking.** Generation there is API-driven, and nothing records which output was accepted.
- **Favicon generators** turn one source image into the standard icon set. A step in the process,
  not a tracker.
- Two web searches for a tool tracking per-repo image needs with provenance found prompt libraries
  and generators, and no tracker. **That negative is search-summary depth**; the global rule asks
  for a real prior-art pass before a new skill is finalised, and this is not one yet.

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

### 2. One file per repo that says what it needs and what it has

The tracking the user asked for. Illustrative shape, format still open:

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

**Rejections are recorded with a reason, because that is what turns a re-roll into a correction** —
scaffoldapy's plan states the lesson and its rejected batch is the counterexample. **`published` is
checkable**: a README or docs reference for most surfaces, and for the social preview the
presentation plan found `usesCustomOpenGraphImage` in `gh repo view --json`.

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

## Open questions

[NEEDS CLARIFICATION: **a skill of its own, or the image half of the storefront skill?** The
presentation plan's open question 1 decides this by measurement (`trigger.py split --proposal`), and
its prior is two skills, one of them "the repo-as-storefront (README, metadata, assets, catalogue)".
This process fits that one. Settle it there, with this plan's catalogue and handoff phrases as cases
in the suite.]

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

[UNVERIFIED: **the favicon set's sizes** — 16, 32, 180, 192 and 512 pixels, plus an ICO — are from a
search summary. Verify against a maintained generator's source before the catalogue states them.]

[DEFERRED: **disclosure of AI-generated images.** Whether to embed IPTC's digital-source-type
metadata, and whether any venue in the presentation plan's §8 has rules for generated images as
opposed to generated text, was not researched.]

## Recommended direction

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
