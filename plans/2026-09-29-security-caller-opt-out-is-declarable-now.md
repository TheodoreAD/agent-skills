---
status: landed
updated: 2026-09-29
source_repo: github.com-personal/repo-tasks
source_session: 0a32e30f-5e28-40f1-b57e-78968efbacdd.jsonl
source_moment: 2026-09-29
source_plan:
---

# The security-caller opt-out can be declared now

## Context

This reports a fact, which is why `source_plan` is blank.
`plans/2026-09-13-repo-tasks-consumer-sweep.md`, "What is left", waits on two repo-tasks changes.
One has landed: `2026-09-29-consumer-can-decline-the-security-caller.md`, in repo-tasks `37cf195`,
now retired there. The other, `2026-09-29-consumer-pyright-tier-and-subtree-include.md`, is still
open and needs decisions on the tier's shape and on sub-tree includes.

`consumers.diff` runs from repo-tasks' own tree and reads this repo's `repo-tasks.toml` directly, so
the declaration takes effect without a repo-tasks release.

## Evidence

Verified 2026-09-29 against a local clone of this repo with the declaration below appended to
`repo-tasks.toml`, under `REPO_TASKS_PROJECTS_ROOT`: `consumers.diff --name agent-skills` printed
`declines the security caller: nothing in uv.lock ships to anyone who installs these skills` in
place of `no caller for .github/workflows/security-reusable.yml`, and did not count it as behind.

## Recommended direction

1. Add to `repo-tasks.toml`, with the reason taken from the security DECISION in the sweep plan:

   ```toml
   [security]
   caller = false
   reason = "<one line: nothing in uv.lock ships to anyone who installs these skills>"
   ```

   `reason` is required; a bare `caller = false` is still reported as behind. The key is documented
   in repo-tasks' `contributing/consumer-sweep.md`, "Still open", not in `file-discovery.md` (which
   covers only the `[pyright]` keys).
2. Update the sweep plan's "What is left": one of the two waits is over. Its retirement still waits
   on the pyright tier.
3. That same run will show the shipped `ruff.toml` moving to the renamed skill path this repo had
   already hand-corrected (repo-tasks `9435863`), once a release carries it.

## Migrated to

- `repo-tasks.toml`, `[security]`: the declaration itself (step 1), with a comment summarising the
  reason and pointing at the sweep plan's DECISION.
- `plans/2026-09-13-repo-tasks-consumer-sweep.md`, "What is left": step 2, plus the verification
  (consumers.diff reporting the caller as declined), the release check, and step 3's observation,
  which the re-run confirmed as `config files behind: ruff.toml, pytest.ini`.
- Not migrated: where repo-tasks documents the key (its `contributing/consumer-sweep.md`). That is
  repo-tasks' to keep current, and the comment in `repo-tasks.toml` needs no pointer to it.
