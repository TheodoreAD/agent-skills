# repo-pitch

Checks the one line a repo shows strangers, on every surface it appears.

Every project has a sentence that says what it is. It appears in the GitHub About box, as the
README's opening line, as the package summary on PyPI or npm, and in a Show HN title. It is usually
written three or four separate times, and the copies drift apart. `standard-readme` has required
since 2017 that the README's short description match both GitHub's description and the package
manager's. In a sample of 17 well-known projects, 4 matched README to GitHub. Of 13 with a registry
summary, 5 matched GitHub to it.

The sentence also tends to go wrong in the same few ways: a list of features instead of a statement
of what the thing is, "X is a…", a leading "A", a superlative, an emoji, or a length the target
surface silently cuts off.

repo-pitch gives your agent a small checker for that one string, with rules calibrated against real
data, and a command that compares the surfaces with each other.

## What you get

- A check of a draft pitch that blocks only on rules a carefully linted corpus almost never breaks,
  and warns on the ones that are real questions rather than defects. The two levels are explained
  below.
- The length budget of every surface it knows, each with where the number came from: GitHub, the
  README short description, Show HN, npm, PyPI, X, Homebrew, Product Hunt and AppStream.
- A reader for a README's short description, finding the line the way a reader would.
- A drift check that reads the README, the GitHub description and the PyPI or npm summary, and says
  whether they are the same string.
- Two house-style rules left for you to set, because real registries disagree on them: a trailing
  period, and a leading capital.

## What it looks like

Real output. A pitch that reads like a feature list:

```
$ pitch.py check "A fast, modern, lightweight CLI tool for managing, syncing, and backing up your dotfiles" --name dotsync --surface github
  "A fast, modern, lightweight CLI tool for managing, syncing, and backing up your dotfiles"  (88 chars)
   warn  over_80: 88 characters
         under every hard limit, but past Homebrew and Show HN
  BLOCK  leading_article: opens with 'A'
   warn  feature_list: 4 commas
         27.0% on GitHub, 1.0% on Debian
```

The same project, said once:

```
$ pitch.py check "Dotfile manager that keeps several machines in sync from one git repo" --name dotsync --surface github
  "Dotfile manager that keeps several machines in sync from one git repo"  (69 chars)
  clean against every rule here — which is not the same as good; see --explain
```

And this repository's own README against its GitHub description:

```
$ pitch.py drift --readme README.md --repo TheodoreAD/agent-skills
  readme   Vendor-neutral Agent Skills in plain SKILL.md directories, readable by any agent.
  github   Vendor-neutral Agent Skills in plain SKILL.md directories, readable by any agent.

  every readable surface carries the same string, as standard-readme requires
```

Note what the first check did not flag: "fast", "modern" and "lightweight". Whether an adjective is
earned is a judgement, and the checker leaves it to you.

## Why its rules block or warn

Each rule was measured twice: across 856 top developer-tool repos on GitHub, and across 85,842
Debian package synopses, which are written to published rules and checked by a linter. The Debian
rate works as a false-positive rate. A rule that real, carefully linted synopses almost never break
may block. One they break now and then is a matter of style, so it only warns.

A leading "A" or "The" appears in 26.8% of the GitHub descriptions and 0.35% of Debian's, so it
blocks. Two or more commas is the sharpest single sign of a feature list, at 27.0% against 1.01%,
but Debian ships 866 correct synopses with two commas, so it warns.

## What it can't tell you

It checks form, not appeal. Across those 856 repos, the correlation between breaking these rules and
star count was +0.056, which is none. So what it can support is narrow: a stranger can tell what the
thing is, the same string appears everywhere, and it fits where it is going. It does not claim a
better pitch brings more stars. Whether the category noun is the right one, whether the claim is
true, and whether it reads clearly to someone who isn't the author are left to a person.

It also doesn't decide who writes the text. Hacker News' guidelines say "Don't post generated text
or AI-edited text", and its Show HN tips ask for the text to be written by hand with no LLM involved
at all. `awesome-readme` requires a description "written by a person. Not AI.", and dev.to bans
AI-assisted articles that promote your own project. A draft line for your own About box is fine to
check. A Show HN title has to be yours.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill repo-pitch
```

Then ask: "is this a good one-liner for the repo?", "does our README match the GitHub description
and the PyPI summary?", "how long can a Show HN title be?".

Needs Python 3.11 or newer. The drift check also needs `gh`, logged in, and reads PyPI or npm over
the network.

## What it touches

It writes nothing. Every command prints, and none edits a README, sets a description or calls a
write API; applying a fix is your own edit or your own `gh repo edit`. It reads a README you name.
The drift check alone uses the network: one `gh repo view` for the GitHub description, plus the PyPI
or npm summary. The complete list is in
[`SKILL.md`](SKILL.md#what-this-skill-reads-runs-and-writes).

## Read more

- [`SKILL.md`](SKILL.md): the full instructions your agent follows.
- [`references/measurements.md`](references/measurements.md): both corpora and how they were drawn,
  the full distributions, each platform limit with the code it was read from, and the two negative
  results that bound what the skill may claim.
