---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: 81492b4f-e6bc-4577-8d01-412b3ff4e7a9.jsonl
source_moment: 2026-09-28
source_plan:
---

# `harvest.py sweep` calls a repo a consumer because a package description mentions it

## Context

The sweep's "repos on this machine that install a repo this session changed" section finds consumers
by a checkout's own manifest or bootstrap naming the changed repo. On a scaffoldapy harvest it
printed:

```
/home/tdumitrescu/projects/github.com-personal/scaffoldapy
  installed by: /home/tdumitrescu/projects/github.com-personal/power-user-linux-setup
a push here is a deploy there — report it and file it
```

The only match is prose, in `power-user-linux-setup/setup.toml`:

```toml
[packages.copier]
description = "Project scaffolding tool with in-place template updates — drives the scaffoldapy repo template"
```

That entry installs `copier` from PyPI. Nothing installs scaffoldapy; copier renders its template
from GitHub only when someone generates a repo. So there is no deploy and nothing to sweep, and the
line's "report it and file it" instruction sent the harvest off to check.

## Evidence

scaffoldapy session `81492b4f-e6bc-4577-8d01-412b3ff4e7a9`, the harvest at boundary
`2026-09-28T18:23:47+03:00`. The row above is the whole section. It cost one `rg` and one read to
dismiss, which is cheap, but the section's own rationale is that a warning firing on no real
obligation is one the reader stops reading.

## Recommended direction

Match an install reference, not the name anywhere in the file. In `setup.toml` that means a
`package`/`url`/`repo` value, or a git URL naming the repo, and never a `description`. Alternatively
skip keys named `description` and TOML comments. Add this `setup.toml` shape as a fixture case that
must not match.
