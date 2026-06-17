# ASSUMPTIONS — Nexus Brain

> `/arch-draft` Phase 9. Working premises the design leans on. Markers: **[VERIFIED]** (probe/source) · **[LIKELY]** · **[ASSUMPTION]** (unconfirmed working premise) · **[research-required]**. Track these — a wrong one propagates.

- **A-1 [VERIFIED]** LanceDB covers embedded + versioning + larger-than-memory + hybrid together; rivals don't (D-25 research, 2026-06-16).
- **A-2 [VERIFIED]** qwen3-embedding-4b (local) + voyage-code-3 (cloud) + qwen3-reranker / voyage-rerank-2.5 are current-best for code RAG (D-23 research, 2026-06-16).
- **A-3 [VERIFIED]** OpenInference auto-instruments LlamaIndex + Anthropic → standard OTel → swappable backends (Context7, 2026-06-16).
- **A-4 [LIKELY]** The LanceDB maintenance contract (optimize/cleanup/git-SHA-tag/RAM-bounded builds) can be made invisible to users on a typical Mac with a real portfolio — **must verify** (O-LANCE-BAKEOFF).
- **A-5 [VERIFIED 2026-06-16 — re-probe, D-27]** CodeGraph (`@colbymchenry/codegraph`) is at **v1.0.1, MIT, bus-factor 1**. Direct reads of the 5 tables **survive** (`schema_versions=1`). **Native single-graph co-indexing exists for same-root nested repos; there is NO native federation across separate `.codegraph` DBs and NO precise cross-repo resolution (heuristic name-matching only) → the federation router is still required.** Pinned `=1.0.1` behind a `CodeGraphPort` + **tree-sitter fallback** (graceful-degrade if absent/abandoned). MCP default surface = 4 tools; `trace`/`context` deleted (→ `explore`); DB path overridable via `CODEGRAPH_DIR`.
- **A-6 [research-required]** Cross-repo symbol resolution via `unresolved_refs` + globally-namespaced `qualified_name` is achievable at acceptable quality; fallback = side-by-side-marked (D-2/O-FED).
- **A-7 [ASSUMPTION]** A bundled PyInstaller sidecar of the Python core notarizes + runs under macOS hardened runtime (NexusOps does this for its FastMCP sidecar — precedent).
- **A-8 [ASSUMPTION]** Claude session transcripts remain parseable at a stable-enough location/schema for opt-in ingestion; Codex deferred until its schema is validated.
- **A-9 [VERIFIED]** NexusOps Phase 8 (Brain seam) is deferred/unbuilt → we conform to frozen platform primitives + co-design the rest (IMPLEMENTATION_PLAN.md, 2026-06-15).
- **A-10 [ASSUMPTION]** Local embedding/rerank inference (qwen3-4b ~2.5GB) is fast enough on target Macs for interactive re-index + query; the cloud opt-in covers users who need more.
- **A-11 [LIKELY]** The DuckDB Lance core extension is stable enough to (optionally) back the federation router in-process; the hand-rolled fan-out router is the baseline if not.
