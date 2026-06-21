# /tdd brief — chunk_schema

## Feature
Freeze the **Chunk** model — the per-project LanceDB row contract (the semantic+lexical
memory unit) — as a Pydantic v2 model with a frozen, snapshot-pinned field set. First of the
four atomic §5 data-contract slices (chunk · stamp · manifest+registry · migrations); each is a
★ freeze-before-fork contract with its own `spec(§5)` schema-snapshot test, so they ship as
separate commits, not one bundle.

## Use case + traceability
- **Task ID:** 1.2
- **Architecture sections it implements:** `ARCHITECTURE.md §5` (data & state model — the Chunk
  record + source-of-truth law); supports the §4 reproducibility invariants (the index is a derived
  cache: `content_hash` + `last_resolved_sha` make a chunk reproducible/revalidatable) and the §10
  trust spine (the `anchor` span). Appendix-A **Chunk** row is the frozen inventory entry.
- **Related context:** authoritative field detail in `docs/planning/DATA_MODEL.md` §① (LanceDB chunk).
  **Cross-doc discrepancy resolved in this brief:** Appendix-A and DATA_MODEL.md disagree on the field
  set — DATA_MODEL adds `ingested_from_sha`/`context_blurb`/`created_at`; Appendix-A adds
  `generation`/`tombstone`. I adjudicate the **union** as canonical (all are real + needed); the
  snapshot test pins the union, and I reconcile the Appendix-A row to match at Step-9 (orchestrator
  territory → integration checkout). FTS/BM25 is a **native LanceDB index on `text`**, NOT a stored
  model field — it is deliberately absent from the field set.

## Acceptance criteria (what "done" means)
- [ ] `Chunk` Pydantic v2 model in `core/model/chunk.py` with exactly the frozen field set (below).
- [ ] **Schema-snapshot test** (`spec(§5)`): `set(Chunk.model_fields) == <checked-in frozen set>` — the
      §2.5-seam freeze pin; any field add/remove/rename fails it (forcing the atomic Appendix-A edit).
- [ ] `model_config` is strict: `extra="forbid"` (parse-don't-trust — unknown fields raise) and
      `frozen=True` (a persisted row is immutable).
- [ ] **No inline `now()`/`uuid4` in the model:** `chunk_id` + `created_at` are **required, no
      `default_factory`** — the constructing caller (Phase-2 ingest) injects them via `IdGen`/`Clock`
      (upholds forbidden-pattern rule 4 / LESSONS §1). A missing required field raises `ValidationError`.
- [ ] Field types pinned: closed sets (`doc_or_code`, `ownership`, `register`) are `Literal`/`Enum`;
      `vector: list[float]` (dimension is stamped at store level, not pinned in the row type);
      `created_at` is a tz-aware `datetime`; `context_blurb: str | None` (code-chunk-only, optional).
- [ ] `model_dump()` → `model_validate()` round-trips (serialization stability for the row).
- [ ] All unit tests in `core/tests/model/test_chunk.py` pass; `/preflight` clean (`uv run mypy .`).
- [ ] Cross-doc: orchestrator reconciles the Appendix-A **Chunk** row to the union set (Step-9).

## Wiring / entry point (Step 7.5)
none — wiring lands in Phase 3.1. `Chunk` is a foundational data contract with no production entry
point this slice: it is first **constructed** in Phase-2 ingest (via injected `IdGen`/`Clock`) and
first **persisted** by the Phase-3.1 LanceDB writer. Reachability this slice = exported from
`core/model/`; consumed starting Phase 2. (Explicit deferral so `spec-lint brief` + Step 7.5 see it.)

## Files expected to touch
**New:**
- `core/model/__init__.py`
- `core/model/chunk.py` — the `Chunk` model (+ any `Literal`/`Enum` for the closed-set fields).
- `core/tests/model/__init__.py`
- `core/tests/model/test_chunk.py` — incl. the `spec(§5)` schema-snapshot test.

If a separate snapshot fixture file is preferred over an inline frozen set, **flag at Step 2.5**.

## RED test outline (Step 2)
Tests in `core/tests/model/test_chunk.py` (all `spec(§5)`-tagged, `unit`):
1. **`test_chunk_schema_snapshot`** — Asserts `set(Chunk.model_fields.keys())` equals the checked-in
   frozen set (the 19 fields below). **The freeze pin.** Why: §2.5-seam — a silent field drift on a
   frozen ★ contract is a cross-track Finding; this catches it at type-check/test time.
2. **`test_chunk_valid_construction`** — Asserts a fully-specified `Chunk(...)` validates + exposes
   each field. Why: the happy-path contract shape.
3. **`test_chunk_rejects_extra_field`** — Asserts an unknown kwarg raises `ValidationError`
   (`extra="forbid"`). Why: §4 parse-don't-trust at the contract boundary.
4. **`test_chunk_is_frozen`** — Asserts mutating a field on an instance raises (`frozen=True`).
   Why: a persisted row is immutable; mutation = a new generation, not an in-place edit (§5).
5. **`test_chunk_requires_chunk_id_and_created_at`** — Asserts omitting `chunk_id` or `created_at`
   raises `ValidationError` (no `default_factory`). Why: forbidden-rule 4 — ids/timestamps come from
   injected `IdGen`/`Clock`, never minted inline in the model.
6. **`test_chunk_created_at_must_be_tz_aware`** — Asserts a naive `created_at` is rejected. Why:
   tz-safe serialization (mirrors the `Clock.now()` contract from 1.1).
7. **`test_chunk_closed_set_fields_reject_unknown`** — Asserts an out-of-enum `doc_or_code` /
   `ownership` / `register` raises. Why: closed-set integrity.
8. **`test_chunk_roundtrip`** — Asserts `Chunk.model_validate(c.model_dump())` == `c`. Why:
   serialization stability for the LanceDB row.

## Frozen field set (the snapshot — my adjudicated union; confirm at Step 2.5)
`chunk_id` · `project_id` · `source_path` · `doc_or_code` · `producer` · `doc_type` · `ownership` ·
`register` · `text` · `vector` · `anchor` · `content_hash` · `last_resolved_sha` · `ingested_from_sha` ·
`embedding_model_version` · `context_blurb` · `generation` · `tombstone` · `created_at`  **(19)**

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW frozen `Chunk` contract (★ freeze-before-fork, §5/Appendix A).
- **§2.5-seam → schema-snapshot test REQUIRED** — included as RED test #1 above.
- **Orchestrator doc rows to write hot (Step-9):** (a) reconcile the **Appendix-A `Chunk` row** to the
  union field set (routes to the integration checkout, root/main, per the multi-track carve-out); (b)
  add a `core/CLAUDE.md` cross-doc-invariants row for `Chunk` (§5) + a lookup-table row. (c) `DATA_MODEL.md`
  is a pre-finalize planning draft (not the binding contract) — note the reconciliation, don't re-edit it.

## Things to flag at Step 2.5
1. **Field-set union — confirm.** My adjudicated 19-field union reconciles Appendix-A + DATA_MODEL.md.
   Default vote: **accept the union** (every field is real + needed; freezing the superset avoids a
   post-fork field-add Finding). Open sub-question → #2.
2. **`anchor` field type.** Raw span `str` (`file:line[-line]`) vs a typed `AnchorSpan` vs the full 1.3
   `Anchor`. Default vote: **`str` span** — decouples 1.2a from 1.3 (parallel slices); the 1.3 `Anchor`
   is the revalidation primitive that *references* a chunk's span, not embedded in the row.
3. **`ingested_from_sha` per-chunk?** It also lives on the store stamp/manifest (per-dataset, 1.2b/c).
   Default vote: **keep it per-chunk** (DATA_MODEL has it; supports per-chunk provenance + partial-gen
   ingest) — but confirm it isn't purely redundant with the stamp.
4. **Enums vs `str` for the semi-open sets.** `doc_or_code`/`ownership`/`register` are closed →
   `Literal`/`Enum`. `producer`/`doc_type` are open-ended (the ingest classifier may grow them). Default
   vote: **`Literal`/`Enum` for the 3 closed sets; `str` for `producer`/`doc_type`** (with a docstring
   noting the known values), so the classifier can extend without a contract bump.
5. **Pydantic `BaseModel` vs `lancedb.pydantic.LanceModel`.** Default vote: **plain `BaseModel`** —
   keep the Phase-1 contract decoupled from LanceDB (the §2.5 DAG: `model` is a leaf; the LanceDB schema
   is derived in Phase 3.1). `vector: list[float]` now; the LanceDB `Vector(dim)` binding lands in 3.1.
6. **Snapshot form — inline frozen set vs fixture file.** Default vote: **inline `frozenset` constant in
   the test** (the test *is* the checked-in snapshot; simplest, one source of truth).

## Dependencies + sequencing
- **Depends on:** 1.1 — *seam discipline only* (no runtime import): `chunk_id`/`created_at` are
  caller-injected via `IdGen`/`Clock`, never `default_factory`'d. The model itself is pure Pydantic.
- **Blocks:** 1.2b (store version stamp — pins `{model, dim}` consistent with `vector`/`embedding_model_version`),
  Phase-2 ingest (constructs `Chunk`), Phase-3.1 (LanceDB writer persists it), retrieval/grounding (read it).
- **Sequencing note:** 1.2b/c/d (stamp · manifest+registry · migrations) follow as separate atomic briefs.
  1.3 (`Anchor`) is parallel; this slice stays decoupled from it via the `str`-span default (Q2).

## Estimated commit count
**1.** A single ★ freeze-before-fork contract + its snapshot test = its own commit (do NOT bundle with
the stamp/manifest/migrations — each is a separate cross-doc invariant wanting atomic doc-edit traceability).

## Lessons-logged candidates anticipated
- **Convention candidate** — "Contract models are `frozen=True`, `extra='forbid'`; ids/timestamps are
  required (no `default_factory`) and caller-injected via the seams." (Reinforces LESSONS §1 / rule 4;
  every 1.2–1.3 model mirrors it.)
- **Architecture-doc note** — the Appendix-A Chunk-row reconciliation (union set; FTS is a native index,
  not a field).
- **Future TODO — operational** — the LanceDB `Vector(dim)` / `LanceModel` binding + FTS index config
  land in Phase 3.1 (derived from this frozen model).

## How to invoke
1. Read this brief end-to-end — esp. the six Step-2.5 questions (Q1 field-union + Q2 anchor-type are load-bearing).
2. Reuse the session (already oriented): jump to `/tdd chunk_schema`.
3. Step 0 (Restate) → Step 1 (files) → Step 2.5 (send the test-design write-up + the snapshot field set + Q answers).
4. Step 9 — surface anything beyond the anticipated candidates.
