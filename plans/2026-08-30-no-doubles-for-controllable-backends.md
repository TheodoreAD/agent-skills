---
status: landed
updated: 2026-08-30
repo: git@github.com:TheodoreAD/agent-skills.git
---

# The rule about doubles is missing from the testing conventions

## Context

Asked directly on 2026-08-30, while planning test work in a personal project: _do the skills say
anywhere not to mock a database, or anything else with a fully controllable backing service?_

They do not. Checked the same day across both candidate skills:

- **`python-conventions`, Testing conventions** covers fixtures-first, fixture scope, DAMP vs DRY,
  and the `monkeypatch` module-attribute trap. It says nothing about when a double is legitimate.
  The closest thing is in its rationale file, quoting the architecture lineage's line that
  monkeypatch-style mocking "couples tests tightly to implementation details" — which is an argument
  for a composition root, not a rule about backing services.
- **`db-defaults`** selects every default partly _for_ "pytest-local testability with no
  docker/cloud". That is the rule's premise, chosen deliberately, and then never cashed in: nothing
  says the point of picking a locally-runnable database is that tests run it for real.

So an agent has the premise and not the conclusion, and reaches for an in-memory fake the moment a
test would otherwise open a file.

## Open questions

[NEEDS CLARIFICATION: Which skill owns it. `python-conventions`' testing section is where an agent
writing a test looks, which argues for putting the rule there and cross-referencing from
`db-defaults`. The counter-argument is that the rule is really about the _choice_ of dependency —
you get to run the real thing because the default was picked to be runnable — which is
`db-defaults`' subject.]

[NEEDS CLARIFICATION: How the boundary is worded so it does not read as "never use a double". The
test that seems to work: **can this suite own the service's whole lifetime, in-process or as a
subprocess it starts and stops?** SQLite, a temp directory, a local queue and your own code under a
subprocess are all yes. A third-party HTTP API is no, and a hand-written stand-in for it is correct
rather than a compromise.]

## Recommended direction

State the rule where an agent writing a test will hit it, with the boundary above as the deciding
question rather than a list of technologies, and with two things it implies that are worth saying
out loud because they are what the rule costs:

- **The real thing must be sandboxed, not merely real.** The existing `tmp_path` guidance already
  carries the sharp version of this — a test that reaches `Path.home()` writes into the real one —
  and running real services makes that failure more likely, not less.
- **Where a framework singleton makes an in-process arrangement dishonest, the answer is a
  subprocess fixture, not a mock.** Starting the real entrypoint against its own temporary state
  reproduces the deployment shape instead of pretending the coupling is absent. It needs a bounded
  readiness wait that fails with the child's output, since a condition that can never become true
  produces a hang rather than a failure.

Worth checking whether the same gap exists in the `polite-mcp-conventions` testing guidance before
writing, so the rule lands once rather than in two half-versions.

## Migrated to

- **`skills/python-conventions/SKILL.md`, "Don't double anything the suite can run for real"** — a
  subsection of the testing conventions, where an agent writing a test is already reading.
- **`skills/db-defaults/SKILL.md`, the selection criteria** — one paragraph cashing the testability
  premise in and pointing at the rule, rather than a second copy of it.

[DECISION: `python-conventions` owns the rule and `db-defaults` points at it. The ownership question
splits cleanly once the two halves are separated: the _choice_ of a runnable dependency is
`db-defaults`' subject, and it already states that criterion — what was missing was the conclusion,
and the conclusion is read at the moment someone writes a test. Checked 2026-08-30:
`polite-mcp-conventions` says nothing about doubles either way, so there is no half-version to
reconcile and no third copy to keep in step.]

[DECISION: the boundary is the lifetime question — can this suite own the service's whole lifetime,
in-process or as a subprocess it starts and stops — rather than a list of technologies. A list goes
stale, invites arguing about membership, and answers nothing about a case not on it.]
