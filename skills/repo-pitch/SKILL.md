---
name: repo-pitch
description: "Use when writing or fixing the one-line description a repo shows the world — a GitHub About box, a README's opening sentence, a package summary on PyPI or npm, a Show HN title, a plugin or extension listing — or when those have drifted apart and you want them to be one string again. Also for judging a draft one-liner before adopting it: what length actually fits each surface, why a list of features reads as a non-answer, and which style rules are real versus somebody's taste. Checks that a pitch is well formed; it does not score whether the project is appealing, and it does not write marketing copy."
license: MIT
compatibility: "Reading a README and checking a pitch need nothing but Python 3. The drift command shells out to `gh` (authenticated) for a GitHub description and reads pypi.org or registry.npmjs.org over the network."
---

# The one line a stranger reads first

A repo's short description is one string with several deploy targets, not several strings.
[`standard-readme`](https://github.com/RichardLitt/standard-readme) has required exactly that since
2017 — the README's short description **must** match the package manager's `description` and
GitHub's description — and almost nobody does it: of 17 well-known projects sampled, 4 matched
README to GitHub; of 13, 5 matched GitHub to their registry.

So the work is usually not writing a new pitch. It is finding the one you already have, deciding
which wording wins, and putting it on every surface.

## What this skill reads, runs and writes

- **Reads**: a README path you name; this repo's own `scripts/`. `drift` additionally reads a GitHub
  repo's description and a package's summary on PyPI or npm.
- **Runs**: `gh repo view <repo> --json description`, under `drift` only. Nothing else shells out.
- **Writes**: **nothing.** Every command prints; none edits a README, sets a description, or calls
  any write API. Applying a fix is your edit, or your `gh repo edit`, taken deliberately.
- **Network**: `drift` only — `api.github.com` through `gh`, plus `pypi.org` or `registry.npmjs.org`
  for the registry summary. Every other command is offline.

## Run the script

[`scripts/pitch.py`](scripts/pitch.py) owns every threshold and every rule. Stdlib only, so it runs
by path.

```shell
python3 <path>/pitch.py check "<the pitch>" --name <project> --surface github
python3 <path>/pitch.py check "<the pitch>" --explain      # what the levels mean, and what it cannot see
python3 <path>/pitch.py surfaces                           # every length budget, with its source
python3 <path>/pitch.py readme README.md                   # the short description, as a reader finds it
python3 <path>/pitch.py drift --readme README.md --repo <owner>/<name> --pypi <package>
```

`check` exits 1 on a blocking finding, `drift` exits 1 when the surfaces disagree, so both work in a
gate. Every command takes `--json`.

## A rule may block only where a controlled corpus clears it

This is the part worth understanding, because it is what separates the checks from somebody's taste.

Each rule carries two rates: how often it fires across **856 top developer-tool repos**, and how
often across **85,842 Debian package synopses** — a corpus governed by written rules and
machine-checked by lintian. The second number is a false-positive rate. A rule that fires on real
linted synopses is a rule about style, and it warns; a rule that essentially never does may block.

| rule                     | Debian | GitHub | level |
| ------------------------ | ------ | ------ | ----- |
| opens `<Name> is a…`     | 0.02%  | 7.8%   | block |
| contains a URL           | 0.01%  | 2.0%   | block |
| contains emoji           | 0.04%  | 16.2%  | block |
| superlative              | 0.17%  | 5.3%   | block |
| over 100 characters      | 0.19%  | 28.7%  | block |
| first person             | 0.20%  | 2.0%   | block |
| opens with an article    | 0.35%  | 26.8%  | block |
| **over 80 characters**   | 2.32%  | 38.3%  | warn  |
| **repeats its own name** | 1.15%  | 27.8%  | warn  |
| **two or more commas**   | 1.01%  | 27.0%  | warn  |

**The three warnings are the interesting ones, which is exactly why they must not block.** Two or
more commas is the sharpest single discriminator found — 27.0% against 1.01% — and it is what a
feature list looks like when it is wearing a pitch's clothes. But Debian ships 866 synopses with two
commas that are right, so it is a question, not a defect.

**Mechanically-enforced rules hold; prose-only ones leak.** Homebrew's ten-rule description cop has
**zero violations across 8,595 shipped formulae**, while the same project's prose rule against
marketing adjectives leaks — `fast` at 3.0%, `modern` at 1.2%. Put in the checker whatever you
actually care about.

## Two style rules have no right answer, so the target supplies it

Real registries hold opposite positions, and a checker that picks a side is wrong about half its
targets:

| axis            | who requires it         | who forbids it                        |
| --------------- | ----------------------- | ------------------------------------- |
| trailing period | Obsidian (90.3% comply) | Homebrew; Debian omits it in 99.1%    |
| leading capital | AppStream; Homebrew     | Debian lowercases 26.19% deliberately |

Both are off unless asked for: `--style trailing-period=required`,
`--style leading-capital=forbidden`.

## What the numbers say a good one looks like

Across those 856 repos: median **68 characters**, p25 43, p75 111. **80% are noun phrases**, 8%
verb-initial. The hard ceiling is 350, and `surfaces` prints every real limit — Show HN 80 (and the
check is `len>`, so exactly 80 passes, leaving 71 after `Show HN:`), npm 255 **truncated silently
mid-word**, PyPI 512, Homebrew 80, Product Hunt tagline 60, X 280 **weighted** with any URL costing
23 and non-Latin characters costing double.

**Naming the parent is surface-dependent, and this was measured rather than reasoned.** The same
Obsidian plugins name "Obsidian" in **90%** of their GitHub repo descriptions and **9.5%** in the
plugin registry — the directory supplies context a standalone repo cannot. Raycast shows the same
gradient inside one product: extensions say "Raycast" 20.3%, commands 1.9%. So decide it per
surface; there is no single right answer to carry between them.

## What this cannot tell you, and one number that bounds the whole thing

Nothing here scores quality. Across those same 856 repos, the correlation between violating these
rules and stars is **+0.056** — none, on a sample restricted to 30k stars and up.

So the defensible claims are narrow: a stranger can tell what this is, the same string appears on
every surface, and it fits where it is going. "A better pitch gets more stars" is not among them,
and no output of this skill should imply it.

Left to a person: whether the category noun is the right one ("package manager" beats "toolchain"
and no script knows that), whether the claim is true, whether it parses for somebody who is not the
author, and whether an analogy flatters a competitor — only 2.1% of descriptions name one, and 10 of
those 18 are "alternative to X", which is a positioning bet rather than a style choice.

## Where the output may go

**Not into a community venue as generated text.** Hacker News' guidelines say plainly _"Don't post
generated text or AI-edited text"_, and its Show HN tips add _"Write your text by hand. Don't use an
LLM to generate any of it (not even a tiny bit, including to edit or spruce it up)."_
`awesome-readme`'s admission criteria say the same independently: _"The description should be
written by a person. Not AI."_ dev.to bans AI-assisted articles that promote your own project at
all.

A draft one-liner for your own repo's About box is your text and this is a checker. A Show HN title
is not, and no amount of "it only edited it slightly" changes that.

## Fixing drift, once `drift` reports it

Pick the wording that survives the shortest surface, then put that exact string everywhere. The
GitHub description is the one people forget, because nothing shows it next to the README — and it is
the one a search result renders.
