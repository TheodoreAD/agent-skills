---
status: in-progress
updated: 2026-09-04
---

# Every script here reads a checkout path as a repo identity, and a worktree is a second one

## Context

Asked by the user 2026-09-04: account for git worktree directory patterns in `plan-docs` and the
adjacent skills.

Every script in this corpus answers "which repo am I in" with `git rev-parse --show-toplevel`, and
then treats the path it gets back as the repo's **identity** — the key a store mirror is named
after, the string an own-repo comparison is made against, the directory an installed-vs-checkout
diff is taken from. That holds exactly as long as a repository has one working tree.

A linked worktree breaks the equation without breaking anything visibly: `--show-toplevel` returns
the worktree, every routing decision downstream is made against a path the main checkout has never
seen, and every verdict still comes back `ok`. **The failure mode throughout is silence** — not a
wrong answer a reader can argue with, but a correct-looking answer about a different repo.

Two directory patterns matter and they fail differently, which is why the plan is about patterns
rather than about worktrees:

- **inside the repo** — `<repo>/.claude/worktrees/<name>`, which is where Claude Code's own
  `EnterWorktree` puts them. The nesting is what does the damage: the worktree path _contains_ the
  main repo path, so anything deriving identity by relative path produces a longer, still
  plausible-looking key.
- **beside the repo** — the shape every other tool produces, and the one this corpus handles worst.
  It is invisible to the nesting problems above and instead reads as a **second clone** to anything
  that walks a projects root.

The sibling shapes are worth naming individually, because "beside the repo" is three conventions
rather than one. Surveyed 2026-09-04:

| shape                                             | who produces it                                     |
| ------------------------------------------------- | --------------------------------------------------- |
| `<repo>.worktrees/<name>` (a grouped sibling dir) | **VS Code's built-in worktree support, by default** |
| `<repo>-<branch>`, flat beside the main checkout  | a human at the shell; the most-cited convention     |
| `<repo>/<repo>.git` + `<repo>/<branch>/`          | the bare-clone parent layout                        |
| `~/worktrees/<project>/<branch>`                  | centralising tools, and an open VS Code request     |

VS Code's is the one to design for, because it is a default rather than a preference: its worktree
test plan states "the default worktree path is a directory the same level as your main repo, named
`<repoName>.worktrees`, and the name of your worktree is the last part of the path", and the request
to make that configurable (microsoft/vscode#293884, Feb 2026) is still open and unanswered. So a VS
Code user who makes a worktree at all gets `<repo>.worktrees/` unless they retype the path.

Worth recording that the pattern advice runs directly against Claude Code: the widely-cited
best-practice guide recommends the flat sibling layout precisely because nesting a worktree inside
the main checkout "leads to confusing `.git` resolution and can break tools that walk up the
directory tree" — which is this plan, arrived at from the outside.

## Evidence — measured 2026-09-04, throwaway repos, nothing in this repo touched

**What git reports.** From `<repo>/.claude/worktrees/wt`:

| command                       | main checkout | linked worktree              |
| ----------------------------- | ------------- | ---------------------------- |
| `rev-parse --show-toplevel`   | the repo      | **the worktree**             |
| `rev-parse --git-common-dir`  | `.git` (rel.) | `<repo>/.git` (**absolute**) |
| `rev-parse --git-dir`         | `.git`        | `<repo>/.git/worktrees/wt`   |
| `.git` at the top of the tree | a directory   | **a file**                   |

`--git-common-dir` is the one that identifies the _repository_ rather than the checkout, and it is
already what `fitness.py` uses (for `FETCH_HEAD`); its `cwd / common` idiom is correct in both
columns, because a `Path` joined with an absolute path yields the absolute one. That makes
`materialize_ref` the only worktree-correct site in the corpus, and the model for the rest.

**`plan-docs` routing, called directly against a real worktree** (`plans.resolve`, fake config,
`projects_root` a temp dir):

```
--- main checkout ---           --- worktree ---
verdict:   ok                   verdict:   ok
rel:       <root>/demo          rel:       <root>/demo/.claude/worktrees/wt
store_dir: <store>/<root>/demo  store_dir: <store>/<root>/demo/.claude/worktrees/wt
rule from: roots entry          rule from: roots entry
```

The root rule still matches, because `_match_rule` walks prefixes — so the verdict is `ok` and
nothing warns. But the store mirror is a **different directory**, which means for any repo routed to
the store (every employer and client repo, the population the store exists for):

- a plan written from a worktree lands where the main checkout's `list` and `absorb` never look;
- a plan filed **for** that repo by another session lands in the main mirror, where the worktree
  session's `absorb` never looks;
- both directions are silent, and `absorb`'s "1 plan awaits absorption" prompt is what would
  normally catch a lost plan.

**`scan --mode tree` skips a nested worktree, and the skip is swallowed.** `scan_targets` enumerates
with `git ls-files --cached --others --exclude-standard`, which reports the worktree as a single
directory entry with a trailing slash (`.claude/worktrees/wt/`) rather than its files. `read_text`
on that raises `IsADirectoryError`, which is an `OSError`, which the loop's
`except (OSError, UnicodeDecodeError): continue` — there for binaries — discards. So the
confidentiality scanner reports "0 hits over tree" for a tree it did not fully read. Staged mode is
unaffected, and staged mode is what the pre-commit rule actually calls, so this is a gap in the belt
rather than in the braces.

**A nested worktree is untracked, not ignored.** `git status --short` in the main checkout shows
`?? .claude/worktrees/`, and `git add -A` adds it as an embedded git repository with a warning and
exit 0 — `warning: adding embedded git repository`. `.gitignore` here covers `__pycache__`, `.venv`
and friends, not `.claude/worktrees/`.

**The sibling pattern is the worse of the two, and it was the one assumed harmless.** Measured
2026-09-04 against a throwaway root holding one repo `abc` plus both sibling shapes
(`abc.worktrees/feat` and `abc-hotfix`), with `plans.py` pointed at it by a fake config:

- `repos` lists **three repos where there is one**. `visit` enrolls on `(path / ".git").exists()`,
  and a linked worktree's `.git` is a plain file, so it passes. The nested pattern is skipped only
  by the walker's dotted-directory rule — accidental, and it does not save the sibling shapes.
- `where` returns `verdict: ok` from all three, with **three different store mirrors**:
  `<store>/root/abc`, `<store>/root/abc-hotfix`, `<store>/root/abc.worktrees/feat`.
- **A branch name entered the confidentiality term list.** `scan --list-terms` came back
  `abc-hotfix`, `abc.worktrees`, `feat`, `root` — `feat` is there because a worktree directory is
  named after its branch and repo-path segments become private terms. Branch names are short
  ordinary words (`feat`, `main`, `docs`, `test`, `fix`), so this is the corpus's own named failure:
  a gate that flags an ordinary word in every document is a gate that gets switched off. Only
  `MIN_PRIVATE_TERM` kept `abc` itself out.

**Detecting a worktree is free, which retires the objection that it costs a git call per
candidate.** In a linked worktree — both sibling shapes and the nested one — `.git` is a plain
**file** whose whole content is `gitdir: <main>/.git/worktrees/<name>`. The walker already stats
that exact path; reading it when it is not a directory is one small read and no subprocess, and the
line hands back the main checkout directly. `--git-common-dir` agrees (`<root>/abc/.git` from
`abc.worktrees/feat`) and stays the right call anywhere a subprocess is already being spent.

The one trap: **a submodule is also `.git`-as-a-file**, so "file means worktree" is wrong. The
discriminator is inside the line — `…/.git/worktrees/<name>` for a worktree, `…/.git/modules/<path>`
for a submodule (measured: `gitdir: ../../.git/modules/vendor/sub`, and relative, where a worktree's
was absolute).

## Where each skill stands

| skill                | what breaks                                                                         | severity                   |
| -------------------- | ----------------------------------------------------------------------------------- | -------------------------- |
| `plan-docs`          | store mirror keyed on the worktree path; `absorb` misses in both directions         | **silent plan loss**       |
| `plan-docs`          | `scan --mode tree` swallows the nested worktree as an unreadable path               | gap in a safety net        |
| `session-harvest`    | `find_checkout` resolves the worktree; step 0's three-row table has no row for it   | wrong remedy offered       |
| `session-harvest`    | `git status --porcelain` reports `?? .claude/worktrees/` as this repo being dirty   | false positive             |
| `session-bash-audit` | own-repo tags compare path slugs, so a worktree session's `git -C` main-repo calls  | unmeasured, reads clean    |
| `skill-authoring`    | the deploy sequence's push installs nothing: `skills add` clones the default branch | **a change that vanishes** |
| `skill-fitness`      | nothing — `--git-common-dir` already identifies the repository                      | correct today              |

Two of these deserve their own sentence.

**`skill-authoring`'s deploy sequence is the sharpest, because it currently reads as complete.** The
documented loop is edit → gate → commit → push → re-install → verify, and the reason push is called
out is that the installer clones from the remote. From a worktree on a feature branch, push succeeds
and installs **nothing new**: `skills add <owner>/<repo>` takes the default branch, so the verify
step compares an installed copy against a checkout that is ahead of what was ever published. That is
the row this corpus already knows as "clean, ahead by commits" in `session-harvest` step 0 — reached
by a different route, and not currently connected to it.

**`session-bash-audit` fails the same way the Windows slug hazard does**, recorded in that skill on
2026-09-04: an own-repo comparison made on a path slug reports zero when the slug does not match,
and zero reads as adherence. Here the mismatch is structural — a worktree session's project slug
ends in `--claude-worktrees-<name>`, so a `git -C <main checkout>` call from it is never tagged
`git-C-own-repo`, and the rule the tag exists to measure goes unmeasured for exactly the sessions
most likely to break it.

## Open questions

**Settled 2026-09-04 by the user — the repository, for the store mirror only.** Every worktree of a
repo shares one store mirror and one `absorb` queue; `mode = "repo"` is untouched, because a plan
file committed in a worktree travels with its branch and that is already right. The asymmetry needed
no second code path: `rel` is derived from the repository while `repo_root` stays the checkout, and
`repo_dir` was always `repo_root / "plans"`. Stated in `plan-docs`'s own body so it is not read as a
bug. Step 4 below.

**Settled 2026-09-04 as predicted — `where` and `doctor` say it, the routing commands just do the
right thing.** `where` earns the line rather than warning with it: once the store mirror is the
repository's, `rel` names a directory the session is not standing in, and unexplained that reads as
a bug. `doctor` names the checkout a worktree belongs to. Nothing else prints anything.

**Settled 2026-09-04 — no, and it is declared rather than half-fixed.** The slug shape betrays only
Claude Code's layout; VS Code's `<repo>.worktrees/<name>` and the flat `<repo>-<branch>` are
indistinguishable from an ordinary repo name, so a partial fix would make the unfixed layouts read
as verified. `session-bash-audit` carries the limitation beside the Windows one. Step 7 below.

**Settled 2026-09-04 — the sibling pattern needs a fix, not a declaration.** The question as
originally written assumed the walker would have to pay a `git worktree list` per candidate. It does
not: `.git` being a file, and the `gitdir:` line inside it, answer both "is this a worktree" and
"which checkout is it a worktree of" with no subprocess, per the evidence above. And the case for
fixing rather than declaring got stronger once measured — one repo listed as three, three store
mirrors, and a branch name in the confidentiality term list. VS Code producing `<repo>.worktrees/`
by default, with no setting to change it, means this arrives without anyone opting in.

What remains open is only the shape of the fix: whether `walk_projects` should **skip** a linked
worktree outright (one repo, one row, one mirror — the worktree is unreachable as a plan
destination) or **fold** it onto its main checkout (routing from inside it still works, and lands in
the main repo's mirror). Folding is the better behaviour and depends on the identity question above;
skipping is strictly less code and is already correct for `repos`, `doctor` and the term list.

## Recommended direction

Cheapest first, and the first two are worth doing whatever the open questions settle.

1. ~~**Gitignore the nested pattern in this repo**~~ — **done 2026-09-04**: `.claude/worktrees/`
   added to `.gitignore`, which removes the `??` entry from every `git status`, the false dirty line
   from every harvest, and the chance of `git add -A` embedding a gitlink.
2. ~~**Make the `scan --mode tree` skip visible.**~~ — **done 2026-09-04**: `scan_targets` now
   returns a `ScanPlan(targets, unread)`; `UnicodeDecodeError` still skips a binary silently, while
   `IsADirectoryError` and every other `OSError` are collected and printed under the hit count by
   `report_unread`, with the second scan to run. Exit status is still hits alone — an unread path is
   a scan to run, not a leak to redact. `tests/unit/test_plan_store.py` covers both halves against a
   real `git worktree add`, and `plan-docs`'s SKILL.md carries it as a fourth failure mode.
3. ~~**Teach `walk_projects` that a linked worktree is not a repo.**~~ — **done 2026-09-04**, by the
   skip route rather than the fold. `linked_worktree_of` reads `.git`-as-a-file, requires a
   `worktrees` segment in its `gitdir:` line (so a submodule's `…/.git/modules/…` stays a repo), and
   returns the checkout it belongs to; `is_repository`, `visit` and `hides_a_repo` all consult it.
   Verified end to end against a root holding both sibling shapes: `repos` went from three rows to
   one, and the derived term list from `abc-hotfix, abc.worktrees, feat, root` to `root` — the
   branch name is out. `visit` **notes** the worktree rather than dropping it silently, on the
   symlink precedent, so `doctor` prints "a linked worktree of `<checkout>`; plan in that checkout
   instead" without `--strict`. Both sibling layouts are parametrized in the tests, and the
   submodule guard is its own test.
4. ~~**Decide the identity question, then key the store mirror off the repository**~~ — **done
   2026-09-04**. Answered by the user: **the repository, for the store mirror only.** One line in
   `resolve` — `identity = linked_worktree_of(root) or root`, with `rel` derived from it — and the
   asymmetry falls out for free rather than needing a second branch: `repo_root` stays the checkout,
   `repo_dir` has always been `repo_root / "plans"`, so a `mode = "repo"` plan still lands in the
   worktree's own `plans/` and travels with its branch, while `rel` (and therefore the store mirror,
   the tier lookup and rule matching) names the repository.

   `--git-common-dir` was the shape the step proposed; `linked_worktree_of` is used instead because
   step 3 already had it and it costs no subprocess. `where` prints a `worktree:` line, since `rel`
   then names a directory the session is not standing in — that is open question 2 settled the way
   it predicted: `where` and `doctor` say it, the routing commands just do the right thing.

   This also closes the disagreement step 3 opened: `repos`/`doctor` and `where` now agree that the
   repository is the unit.
5. ~~**Add the worktree row to `session-harvest` step 0's table**~~ — **done 2026-09-04**. The table
   went from three causes to four, and `skills-state` prints a `worktree:` line naming the checkout
   it belongs to. `find_checkout` itself was left alone deliberately: resolving to the worktree is
   _correct_, because the source being edited is the one to diff against. What was wrong was the
   remedy underneath it, so the fix is a named row and a printed line rather than a different
   resolution.
6. ~~**Say it in `skill-authoring`**~~ — **done 2026-09-04**, as a PITFALL under step 5 (Push).
   Written as the general rule first — a push is necessary, not sufficient, because the installer
   takes the remote's **default branch** — with the worktree as the case where it bites without
   anyone choosing a branch. Names both directory layouts and gives `--git-common-dir` as the direct
   test.
7. ~~**Declare the limit in `session-bash-audit`**~~ — **done 2026-09-04**, beside the Windows slug
   paragraph, and declared rather than fixed. Recorded there that the tags compare by exact
   equality, so from a worktree a `git -C <main checkout>` call is tagged nothing at all and its
   `cd` equivalent is tagged `cd-other` — the name for the recommended _cross-repo_ form. No fix is
   possible from the data: the script reads transcripts offline and cannot ask git, and the slug
   shape only betrays Claude Code's layout, so half a fix would make the other layouts read as
   verified. Worth noting the claim about that slug is **derived, not observed** — none of the 211
   project directories on this machine is a worktree, so no session here has ever run from one.

Out of scope here and **filed 2026-09-04**: `~/AGENTS.md` states that parallel sessions on this
machine **share one working tree**, and several of its rules — undo by SHA rather than a relative
ref, "nothing of theirs to reset", the caution about checking out an old commit — are reasoned from
that. Worktrees make it false. That belongs to `power-user-linux-setup`, whose store mirror now
holds `2026-09-04-worktrees-break-the-one-working-tree-assumption.md`; a session working there is
offered it by `absorb`. Nothing in this repo waits on it.
