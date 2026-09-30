# mcp-python-conventions-taudelta

Rulings for the Python inside a stdio MCP server, where stdout is the protocol.

An MCP server looks like any other Python program, so an agent writes it like one. It debugs with
`print()`, lets exceptions carry whatever message they happen to have, and gives each tool a
one-line docstring in PEP 257 style. In ordinary Python those are fine habits. Inside a server that
talks JSON-RPC over stdio, each one is a bug: the first corrupts the protocol stream, the second can
hand internal detail to the calling model, and the third is the only text the model reads when it
decides whether to call your tool at all.

This skill tells the agent what is different _because_ the code is an MCP server, and nothing else.
It is one author's rulings rather than a neutral reference: where there is a choice, it picks one
answer and says why, so the agent doesn't re-decide it every session. The `-taudelta` suffix marks
it as that kind of skill.

It works with any agent that reads [Agent Skills](https://agentskills.io): Claude Code, Codex,
Cursor, Copilot, Gemini CLI and others. The rulings assume FastMCP and the stdio transport.

## What you get

- Logging that cannot break the protocol. No bare `print()` in server code, and the standard
  `logging` module pointed at stderr at startup. The MCP spec says a server must not write anything
  to stdout that is not a valid MCP message, so a single stray line corrupts the stream.
- A warning that your own code is not the whole risk. A dependency that logs to stdout by itself is
  not fixed by configuring your logging, so the check that counts is a real round trip over stdio,
  not code review.
- A deliberate choice at the tool boundary about what an error may say. FastMCP's default already
  sends a plain exception's full detail to the client, so the skill has the agent either raise
  `ToolError` with a message written for the model or let a plain exception through knowingly.
- A reason not to reach for the blanket fix. Turning on `mask_error_details` for the whole server
  also hides the useful validation messages, like a bad argument or a batch that is too big, that
  the calling model needs to see.
- Tool docstrings written as the model's instructions. That means what the tool does and how it
  differs from its nearest sibling, when to use it, where each parameter's value comes from, and
  what the response holds, in at least three or four sentences. This follows Anthropic's own
  guidance for tool definitions, which calls detailed descriptions "by far the most important factor
  in tool performance".
- The next step once prose is not enough: per-parameter descriptions through
  `Annotated[x, Field(description=...)]`, and `annotations=` such as `destructiveHint` on any tool
  with real side effects, since clients use those hints to decide when to ask before calling.

## What it looks like

A tool the way an agent writes it unaided:

```python
@mcp.tool()
def get_listing_price(listing_url: str) -> float:
    """Get the price of a listing."""
    print(f"looking up {listing_url}")
    return _lookup_listing_price(listing_url)
```

The same tool following the skill, abridged from its runnable snippet:

```python
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def get_listing_price(
    listing_url: Annotated[str, Field(description="A listing URL from a prior search_listings result.")],
) -> float:
    """Fetch the current asking price for one listing. Distinct from
    search_listings, which returns prices for many listings at once — use
    this only when you already have a specific listing_url and need a fresh,
    single-item price check.

    Pass listing_url exactly as returned by search_listings; a URL you
    construct yourself is not guaranteed to resolve. Returns a single float
    (site currency, no symbol) or raises if the listing no longer exists.
    """
    try:
        return _lookup_listing_price(listing_url)
    except ListingNotFoundError as e:
        raise ToolError(f"Listing not found: {listing_url}") from e
```

The first version breaks the stdio stream on its first call. The second tells the model when to pick
it over its sibling, and decides in writing what the error says.

## Why not just use the general Python conventions

These rules were split out of the author's general Python conventions skill on 2026-08-31, because
they are not style. Two of the three are protocol correctness, and none is something a model has a
general-Python reason to know. A model's instinct for a docstring is a short summary, which is
exactly the wrong shape here, so a stricter version of ordinary docstring advice would still point
the wrong way.

## What checking real servers found

The rulings were checked against the author's own FastMCP servers. No server package contained a
`print()`, but none configured logging either, so correctness rested on nobody having written one
yet. No server used `ToolError` anywhere, and batch tools copied `str(exc)` from any caught
exception straight into their results. Tool docstrings were already strong, yet none of about eleven
tools set per-parameter descriptions in the schema, and the tools that add to and remove from a real
shopping cart carried no `destructiveHint`.

## Install

```shell
npx skills add TheodoreAD/agent-skills --global --skill mcp-python-conventions-taudelta
```

It is picked up when your agent is writing or reviewing the code of an MCP server. For packaging,
installing and registering the server, see [mcp-server-shipping](../mcp-server-shipping/); for
general Python design questions, [python-conventions-taudelta](../python-conventions-taudelta/).

## What it touches

Nothing. It ships no scripts and runs nothing; it only guides what your agent writes.

## Read more

- [`SKILL.md`](SKILL.md): the rulings your agent follows.
- [`references/rationale.md`](references/rationale.md): the spec text, the FastMCP behaviour, the
  tool-description guidance each ruling rests on, and what the audit of real servers found.
- [`references/snippets/mcp-tool-boundary.py`](references/snippets/mcp-tool-boundary.py): the
  runnable example above, with its tests.
