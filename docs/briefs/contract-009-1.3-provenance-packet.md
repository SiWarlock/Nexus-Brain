# /tdd brief — provenance_packet_contract

## Feature
Freeze the `ProvenancePacket` contract (§10) — the evidence + freshness + confidence record attached to **every** answer (the audit of trust): cited `file:line[]` spans, the SHAs they're grounded at, contributing project/source/session ids, index freshness, overall confidence, drift markers, and the aggregated `EvidenceRef` list. Last of Phase 1.3's three trust contracts (Anchor `5b50b5f` + EvidenceRef `518da07` landed).

## Use case + traceability
- **Task ID:** 1.3 (slice **1.3b** — ProvenancePacket; completes Phase 1.3)
- **Architecture sections it implements:** `ARCHITECTURE.md §10` (the Provenance Packet — north-star grounding record), Appendix A (ProvenancePacket + EvidenceRef row, line 217), §2.5 (import-DAG seam → schema-snapshot pin). §4 (parse-don't-trust).
- **Related context:** field authority reconciled across Appendix-A:217 + §10 (line 110) + DOMAIN_MODEL (ER map `Answer 1──1 ProvenancePacket 1──* Evidence`) + DATA_MODEL (the fuller draft). Composes the frozen `EvidenceRef` (1.3c, `model.evidence`). LESSON 6 (named vs deferred enum) + LESSON 7 (whitespace-strip identity) apply. The §5-model conventions (frozen/extra-forbid/Field/omit-each/snapshot) carry over.

## Acceptance criteria (what "done" means)
- [ ] `ProvenancePacket` is a frozen Pydantic v2 model (`frozen=True`, `extra="forbid"`) with **10 fields**: `project_ids`, `source_ids`, `citations`, `commit_shas`, `session_ids`, `recorded_sha`, `index_freshness`, `confidence`, `drift_markers`, `evidence`.
- [ ] **`spec(§10)` schema-snapshot test** pins `set(ProvenancePacket.model_fields) == EXPECTED_PROVENANCE_FIELDS` (§2.5-seam ★ freeze).
- [ ] `evidence` is `list[EvidenceRef]` (composes the frozen 1.3c contract) — the **additive Appendix-A:217 reconciliation** (the DOMAIN_MODEL ER `ProvenancePacket 1──* Evidence`; see Step-2.5 Q1). Accepts `EvidenceRef` instances; rejects a non-`EvidenceRef` element; empty list allowed.
- [ ] `citations` is `list[str]` of `file:line` tokens (the spans the grounding gate post-validates) — **NOT** `list[Anchor]` (§10 says `file:line[]`; the gate re-resolves against live anchors). See Q2.
- [ ] `confidence` is a `float` in `[0.0, 1.0]` (required — every answer carries an overall confidence).
- [ ] `recorded_sha` is **optional** (`str | None = None`) — the recorded-Citations SHA; `index_freshness` is a required strip+min_length `str` marker (vocabulary owned by the Phase-4 freshness subsystem — Q5).
- [ ] All identity/token string fields + list elements (`project_ids`, `source_ids`, `commit_shas`, `session_ids`, `citations`, `drift_markers` elements; `recorded_sha`, `index_freshness`) use `StringConstraints(strip_whitespace=True, min_length=1)` (LESSON 7) — no empty/whitespace tokens; surrounding whitespace stripped.
- [ ] List fields are **required, no default**, but an **empty list is valid** (an ungrounded/flagged answer has `citations=[]`); **never** a mutable `= []` default (use `default_factory=list` only if Q4 flips to defaulting).
- [ ] `extra="forbid"` rejects unknown kwargs; `frozen=True` rejects mutation; an omit-each-**required**-field test pins required-ness; python + JSON round-trips equality-stable (incl. nested `EvidenceRef` + `None` `recorded_sha`).
- [ ] All unit tests in `core/tests/model/test_provenance.py` pass; `/preflight` clean (canonical visible gate; `mypy .` override).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + reconciles Appendix-A:217 hot — adding `evidence[]` to the packet portion).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 4 (§10 grounding).** ProvenancePacket is a freeze-before-fork §10 contract; the grounding gate constructs one per answer at Phase-4 (post-validating each `citations` span against live anchors, attaching `evidence`). Exported as `model.provenance`. **Intra-`model/` import:** this slice imports `from model.evidence import EvidenceRef` — a contract composing a sibling contract **within the `model/` layer**, which is NOT a §2.5 cross-subsystem import (that rule governs subsystem siblings like retrieval/federation, not intra-model composition; cf. `manifest.py` composing `ManifestArtifact`). Confirm at Step 2.5 if you read it otherwise. Not a tested-but-unwired gap.

## Files expected to touch
**New:**
- `core/model/provenance.py` — the frozen `ProvenancePacket` model.
- `core/tests/model/test_provenance.py` — snapshot + behavioral tests (incl. nested `EvidenceRef`).

**Modified:** none (Appendix-A + `core/CLAUDE.md` rows are orchestrator territory — flagged at Step 9).

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/model/test_provenance.py` (`pytestmark = pytest.mark.unit`; `from model.provenance import ProvenancePacket`; `from model.evidence import EvidenceRef`):

1. **`test_provenance_schema_snapshot`** — Asserts: `set(ProvenancePacket.model_fields) == EXPECTED_PROVENANCE_FIELDS` (10-field frozenset). Why: §2.5-seam ★ freeze (§10/Appendix-A:217).
2. **`test_provenance_valid_construction_full`** — Asserts: all 10 fields (with ≥1 `EvidenceRef`) construct + round-read. Why: §10 happy path.
3. **`test_provenance_rejects_extra_field`** — Asserts: unknown kwarg raises. Why: §4 (`extra="forbid"`).
4. **`test_provenance_required_fields`** — Asserts: omitting each required field raises; omitting `recorded_sha` does NOT. Why: LESSON 3 omit-each on the required subset.
5. **`test_provenance_empty_lists_allowed`** — Asserts: empty `project_ids`/`citations`/`commit_shas`/`session_ids`/`drift_markers`/`evidence` construct. Why: an ungrounded/flagged answer carries empty citation/evidence lists (§10 answer-but-flag).
6. **`test_provenance_rejects_empty_string_elements`** — Asserts: `""`/`"   "` raise as a list element (each string list) AND for `recorded_sha`/`index_freshness`. Why: LESSON 7.
7. **`test_provenance_strips_whitespace`** — Asserts: `" x "` → `"x"` for an element + a scalar string field. Why: `StringConstraints(strip_whitespace=True)`.
8. **`test_provenance_confidence_range`** — Asserts: `-0.1`/`1.1` raise; `0.0`/`1.0` valid. Why: `[0,1]` overall confidence.
9. **`test_provenance_recorded_sha_optional`** — Asserts: omitted/`None` ok; present kept (stripped). Why: optional recorded-Citations SHA.
10. **`test_provenance_evidence_typed`** — Asserts: `evidence` accepts `EvidenceRef` instances; a non-`EvidenceRef` (e.g. a dict missing required fields, or an int) raises; empty allowed. Why: the additive `list[EvidenceRef]` composition (Q1) — parse-don't-trust on the nested contract.
11. **`test_provenance_is_frozen`** — Asserts: post-construct mutation raises.
12. **`test_provenance_roundtrip` / `test_provenance_json_roundtrip`** — Asserts: python + JSON round-trips equality-stable, incl. nested `EvidenceRef` serialization + `None` `recorded_sha` → null. Why: persist/MCP-egress boundary with a nested model.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW model `ProvenancePacket` — §10 / Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc table — NEW `ProvenancePacket` row (10-field snapshot `spec(§10)`; composes `list[EvidenceRef]`; optional `recorded_sha`; whitespace-strip tokens; `confidence` `[0,1]`; pin `test_provenance.py`).
  - `ARCHITECTURE.md` Appendix-A:217 — **reconcile** the ProvenancePacket portion to enumerate the frozen 10 fields **including `evidence[]`** (additive — the row currently lists the flat/scalar fields but omits the evidence aggregation the ER map mandates). Orchestrator writes hot + **notes the additive reconciliation for owner awareness via the lead** (same pattern as the Chunk 16→19 / D-A7 reconciliation — orchestrator-adjudicated additive, no invariant change).
- **§2.5-seam (shared-contract) model touched?** YES — `ProvenancePacket` §10 is §2.5-crossed. RED includes the `spec(§10)` snapshot (#1).

## Things to flag at Step 2.5
1. **`evidence: list[EvidenceRef]` on the frozen packet? (load-bearing reconciliation).** Default vote: **YES** — the DOMAIN_MODEL ER map is explicit (`ProvenancePacket 1──* Evidence`) and the packet IS "the evidence record"; Appendix-A:217's summary under-lists it (lists the flat/scalar fields). Additive reconciliation, orchestrator-adjudicated (D-A7 pattern), no invariant change, lead-noted for owner. If you'd keep evidence OFF the packet (hanging off the Answer separately) → 9 fields; ping `TWEAK`. My vote embeds it (sequencing EvidenceRef before ProvenancePacket was for exactly this).
2. **`citations` = `list[str]` (file:line tokens) vs `list[Anchor]`.** Default vote: **`list[str]`** — §10 enumerates `file:line[]`; the gate post-validates each span string against live anchors at answer-time. The packet records citation *strings* + `commit_shas` (the grounding SHAs) + the rich `evidence` refs; it does NOT embed full `Anchor` objects (anchors are the chunk-level revalidation primitive). Format of a `file:line` token (`"path:line"` / `"path:start-end"`) is producer-owned (deferred, like the anchor span format).
3. **`low_confidence_links` — a separate field?** Default vote: **NO** — §10 (line 110) + Appendix-A enumerate `confidence + drift_markers` and omit it. The grounding gate's "couldn't ground: X" flagged set is carried by low-confidence `EvidenceRef`s + the gate's answer-time output (Phase-4), not a separate frozen packet field. Keeps the packet aligned to the binding §10 enumeration. (Record as a Phase-4 grounding-gate note.)
4. **List fields: required-no-default (empty allowed) vs `default_factory=list`.** Default vote: **required, no default; empty list valid** (explicit construction — the §5-model posture; an ungrounded answer passes `citations=[]` explicitly). NEVER a bare mutable `= []`. If you prefer ergonomic defaulting, `Field(default_factory=list)` is the safe form — but I vote no-default for construction-explicitness on a trust record.
5. **`index_freshness` — bare `str` marker vs enum/timestamp.** Default vote: **bare strip+min_length `str` marker**; the freshness vocabulary (e.g. `fresh|stale|drift_detected` or a timestamp) is owned by the Phase-4 drift/freshness subsystem — deferring it mirrors the anchor span-format + EvidenceType-membership deferrals (don't over-specify the frozen seam).
6. **`confidence` scalar `float` vs list of markers.** Default vote: **scalar `float [0,1]`** (the answer's overall confidence) — §10 reads "confidence + drift markers" ⇒ a scalar confidence alongside the `drift_markers` list (DATA_MODEL's plural "confidence_markers" is covered by `drift_markers` + the scalar).

## Dependencies + sequencing
- **Depends on:** 1.3c `EvidenceRef` (`518da07`, composed as `list[EvidenceRef]`); 1.3a `Anchor` (`5b50b5f`, referenced conceptually via `citations`/evidence `resource_ref`); 1.1 conventions.
- **Blocks:** §10 grounding gate (Phase 4 — constructs the packet per answer); completes Phase 1.3 (→ the before-fork whitespace retrofit slice + 1.4 ports).

## Estimated commit count
**1.** One focused ★ freeze-before-fork contract (ProvenancePacket + 10-field snapshot + the `EvidenceRef` composition). Not bundled — its own snapshot + Appendix-A reconciliation + atomic cross-doc pairing (same rationale as 1.2a–d / 1.3a / 1.3c). It is the most field-rich 1.3 model + carries the additive reconciliation, so isolation keeps bisectability + traceability.

## Lessons-logged candidates anticipated
- **Convention candidate** — possibly "frozen contracts compose sibling frozen contracts by value (`list[ChildModel]`), and parse-don't-trust extends to the nested element" (if the nested-typed-list handling surfaces a wrinkle worth banking; else none — 1.3a/1.3c conventions already cover the rest).
- **Architecture-doc note candidate** — the Appendix-A:217 ProvenancePacket reconciliation (+`evidence[]`); the `low_confidence_links` Phase-4 grounding-gate note (Q3).
- **Future TODO — belongs-to-phase** — `index_freshness` vocabulary + `file:line` token format → Phase-4 (freshness subsystem / anchor producer); the grounding gate's flagged-unsupported representation (Q3) → Phase-4 §10.

## How to invoke
1. **Read this brief end-to-end** — 6 Step-2.5 questions (Q1 evidence-embedding is load-bearing).
2. **Run `/tdd provenance_packet_contract`** (session oriented — no `/session-start`).
3. **Step 0 (Restate)** — confirm ProvenancePacket (completes 1.3).
4. **Step 1 (Identify files)** — `core/model/provenance.py` + `core/tests/model/test_provenance.py`.
5. **Step 2.5** — tight write-up (per-test `Asserts:` lines + acceptance→test coverage map); answer the 6 Qs (esp. Q1). Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9** — categorized flags + the ProvenancePacket cross-doc row ask + the Appendix-A:217 `evidence[]` reconciliation + ship-ask.
