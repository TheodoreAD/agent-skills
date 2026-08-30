---
status: landed
updated: 2026-08-30
---

# `python-conventions`: a fourth Pydantic trap, and the override it needs recording

## Context

Filed from a project that spent a session migrating ~30 frozen dataclasses to Pydantic `BaseModel`
under the skill's own "if a project uses Pydantic for anything, it uses Pydantic for everything"
alternative. Two of the three bullets already under **Pydantic traps a dataclass never had** came
from that project's design work and were correct in practice. A third trap of exactly the same shape
— measured against the same pydantic 2.13.5 — is missing, and it is the one that changed a public
API rather than a call site.

Both items below are small, additive edits to `skills/python-conventions/SKILL.md`. Neither is
urgent.

## The trap

**Pydantic converts any `ValueError` raised inside a validator into its own `ValidationError`.**
Anything that is not a `ValueError` propagates untouched.

That is unremarkable until a project has its own exception hierarchy whose base is `ValueError` —
which is a common and previously well-reasoned choice, made so that callers already handling bad
input generically keep working. After the migration, every one of that hierarchy's classes stops
reaching a caller: a construction that used to raise `MyValidationError` now raises
`pydantic.ValidationError`, and any subclass distinction the project maintained is recoverable only
by matching on the message text.

In the project that hit it, the classes at stake were a validation error and a unit-mismatch error,
where telling the two apart is the point of having them. The fix was to drop `ValueError` from the
base:

```python
class ProjectError(Exception): ...


class ValidationError(ProjectError): ...  # deliberately NOT a ValueError


class UnitMismatchError(ValidationError): ...
```

with the consequence written down, since `pydantic.ValidationError` _is_ a `ValueError`: catching
everything a construction can raise becomes `(ProjectError, ValueError)` — the project's own
complaints, plus the structural ones pydantic raises on its own (a missing field, a `float` where a
`Strict()` `Decimal` is meant).

The inverse choice is equally valid and worth naming, because it is the right one at a parsing
boundary: **raise plain `ValueError` deliberately** so pydantic _does_ capture it, attaches the
field's own location, and collects several complaints into one report. The same project did exactly
this in its file-format loader, and rendered the collected report back into its own error type at
the boundary. So the rule is not "never subclass `ValueError`" — it is that the choice now decides
whether an error carries a type or a location, and it has to be made per layer.

[NEEDS CLARIFICATION: Whether this is a fourth bullet under the existing "Pydantic traps" heading or
belongs one level up, since unlike the other three it changes a public API rather than a call site.
A fourth bullet is the smaller edit and keeps the section's "measured against 2.13.5" framing
intact.]

## The override that should be recorded

The same project took the all-or-nothing alternative and therefore contradicts the skill's default
split (Pydantic at boundaries, `@dataclass(frozen=True)` for internal records) throughout its
engine. The skill already licenses that as "a legitimate substitute, not a divergence" — so nothing
is wrong — but the project's own plan noted that the skill should record the exception rather than
be left looking like a rule that project silently ignores.

Worth one clause naming what makes the substitute the right call in practice, since the project
found a reason the skill does not currently give: the deciding factor was not consistency but that a
single `Annotated` alias replaced thirteen hand-maintained `object.__setattr__` normalisation sites
of the codebase's most load-bearing invariant. The skill's line 103 already gestures at this cost
for frozen dataclasses; it is stronger evidence for the alternative than the consistency argument
currently carrying it.

## Recommended direction

Two bullets, no restructuring. The measurements are done and quoted above; nothing here needs
re-verifying beyond confirming the pydantic version the section claims.

## Migrated to

- **`skills/python-conventions/SKILL.md`, "Pydantic traps a dataclass never had"** — a fourth
  bullet, with the inverse case (raise plain `ValueError` at a parsing boundary) as a sub-bullet,
  and the section's opening count and Model-default line updated to carry it.
- **`skills/python-conventions/SKILL.md`, the project-wide alternative** — one bullet naming what
  actually argues for it: one `Annotated` alias against thirteen hand-maintained
  `object.__setattr__` normalisation sites, which is stronger than the consistency argument that was
  carrying it alone.

[DECISION: a fourth bullet rather than a promotion one level up, which was the open question. It is
the smaller edit, it keeps the section's "measured against 2.13.5" framing intact, and the section's
opening line now says which of the four changes a public API rather than a call site — so the reader
gets the distinction without the trap leaving the company of its three siblings.]
