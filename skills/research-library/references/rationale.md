# Why a research library, and why these conventions

Design rationale for `SKILL.md`. What the library _is_ and how to use it live in the skill; this
page is the _why_, including the alternatives that were researched and rejected.

## Why it exists

Reference material — vendor repo clones, PDFs, mirrored docs — used to live inside a project's own
gitignored `reference/` directory. Two problems with that:

1. **Agent security exposure.** Gitignored is not unreadable. Anything operating with a repo as its
   working directory — a search agent, a recursive grep, "read the whole repo" — walks straight into
   third-party cloned code and docs and treats their content as trusted project context. That is the
   vector prompt-injection-via-cloned-repo attacks use. Moving the content fully outside any repo
   directory takes it out of the _default_ blast radius of repo-scoped operations; it enters an
   agent's context only when a task explicitly names the external path. Deliberate, not ambient.
2. **Not shareable.** Every repo wanting the same reference material re-cloned it into its own
   gitignored tree, duplicating disk and staleness.

## Flat, not namespaced per project

Namespacing entries under the project that pulled them in was the first idea and does not hold up:
the point of a shared library is that projects overlap in what they reference, and filing each clone
under whichever project happened to need it first just hides the duplication the library exists to
avoid.

## Naming: always `<host>--<owner>--<repo>`, no special case for the popular host

This caught a real mistake during the first migration: two of the four repos being moved in turned
out to be hosted on a self-hosted GitLab instance, not GitHub, despite looking like they might be. A
uniform rule forces checking the actual `origin` remote for every entry, every time; a "GitHub, no
prefix" special case would have hidden that assumption. The prefix is the full host, not a generic
label like `gitlab` — that keeps `gitlab.com` distinct from a self-hosted instance.

## Location: a plain directory, not an XDG data dir

Where a machine otherwise files tool installs under `~/.local/share/<tool>`, that convention is
about _tool_ installs cluttering `$HOME`. This is human-facing content opened directly — PDFs,
epubs, source you read — so it behaves more like `~/Documents` than a program's data directory.
Hence a plain `~/research` default, overridable via `$RESEARCH_HOME`.

## Provenance in each entry, not a central manifest

Every entry carries its own `SOURCE.md` rather than being listed in one index that drifts out of
sync with the directory.

It is not only for non-git items. A repo's default branch is not guaranteed to match what is
actually published as "the docs" — docs sites are often built from a `stable`/release-tag branch, or
from an entirely separate docs repo. `note:` is where that gets flagged.

[PITFALL: **A clone pinned to a tag re-fetches that tag forever and reports success.** Found doing
the first real migration, not anticipated: a `gnome-shell` clone had been created with an explicit
release tag, leaving `remote.origin.fetch = +refs/tags/46.0:refs/tags/46.0`. The naive refresh loop
(`git fetch --depth 1 origin`) happily re-fetched that same months-old tag on every run and reported
"up to date" — silently wrong, never an error. Fixed by reconfiguring the fetch refspec to the real
default branch, found via `git ls-remote --symref origin HEAD`. Check
`git config --get-all remote.origin.fetch` on any entry that looks suspiciously stale.]

## Discoverability needs two layers, not one

- **This skill** teaches the _mechanism_ — where the library is, the naming convention, how to add
  and update entries. It applies in every project automatically.
- **Each project's own `AGENTS.md` still needs a short, project-specific pointer** — "for GNOME
  Shell extension behaviour, check `$RESEARCH_HOME/repos/gitlab.gnome.org--GNOME--gnome-shell`
  before reading anything online" — because _which_ entries matter to a given project is knowledge
  this skill cannot have. It is also what makes the convention visible to agents that read
  `AGENTS.md` but have no skill-discovery mechanism of their own.

The instruction that actually delivers "stop refetching things you already have" lives in both: the
skill says _how_ to check the library, each project's `AGENTS.md` says _prefer the local copy over a
web fetch_ as a standing rule rather than a one-off suggestion.

## Docs sites, not just repos

Researched rather than guessed, since mirroring whole websites is a bigger commitment than cloning a
repo:

- **`llms.txt` / `llms-full.txt`** is a real, growing convention — a plain-markdown index or full
  concatenated dump of a docs site, published specifically so an agent can fetch clean text instead
  of crawling rendered HTML. Not a formal standard (no public commitment from major model vendors to
  read it automatically as of early 2026), but real adoption (Stripe, Clerk, Snowflake, others).
  Where a site has one, it is the best thing to cache.
- **Prefer the source repo over the built site when one is public.** Most docs sites
  (mkdocs/docusaurus/sphinx) are generated from markdown or rst in a public repo, often the
  project's own. Cloning that gets clean source instead of scraped HTML, and reuses the `repos/`
  bucket and update mechanism that already exist — no new tooling.
- **Fallback tier, only when neither exists:** purpose-built mirror-to-markdown tools —
  [`llms-mirror`](https://pypi.org/project/llms-mirror/0.1.0/) (pulls via a site's `llms.txt` index)
  and [`site2md`](https://github.com/CamiloMartinezM/site2md) (wget-based mirror plus HTML-to-
  Markdown cleanup). Both beat a hand-rolled `wget --mirror` and manual conversion.
- **Order: `llms.txt` → clone the source repo → general site-to-markdown mirror.** Full site
  mirroring is the last resort: most staleness risk, plus a new tool dependency.
- **Bucket:** `pages/<host>--<site>/`, no version segment by default — "latest" is normally the
  goal, so re-fetch in place rather than accumulating dated snapshots. The version actually fetched
  goes in that entry's `SOURCE.md`.
- Docs sites move faster than repos and have no pinned commit to anchor to, so a repo-oriented
  refresh loop is the wrong tool for `pages/` entries; they want their own, shorter cadence.

Sources:
[Write LLM-friendly docs (Fern)](https://buildwithfern.com/post/how-to-write-llm-friendly-documentation),
[llms.txt guide (Fern)](https://buildwithfern.com/post/optimizing-api-docs-ai-agents-llms-txt-guide),
[Snowflake docs for AI agents](https://docs.snowflake.com/en/release-notes/2026/other/2026-04-15-agent-friendly-docs),
[llms.txt: Making Your Project Discoverable to AI Agents](https://www.agentpatterns.ai/standards/llms-txt/).

## RAG / embeddings — researched, not adding

**The mechanics, briefly:** RAG means an external index, not the model's trained knowledge, supplies
facts at answer time — chunk the source text, embed each chunk, store the vectors, embed the query
at search time, splice the nearest chunks into the prompt. It is how you search a corpus too large
to hand the model wholesale, and it matches on meaning rather than exact wording — at the cost of a
whole pipeline (chunker, embedding model, vector store, re-embed-on-update) to build and keep in
sync.

**2026 consensus:** the industry has moved _away_ from vector-DB RAG for code specifically. Multiple
sources describe Claude Code itself moving off a vector-RAG pipeline toward agentic search (grep,
glob, file reads, symbol navigation), because code questions are usually literal ("where is `X`
defined") and exact-match search answers them better and cheaper. RAG still earns its place for
monorepos too large to grep from scratch each time, genuine concept search, and large non-code
corpora — usually hybrid, not embeddings alone.

**Applied here: it does not clear the bar.** Curated entries, an `AGENTS.md` naming the exact
relevant path, individually modest-sized repos and docs — that is already what makes agentic
grep-and-read sufficient, using tools an agent has natively with zero added infrastructure.

**Checked against actual expected use, not just in the abstract:** the realistic workloads are a
single book at a time (themes, characters, style) or a handful of papers on one topic — not hundreds
of documents with repeated queries, the scenario where RAG's cost and recall numbers actually apply.
At that scale the corpus fits in a single context window outright, so there is no retrieval step to
need; and for the whole-book case, chunked retrieval works _against_ the task, because themes and
style are properties of the whole text and top-k retrieval severs exactly the cross-chapter
connections that analysis depends on.

**Revisit trigger, not a default:** a genuinely large, term-agnostic corpus — a huge manual or
document dump where the right search term is not known and a full read-through is impractical — is
the specific condition that would justify a lightweight local option (a local embedding model plus
something like `sqlite-vec`, exposed via an MCP server). Added for that case, not preemptively.

Sources:
[RAG Is Not Always the Answer Anymore (DEV Community)](https://dev.to/nimay_04/rag-is-not-always-the-answer-anymore-how-ai-agents-search-code-in-2026-43m3),
[Why Claude Code Dropped Vector DB-Based RAG (SmartScope)](https://smartscope.blog/en/ai-development/practices/rag-debate-agentic-search-code-exploration/),
[Code Retrieval: Grep, RAG, or Both? (Medium)](https://medium.com/@jhanavibehl/code-retrieval-grep-rag-or-both-706cdefd0b70),
[grep vs. RAG (LlamaIndex)](https://www.llamaindex.ai/blog/is-grep-all-you-need-lexical-vs-sematic-search-for-agents).
