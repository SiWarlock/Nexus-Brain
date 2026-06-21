# /tdd brief — schema_migrations

## Feature
Freeze the **on-disk schema migration engine** — a **pure, deterministic** forward-only
`schemaVersion` runner with **downgrade-refuse** + missing-migration detection — for the serialized
§5 files (manifest, registry). Completes Task 1.2 (the four §5 models ✓ + this migration framework).

## Use case + traceability
- **Task ID:** 1.2
- **Architecture sections it implements:** `ARCHITECTURE.md §5` — "Manifest/registry schema is FROZEN
  (closes OQ-6) with a forward-only `schemaVersion` migrator + backup-before-migrate + downgrade-refuse
  (D-26/C-12)." Supports §4 invariant 1 (the index is a reproducible cache; on-disk schema evolves
  forward-only, never silently downgraded).
- **Related context:** the serialized files (`ProjectManifest` `schemaVersion`, `Registry`
  `schema_version` — both frozen in 1.2c1/1.2c2) carry a format version the loader migrates.
  **Scope boundary (load-bearing):** at the contract-freeze stage this is the **PURE engine** (data→data
  transform + version-check). The actual **file read/write + backup-before-migrate is HOST-owned** (via
  `HostPort.perform`, Phase 2+) — raw FS access would violate the §4/§7 single-mutation-chokepoint, and
  `HostPort` isn't built until 1.4. So the engine does **no I/O**; it exposes what the host needs to
  back-up-then-write. There are **no real migrations yet** (current = v1) — this freezes the FRAMEWORK +
  the downgrade-refuse safety rule, tested with synthetic migration chains.
- Conventions: LESSONS §1/§3/§5 (typed, Field(...), no inline I/O; run the canonical `/preflight`).

## Acceptance criteria (what "done" means)
- [ ] A pure migration engine in `core/model/migrations.py`: `migrate(data, from_version, *, chain, current_version) -> dict`
      applies the registered forward chain `vN → vN+1 → … → current_version`.
- [ ] **Downgrade-refuse:** `from_version > current_version` raises `DowngradeRefused` (never load/transform a
      file newer than the code supports — forward-only).
- [ ] **Identity at current:** `from_version == current_version` returns the data unchanged (no-op).
- [ ] **Missing-migration detection:** a gap in the chain (`vN → vN+1` not registered) raises `MissingMigration`
      — never silently skip a version.
- [ ] `CURRENT_MANIFEST_SCHEMA_VERSION` / `CURRENT_REGISTRY_SCHEMA_VERSION` baselines = **1** (no migrations
      registered yet); the engine is generic (parametrized by current_version + chain), used for both files.
- [ ] The engine does **NO file I/O** (pure data→data); the **backup-before-migrate + write protocol is
      documented as host-owned** (Phase 2+ via `HostPort`: back up the original → write the migrated result).
- [ ] Typed errors (`DowngradeRefused`, `MissingMigration`); migrated dict re-validated by the caller's
      Pydantic model (the engine transforms keys/values; the model validates — separation of concerns).
- [ ] All unit tests in `core/tests/model/test_migrations.py` pass; `/preflight` clean (`uv run mypy .`).

## Wiring / entry point (Step 7.5)
none — wiring lands in Phase 2/3. The engine is invoked by the host's startup-reconcile loader (Phase 2+):
read file → `migrate(...)` → host backs up the original → writes the migrated result → Pydantic-validate.
No production entry point this slice; exported from `core/model/`.

## Files expected to touch
**New:**
- `core/model/migrations.py` — the engine + `DowngradeRefused`/`MissingMigration` + the version baselines.
- `core/tests/model/test_migrations.py`.

## RED test outline (Step 2)
Tests in `core/tests/model/test_migrations.py` (`spec(§5)`-tagged, `unit`; use SYNTHETIC migration chains):
1. **`test_migrate_identity_at_current`** — `from_version == current` → data returned unchanged.
2. **`test_migrate_forward_single_step`** — a synthetic `{1: v1_to_v2}` chain, current=2 → `migrate(data, 1)` applies it.
3. **`test_migrate_forward_multi_step`** — `{1: …, 2: …}`, current=3 → steps apply in ascending order.
4. **`test_downgrade_refused`** — `from_version=3`, current=2 → raises `DowngradeRefused`.
5. **`test_missing_migration_raises`** — `from_version=1`, current=3, chain missing `2→3` → raises `MissingMigration`.
6. **`test_engine_does_no_io`** — `migrate(...)` performs no filesystem access (signature is data→data; assert no temp/backup files created). Why: §4/§7 — the engine never touches the FS; the host does.
7. **`test_current_baselines_are_v1`** — `CURRENT_MANIFEST_SCHEMA_VERSION == CURRENT_REGISTRY_SCHEMA_VERSION == 1`.
8. **`test_migrate_does_not_validate`** — `migrate` returns a raw dict (doesn't construct the Pydantic model); the caller validates. Why: separation (transform vs validation).

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** none (behavioral engine, not a field-bearing model — like 1.1, **no schema-snapshot test**).
- **§2.5-seam:** the migration protocol crosses the seam (every track reading manifest/registry uses it) — but it's
  behavioral, so conformance is pinned by the tests above, not a field snapshot.
- **Orchestrator rows (Step 9):** add a `core/CLAUDE.md` cross-doc row for the migration engine (§5) + lookup;
  no Appendix-A field change (the schemaVersion fields are already on the manifest/registry rows).

## Things to flag at Step 2.5
1. **Pure engine vs I/O scope (load-bearing, §4/§7).** Default vote: **PURE engine** (data→data); file read/write +
   backup-before-migrate are HOST-owned (HostPort, Phase 2+). The engine never touches the FS. Confirm — this keeps
   the migrator off the mutation-chokepoint + decoupled from the unbuilt HostPort.
2. **Generic engine vs per-file migrators.** Default vote: **one generic engine** parametrized by
   `(current_version, chain)`; manifest + registry each pass their own baseline + (empty, for now) chain.
3. **Migration chain shape.** Default vote: **a registry `dict[int, Callable[[dict], dict]]`** keyed by the
   `from_version` of each `vN → vN+1` step; the engine walks ascending from `from_version` to `current`.
4. **Typed errors.** Default vote: `DowngradeRefused` + `MissingMigration` (+ a common base, e.g. `MigrationError`).
5. **`backup-before-migrate`** — Default vote: **documented protocol only** (host backs up the original before
   writing the migrated result). Out of scope for the pure engine; record the host-contract for Phase 2+.
6. **Does the engine re-validate against the target model?** Default vote: **no** — returns a raw dict; the caller
   constructs/validates the Pydantic model. Separation: transform (engine) vs validation (model).

## Dependencies + sequencing
- **Depends on:** 1.2c1 + 1.2c2 (the manifest/registry `schemaVersion` fields the engine migrates). No 1.1
  runtime import. No `HostPort` dependency (pure engine; I/O deferred).
- **Blocks:** Phase-2/3 startup-reconcile loader (reads file → migrate → host backs-up + writes → validate);
  any future schema change (registers the first real `v1 → v2` migration here).
- **This COMPLETES Task 1.2** (chunk/stamp/manifest/registry + this migration engine) → end-of-1.2 cycle boundary.

## Estimated commit count
**1.** A focused pure engine + its synthetic-chain tests = one logical unit, one commit.

## Lessons-logged candidates anticipated
- **Architecture-doc note** — the pure-engine / host-owns-I/O-and-backup split (the migrator never touches the FS;
  backup-before-migrate is the host's Phase-2+ contract).
- **Convention** — reinforces LESSONS §1/§3/§5; no NEW lesson expected.

## How to invoke
1. Read end-to-end — Q1 (pure engine, host-owns-I/O) is the load-bearing §4/§7 scope call.
2. Reuse the session: `/tdd schema_migrations`. Step 8 = run the canonical `/preflight` (LESSON §5; override the
   stale `mypy core` line with `uv run mypy .` per D-A3).
3. Step 0 → Step 1 → Step 2.5 (write-up + Q answers). Step 9 — surface anything beyond the candidates.
