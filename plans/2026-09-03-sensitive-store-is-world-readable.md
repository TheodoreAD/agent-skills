---
status: planned
updated: 2026-09-03
---

# The sensitive plans store is created world-readable

## Context

Found 2026-09-03 while answering a different question — whether moving the corpus's paths to XDG
locations would solve any security issue. It would not, and the reason it would not is what turned
this up: XDG says **where** a file goes, not **who may read it**, and nothing in this corpus has
ever said the second thing.

`plan-docs` keeps a two-tier store. The sensitive tier exists for exactly one reason: to hold
employer and client work outside every working tree, so it cannot be committed to a repo that gets
published, and it deliberately has no remote. That is a confidentiality design, and every part of it
is implemented except the filesystem mode underneath.

## Evidence

**No `mkdir` in the corpus passes a mode.** Checked across all five scripts (`plans.py`,
`library.py`, `harvest.py`, `fitness.py`, `audit.py`): every call is
`mkdir(parents=True, exist_ok=True)`, so the mode is the default masked by the process umask.

**Measured on this machine, 2026-09-03** (umask `002`):

| path                | mode    | what it holds                        |
| ------------------- | ------- | ------------------------------------ |
| `~/plans-sensitive` | **775** | employer and client plans            |
| `~/plans`           | 775     | the shareable tier                   |
| `~/research`        | 775     | third-party clones                   |
| `~`                 | 755     | nothing above gates any of the above |

So the tier whose whole purpose is confidentiality is world-readable and group-writable, and `$HOME`
does not gate it either.

**Neither `SKILL.md` nor `design-rationale.md` mentions permissions, a mode, or `chmod` anywhere.**
This is not a rule that was written and missed; the dimension was never considered.

[DECISION: **the controls the design actually leans on are intact — verified, not assumed, before
calling this an exposure.** `~/plans-sensitive` is a git repo with **no remote configured**, so
nothing can push it. The shareable store's remote is `TheodoreAD/plans`, confirmed **private** via
`gh api`. The confidentiality design is holding at the layer it was designed at. What was never set
is the layer below it.]

[PITFALL: **severity is low here and that is a property of this machine, not of the design.** This
box has exactly one non-system account (uid 1000) and the `tdumitrescu` group has no other members,
so no other human can read the store. What can is any process running under a **different uid** — a
service account, a container bind-mounting `$HOME`, a backup or sync agent. The exposure becomes
real the moment the sensitive tier is used on a shared or work machine, which is precisely the
population it was designed for. Reading the local `775` as harmless because this laptop is
single-user is reading the wrong machine.]

## Decisions

[DECISION: **`0700` by content, not by a list of directories.** Both plan stores get it — the
sensitive tier obviously, and the shareable tier because "shareable" means shareable with the people
you choose, not readable by any local uid, and it costs nothing. `$RESEARCH_HOME` does **not**: it
holds clones of public third-party repos, so `0700` there protects nothing and would be a gesture,
and a rule that does visibly meaningless things is a rule that gets copied without thought. This is
rule 8 of `2026-09-03-where-skills-put-things-on-disk.md` restated rather than an exception to it —
the mode follows the content, which is why the answer differs per store without the rule differing.]

[DECISION: **`install` creates with the right mode; `doctor` reports and never fixes.** These are
not two answers to one question, they are two commands. Creating a directory correctly is not
"fixing" anything, so `install` simply passes `mode=0o700` and there is nothing to decide there.
`doctor` is documented read-only, and a silent `chmod` would both break that contract and override a
widening the user may have chosen for a reason the tool cannot see — a `plans` store shared with a
second account of their own, say. It reports the mode it found and the one-line `chmod` to run.]

[DECISION: **it is a corpus rule, and it goes in `skill-authoring`** beside the destination table
from `2026-09-03-where-skills-put-things-on-disk.md`. Every skill that creates a directory for a
user's data has this gap; writing it only into `plan-docs` fixes the instance and leaves the class.
One sentence: a skill that creates a directory for the user's own data states its mode, and it is
`0700` when the content is private.]

## Recommended direction

**Create the store root with an explicit mode, and `chmod` the two that exist.**
`mkdir(parents=True, exist_ok=True, mode=0o700)` is the whole code change. Two details worth having
written down:

- A umask can only ever **narrow** a mode passed to `mkdir`, never widen it, so `0o700` is safe to
  pass unconditionally — no umask handling needed.
- Python's `parents=True` **does not** apply `mode` to the intermediate directories it creates, only
  to the final one. That does not matter here, because a store root at `0700` blocks traversal to
  everything beneath it whatever those children's own modes are. It would matter if the mode were
  set on a leaf instead, which is the version to avoid.

**And say it in the skill.** The tier table describes what each store is _for_; it should say what
each is created as, because a reader who moves a store, restores one from a backup, or creates one
by hand gets whatever their umask hands them and nothing tells them that is wrong.

[DEFERRED: **XDG is a separate question and does not answer this one.** The spec does carry a single
permission sentence — a missing destination directory "should be created with permission mode 0700"
— but the protection there is the `0700`, not the path, and it can be passed today without moving
anything. What XDG would genuinely buy is predictable override-respecting locations and not
scattering top-level dotfiles. One caution if the sensitive store ever does move under
`~/.local/share/`: sitting among ordinary application data makes it **less** conspicuously separate,
and part of why it has never been backed up or synced by accident is that it is conspicuous. If it
moves, the `0700` matters more, not less.]
