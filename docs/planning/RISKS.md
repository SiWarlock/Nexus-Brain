# RISKS — Nexus Brain

> `/arch-draft` Phase 14 (risk register). Each: risk · impact · likelihood · mitigation · test/spike signal. `TR` technical · `PR` product · `SR` security · `IR` integration. Posture: production-grade → each risk has a falsifiable signal.

| # | Risk | Impact | Likelihood | Mitigation | Signal |
|---|---|---|---|---|---|
| **TR-1** | **Cross-repo federation quality** — `unresolved_refs`/`qualified_name` resolution is the unproven bet (D-2) | High (the differentiator) | Med | Side-by-side-marked fallback (never silently wrong); ship single-project-solid regardless | Federation spike (O-FED); eval: cross-repo correctness + degraded-marking |
| **TR-2** | **LanceDB maintenance contract leaks to users** — optimize/compaction/RAM-build stutters on a real Mac portfolio (D-25 W1/W4) | High (UX + trust) | Med | Scheduled background optimize/cleanup; per-project datasets keep builds small; RAM-bounded batches; monitor `num_unindexed_rows` | O-LANCE-BAKEOFF: index-build RAM, optimize latency, steady-state disk |
| **TR-3** | **LanceDB pre-1.0 API churn** (handle pattern flipped across minors; leaks pre-0.25) (D-25 W5) | Med (ergonomics, not data — substrate stable) | Med | Pin `lancedb`; version-appropriate handle pattern; recycle sidecar; data safe on Lance format 2.1 | CI pins + integration test vs LlamaIndex |
| **TR-4** | **FastMCP 3.0 migration** breaking changes (D-24) | Med | High (known) | Budget migration; pin major; conformance tests | Migration slice green |
| **TR-5** | **Embedding drift / re-embed cost** on model/dim change across a portfolio | Med | Med | Blue-green generations + rollback; content-hash resume; re-embed only deltas (D-14) | Crash-recovery + re-embed-equivalence tests |
| **TR-6** | **CodeGraph dependency** — availability, concurrency under load, or schema change (A-5) | Med | Low–Med | External-dep detection + verify; read-only gating on `schema_versions`; code-only/tree-sitter fallback | `setup` probe; schema-gate test |
| **TR-7** | **Index freshness under burst / branch-switch** (watcher misses) | Med (stale answers) | Med | git-hook backstop guarantees convergence; debounce; drift radar marks staleness | Freshness/convergence eval |
| **TR-8** | **Sidecar notarization** (PyInstaller core under macOS hardened runtime) (A-7) | Med (ship blocker) | Low | Follow the NexusOps sidecar precedent; deep-sign order; `spctl` CI gate | Notarization CI gate |
| **PR-1** | **Trust collapse** — a confident answer with a stale/wrong citation (the cardinal failure, D-6) | Critical | Med w/o gate | Grounding gate (answer-but-flag) + anchor revalidation + provenance; CI-gated trust evals | Grounding-correctness + stale-anchor-false-confidence = 0 |
| **PR-2** | **"Just another RAG tool"** — federation/grounding not visibly better | High | Med | Lead with evidence chips + freshness + cross-portfolio; eval Recall@k | User-rated usefulness; Recall@k |
| **PR-3** | **Install friction** (CodeGraph + Ollama + model multi-GB pulls) | Med (adoption) | Med | `setup` provisions with progress UX; degrade gracefully if a dep is absent | Setup success rate; degraded-mode UX |
| **SR-1** | **Secret/PII leak into the index or cloud** (embedding-inversion) (D-15) | Critical | Med w/o redactor | Redaction-before-embed (no holes) + keychain-only secrets + property/fuzz test | Redaction-recall fuzz = **zero leaks** (hard gate) |
| **SR-2** | **Cloud provider trains on your code** (Voyage default opt-IN) (PH-3) | High | High w/o gate | Enforce + document Voyage opt-out; ZDR for generation; local-first default | Adapter refuses cloud without opt-out confirmed |
| **SR-3** | **Transcript ingestion without consent** | High | Low w/ gate | Per-project opt-in stricter than docs; no raw transcripts; exclude `thinking` | Consent-gate test |
| **SR-4** | **Allowlist violation** — agent mutates outside the bounded set (D-4) | High | Low | Bounded-allowlist enforcement + preview + audit; don't-clobber merge | Unauthorized-mutation = 0 |
| **SR-5** | **Telemetry exfiltration** — accidental phone-home (D-22) | High (privacy) | Low | OTel off-by-default + local-only; no analytics/crash beacons; CI check for egress | No-egress test |
| **IR-1** | **NexusOps seam drift** — platform contracts evolve before Phase 8 builds | Med | Med | Conform to frozen primitives; `HostPort` adapter isolates; `MAIN_PLATFORM_INTERFACE.md` is the contract (D-21) | Contract snapshot test at the seam |
| **IR-2** | **Repo/packaging coupling** — standalone vs embedded fork drift | Med | Low | One core, two adapters; published `nexus-brain-core`; never fork (D-21) | Core API stability test |

**Top-3 to retire early:** TR-1 (federation spike), TR-2/O-LANCE-BAKEOFF (maintenance-contract bake-off), SR-1 (redaction property/fuzz harness). These gate the north star + the foundation.
