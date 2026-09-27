---
status: idea
updated: 2026-09-27
---

# Package health: report what a release actually ships

## Context

`research-library`'s `scripts/package_health.py` judges a PyPI package on maintenance, typing,
battle-testing and fit. It was written because sessions kept hand-rolling
`pypi.org/pypi/<name>/json` fetches: 61 across 12 sessions, measured 2026-08-30 (its own docstring).

It does not report **what a release ships**, meaning its file list. That is exactly the question the
machine-wide install rule asks. The home `AGENTS.md` section "Installing a tool on this machine"
tells an agent to look for a maintained PyPI wrapper first (`shellcheck-py`, `actionlint-py`…), and
to "judge the wrapper from its own PyPI file list (`curl -s https://pypi.org/pypi/<name>/json`),
never from a search summary". Those facts are:

- **platform-tagged wheels**, meaning the binary ships inside the wheel, versus **sdist-only**,
  meaning it fetches or builds at install time;
- **file sizes**, which are the adoption cost;
- **release count**;
- **whether the wrapper's version tracks the upstream release**, checked against the upstream
  changelog.

That rule cites two cases where this went wrong in both directions. A search summary claimed
`hadolint-py` downloads at install time, and it nearly got rejected for a false reason: it ships
real 12 MB wheels. `lychee-bin` turned out to be a 78 MB wheel with exactly one release, which
reversed a decision already made to adopt it.

So the one rule that most needs the file list is the one the script can't answer, and the rule
itself spells the answer as a hand-rolled `curl`.

It surfaced 2026-09-27 in a Google-stack CLI research session. A research subagent had been told to
`curl` PyPI for exactly this, and had to be redirected to `package_health.py` with the file-list gap
named.

[UNVERIFIED: how often sessions still hand-roll the PyPI fetch after `package_health.py` landed. A
rough `rg` for `curl…pypi.org/pypi/` over `~/.claude/projects` matched around 170 transcripts on
2026-09-27. That count is contaminated, because the home `AGENTS.md` rule text contains the same
string and is loaded into sessions. Measure it with `session-bash-audit` or `skill-fitness`'s
repeated-script mode, counting Bash tool-use commands only.]

## Open questions

[NEEDS CLARIFICATION: extend `package_health.py`, or add a sibling script (`release_files.py`)? A
flag such as `--files`, or an always-on section, keeps one entry point for "judge this package". But
the wrapper question has a different second input: the **upstream** repo whose releases the wrapper
should track. That is not the same repo as the package's own, which `package_health.py` already
takes as `<owner/repo>`. For `shellcheck-py` the package repo is `shellcheck-py/shellcheck-py` and
upstream is `koalaman/shellcheck`.]

[NEEDS CLARIFICATION: how to compare wrapper and upstream versions. Wrappers often use the upstream
version with a suffix (`0.10.0.1`), and some are unrelated. A reasonable first cut reports both
latest versions and the lag in days between upstream's release and the wrapper's matching one. It
flags "no matching wrapper release" rather than trying to parse every scheme.]

[NEEDS CLARIFICATION: does the release-file report belong in `research-library` at all, or in
`power-user-linux-setup`, which owns the install rule and `setup.toml`? It belongs here if judging
"what does installing this cost" counts as part of judging a dependency, which the skill's
description already claims ("whether a version cap it carries will hold you back"). And the skill is
what's installed on every machine.]

## Recommended direction

1. Extend `package_health.py`. For the latest **stable** release, and optionally the last N, list
   every file with:
   - its type (wheel or sdist);
   - its wheel tags (Python, ABI, platform);
   - its size;
   - its upload time.

   Then summarise:
   - whether a `manylinux`/`musllinux` x86_64 wheel exists for this machine;
   - the largest file;
   - pure-Python (`py3-none-any`) versus platform-specific;
   - sdist-only, which means install-time build or fetch.

   It reuses the transport it already has. The same PyPI JSON payload is already fetched, so there
   is no extra request.
2. `--upstream <owner/repo>` adds the wrapper-tracking check through `gh api` releases: upstream's
   latest release date and version, whether the wrapper has a matching version, and the lag.
3. `--json` carries all of it, like the rest of the report.
4. Update the SKILL.md "Judging a candidate dependency" section with the new line and one example
   (`shellcheck-py` with upstream `koalaman/shellcheck`).
5. Tests in `tests/unit/`, using a recorded PyPI payload fixture in `tests/fixtures/`, never inside
   the skill.

[DEFERRED: repointing the home `AGENTS.md` install rule from
`curl -s https://pypi.org/pypi/<name>/json` to this script. That rule is a fragment in
`power-user-linux-setup` (`config/agents-md/`), so once this lands, file it with
`plans.py new … --for github.com-personal/power-user-linux-setup` rather than editing that repo from
here.]
