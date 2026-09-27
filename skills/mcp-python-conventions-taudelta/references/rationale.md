# Why these MCP server code conventions

Extracted from `python-conventions`' rationale on 2026-08-31, where these were sections 9 to 11.
Cross-references to the surrounding sections now point at that skill's own rationale, which is a
separate install.

## 9. MCP-stdio logging discipline

**Scope: stdio-transport MCP servers only** (the `*-polite-mcp` family) — not
`power-user-linux-setup` itself, which has no MCP server and no stdio-framing constraint.

**The spec is unambiguous, fetched directly, not inferred.** MCP specification, stdio transport page
(2026-07-28 revision) —
[modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
— quoted verbatim: "The server **MUST NOT** write anything to its `stdout` that is not a valid MCP
message. The server **MAY** write UTF-8 strings to `stderr` for any logging purposes." All of stdout
is reserved, not just framing bytes — a stray `print()`, a dependency's own
`logging.StreamHandler()` wired to stdout, or a traceback printed instead of raised all corrupt the
JSON-RPC stream.

**FastMCP (`fastmcp==3.4.7`, this family's pinned version) already defaults its own logging to
stderr — corroborated across independent secondary sources (a GitHub issue thread, unaffiliated blog
posts), but a first-party doc page/source fetch could not be completed during this research (the
FastMCP GitHub org transferred `jlowin/fastmcp` → `PrefectHQ/fastmcp` mid-pass, breaking several
URLs) — treat as reliable, not as a verbatim citation. The framework protects itself by construction
but doesn't document the _why_, and doesn't guard a server author's own code or dependencies.

**Ground truth against the sibling repos: no violation today, but no guard either.** Zero `print()`
calls inside any `*_polite_mcp/` package proper (the only hits are in standalone dev/ops scripts —
`recapture_fixtures.py`, `spike_cdp.py`, `login.py`, `recover_session.py` — never imported by
`server.py`, never run as part of the stdio process). Zero `logging`/`basicConfig`/`StreamHandler`
imports anywhere across all three repos — correctness today rests on "nobody happened to write
`print()` in `server.py` yet," not on any enforced convention.

**Decision: never call bare `print()` in package code** (the existing standalone-dev-script category
is fine as-is — those never run inside the stdio process). **Route all logging through the stdlib
`logging` module, explicitly configured to stderr at server startup**
(`logging.basicConfig(stream=sys.stderr, ...)`, or defer to FastMCP's own `configure_logging()`/
`get_logger()`, which already defaults there) rather than leaving it unconfigured and implicit.
State the caveat plainly wherever this lands: explicit stderr configuration protects code this
project owns, not a third-party dependency that writes to stdout on its own initiative — the only
fully robust check is exercising the real stdio transport end-to-end (MCP Inspector, or a real
client round-trip), not code review alone.

## 10. Error handling at the MCP tool boundary

**Scope: stdio-transport MCP servers only**, same as §9.

**FastMCP has a documented, structured mechanism, fetched directly from
[gofastmcp.com/servers/tools](https://gofastmcp.com/servers/tools).** `ToolError` (from
`fastmcp.exceptions`) is the sanctioned channel: its message reaches the client unmodified,
"regardless of the `mask_error_details` setting." **The load-bearing, easy-to-miss fact: FastMCP's
default already unmasks plain exceptions.** A tool that raises a standard
`ValueError`/`TypeError`/... without `ToolError` has its full exception detail included in the
client-facing response by default (`mask_error_details=False`) — not something a repo opts into by
skipping a setting, the out-of-the-box behavior. `mask_error_details=True` converts non-`ToolError`
exceptions to a generic message, but `ToolError` messages still pass through even with masking on —
it's the explicit "this text is safe to show" channel, masking is the "don't show anything else"
channel.

**This has the identical shape to the `SecretStr` caveat** in `python-conventions`' settings
section, **not a new kind of problem.** `mask_error_details=True` protects against FastMCP's own
automatic traceback inclusion, but does nothing to sanitize text a developer deliberately embeds in
a `ToolError` message or hands to `str(exc)` — if that string itself contains something sensitive,
masking never touches it, exactly as `SecretStr` never touches a value already pulled via
`.get_secret_value()`. Also orthogonal to `python-conventions`' exception-hierarchy decision:
internal hierarchies govern what the _code_ catches and discriminates on; `ToolError` governs what
crosses the MCP wire — a separate concern the existing hierarchy decision doesn't cover.

**Ground truth: zero `ToolError` imports or uses anywhere in the family.** All three repos call
plain `FastMCP("name")` with no `mask_error_details` argument, so FastMCP's unmasked default applies
everywhere. Two patterns exist in practice: direct `raise ValueError(...)` for bad tool arguments
(uncaught, propagates through FastMCP's default unmasked path — consistent with upstream default,
nothing hidden or leaked beyond what FastMCP already does), and per-item `except Exception` inside
batch tools (deliberately broad, `# noqa: BLE001`) that writes `error=str(exc)` into a structured
result field rather than re-raising — isolates one bad item from failing an entire batch (a good,
deliberate pattern for that problem), but means whatever text `str(exc)` produces for _any_
exception type flows to the client with zero review. Today likely benign (the caught exceptions are
mostly this project's own deliberately-worded `ValueError`/`NotFoundError` types), but an unreviewed
assumption — a future dependency exception (a raw Playwright/requests error embedding a URL, header,
or path) would flow through identically, unexamined.

**Decision: adopt `ToolError` at the MCP tool boundary specifically** — the point an internal
exception is about to cross back to the client is the one place that decides what's safe to expose,
by either re-raising as `ToolError` with an explicit, hand-written message, or leaving a plain
exception to raise (accepting FastMCP's default unmasked behavior). Never assume `str(exc)` of an
arbitrarily caught exception is safe by default just because it happens to be dev-controlled today.
Do **not** flip `mask_error_details=True` project-wide as the fix — it would suppress legitimately
useful debugging detail the plain-`ValueError` argument-validation call sites still rely on being
visible to the calling agent; the finer-grained per-message `ToolError` choice mirrors the settings
section's own preference for explicit control over a broad, blanket toggle.

## 11. MCP tool docstrings — the LLM-facing contract

**Scope: any function decorated as an MCP tool** (`@mcp.tool()` in this family's FastMCP-based
servers) — a genuinely distinct concern from general docstring style, not an extension of one (no
general docstring-content rule exists in the Python conventions to extend; its type-hygiene section
covers only type-hint hygiene). The reader and the failure mode are both different: a human-facing
docstring costs reading time when weak; an MCP tool description is read by an LLM at inference time
to decide whether to invoke the tool at all and with what arguments — a weak one causes
wrong-tool-picked, wrong-arguments, or never-invoked failures, a correctness cost paid by every
future call, not a comprehension-speed one. Mechanically, in this exact stack: FastMCP's docstring
parser turns the _entire_ docstring into the wire-level `Tool.description` — there is no split
between "the IDE-tooltip part" and "the MCP-wire part." A PEP-257-conformant one-line summary would
be a _worse_ MCP tool description by the bar below even though it would pass ordinary
docstring-style review cleanly.

**MCP spec, fetched directly**:
[modelcontextprotocol.io/specification/2025-11-25/server/tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
— "Tools in MCP are designed to be **model-controlled**, meaning that the language model can
discover and invoke tools automatically." The spec itself is thin on content guidance (`description`
is defined only as "Human-readable description of functionality" — no prescribed length/structure).

**Anthropic's platform docs are the most directly actionable source found**,
["Define tools"](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), "Best
practices for tool definitions," fetched directly: **"Provide extremely detailed descriptions. This
is by far the most important factor in tool performance."** Content checklist: what the tool does,
when it should/shouldn't be used, what each parameter means and how it affects behavior, caveats/
limitations, what information the tool does _not_ return. **"Aim for at least 3–4 sentences for each
tool description, more if the tool is complex."** Also: consolidate related operations into fewer
tools rather than one-tool-per-action ("fewer, more capable tools reduce selection ambiguity");
meaningful namespacing once a library spans multiple services; design responses to return only
high-signal information ("Bloated responses waste context"). A worked good-vs-poor example pair
(`get_stock_price`) is given directly: the good version states what's returned, when to use it, and
what it explicitly does _not_ cover in ~3 sentences; the poor version is a six-word fragment with no
parameter description at all.

**Anthropic's engineering blog,
["Writing effective tools for agents"](https://www.anthropic.com/engineering/writing-tools-for-agents),
is the deeper "why."** Core heuristic, quoted in full: **"When writing tool descriptions and specs,
think of how you would describe your tool to a new hire on your team. Consider the context that you
might implicitly bring — specialized query formats, definitions of niche terminology, relationships
between underlying resources — and make it explicit."** Parameter-naming guidance: "input parameters
should be unambiguously named: instead of a parameter named `user`, try a parameter named `user_id`"
— this family's tools already do this consistently (`listing_url`, `seller_url`, `category_slug`,
never a bare `id`/`url`). "Every word in your tool's name, description, and parameter documentation
shapes how agents understand and use it" — the function name is part of the same selection surface
as the prose. The article's evidence this matters at all: Claude Sonnet 3.5's SWE-bench Verified
result followed specifically from "precise refinements to tool descriptions, dramatically reducing
error rates."

**OpenAI's guidance is directionally consistent but pulls toward brevity for a different reason —
token cost, not clarity** (aggregated via search, not independently deep-fetched — the weaker
citation here): "a tool list with 10 verbose function descriptions can add hundreds of tokens to
every API call... keep descriptions specific but concise." A real tension with Anthropic's "3–4
sentences minimum" bar, not a contradiction — different cost model. OpenAI's guidance targets a
large multi-tool library resent every call; this family's actual shape (5–8 tools per server, MCP's
session-scoped tool listing, not resent per-message) pays that token cost once per session, not per
message — **Anthropic's "detailed over concise" bar is the better fit here**, a judgment call, not a
claim that OpenAI's advice is wrong in its own context.

**Ground truth: this family's own code is already unusually strong practice, well beyond the
Anthropic floor — worth naming specifically what it does right.** Read directly from
`olx-polite-mcp/olx_polite_mcp/server.py` and `freshful-polite-mcp/freshful_polite_mcp/server.py`
(both `fastmcp==3.4.7`, no `description=` override anywhere — every tool relies on docstring
parsing): `get_listing_details_batch`'s docstring **disambiguates from the sibling
`get_listing_details` tool by name, inline**, states argument provenance ("pass `listing_url` from a
`search_listings` result"), and explains its batch cap as a deliberate anti-misuse guard, not just a
number ("specifically to keep that from being a one-call blanket-enrichment shortcut"), preempting a
plausible LLM misuse pattern rather than only documenting the ceiling. `list_favorites` explicitly
contrasts itself against `list_usuals` and `search_products`. `get_shopping_patterns`'s docstring
states a measured response-size number (~69KB for 200 products, against a ~64KB cap) as the reason a
smaller default shape exists — response-shape documentation, not just tool-purpose documentation.

**Two concrete, checkable gaps found — mechanism, not content quality.** (1) None of the ~11 tools
grepped use `Annotated[x, Field(description=...)]` or a docstring `Args:` section — every parameter
description lives only in free-form prose, so the JSON-Schema
`inputSchema.properties.<param>.description` field itself is empty for every parameter in both files
(checkable via `tools/list`). Functionally this mostly still reaches the LLM (most clients send the
whole description), but it's unexercised as FastMCP's parameter-description mechanism is designed to
work. (2) `add_to_cart`/`remove_from_cart` in `freshful-polite-mcp` — real-money-adjacent, clearly
destructive/write operations — have no `annotations=` set (`readOnlyHint`/`destructiveHint`/etc., a
structurally separate field from `description`, per the MCP spec). FastMCP's own docs state clients
"use annotation hints to determine when to skip confirmation prompts" — a client capable of
consulting `destructiveHint` gets no signal from this server at all today, relying entirely on
docstring prose to convey what the field exists specifically to make machine-readable. (Per the
spec, annotations must also be treated as untrusted unless from a trusted server — a security
framing distinct from the writing-quality question here.)

**Decision:** for any `@mcp.tool()`-decorated function, the docstring is the tool's contract with an
LLM caller, not internal documentation — write to Anthropic's bar (what it does and how it differs
from its nearest sibling by name, when to use/not use it, where each non-obvious parameter's value
comes from, response shape/size caveats, at least 3–4 sentences, more for a complex tool), not PEP
257's. Concrete shape, extracted from this family's own strongest examples rather than invented
fresh:

```python
@mcp.tool()
def get_listing_details_batch(listing_urls: list[str], report_path: str | None = None) -> DetailBatchReport:
    """<What it does, one sentence, and how it differs from the nearest sibling tool by name.>

    <When to use it vs. not — e.g. the shortlist-vs-full-search distinction, the batch-cap rationale.>

    <Where each non-obvious parameter's value comes from — "pass X from Y's result" — and what
    the response contains/omits, including size caveats if the tool can return a lot of data.>
    """
```

Two secondary follow-ups, worth a line each even though they're not the docstring itself: attach
per-parameter descriptions via `Annotated[x, Field(description=...)]` so the JSON-Schema itself
carries them, not just the aggregate description text; and set `annotations=` on any tool with real
side effects, since clients use it specifically to decide when to skip or require confirmation
prompts.

**Honesty flags carried forward**: the OpenAI-conciseness citation and FastMCP's claim that
"docstrings should describe response shape" both came from search summaries, not independently
re-fetched primary text — directionally trusted, not verbatim-cited. "FastMCP docstrings are
LLM-facing" is a correct-but-inferred combination of two separately-verified facts (FastMCP
populates `Tool.description` from the docstring; the spec defines `Tool.description` as what the
model-controlled invocation flow reads), not one direct FastMCP statement.
