---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/power-user-linux-setup
source_session: 156d723c-4e21-41ef-aac9-bfd6c05b681c.jsonl
source_moment: 2026-09-05T19:40:00+03:00
---

# `skills-state --since` asks the operator for a value the script already knows

## Context

`session-harvest`'s step 0 prescribes `python3 $H skills-state --since <session start>`, and it is
the **first** substantive command of a harvest. But the session start is printed by `transcript`,
which the same block lists afterwards — so at the moment the value is needed it has not been
produced, and the operator supplies it by hand.

Confirmed 2026-09-05, this session: the first call passed midnight local as a stand-in, because that
was the only bound to hand. It reported `session-harvest` `SKILL.md` as moved by **9** commits;
re-run with the real start (`2026-09-04T22:43:15Z`, from `transcript`) it reported **8**. Small, and
in the direction that inflates — an over-count makes the staleness branch look more urgent than it
is, which is the branch that costs the most to walk.

The value is not hard to get: `skills-state` runs in the same process as the resolver that `turns`,
`sweep` and `claims` already use, and that resolver prints `started:` from the transcript's first
entry. Every other subcommand resolves the session from `$CLAUDE_CODE_SESSION_ID` without being
told; this one alone requires the operator to fetch a timestamp from a sibling subcommand and retype
it.

[DECISION: **this belongs in the script, not in a clearer sentence in step 0.** The skill's own
standard — "a correction that a script can simply not make belongs in the script" — applies exactly:
reordering the block so `transcript` comes first would still leave a value to copy between two
commands, and the copy is the error surface. Default `--since` to the resolved session start, keep
the flag as an override for auditing a window that is not this session's.]

## Open questions

[NEEDS CLARIFICATION: what the default should be when no session resolves — a harness that exports
no id, or a `--checkout`-only invocation outside a session. Reporting every commit ever is useless
noise; erroring turns a currently-working invocation into a failure. Probably: keep the current
behaviour of requiring the flag in that case, and default only when a transcript was resolved, so
the change is additive.]

## Recommended direction

One resolver call in `skills-state`, the flag kept as an override, and step 0's command block loses
the placeholder. Worth doing alongside `2026-09-05-skills-state-skill-flag-replaces-defaults.md`,
which is the other change to the same subcommand's argument handling — same function, same review.
