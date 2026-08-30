---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/agent-skills.git
---

# Does the SQLAlchemy material warrant a skill of its own?

## Context

Inherited from a personal project's now-retired SQLAlchemy adoption plan, which raised the question
and answered it "not yet" on 2026-08-29, with a condition attached: revisit once the port had landed
and the advice had been tested by something other than a probe. The port landed the same day, so the
condition is met and this is the revisit.

What exists today is four edits to `db-defaults` (`a459dcc`), made while the project had not yet
written a line of SQLAlchemy. `~/AGENTS.md` requires a convention to be piloted on a real working
repo before it reaches a shareable artifact, which is exactly why declining then was right.

The material that now exists, all of it measured against SQLAlchemy 2.0.52 rather than researched:

- Two SQLite defaults that are wrong and silent — `Numeric` round-tripping a `Decimal` through a
  float, and an aware datetime coming back naive — both invisible on Postgres, which is what makes
  them traps for a Postgres-first project with a SQLite test tier.
- `STRICT` accepts five type names, so `String`, `Date` and `BigInteger` all fail schema creation
  there; `Text` plus `type_annotation_map` is the fix.
- Alembic's SQLite batch mode drops triggers, and skips a `CheckConstraint` that is both reflected
  and unnamed. Naming every constraint is the cheap insurance.
- `DDL()` runs `statement % context` unconditionally, so a literal `%` in DDL raises before the
  database sees it.
- An `AsyncSession` shared between concurrent tasks **hangs** rather than raising.
- `lazy="raise"` turns a forgotten eager load from a `MissingGreenlet` traceback into an error that
  names the attribute.

## Open questions

[NEEDS CLARIFICATION: Whether this is a skill or more edits to `db-defaults`. The argument for a
skill is that the list above is procedural — "when you set up SQLAlchemy, do these six things" — and
`db-defaults` is a chooser, answering "which database for this shape of problem". The argument
against is that a skill nobody triggers is worse than a paragraph someone reads, and one project is
still a sample of one.]

[NEEDS CLARIFICATION: How much of it is SQLite-specific rather than SQLAlchemy-specific. Four of the
six items above are about the SQLite dialect being laxer or different, which matters to any project
using SQLite as a test tier for a Postgres deployment — a common shape, but not the only one, and a
skill scoped to it would need to say so in its own description.]

## Recommended direction

Wait for a second project. The `sqlite_strict` item is the argument for waiting rather than for
hurrying: it survived a probe and was still wrong in the first draft that quoted it. One repo's
experience is a good source for a skill's content and a bad source for its scope.
