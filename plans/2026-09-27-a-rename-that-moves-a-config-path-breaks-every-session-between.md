---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl
source_moment: 2026-09-27T19:47:51Z
---

# The plan-docs rename is half-deployed, and the installed skill now misfiles into the sensitive tier

## Context

`agent-skills` holds an unpushed commit,
`81626a9 plan-docs: rename to plan-conveyor, config path and
variable included`. The config half of
it has already taken effect on this machine — `~/.config/plan-conveyor/` exists and
`~/.config/plan-docs/` does not — while the skill half has not, because the installer clones from
the remote and the commit is unpushed. So the installed skill is still
`~/.agents/skills/plan-docs/`, and its script looks for a config file that has moved.

**An unconfigured `plans.py` does not fail closed.** Two behaviours, both measured 2026-09-27 from a
session in another repo:

- `where` exits 3 with `no config file at /home/tdumitrescu/.config/plan-docs/config.toml`, which is
  the honest half — a session sees it and stops.
- `new <topic> --for <repo>` **succeeds**, and files into the **sensitive** tier, because with no
  config `shareable_roots` defaults to empty and every root is therefore sensitive. The command
  prints `tier: sensitive` and a path under `plans-sensitive/`, which reads as a correct filing
  unless you know what tier that root belongs to.

The second is the damaging one, and it is the ordinary cross-repo filing every session is told to
make. The sensitive tier deliberately has no remote, so a plan landing there is unbacked; it is also
outside what the shareable tier's pre-push content scan ever examines, and it puts a
`github.com-personal/` root into a store whose whole purpose is that it holds no such thing.

The window is not small. `~/.agents/AGENTS.md` names the installed path
(`python3 ~/.agents/skills/plan-docs/scripts/plans.py …`) in its own rules, so every session on the
machine is being pointed at the broken copy for as long as the commits stay unpushed, and none of
them has a reason to look.

## Evidence

Session `65f8437a-a90e-41c6-9b1f-9b43d713ed9b.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-invoke-stubs/`, 2026-09-27,
during a `session-harvest` run. It hit both halves in sequence while filing two ordinary harvest
findings, having used the installed script successfully throughout the same session's earlier work
on 2026-09-07 — before the config moved.

The misfile was real, not hypothetical: an empty skeleton was created at
`plans-sensitive/github.com-personal/agent-skills/2026-09-27-harvest-window-on-a-session-resumed-weeks-later.md`
and removed by hand. Nothing else from that root was tracked in the sensitive store, so this was the
first one.

`skills-state` in the same run named the condition without connecting it to a consequence:

```
== plan-conveyor ==
  not installed — every path a rule names for other sessions is dead
```

That line is about paths that error. What actually happened was a path that **worked and wrote to
the wrong place**, which no line in the report covers.

## Open questions

**Decided 2026-09-28: `new` refuses in every form without a config, exit 3.** The question was
narrower than it read. Plain `new` already refused — it goes through the routing verdict, which says
`no config file` — so this was never a policy of treating "no config" as valid. It was two routes
skipping the verdict: `--for` calls `resolve()` but uses only its store path, and `--unscoped` never
routes. Both now check the config first, with a parametrized test over all three forms asserting
neither store is created. The tier default for an unrouted root on a configured machine is
untouched, since that reasoning still holds there.

**Decided 2026-09-27, in `073141b`: yes.** `skill-authoring-taudelta` now says a rename that moves
state outside the skill directory moves it after the install — push, install, move — with this
incident as the evidence and the fallback pitfall below alongside it.

## The window is closed, and the mitigation was aimed the wrong way

Confirmed 2026-09-27 by the session that caused it, absorbing this plan after the fact. The commits
were pushed, `skills add TheodoreAD/agent-skills --global` ran, the eight superseded copies were
removed, and the installed `plan-conveyor/scripts/plans.py` resolves the moved config with no
fallback notice. `plans-sensitive/` holds nothing but its own `README.md`, so the hand-removal of
the misfiled skeleton was complete. Timings: the config moved at 22:37 local, the push landed at
~23:07, so the window was **roughly thirty minutes** and this plan was filed from inside it at
22:47.

[PITFALL: **the rename shipped a config fallback, and the fallback could not have helped.** The
renaming session did think about the config path breaking — `config_path` reads the pre-rename
directory when the current one is absent, `harvest.py` grew the same fallback independently, and
four tests cover it. Every one of those lives in the **new** code. The failure here is the mirror
image: **old installed code looking for a path that had already moved**, where nothing in the new
commit is running yet. A fallback protects the upgrade; it cannot protect the interval before the
upgrade arrives, and that interval is the one a rename creates. The renaming session verified the
right number for the wrong direction — 61 private terms through the fallback and 61 after the move —
and that check would have passed identically while another session was misfiling into the sensitive
tier.]

So the ordering rule the second open question is reaching for is sharper than "the sequence would
have closed this": **when a rename moves state that lives outside the skill directory, the move
belongs after the install, not before it.** Editing the code and moving the file are one commit's
worth of work and two events on the machine, and the safe order is push → install → move, because
only then is the code that knows both paths the code that is running.

## Recommended direction

Push the rename commits and run `inv ai.install-skills`, which closes the window; that is the
owner's call and this plan does not propose doing it from elsewhere. **Done 2026-09-27** — see
above.

Then decide the two questions above. The first is a small change to `plans.py` with a real safety
argument behind it. The second is where this generalises: the rename itself was done carefully — the
commit message says the config path and variable moved with it — and the gap still opened, because
correctness inside the repo and deployment across the machine are two different events with time
between them.

## Migrated to

- **The ordering rule and the fallback pitfall** — `skills/skill-authoring-taudelta/SKILL.md`, the
  paragraphs after "Renaming or deleting a skill needs a second step" (`073141b`), including why the
  gap is quiet rather than loud.
- **The refusal** — `Workspace.require_config` in `skills/plan-conveyor/scripts/plans.py`, whose
  docstring carries the incident, and `test_no_config_refuses_every_new` (`707abfc`).
- **Not migrated**: the window's timings and the session id. They are evidence for a rule that now
  has its own dated evidence in both destinations, and `plans.py archive` reads them back from here.
