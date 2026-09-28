---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/scaffoldapy
source_session: 81492b4f-e6bc-4577-8d01-412b3ff4e7a9.jsonl
source_moment: 2026-09-28
source_plan:
---

# This repo's `.venv` is on 3.14 while its skills' floor is 3.11

## Context

This reports a fact, which is why `source_plan` is blank. The tier rules (scaffoldapy's
`plans/2026-09-18-python-version-tier-rules.md`, and `~/.agents/AGENTS.md`, "Setting or changing a
Python project's version floor") say a repo whose shipped scripts run on an ambient `python3`
**develops at those scripts' floor**, so the ordinary test run is the floor check. That only holds
if the venv is actually on 3.11.

**Cause:** `UV_PYTHON=3.14` left the dotfiles on 09-19 but stayed in the systemd user manager until
a reboot on 2026-09-28 at 15:18. gnome-session writes its environment there at exit, and a
long-lived Claude daemon kept the manager alive across re-logins. Any agent session's bare
`uv run`/`uv sync` rebuilt the venv at 3.14, since the variable outranks `.python-version`.
`power-user-linux-setup` owns that mechanism.

## Evidence

Read-only, 2026-09-28, from scaffoldapy's `floor-audit.py` (attached to that plan):

```
agent-skills            3.11   3.11   3.14.5    not packaged  <-- venv above floor
```

That is declared floor, `.python-version`, then the venv's own interpreter. After the reboot, a
project declaring 3.11 resolves to 3.11.15, so the fix will now hold.

## Recommended direction

1. From a session started after the reboot (`env | rg UV_` prints nothing): `inv venv.recreate`,
   then `inv venv.check`.
2. Run the suite at 3.11 and read failures as the point. This is where a 3.12+ API in a skill script
   shows up, which ran unnoticed on 3.14. The separate below-floor finding the tier-rules plan
   measured on 09-18, unguarded `import tomllib` failing on 3.10, needs the version guard, not this.

## Migrated to

Nothing to migrate: this was machine state, not a design. Done 2026-09-28 from a session with no
`UV_*` in its environment: `inv venv.recreate` put `.venv` on 3.11, `inv venv.check` confirmed it,
and the whole suite passed there (1295 tests) with no 3.12+ API surfacing — the one known case,
`typing.override` in the tests, had already moved to `typing_extensions`. The cause is owned by
`power-user-linux-setup`, as the Context says.
