---
status: idea
updated: 2026-09-07
---

# Keeping the research library's clones small, and warning about the ones that will not be

## Context

Asked for by the user 2026-09-07: keep clones shallow on update — or reasonably shallow — since
large repos otherwise become a problem; keep a record of repos that can cause disk-space trouble;
and warn about them when cloning, when updating, and on demand. All of it scriptable.

Measured against the real store before designing anything, because the premise turns out to be half
right in a way that changes what to build.

### What the store actually looks like

71 repo entries, **4.8 GB total**. The largest three are 2.1 GB of that — 43% of the store in three
directories.

| entry             | total  | `.git` | working tree | commits |
| ----------------- | ------ | ------ | ------------ | ------- |
| `nodejs/node`     | 940 MB | 122 MB | ~818 MB      | 1       |
| `block/goose`     | 646 MB | 296 MB | ~350 MB      | 1       |
| `RooCode`         | 473 MB | —      | —            | 1       |
| `aiogram/aiogram` | 33 MB  | 9 MB   | ~24 MB       | **436** |

**70 of 71 entries are at exactly one commit.** Shallowness is not eroding, and the reason is that
the machine's refresher already does the right thing:

```shell
git -C "$repo" fetch --depth 1 origin -q && git -C "$repo" reset --hard FETCH_HEAD -q
```

So the shallow half of the request is, on this machine, already solved — and that is precisely why
it is worth planning rather than implementing blind. Three things follow.

**1. The guarantee is unowned.** `library.py` has `name`, `add`, `provenance` and `check`, and **no
`update`**. The re-shallowing lives in `~/.local/bin/research-update`, a script in a different repo
that `SKILL.md` refers to only as "where the machine provides a refresher on `PATH`". A reader who
installs this skill and nothing else has no refresher at all, so the documented "shallow fetch and
hard reset" is prose they have to implement correctly every time. The skill's own disclosure block
already says "`update` refreshes clones", naming a subcommand that does not exist.

**2. Depth is not where the size is.** `nodejs/node` is 940 MB at **one commit**: 818 MB of that is
the checkout. No amount of re-shallowing touches it. `block/goose` is the other shape — 296 MB of
pack at a single commit, i.e. large blobs rather than long history. A plan that only keeps clones
shallow would report success while the store keeps growing, which is the failure mode this corpus
cares about most: a check that passes because it is measuring the wrong thing.

**3. The refresher will silently destroy a deliberate divergence.** `aiogram` sits at 436 commits
because a session deepened it on purpose to read a dependency's constraint history — a divergence
recorded at the time as a store finding. The next `research-update` run does `fetch --depth 1` over
every entry under `repos/` and would truncate it back to 1, with no warning and nothing to notice
afterwards. Found by measurement while writing this; it is a live hazard in the current tooling, not
a hypothetical.

## Open questions

[NEEDS CLARIFICATION: does `update` become a `library.py` subcommand? It is the natural home — the
skill documents the behaviour, ships a script, and currently depends on a binary in another repo
that no reader of the published skill has. The argument against is that the machine's refresher
already works and a second implementation is a second thing to keep in step. Deciding this settles
where every other item below lands.]

[NEEDS CLARIFICATION: what protects a deliberately-deepened entry from being re-shallowed? The
mechanism has to be something the entry itself carries, because the refresher loops a directory and
has no other memory — a `depth:` or `pinned:` field in `SOURCE.md` is the obvious candidate, since
`provenance` already owns that file and `check` already reads it. Whatever it is, an update that
would truncate history has to say so rather than do it quietly.]

[NEEDS CLARIFICATION: what is "a record of repos that can cause disk space issues" — derived, or
curated? For an entry already on disk it should be **derived**: `du` per entry is exact, needs no
maintenance, and cannot go stale. A curated list only earns its place for the case measurement
cannot reach, which is the pre-clone warning. Keeping both risks two answers that disagree.]

[NEEDS CLARIFICATION: at clone time there is nothing local to measure, so where does the warning's
number come from? GitHub's repo API returns a `size` field, one unauthenticated request for a public
repo — but it reports the **packed repository** size, and this store's worst case is a checkout that
expands far beyond it. Whether that number predicts the on-disk cost well enough to warn on has to
be verified against the four entries above before it is trusted; a warning that is wrong by an order
of magnitude in the reassuring direction is worse than none.]

[NEEDS CLARIFICATION: what is the threshold, and what happens at it — warn, ask, or refuse? The
skill's own conventions point at warn-and-ask (`apt`-shaped: proceed by default, an explicit flag to
skip the prompt), never refuse. But the threshold itself is a judgement: 100 MB would fire on 14 of
71 entries here, 500 MB on 3.]

[NEEDS CLARIFICATION: where does a curated record live, if there is one? The store is **not
version-controlled**, so a list kept there is unbacked-up and invisible to anyone else — the same
gap that makes a half-finished entry undetectable. Inside the skill it ships to strangers, and this
repo's own rule is that a measurement which ships must be labelled as somebody else's rather than
offered as a baseline to compare against. Neither location is obviously right.]

[NEEDS CLARIFICATION: do `--filter=blob:none` or a sparse checkout actually help, and what do they
cost? They are the only levers that touch the 818 MB checkout, and they conflict head-on with this
skill's own "grep the real source, don't trust docs/README prose" rule — a partial clone
materialises blobs on demand (so a grep pulls them anyway, over the network, possibly slower than
having them), and a sparse checkout means the grep silently does not see the paths that were
excluded. Measure one large entry both ways before adopting either; a silent grep miss in a
reference clone is worse than the disk it saves.]

[NEEDS CLARIFICATION: does re-shallowing need a `gc` to reclaim anything? `fetch --depth 1` moves
the shallow boundary but the superseded objects stay in the object store until `reflog expire` and
`gc --prune`. The measured store shows `garbage: 0` and no loose objects, so this is not currently
costing anything here — but it is the mechanism by which a frequently-updated clone would grow at a
constant depth, and it is worth confirming rather than assuming either way.]

## Recommended direction

Rough, and ordered so that each step is useful on its own.

1. **Measure first, in `check`.** A size section — per entry, split `.git` from the working tree,
   sorted, with the store total and a top-N — is pure reporting, needs no decision, and answers
   "when a report is requested" immediately. It also makes every later threshold argument concrete
   instead of hypothetical.
2. **Then `library.py update`,** so the shallow guarantee belongs to the skill rather than to one
   machine's `PATH`. It should do what the existing refresher does, plus the two things that one
   cannot: skip an entry whose provenance marks it deliberately deepened, and report the size delta
   per entry so a clone that grew is visible in the run that grew it.
3. **Then the pre-clone warning in `add`,** once the previous step has established whether a host's
   reported size predicts on-disk cost. Warn and ask; never refuse.
4. **Treat the record as derived wherever it can be.** Curate only what measurement cannot see, keep
   it small, and say plainly in the skill that it is one author's observation rather than a rule.
5. **Leave sparse/partial checkouts to a separate decision.** They are the only thing that touches
   the dominant cost and the only thing that can silently break what a reference clone is for.

The framing worth carrying into the work: **the request names depth, and the measurement says
checkout.** Both are real, they need different mechanisms, and the shallow one is nearly done while
the large one has not been started.
