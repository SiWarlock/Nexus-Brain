# PRODUCT_BRIEF — Nexus Brain

> **Planning mode:** Expanded · **Build posture:** Production-grade · **Date:** 2026-06-15
> **Source:** `docs/product/PRD.md` (v2) + `docs/integrations/MAIN_PLATFORM_INTERFACE.md` (v0.2) + `docs/requirements/ONBOARDING_AND_DOC_LIFECYCLE.md` + `docs/research/RESEARCH_DOSSIER.md`.
> **Stage:** `/arch-draft` Brain-1 rough draft. Captures Phase 0 (Intake) + Phase 1 (Product Mechanics). Tags: `locked` / `proposed` / `open question` / `scope simplification` / `production-hardening` / `deferred` / `research required`.

---

## Phase 0 — PRD Intake

### Product in One Sentence
A **local-first, multi-project memory · retrieval · reasoning · action-planning engine** that indexes code + docs + git/PR history + (opt-in) Claude/Codex session history per project, fuses a **curated docs pipeline** with a **federated live code graph**, and serves **evidence-backed, `file:line`-anchored** answers to a frontier model — usable **standalone first**, and designed to later integrate into the **NexusOps** platform as a **propose-only** memory/reasoning sidecar.

### What the Product Is
Portfolio memory-with-provenance · anchor-aware drift detection · hybrid (dense + BM25) retrieval with rerank + whole-file hydration · a local **MCP server** (the trust boundary) · an **embedded frontier-model agent** behind a standalone chat **UI + CLI** · action **planning** (propose-only) · per-project local stores with **federated** query.

### What the Product Is Not
A full IDE · a terminal multiplexer · a git client · a cloud SaaS (local-first by default) · a replacement for Claude Code / Codex / CodeGraph / cc-crew · a workflow orchestrator by itself · a system that silently mutates code, tickets, git state, or host config · a generic enterprise RAG tool.

### Primary Problem
**Memory with provenance** across many agent-driven repos, sessions, tickets, worktrees, branches, PRs, and docs: *what happened, when, which agent/session, which task, which files, which commit/PR, which decision governed it, what's now stale, and what should happen next* — answered with **trustable, re-validated citations**, not opaque vector chunks.

### Primary User
**Persona A — the portfolio solo developer** (the owner): runs many local projects with Claude Code / Codex sessions and project-specific workflow scaffolding. Secondary: **B** (new teammate needing a cited guided understanding), **C** (tech lead / reviewer tracking drift + PR impact), **D** (future NexusOps platform user).

### Core Workflow
`setup` (once per machine: detect/install CodeGraph, register MCP server, create `~/.project-brain/` store + registry) → `add <repo>` (init CodeGraph index · discover + classify docs · anchor-aware chunk · first ingest · write `.project-brain/manifest.json` · enroll sync) → **index** kept fresh (watcher + git-hook backstop; idle-evicted per-project workers; federation router) → **ask** (hybrid retrieval → rerank → whole-file hydration → frontier model → grounded answer with `file:line` anchors + freshness) → (opt-in) **session memory** → episode cards → **drift radar** → (later, integrated) **action plans** proposed through the NexusOps Action Gateway.

### Explicit PRD Requirements
`PB-1` project registration/ingestion · `PB-2` source-agnostic doc discovery · `PB-3` anchor-aware chunking + drift detection · `PB-4` retrieval + evidence-backed answering + grounding policy · `PB-5` opt-in session memory (local embeddings, no raw transcripts, no `thinking` blocks) · `PB-6` implementation-plan awareness (`IMPLEMENTATION_PLAN.md`, legacy `MVP_TASKS.md`) · `PB-7` workflow-pack awareness (pack vs instance) · `PB-8` action planning (propose-only, 5 modes) · `PB-9` platform event consumption (redacted outbox) · `PB-10` evidence/provenance packet · `PB-11` safety/privacy/consent (redaction-before-embed, keychain, audited requests).

### Implied Requirements
Install/bootstrap (CodeGraph dependency detect→install→verify; idempotent/reversible/consented MCP + skills registration; central store) · sync/freshness (Watchman/fswatch watcher + `post-commit/merge/checkout` git-hook correctness backstop; debounce; on-demand worker activation + idle eviction; federation router reading per-project SQLite read-only over WAL) · redaction-before-embed (secret/PII; embedding-inversion threat) · embedding-version consistency + re-embed/blue-green on model/dim change · per-project `policy.yaml` · `.brainignore` · owned/foreign/supplemental doc model + don't-clobber discipline.

### External Dependencies
**CodeGraph** (`@colbymchenry/codegraph@0.9.7`, per-repo SQLite + stdio MCP; no native cross-repo) · **LanceDB** *(or sqlite-vec)* vector+FTS store · **embeddings** (voyage-code-3 cloud / **bge-m3** local via Ollama) · **LlamaIndex** (parsing/`CodeHierarchyNodeParser`) · **FastMCP 3.x** (Python, stdio) · **Watchman/fswatch** · **frontier model API** (Claude; the embedded agent) · OS service manager (launchd/systemd `--user`). **Later:** NexusOps platform contracts (`nexusops-shared` 0.34.0).

### Ambiguities / Open Questions
Standalone product **name** (`Nexus Brain` working; possible **Nexus/Nexus Brain**) · **vector store** lock (LanceDB vs sqlite-vec) · **standalone UI tech** stack · how much cc-crew parsing is hardcoded vs workflow-pack-parser · `.project-brain/manifest.json` schema · CodeGraph multi-repo/concurrency unverified bits · embedding model default (cloud voyage vs local bge-m3) and the privacy posture default.

### Initial Risk Areas
**(Technical)** CodeGraph **multi-project federation** is the load-bearing **unproven bet** (no native cross-repo resolution; orchestration-layer fan-out + union-read + `unresolved_refs` join) `research required`; embedding **drift/re-embed cost**; **index freshness** under burst/branch-switch; long-context-vs-RAG cost/latency. **(Privacy/security)** **redaction recall** for secrets/PII before embedding (embedding-inversion can reconstruct near-source text) `production-hardening`; transcript-ingestion consent; idempotent/reversible host-config mutations. **(Product)** trust collapse if a confident answer carries a stale/wrong citation. **(Integration)** the NexusOps Brain seam (their Phase 8) is **deferred/unbuilt** — design to the frozen primitives, co-design the rest.

### Recommended Planning Mode
**Expanded** — confirmed by owner (privacy/secret surface + rich domain model justify a first-class `THREAT_MODEL.md` + `DATA_MODEL.md`).

### Build Posture
**Production-grade** — confirmed by owner. Scope is the standalone MVP, but the **load-bearing paths are production-grade**: redaction-before-embed, secret handling, transcript consent, idempotent/reversible host-config mutations, freshness/recovery, and grounding/citation correctness are **in-scope baseline**, not deferrable. Cuts are explicit, flagged `scope simplification` / `deferred` items. A demo is OPTIONAL under this posture.

---

## Phase 1 — Product Mechanics

### Core Object of Value
The durable core object is the **per-project index** — a *rebuildable derived cache* keyed by content hashes (source files + an embedding-model-version stamp deterministically reproduce it; source files are the only non-reproducible asset). It **yields** the unit of delivered value: a **grounded answer**. The **anchor** (a typed, continuously re-validated `file:line` edge between prose and code) is the **trust primitive** that makes answers trustworthy.

### State-Changing Actions
`add` a project · ingest/index (chunk + embed) · re-embed on file/chunk-hash change · **tombstone + replace** stale chunks keyed on `source_path` · revalidate anchors against current code · ingest a session → redacted **episode card** · register/refresh sync (watcher + git-hook) · re-embed/blue-green on embedding-model/dim change · (later, integrated) **propose** an action plan to the NexusOps Gateway.

### Lifecycle
project **added** → **indexed** → **queryable** ⇄ **kept-fresh** (watcher = freshness; git-hooks = guaranteed convergence) → **drift-detected** (anchors/docs stale) → **re-indexed** (incremental, content-hash delta; temp generation + atomic swap; prior generation stays live on crash) → **archived/removed**. Per-project workers are **lazy-started on demand and idle-evicted**; only the **federation router** is always-on.

### Units / Records
**Anchors** (`file:line` edges) · **chunks** (doc heading-split / code AST via `CodeHierarchyNodeParser`, + Contextual Retrieval blurbs) · **embeddings** (model+dim+schema-version stamped) · **episode cards** (redacted session summaries) · **manifests** (`.project-brain/manifest.json`, sibling to the read-only cc-crew `.scaffolding/manifest.json`) · **provenance packets** (per answer) · the per-project **registry** row (`project_id → db_path + schema_version + model_version`).

### Who/What Creates the Main Objects
`add`/`sync` create the index + anchors + chunks. The **embedded agent** (UI/CLI, calling the Claude API) **and** external agents (Claude Code/Codex over **MCP**) both create **queries** → grounded answers. Session ingestion creates episode cards. The user creates `policy.yaml` / `.brainignore`.

### Who/What Resolves / Completes Them
The **retrieval core** resolves a query → hybrid retrieve → rerank → whole-file hydrate → frontier model → grounded answer + provenance. The **drift radar** resolves staleness → flag/refresh. The **sync engine** resolves change → incremental re-index.

### Hidden Mechanics
The index is a *cache, not a source of truth* (source files are) — so **freshness + reproducibility** are first-class. **Two consumption surfaces share one retrieval core**: (1) the embedded agent behind the standalone chat UI/CLI, (2) the MCP server external agents drive — the **MCP server is the trust boundary** and the only thing touching raw code. **Federation is read-side**: N per-repo CodeGraph DBs + N per-project vector stores, union-read behind one router; cross-repo *symbol* resolution rides `unresolved_refs.reference_name` + `qualified_name`.

### Confirmed Mechanics (locked this phase)
- **Federation from day one** `[locked — owner 2026-06-15]`. The MVP ships the federation router + multi-project registry + N-store union-read + cross-repo query. **Cross-repo *symbol/edge resolution* is `research required`** with a fallback to "N graphs side-by-side" (per-project answers union-ranked) when resolution is unavailable — the system must degrade gracefully, never fail.
- **Two surfaces; embedded agent is the MVP face** `[locked — owner 2026-06-15]`. Nexus Brain ships an **embedded frontier-model agent loop** (calls the Claude API) behind a standalone chat **UI + CLI** — the "interact with the agent" surface — **and** exposes the **MCP server** for external agents (Claude Code/Codex/CI). Both are clients of one internal **retrieval core**; the MCP server is the shared trust boundary.

### Impossible-by-Construction (load-bearing invariants)
Embed raw transcripts or secrets/PII · answer without evidence (grounding gate) · silently mutate user files, host config, tickets, or git state · mix embedding models/dims within one store · (integrated) execute any operational action directly — Brain only **proposes** through the NexusOps Action Gateway.

### Still Ambiguous (→ later phases)
Default embedding model + privacy posture (cloud voyage-code-3 vs local bge-m3) · vector store lock · standalone UI tech · federation router transport (in-process WAL read vs MCP-proxy) · how the embedded agent's loop relates to the MCP tool surface (shared internal API vs the agent calling its own MCP).
