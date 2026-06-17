# RESEARCH — Nexus Brain

> `/arch-draft` Phase 10. Current/external facts verified through research, with sources + architecture impact. Consolidates: the original `docs/research/RESEARCH_DOSSIER.md` (2026-06-03) + two adversarial research workflows (2026-06-16) + Context7 library checks. Markers: **[VERIFIED]** / **[UNVERIFIED]** / **[research-required]**.

## R1 — Embedding + rerank stack (workflow, 9 agents, adversarially verified, 2026-06-16)
- **[VERIFIED] Local embedding:** `qwen3-embedding-4b` (Apache-2.0, ~2.5GB Ollama, 40K ctx, Matryoshka, dense-only → pair w/ BM25) beats bge-m3 (~80 MTEB-Code vs no code-specific score). **Upgrade** from the 06-03 pick. Sources: github.com/QwenLM/Qwen3-Embedding, arxiv 2506.05176, ollama.com/library/qwen3-embedding.
- **[VERIFIED] Cloud embedding:** `voyage-code-3` confirmed best for code (32K ctx, ~13–17% lead, no voyage-code-4). `gemini-embedding-2` (MTEB-Code 84.0) a challenger but **[UNVERIFIED]** vs Voyage for code (vendor-only) → bake-off. Sources: docs.voyageai.com, arxiv 2605.27295.
- **[VERIFIED] Reranker:** local `qwen3-reranker` (MTEB-Code 81.20 vs bge-reranker-v2-m3 41.38). Cloud default `voyage-rerank-2.5` but **not the leader** → bake-off vs zerank-2 (#1) / cohere-rerank-4-pro (#2). Source: Qwen3 paper Table 4, Agentset leaderboard Feb 2026.
- **[VERIFIED] Context augmentation:** add `voyage-context-3` (cloud, ~6.76% chunk gain, no per-chunk LLM call); local = Anthropic Contextual Retrieval / late-chunking.
- **Honesty correction:** the "81.20" headline = the *reranker*, not the embedder (vendor-table confusion). → **Impact:** D-23 provider menu.

## R2 — Vector store (workflow, 10 agents, adversarial, 2026-06-16)
- **[VERIFIED] LanceDB CONFIRMED decisively** — only embedded store covering R1(in-process)+R3(versioning)+R7(larger-than-memory) together. Apache-2.0, $30M Series A, Lance SDK 1.0/format 2.1 stable; high-level `lancedb` API pre-1.0 Alpha (pin). Rivals fail a hard req: Chroma (no versioning + macOS RAM blow-ups), sqlite-vec (pre-v1 churn + no versioning + ~280× slower at 100k), DuckDB-VSS (crash-unsafe HNSW persistence), Qdrant-local/Milvus-Lite (dev-only), Weaviate-embedded (spawns server). Sources: lancedb docs, sprytnyk.dev 700M-vector retrospective, GitHub issue trackers, neutral 2026 comparisons.
- **[VERIFIED] Maintenance contract required** (W1 optimize-after-write, W2 version cleanup + git-SHA tags, W3 single-writer/read-only-federation, W4 RAM-bounded builds, W5 pin + handle pattern). → **Impact:** D-25, PH-1.
- **[VERIFIED] DuckDB Lance core extension (May 2026)** — ATTACH+JOIN+hybrid over Lance datasets in-process → optional federation-router backing (keeps R1). → **Impact:** D-25/architecture §federation.
- **[research-required]** Pre-GA local bake-off (O-LANCE-BAKEOFF).

## R3 — Observability + evals (Context7, 2026-06-16)
- **[VERIFIED] OpenInference** auto-instruments LlamaIndex + Anthropic → standard OTel → any OTLP backend (vendor-neutral). **Langfuse** OSS self-hostable but **filters out non-LLM spans** (layer-2 only; no infra metrics/logs/alerting). **SigNoz** = OSS OTel-native single-pane (traces+metrics+logs+alerts) for layer-1. **LangSmith** cloud-default + phones home → privacy tension. → **Impact:** D-9 (Collector fan-out: gen_ai→Langfuse, all→SigNoz), D-22 (ship instrumented-but-silent).
- **[VERIFIED]** Orchestration: LangGraph's durable-execution strengths map weakly (propose-only offloads heavy execution to NexusOps) → DIY/LlamaIndex Workflows (D-8).

## R4 — Stack sanity (2026-06-16)
- **[VERIFIED]** KEEP LanceDB, Anthropic Citations API (GA grounding), CodeGraph (vector-seed→graph-traverse = 2026 best practice). **FastMCP 3.0** has breaking changes (`ui=`→`app=`, removed kwargs) → migration + pin (D-24). Pin `CodeHierarchyNodeParser` + tree-sitter fallback.

## R5 — From the original dossier (2026-06-03, still relevant)
- RAG technique stack: hybrid (dense+BM25) → rerank → **whole-file hydration** (biggest code-QA lever); long-context-vs-RAG rule (<~200K → cached long-context); 3-layer grounding (Contextual Retrieval + Citations API + post-validation). CodeGraph probe: per-repo SQLite, no native cross-repo (federate at orchestration layer); WAL read-only union; launchd/systemd on-demand activation + idle eviction; content-hash incremental + tombstone-replace; never mix embedding models in a store. Full detail + competitor landscape: `docs/research/RESEARCH_DOSSIER.md`.

## Net architecture impacts
Provider menu (D-23) · LanceDB + maintenance contract + DuckDB-Lance federation option (D-25) · OTel-first layered observability (D-9) · FastMCP 3.0 migration (D-24) · all confirm the data plane (DATA_MODEL) unchanged.
