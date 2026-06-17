# Nexus Brain — Research Dossier (Appendix)

> Referenceable appendix to [`PRD.md`](./PRD.md). Condenses the research findings, the competitor table, and the key 2026 tooling decisions. **Honesty markers:** **[VERIFIED]** = confirmed by live probe or cited source; **[UNVERIFIED]** / **[ASSUMPTION]** = not confirmed, do not build as if true.
> Date: 2026-06-03.

---

## 1. The opinionated 2026 stack (decisions at a glance)

**TL;DR stack:** LanceDB (single store, `project` filter, hybrid + `merge_insert`) → voyage-code-3 *(or bge-m3 local)* → tree-sitter/`CodeHierarchyNodeParser` + heading-split + Contextual Retrieval → hybrid + Voyage rerank-2.5 → **hydrate whole files into the frontier model** → LlamaIndex parsing, DIY orchestration.

| Decision | Pick | Runner-up | Why (key facts) |
|---|---|---|---|
| Vector store | **LanceDB** | sqlite-vec | Embedded/in-process, columnar single store, Rust-fast, larger-than-memory via disk indexing, **dense + native FTS (BM25) + hybrid in one table** with `RRFReranker`, SQL metadata filters, first-class `delete`/`merge_insert` (upsert). **Caveat:** dropped Tantivy for native FTS — new rows need `table.optimize()` to fold into FTS/ANN or they fall back to flat scan. Projects partition by a `project` column + filter, not separate files. |
| Vector store (alt) | **sqlite-vec** | — | One literal `.db` file + SQL-native joins; pair with FTS5 (BM25) → DIY hybrid via RRF. Lighter, ubiquitous; ANN brute-force-ish but fine < ~1M chunks. |
| (Skip) | hosted (Pinecone/Qdrant Cloud/Turbopuffer/pgvector-Supabase/Milvus/Weaviate) | — | Network latency (Turbopuffer cold p50 >200 ms), $64+/mo floor, ships code off-box. pgvector only if already in Postgres. |
| Embedding (cloud) | **voyage-code-3** | text-embedding-3-large | Code-tuned: **~13.8% avg better over 32 code datasets**; markdown-friendly; **Matryoshka dims (256/512/1024/2048) + int8/binary quant** → cut storage hard with minimal loss. Quality pick if a paid API + sending code to Voyage is acceptable. |
| Embedding (local) | **bge-m3** (Ollama) | nomic-embed-text-v1.5/v2; mxbai-embed-large; qwen3-embedding-8B | Multilingual, **8K context** (holds context better than nomic/mxbai which degrade past ~1K tokens), natively emits **dense + sparse + ColBERT** (hybrid in one model). nomic = lightweight default (~300 MB); mxbai edges it on <512-tok English; qwen3-8B for top local quality (MTEB ~70.6). **Never mix models across the store — re-embed all on any change.** |
| Chunking (docs) | heading-split (H1→H2→H3) + keep heading path; **late chunking** for long docs | — | Late chunking (Jina v3: mean-pool full doc then slice) preserves global context with no per-chunk LLM call. |
| Chunking (code) | **AST/tree-sitter** via `CodeHierarchyNodeParser` (LlamaIndex) + **Contextual Retrieval** | — | cAST (CMU 2025): structural chunks beat fixed-line by **+4.3 Recall@5 (RepoEval), +2.67 Pass@1 (SWE-bench)**. `CodeHierarchyNodeParser` splits by scope + injects parent/child refs. Contextual Retrieval (Anthropic): prepend a 1–2 sentence context blurb before embedding & BM25 — large failed-retrieval reductions. Late chunking for docs; Contextual for disconnected code chunks. |
| Retrieval | **hybrid (dense + BM25) → rerank → whole-file expansion** | — | BM25 non-negotiable for code (exact identifiers, error strings, API names embeddings blur). Rerank top ~30–50 → ~10 (Voyage rerank-2.5 balanced; bge-reranker-v2-m3 local). **Retrieve-then-read whole files** is the single biggest code-QA lever with a 200K–1M window. Query rewriting / HyDE optional. |
| Framework | **LlamaIndex** core (parsing + nodes + retriever assembly), **DIY** orchestration | Haystack; txtai | Best ingestion/parsing; `CodeHierarchyNodeParser`; native LanceDB+Voyage+reranker integrations; faster retrieval than LangChain. Skip LangChain/LangGraph agent machinery for a personal KB. |

---

## 2. CodeGraph local probe — concrete verdict

> The load-bearing risk. All claims below are from a live probe of `@colbymchenry/codegraph@0.9.7` (Node CLI, registered as an MCP stdio server `codegraph serve --mcp` in both `~/.codex/config.toml` and `~/.claude.json`).

### What was VERIFIED
- **[VERIFIED] Headless watcher/daemon — YES, but socket-scoped.** The `serve` watcher is fronted by a per-repo Unix-socket daemon (`.codegraph/daemon.sock`). Multiple agents share it; it **idle-times-out at 300 s** with zero clients. On reconnect it does a catch-up sync of files changed while down (self-heals across daemon death). No `watch`/`daemon` subcommand — the watcher only exists inside `serve` (`--no-watch` to disable). Not a boot-persistent system service.
- **[VERIFIED] Multi-workspace — NO multiplexing; strictly one-index-per-repo.** Each repo: its own `.codegraph/`, `codegraph.db`, `daemon.sock`, daemon pid. `serve` takes ONE project (`-p` or client `rootUri`). Federation = **N daemons + N databases**, no built-in cross-repo symbol resolution.
- **[VERIFIED] Index = per-repo SQLite (node-sqlite, WAL), stable schema (`schema_versions` v4):**
  - **`nodes`**(id, kind, name, qualified_name, **file_path**, language, start/end line+col, docstring, signature, visibility, is_exported/async/static/abstract, decorators+type_parameters JSON, updated_at).
  - **`edges`**(source→target, **kind**, metadata JSON, line, col, provenance) FK CASCADE. Observed kinds: `contains` 115, `calls` 65, `imports` 26, `instantiates` 10.
  - **`files`**(path PK, **content_hash**, language, size, modified_at, indexed_at, node_count, errors).
  - **`unresolved_refs`** (name + candidates JSON — the seam where cross-file/cross-repo links would live), **`nodes_fts`** (FTS5 over name/qualified_name/docstring/signature, kept live by AFTER INSERT/UPDATE/DELETE triggers), `project_metadata` (empty in sample).
  - All paths **repo-relative** (`app/agent.py`) → DBs relocatable but not cross-repo-addressable. `.codegraph/.gitignore` excludes `*.db`, `cache/`, `*.log`, `.dirty` — per-machine, never committed.
- **[VERIFIED] Liveness/lag.** File-watcher incremental sync; observed **39–53 ms/file**; server's MCP instructions state "index lags writes by ~1 s." Staleness bounded by content_hash diffing; catch-up re-syncs changed files on startup.
- **[VERIFIED] Sample `status --json`:** `fileCount:16, nodeCount:131, edgeCount:216`, `backend:node-sqlite`, `languages:["python"]`, plus `pendingChanges{added,modified,removed}` delta and a `worktreeMismatch` field.

### What CANNOT be determined (UNVERIFIED — do not build as if true)
- **[UNVERIFIED] Cross-repo resolution inside `serve`** beyond per-repo `rootUri` — no flag seen, no multi-root config.
- **[UNVERIFIED] Whether `project_metadata` stores a root path** — empty in sample.
- **[UNVERIFIED] Live daemon behavior under concurrent multi-client load** — all daemons were idle-exited at probe time.

### Verdict
Always-live structural queries **per repo** are free (watcher + sub-second SQLite + FTS triggers + self-healing catch-up). Multi-project is NOT native. To get always-live multi-project, **federate at the orchestration layer:** (1) **keep daemons warm** per active workspace (or accept cheap cold re-attach); (2) **fan out, not multiplex** — one `serve --mcp` or one-shot `codegraph query/context/callers/callees/impact` per workspace (CLI subcommands run headless against any `.codegraph` without an MCP session — ideal for a script-driven crew); (3) **federate via the stable seam** — read N `codegraph.db` read-only (WAL ATTACH), union results, resolve cross-repo via `unresolved_refs.reference_name` + `qualified_name`; gate on `schema_versions`.

---

## 3. Cross-tool federation patterns (the prior art to steal from)

- **SCIP (Sourcegraph):** protobuf, symbol-string-keyed index (~8× smaller, 3× faster than LSIF), emitted by per-language indexers. **Lesson:** define a stable, language-agnostic **symbol-ID + edge schema** and let many producers write to it (CodeGraph's `qualified_name` + `edges.kind` is exactly this seam).
- **Cross-repo nav = global monikers, not shared graphs (scip-typescript):** follows symbols across repos/dependencies by resolving to where defs live. **Lesson:** make `qualified_name` globally unique (namespace by repo) and resolve `unresolved_refs` across DBs.
- **Stack Graphs (GitHub):** incremental, build-free, per-file, language-agnostic name binding, indexed per commit. **Validates** CodeGraph's tree-sitter + content-hash + per-file sync; federate by composing per-file shards, not re-indexing the world.
- **Meta Glean:** code facts in RocksDB, queried in Angle (Datalog), first-class **incremental indexing** + **derived predicates**. **Lesson:** model federation as stackable per-repo fact DBs with derived cross-repo views (what ATTACH-and-union achieves).
- **Cursor:** Merkle tree over file hashes → walk only diverging branches every ~10 min; cache embeddings by chunk content. **Lesson:** hash-diff to find dirty units, recompute only those (`files.content_hash` is the primitive).
- **Aider:** def/ref symbol graph, PageRank with personalization toward the active task, binary-search ranked tags into a token budget. **Lesson:** rank `nodes` by `edges` centrality to pick per-task context (folded into our retrieval; bus-factor is the one user-facing use).
- **Cody:** dropped embeddings for native BM25 + signals, scales to 300k+ repos, ~10 repos/query with a merged global ranking. **Lesson:** for many-repo federation, lexical/structural (FTS5 + edges) scale and stay live more cheaply than embedding stores; merge per-repo result sets into one global ranking.

**Net steer:** CodeGraph nails *live + structural + cheap* per repo. For an always-live multi-project crew, **fan out per workspace, keep daemons warm (or lean on fast catch-up), and federate read-side** by unioning the N stable `codegraph.db` schemas and resolving `unresolved_refs` across them — taking incremental-shard, hash-diff, global-symbol-ID, and merged-ranking cues from Glean/Stack-Graphs/Cursor/SCIP/Cody.

---

## 4. Sync, freshness & federation design

**Recommended architecture (short version):** each project's index is a **rebuildable derived cache keyed by content hashes**, owned by a **per-project worker** a host service-manager **lazy-starts on demand and idles out**, with a thin **federation router** reading each project's **SQLite read-only over WAL** behind one query surface. Never share one giant index; never keep N watchers hot. Invariant: *source files + an embedding-model-version stamp deterministically reproduce the index.*

- **(a) Incremental indexing.** Merkle/file-hash manifest per project (Cursor model); two granularities — file-hash → which files changed, chunk-hash → which chunks re-embed. Deletes **tombstone** (soft-delete + periodic vacuum). LangChain "incremental" mode = upsert new + delete prior rows for a changed source.
- **(b) Triggers.** **Watchman** (recursive roots, **settles before notifying**, incremental **"since `<clock-id>`"** queries — first query returns everything) as the low-latency path; **fswatch** portable fallback. **Debounce** the event stream (coalesce bursts). **git hooks** (`post-commit`/`post-merge`/`post-checkout`) as the **correctness backstop** for branch switches/merges a debounced watcher can miss or storm on. *Watcher = freshness; hooks = guaranteed convergence.*
- **(c) Daemon/service management.** Don't run N hot watchers — **on-demand activation + idle eviction (LRU of hot indexes).** **macOS launchd** (user agent in `~/Library/LaunchAgents`): a router agent with `RunAtLoad`/`KeepAlive`; per-project workers started on demand via **`Sockets`** (socket activation), self-terminating after idle — **[VERIFIED]** launchd's `TimeOut` is only *suggested*, so the **worker must exit itself**; **`ThrottleInterval` defaults to 10 s** (crash-loop backoff: a job dying in <10 s waits `10−runtime`). **Linux systemd `--user`:** per-project `.service` + `.socket` unit; `Restart=on-failure`, `RestartSec=5s`, `StartLimitIntervalSec`/`StartLimitBurst`, `MemoryMax=`/`CPUQuota=`. *Only the router is always-on.*
- **(d) Federation.** Schema-stable SQLite per project; a **router/registry** maps `project_id → db_path + schema_version + model_version`. **Read live SQLite read-only over WAL (default):** **[VERIFIED]** WAL allows many readers without blocking the writer; constraints — **same host only** (needs shared memory; no network FS), read-only opener needs `-shm`/`-wal` readable or dir write-perm or the **`immutable`** query param. Zero-IPC, sub-ms (the codegraph model). **Proxy per-project servers (MCP-style)** only for stores that can't be opened in-process. **Structural queries for any registered project without being "in" the repo** — the call-graph lives as rows/edges, so the router runs `callers/callees/trace/impact` against the registered DB directly. A `schema_version` column lets the router refuse/upgrade mismatches.
- **(e) Consistency.** Stamp every store with `{embedding_model, dimension, schema_version, index_built_at, source_root_hash}`. On worker start, compare to config: **[VERIFIED]** dimension mismatch → **hard rebuild** (mixing dims throws/`inf`); same-dim different model → **silent quality rot** (cosine ~0.85→~0.65) → re-embed. **Never update in place** — re-embed to a new versioned index then flip the query path (reverse order reproduces the failure); keep the old for rollback. **[ASSUMPTION]** Drift-Adapter (learned old→new linear map) can defer full re-embeds, falling back to dual-index/blue-green when mapped accuracy drops. **Partial-failure recovery is free** — reindex writes a temp generation + atomic swap; a crash leaves the prior generation live; the content-hash manifest resumes only missing deltas (idempotent). Source files are the only non-reproducible asset.

---

## 5. Query / harness layer

**Recommended:** an **MCP-tool-first agentic harness.** Expose the index as a **local MCP server** (FastMCP 3.x, Python — GA Feb 2026, pin ≥3.2; decorator API, OTel, granular auth; or the TS SDK for standalone) over **stdio**. The server is the trust boundary and the only thing touching raw code. **NexusOps integration note:** the platform's decided Brain runtime (ADR-005) is exactly this — a **Python/FastMCP stdio sidecar** with a daemon-owned lifecycle (loopback-HTTP fallback). The TS-SDK option is standalone-only; the integrated sidecar is Python/FastMCP.

- **Tools (model-invoked) vs Resources (app-pinned).** Make retrieval *tools* (`search`, `get_file/get_chunk`, `graph(symbol, kind=callers|callees|impact|trace)`, `list_projects/status`) so the model drives the loop; reserve *resources* for stable artifacts (`repo://{project}/manifest`). Return structured results with stable IDs + `file:line` anchors; stream large `search`/`graph` calls.
- **Agentic RAG vs classic RAG.** Default agentic (retrieval as a tool in a ReAct loop): rewrite → fan out `search` → **retrieve-then-read whole files** → graph-trace → synthesize. **Tradeoff: 3–10× more tokens.** So gate it: classic single-pass for lookups; agentic loop for multi-hop / cross-project / compare-trace / "why/impact". Let the model pick by giving both cheap (`search`) and expensive (`get_file`, `graph`) tools + a budget rule.
- **Long-context vs RAG decision rule.** **[VERIFIED — Anthropic]** if the relevant corpus is **< ~200K tokens (~500 pages), skip the vector DB** — stuff it into context behind prompt caching (>2× faster, up to 90% cheaper, no retrieval-failure surface). Claude's **1M window** stretches a single project's full code+docs into "load it all" territory. Use RAG only above that, or for many projects. **Rule:** per-project < ~200K → cached long-context; scope > window or many projects → agentic RAG; **graph tools always-on.** (Latency caveat: 1M-token requests are slower than fetching 5 chunks — prefer retrieval when latency-sensitive even if it'd fit.)
- **Prompt-caching.** Cache the stable prefix (system + tool schemas + pinned corpus/manifest). **[VERIFIED]** pricing: cache *write* = 1.25× input (5-min TTL) or 2× (1-hr); cache *read* = 0.1× input. Breakeven: 5-min on the 2nd request, 1-hr on the 3rd. Default 5-min for spiky interactive; 1-hr only for sustained batch/eval. Order content stable→volatile. **[ASSUMPTION]** a March-2026 Claude Code regression silently dropped TTL 1h→5m — pin/verify. Contextual-Retrieval indexing itself uses caching: ~**$1.02 per 1M document tokens** when the doc is cached once.
- **Citation / grounding / hallucination guards (3 stacked layers).** (1) **Contextual Retrieval at index time** — **[VERIFIED]** measured top-20 retrieval-failure reduction **35% (embeddings) → 49% (+BM25) → 67% (+reranking)**. (2) **Native Citations API** (GA June 2025) — pass retrieved files as `document` blocks; Claude auto-emits sentence-level citations (reported source-hallucination 10%→0%, +20% references/response). (3) **Grounding contract** — require every answer to carry `file:line` anchors from tool outputs; post-validate cited spans exist; refuse/flag unsupported claims.
- **Privacy posture (per project).** What leaves = only the text the host sends (prompts + chosen tool outputs); embeddings/index stay local with local embedders. **Local-only** (BGE/E5/all-MiniLM + local rerank + on-device gen). **Hybrid (default):** local embeddings + index; only frontier *generation* cloud, over ZDR. **Cloud:** only with ZDR + DLP. Cross-cutting: **redact secrets/PII before embedding** (embedding-inversion can reconstruct near-source text), DLP gate at the MCP boundary, per-project `policy.yaml` honored by `list_projects()`.

---

## 6. Competitive landscape (full table)

| Tool | Indexing / Sync | Multi-repo? | Docs+Code? | Local? | Core gap vs. our concept |
|---|---|---|---|---|---|
| **Sourcegraph Cody / Deep Search** | Server-side code graph + RAG, webhook/crawl sync | **Yes** (best-in-class; ~10 repos/query, 300k+ enterprise) | Code + URLs/docs as context layers | Cloud / enterprise self-host | Heavy enterprise install; docs 2nd-class; per-query cap (~10), not portfolio-wide |
| **GitHub Copilot (Spaces / repo index)** | Auto semantic index per repo; Spaces = manual bundles | Partial | Docs only if added to a Space | Cloud (VS Code index can include local) | Knowledge Bases **sunset Nov 2025**; Spaces manual/single-context; no cross-portfolio graph; GitHub-centric |
| **Cursor (@codebase, @docs)** | Local AST chunk + embed; vectors to cloud (Turbopuffer), code stays local | Weak (per-workspace) | `@docs` indexes doc sites; code separate | **Hybrid** | Single-workspace bias; no federated graph; docs+code never reasoned jointly |
| **Continue.dev** | Local vector index; `@codebase`/`@docs`/`@url`; Apache-2.0 | Weak | `@docs` separate | **Yes** | Open + local but single-repo; no portfolio brain, no live code-graph federation |
| **Aider** | tree-sitter repo map + PageRank into prompt | No | Code only | **Yes** | Per-session single-repo map; no persistence, no docs, no cross-project memory |
| **Bloop** | On-device MiniLM (Tantivy + Qdrant), Rust | Local + remote | Code search only | **Yes** | Search tool, not a reasoning brain; no docs; largely dormant |
| **Pieces for Developers** | OS-level capture → local knowledge graph, 9-mo memory | N/A (activity) | Captures whatever you touch | **Yes** (air-gapped) | Captures *activity*, not a structured code+docs graph; no cross-repo architectural reasoning |
| **Unblocked** | Server-side synthesis of code + Slack/Jira/Confluence/PRs; MCP serving | **Yes** | **Yes** | Cloud | Strongest "context engine" rival, but cloud-only, team/enterprise, no live code-graph federation |
| **Glean** | 100+ connectors → per-tenant knowledge graph; real-time, ACL-aware | **Yes** | Docs-heavy; code one source | Cloud (isolated tenant) | Enterprise horizontal search; shallow code-graph; not developer/portfolio-centric; not local |
| **Danswer / Onyx** | 50+ connectors, hybrid RAG + LLM KG; MIT CE | Yes (sources) | Docs/chat; code weak | **Yes** | Generic enterprise RAG; no AST/call-graph; not multi-project code reasoning |
| **Devin / DeepWiki** | LLM + graph → auto wiki per repo; MCP server | Per-repo wikis (50k+ public) | **Yes** | Cloud (public repos) | Per-repo wiki, not federated; cloud; no local-first portfolio |
| **Greptile** | Full-repo semantic graph before review; agent swarm | Partial (`greptile.json`) | Code-centric | Cloud (self-host avail) | Optimized for PR review, not portfolio Q&A; docs secondary |
| **Dosu** | Hybrid RAG/vector → living KG from code+issues+tickets | Per-project | **Yes** | Cloud | Doc-automation/GitHub-bot framing; not a local cross-portfolio harness |
| **Ellipsis / Korbit** | PR-scoped analysis | No | Code only | Cloud | Review/mentor bots; no knowledge brain |
| **CodeGPT** | Uploaded repo "Graphs"; BYO-key; self-host EE | Multi-graph | Code + agents | Hybrid/self-host | Graphs manual/uploaded; no live federation or docs pipeline |
| **Komment** | Tracks code deltas → re-documents | Per-repo | Generates in-code docs | Cloud | Doc *generator*, not a queryable brain |
| **Swimm** | Code-coupled docs + patented Auto-sync (flags drift) | Per-repo | **Yes** (tight code↔doc) | Cloud/self-host | Authoring tool; no AI portfolio reasoning, single-repo |
| **Mintlify / ReadMe** | Doc-site index; agentic retrieval over docs | No | Docs only | Cloud | Pure docs AI; code-blind |
| **Notion AI** | Connectors + Workers/agent platform (May 2026) | Workspace-wide | Docs-heavy; code-blind | Cloud | Horizontal PKM; no code intelligence or repo graph |

### White-space — four silos none unify
1. **Code-graph engines** (Cody, Greptile, Aider, Bloop, CodeGraph) — real AST/call-graph, but docs an afterthought, reasoning per-repo or capped (~10).
2. **Enterprise RAG / context engines** (Glean, Unblocked, Onyx, Dosu) — multi-source, org-wide, but cloud-bound, ACL-gated, code is one flat source with no live structural graph.
3. **Docs tooling** (Swimm, Mintlify, ReadMe, Komment, DeepWiki) — strong docs, code-blind reasoning.
4. **Local memory** (Pieces, Continue) — local-first, but single-repo or activity-capture, not a structured portfolio brain.

**Differentiation — the un-served intersection:** local-first + frontier harness; portfolio-wide reasoning (not per-query caps); a curated docs *pipeline* (not scraped doc-sites) reasoned *jointly* with code; live code-graph *federation*. **One-line:** every rival is *cloud multi-repo OR local single-repo OR docs-only OR review-scoped* — we are the only **local-first, frontier-model brain that reasons across an entire portfolio with a curated docs pipeline fused to a live, federated code graph.**

---

## 7. cc-crew artifact inventory (the brain's ingest surface)

cc-crew is a doc-emitting pipeline; every artifact is markdown with predictable structure.

| Artifact | Path | Producer | Ingest-relevant structure |
|---|---|---|---|
| **Planning set** | `docs/planning/*.md` | `arch-draft` | `PRESEARCH`, `RESEARCH` (cited), `DECISIONS`, `ARCHITECTURE_DRAFT` (stable `§<N>`), `DIAGRAM_PLAN`, `CLAUDE_CODE_HANDOFF`; Expanded mode adds `DOMAIN_MODEL`, `THREAT_MODEL`, `REQUIREMENTS`, `RISKS`. Decisions tagged `locked`/`proposed`/`open question`/`MVP simplification`/`deferred`/`research required`. |
| **Architecture contract** | `ARCHITECTURE.md` (root) | `arch-finalize` | Binding. `## Executive summary` + stable `§N` anchors + Appendix A model/contract inventory. Loaded on-demand by section. |
| **Task tracker** | `IMPLEMENTATION_PLAN.md` (root; legacy name `MVP_TASKS.md`, renamed in scaffold migration M-0003) | `tasks-gen` | Phases carry `**Spec anchors:** ARCHITECTURE.md §X`; dense checkbox tasks with `Files:`, `Cross-doc invariant:`. Parser should stay tolerant of the legacy name. |
| **Lessons** | `<area>/LESSONS.md` | `/tdd` Step 9 | Stable-ID entries `## <a id="N"></a>N. <topic> — <rule>` + `Date`/`Source slice` + `file:line` cites + `Rule:`. Index mirrored in `<area>/CLAUDE.md`. |
| **Layer docs** | `docs/layers/OVERVIEW.md` + `NN-<slug>.md` | `layer-docs` | **Richest input.** Per-layer: `## Executive summary` (plain, 3–6 sentences) THEN depth (Responsibilities · Key components table with `path:line` · Interfaces · Data · Dependencies · Flow · Decisions · Gotchas · Connects-to). Every non-trivial claim anchored `file:line`; drift flagged. |
| **content.json** | `docs/learn-site/content.json` | `learn-site` | Already structured: `{project, layers[{id,name,plain,deep,components[{name,what,ref}],depends_on,used_by}], flow[], glossary[]}`. The cleanest ingest payload. |
| **Provenance** | `.scaffolding/manifest.json` | `scaffold-generate` | `schemaVersion 2`; `scaffoldingRepo`, `generatedFromSha`, `lastUpgradedFromSha`, `mode`, `tracks[]`, `placeholders{}`, `codeAreas[]`, `generatedFiles[{dest,template,kind}]`, `exampleBlocks[]` (plus a build `posture`, e.g. production-grade). Machine-owned, committed, never hand-edited. |
| READMEs / CLAUDE.md | root + per-area | generator | Conventions, tech-stack tables, lessons index. |

**Two load-bearing conventions the brain must honor:** (1) the **`file:line` anchor** — the universal prose⇄code join (store + re-validate as first-class metadata, not opaque text); (2) the **plain ⇄ deep dual register** — exec-summary = `plain`, depth = `deep` (store both per chunk; already serialized in `content.json`).

**Manifest reuse — EXTEND, don't fork.** The brain **reads** `manifest.json` for identity (`scaffoldingRepo`, `placeholders.PROJECT_NAME`, `codeAreas[]`, `generatedFromSha`) + `generatedFiles[]` as a doc-discovery hint, and **writes its own sibling** `.scaffolding/brain.json` / `.project-brain/manifest.json` (same SHA-stamp idiom) recording the ingest contract (artifacts + content-hashes, `ingestedFromSha`, embedding-model + chunker + schema versions, staleness pointer). **Must not edit `manifest.json`** — `/scaffold-upgrade` rewrites it and treats hand-edits as merge-base corruption.

**Skill handoff chain:**
```
arch-draft → arch-finalize → tasks-gen → scaffold-generate → /tdd ─┐
                                                                    │ (build runs)
        ┌──────────────── layer-docs ◀──────────────────────────────┘
        │                  │ writes docs/layers/ (file:line, plain/deep)
        ▼                  ▼
  learn-site ◀──── [ Nexus Brain ] ──── /ask, federation MCP
 (human site)      ingest + index + query   (agent/IDE/CI consumer)
```
`layer-docs` is the producer/normalizer; the brain slots **parallel to learn-site** as the *queryable* sink (learn-site = human view). `content.json` is effectively a pre-built ingest manifest (fast path); re-derive from `docs/layers/` for the faithful path.

---

## 8. Repo boundary & contract (condensed)

**The only coupling = `DOC_FORMAT_SPEC vN`** (carries its own `schemaVersion`; cc-crew bumps only on doc-structure change; the brain declares a `specRange`). Four parts: (a) layer-doc structure (exec-summary-first plain/deep), (b) `file:line` anchor grammar, (c) read-only manifest identity fields, (d) `content.json` schema (optional fast path). The brain owns `.project-brain/manifest.json` (sibling, never a mutation).

**Graceful degradation (the brain never requires cc-crew):** no `manifest.json` → repo-name identity + code-only; no `docs/layers/` → no plain/deep, no drift validation; no `content.json` → re-derive or skip; older `specRange` → ingest the subset + flag the rest. Mirrors how layer-docs/learn-site already degrade to code-only.

**Three sanctioned seams:** (1) brain consumes cc-crew outputs (primary); (2) cc-crew may optionally invoke the brain (terminal `/ingest`; `/ask` as a context-MCP `/tdd`/`arch-finalize` query when present); (3) shared `DOC_FORMAT_SPEC` (lives next to cc-crew).

**Independent versioning — decoupling invariants:** (1) no code imports across repos (file-format coupling only); (2) cc-crew never *requires* the brain; (3) the brain never *blocks* cc-crew, tolerates absent/older artifacts; (4) manifest identity is read-only to the brain so `/scaffold-upgrade` and brain ingest never contend. A breaking change is localized to a single version axis and the consumer degrades rather than fails.

**Relevant read-only contract files (the brain keys on these):**
- `/Users/dreddy/Documents/Dev/AI-tools/claude-code-tdd-agent-crew-scaffolding/skills/layer-docs/references/layer-docs-playbook.md` (anchor + plain/deep spec)
- `/Users/dreddy/Documents/Dev/AI-tools/claude-code-tdd-agent-crew-scaffolding/skills/learn-site/references/learn-site-playbook.md` (`content.json` schema)
- `/Users/dreddy/Documents/Dev/AI-tools/claude-code-tdd-agent-crew-scaffolding/templates/ARCHITECTURE.md`
- `/Users/dreddy/Documents/Dev/AI-tools/claude-code-tdd-agent-crew-scaffolding/templates/IMPLEMENTATION_PLAN.md` (legacy: `MVP_TASKS.md`)
- `GENERATE-WITH-CLAUDE.md:325` (manifest schema, Step 12.5)

---

## 9. Key sources

**RAG stack:** voyage-code-3 (Voyage AI blog; MongoDB writeup) · Ollama embedding benchmarks (Morph) · Embedding models 2026 (Milvus) · cAST AST chunking (arXiv 2506.15655) · Anthropic Contextual Retrieval · Late Chunking (Jina/arXiv 2409.04701) · LanceDB FTS + hybrid + rerankers docs; Tantivy removal (GH #2998) · sqlite-vec vs LanceDB (Shaharia) · rerankers leaderboard (Agentset); reranker guide 2026 (ZeroEntropy) · RAG frameworks 2025 (langcopilot); LlamaIndex vs LangChain (IBM).

**Federation / code-intel:** SCIP; cross-repo nav; scip-typescript (Sourcegraph) · Stack Graphs (GitHub blog + arXiv 2211.01224) · Glean indexing + incremental (Meta) · Cursor secure indexing · Aider repo-map · Cody remote-repo context.

**Sync / freshness:** Cursor indexing (Engineer's Codex) · LangChain embeddings (Analytics Vidhya) · Watchman; fswatch; fsmonitor-watchman hook; githooks · SQLite WAL (sqlite.org) · launchd tutorial (launchd.info); ThrottleInterval (ilostmynotes); launchd.plist man page · systemd/User (ArchWiki); OpenClaw daemon FAQ (MeshMini) · RAG postmortem (Decompressed); OpenViking #1066; Embedding portability (Mixpeek); Drift-Adapter (arXiv 2509.23471); embedding spaces (Gary Stafford).

**Harness:** Anthropic Contextual Retrieval + Claude Cookbook · Citations API + docs · Prompt-caching docs; TTL regression (#46829); Anthropic pricing 2026 (Finout) · FastMCP; MCP Python SDK; FastMCP 3.0 guide · Agentic RAG vs Classic (TDS; digitalapplied) · Long-context vs RAG (SitePoint) · RAG/PII exposure (Protecto; sandipanhaldar).

**Competitors:** Sourcegraph Cody docs + multi-repo context · Cursor indexing + secure indexing · Copilot Spaces + indexing + KB sunset · Continue.dev · Aider · Bloop/Qdrant · Pieces LTM · Unblocked context engine · Glean knowledge graph · Onyx · DeepWiki (Cognition) · Greptile · Dosu · Ellipsis · Korbit · CodeGPT · Komment · Swimm auto-sync · Mintlify AI Assistant · Notion dev platform · cross-repo reasoning limits (buildmvpfast) · Code Digital Twin (arXiv 2503.07967).
