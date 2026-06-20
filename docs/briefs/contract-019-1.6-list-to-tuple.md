# /tdd brief — frozen_collection_list_to_tuple

## Feature
Convert frozen-contract collection fields from `list[...]` to `tuple[...]` (LESSON 8 deep
immutability) — primarily `ProvenancePacket`'s 7 collections (so a composed
`McpResult.provenance.evidence` can no longer be `.append`-mutated), plus an audit of the other
frozen contracts (`GenerateResult.citations`, `manifest.artifacts`). `chunk.vector` is deferred to
Phase 3.1 (LanceDB binding).

## Use case + traceability
- **Task ID:** 1.6 (atomic sub-slice **1.6b** — list→tuple; sibling of 1.6a [`0520304`, landed] + 1.6c StrictBool)
- **Architecture sections it implements:** `ARCHITECTURE.md §10` (`ProvenancePacket` — the grounding record), §5 (`Chunk`/`ProjectManifest`), §7 (`GenerateResult`). Applies **LESSON 8** (frozen-contract collections are `tuple`).
- **Related context:**
  - Carry-forward (c) + the **1.5c2 code-quality catch**: `ProvenancePacket.evidence` (and the other 6 collections) are still `list[...]`, so `frozen=True` does NOT deep-freeze them — a composed `McpResult.provenance.evidence.append(...)` succeeds today. 1.5c2's own `McpResult.items`/`McpResultItem.ids` already use `tuple`; this closes the composed gap end-to-end.
  - LESSON 8 (`core/LESSONS.md#8`) — pinned by `test_provenance.py` already for the nested/deep-frozen behavior; this slice flips the container type.
  - Field NAMES unchanged → all `spec(§5)`/`spec(§10)`/`spec(§7)` field-name snapshots stay green; JSON serialization of a tuple == a list (JSON array) so on-disk-key/JSON-shape snapshots stay green. The break surface is in-test list-literal comparisons (update to tuple).

## Acceptance criteria (what "done" means)
- [ ] `ProvenancePacket`'s 7 collection fields — `project_ids`, `source_ids`, `citations`, `commit_shas`, `session_ids`, `drift_markers`, **`evidence`** — are `tuple[...]` (`evidence: tuple[EvidenceRef, ...]`); a list input coerces to tuple; each is empty-valid (no mutable default).
- [ ] **Deep immutability proven:** `.append()` on any of the 7 (and on a composed `McpResult.provenance.evidence`) raises `AttributeError` — the end-to-end closure of the 1.5c2 catch.
- [ ] Audit + convert the other frozen-contract list collections: `GenerateResult.citations` (ports/providers) + `ProjectManifest.artifacts` (model/manifest) → `tuple[...]` if currently `list` (per Q2). Note any others found.
- [ ] `chunk.vector` is **deferred to Phase 3.1** (LanceDB `Vector(dim)`/`LanceModel` owns its representation) — left `list[float]` with an in-code note + a carry-forward (per Q1). `registry.entries` (a `dict`) is out of scope (dict immutability is a separate concern — note, don't change).
- [ ] All existing 222 tests stay green (snapshots unchanged; in-test list-literal comparisons updated to tuple where they now compare a tuple field).
- [ ] `/preflight` clean (canonical, visible — LESSON 5; `uv run mypy .` — D-A3).
- [ ] Cross-doc: flag at Step 9 — no field add/remove/rename (container-type change only); the `core/CLAUDE.md` cross-doc notes already say "tuple (LESSON 8)" for the 1.4/1.5 fields; I'll confirm the provenance/manifest/providers notes at /orchestrate-end.

## Wiring / entry point (Step 7.5)
**none — internal immutability hardening of frozen contracts.** No new entry point; tightens existing models Phase 2+/4 consumes. Reachability = the existing + new immutability tests.

## Files expected to touch
**Modified:**
- `core/model/provenance.py` — 7 collections `list`→`tuple`.
- `core/ports/providers.py` — `GenerateResult.citations` → `tuple` (if list; Q2).
- `core/model/manifest.py` — `ProjectManifest.artifacts` → `tuple` (if list; Q2).
- `core/tests/model/test_provenance.py`, `test_manifest.py`, `core/tests/ports/test_providers.py` — add tuple-type + deep-immutability assertions; update any list-literal comparisons.

If the audit finds another frozen-contract list collection, **flag at Step 2.5**.

## RED test outline (Step 2)
1. **`test_provenance_collections_are_tuples`** (`test_provenance.py`) — each of the 7 fields is a `tuple`; a `list` input coerces to `tuple`; empty-valid. Why: LESSON 8 container type.
2. **`test_provenance_deep_immutable`** — `.append()` on each of the 7 raises (already partially covered for the nested element — extend to the container). Why: LESSON 8 deep immutability.
3. **`test_composed_mcpresult_provenance_immutable`** (`test_mcp_contract.py` or `test_provenance.py`) — a constructed `McpResult` with a `provenance` whose `evidence` cannot be `.append`-ed (the end-to-end 1.5c2-catch closure). Why: the composed gap.
4. **`test_generate_result_citations_tuple`** (`test_providers.py`) — `citations` is `tuple`; immutable. Why: LESSON 8 (Q2 — confirm/convert).
5. **`test_manifest_artifacts_tuple`** (`test_manifest.py`) — `artifacts` is `tuple`; immutable; list input coerces. Why: LESSON 8 (Q2).
6. **(implicit) full suite green** — 222 + new; snapshots unchanged; updated list-comparisons.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** **none** — container-type change only (no field add/remove/rename); all field-name + on-disk-key + JSON-shape snapshots stay green.
- **Orchestrator doc rows to write hot:** confirm the `core/CLAUDE.md` cross-doc notes for `ProvenancePacket`/`ProjectManifest`/`GenerateResult` say "tuple (LESSON 8)" (refine at /orchestrate-end if they still say "list").
- **§2.5-seam:** the frozen contracts are touched but **shape-unchanged** — the existing snapshots staying green IS the regression guard; no new snapshot needed.

> **Orchestrator territory** (`core/CLAUDE.md` "must NOT touch"): flag at Step 9.

## Things to flag at Step 2.5
1. **`chunk.vector` — convert now or defer to Phase 3.1?** My default vote: **defer to Phase 3.1.** LanceDB's `Vector(dim)`/`LanceModel` binding (Phase 3.1) owns the vector's on-disk + Python representation; forcing `tuple` now risks the binding + a 3.1 re-touch, and the mutation hazard on a write-once numeric vector is low. Leave `list[float]` + an in-code note; carry-forward "3.1 makes vector immutable per LESSON 8 when the Vector binding lands." (Convert now only if you've confirmed `LanceModel` accepts a tuple.)
2. **`GenerateResult.citations` + `manifest.artifacts` — in scope?** My default vote: **yes, convert if currently `list`** (LESSON 8 consistency — they're frozen-contract collections). Confirm their current types at Step 1; if already `tuple`, just assert it. Audit for any other frozen-contract `list` field while you're in there.
3. **`registry.entries` (a `dict`) — out of scope?** My default vote: **yes, out of scope** — dict immutability is a separate concern (no clean frozen-dict; LESSON 8 is list→tuple specifically). Note it in-code as a known residual, don't change it here.

## Dependencies + sequencing
- **Depends on:** 1.3b `ProvenancePacket` (`77276e3`), 1.4 `GenerateResult`, 1.2 `ProjectManifest` — all landed. Rebases cleanly on 1.6a (`0520304`) which touched provenance.py's str alias (different lines).
- **Blocks:** nothing forks until /phase-exit 1; 1.6c (StrictBool) is an independent sibling. A mutable collection in a frozen cross-track contract post-fork = a LESSON-8 Finding → land before /phase-exit 1.

## Estimated commit count
**1.** A focused container-type hardening (LESSON 8). Not a safety pin; keep it its own commit (distinct concern from 1.6a/1.6c).

## Lessons-logged candidates anticipated
- **Future TODO — Phase 3.1:** make `chunk.vector` immutable (tuple or the LanceModel-native immutable form) when the `Vector(dim)` binding lands (deferred from 1.6b).
- **Future TODO** — `registry.entries` dict-immutability residual (no clean frozen-dict; revisit if it becomes a mutation hazard).
- (No new convention expected — this applies LESSON 8.)

## How to invoke
1. Read this brief end-to-end — esp. Q1 (`chunk.vector` defer) + Q2 (audit scope).
2. Run **`/tdd frozen_collection_list_to_tuple`**.
3. **Step 0/1** — confirm restate + the audited file list (flag any other frozen-contract `list` you find).
4. **Step 2.5** — send the test-design write-up + answer the 3 Qs; wait for `APPROVED.` before GREEN.
5. **Step 9** — confirm snapshots stayed green + flag the chunk.vector/registry.entries carry-forwards.
