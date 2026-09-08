---
status: landed
updated: 2026-09-08
---

# Text-only reference clones: skip what a grep skips anyway

## Context

Asked for by the user 2026-09-07: _"look into sparse checkout, i.e. without binary files that
wouldn't be greppable either way. we don't want to run anything, just search text."_

That reframing is the whole plan. The earlier size work
(`2026-09-07-research-library-clone-size.md`) treated sparse checkout as a **path** question and
parked it as too risky, because excluding a directory means a grep silently does not see it —
silent, which is the failure this corpus weighs heaviest. Excluding files a text search **already
skips** carries no such risk: ripgrep and grep both treat a file containing a NUL byte as binary and
skip it, so those bytes buy a search nothing at all. The saving is free by construction.

Everything below is measured. The mechanism probe changed the design and it also corrects a
conclusion the earlier plan recorded as settled.

### Scope, stated first because "exclude binaries" reads wider than it is

Raised by the user on reading the first draft: the library holds PDFs, epubs and other ebook formats
in their own right. Two boundaries follow, and neither is optional.

**Sparse patterns reach `repos/` and nothing else.** `docs/` (6 entries, 4 MB — PDFs with their
provenance files) and `pages/` (3 entries, 1 MB — mirrored doc snapshots) are loose files that no
git clone contains, so a sparse-checkout pattern cannot touch them and must never be described as if
it could. Those buckets exist precisely to hold material that is not greppable source, and the 41%
figure below is measured over `repos/` only.

**And "not greppable" is the wrong criterion for a document.** A PDF is binary to ripgrep and is
still readable by an agent — Claude reads PDFs natively — so the real line is not
greppable-versus-not but **document versus demo asset**. Nine PDFs sit inside repo clones today,
including a 4.8 MB `flameshot-documentation.pdf` that is exactly the reference material this library
exists for. They total **6.6 MB, 0.52% of the ungreppable bytes**, so keeping every one of them
costs half a percent of the saving and removes the only case where this exclusion could lose
something a reader wanted. `!*.pdf` came out of the pattern list for that reason.

## What the measurements say

### 1. 41% of the library's working trees cannot be searched

Across all 77 repo entries, working trees only (`.git` excluded), classifying a file as binary by
the same NUL-byte rule ripgrep uses:

|                     |                    |
| ------------------- | ------------------ |
| working trees total | 2,959 MB           |
| greppable text      | 1,722 MB           |
| **ungreppable**     | **1,236 MB (41%)** |

By extension, the top of the excluded weight: **PNG 560 MB across 6,584 files**, MP4 181 MB (27
files), GIF 180 MB (58), `.so` 78 MB (9), JPG 59 MB (133), `.dex` 25 MB (4).

Ten entries hold more than 20 MB of ungreppable bytes each, and most of them are mostly that:

| entry                                    | ungreppable | of tree | share |
| ---------------------------------------- | ----------- | ------- | ----- |
| `block/goose`                            | 309 MB      | 342 MB  | 90%   |
| `RooCodeInc/Roo-Code`                    | 275 MB      | 292 MB  | 94%   |
| `betawatch/tandroid`                     | 115 MB      | 239 MB  | 48%   |
| `sst/opencode`                           | 75 MB       | 125 MB  | 59%   |
| `shanraisshan/claude-code-best-practice` | 69 MB       | 73 MB   | 94%   |
| `intellectronica/ruler`                  | 68 MB       | 70 MB   | 97%   |
| `Aider-AI/aider`                         | 65 MB       | 74 MB   | 88%   |
| `Futsch1/medTimer`                       | 41 MB       | 44 MB   | 92%   |
| `cline/cline`                            | 25 MB       | 55 MB   | 46%   |
| `google-gemini/gemini-cli`               | 23 MB       | 102 MB  | 22%   |

### 2. The biggest entry is the counterexample, and that settles the scope

`nodejs/node` is **2% binary** — 15 MB of a 668 MB tree. Its 675 MB `deps/` is vendored V8 and
OpenSSL **source**: greppable text, every byte of it. So the two levers hit disjoint sets:

- **type exclusion** saves 309 MB on `goose`, 275 on `Roo-Code`, 115 on `tandroid` — and 15 on
  `node`;
- **path exclusion** saves 675 MB on `node` — and little anywhere else.

Neither subsumes the other, and only the first is safe. This plan is the first one; the second stays
where it was, unresolved and correctly so.

### 3. Git can express it, and the saving is 48×

Probed on `intellectronica/ruler` (97% binary), three clones of the same commit:

| clone                                              | `.git`     | working tree | files | total     |
| -------------------------------------------------- | ---------- | ------------ | ----- | --------- |
| `--depth 1`                                        | 71,196 KB  | 72,960 KB    | 257   | ~144 MB   |
| `--depth 1 --sparse` + type patterns               | 71,204 KB  | **2,348 KB** | 256   | ~72 MB    |
| `--depth 1 --filter=blob:none --sparse` + patterns | **644 KB** | **2,348 KB** | 256   | **~3 MB** |

**`grep -rIl ruler` returns the identical 185 files in all three.** One file was excluded: a 69 MB
`.gif`.

Patterns are `sparse-checkout set --no-cone '/*' '!*.png' '!*.jpg' …` — **non-cone mode**, because
cone mode matches directories and the criterion here is file type.

The probe's list carried `!*.pdf`; the shipping list must not, per the scope note above. Nothing
else about the measurement changes — the excluded file in this repo was a 69 MB `.gif`, and document
formats are 0.52% of the excluded weight library-wide.

### 4. The correction: `blob:none` is useless alone and transformative with sparse

The earlier plan recorded, correctly measured and wrongly generalised: _"A blobless partial clone
saves nothing here — `--depth 1` and `--depth 1 --filter=blob:none` both produce 6 MB. Ruled out,
with a number."_ That is true **without** a sparse set, because the checkout materialises every blob
at HEAD, so the filter has nothing left to defer.

With a sparse set the excluded blobs are never wanted, so they are never fetched — which is the
difference between row 2 and row 3 above, `.git` going from 71,204 KB to 644 KB. **The two are
useless separately and transformative together**, and the earlier "ruled out" line has to be
corrected rather than left standing: it is the kind of settled-looking negative result that stops
anyone re-testing the combination.

### 5. The existing update path survives it

`fetch --depth 1` + `reset --hard FETCH_HEAD` on the sparse blobless clone: `.git` 664 KB, tree
2,348 KB, 256 files, `core.sparseCheckout` still true and the pattern list intact. So
`library.py update` needs no special case — the entry stays text-only across refreshes on its own.

## What landed

`add` clones text-only by default: `--depth 1 --filter=blob:none --sparse` and then the non-cone
pattern set, `text-only: yes` in `SOURCE.md`, `--all-files` per call and `RESEARCH_TEXT_ONLY=0` per
machine. `check` reports both directions of drift. `size --ungreppable` measures by content.
`update` was not touched.

**Verified end to end 2026-09-08 with the shipping pattern list**, `intellectronica/ruler` cloned
both ways at the same commit — the measurement that matters most, because the whole safety argument
is that a text search cannot tell the difference:

|                              | text-only  | `--all-files` |
| ---------------------------- | ---------- | ------------- |
| on disk                      | **3.0 MB** | 141 MB        |
| `.git`                       | **644 KB** | 70 MB         |
| files in the working tree    | 257        | 258           |
| files `grep -rIl .` can read | **257**    | **257**       |
| `grep -rIl ruler`            | **190**    | **190**       |

The searchable sets are **identical, file for file**, and the one file the exclusion removed is a 69
MB `.gif`. A refresh afterwards left `core.sparseCheckout` true and the pattern list intact, so
measurement 5 holds against the real code and not only the probe.

Re-measured over the library at 86 entries while building `--ungreppable`: **1,286 MB of 3,274 MB of
working tree, 39%**, against 41% of 2,959 MB when this plan was written. `nodejs/node` is still the
counterexample at 15 MB of 669.

[DECISION: **text-only is the default**, `--all-files` opts one clone out, `RESEARCH_TEXT_ONLY=0`
opts a machine out. Asked 2026-09-08; the user's answer was that there are no consumers but
themselves across several machines, so the general rule against moving a published tool's default
under its consumers has nothing to protect here yet — _"we should make it default, with opt-out via
command line, but allow configuration to flip that if needed"_. The configuration is one env var
rather than a config file: the library already has exactly one (`RESEARCH_HOME`), and a second
mechanism for a single boolean would be the larger change.]

[DECISION: `--no-cone` is safe to build on for now, and the fallback is written down rather than
rediscovered. Read 2026-09-08 in git's own tree: `Documentation/git-sparse-checkout.adoc` says
outright _"For all these reasons, non-cone mode is deprecated. Please switch to using cone mode"_,
and `Documentation/BreakingChanges.adoc` does not mention sparse-checkout at all — deprecated in the
docs, scheduled for removal nowhere. Cone mode is not an alternative: it matches directories and the
criterion here is file type. If removal is ever scheduled, the fallback is writing
`.git/info/sparse-checkout` and setting `core.sparseCheckout` directly, which is the same mechanism
one layer down and is plumbing rather than the deprecated porcelain.]

[DECISION: the pattern list is a constant in `library.py`, `UNGREPPABLE_EXTENSIONS`, with no
per-entry override. It is organised by category rather than by what this library happens to hold, so
it covers a repo nobody has cloned yet; the measured tail it deliberately does not chase is per-repo
oddities — `.binobj`, `.tgv`, `.res` — worth under a megabyte together. The override waits for an
entry that actually needs it.]

[DECISION: the keep-list is `pdf`, the ebook formats (`epub`, `mobi`, `azw3`, `djvu`, `chm`) and the
office containers (`docx`, `xlsx`, `pptx`, `odt`, `ods`, `odp`) — binary to a grep and kept anyway,
because an agent reads them and the line is document-versus-demo-asset. Measured cost of keeping
every one: 9 PDFs inside repo clones, 6.6 MB, **0.5% of the excluded weight**. `.svg` needs no entry
at all and is the tell that this is a judgement about purpose constrained by a fact: it is text, so
the NUL rule keeps it whatever anyone thinks of it as a demo asset.

Worth recording because it caught the count: a NUL scan finds **eight** of those nine, because one
PDF carries no NUL in its first 8 KB and ripgrep searches it as text. The NUL rule is a property of
a file, not of a format — which is precisely why the keep-list is a stated judgement rather than
something derived from a scan of what happens to be on disk.]

[DECISION: the extensionless residue is the answer, and no size-based second filter is added.
Measured library-wide rather than on `node` alone: 620 files and 16 MB, **1.25% of the ungreppable
weight**. What the residue costs is that the patterns cannot prove an entry holds no ungreppable
bytes — so `size --ungreppable` classifies by **content** instead, which is a different rule from
the exclusion list on purpose. The report can therefore contradict the patterns, which is the only
way the gap stays visible.]

[DECISION: case variants are not in the pattern list. Git matches sparse patterns case-sensitively,
so `IMG.PNG` survives; measured 2026-09-08, 4 files and 0.3 MB of the whole library carry an
uppercase extension — 0.02% of the excluded weight, against doubling the list.]

[DECISION: a `docs/` or `pages/` entry needs no rejection of `--all-files`, because `add` only ever
creates repo entries and the flags are unreachable from those buckets. It becomes real only if
`provenance` ever grows a fetching half, and belongs to that change rather than to this one.]

[DECISION: a failed `sparse-checkout set` runs `sparse-checkout disable` and then raises. A
`--sparse` clone starts with only its root files checked out, so the untreated failure leaves an
entry that is present, is a real git clone, passes every check the script makes, and holds almost
none of the repo — the store's characteristic silent shape. The provenance file is written before
the raise, so the entry ends up complete and conformant while the run ends up loud.]

## The retrofit, run 2026-09-08

The existing library was re-cloned entry by entry rather than left as the plan's largest loose end.
Seven entries, chosen by ungreppable **share** rather than by total size — which is the correction
the new column paid for immediately, since `npm/cli` is the fourth-largest entry in the store and
only 15% ungreppable, so it would have been picked by every ranking that did not have this number:

| entry                                    | before | after  | reclaimed  |
| ---------------------------------------- | ------ | ------ | ---------- |
| `block/goose`                            | 638 MB | 42 MB  | 596 MB     |
| `RooCodeInc/Roo-Code`                    | 464 MB | 22 MB  | 442 MB     |
| `sst/opencode`                           | 204 MB | 63 MB  | 141 MB     |
| `intellectronica/ruler`                  | 140 MB | 2 MB   | 138 MB     |
| `shanraisshan/claude-code-best-practice` | 135 MB | 6 MB   | 130 MB     |
| `Aider-AI/aider`                         | 139 MB | 11 MB  | 128 MB     |
| `Futsch1/medTimer`                       | 84 MB  | 4 MB   | 80 MB      |
| **total**                                | 1.8 GB | 150 MB | **1.7 GB** |

Store-wide: **4,728 MB → 3,073 MB**, and ungreppable **1,286 MB (39%) → 380 MB (16%)**. `check`
reports the same four pre-existing findings as before and no new ones. `goose` still answers a real
search — `rg -c recipe` over it returns 8,878 matches across 309 of 1,990 files.

Three things the run established that a design discussion would not have:

**A re-clone destroys the provenance, and three of the seven carried multi-line hand-written notes**
— why a decompile is tracked per release, why a candidate was cloned during a prior-art survey. An
`add --note` would have flattened each onto one line. The working shape is to restore the old file
whole and then rewrite only `ref`, `fetched` and `text-only` through `set_provenance_field`, which
is the line editor that already exists for exactly this and leaves a `note: |` block untouched.

**`betawatch/tandroid` was excluded, and it is the case that makes a blanket `--retrofit` wrong.**
It is 115 MB ungreppable of a 239 MB tree, so every size heuristic selects it — and its own note
says it is a decompile of a specific shipped Telegram beta, tracked per release. Re-cloning changes
_which build the entry is_. That is a content decision wearing a disk decision's clothes, and no
threshold can tell the two apart.

**The verification that mattered is not a size comparison.** Sizes only say something got smaller.
`git ls-files -t` names every path git actually excluded, and asserting each one's extension is in
the list is what would catch a pattern doing something unintended. It passed on all 1,883 excluded
paths across the seven entries, which is a far stronger statement than any of the megabyte figures.

[DECISION: no `--retrofit` command. The operation is a loop over `add`, and the two things it has to
get right — preserving a hand-written provenance, and not re-cloning an entry that is pinned to a
particular upstream state on purpose — are a judgement per entry rather than a flag.
`size
--ungreppable` supplies the ranking, and a session that wants this runs the loop with the
ranking in front of it, as this one did.]

## Migrated to

- **`skills/research-library/references/rationale.md`**, "Text-only clones: what the retrofit
  settled, and why there is no command for it" — the rejected `--retrofit`, the entry that every
  size heuristic selects and no threshold may re-clone, the provenance-restore shape a hand-run
  needs, the `git ls-files -t` verification that beats any size comparison, and the default-on
  decision together with the condition that would reopen it.
- **`skills/research-library/SKILL.md`**, "Clones hold text, because that is all anyone searches"
  and "What the library costs" — the mechanism, the end-to-end verification, the document keep-list,
  the drift reporting, and the correction to the earlier plan's "`blob:none` saves nothing".
- **`skills/research-library/scripts/library.py`** already held the decisions that constrain the
  code: the non-cone deprecation and its fallback in `sparse_patterns()`, the disable-then-raise on
  a failed `sparse-checkout set`, the category-organised pattern list, the case-sensitivity
  measurement, the NUL-rule-is-a-property-of-a-file finding beside `DOCUMENT_EXTENSIONS`, and the
  extensionless residue in `cmd_size`. Each was verified present during this retirement rather than
  assumed.
- **`plans/2026-09-07-research-library-clone-size.md`**, which stays open — the path-exclusion half,
  which was never this plan's, and the one thing this work hands it.

Not migrated: the measurement tables. The library moves, so the numbers are evidence for decisions
that have now been taken rather than facts worth keeping current; the ones that still do work are
quoted at the decisions they support.

## What is still deliberately not done

**Path exclusion.** A different lever on an almost disjoint set of entries, and the unsafe one:
excluding a directory means a grep silently does not see it. It stays where it was, in
`2026-09-07-research-library-clone-size.md`, unresolved and correctly so. One thing this work does
hand it: `check` now reports any sparse checkout that nothing records, whatever narrowed it — which
is the "so the grep saw everything is never assumed" half that plan named as the middle answer worth
testing.
