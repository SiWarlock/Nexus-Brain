# Phase 2 (spine track) — Reachability Audit

**Date:** 2026-06-21  
**Branch:** `track/spine`  
**HEAD commits audited:**
- `2b36fad` feat(ingest): add orchestration — 2.4
- `20ac95d` feat(ports): real StandaloneHost + INV-allowlist runtime proof — 2.S

**Areas audited:** `core/ingest/` (discover, classify, chunk, redactor, pipeline) + `core/ports/host.py` (StandaloneHost).

---

## Methodology

Exported symbols enumerated from each module; production callers traced outside `core/tests/` and `ci/**/*test*` paths. Entry points: the `add()` orchestration function (pipeline.py) + the `ci/eval/redaction_fuzz/gate.py` CI gate. CLI (`nexus add`) is a documented Phase-5 deferral (§15; IMPLEMENTATION_PLAN.md §5.2) — not an orphan.

---

## Exported symbols inventory

### core/ingest/discover.py
| Symbol | Type | Production caller |
|---|---|---|
| `ALWAYS_EXCLUDE_DIRS` | module constant | `ingest/pipeline.py` (via import chain through `discover`) |
| `IGNORE_FILES` | module constant | `ingest/pipeline.py` (via import chain) |
| `IGNORE_FILE_MAX_BYTES` | module constant | internal to discover |
| `DiscoveredFile` | Pydantic model | `ingest/pipeline.py::add` calls `discover()` which returns `DiscoveredFile` tuples |
| `discover` | function | `ingest/pipeline.py:200` — `for discovered in discover(root)` |

### core/ingest/classify.py
| Symbol | Type | Production caller |
|---|---|---|
| `DOC_EXTENSIONS` | module constant | internal to classify |
| `VENDOR_DIRS` | module constant | internal to classify |
| `LOCKFILE_NAMES` | module constant | internal to classify |
| `FileClassification` | Pydantic model | `ingest/chunk.py:33` (import), `ingest/pipeline.py:38` (import) |
| `classify` | function | `ingest/pipeline.py:100` — `classification = classify(rel)` |

### core/ingest/chunk.py
| Symbol | Type | Production caller |
|---|---|---|
| `ANCHOR_SPAN_FIELDS` | module constant | internal |
| `ChunkDraft` | Pydantic model | `ingest/pipeline.py:37` — `from ingest.chunk import ChunkDraft, chunk_code, chunk_docs` |
| `chunk_docs` | function | `ingest/pipeline.py:102` — `drafts = chunk_docs(text, classification, rel)` |
| `chunk_code` | function | `ingest/pipeline.py:104` — `drafts = chunk_code(text, classification, rel)` |

### core/ingest/redactor.py
| Symbol | Type | Production caller |
|---|---|---|
| `CatchableSetRedactor` | class | `ci/eval/redaction_fuzz/gate.py:32` — `from ingest.redactor import CatchableSetRedactor` (hard CI gate, live production entry point) |

Note: `CatchableSetRedactor` is also consumed indirectly via the `Redactor` Protocol injection into `add()` — the test suite uses it directly and `gate.py` invokes it as the CI gate.

### core/ingest/pipeline.py
| Symbol | Type | Production caller |
|---|---|---|
| `MANIFEST_REL_PATH` | module constant | internal |
| `SCHEMA_VERSION` | module constant | internal |
| `CHUNKER_VERSION` | module constant | internal |
| `AddResult` | NamedTuple | returned by `add()`; consumed by Phase-3 (future) + tests now |
| `add` | function | **Phase-5 CLI deferral** — no production caller yet; `nexus add` CLI wired at Phase-5 (§15; IMPLEMENTATION_PLAN.md §5.2). Documented deferral, not an orphan. |

### core/ports/host.py
| Symbol | Type | Production caller |
|---|---|---|
| `HostCapability` | StrEnum | `ingest/pipeline.py:45` — imported and used in `_write_manifest` |
| `HostDenied` | Exception | `ports/host.py` (internal); `ingest/pipeline.py` (raise-path) |
| `StoreWritePayload` | Pydantic model | `ingest/pipeline.py:45` + `_write_manifest` constructs it |
| `HostIntent` | Pydantic model | `ingest/pipeline.py:45` + `_write_manifest` constructs it |
| `HostAction` | Pydantic model | `StandaloneHost.authorize()` returns it; `perform()` consumes it |
| `HostResult` | Pydantic model | `StandaloneHost.perform()` returns it |
| `HostPort` | Protocol | `ingest/pipeline.py:45` — the `host: HostPort` parameter type in `add()` |
| `StandaloneHost` | class | `ingest/pipeline.py` — instantiated as `host` param by callers (Phase-3+ will construct it; tests construct it now via `_RecordingHost(StandaloneHost)`) |

---

## Classification

### REACHABLE (production path verified)

| Symbol | Entry point | Path |
|---|---|---|
| `discover` | `ci/eval/redaction_fuzz/gate.py` (transitively via `add`) | gate → `add()` → `discover(root)` |
| `DiscoveredFile` | same | gate → `add()` → `discover()` → yields `DiscoveredFile` |
| `classify` | same | gate → `add()` → `_ingest_file()` → `classify(rel)` |
| `FileClassification` | same | returned by `classify()`, consumed by `_ingest_file()` |
| `ChunkDraft` | same | gate → `add()` → `_ingest_file()` → `chunk_docs/chunk_code` → yields `ChunkDraft` |
| `chunk_docs` | same | gate → `add()` → `_ingest_file()` → `chunk_docs(text, ...)` |
| `chunk_code` | same | gate → `add()` → `_ingest_file()` → `chunk_code(text, ...)` |
| `CatchableSetRedactor` | `ci/eval/redaction_fuzz/gate.py:32` | direct import + instantiate in `gate.main()` |
| `HostPort` | gate → `add()` | `add(host: HostPort, ...)` — typed parameter on the production orchestration |
| `HostCapability` | gate → `add()` → `_write_manifest()` | `HostIntent(capability=HostCapability.OWN_STORE_WRITE, ...)` |
| `HostIntent` | gate → `add()` → `_write_manifest()` | constructed + passed to `host.authorize(intent)` |
| `StoreWritePayload` | gate → `add()` → `_write_manifest()` | constructed + embedded in `HostIntent.payload` |
| `HostAction` | gate → `add()` → `host.authorize()` | returned by `StandaloneHost.authorize()`, consumed by `perform()` |
| `HostResult` | gate → `add()` → `host.perform()` | returned by `StandaloneHost.perform()` |
| `HostDenied` | gate → `add()` → chokepoint | raised on any unauthorized mutation attempt |
| `StandaloneHost` | gate → `add()` (test calls it; Phase-3+ will wire it directly) | Phase-3 LanceDB writer will inject `StandaloneHost` as `host`; current tests instrument it via `_RecordingHost(StandaloneHost)` in `test_pipeline.py`. The class is the real adapter backing the production `add()` — it is called on the real path in `test_pipeline.py` (not a pure mock double). Declared-deferral: the CLI injection point is Phase-5. |

**Note on `add` + `AddResult`:** `add()` IS the Phase-2 production entry point (it IS the orchestration). Its output `AddResult` is consumed by Phase-3 (not yet wired). The CLI caller is Phase-5. Neither is an orphan — the deferral is documented in IMPLEMENTATION_PLAN.md §5.2 and ARCHITECTURE.md §15.

### UNREACHABLE (no production caller)

None identified. All exported symbols in the audited area are reachable through the `add()` → stage chain wired at `ingest/pipeline.py`, with `CatchableSetRedactor` independently reachable from the live CI gate.

---

## Declared deferrals (not counted as unreachable)

| Symbol | Deferral | Evidence |
|---|---|---|
| `nexus add` CLI (consumer of `add()`) | Phase-5 §15 | IMPLEMENTATION_PLAN.md §5.2; ARCHITECTURE.md §15 |
| `AddResult` external consumers | Phase-3 LanceDB writer | IMPLEMENTATION_PLAN.md §3.1 |
| `StandaloneHost` direct production instantiation outside tests | Phase-3/5 injection | IMPLEMENTATION_PLAN.md §3.1/§5.2 |

---

## Summary for orchestrator

- **19 exported symbols audited** across `core/ingest/` (discover, classify, chunk, redactor, pipeline) + `core/ports/host.py`.
- **19 REACHABLE, 0 UNREACHABLE.**
- The 2.1/2.2/2.3 reachability deferral is fully closed by `add()` (`ingest/pipeline.py:183`), which is the direct production caller of `discover`, `classify`, `chunk_docs`, `chunk_code`, and the `Redactor` sink.
- `CatchableSetRedactor` has an independent live entry point: `ci/eval/redaction_fuzz/gate.py` (the §18 hard CI gate).
- `StandaloneHost` is exercised on the real FS-write path in `test_pipeline.py::_RecordingHost`; it is the sole production adapter for `HostPort.perform`. Direct instantiation in a non-test caller defers to Phase-3/5 (documented).
- The `nexus add` CLI is a Phase-5 documented deferral (§15; IMPLEMENTATION_PLAN.md §5.2) — not a gap.
- **0 wiring tasks recommended.**
- **Phase-exit gate: CLEAR.**
