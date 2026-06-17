# ARCHITECTURE_DRAFT.md — Nexus Brain

> **Status:** Brain-1 ROUGH DRAFT (`/arch-draft`). For adversarial finalization by `/arch-finalize` (Brain 2, different model) → then `/tasks-gen`. **Not binding yet.** Tags: `[LOCKED]` (DECISIONS-confirmed) · `[PROPOSED]` · `[PH]` production-hardening · `[P1]/[P2]` deferred · `[SPIKE]` · `[OPEN]`.
> **Planning mode:** Expanded · **Build posture:** Production-grade · **No timebox** (correctness/best-practice over speed). Dates 2026-06-15/16.
> **Architecture sentence:** *Nexus Brain is a local-first, multi-project memory engine whose delivery-agnostic core ingests code + docs + (opt-in) sessions into per-project, version-stamped LanceDB indexes fused at query time with an external code graph, and answers through a frontier model where every claim carries a continuously-revalidated `file:line` anchor — shipped standalone (a Tauri desktop app + bundled Python sidecar) and, later, embedded in NexusOps as a propose-only sidecar, with the only difference a swapped host adapter.*
> **Anchor stability:** `§N` are stable IDs — append, never reorder. Companion artifacts (binding detail): `DECISIONS.md` (D-1..D-25), `DATA_MODEL.md`, `DOMAIN_MODEL.md`, `REQUIREMENTS.md`, `THREAT_MODEL.md`, `EVALUATION_CRITERIA.md`, `RISKS.md`, `RESEARCH.md`.

## §0 — Decision ledger
The load-bearing decisions are recorded once in **`DECISIONS.md` (D-1..D-25)** and are binding where confirmed. This draft references them by id; it does not restate rationale.

## §1 — Goals & non-goals `[LOCKED]`
**Goals (MVP):** portfolio-wide, evidence-backed, `file:line`-anchored Q&A over many local repos; the **trust/citation north star** (grounding gate + continuous anchor revalidation); local-first privacy (redaction-before-embed; keychain); federation-from-day-one (D-2); two surfaces over one core — embedded agent (desktop UI/CLI) + MCP server (D-3); drift/freshness ("never stale silently"); production-grade foundation.
**Non-goals (MVP):** an IDE / terminal mux / git client / cloud SaaS; replacing Claude Code/Codex/CodeGraph/cc-crew; multi-user RBAC; agent egress isolation; the NexusOps integration *runtime* (seam designed, adapter deferred — §20); Windows; Codex session ingestion (`[P1]`).

## §2 — Product definition & scope `[LOCKED]`
Authoritative: `PRODUCT_BRIEF.md`, `docs/product/PRD.md` (v2). Five capabilities: **memory · retrieval · reasoning · action-planning · drift**. Standalone-first; embedded later. First vertical slice (D-18): `add` one repo → ingest → hybrid+graph retrieve → grounded answer → eval green.

## §3 — Locked architecture decisions `[LOCKED]`
See §0 / `DECISIONS.md`. Spine: ports-and-adapters core (D-21) · LanceDB per-project (D-11/D-25) · three-store fuse-at-query (D-12) · hybrid+rerank+hydrate RAG (D-13) · grounding gate (D-7) · pluggable providers (D-23) · LlamaIndex Workflows (D-8) · OTel-first observability (D-9/D-22) · Tauri desktop + Python sidecar (D-17) · redaction + keychain (D-15).

## §4 — System overview `[LOCKED]`
### §4.1 — Process topology
```
macOS host (single user = trust boundary)
 ┌ Nexus Brain desktop app (Tauri: Rust host + WebView; NexusOps-ui-kit) — the standalone face
 │     ↕ loopback HTTP + per-launch token (D-5)  OR  in-process
 ┌ Nexus Brain CORE (Python sidecar; PyInstaller-bundled) — the engine; runnable headless
 │   retrieval core · ingestion/index workers · federation router · drift radar · embedded agent (LlamaIndex Workflow)
 │   redactor · provider registry · ObservabilitySink · SecretStore(keychain) · HostPort(StandaloneHost)
 │     ↕ stdio MCP (+opt loopback)   → external agents (Claude Code / Codex / CI)
 │     ↕ Ollama (local models) · Voyage/Claude APIs (cloud, redacted, opt-out enforced)
 │     ↕ read-only                   → per-project: LanceDB datasets + CodeGraph SQLite + .project-brain/manifest
 └ (later) HostPort(NexusOpsHost) → NexusOps Gateway (propose-only) + event outbox  [§20, P2]
```
### §4.2 — Architectural laws `[LOCKED]`
1. **The index is a cache, not source-of-truth** (reproducible from source + model-stamp).
2. **No claim is served as cited unless its anchor is `live`** (grounding gate; north star).
3. **Side-effects flow only through the active `HostPort`** — standalone bounded-allowlist / integrated propose-only; the core never raw-mutates.
4. **Redaction-before-embed has no holes**; secrets only as keychain refs.
5. **Single-writer-per-index; the federation router is read-only** (D-25 W3).
### §4.3 — Why this shape
One delivery-agnostic core with **ports** (`HostPort`, `EventSource`, `EmbeddingProvider`/`Reranker`/`ContextStrategy`/`ModelProvider`, `ObservabilitySink`, `SecretStore`) lets standalone + embedded be two adapters, never a fork (D-21), and makes every external model/store/backend swappable + version-stamped.

## §5 — Domain model `[LOCKED]`
Authoritative: `DOMAIN_MODEL.md` + `DATA_MODEL.md`. Entities, the three-store map, ubiquitous language, the 7 core invariants, and state machines (Index generation · Anchor · Project · Worker · Doc lifecycle; WorkflowInstance = 12 frozen R-7 states for NexusOps alignment). Shared IDs map 1:1 to NexusOps's 22 `IdKind` at the seam.

## §6 — Core module architecture `[PROPOSED]`
Ports-and-adapters (hexagonal). Python packages in one monorepo (D-21):
- `nexus-brain-core` (publishable): `ingest` (discover·classify·chunk·redact) · `index` (embed·LanceDB write·version/optimize/cleanup) · `retrieval` (hybrid·rerank·hydrate·route) · `grounding` (anchor parse/revalidate·gate·provenance) · `federation` (router·RRF) · `agent` (LlamaIndex Workflow) · `drift` (radar·owned-doc refresh) · `sessions` (episode cards) · `providers` (registry) · `ports` (the interfaces) · `redactor` · `manifest`/`registry`.
- Entrypoints: `nexus-brain-cli` · `nexus-brain-mcp` (FastMCP 3.x server) · `nexus-brain-app` (Tauri; StandaloneHost + embedded agent) · later `nexus-brain-nexusops` (NexusOpsHost adapter).

## §7 — Data & state model `[LOCKED]`
Authoritative: `DATA_MODEL.md`. Three stores: ① LanceDB per-project dataset (embeddings + BM25 + anchors + version tags), ② CodeGraph SQLite (external, read-only), ③ `.project-brain/manifest.json` + `~/.project-brain/` registry. **LanceDB maintenance contract `[PH]` (D-25):** `optimize()` after each upsert batch + `num_unindexed_rows≈0` monitoring; scheduled `cleanup_old_versions()`; git-SHA version tags (doubles as R3); single-writer; RAM-bounded batched builds; pin `lancedb`; `spawn` not `fork`. Blue-green re-embed on model/dim change.

## §8 — Retrieval & grounding pipeline `[LOCKED]`
**Index time:** discover → classify (owned/foreign/supplemental) → chunk (docs heading-split+late-chunk; code AST `CodeHierarchyNodeParser` pinned + tree-sitter fallback) → **context augmentation** (voyage-context-3 cloud / late-chunking local) → **redact** → embed (provider) → LanceDB write + stamp + `optimize()`.
**Query time:** scope → route (per-project <~200K → cached long-context; else agentic RAG) → **hybrid (dense+BM25)** → **rerank** (~30–50→~10) → CodeGraph structural tools (callers/callees/impact/trace) → **whole-file hydration** → frontier model (Contextual Retrieval + Citations API) → **grounding gate** (post-validate cited spans; answer-but-flag; opt-in strict) → answer + evidence chips + **provenance packet** + freshness banner. FTS boolean logic lives in the router (D-25 W7).

## §9 — Federation `[LOCKED + SPIKE]`
Router reads N per-project LanceDB datasets **read-only** + queries N CodeGraph DBs; **union + RRF rank-fusion**; gate each on `schema_version`/`model_version`. **Cross-repo symbol resolution** via `unresolved_refs.reference_name` + namespaced `qualified_name` = `[SPIKE]` (O-FED); fallback = side-by-side-marked. **Implementation option:** the **DuckDB Lance core extension** (ATTACH+JOIN+hybrid over Lance datasets, in-process) can back the router (D-25). On-demand worker activation + LRU idle eviction; only the router is always-on.

## §10 — Sync & freshness `[LOCKED]`
Watchman/fswatch (freshness) + `post-commit/merge/checkout` git-hooks (correctness backstop); debounce; content-hash delta (file-hash → files, chunk-hash → chunks) → re-embed → tombstone+replace keyed on `source_path` → `optimize()`. **Drift radar** revalidates anchors (`live|stale|moved|unknown`), ranks by authority×recency×code-agreement, triggers ownership-gated owned-doc refresh (don't-clobber). *Watcher = freshness; hooks = convergence.*

## §11 — Agent & surfaces `[LOCKED]`
**Embedded agent** = a LlamaIndex Workflow (D-8) driving the retrieval **tools** (the same internal core the MCP server exposes), calling Claude. **MCP server** (FastMCP 3.x) exposes `search`/`get_file`/`graph`/`list_projects`/`status` — the **trust boundary** (redact + policy-filter before results leave; stdio default, opt loopback+token). **CLI** (`nexus`/`nb`: setup/add/sync/status/ask). **Desktop UI** (Tauri; chat + evidence chips + freshness + project mgmt). All are clients of one core.

## §12 — Host adapters & the standalone↔embedded seam `[LOCKED]`
`HostPort` (D-21) authorizes + performs side-effects. **StandaloneHost:** bounded-mutation allowlist (own store · owned-doc refresh w/ don't-clobber · consented host-config), reads git directly, embedded agent + desktop/CLI/MCP. **NexusOpsHost `[P2]`:** propose-only — mutations → typed `ActionPlan`/`ActionRequest` to the Gateway; consumes the redacted outbox; shared IDs; drawer surface (= `MAIN_PLATFORM_INTERFACE.md` v0.2). The core never forks; embedded = additive adapter. Build the `HostPort` seam from day one.

## §13 — Providers (pluggable, version-stamped) `[LOCKED]`
Per-project `policy.yaml` at `add` (D-23). Embedding: local `qwen3-embedding-4b` default / cloud `voyage-code-3` opt-in (+ alts). Reranker: local `qwen3-reranker` / cloud `voyage-rerank-2.5` (+ bake-off). Context: voyage-context-3 / late-chunking. Generation: Claude (hybrid posture). **Privacy gate `[PH]`:** cloud adapters enforce + document training opt-out (Voyage). Switching a provider = blue-green re-embed.

## §14 — Observability & evals `[LOCKED]`
**Instrument once:** OTel + OpenInference (LlamaIndex + Anthropic) across the whole system. **OTel Collector hub** fans out: `gen_ai.*` → **Langfuse** (LLM traces + evals + datasets); all spans/metrics/logs → **SigNoz** (operational APM). Thin `ObservabilitySink` seam. **Eval harness** (CI-gated, golden sets in-repo, custom evaluators → Langfuse) defends the north star (`EVALUATION_CRITERIA.md`). **Ship instrumented-but-silent `[PH]`:** OTel off-by-default + local-only + **never phones home**; backends + harness are dev/CI only (D-22).

## §15 — Security & trust boundaries `[LOCKED]`
Authoritative: `THREAT_MODEL.md`. Binding invariants: redaction-before-embed (zero-leak fuzz gate) · secrets keychain-only · bounded-allowlist (standalone) / propose-only (integrated) · MCP-boundary redaction+policy regardless of caller · no open port by default · cloud training opt-out enforced · transcript consent · no phone-home · idempotent/reversible/consented host-config · owned-doc don't-clobber · grounding gate (trust).

## §16 — Packaging, install & lifecycle `[LOCKED]`
Tauri-bundled signed/notarized `.dmg`/`.app` (auto-updater) + **Homebrew Cask**; CLI via bundle/pipx/brew formula; **bundled PyInstaller sidecar** (no system Python) (D-17/D-20). `setup` provisions CodeGraph + Ollama + model (detect→install→verify, idempotent/consented, progress UX). `uninstall` reverses every host mutation. Notarization (hardened runtime, deep-sign, `spctl` CI gate) — follow the NexusOps sidecar precedent `[PH]`. Linux later: AppImage/tarball + systemd `--user`.

## §17 — Testing strategy `[LOCKED]`
**Test-first (deterministic):** chunking, anchor parse/revalidate, hybrid-fusion math, redaction, manifest/version stamping, state machines, federation rank-fusion, the maintenance-contract scheduling logic. **Eval-covered (non-deterministic):** generation, real embeddings, the agent loop, retrieval quality — golden sets + recorded fixtures + injectable clock/seed (`EVALUATION_CRITERIA.md`). **CI gates:** unit (merge) · redaction-recall fuzz=0 (merge) · eval no-regression (release) · notarization (release).

## §18 — Failure modes & recovery `[LOCKED]`
Model API down → retrieval-only degraded answer. CodeGraph down → 300s idle normal; catch-up sync / one-shot CLI. Worker evicted → cheap re-attach. Crash mid-reindex → prior generation serves (atomic swap); idempotent delta resume. Corrupt store → rebuild from source. Schema/model mismatch → exclude + flag. Stale anchor → marked, never silently trusted. (Detail: `RISKS.md`, `USER_FLOWS` F10.)

## §19 — MVP boundaries & sequencing `[LOCKED]`
**Build order (invariants → spine → breadth):** (0) spikes: O-FED federation, O-LANCE-BAKEOFF, redaction fuzz harness. (1) core skeleton + ports + provider registry + keychain. (2) ingest→index one repo (chunk·redact·embed·LanceDB·manifest·maintenance contract). (3) retrieval core (hybrid·rerank·hydrate·CodeGraph tools) + grounding gate + provenance. (4) embedded agent (LlamaIndex Workflow) + CLI `ask`. (5) MCP server (trust boundary). (6) sync/freshness + drift radar. (7) federation router (multi-repo). (8) Tauri desktop UI. (9) sessions/episode cards (opt-in). (10) observability + eval harness wired. **Deferred `[P1]/[P2]`:** Codex sessions · NexusOpsHost adapter + drawer · advanced workflow-pack parsing · policy-automation.

## §20 — NexusOps integration scope (forward) `[P2]`
The `NexusOpsHost` adapter (§12) + `MAIN_PLATFORM_INTERFACE.md` v0.2: propose-only `ActionPlan` via the Gateway, redacted-outbox consumption, shared IDs, the drawer. NexusOps Phase 8 is **deferred/unbuilt** → conform to frozen primitives (22 IDs, EventEnvelope, RiskLevel 0–4, ActionPlan shape, propose-only law), co-design `BrainEventMapping` + the `brain.*` catalog. The published `nexus-brain-core` API is the dependency contract.

## §21 — Open questions & spikes `[OPEN]`
Authoritative: `OPEN_QUESTIONS.md` + `RISKS.md`. Top spikes before/within build: **O-FED** (cross-repo resolution) · **O-LANCE-BAKEOFF** (maintenance-contract invisibility) · **redaction property/fuzz** harness · reranker/cloud-embedder **bake-offs** · long-context-vs-RAG threshold. None blocks the first vertical slice.
