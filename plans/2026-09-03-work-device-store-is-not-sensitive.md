---
status: landed
updated: 2026-09-12
---

# On a work device the store is not "sensitive", it is just the store

## Context

Stated by the user 2026-09-03: on an employer device everything in `~/plans/` is not sensitive,
because **the corporate context is the entire context**. The company's GitHub sits inside the
corporate security boundary, shielded from the public, and the central store should be committed to
a private repo there — exactly as personal work is committed to a private repo on a personal
machine.

That is a correction to the model, not a request for a flag. **"Sensitive" is a _relative_
classification**: it means "must not go where the other tier goes". On a contractor device the
relation is real — client A's work must not reach client B's remote or a personal one, and the split
is the whole design. On a work device there is nothing to be sensitive relative to. One
organisation, one context, one store.

Raised again 2026-09-12, from the same machine: _"plan docs doctor reports some weird stuff related
to work vs contractor machine and sensitive vs non sensitive"_, together with the question this plan
had not answered — whether the separation between an organisation's repos and the user's own repos
on a corporate GitHub instance is modelled anywhere.

## What the code does today

Measured 2026-09-12 by running the work-device path on a contractor machine
(`PLAN_DOCS_DEVICE=work`), which is what the config key does anyway:

- `doctor` prints the single store as `[sensitive, remote: origin]` and puts `sensitive` in the tier
  column of **every** root, the user's own personal root included. The tier is
  `SHAREABLE if device == CONTRACTOR else SENSITIVE`, stamped once in `load_config`.
- `remote_problems` applies the sensitive tier's posture to that store and **warns on any remote at
  all**: _"one personal remote holding an employer's internal work is the outcome this check exists
  to avoid; a sanctioned destination is fine, a personal one is not."_ On a work device that fires
  forever, on the shape the user calls correct.
- `install` writes the **sensitive-tier README** into that store — "a local git repository with no
  remote, deliberately… several clients' internal architecture" — because the README is keyed on the
  tier.
- `install --explain` prints `keep <store> [sensitive] (git repository, no remote)`, where the "no
  remote" half is derived from the tier rather than read from the repository, so it is false on a
  store that has one. It also still asks the `shareable_roots` question, which SKILL.md says stops
  applying on a work device.
- `list`, `where --json` and `config show` all carry the tier too. `where`'s prose output is already
  correct: _"device: work — one organisation, so one store and no tier to choose"_.

It does not refuse anywhere, which is better than it first looked. But the machine is told the wrong
thing in five places, and the one check that matters fires on the right behaviour.

[PITFALL: **a check that fires on correct behaviour is worse than no check**, because it is trained
away rather than read. This one has the shape exactly: the only sensible destination on a work
device is the corporate host, so the first thing a user learns is that this warning is noise — and
the day a genuinely personal remote appears, the message is indistinguishable from the one they have
been ignoring for months. The risk it guards is real and does not go away on a work device; the
check as written cannot see it.]

## Design

### 1. The tier vocabulary stops applying on a work device

[DECISION: **a third tier value, `single`, rather than either of the two alternatives.** Settled
2026-09-12. Keeping `sensitive` internally and hiding it at the print sites leaves the field saying
something false, and the next reader re-derives "the work store is sensitive" from it; making `tier`
meaningless and having every reader ask `split_by_sensitivity` first touches routing, `where`,
`new --for`, `archive` and `uninstall` for no gain, since those need _a_ key whatever it is called.
A third value keys the README and the store lookup honestly and changes nothing structural.]

[DECISION: **human output on a work device prints no tier at all, and `--json` emits `tier: null`
rather than `"single"`.** A consumer reading `"single"` would have to know it is not a sensitivity
claim; `null` cannot be misread, and the human line —
`store: <path> (from $PLANS_HOME) [remote:
origin]` — says everything a one-store machine has to
say.]

Concretely: `tier_of` returns the new value when `split_by_sensitivity` is false; `store_of` keeps
answering with the single store for any tier asked; `STORE_README` gains an entry written for a work
device (one organisation, one store, full history, a remote only where it is sanctioned, and the
reminder that keeping the target repo private is the user's own step); `misfiled_plans` compares the
new value against itself and so still reports nothing, as today.

### 2. `install` stops asking about a split that does not exist

`install_decisions` drops the `shareable_roots` question when `split_by_sensitivity` is false —
SKILL.md already claims this and the code does not do it — and `explain_install` reads the
repository's actual remotes for its `(no remote)` note instead of inferring it from the tier.

### 3. `sanctioned_remotes`: the check asks _which_ remote, not _whether_

The key is per-machine config, like everything else in this file, and governs the **guarded store
only**: the single store on a work device, the sensitive tier on a contractor device.

[DECISION: **the guarded store only, leaving the shareable tier exactly as it is.** Settled with the
user 2026-09-12. The shareable tier is allowed a remote by design and is gated on _content_ by
`scan`, which is a different question from destination; checking it too would change behaviour on a
machine that works today and add a row nobody asked for. This also makes the key the hook the
sensitive tier's durability plan already wants for an external drive —
`2026-08-29-sensitive-tier-durability.md`, whose recommendation ends "the check either learns which
remotes are sanctioned".]

[DECISION: **an entry is a segment prefix of the remote's parsed identity, or a path prefix for a
destination that has none.** `<host>`, `<host>/<owner>` or `<host>/<owner>/<repo>`, matched
segment-wise against `parse_remote`'s `host` and `owner`, so one entry can cover a whole instance,
one namespace on it, or exactly one repository. An entry beginning with `/` or `~` is matched as a
path prefix instead, because `parse_remote` returns **None** for a local path and for `file://` —
deliberately, and that is the shape an external drive or NAS arrives in.]

[DECISION: **a bare owner with no host is refused at `config set` time, with the reason in the
message.** `own_accounts` matches a bare account name on any host on purpose — that is what makes
one entry cover github.com and an enterprise instance — and reusing it here would be the exact hole
this check exists to close: a bare name cannot tell `<corp-host>/<you>` from `github.com/<you>`, and
only the first is inside the corporate boundary. The refusal is code rather than documentation
because the mistake is silent: the config would be well-formed and the check would pass.]

[DECISION: **unset means today's behaviour — every remote on the guarded store warns — not
silence.** A machine nobody has configured must keep the protection it has. What changes is that the
message carries the `config set` line that answers it, so it becomes a decision made once instead of
a row that trains its own dismissal.]

A matched remote drops out of `doctor`'s problems and is annotated where the store is printed:
`remote: origin (sanctioned)`. A declared destination reading as confirmed is worth one word —
silence and "not checked" look identical otherwise.

`install_decisions` gains the question, shown only when the guarded store actually has a remote or
the device is `work`; otherwise it lengthens a walkthrough that exists to stay short. Its suggestion
is the corporate host plus the already-confirmed `own_accounts` entry — derived, but from a value
the user confirmed rather than from the commonest owner on the machine, which is the derivation
`own_accounts` itself refuses.

### 4. What the check cannot do, said in the skill rather than left implied

It matches a URL. Whether the destination repository is private, internal or public needs an API
call, and this script is stdlib with no network — so the check answers "is this the destination you
declared", never "is this repository private". Keeping the store repo private is the user's own
step, and the skill says so next to the key, so a green `doctor` is not read as more than it is.

### 5. Organisation versus your own namespace: it is ownership, and it already exists

The question asked 2026-09-12 was whether the separation between public repos in the corporation's
organisations and private repos in the user's own account on the corporate instance is modelled.
Three axes exist today and none of them is visibility:

| axis           | read from                    | decides                                                                 |
| -------------- | ---------------------------- | ----------------------------------------------------------------------- |
| ownership      | the repo's own remote        | route: your account keeps `plans/`, an org's repos go to the store      |
| tier           | `shareable_roots` + `device` | which store may have a remote — a contractor concept                    |
| `public_roots` | config                       | which directory _names_ may appear in a published repo (`scan`'s terms) |

[DECISION: **repo visibility is not modelled, and ownership is the right axis for what was being
asked.** Settled 2026-09-12. The org/own-account separation already drives the two things it should:
an organisation's repos go to the store because the organisation has its own tracker, and the user's
own namespace on the corporate host is where the store's own remote belongs — a store pushed into an
organisation's repository would show every plan on the machine to that organisation. Visibility
itself is unobservable offline, so it could only ever be a field nobody maintains, which is the bar
"a field is a contract every future plan pays for" already sets.]

## Files touched

- `skills/plan-docs/scripts/plans.py` — the tier constant and `tier_of`; `STORE_README`;
  `remote_problems`; `_print_stores` and the tier columns in `doctor`, `list`, `where` and
  `config show`; `install_decisions` and `explain_install`; the config schema, the skeleton's
  comments, and `config set` validation for the new key.
- `skills/plan-docs/SKILL.md` — the work-device rows in "First: which kind of machine is this?", the
  remote rule in "Is this machine set up, and what is in it", the new key in the `config set` list
  and the TOML example, and the sentence about what the check cannot see.
- `skills/plan-docs/references/design-rationale.md` — why a work device gets a third tier value
  rather than a hidden one, why the key is host-qualified where `own_accounts` is not, and why the
  shareable tier stays unchecked.
- `tests/unit/test_plan_store.py` — the existing work-device tests assert on the tier word and will
  need updating rather than adding to.

## Verification

- `test_a_work_device_has_one_store_and_still_refuses_a_personal_remote` and
  `test_a_work_device_routes_every_root_to_the_one_store` keep passing, with their tier assertions
  rewritten to the new output.
- New tests: no tier word anywhere in a work device's `doctor`; a sanctioned remote produces no
  problem row and prints `(sanctioned)`; an unsanctioned one still warns and names the key; a bare
  owner is refused by `config set`; a `/media/...` path prefix matches; a contractor device's
  shareable tier is unaffected by the key being set.
- `PLAN_DOCS_DEVICE=work python3 …/plans.py doctor` on this machine, which is how every symptom
  above was found, run again with a sanctioned entry set and expected to be quiet.

Done 2026-09-12. Twelve tests, including the two rewritten ones. On this machine's real data, the
work-device path now prints `store: … [remote: origin]` with no tier word anywhere, a tier column
that is gone rather than reading `sensitive` against the personal root, and `--json` reporting
`tier: null` for every root and for the store itself. With
`sanctioned_remotes = ["github.com/TheodoreAD"]` recorded in a **copy** of the config — the real one
was not touched — the same run reports `problems (0)` and prints `remote: origin (sanctioned)`,
which is the whole of what this plan asked for: the documented workflow is silent, and the check
still has something to say about anything else. The contractor path is byte-identical to before.

## Migrated to

- `skills/plan-docs/references/design-rationale.md`, "Why a work device names no tier, and what its
  remote check asks instead (2026-09-12)" — every `DECISION` above, the `PITFALL` about a check that
  fires on correct behaviour, the five symptoms that were measured, and the ownership-versus-
  visibility answer to the question this plan was reopened with.
- `skills/plan-docs/SKILL.md` — the device table and the no-tier paragraph under "First: which kind
  of machine is this?", the `sanctioned_remotes` rules with what the check cannot see, the
  `config set` list, the TOML example, and the guarded-store sentence in the `doctor` section.
- `skills/plan-docs/scripts/plans.py` with `tests/unit/test_plan_store.py` — the behaviour itself
  and the tests that hold it, including the two whose tier assertions this plan predicted would need
  rewriting.
- `plans/2026-08-29-sensitive-tier-durability.md` — the one live thread. Its recommendation asked
  for a check that learns which remotes are sanctioned; that now exists, so the note went to the
  plan that stays open rather than dying with this one.

Deliberately not migrated: the before-and-after terminal output. It was evidence for the change,
`PLAN_DOCS_DEVICE=work` reproduces it in one command, and it names this machine's roots — which is
exactly what a published repo must not carry.
