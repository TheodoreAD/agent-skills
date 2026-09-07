---
status: idea
updated: 2026-09-07
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

## Open questions

[NEEDS CLARIFICATION: is text-only the **default** for new entries, or opt-in? The library's stated
purpose is text search, the excluded bytes are useless for it by construction, and 41% is a large
number to leave on the floor by default. Against: changing what a tool already does belongs behind
an opt-in, and an entry someone later wants an image out of would surprise them. Leaning default-on
with `--all-files` to opt out, but it is a real decision and the reason to file rather than assume.]

[NEEDS CLARIFICATION: is `--no-cone` safe to build on? Git documents cone mode as the recommended
one and non-cone as legacy; the probe printed no warning on this version, but a deprecation that
lands later would break every entry cloned this way. Check what git actually says about removal
before this becomes the default, and know what the fallback is — most likely writing the sparse
pattern file under `.git/info/` directly, which is the same mechanism one layer down.]

[NEEDS CLARIFICATION: where does the pattern list live, and who edits it? A constant in `library.py`
is one answer and covers the measured 95% (PNG, MP4, GIF, JPG, `.so`, `.dex`, fonts, archives). A
per-entry override in `SOURCE.md` would handle the repo whose `.bin` fixtures are actually the thing
being read. Start with the constant, and only add the override when an entry needs it.]

[NEEDS CLARIFICATION: extension patterns cannot catch an extensionless binary, and the measurement
used content. `nodejs/node` carries 607 extensionless binary files, totalling under 1 MB, so the gap
is real and currently worthless — but it means `check` cannot verify "this entry holds no
ungreppable bytes" from the patterns alone. Is that worth a size-based second filter
(`--filter=blob:limit=`), or is under-1-MB residue simply the answer?]

[NEEDS CLARIFICATION: what happens to the 1.2 GB already on disk? Sparse can be applied to an
existing clone and reclaims the working tree; the blobs are already in the pack, so the `.git` half
needs a re-clone. That makes retrofitting a per-entry choice between a partial saving now and a
re-download — worth quantifying before offering a `--retrofit` anything.]

## Recommended direction

1. **`add --text-only`** (name provisional): `--depth 1 --filter=blob:none --sparse`, then the
   non-cone pattern set, recorded in `SOURCE.md` so `check` can report which entries are text-only
   and nobody has to infer it from a file listing.
2. **Nothing in `update` changes** — measurement 5 says the shape survives a refresh untouched.
3. **`size` grows an ungreppable column**, which is where the 41% came from and is what makes the
   case for retrofitting any given entry concrete rather than rhetorical.
4. **Leave path exclusion alone.** It is a different lever on a different set of entries, it is the
   unsafe one, and the two should not be decided together just because both are spelled
   `sparse-checkout`.
5. **Correct the earlier plan's `blob:none` line** as part of this work, not after it.
