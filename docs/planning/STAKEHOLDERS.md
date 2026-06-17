# STAKEHOLDERS — Nexus Brain

> `/arch-draft` Phase 3 (Stakeholders & Reviewers). Solo build → the owner holds most hats; the two real "reviewers" are the cross-model finalize pass and the downstream NexusOps integration.

## North-Star Acceptance Bar `[locked — owner 2026-06-15]`
**Trust / citation correctness is THE primary rejection bar.** Every served claim must carry a **live, re-validated `file:line` anchor**; the system **refuses or flags** unsupported claims; a confident-but-wrong or **stale** citation is the cardinal failure. Freshness, privacy, and federation are **load-bearing supports beneath** this bar, not substitutes for it. This north star prioritizes: anchor parsing + **continuous revalidation**, the **grounding gate** (post-validate every cited span exists), and a **provenance packet** on every answer.

## Stakeholder Matrix
| Stakeholder | Cares About | Would Reject If | Evidence Needed | Architecture Must Address |
|---|---|---|---|---|
| **Owner — as product** | Does it answer "when/how/why did we do X" across the portfolio, fast, trustably? | Answers feel like generic RAG; citations can't be trusted; too slow to be daily-driver | Working evidence-backed answers with clickable `file:line`; freshness stamps | The grounding gate; anchor revalidation; the ask flow (long-context vs RAG routing) |
| **Owner — as security/data** | No secret/PII in the index or sent to cloud; consented transcript ingestion; local-first | Any credential reachable in the store or a cloud prompt; transcripts ingested without opt-in | Redaction property/fuzz tests; keychain-only secrets; consent gate | `THREAT_MODEL.md`; Redactor-before-embed; per-project `policy.yaml` |
| **Owner — as eng/maintainer** | Reproducible, recoverable, debuggable; sane sync; not a daemon zoo | Index corruption with no recovery; N hot watchers melt the machine; non-deterministic indexes | Content-hash reproducibility; blue-green re-embed; on-demand workers + idle eviction | `DATA_MODEL.md`; sync/freshness design; service management |
| **`/arch-finalize` (Brain-2, different model)** | A thorough, honest, well-tagged draft it can adversarially audit | Hand-waved load-bearing decisions; missing flows/failure-modes/data-model; unflagged scope cuts | Tagged decisions; stop-conditions honored; anchored `ARCHITECTURE_DRAFT.md` | Every decision tagged; gap-audit-ready structure |
| **NexusOps integration (downstream)** | Nexus Brain conforms to frozen platform primitives + the propose-only law when integrated | Brain invents action types; mutates directly; ignores shared IDs / EvidenceType / outbox | The standalone APIs map cleanly to `MAIN_PLATFORM_INTERFACE.md` v0.2 | A clean internal seam between the standalone core and the (later) Gateway client |
| **Persona B/C (future collaborators)** | A cited, guided understanding without reading everything | Knowledge is locked in the owner's head; no provenance | Evidence chips; plain/deep registers | Reuse of the same grounded-answer surface |

## Tradeoffs Stakeholders Tolerate
- **Latency for trust:** the owner tolerates a slower agentic-RAG / long-context answer if it is correctly cited (trust > speed).
- **Cloud generation, local index:** hybrid posture (local embeddings/index; only frontier *generation* cloud over ZDR) is acceptable; full-cloud is not the default.
- **Federation imperfection:** cross-repo *edge* resolution may be best-effort/degraded **as long as it is marked**, never silently wrong.
