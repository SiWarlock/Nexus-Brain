# REQUIREMENTS — Nexus Brain

> `/arch-draft` Phases 6 + 8 (extracted + posture-inferred). Posture: **production-grade** → hardening rows are in-scope baseline, tagged `[PH]` (production-hardening), not deferrable. `[FR]` functional · `[NFR]` non-functional · `[PH]` production-hardening · `[P1]/[P2]` deferred tier. Each maps to a flow (USER_FLOWS) and/or decision (DECISIONS). MUST/SHOULD/MAY per RFC-2119.

## Functional — Ingestion & Indexing
- **FR-1 [FR]** MUST register a project from a local repo path; maintain a portfolio registry; per-project stores (PB-1). → F2
- **FR-2 [FR]** MUST discover docs source-agnostically (md/mdx/rst/adoc, README/ARCHITECTURE/ADR, `.github`, OpenAPI/schemas, code-embedded) honoring `.gitignore` + `.brainignore`; classify producer / `doc_type` / owned·foreign·supplemental (PB-2). → F2
- **FR-3 [FR]** MUST ingest even when no docs/scaffold exist (code-only); MUST NOT hard-require complete docs (R-PARTIAL). → F2
- **FR-4 [FR]** MUST anchor-aware chunk: docs heading-split + late-chunking; code AST (`CodeHierarchyNodeParser`, pinned + tree-sitter fallback) + Contextual Retrieval (D-24). → F2
- **FR-5 [FR]** MUST embed via the pluggable provider (local `qwen3-embedding-4b` default / cloud opt-in), stamp `{model,dim,schema,sha}` (D-23). → F2
- **FR-6 [FR]** MUST write `.project-brain/manifest.json`; MUST NOT mutate `.scaffolding/manifest.json` or the CodeGraph store (PB-1; D-12). → F2

## Functional — Retrieval & Answering (the north star)
- **FR-7 [FR]** MUST do hybrid (dense + BM25) retrieval → rerank → whole-file hydration; route long-context-vs-RAG by corpus size (D-13). → F3/F4
- **FR-8 [FR]** MUST return evidence-backed answers with a Provenance Packet (PB-4/PB-10). → F3
- **FR-9 [FR]** MUST enforce the **grounding gate** (answer-but-flag; post-validate every cited span exists; opt-in strict mode) (D-7). → F3
- **FR-10 [FR]** MUST parse + continuously **revalidate anchors** (`live|stale|moved|unknown`); MUST include drift state in provenance (PB-3). → F3/F8
- **FR-11 [FR]** MUST support portfolio/federated query: union N stores → RRF rank-fusion; cross-repo symbol resolution best-effort + **marked** when degraded (D-2). → F5
- **FR-12 [FR]** MUST expose retrieval as **MCP tools** (`search`/`get_file`/`graph`/`list_projects`/`status`) AND drive the **embedded agent** over the same core (D-3). → F3/F4
- **FR-13 [FR]** MUST honor `policy.yaml` + redact at the MCP boundary regardless of caller (D-5). → F4

## Functional — Sessions, Plans, Workflow, Drift
- **FR-14 [FR]** SHOULD ingest Claude Code sessions (Codex `[P1]`) — opt-in, redacted, no raw transcripts, no `thinking`, → episode cards with commit-link confidence (PB-5). → F7
- **FR-15 [FR]** MUST parse implementation plans (`IMPLEMENTATION_PLAN.md`, legacy `MVP_TASKS.md`); SHOULD extract phases/tracks/tasks/anchors (PB-6). → F2/F3
- **FR-16 [FR]** MUST distinguish workflow pack vs instance; detect personalized instances (PB-7). → F2/F8
- **FR-17 [FR]** MUST run the **drift radar** + ownership-gated owned-doc refresh (allowlist + preview + don't-clobber) (D-4). → F8
- **FR-18 [P2]** (integrated) MUST produce **Action Plans** via the NexusOps Gateway (propose-only) + consume the platform outbox (PB-8/PB-9). → F11

## Functional — Install / lifecycle
- **FR-19 [FR]** MUST provide `setup`/`add`/`sync`/`status`/`ask` CLI; idempotent, reversible, consented host-config (MCP + skills registration); central store (R-INSTALL/R-ADD). → F1/F2/F12
- **FR-20 [FR]** MUST provision external deps (CodeGraph, Ollama + model) via `setup` (detect→install→verify) with progress UX (D-20). → F1
- **FR-21 [FR]** MUST ship as a signed/notarized desktop app (Tauri) + Homebrew Cask + bundled Python sidecar; CLI installable headless (D-17/D-20). → F1
- **FR-22 [FR]** MUST support `uninstall`/reset (reverse every host mutation; preserve-data option) (D-4). → F12

## Non-functional
- **NFR-1 [NFR]** Index lag bounded after file save; git-hook backstop guarantees convergence (watcher=freshness, hooks=correctness) (D-14). → F6
- **NFR-2 [NFR]** Reproducibility: source + model-stamp deterministically reproduce the index; **no in-place re-embed** (blue-green) (D-14).
- **NFR-3 [NFR]** Latency: classic single-pass for lookups; agentic RAG for multi-hop; graph tools always-on (D-13). Per-project <~200K tokens → cached long-context.
- **NFR-4 [NFR]** Local-first by default; hybrid posture (local index/embed, cloud generation over ZDR) (D-23).
- **NFR-5 [NFR]** Pluggability: embedding/rerank/context/model providers swappable per-project + version-stamped (D-23).

## Production-hardening (in-scope baseline)
- **PH-1 [PH]** **LanceDB maintenance contract** (D-25): `optimize()` after each upsert batch + monitor `num_unindexed_rows≈0`; scheduled `cleanup_old_versions()`; git-SHA-tag every build; single-writer-per-dataset + read-only federation; RAM-bounded batched index builds; pin `lancedb`; `spawn` not `fork`; arm64 wheels verified in CI.
- **PH-2 [PH]** **Redaction-before-embed** has no holes (secrets/PII), gated at persist + embed + cloud-egress; secrets only as keychain refs (D-15). → THREAT_MODEL.
- **PH-3 [PH]** **Cloud provider privacy gate** — enforce + document Voyage training opt-out (and any cloud provider's training terms) (D-23).
- **PH-4 [PH]** Crash-safety/recovery: atomic-swap generations; prior generation serves on crash; idempotent resume from content-hash manifest (D-14; F9/F10).
- **PH-5 [PH]** Embedding-model/dim change → blue-green re-embed + rollback (D-14).
- **PH-6 [PH]** **Observability** instrumented (OTel + OpenInference) but OFF by default + local-only + never phones home; eval harness CI-gated (D-9/D-10/D-22).
- **PH-7 [PH]** All host-config mutations idempotent + reversible + consented (D-4); no telemetry exfiltration.
- **PH-8 [PH]** FastMCP **3.0 migration** + pinned major (D-24).
- **PH-9 [PH]** Graceful degradation everywhere: model API down → retrieval-only; CodeGraph down → catch-up/CLI fallback; worker evicted → cheap re-attach; schema/model mismatch → exclude + flag (F5/F10).

## Coverage check
Every PB-1..PB-11 + every USER_FLOWS flow maps to ≥1 FR/PH above. No requirement is flow-orphaned (USER_FLOWS stop-condition satisfied).
