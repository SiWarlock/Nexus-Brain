# OPEN_QUESTIONS — Nexus Brain

> `/arch-draft` Phase 9. What's still undecided/unverified. Each has an owner-default so the build never blocks. Most load-bearing product/architecture decisions are LOCKED (DECISIONS D-1..D-25); these are the residual spikes + tuning.

| # | Question | Default / fallback | Gate |
|---|---|---|---|
| **OQ-1** | Cross-repo symbol resolution quality (O-FED) | side-by-side-marked union (never silently wrong) | federation spike before promoting cross-repo edges |
| **OQ-2** | Reranker bake-off winner (cloud): voyage-rerank-2.5 vs zerank-2 vs cohere-4-pro (O-BAKEOFF) | voyage-rerank-2.5 (stack-coherent) | in-domain golden-set bake-off |
| **OQ-3** | Cloud embedder: voyage-code-3 vs gemini-embedding-2 | voyage-code-3 | same bake-off |
| **OQ-4** | LanceDB maintenance-contract invisibility on real HW (O-LANCE-BAKEOFF / A-4) | the contract as specced (D-25) | pre-GA local bake-off |
| **OQ-5** | Long-context vs RAG cutover threshold (~200K) | ~200K tokens/project | validate on real cost/latency |
| **OQ-6** | `.project-brain/manifest.json` exact schema | the DATA_MODEL sketch | freeze at first ingest slice |
| **OQ-7** | Local generation model for strict local-only mode | TBD (e.g. a local Qwen/Llama) | only when a user opts into strict-local |
| **OQ-8** | How much cc-crew parsing is hardcoded vs a workflow-pack parser | hardcode cc-crew first; generalize via a pack parser later | P1 |
| **OQ-9** | Codex session schema for ingestion | defer Codex until validated (Claude first) | P1/P3 |
| **OQ-10** | `jina-*` / `zerank-2` license per-tag (commercial use) | exclude from defaults; API-only / opt-in | before exposing in the menu |
| **OQ-11** | Standalone product **name** — confirmed **Nexus Brain** (D-19); only branding polish (icon, bundle id) remains | Nexus Brain / `nexus`/`nb` CLI | — |
| **OQ-12** | When NexusOps integration begins (the NexusOpsHost adapter) | after standalone MVP is solid; same monorepo (D-21) | post-MVP |

**Decided (formerly open):** embedding/privacy posture (D-23), platform scope (D-16), UI tech (D-17), timebox (D-18), name (D-19), packaging (D-20), repo/separation (D-21), ship-obs (D-22), vector DB (D-25).
