# DOMAIN_MODEL — Nexus Brain

> `/arch-draft` Phase 5 (entities · relationships · ubiquitous language · invariants). Schemas + state machines live in `DATA_MODEL.md`; this is the conceptual map. Posture: production-grade.

## Ubiquitous language (glossary)
- **Portfolio** — the set of all registered projects on one machine (the federation scope).
- **Project** — one local repo registered with Nexus Brain (`project_id`). Owns its three stores (DATA_MODEL ①②③).
- **Index** — a project's derived, versioned LanceDB dataset (a *generation*). Rebuildable from source + model-stamp.
- **Chunk** — an embedded unit (code AST node / doc heading-section) with text, vector, BM25, and an **anchor**.
- **Anchor** — the trust primitive: a typed `file:line[-range]` edge between prose/answer and code, continuously revalidated (`live|stale|moved|unknown`).
- **EmbeddingProvider / Reranker / ModelProvider / ContextStrategy** — pluggable, version-stamped components (D-23).
- **Episode Card** — a redacted, summarized session (Brain-owned; opt-in). Raw transcripts never embedded.
- **Query → Answer** — a question resolved by the retrieval core into a **grounded answer** + **Provenance Packet**.
- **Provenance Packet** — the evidence + freshness + confidence record attached to every answer (the audit of trust).
- **Evidence / Evidence Chip** — a user-visible reference (serializes to NexusOps `EvidenceRef` at the seam).
- **Manifest** — `.project-brain/manifest.json`, Nexus-Brain-owned (sibling to the read-only cc-crew `.scaffolding/manifest.json`).
- **Registry** — `~/.project-brain/`, the portfolio catalog the **Federation Router** reads.
- **Policy** — per-project `policy.yaml` (providers, privacy posture, ingestion consent, `.brainignore`).
- **Drift** — divergence between indexed content-hashes and current source; surfaced by the **Drift Radar**.
- **Host** — the adapter that authorizes + performs side-effects: **StandaloneHost** (bounded allowlist) or **NexusOpsHost** (propose-only). The core depends on the abstract `HostPort` (D-21).
- **Workflow Pack / Instance** — a reusable scaffold template vs a project-specific personalized install (PRD §7.7–7.8; cc-crew is the first pack, optional).
- **Action Plan** — (integrated) a proposed multi-step plan submitted to the NexusOps Gateway; Brain never executes (D-4).

## Entity-relationship map
```
Portfolio 1──* Project 1──1 Index(generation*)        Project 1──1 CodeGraph store (external)
Project 1──1 Manifest      Project 1──1 Policy         Project 1──* WorkflowInstance(0..1 active)
Index 1──* Chunk 1──1 Anchor *──1 SourceFile@SHA
Project 1──* EpisodeCard (opt-in)   EpisodeCard *──* Commit (confidence-weighted)
Query 1──1 Answer 1──1 ProvenancePacket 1──* Evidence *──1 {Chunk|Anchor|Commit|EpisodeCard|PlanTask|Ticket|...}
RetrievalCore ──uses──> EmbeddingProvider, Reranker, ContextStrategy, ModelProvider (all pluggable, stamped)
FederationRouter ──reads(read-only)──> N×Index + N×CodeGraph store  (union + RRF rank-fusion)
HostPort ◁──implements── StandaloneHost | NexusOpsHost
Core ──emits──> ObservabilitySink (OTel)   Core ──reads/writes secrets via──> SecretStore (keychain)
```

## Core invariants (domain rules; tested)
1. **The Index is a cache, never source-of-truth** — source files + model-stamp reproduce it (DATA_MODEL §reproducibility).
2. **Every Answer carries a ProvenancePacket; no claim is presented as cited unless its Anchor is `live`** (the grounding gate, D-7; north star D-6).
3. **No Chunk is embedded before passing the Redactor; no Anchor trusted when not `live`.**
4. **One EmbeddingProvider per Index generation** — never mixed; switching = blue-green new generation (D-14).
5. **A Project's CodeGraph store is read-only to Nexus Brain; the `.scaffolding/manifest.json` is read-only; Nexus Brain only writes its own `.project-brain/` + LanceDB datasets.**
6. **Side-effects flow only through the active `HostPort`** — StandaloneHost (bounded allowlist) or NexusOpsHost (propose-only). The core never performs a raw mutation.
7. **Single-writer-per-Index; the Federation Router is read-only** (D-25 W3).

## State machines
See `DATA_MODEL.md` (Index generation · Anchor · Project · per-project Worker · Doc lifecycle). WorkflowInstance = the 12 frozen R-7 states (NexusOps alignment).
