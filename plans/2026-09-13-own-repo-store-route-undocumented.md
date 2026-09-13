---
status: landed
updated: 2026-09-13
source_repo: github.com-personal/power-user-linux-setup
source_session: 8e1ea2df-8de1-4cd1-873d-5a0f058aaa6d.jsonl
source_moment: 2026-09-13T11:55:13Z
source_plan:
---

# plan-docs: "hold this repo's plan in the store" has a route nobody is told about

## Context

A user in a repo-routed repo asked for a plan **"in the central store (there's another session
writing to the repo)"**. plan-docs already has the right route: `plans.py new <topic> --to store`
writes into this repo's store mirror and never touches the working tree, and the next session there
is offered it by `absorb`. Nothing points a session at it:

- **`SKILL.md` never mentions `new --to`.** It documents `--to` only on `move` ("a repo switching
  where it keeps plans") and `move <file> --to repo` for absorption. Its creation guidance offers
  plain `new` (repo route), `new --for <repo>` (another repo) and `new --unscoped` (no repo yet).
- **The refusal names the wrong alternative.** `new <topic> --for <the session's own repo>` exits 1
  with `--for names the repo this session is already in; use plain \`new
  <topic>\``. That is
  correct when the user only mistyped`--for`. When`--for` was reached for
  _because_ the tree is busy, the suggested fallback writes into exactly the tree the user said to
  stay out of.

What the session did instead is a failure as a rule-followed-wrong-outcome, not a skipped rule: it
used `new --unscoped`, per "Plans that belong to no repo yet". That kept the tree clean, but put a
plan that plainly belongs to a repo where `absorb` never looks. Only `list --scope repo`, which
reads the unscoped area, would have surfaced it, and `graduate` was the only way back in. Graduating
it routes through the repo's own rule and writes into that same busy tree. The plan sat unscoped for
about 3h15m, through three commits, until a harvest in the same session noticed `new` accepts `--to`
and moved it with `move <file> --to store`. `absorb` offered it immediately afterwards.

## Evidence

- Transcript `8e1ea2df-8de1-4cd1-873d-5a0f058aaa6d.jsonl`. The ask is at `2026-09-13T11:55:13Z`:
  "create a plan in the central store (there's another session writing to the repo)".
- The refusal, verbatim: `error: --for names the repo this session is already in; use plain \`new
  platform-neutral-imagery-prompts\``.
- The fallback: `new platform-neutral-imagery-prompts --unscoped`, which printed
  `note: belongs to no repo yet — plans.py graduate <file> --to <repo> when it does`.
- The fix: `plans.py new --help` lists `--to {repo,store}  override the configured write target`.
  `move <unscoped path> --to store` then relocated the plan into the repo's mirror, store commit
  `55c0585`. `absorb` listed it on the next call.
- `rg -n -e 'new .*--to' -e '--to store' skills/plan-docs/SKILL.md` matches only the `move` line.

## Open questions

None. Both changes below are additive.

## Recommended direction

Landed as `452c89b` and `7ce55d8`, all three items including the optional one: the refusal names
`--to store`, an unscoped create from inside a routed repo prints a note naming it, and `SKILL.md`
has the command row and a paragraph beside the parallel-session guidance.

1. **The refusal names both routes.** For example:
   `--for names the repo this session is already in; use plain \`new <topic>\`, or \`new <topic>
   --to store\` to keep it out of the working tree`. A test in the plan-docs unit suite pins the
   wording.
2. **`SKILL.md` gets one row for the case**, where the command table already lives:
   `new <topic> --to store  # this repo's plan, kept out of a working tree another session holds`.
   It also belongs beside the "Something that belongs to a repo you are not in" guidance on parallel
   sessions sharing a tree, since that is the trigger.
3. **Optionally, `new --unscoped` warns from inside a routed repo**, naming `--to store`. An
   unscoped plan created from inside a repo is very likely that repo's.
