# polite-mcp-conventions-taudelta

How an agent should behave when it acts on your real, logged-in accounts.

**This skill is personal.** It was written for one author's own shopping and classifieds automation
repos, a family of `*-polite-mcp` servers that drive real, logged-in accounts on a handful of online
shops. Its description names those repos, so it will rarely fire anywhere else, and installing it
as-is gains you little. It is published as a worked example: three rules from real sessions that you
could copy into your own conventions if your agent acts on anything of yours that is live. Like
every `-taudelta` skill, it is one author's rulings rather than a neutral reference.

## The problem it answers

An agent working on automation against a live personal account is doing two kinds of thing that look
alike. Reading a page is harmless. Clicking "add to cart" on your real account is not, even when the
item is cheap and the action can be undone. And when the flow needs your input on many small items,
such as how many of each of eight products, the agent's easiest move is to print a list and ask you
to type every answer, which is the slowest possible way to give them.

## The three rules

- Confirm before the first live mutating action in a session. Before the first real change to your
  account, such as an add-to-cart rather than a read, the agent stops and asks, framed as a one-off
  scoped test of what will run and how it will be undone. Once you approve and the behaviour is
  confirmed, later actions of the same kind in that session don't ask again.
- Batch small decisions instead of asking for a typed list. Several independent choices go into
  guided questions of about four at a time, each with a suggested answer first. For a long list of
  similar items that each have a sensible default, a numbered table you edit by index is lighter
  still.
- Write research findings into the plan before implementing. After a live exploration of a site,
  what was learned goes into the repo's `PLAN.md` first, so the reasons for the design live in a
  file rather than in a conversation.

## What it looks like

An illustration of the table form, on the second page of a list:

```
11  oat milk 1L          x2
12  eggs, 10             x1
13  ground coffee 500g   x1
...
```

The usual reply is `ok`. The exceptions are indices, such as `-12`, `13x2` or `only 11,13`. Rows are
numbered continuously across pages, so an index never means two things, and the agent echoes its
reading of the reply in one line before anything reaches the real cart.

## Where the rules came from

Each rule carries the session it came from. On 2026-08-14 the agent asked before its first live
add-to-cart and got a quick "yes, test on one cheap item", which is why asking first is the default
rather than excess caution. The batching rule comes from the user's own words in a reorder session:
having to type everything out "kills the ux". And the index table was the user's idea, on
2026-09-26. Run the same day over eight pages of products, every reply was an index expression of
two to eleven characters, and none needed clarifying.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill polite-mcp-conventions-taudelta
```

It only fires when you work in one of the repos its description names. To use the rules elsewhere,
copy the ones you want into your own `AGENTS.md` or your own skill, in your own words and with your
own repo names.

## What it touches

Nothing. It ships no scripts and runs nothing; it only guides how your agent asks before acting.

## Read more

- [`SKILL.md`](SKILL.md): the rules as your agent reads them, with the conditions on the index
  table.
- [mcp-server-shipping](../mcp-server-shipping/) and
  [mcp-python-conventions-taudelta](../mcp-python-conventions-taudelta/): how the same servers are
  installed, and how their code is written.
