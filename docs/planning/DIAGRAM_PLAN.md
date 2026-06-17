# DIAGRAM_PLAN — Nexus Brain

> `/arch-draft` Phase 17. Plans the architecture diagrams (drawn at finalize/build, not now). Each: purpose · type · key nodes/edges · the §anchor it illustrates.

## D1 — System topology (full-scope) `[primary]`
- **Type:** component/deployment. **Illustrates:** §2 (final).
- **Nodes:** Tauri desktop app · Python core sidecar (retrieval core, ingest/index workers, federation router, drift radar, embedded agent, redactor, provider registry, HostPort) · external agents (Claude Code/Codex/CI) · Ollama · Voyage/Claude APIs · per-project {LanceDB, CodeGraph, manifest} · (dashed) NexusOps Gateway + outbox.
- **Edges:** loopback HTTP/in-process (UI↔core) · stdio MCP (external agents↔core) · read-only (core↔stores) · API calls (redacted) · dashed propose-only (→NexusOps).

## D2 — Ports-and-adapters (the seam) `[primary]`
- **Type:** hexagonal. **Illustrates:** §7 / §2.5 / D-21 (final).
- **Center:** core. **Ports:** HostPort, EventSource, EmbeddingProvider/Reranker/ContextStrategy/ModelProvider, ObservabilitySink, SecretStore. **Adapters:** StandaloneHost ‖ NexusOpsHost(P2); Ollama/Voyage/OpenAI providers; keychain; OTel sink.

## D3 — The three-store data plane `[primary]`
- **Type:** data-flow. **Illustrates:** §5 / DATA_MODEL (final).
- **Shows:** ① LanceDB (embeddings+BM25+anchors+version tags) ② CodeGraph SQLite (external, read-only) ③ manifest/registry; index worker writes ①③; fuse-at-query; git-SHA version tags; blue-green generations.

## D4 — Retrieval & grounding pipeline `[primary]`
- **Type:** sequence/flow. **Illustrates:** §8–§10 (final).
- **Index lane:** discover→classify→chunk→context-aug→redact→embed→LanceDB→optimize. **Query lane:** scope→route→hybrid→rerank→graph-tools→hydrate→generate→**grounding gate**→answer+provenance.

## D5 — Federation read model `[secondary]`
- **Type:** fan-out. **Illustrates:** §11 (final). Router → N×{LanceDB,CodeGraph} read-only → RRF union; cross-repo via unresolved_refs (spike); DuckDB-Lance option; on-demand workers + LRU eviction.

## D6 — Sync & freshness loop `[secondary]`
- **Type:** state/flow. **Illustrates:** §12 (final). Watcher+git-hooks→debounce→content-hash delta→re-embed→tombstone+replace→optimize; drift radar→anchor states→owned-doc refresh.

## D7 — Observability fan-out `[secondary]`
- **Type:** pipeline. **Illustrates:** §19 / D-9 (final). App (OTel+OpenInference) → Collector → {gen_ai→Langfuse; all→SigNoz}; ship-silent note.

## D8 — Security/trust boundary `[secondary]`
- **Type:** boundary/trust-zone. **Illustrates:** §18 / THREAT_MODEL (final). The machine boundary; MCP-boundary redaction; keychain; allowlist vs propose-only; redaction-before-embed; no-egress.

## D9 — State machines `[reference]`
- **Type:** state. Index generation · Anchor · Project · Worker · Doc lifecycle (from DATA_MODEL).
