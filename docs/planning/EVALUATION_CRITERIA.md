# EVALUATION_CRITERIA — Nexus Brain

> `/arch-draft` Phase 7. How we know it works — and the regression gate that *defends the north star*. The eval harness is a **first-class, CI-gated deliverable** (D-10), not an afterthought. Tooling: bespoke custom evaluators + Langfuse datasets/experiments/scores (D-9). Posture: production-grade.

## Acceptance bar (the north star, D-6)
**Trust / citation correctness.** A confident-but-wrong or stale citation is the cardinal failure. The harness must make this *measurable* and *gated* — a release cannot regress the trust metrics.

## The eval harness (CI-gated)
- Golden datasets **versioned in-repo**; runs via the cc-crew `/eval` path; custom code + LLM-as-judge evaluators; scores/experiments recorded in Langfuse (local).
- Every embedding/rerank/context provider change re-benchmarks against the same golden sets (D-23) — "best results" is a *living* property.
- Deterministic where possible (fixed seeds, recorded fixtures for non-deterministic surfaces).

## Metrics (with rough target direction; thresholds set at first bake-off)
| Dimension | Metric | Target |
|---|---|---|
| **Trust** | Citation precision / recall | maximize precision (no false cites); high recall |
| **Trust** | Grounding-gate correctness — % of unsupported claims correctly flagged | → 100%; **zero** unflagged unsupported claims |
| **Trust** | Stale-anchor false-confidence rate — answers citing a non-`live` anchor as live | **zero** (hard gate) |
| **Retrieval** | Recall@k on a golden Q→relevant-chunk set (code + docs) | high; the differentiator |
| **Retrieval** | Anchor-revalidation accuracy (`live/stale/moved/unknown` vs ground truth) | high |
| **Federation** | Cross-repo answer correctness; degraded results **marked**, never silently wrong | no silent cross-repo errors |
| **Freshness** | Index lag after save; git-hook convergence; drift-detection latency | bounded; converges |
| **Security** | **Redaction recall** — secret-shaped fuzz inputs → leaks into index/cloud | **zero leaks** (hard gate; property/fuzz test) |
| **Safety** | Unauthorized-mutation incidents (allowlist violations) | **zero** |
| **Perf** | LanceDB `optimize()` latency, index-build RAM, steady-state disk on a real portfolio | within budget (O-LANCE-BAKEOFF) |

## Bake-offs (research-required, feed the harness)
- **Reranker:** voyage-rerank-2.5 vs zerank-2 vs cohere-rerank-4-pro, on a 100–500-query in-domain code+docs golden set (D-23 / O-BAKEOFF).
- **Cloud embedder:** voyage-code-3 vs gemini-embedding-2 on the same corpus.
- **LanceDB local bake-off:** maintenance-contract invisibility on a representative multi-repo corpus on a typical Mac (O-LANCE-BAKEOFF).
- **Long-context vs RAG routing threshold:** validate the ~200K cutover on real cost/latency.

## Non-deterministic surfaces (eval-covered, not unit-tested)
Live model generation, real embeddings, the agent loop, federation ranking — covered by the eval suite + recorded fixtures + injectable clock/seed; deterministic logic (chunking, anchor parse/revalidate, hybrid fusion math, redaction, manifest/version stamping, state machines) is unit-test-first (TDD).

## "Done" for a slice
A slice is done when: its deterministic logic is test-first green, its eval metrics don't regress the gate, redaction-recall fuzz is zero-leak, and (for retrieval slices) Recall@k + grounding correctness hold on the golden set.
