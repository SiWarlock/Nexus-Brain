# Anchor remap — ARCHITECTURE_DRAFT §N → binding ARCHITECTURE.md §N

> Produced by `/arch-finalize` (2026-06-16). The draft's `§0–§21` are **superseded**; the binding `ARCHITECTURE.md` uses the open-ended append-only `§1–§26` + Spec Anchor Index + Appendix A (LBD-17). Downstream references (`DIAGRAM_PLAN.md` "Illustrates", `DECISIONS.md`) updated to the final column.

| Draft anchor | Final anchor(s) | Note |
|---|---|---|
| §0 Decision ledger | §3 | now a pointer → DECISIONS.md D-1..D-27 |
| §1 Goals & non-goals | §1 | |
| §2 Product definition | §1 + §2 | folded |
| *(none)* | **§2.5 Subsystem DAG & seams** | NEW (template-required; was absent → critical C-14) |
| §3 Locked decisions | §3 | |
| §4 System overview / §4.1 topology | §2 | |
| §4.2 architectural laws | §4 (invariants) | |
| §5 Domain model | §4 | |
| §6 Core module architecture | §7 (ports) + §2.5 | |
| §7 Data & state model | §5 + §6 | split (LanceDB + maintenance contract carved to §6) |
| §8 Retrieval & grounding pipeline | §9 + §10 | split (grounding/anchors/provenance carved to §10) |
| §9 Federation | §11 | |
| §10 Sync & freshness | §12 | |
| §11 Agent & surfaces | §13 + §14 + §15 | split (agent / MCP-boundary / CLI+UI) |
| §12 Host adapters | §7 | |
| §13 Providers | §16 | |
| §14 Observability & evals | §19 | |
| §15 Security & trust boundaries | §18 | |
| §16 Packaging, install & lifecycle | §20 + §21 | split (packaging / setup-lifecycle) |
| §17 Testing strategy | §19 + §10 + §7 | test seams → §7/§10; eval harness → §19 |
| §18 Failure-mode contract | §22 | expanded to a full inline table |
| §19 MVP boundaries & sequencing | §24 | |
| §20 NexusOps integration scope | §23 | |
| §21 Open questions & spikes | §26 | |
| *(new)* | §17 Session memory & episode cards · §25 Cross-cutting · Spec Anchor Index · Appendix A | new homes for previously-embedded content |
