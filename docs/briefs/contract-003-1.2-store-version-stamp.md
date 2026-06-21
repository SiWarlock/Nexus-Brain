# /tdd brief — store_version_stamp

## Feature
Freeze the **StoreVersionStamp** — the one-per-dataset store-level stamp that is the §5
source-of-truth for `{schema, model, dim}` — as a frozen Pydantic v2 model with a snapshot-pinned
field set. Second of the four atomic §5 data-contract slices (chunk ✓ → **stamp** → manifest+registry → migrations).

## Use case + traceability
- **Task ID:** 1.2
- **Architecture sections it implements:** `ARCHITECTURE.md §5` (the **source-of-truth law**: the
  store-level stamp = canonical `{schema, model, dim}`; the git-SHA **LanceDB version tag** = canonical
  SHA; manifest+registry = DERIVED). Supports §4 reproducibility invariant 1 (source + model-stamp →
  deterministically reproduce the index) and invariant 6 (one EmbeddingProvider per generation).
- **Related context:** Appendix-A **Store version stamp** row + `docs/planning/DATA_MODEL.md` line 32.
  **Source-of-truth adjudication (load-bearing):** Appendix-A lists 5 fields and states "git-SHA =
  LanceDB version tag (canonical)" — it DELIBERATELY omits the SHA from the stamp. DATA_MODEL.md's draft
  loosely added `ingested_from_sha` to the stamp; that is **superseded by the §5 law** — a stamp SHA
  field would be a SECOND home for the generation SHA and could disagree with the version tag, violating
  source-of-truth. So the stamp = **5 fields, NO SHA field**. (This also resolves 1.2a's Q3: the chunk's
  per-chunk `ingested_from_sha` is legitimate finer-grained provenance — incremental ingest can mix SHAs
  within a generation — and is NOT redundant with a stamp field, because the stamp has none.)
- Conventions inherited from 1.2a (LESSONS §1, §3): `frozen=True`, `extra="forbid"`, required fields via
  `Field(...)`, an **omit-each-field test**, and a BaseModel/ABCMeta shadow-name check.

## Acceptance criteria (what "done" means)
- [ ] `StoreVersionStamp` Pydantic v2 model in `core/model/stamp.py` with exactly the 5-field set below.
- [ ] **Schema-snapshot test** (`spec(§5)`): `set(StoreVersionStamp.model_fields) == {5 frozen fields}`.
- [ ] `model_config`: `frozen=True` + `extra="forbid"`. A stray `ingested_from_sha`/`git_sha`/`sha` kwarg
      is **REJECTED** (pins the "the SHA is NOT a stamp field; the version tag is canonical" decision).
- [ ] **No inline `now()`:** `index_built_at` is required, no `default_factory` — caller injects it via
      `Clock` (forbidden-rule 4 / LESSONS §1). It is `AwareDatetime` (tz-aware, rejects naive).
- [ ] All non-optional fields pinned required by an omit-each-field test (LESSONS §3 generic guard).
- [ ] Types: `dimension: PositiveInt`, `schema_version: PositiveInt`, `embedding_model: str`,
      `source_root_hash: str`, `index_built_at: AwareDatetime`.
- [ ] `model_dump_json()` → `model_validate_json()` round-trips; `-W error` import clean.
- [ ] Model docstring states the source-of-truth law (stamp canonical for `{schema,model,dim}`; SHA lives
      in the LanceDB version tag, set at write-time in Phase 3.1; manifest+registry are derived).
- [ ] `/preflight` clean (`uv run mypy .`).

## Wiring / entry point (Step 7.5)
none — wiring lands in Phase 3.1. The stamp is a foundational data contract with no production entry
point this slice: it is first **written** (one per dataset, `index_built_at` via injected `Clock`) by the
Phase-3.1 LanceDB writer alongside the git-SHA version tag, and **read** at startup for the §5 reconcile +
the later federation `{schema,model}` store-gate. Reachability this slice = exported from `core/model/`.

## Files expected to touch
**New:**
- `core/model/stamp.py` — the `StoreVersionStamp` model.
- `core/tests/model/test_stamp.py` — incl. the `spec(§5)` schema-snapshot test.

`core/model/__init__.py` + `core/tests/model/__init__.py` already exist (1.2a). If a stamp helper or shared
validator is needed, **flag at Step 2.5**.

## RED test outline (Step 2)
Tests in `core/tests/model/test_stamp.py` (all `spec(§5)`-tagged, `unit`):
1. **`test_stamp_schema_snapshot`** — Asserts `set(StoreVersionStamp.model_fields.keys())` == the 5-field
   frozen set. **The freeze pin.** Why: §2.5-seam — drift on a ★ contract is a cross-track Finding.
2. **`test_stamp_valid_construction`** — Asserts a fully-specified stamp validates + exposes fields.
3. **`test_stamp_rejects_sha_field`** — Asserts `StoreVersionStamp(..., ingested_from_sha="...")` raises
   `ValidationError` (`extra="forbid"`). Why: the SHA is the version tag, NOT a stamp field (§5 law).
4. **`test_stamp_is_frozen`** — Asserts field mutation raises (`frozen=True`).
5. **`test_stamp_all_required`** — Asserts omitting EACH field raises `ValidationError` (none optional).
   Why: LESSONS §3 generic shadow/required-ness guard.
6. **`test_stamp_index_built_at_tz_aware`** — Asserts a naive `index_built_at` is rejected (`AwareDatetime`).
7. **`test_stamp_positive_ints`** — Asserts `dimension<=0` and `schema_version<=0` raise. Why: a 0/neg
   embedding dim or schema version is invalid.
8. **`test_stamp_roundtrip`** — Asserts `model_validate_json(model_dump_json())` == the stamp.

## Frozen field set (the snapshot)
`embedding_model` · `dimension` · `schema_version` · `index_built_at` · `source_root_hash`  **(5 — NO SHA field; the git-SHA is the LanceDB version tag, §5-canonical)**

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW frozen `StoreVersionStamp` (★ freeze-before-fork, §5/Appendix A).
- **§2.5-seam → schema-snapshot test REQUIRED** — RED test #1.
- **Appendix-A:** the existing **Store version stamp** row already lists these 5 fields + states "git-SHA =
  LanceDB version tag (canonical)" — **no Appendix-A edit needed** (the slice implements the row as-written).
  I'll record at Step 9 that DATA_MODEL.md's draft `ingested_from_sha`-in-stamp is superseded by §5 (note
  only; DATA_MODEL is a pre-finalize draft, not re-edited).
- **Orchestrator doc rows (Step 9):** add a `core/CLAUDE.md` cross-doc row for `StoreVersionStamp` (§5) +
  lookup row.

## Things to flag at Step 2.5
1. **Stamp field set = 5, NO SHA field (load-bearing, §5 source-of-truth).** Default vote: **5 fields,
   stamp omits the SHA** — Appendix-A + the §5 law make the LanceDB version tag the canonical SHA home; a
   stamp SHA field is a second home that can disagree. This supersedes DATA_MODEL's draft 6th field. (If
   you believe the stamp genuinely needs a recorded SHA distinct from the version tag, raise it — but the
   default is the law as written.)
2. **`dimension` / `schema_version` as `PositiveInt`.** Default vote: **yes** — a 0/negative embedding
   dim or schema version is never valid; pin it at the contract.
3. **`index_built_at` = `AwareDatetime`, required, Clock-injected (no default).** Default vote: **yes** —
   identical posture to 1.2a `created_at`; never inline `now()`.
4. **Model name `StoreVersionStamp`.** Default vote: **`StoreVersionStamp`** (matches Appendix-A "Store
   version stamp"). Alt: `VersionStamp`/`StoreStamp`.
5. **`schema_version` semantics.** It is the **on-disk store schema version** the 1.2d forward-only
   migrator keys on (NOT the chunk/model version). Default vote: **`int`, starts at 1**; document it.
6. **Shadow check (LESSONS §3).** None of the 5 names shadow `BaseModel`/`ABCMeta` — but include the
   omit-each test (#5) regardless, as the generic guard.

## Dependencies + sequencing
- **Depends on:** 1.1 (`Clock` for `index_built_at`; seam discipline) + 1.2a conceptually (the stamp's
  `embedding_model`/`dimension` must stay consistent with the chunks' `embedding_model_version`/vector dim
  — a one-model-per-generation invariant the Phase-3 writer enforces, not this model).
- **Blocks:** 1.2c (manifest + registry are DERIVED projections of the stamp + version tag), Phase-3.1
  (writer stamps the dataset), the later federation router (gates each store on its own stamp).

## Estimated commit count
**1.** A single ★ freeze-before-fork contract + its snapshot test = its own commit (do NOT bundle with
manifest/registry/migrations).

## Lessons-logged candidates anticipated
- **Architecture-doc note** — confirm the stamp-omits-SHA decision as the canonical reading of §5 (the
  version tag is the sole SHA home); DATA_MODEL draft reconciliation.
- **Convention candidate** — reinforces LESSONS §1/§3 (frozen + extra-forbid + Field(...) + omit-each +
  AwareDatetime + no-inline-now); no NEW convention expected unless the build surfaces one.

## How to invoke
1. Read end-to-end — Q1 (5 fields, stamp-omits-SHA) is the load-bearing §5 decision; confirm before GREEN.
2. Reuse the session: `/tdd store_version_stamp`.
3. Step 0 → Step 1 → Step 2.5 (send the write-up + the 5-field snapshot + Q answers).
4. Step 9 — surface anything beyond the anticipated candidates.
