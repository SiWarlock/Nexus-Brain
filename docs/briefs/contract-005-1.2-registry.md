# /tdd brief — global_registry

## Feature
Freeze the **global Registry** (`~/.project-brain/registry`) — the cross-project routing index the
federation router reads — and its **RegistryEntry** row, as frozen Pydantic v2 models with snapshot-pinned
field sets. A **DERIVED projection** (rebuildable by scanning manifests, §5). Fourth and last of the
data-model §5 slices' core models (chunk ✓ → stamp ✓ → manifest ✓ → **registry** → migrations is 1.2d).

## Use case + traceability
- **Task ID:** 1.2
- **Architecture sections it implements:** `ARCHITECTURE.md §5` — the registry is a **DERIVED routing index**
  (`project_id → {entry}`), rebuildable by scanning per-project manifests; gated per-store on its own
  `{schema, model}` stamp. Supports §4 invariant 5 (read-only federation reads the registry).
- **Related context:** `docs/planning/DATA_MODEL.md` line 45 + Appendix-A "Manifest + Registry" row.
  **Reconciliation:** Appendix-A entry = `{db_path, schema_version, model_version, codegraph_db_path,
  last_indexed_sha}` (5); DATA_MODEL adds `policy` (6). I adjudicate the **6-field union** for RegistryEntry.
  Unlike the manifest, all registry keys are **snake_case** (no camelCase) — so no aliasing complexity, but
  LESSON §4 (two-snapshot pattern) still applies trivially (by-alias keys == field names).
- Conventions: LESSONS §1/§3/§4; `frozen=True`, `extra="forbid"`, `Field(...)`, omit-each, shadow check,
  `min_length=1` on identity strings (the uniform whitespace-strip sweep is a separate before-fork Carry-forward).

## Acceptance criteria (what "done" means)
- [ ] `RegistryEntry` + `Registry` Pydantic v2 models in `core/model/registry.py`, `frozen=True` + `extra="forbid"`.
- [ ] **Schema-snapshot tests** (`spec(§5)`): RegistryEntry field set (6) + the Registry wrapper field set, each
      == a checked-in frozen set.
- [ ] `Registry` holds the `project_id → RegistryEntry` map + its own `schema_version` (the **registry-file**
      format version the 1.2d migrator keys on — DISTINCT from `RegistryEntry.schema_version`, which is the
      per-project STORE schema version mirrored from that project's stamp/manifest).
- [ ] Model docstrings state: the registry is a DERIVED projection (rebuildable by scanning manifests), NOT
      canonical; it is a routing index (read-only to federation).
- [ ] `min_length=1` on identity strings (`db_path`, `codegraph_db_path`, `last_indexed_sha`, `model_version`,
      and the project_id keys); `schema_version`(s) PositiveInt; no inline `now()`/`uuid4`.
- [ ] An empty registry (`{}` / zero entries) is valid (a fresh machine has no projects).
- [ ] `/preflight` clean (`uv run mypy .`); `-W error` import clean.
- [ ] Cross-doc: orchestrator reconciles the Appendix-A registry row to the 6-field entry (Step-9).

## Wiring / entry point (Step 7.5)
none — wiring lands in Phase 2/3 + federation. The registry is a derived projection with no production entry
point this slice: first **built/reconciled** at startup (scan manifests) by the Phase-3 host; read by the
later federation router to fan out. Exported from `core/model/`.

## Files expected to touch
**New:**
- `core/model/registry.py` — `RegistryEntry` + `Registry`.
- `core/tests/model/test_registry.py` — incl. the `spec(§5)` snapshots.

## RED test outline (Step 2)
Tests in `core/tests/model/test_registry.py` (all `spec(§5)`-tagged, `unit`):
1. **`test_registry_entry_schema_snapshot`** — `set(RegistryEntry.model_fields)` == the 6-field frozen set. Freeze pin.
2. **`test_registry_schema_snapshot`** — `set(Registry.model_fields)` == the Registry wrapper field set. Freeze pin.
3. **`test_registry_entry_valid_construction`** + **`test_registry_valid_construction`** (with ≥1 entry in the map).
4. **`test_registry_entry_rejects_extra`** + **`test_registry_rejects_extra`** — `extra="forbid"`.
5. **`test_registry_entry_is_frozen`** + **`test_registry_is_frozen`** — `frozen=True`.
6. **`test_registry_entry_all_required`** + **`test_registry_all_required`** — omit-each-field (LESSONS §3).
7. **`test_registry_accepts_empty`** — a `Registry` with zero entries validates (fresh machine).
8. **`test_registry_entry_identity_min_length`** — empty `db_path`/`codegraph_db_path`/`last_indexed_sha`/`model_version` rejected.
9. **`test_registry_roundtrip`** — `model_validate_json(model_dump_json())` == the registry (on-disk round-trip).
10. **`test_registry_two_schema_versions_distinct`** — assert `Registry.schema_version` and `RegistryEntry.schema_version`
    are independent fields (a registry-format bump ≠ a per-project store-schema bump). Why: the brief's load-bearing distinction.

## Frozen field sets (the snapshots)
**RegistryEntry (6):** `db_path` · `schema_version` · `model_version` · `codegraph_db_path` · `last_indexed_sha` · `policy`
**Registry:** `schema_version` · `entries`  *(`entries: dict[str, RegistryEntry]`; see Q1)*

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW frozen `RegistryEntry` + `Registry` (★ freeze-before-fork, §5/Appendix A).
- **§2.5-seam → schema-snapshot tests REQUIRED** (RED #1, #2).
- **Orchestrator rows (Step 9):** reconcile Appendix-A registry entry 5→6 fields (integration); add `core/CLAUDE.md`
  RegistryEntry + Registry cross-doc rows + lookup.

## Things to flag at Step 2.5
1. **`Registry` shape — wrapper `{schema_version, entries: dict}` vs a `RootModel(dict[str, RegistryEntry])`.**
   Default vote: **wrapper `{schema_version, entries}`** — the on-disk registry file needs its own format
   `schema_version` for the 1.2d migrator (backup-before-migrate, downgrade-refuse), which a bare RootModel
   can't carry. Confirm.
2. **The two `schema_version`s (load-bearing — don't conflate).** `Registry.schema_version` = registry-FILE
   format version; `RegistryEntry.schema_version` = per-project STORE schema (mirrors that project's
   stamp/manifest). Default vote: **two distinct fields**, documented; test #10 pins it.
3. **`policy` field type.** DATA_MODEL has a bare `policy` on the entry. Default vote: **`str` (a policy ref /
   path / privacy level marker)** for now — the real `policy.yaml` model is 1.5; keep the registry a routing
   index that *references* policy, doesn't embed it. Flag if it should be a structured enum (`local|cloud`).
4. **`model_version` vs the stamp's `embedding_model`.** The registry entry's `model_version` is the routing
   gate's model identity (mirrors the stamp). Default vote: **`str`, min_length=1**, consistent with the stamp.
5. **Empty registry = `{}`.** Default vote: **allowed** (fresh machine, zero projects) — no `min_length` on `entries`.
6. **Shadow check (LESSONS §3):** none of the field names obviously shadow; include omit-each; verify no UserWarning.

## Dependencies + sequencing
- **Depends on:** 1.2c1 (the registry is built by scanning manifests — derived consistency), 1.2b/1.2a
  conceptually. No runtime import of 1.1.
- **Blocks:** 1.2d (migrations — the registry-file `schema_version` is one of the migrator's targets), Phase-3
  startup reconcile, the later federation router (reads the registry to fan out).

## Estimated commit count
**1.** Two co-designed models (registry + its entry) frozen together = one logical unit, one commit.
(This completes the §5 data models; 1.2d migrations is the next slice.)

## Lessons-logged candidates anticipated
- **Architecture-doc note** — Appendix-A registry entry 5→6 reconcile (`+policy`); the two-schema_version distinction.
- **Convention** — reinforces LESSONS §1/§3/§4; no NEW lesson expected.

## How to invoke
1. Read end-to-end — Q1 (wrapper vs RootModel) + Q2 (the two schema_versions) are the load-bearing calls.
2. Reuse the session: `/tdd global_registry`. Use **`validate_by_name`/`validate_by_alias`** if any alias is
   needed (none expected — all-snake), NOT the deprecated `populate_by_name`.
3. Step 0 → Step 1 → Step 2.5 (write-up + both snapshots + Q answers).
4. Step 9 — surface anything beyond the anticipated candidates.
