# /tdd brief — mcp_contract_results

## Feature
Freeze the **result half** of the §14 MCP tool contract — the grounded result shape
(`McpResultItem` = chip + file:line + ids, composing the 1.3c `EvidenceRef`; `McpResult` =
items + `ProvenancePacket` + a truncation flag) + the **`PolicyDenied` marker** (policy-denied →
marker-not-error) + the response-size bound. Completes the §14 contract started in 1.5c1.

## Use case + traceability
- **Task ID:** 1.5 (atomic sub-slice **1.5c2** — MCP results; completes 1.5; siblings 1.5a `343b6fb`, 1.5b `a9df580`, 1.5c1 `e65b9e3`)
- **Architecture sections it implements:** `ARCHITECTURE.md §14` (MCP result + policy-denied-marker), §10 (composes the frozen `ProvenancePacket` + `EvidenceRef` — the §10 grounding record on every answer), Appendix A "MCP tool contract" row. In-scope touches §4 (parse-don't-trust), §2.5 (seam).
- **Related context:**
  - 1.5c1 (`core/model/mcp_contract.py`) — this slice EXTENDS that file with the result/marker shapes.
  - Composition pattern = **LESSON 8** (`ProvenancePacket`, 1.3c): a frozen contract composing sibling frozen contracts by value uses `tuple[Child, ...]` + nested parse-don't-trust + deep immutability + dict→model coercion. Mirror `core/model/provenance.py` exactly.
  - `EvidenceRef` (`core/model/evidence.py`) is "the chip the §10 grounding layer surfaces" — the MCP result COMPOSES it (intra-`model` import — allowed; NOT a cross-sibling `ports` import).
  - §14 "policy-denied → **marker-not-error**": denial is a returned VALUE, never a raised exception (a raise would look like a tool failure, not a policy outcome).
  - This slice carries the **complete-contract** cross-doc row + Appendix-A reconciliation (deferred from 1.5c1).

## Acceptance criteria (what "done" means)
- [ ] `McpResultItem` (frozen, `extra="forbid"`) = the evidence-bearing result element: `{chip: EvidenceRef, file_line, ids: tuple[...]}` (per Q1) — composes the 1.3c `EvidenceRef`; `chip` coerces from a nested dict (parse-don't-trust); `file_line`/`ids` elements strip + min_length (LESSON 7). Field-name snapshot `spec(§14)`.
- [ ] `McpResult` (frozen, `extra="forbid"`) = the grounded response envelope: `{items: tuple[McpResultItem, ...], provenance: ProvenancePacket, truncated: bool = False}` — composes the 1.3c `ProvenancePacket`; `items` is a `tuple` (LESSON 8), empty-valid; `provenance` coerces from a nested dict. Field-name snapshot `spec(§14)`.
- [ ] `PolicyDenied` (frozen, `extra="forbid"`) = the policy-denied **marker** (a returned value, NOT an exception): `{denied: Literal[True], reason}` (per Q2). Field-name snapshot `spec(§14)`. A tool's contract return is `McpResult | PolicyDenied`.
- [ ] **Deep immutability + nested parse-don't-trust** (LESSON 8): mutating `items`/the nested `chip`/`provenance` raises; a bad nested element is rejected at parse; `model_dump`→`model_validate` (and the JSON path) round-trips with equality.
- [ ] **Response-size bound:** `MAX_RESPONSE_ITEMS` named constant (per Q4) + the `truncated` flag (default `False`); pinned by a constant test (a future loosening is test-visible — LESSON 10 spirit / §14 "bound response sizes").
- [ ] Parse-don't-trust (§4): unknown keys rejected (`extra="forbid"`) on all new models.
- [ ] `/preflight` clean (canonical, visible — LESSON 5; `uv run mypy .` — D-A3).
- [ ] **Cross-doc (this slice):** flag at Step 9 — the orchestrator writes the **complete** `mcp_contract` cross-doc row in `core/CLAUDE.md` (params from 1.5c1 + results from 1.5c2) + reconciles the Appendix-A "MCP tool contract" row (additive if the frozen field set extends the summary — D-A7 pattern).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 8** (8.1 server returns these result shapes / the `PolicyDenied` marker; 8.2 applies egress redaction to result content + the policy-deny decision + the response-size enforcement). Frozen contract like the 1.4 ports / 1.5c1 — no Phase-1 caller; the snapshot + composition tests are its Phase-1 reachability.

## Files expected to touch
**Modified:**
- `core/model/mcp_contract.py` — add `McpResultItem`, `McpResult`, `PolicyDenied`, `MAX_RESPONSE_ITEMS` (extends 1.5c1; imports `EvidenceRef` from `model/evidence`, `ProvenancePacket` from `model/provenance` — intra-`model`).
- `core/tests/model/test_mcp_contract.py` — add the result/marker tests (extends 1.5c1).

If implementation needs files beyond this list, **flag at Step 2.5** before GREEN.

## RED test outline (Step 2) — extend `core/tests/model/test_mcp_contract.py`
1. **`test_mcp_result_item_composes_evidence_ref`** — `McpResultItem` field-name snapshot; `chip` is an `EvidenceRef` that coerces from a nested dict; `file_line`/`ids` strip + reject empty. Tag `spec(§14)`. Why: §14 chip+file:line+ids; LESSON 8 nested coercion.
2. **`test_mcp_result_envelope`** — `McpResult` field-name snapshot; `items` is a `tuple` (empty-valid); `provenance` coerces from a nested `ProvenancePacket` dict; `truncated` default `False`. Tag `spec(§14)`. Why: §14 result(...provenance); §10 composition; LESSON 8.
3. **`test_policy_denied_marker`** — `PolicyDenied` field-name snapshot; `denied` is `True`; it's an ordinary frozen value (constructible, not raised). Tag `spec(§14)`. Why: §14 marker-not-error.
4. **`test_result_deep_immutable`** — mutating `McpResult.items` / a nested `chip` field / `provenance` raises; a bad nested element (e.g. an `EvidenceRef` with an extra key) is rejected at parse. Why: LESSON 8 deep-frozen + nested parse-don't-trust.
5. **`test_result_json_roundtrip`** — `McpResult` (items + provenance) `model_dump`/`model_validate` + the JSON path round-trip with equality. Why: LESSON 8 round-trip.
6. **`test_response_bound_constant`** — `MAX_RESPONSE_ITEMS` exists + equals the documented value; `truncated` defaults `False`. Why: §14 bound response sizes (visible-loosening).
7. **`test_result_models_frozen_extra_forbid`** — all 3 new models frozen + unknown key rejected. Why: parse-don't-trust §4.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW (completing) — `McpResultItem` + `McpResult` + `PolicyDenied` + `MAX_RESPONSE_ITEMS` (§14, composing §10 `EvidenceRef`/`ProvenancePacket`).
- **Orchestrator doc rows to write hot (this slice):** the **complete** `mcp_contract` cross-doc row in `core/CLAUDE.md` (RetrievalScope + 5 param models from 1.5c1 + the result/marker shapes from 1.5c2); the Appendix-A "MCP tool contract" reconciliation (additive — D-A7 pattern; covers the result envelope + policy-denied marker + ingress allow-list if they extend the summary).
- **§2.5-seam (shared-contract) model touched?** **YES** — completes the ★ MCP trust-boundary contract. RED **includes** the `spec(§14)` field-name snapshots for the 3 new models, authored this cycle.

> **Orchestrator territory** (canonical list: `core/CLAUDE.md` "must NOT touch"): flag at Step 9; orchestrator writes hot + commits at `/orchestrate-end`.

## Things to flag at Step 2.5
1. **Result-item composition — compose `EvidenceRef`, or a flat chip model?** My default vote: **compose the 1.3c `EvidenceRef`** as `chip` + add `file_line` + `ids` at the item level. Reuses the frozen §10 chip (intra-`model` import, allowed), avoids a parallel chip definition that could drift from `EvidenceRef`. (If the `EvidenceRef.resource_ref` vs item `ids` overlap feels redundant, we can fold ids into the chip — say so; my lean is keep the chip pure and carry result-level `ids`/`file_line` alongside.)
2. **`PolicyDenied` representation — distinct marker in a `McpResult | PolicyDenied` union, or a `denied` field on the envelope?** My default vote: **a distinct frozen `PolicyDenied` marker**, tool return typed `McpResult | PolicyDenied`. "Marker-not-error" means it's a normal return value; a separate type makes the deny path unmistakable + keeps `McpResult` clean. (`denied: Literal[True]` so it can't masquerade as a non-deny.)
3. **Streaming — freeze a streaming type now, or defer to Phase 8 transport?** My default vote: **defer the streaming ENVELOPE to Phase 8** (it's a transport/server concern); the frozen contract's per-item shape (`McpResultItem`) IS the stream granularity (the server streams items). Document the deferral in-code. Freezing a streaming-chunk type now would pre-commit a transport detail Phase 8 owns.
4. **Response bound — items-count vs bytes?** My default vote: **`MAX_RESPONSE_ITEMS` (items count) + the `truncated` flag** on `McpResult`; a bytes-level cap is a Phase-8 transport detail (additive). The contract pins "bounded + signals truncation."
5. **Per-tool result specializations (get_file content / list_projects list / status detail) — freeze now or defer?** My default vote: **freeze the §14-specified grounded result (`McpResult` = chip+file:line+ids+provenance) + `PolicyDenied` + the bound now; defer the per-tool result specializations to Phase 8 (additive).** §14's "result(...)" specifies the grounded (search/graph) shape; get_file (redacted content), list_projects (project list), status (ops data) are simpler, not the chip+provenance result, and are Phase-8-shaped. **This is a conscious partial-freeze — flag if you/the lead think get_file's result should be frozen now.**

## Dependencies + sequencing
- **Depends on:** 1.5c1 (`e65b9e3`, same file) · 1.3c `ProvenancePacket` + `EvidenceRef` (`77276e3`/`518da07`, composed). Intra-`model` imports only (no `ports`).
- **Blocks:** Phase 8.1/8.2 (server returns these shapes + enforces the bound/redaction/policy-deny) · Phase 11 UI (renders chips + file:line + provenance).

## Estimated commit count
**1.** Completes the §14 contract (composes the §10 grounding contracts + the policy-denied marker). Own commit (contract completion; the policy-denied egress marker is trust-boundary-relevant).

## Lessons-logged candidates anticipated
- **Architecture-doc note candidate** — the Appendix-A "MCP tool contract" reconciliation (additive — result envelope + policy-denied marker + ASCII ingress allow-list) at this slice's close.
- **Future TODO — phase 8:** per-tool result specializations (get_file redacted-content result, list_projects, status); the streaming envelope (transport); bytes-level response bound; egress redaction applied to result content + the policy-deny decision (8.2).
- **Convention candidate (maybe):** "policy-denied is a typed returned marker (`Result | Denied`), never a raised exception — a denial is an outcome, not a failure" (if not already implied by LESSON 11/the existing patterns).

## How to invoke
1. Read this brief end-to-end — esp. Step-2.5 Q2 (PolicyDenied shape), Q3 (streaming deferral), Q5 (partial-freeze of per-tool results).
2. Run **`/tdd mcp_contract_results`**.
3. **Step 0/1** — confirm restate + file list (this EXTENDS the 1.5c1 file).
4. **Step 2.5** — send the test-design write-up + answer the 5 Qs; wait for `APPROVED.` before GREEN.
5. **Step 9** — flag the **complete** cross-doc row + Appendix-A reconciliation (this slice writes them) + anything beyond the anticipated candidates.
