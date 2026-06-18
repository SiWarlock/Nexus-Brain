# Session contract-002 — Phase-1 determinism seams + §5 data contracts

- **Date:** 2026-06-17
- **Phase:** Phase 1 — Shared contracts & ports freeze (the forced-serial bottleneck)
- **Track:** contract (`track/contract`)
- **Role:** implementer (`contract-core-implementer`)
- **Predecessor session:** none (first implementer session on this track). Companion: orchestrator handoff `contract-001-2026-06-17-phase1-contracts.md`.
- **Successor session:** `contract-003-2026-06-18-trust-contracts-and-port-freeze.md` (Phase 1.3 trust contracts + Phase 1.4 the 11-port freeze).

## Why this session existed

Bootstrap the `contract` track: stand up the `core/` Python engine skeleton and freeze the Phase-1
determinism seams (1.1) and the four §5 data contracts + their migration framework (1.2a–1.2d) —
the freeze-before-fork contracts every downstream track reads read-only. This is the bottleneck:
nothing forks until these land.

## What was built

### Files created
- **Skeleton (1.1, `61853b3`):** `core/pyproject.toml` (uv virtual project · pydantic v2 · ruff · mypy --strict · pytest; flat layout rooted at `core/`), `core/uv.lock`, `core/ports/__init__.py`, `core/testing/__init__.py`, `core/tests/__init__.py`, `core/tests/ports/__init__.py`.
- **Determinism seams (1.1, `61853b3`):** `core/ports/clock.py` (`Clock` Protocol + `SystemClock`), `core/ports/idgen.py` (`IdGen`/`Seed` Protocols + `UuidGen`/`SystemSeed`), `core/testing/fakes.py` (`FakeClock`/`FakeIdGen`/`FakeSeed` — the canonical test-double home), `core/tests/ports/test_clock.py` + `test_idgen.py` (16 tests).
- **Chunk (1.2a, `269b68e`):** `core/model/__init__.py`, `core/model/chunk.py` (19-field frozen LanceDB row), `core/tests/model/__init__.py`, `core/tests/model/test_chunk.py` (10 tests).
- **StoreVersionStamp (1.2b, `4fab4ab`):** `core/model/stamp.py` (5-field §5 source-of-truth, no SHA field), `core/tests/model/test_stamp.py` (11 tests).
- **Manifest (1.2c1, `07c3cba`):** `core/model/manifest.py` (`ProjectManifest` 12 + `ManifestArtifact` 5, camelCase on-disk aliases), `core/tests/model/test_manifest.py` (17 tests).
- **Registry (1.2c2, `665dd8b`):** `core/model/registry.py` (`Registry` wrapper + `RegistryEntry` 6, two distinct schema_versions), `core/tests/model/test_registry.py` (17 tests).
- **Migration engine (1.2d, `bb000b1`):** `core/model/migrations.py` (pure forward-only runner + `DowngradeRefused`/`MissingMigration`), `core/tests/model/test_migrations.py` (11 tests).

### Files modified
- `core/pyproject.toml` (1.2a) — added `model` to `[tool.mypy] files` + `[tool.ruff.lint.isort] known-first-party` to wire the new package into the gate.
- `core/model/stamp.py` + `core/tests/model/test_manifest.py` (`1ffdcc4`) — wrapped 3 over-100-col lines (E501; see TDD/Findings below).

**Suite at close:** 82 tests, `spec(§5)`/`spec(§7)`-tagged; visible gate clean (ruff · format · mypy --strict · pytest), `-W error` import clean.

## Decisions made
- **Flat layout rooted at `core/`** (Q1, 1.1): `from ports.clock import Clock`; pytest `pythonpath=["."]`; type-check is `uv run mypy .` (the template's `mypy core` doesn't fit — orchestrator updated `core/CLAUDE.md`; the `/preflight` command-file edit is escalated to the lead).
- **Ports = `typing.Protocol` + real adapter + contract-faithful `Fake*` double** (LESSON §1); minted ids are opaque (LESSON §2).
- **Contract models:** `frozen=True` + `extra="forbid"`; required fields via `Field(...)`; an omit-each-field test as the generic guard; scope-suppress any BaseModel/ABCMeta name-shadow warning (LESSON §3, born from the `Chunk.register` bug).
- **StoreVersionStamp omits the SHA** (load-bearing §5): the git-SHA is the LanceDB version tag (sole canonical home); a stamp SHA field would be a divergent second home. Resolves 1.2a's Q3 (the chunk's per-chunk `ingested_from_sha` is legitimate finer-grained provenance).
- **Manifest on-disk JSON contract:** snake_case Python fields + camelCase aliases on ONLY `schemaVersion`/`ingestedFromSha`; `validate_by_name`+`validate_by_alias` (the pydantic 2.11+ names — `populate_by_name` is deprecated and would break `-W error`). Two snapshots: Python field-name + by-alias on-disk key (LESSON §4).
- **Registry = wrapper** (not RootModel) so the file carries its own format `schema_version` for the migrator, distinct from the entry's per-project store schema. Non-empty `project_id` map keys via `Annotated[str, StringConstraints(min_length=1)]`.
- **Migration engine is PURE** (load-bearing §4/§7): data→data, NO file I/O (import-purity-pinned); backup-before-migrate + read/write are HOST-owned (HostPort, Phase 2+). Identity returns a defensive copy. Downgrade-refuse fail-closed; missing-migration detection.
- **`policy` min_length=1** (registry): an empty privacy marker is a fail-open shape; closed it now (fail-CLOSED semantics deferred to the 1.5 policy model).

## Decisions explicitly NOT made (deferred)
- **Uniform whitespace-strip on identity strings** (`StringConstraints(strip_whitespace=True, min_length=1)`) — deferred to a uniform before-fork sweep across 1.2b/1.2c1/1.2c2 rather than piecemeal (orchestrator Carry-forward).
- **Strict on-disk key-shape rejection** for the manifest's aliased fields (reject snake-key + duplicate-key) — the frozen model is a lenient reader / strict writer; strict rejection is owned by the Phase-2+ host startup-reconcile loader.
- **`vector` dim/finiteness, `anchor`/`*_sha` format** validation — deferred to the Phase-3.1 LanceDB `Vector(dim)` binding and the 1.3 `Anchor` + stamp sha seam, respectively.
- **`policy` fail-closed semantics** (absent/unrecognized → most-restrictive, local-only) — owned by the 1.5 `policy.yaml` model.
- **Real `v1→v2` migrations** — none yet; the framework + downgrade-refuse safety are frozen and exercised with synthetic chains.

## TDD compliance
**Clean — no violations.** Every slice was test-first (RED confirmed for the right reason before GREEN); each Step-9 fold re-entered RED for its driver (e.g. `register`-required, stamp/manifest/registry min_length, identity-returns-copy). `1ffdcc4` was a pure lint wrap (no behavior, not a TDD slice). Behavioral engines (1.1 ports, 1.2d migrations) carry no schema-snapshot by design (like 1.1) — conformance is pinned behaviorally.

**Finding raised + resolved this session (gate integrity → LESSON §5):** 1.2b + 1.2c1 shipped 3 E501 lint violations undetected because my Step-8 gate command suppressed ruff output (`ruff check . >/dev/null && echo OK` short-circuits silently on failure). Impact was lint-only (mypy/pytest were never suppressed). Fixed in `1ffdcc4`; switched to visible-output gates with explicit exit codes.

## Reachability
All Phase-1 contracts are foundational — exported from `core/ports/`, `core/model/`, `core/testing/` with **no production entry point this phase, by design**:
- `Clock`/`Seed`/`IdGen` — first consumed in 1.2+ (id/timestamp injection) and §10 anchor revalidation.
- `Chunk` — first constructed in Phase-2 ingest, persisted by the Phase-3.1 LanceDB writer.
- `StoreVersionStamp`/`ProjectManifest`/`Registry` — first written/reconciled by the Phase-2/3 host startup-reconcile.
- migration engine — invoked by that same Phase-2/3 startup-reconcile loader.

No tested-but-unwired *gaps* (these are contracts awaiting their consumers, not dead code); CodeGraph is greenfield so there is no call path to trace yet. No later slice removed any wiring.

## Open follow-ups (Carry-forwards — orchestrator-tracked)
1. **Whitespace-strip identity sweep** — before fork; uniform across 1.2b/1.2c1/1.2c2 (+ future identity fields).
2. **policy fail-closed semantics** → 1.5 policy model.
3. **Strict on-disk key-shape rejection** (manifest aliased fields) → Phase-2+ host startup-reconcile loader. *(Note: `core/CLAUDE.md` cross-doc row currently phrases this as "→ 1.2d loader"; 1.2d turned out to be the pure engine, not the loader — the loader is Phase-2+. Minor orchestrator-doc clarification.)*
4. **vector dim/finiteness** → Phase-3.1 `Vector(dim)` binding; **anchor/`*_sha` format** → 1.3 `Anchor` + stamp sha seam.
5. **backup-before-migrate + file read/write protocol** → Phase-2+ host (HostPort) — the migration engine deliberately does no I/O.
6. **`/preflight` command-file `mypy core`→`mypy .`** edit — escalated to the lead (agent-loaded config, needs user authorization).

## How to use what was built
- **Inject seams, never call inline:** construct with `Clock`/`IdGen`/`Seed` (real adapters in prod; `core/testing/fakes.py` doubles under test). Never `datetime.now()`/`uuid4()`/`random.*` in `core` (forbidden-rule 4).
- **Build a contract model** by Python field name; serialize the manifest on-disk with `model_dump_json(by_alias=True)`; validate untrusted on-disk/MCP input with `model_validate(_json)` (parse-don't-trust).
- **Migrate an on-disk file:** host reads it → `migrate(data, from_version, chain=..., current_version=CURRENT_*_SCHEMA_VERSION)` → host backs up the original → writes the result → re-validate with the Pydantic model.
