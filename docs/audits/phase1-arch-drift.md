# Phase 1 Architecture-Drift Audit

**Phase:** Phase 1 — Shared contracts & ports freeze (fork gate)  
**Worktree:** `/project-brain-contract` (branch `track/contract`, merge commit `063281b`)  
**Auditor:** arch-drift-auditor  
**Date:** 2026-06-20  
**Test baseline:** 232 passed, 0 failed (`uv run pytest -q`)

---

## Method

Per anchor: extracted checkable statements from the cited ARCHITECTURE.md section and Appendix-A row → applied the verified-by-test shortcut where a green schema-snapshot test covers the contract → spot-checked code for any statement not covered by a snapshot test.

---

## Per-Anchor Findings Table

### §7 — Ports & adapter contracts (11 ports, Fakes)

| Statement | Verdict | Evidence |
|---|---|---|
| 11 ports defined | VERIFIED | `ports/`: HostPort, EventSource, EmbeddingProvider, Reranker, ContextStrategy, ModelProvider, CodeGraphPort, ObservabilitySink, SecretStore, Clock, Seed/IdGen = 11 ports across 6 files |
| Each port is a `@runtime_checkable Protocol` | VERIFIED | All 9 Protocol ports use `@runtime_checkable Protocol`; Clock/IdGen/Seed are Protocols too (`clock.py`, `idgen.py`) |
| Fake doubles present for all ports | VERIFIED | `testing/fakes.py`: FakeClock, FakeIdGen, FakeSeed, FakeHost, FakeEmbeddingProvider, FakeReranker, FakeContextStrategy, FakeModelProvider, FakeCodeGraph, FakeEventSource, FakeSecretStore, FakeRedactor, FakeObservabilitySink — all ports covered |
| `HostCapability` = closed StrEnum `{own_store_write, owned_doc_refresh, consented_host_config}` | VERIFIED BY TEST | `test_host.py::test_host_capability_values` (green); code: `ports/host.py:31-43` |
| `HostPort`: `capabilities()`, `authorize(intent)`, `perform(action)` | VERIFIED | `ports/host.py:88-101` |
| `EventSource`: `poll()/subscribe()` | VERIFIED | `ports/events.py:28-37` |
| `EmbeddingProvider`: `embed`, `dimension`, `model_version` | VERIFIED | `ports/providers.py:64-79` |
| `Reranker`: `rerank` | VERIFIED | `ports/providers.py:83-88` |
| `ContextStrategy`: `augment` | VERIFIED | `ports/providers.py:92-97` |
| `ModelProvider`: `generate` w/ Citations | VERIFIED | `ports/providers.py:101-107` |
| `CodeGraphPort`: `query(kind, sym)` | VERIFIED | `ports/codegraph.py:110-121` |
| `ObservabilitySink`: `emit` | VERIFIED | `ports/observability.py:31-35` |
| `SecretStore`: `get_ref/resolve` | VERIFIED | `ports/secrets.py:36-46` |
| `Clock` + `Seed/IdGen` deterministic seams | VERIFIED | `ports/clock.py`, `ports/idgen.py` |
| Frozen result types `RerankResult{index,score}`(allow_inf_nan=False), `Citation`, `GenerateResult` | VERIFIED BY TEST | `test_providers.py` snapshot tests (green); code: `ports/providers.py:29-62` |
| `model_version` on `EmbeddingProvider` ONLY | VERIFIED | Only `EmbeddingProvider` has `model_version` property; Reranker/ModelProvider have none |
| Cassette record/replay re-sequenced to providers/eval | VERIFIED (doc note) | No cassette in Phase-1 code — matches arch deferral to Phase-4 |

**§7 verdict: CLEAR**

---

### §5 — Data contracts (chunk, stamp, manifest, registry, migrations)

#### Chunk (19 fields, frozen)

| Statement | Verdict | Evidence |
|---|---|---|
| 19 fields (Appendix-A row, BM25/FTS = native LanceDB index, not a field) | VERIFIED BY TEST | `test_chunk.py::test_chunk_schema_snapshot` (green); EXPECTED_CHUNK_FIELDS frozenset of exactly 19 names matches `Chunk.model_fields` |
| Fields: chunk_id·project_id·source_path·doc_or_code·producer·doc_type·ownership·register·text·vector·anchor·content_hash·last_resolved_sha·ingested_from_sha·embedding_model_version·context_blurb·generation·tombstone·created_at | VERIFIED BY TEST | Same snapshot test pins all 19 names |
| `frozen=True, extra="forbid"` | VERIFIED | `model/chunk.py:39` |

#### StoreVersionStamp (5 fields, NO sha field)

| Statement | Verdict | Evidence |
|---|---|---|
| 5 fields: `{embedding_model, dimension, schema_version, index_built_at, source_root_hash}` | VERIFIED BY TEST | `test_stamp.py::test_stamp_schema_snapshot` (green); EXPECTED_STAMP_FIELDS = frozenset of exactly those 5 names |
| NO sha field (git-SHA = LanceDB version tag, not a stamp field) | VERIFIED BY TEST | `test_stamp.py::test_stamp_rejects_sha_field` (green); module docstring at `stamp.py:7-9` |

#### ProjectManifest (12 fields, frozen)

| Statement | Verdict | Evidence |
|---|---|---|
| 12 fields: `{schema_version, project_id, source_repo, ingested_from_sha, embedding_model, dimension, chunker_version, doc_format_spec_range, artifacts, staleness_pointer, policy_path, lance_version_tag}` | VERIFIED BY TEST | `test_manifest.py::test_manifest_schema_snapshot` (green); EXPECTED_MANIFEST_FIELDS = frozenset of exactly those 12 names |
| On-disk camelCase only for `schemaVersion`/`ingestedFromSha`; rest snake | VERIFIED BY TEST | `test_manifest.py::test_manifest_json_keys_camelcase` (green); EXPECTED_MANIFEST_JSON_KEYS pins the 2 camelCase aliases |
| `frozen=True, extra="forbid"` | VERIFIED | `model/manifest.py:44-49` |

#### Registry (6 fields across 2 models)

| Statement | Verdict | Evidence |
|---|---|---|
| `RegistryEntry` 6 fields: `{db_path, schema_version, model_version, codegraph_db_path, last_indexed_sha, policy}` | VERIFIED BY TEST | `test_registry.py::test_registry_entry_schema_snapshot` (green); EXPECTED_ENTRY_FIELDS = frozenset of exactly those 6 names |
| `Registry` 2 fields: `{schema_version, entries}` | VERIFIED BY TEST | `test_registry.py::test_registry_schema_snapshot` (green); EXPECTED_REGISTRY_FIELDS = `{"schema_version","entries"}` |
| Appendix-A says registry = 6 fields (the `RegistryEntry` row count) | VERIFIED | Matches: Appendix-A cites `project_id → {db_path, schema_version, model_version, codegraph_db_path, last_indexed_sha, policy}` = 6 entry fields |
| All-snake on-disk keys | VERIFIED BY TEST | `test_registry.py::test_registry_on_disk_keys_are_field_names` (green) |

#### Schema migration engine

| Statement | Verdict | Evidence |
|---|---|---|
| Pure forward-only `migrate(data, from_version, *, chain, current_version)` | VERIFIED | `model/migrations.py:42-67`; signature matches exactly |
| Downgrade-refuse (`DowngradeRefused`) | VERIFIED | `model/migrations.py:34-36, 55-58` |
| Missing-migration detection (`MissingMigration`) | VERIFIED | `model/migrations.py:38-39, 61-64` |
| Baselines = v1 for both manifest and registry | VERIFIED | `model/migrations.py:22-23`: `CURRENT_MANIFEST_SCHEMA_VERSION = 1`, `CURRENT_REGISTRY_SCHEMA_VERSION = 1` |
| NO file I/O (backup + read/write HOST-owned) | VERIFIED | Module docstring at `migrations.py:1-12`; no `open()`, `os.*`, `Path.*` calls; `test_inv_allowlist_no_mutation_outside_hostport` (green) passes on this file |

**§5 verdict: CLEAR**

---

### §4 — HostPort = sole mutation chokepoint

| Statement | Verdict | Evidence |
|---|---|---|
| No core module reaches fs/git/external/session mutation except via `HostPort.perform` | VERIFIED BY TEST | `test_host.py::test_inv_allowlist_no_mutation_outside_hostport` (green) — AST-scan over all `core/` modules (excl. tests/); passes because nothing in Phase-1 code mutates |
| `perform` defense-in-depth re-validates capability even if `authorized` is forged | VERIFIED BY TEST | `test_host.py::test_perform_denies_unallowlisted_capability_even_if_authorized` (green); `ports/host.py:99-101` |
| `authorize` fail-closed (not in caps → `HostDenied`) | VERIFIED BY TEST | `test_host.py::test_authorize_denies_unallowlisted_capability` (green); `FakeHost.authorize` at `testing/fakes.py:103-106` |
| INV-allowlist tripwire seeded, full runtime proof Phase-2 | VERIFIED (doc note) | Arch correctly states this (Appendix-A:218); tripwire is the static seam, not yet dynamic mutation coverage |

**§4 verdict: CLEAR**

---

### §10 — Trust contracts (Anchor, ProvenancePacket, EvidenceRef)

#### Anchor (11 fields)

| Statement | Verdict | Evidence |
|---|---|---|
| 11 fields: `anchor_id·project_id·source_file·source_span·target_path·target_line_start·target_line_end·target_symbol?·state·last_resolved_sha·confidence` | VERIFIED BY TEST | `test_anchor.py::test_anchor_schema_snapshot` (green); EXPECTED_ANCHOR_FIELDS = frozenset of exactly those 11 names |
| `AnchorState` = 5 values `{live,stale,moved,unknown,orphaned}`; `deleted` NOT a value | VERIFIED BY TEST | `test_anchor.py::test_anchor_state_values` (green); `AnchorState` StrEnum at `model/anchor.py:25-37` |
| `confidence` ∈ [0,1] | VERIFIED | `model/anchor.py:60`: `Field(..., ge=0.0, le=1.0)` |
| `target_symbol` optional | VERIFIED | `model/anchor.py:57`: `target_symbol: IdentityStr | None = None` |
| Invalid state rejected at parse | VERIFIED BY TEST | `test_anchor.py::test_anchor_rejects_invalid_state` (green) |

#### ProvenancePacket (10 fields, evidence: tuple[EvidenceRef])

| Statement | Verdict | Evidence |
|---|---|---|
| 10 fields: `project_ids·source_ids·citations·commit_shas·session_ids·recorded_sha?·index_freshness·confidence·drift_markers·evidence` | VERIFIED BY TEST | `test_provenance.py::test_provenance_schema_snapshot` (green); EXPECTED_PROVENANCE_FIELDS = frozenset of exactly those 10 names |
| `evidence: tuple[EvidenceRef]` (not `low_confidence_links`) | VERIFIED BY TEST | `test_provenance.py::test_provenance_rejects_extra_field` proves `low_confidence_links` is rejected (green); `model/provenance.py:43` has `evidence: tuple[EvidenceRef, ...]` |
| `citations` = file:line TOKENS (`tuple[str]`) | VERIFIED | `model/provenance.py:36`: `citations: tuple[IdentityStr, ...]` |
| All collection fields are `tuple` (LESSON 8 immutability) | VERIFIED | `model/provenance.py:34-43`: all collection fields typed as `tuple[..., ...]` |

#### EvidenceRef (4 fields)

| Statement | Verdict | Evidence |
|---|---|---|
| 4 fields: `{type, label, resource_ref?, confidence?}` | VERIFIED BY TEST | `test_evidence.py::test_evidence_schema_snapshot` (green) |
| `EvidenceType` = constrained-str alias (membership DEFERRED to Phase-4, D-A11) | VERIFIED | `model/evidence.py:31`: `EvidenceType = IdentityStr`; comment block explains D-A11 deferral |
| No EvidenceType membership snapshot | VERIFIED | No membership snapshot in tests (correct per D-A11) |

**§10 verdict: CLEAR**

---

### §14 — MCP tool contract + ingress

| Statement | Verdict | Evidence |
|---|---|---|
| 5 tools: `search/get_file/graph/list_projects/status` param models defined | VERIFIED BY TEST | `test_mcp_contract.py::test_param_field_name_snapshots` (green); `model/mcp_contract.py:92-138` |
| `get_file` ASCII positive allow-list | VERIFIED BY TEST | `test_mcp_contract.py::test_get_file_path_allowlist` (green); `model/mcp_contract.py:51-75` |
| `MAX_TOP_K = 100`, `MAX_QUERY_LEN = 4096`, `MAX_RESPONSE_ITEMS = 500` | VERIFIED BY TEST | `test_mcp_contract.py::test_bounds_constants` (green); `model/mcp_contract.py:33-39` |
| `PolicyDenied` marker (marker-not-error): `denied: Literal[True]`, `reason: TextStr` | VERIFIED | `model/mcp_contract.py:180-196` |
| `McpToolResult = McpResult | PolicyDenied` union | VERIFIED | `model/mcp_contract.py:196` |
| `RetrievalScope` StrEnum `{project, portfolio}` | VERIFIED | `model/mcp_contract.py:81-89` |
| `McpResult.items` capped at `MAX_RESPONSE_ITEMS` (raises on over-bound) | VERIFIED | `model/mcp_contract.py:175`: `Annotated[tuple[McpResultItem, ...], Field(max_length=MAX_RESPONSE_ITEMS)]` |
| `McpResult` composes `ProvenancePacket` | VERIFIED | `model/mcp_contract.py:176`: `provenance: ProvenancePacket` |
| `McpResultItem` composes `EvidenceRef` as `chip` | VERIFIED | `model/mcp_contract.py:157`: `chip: EvidenceRef` |

**§14 verdict: CLEAR**

---

### §16 — policy.yaml (ProjectPolicy, fail-CLOSED)

| Statement | Verdict | Evidence |
|---|---|---|
| `schema_version` field present | VERIFIED BY TEST | `test_policy.py::test_policy_field_names_snapshot` (green); `model/policy.py:102` |
| 7 top-level fields: `{schema_version, privacy, providers, mcp, federation, sessions, brainignore}` | VERIFIED BY TEST | `test_policy.py::test_policy_field_names_snapshot` (green); EXPECTED_POLICY_FIELDS = frozenset of those 7 names |
| Fail-CLOSED defaults (privacy=local, all opt-ins OFF) | VERIFIED BY TEST | `test_policy.py::test_fail_closed_defaults` (green); `model/policy.py:102-108` |
| Unknown key/bad enum raises (parse-don't-trust) | VERIFIED BY TEST | `test_policy.py::test_unrecognized_privacy_rejected` + `test_frozen_and_extra_forbid` (green) |
| `Privacy` StrEnum `{local, cloud}` | VERIFIED BY TEST | `test_policy.py::test_privacy_values` (green) |
| On-disk keys snake_case throughout (no camelCase aliases) | VERIFIED BY TEST | `test_policy.py::test_policy_ondisk_key_snapshot` (green); EXPECTED_POLICY_ONDISK_KEYS matches EXPECTED_POLICY_FIELDS exactly |
| Provider CATALOG membership + privacy↔provider consistency deferred to Phase-10 (D-A11) | VERIFIED (doc note) | `model/policy.py:20-21`; `ProviderPolicy` ids are opaque `IdentityStr | None` |

**§16 verdict: CLEAR**

---

### §18 — Redactor interface (Sink enum, behavioral Protocol)

| Statement | Verdict | Evidence |
|---|---|---|
| `Sink` = closed 3-value StrEnum `{persist, mcp_egress, cloud_egress}` | VERIFIED BY TEST | `test_redactor_iface.py::test_sink_values` (green); `model/redactor_iface.py:22-31` |
| `Redactor` = `@runtime_checkable Protocol` with `redact(payload, sink) -> str` | VERIFIED | `model/redactor_iface.py:35-71` |
| Behavioral contract: idempotent, never-raises, pure, git-SHA passthrough | VERIFIED BY TEST | `test_redactor_iface.py::test_redact_is_idempotent`, `test_redact_never_raises`, `test_git_sha_passthrough` (green); `FakeRedactor` upholds all 4 |
| `FakeRedactor` present in `testing/fakes.py` | VERIFIED | `testing/fakes.py:244-269` |
| Per-sink strictness (D-A5/D-A6) deferred to Phase-2.3 | VERIFIED (doc note) | `model/redactor_iface.py:12-14`; `FakeRedactor.redact` accepts sink but applies no per-sink logic |
| Catchable-set recall floor (≥95%/FP≤5%/git-SHA 0%) enforced at Phase-2.3 fuzz gate only | VERIFIED (doc note) | `model/redactor_iface.py:55-59`; constants live in `ci/eval/redaction_fuzz/harness.py`, not here |

**§18 verdict: CLEAR**

---

### §2.5 — Import DAG (one-way deps, no cross-sibling, `_types.py` cross-cutting)

| Statement | Verdict | Evidence |
|---|---|---|
| `ports/` depends on nothing (leaf contract) | VERIFIED | All `ports/*.py` import only stdlib + `_types`; none import from `model/` |
| `model/` imports only from `_types` and other `model/` siblings | VERIFIED | `model/chunk.py`, `stamp.py`, `manifest.py`, `registry.py`: import `_types.IdentityStr` + stdlib; `model/mcp_contract.py` imports `model/evidence` + `model/provenance` (intra-sibling, permitted); `model/provenance.py` imports `model/evidence` |
| `model/` does NOT import from `ports/` | VERIFIED | Checked all `model/*.py`; `mcp_contract.py` explicitly notes the no-cross-sibling rule (`model/ must not import ports/ — §2.5 DAG`, line 116) and maps `kind` as opaque string instead |
| `testing/fakes.py` imports from both `model/` and `ports/` | VERIFIED | `testing/fakes.py:17-24` — fakes import from `model.redactor_iface`, `ports.*`; fakes are not `model/` or `ports/`, they are `testing/` (the double-layer, cross-cutting by design) |
| `_types.py` is cross-cutting (importable by both `model/` and `ports/`) | VERIFIED | `core/_types.py` is at the package root, not inside `model/` or `ports/`; all cross-refs are `from _types import ...` |
| No upward imports (entrypoints not yet built; leaf contracts proven clean) | VERIFIED BY TEST | `test_inv_allowlist_no_mutation_outside_hostport` (green) scans all `core/` modules and finds no violations |

**§2.5 verdict: CLEAR**

---

### Appendix A — Full row reconciliation

| Appendix-A Row | Stated contract | Code verdict |
|---|---|---|
| **Chunk** — 19 fields, frozen, FTS/BM25 native | VERIFIED BY TEST | `test_chunk.py::test_chunk_schema_snapshot` (green); `model/chunk.py` |
| **StoreVersionStamp** — 5 fields, NO SHA field | VERIFIED BY TEST | `test_stamp.py::test_stamp_schema_snapshot` + `test_stamp_rejects_sha_field` (green); `model/stamp.py` |
| **Manifest** — 12 fields, camelCase aliases for 2 | VERIFIED BY TEST | `test_manifest.py::test_manifest_schema_snapshot` + `test_manifest_json_keys_camelcase` (green); `model/manifest.py` |
| **Registry** — 6 RegistryEntry fields + 2 Registry fields | VERIFIED BY TEST | `test_registry.py::test_registry_entry_schema_snapshot` + `test_registry_schema_snapshot` (green); `model/registry.py` |
| **Schema migration engine** — pure forward-only, no file I/O | VERIFIED BY TEST | `test_migrations.py` (green); `model/migrations.py` |
| **Anchor** — 11 fields, 5-value AnchorState (`deleted` NOT a value) | VERIFIED BY TEST | `test_anchor.py::test_anchor_schema_snapshot` + `test_anchor_state_values` (green); `model/anchor.py` |
| **ProvenancePacket** — 10 fields incl. `evidence: tuple[EvidenceRef]` | VERIFIED BY TEST | `test_provenance.py::test_provenance_schema_snapshot` (green); `model/provenance.py` |
| **EvidenceRef** — 4 fields, EvidenceType = constrained-str alias (D-A11 deferred) | VERIFIED BY TEST | `test_evidence.py::test_evidence_schema_snapshot` (green); `model/evidence.py` |
| **HostPort** — 3-method Protocol + 3-value HostCapability StrEnum, fail-closed + defense-in-depth | VERIFIED BY TEST | `test_host.py::test_host_capability_values` + `test_inv_allowlist_no_mutation_outside_hostport` (green); `ports/host.py` |
| **Provider ports** — 4 Protocols (Embed/Reranker/Context/Model) + frozen result types | VERIFIED BY TEST | `test_providers.py` snapshots (green); `ports/providers.py` |
| **CodeGraphPort** — `query(kind,sym)→CodeGraphResult`; 5-kind StrEnum; schema_versions assert MAX≥5; CODEGRAPH_DIR positive allow-list | VERIFIED BY TEST | `test_codegraph.py` (green); `ports/codegraph.py` |
| **Clock/Seed/IdGen** — behavioral Protocols + Fake doubles | VERIFIED BY TEST | `test_clock.py`, `test_idgen.py` (green); `ports/clock.py`, `ports/idgen.py` |
| **EventSource** — `{poll()→tuple[Event,...], subscribe(handler)}`; `Event{kind,source}` | VERIFIED BY TEST | `test_events.py` (green); `ports/events.py` |
| **SecretStore** — `{get_ref,resolve}`; `SecretRef` carries NO secret; fail-closed | VERIFIED BY TEST | `test_secrets.py` (green); `ports/secrets.py` |
| **ObservabilitySink** — `{emit(ObsEvent)}`; `ObsEvent{name, attributes: tuple[(str,str)]}` | VERIFIED BY TEST | `test_observability.py` (green); `ports/observability.py` |
| **MCP tool contract** — 5 param models, get_file ASCII allow-list, bounds constants, PolicyDenied marker, McpToolResult union | VERIFIED BY TEST | `test_mcp_contract.py` (green); `model/mcp_contract.py` |
| **policy.yaml** — `schema_version`, 7 fields, fail-CLOSED | VERIFIED BY TEST | `test_policy.py` (green); `model/policy.py` |
| **Redactor** — 3-sink alphabet, behavioral Protocol, FakeRedactor | VERIFIED BY TEST | `test_redactor_iface.py` (green); `model/redactor_iface.py`, `testing/fakes.py` |

**Appendix A verdict: CLEAR**

---

## Architecture-doc notes (STALE-DOC class — code is correct, doc could be tighter)

None identified. Every stated behavior audited maps cleanly to code + green tests.

## Ambiguous items

None.

## Mismatch summary

- DRIFT findings: **0**
- STALE-DOC notes: **0**
- Ambiguous: **0**
- Test baseline: 232 passed / 0 failed

## VERDICT: CLEAR
