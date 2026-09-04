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

[NEEDS CLARIFICATION: **is "the repository" or "this checkout" the right identity for a plan?** Both
are defensible and the answer decides the `plan-docs` fix. Keying on the repository
(`--git-common-dir`) means every worktree of a repo shares one mirror and one `absorb` queue, which
matches how a human thinks about "the repo's plans" and makes a plan written on a feature branch
visible from main. Keying on the checkout is what happens today, and has one real virtue: a plan
written in a worktree is about the work in that worktree. The store case looks clearly like the
first; the `mode = "repo"` case already behaves like the second for free, because the plan file
travels with the branch it was committed on. So the likely answer is "repository, for the store
mirror only" — but that asymmetry needs stating explicitly or it reads as a bug.]

[NEEDS CLARIFICATION: **should a worktree be reported, or silently normalised?** A session that does
not know it is in a worktree is the one this plan is about, so there is a case for
`plans.py where`/`doctor` naming it outright. Against: a line printed on every command in a
perfectly healthy worktree is the "warning nobody can act on" this corpus keeps deleting. Probably
`where` and `doctor` say it, and the routing commands just do the right thing.]

[NEEDS CLARIFICATION: **can `audit.py` know a slug is a worktree at all?** It reads transcripts
offline, long after the directory may be gone, so it cannot ask git. The only signal in the data is
the slug's own shape — a `-claude-worktrees-` segment for the Claude Code pattern, and nothing at
all for a sibling worktree. That means a partial fix for one directory pattern and no fix for the
other, which may be worse than a declared limitation.]

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
3. **Teach `walk_projects` that a linked worktree is not a repo.** Promoted above the identity
   question because it needs no decision from it and is the biggest measured damage: `.git` as a
   file whose `gitdir:` names `…/.git/worktrees/…` is the whole test, no subprocess, at the one
   `(path / ".git").exists()` call the walk already makes. Fixes `repos` counting one repo as three
   and keeps branch names out of the private term list. Guard the submodule case
   (`…/.git/modules/…`), which is `.git`-as-a-file too.
4. **Decide the identity question, then key the store mirror off `--git-common-dir`** — resolving to
   the main checkout's `rel` for every worktree of that repo. `fitness.py`'s existing call is the
   shape to copy; it is three lines and no new dependency.
5. **Add the worktree row to `session-harvest` step 0's table**, and teach `find_checkout` to say
   which working tree it resolved. The existing table already has the vocabulary — a worktree on a
   feature branch is "clean, ahead by commits" wearing a different hat.
6. **Say it in `skill-authoring`**: a skill edited in a worktree is not installable until its branch
   is what the remote's default branch holds, so the deploy sequence needs either a merge first or
   the local-path install (`skills add ../my-skills`) it already documents for drafting.
7. **Declare the limit in `session-bash-audit`** beside the Windows slug paragraph added the same
   day, since it is the same defect with a different cause: an own-repo row that reads clean because
   the comparison could not fire.

Out of scope here and worth filing separately: `~/AGENTS.md` states that parallel sessions on this
machine **share one working tree**, and several of its rules — undo by SHA rather than a relative
ref, "nothing of theirs to reset", the caution about checking out an old commit — are reasoned from
that. Worktrees make it false. That belongs to `power-user-linux-setup`, not here.
