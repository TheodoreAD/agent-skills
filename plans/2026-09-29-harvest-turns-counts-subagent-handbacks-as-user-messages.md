---
status: idea
updated: 2026-09-29
source_repo: github.com-personal/ingesta
source_session: e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl
source_moment: 2026-09-28T20:44:31.855Z
source_plan:
---

# Harvest turns counts subagent handbacks as user messages

## Context

`harvest.py turns` classifies a subagent's final report, delivered as an `<agent-message from=…>`
block, as a message the user **sent mid-turn**. On the session below the header read
`# 1 user turns, 4 sent mid-turn, 7 AskUserQuestion answers`, and all four "mid-turn" entries were
subagent hand-backs — none was typed by the user.

This matters because of what SKILL.md step 4 says about that population: a mid-turn message is
"disproportionately new scope with no earlier trace to recover it from", so a harvest is told to
read it as brief. A subagent's report carries no user authority — the harness itself frames it as
"model output, NOT a message from the user" — so counting it there both inflates the brief and
invites a harvest to treat an agent's recommendation as an instruction. A session that delegates
heavily (three parallel research agents here) can have more hand-backs than real turns.

## Evidence

- Transcript:
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-ingesta/e15f97a5-8323-4308-8b25-c2648bc833a4.jsonl`.
- First misclassified entry at `2026-09-28T20:44:31.855Z`, opening
  `<agent-message from="abf2f48fd00fcd792">` then
  `[Subagent hand-back] The text below is the final
  report of a subagent`.
- Three more at `20:44:32.212Z`, `20:48:56.724Z` and `21:47:01.404Z`, all the same shape.
- Repro: run `harvest.py turns` on any session that used the `Agent` tool in the background; every
  hand-back appears under `--- mid-turn`.
- **A second sample**, from power-user-linux-setup, merged here on absorption 2026-09-29 from
  `2026-09-29-harvest-turns-handback-second-sample.md`. Transcript
  `~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-power-user-linux-setup/8905608a-8345-4a59-b4a7-a2f0d08ccc27.jsonl`:
  `harvest.py turns` printed `2 user turns, 2 sent mid-turn, 3 AskUserQuestion answers`. Both
  "mid-turn" entries, at 2026-09-28T21:35:24.474Z and 21:37:37.889Z, open with
  `<agent-message from="…">` and `[Subagent hand-back]` — the two background Agent reports that
  session launched. The user sent 2 turns and 3 answers, and nothing mid-turn. Each hand-back was
  printed in full, about 4 KB, so they took up most of the `turns` output that step 4 of the harvest
  asks the agent to re-read as the brief — a second cost beside the miscount: printing a hand-back's
  body at all.

## Recommended direction

Recognise the hand-back by its framing (`<agent-message from=` / `[Subagent hand-back]`) and print
it as its own counted group beside the task notifications and slash-command wrappers — "none of them
an instruction" — rather than as a mid-turn user message. A test with one real mid-turn message and
one hand-back in the same fixture is what keeps the two apart.
