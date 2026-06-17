# CLAUDE_CODE_HANDOFF — Nexus Brain

> `/arch-draft` Phase 16. Instructions for the NEXT stage (`/arch-finalize`, Brain 2 — a different model, on purpose). **Do not implement.** Finalize the architecture, then `/tasks-gen`.

## Build posture (carry through the model switch)
**Production-grade · Expanded mode · no timebox** (correctness/best-practice over speed). Finalize + gap-audit against this posture: error paths, idempotency, observability, secrets, deploy/rollback, and the **LanceDB maintenance contract** are in-scope baseline, not deferrable. The standalone-MVP-first framing must be preserved.

## What `/arch-finalize` should do
1. **Read ALL of `docs/planning/*`** (the 18 artifacts below) + the upstream `docs/product/PRD.md`, `docs/integrations/MAIN_PLATFORM_INTERFACE.md`, `docs/requirements/ONBOARDING_AND_DOC_LIFECYCLE.md`, `docs/research/RESEARCH_DOSSIER.md`.
2. **Do NOT start implementation.**
3. **Run a second-pass gap audit** (~13 dimensions): missing flows · lifecycle states · failure modes · interfaces/schemas (esp. the `HostPort`/port contracts, the `.project-brain/manifest.json` schema, the LanceDB chunk schema) · source-of-truth clarity · unresearched deps · inconsistent decisions · overbuilt scope · missing tests/deploy/trust-boundaries/diagrams/task anchors. Pay special attention to: the **federation cross-repo spike** (O-FED), the **LanceDB maintenance-contract invisibility** (O-LANCE-BAKEOFF), the **redaction property/fuzz** harness, and the **NexusOps seam** (conform to frozen primitives; co-design the rest).
4. **Propose precise edits; confirm load-bearing changes with the owner;** then produce the **finalized `ARCHITECTURE.md`** (repo root) from the project's `scaffold/templates/ARCHITECTURE.md`, binding every section to stable `§N` anchors.
5. **Only then** generate `IMPLEMENTATION_PLAN.md` (`/tasks-gen`) from `scaffold/templates/IMPLEMENTATION_PLAN.md`, decomposing §19's build order.

## Artifacts written (Expanded set, 18)
`PRODUCT_BRIEF · USERS · STAKEHOLDERS · USER_FLOWS · DOMAIN_MODEL · REQUIREMENTS · CONSTRAINTS · EVALUATION_CRITERIA · ASSUMPTIONS · OPEN_QUESTIONS · RESEARCH · DECISIONS · RISKS · THREAT_MODEL · DATA_MODEL · ARCHITECTURE_DRAFT · DIAGRAM_PLAN · CLAUDE_CODE_HANDOFF` (all in `docs/planning/`).

## Decisions locked (D-1..D-25, see DECISIONS.md)
Posture/mode · federation-from-day-one · two-surfaces+embedded-agent · bounded-allowlist vs propose-only · trust posture (local + loopback) · north star (citation correctness) · grounding gate · LlamaIndex orchestration · OTel-first observability (Langfuse+SigNoz+Collector) · bespoke eval harness · LanceDB per-project (+ maintenance contract, adversarially verified best) · three-store model · RAG pipeline · versioning/freshness · redaction+keychain · platform (macOS-first/Linux-ready) · Tauri desktop + Python sidecar · no timebox · name **Nexus Brain** · packaging (dmg/brew/sidecar) · one-core/two-adapters/monorepo+published-core · ship-instrumented-but-silent · embedding/rerank providers (qwen3-embedding-4b/voyage-code-3/qwen3-reranker/voyage-rerank-2.5, pluggable).

## Still-open / research-required (resolve in finalize or as spikes)
`O-FED` cross-repo resolution · `O-LANCE-BAKEOFF` maintenance-contract invisibility · `O-BAKEOFF` reranker/cloud-embedder bake-offs · `O-VAL` model-fact validations · `OQ-6` manifest schema freeze · `OQ-7` strict-local generation model. None blocks the first vertical slice. (Detail: `OPEN_QUESTIONS.md`.)

## Notes for the finalizer
- **Repo dir is `project-brain/`** (the product name is **Nexus Brain**; dir name ≠ product name). A doc rename pass to "Nexus Brain" across the PRD/docs is pending — flag if it should happen before or after finalize.
- The **scaffold** is freshly vendored at `scaffold/` (current; uses `IMPLEMENTATION_PLAN.md`). Use `scaffold/templates/` for the finalized `ARCHITECTURE.md` + `IMPLEMENTATION_PLAN.md`.
- The NexusOps platform docs (sibling `../NexusOps/`) are the integration ground truth; `MAIN_PLATFORM_INTERFACE.md` v0.2 is the seam contract.
