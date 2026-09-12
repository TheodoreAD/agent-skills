# Security policy

## Reporting a vulnerability

**Report privately, not in a public issue:**
[open a draft security advisory](https://github.com/TheodoreAD/agent-skills/security/advisories/new).
Private vulnerability reporting is enabled on this repository, so that form is available to anyone
with a GitHub account and the report stays between us until there is a fix.

What to expect, for a repository maintained by one person in their own time:

- **An acknowledgement within 7 days.** If you have heard nothing after that, assume the
  notification was missed rather than ignored, and say so on the same advisory.
- **An assessment within 30 days**, saying whether the report is accepted, and if so what the fix
  will be and roughly when.
- **Coordinated disclosure.** Nothing is published until a fix is available or we agree the report
  does not need one. Credit in the advisory unless you would rather not be named.

There is no bounty.

## What is in scope

Every skill here is `SKILL.md` instructions plus, in some cases, a stdlib Python script. The
interesting vulnerability classes for that shape are:

- **A script doing something its skill does not disclose.** Every skill that ships a script or
  instructs a write outside your repository carries a `## What this skill reads, runs and writes`
  section. A gap between that section and what the code does is a defect worth reporting even if
  nothing malicious follows from it.
- **Prompt injection through skill content** — instructions that would make a reading agent act
  against its user.
- **A path a script writes to that it should not**, including anything outside the directories its
  disclosure names.
- **Command injection** in the places a script shells out.

## What is not a vulnerability here

- **A skill telling an agent to run a command that then does something destructive on your
  machine.** These skills instruct; your agent and your permission settings decide what executes.
  Review a skill before installing it — the whole format is two files you can read.
- **Broad read access being broad.** `session-harvest` and `session-bash-audit` read agent
  transcripts, and `session-harvest` additionally inspects processes, listening sockets and git
  state across repositories. That is what those skills are for, it is disclosed in each one, and
  neither contains a network client of any kind — a claim you can check with one `grep`. A scanner
  flagging the shape is not a finding; a script _sending_ any of it somewhere would be.
- **A third-party scanner's verdict on its own.** Several public indexes rate these skills
  automatically and disagree with each other. If you think a rating reflects a real problem, report
  the problem rather than the rating.

## Supported versions

There is one supported version: the current default branch. Skills are installed by copying from it,
so a fix reaches you when you re-install. There are no release branches and nothing is backported.
