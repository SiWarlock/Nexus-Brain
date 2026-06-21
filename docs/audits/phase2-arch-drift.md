# Phase 2 — Architecture-drift audit (spine track)

> Dispatched by `/phase-exit 2` (2026-06-21). Read-only diff of each cited `ARCHITECTURE.md`
> Spec-anchor statement vs the shipped code on `track/spine` @ `2b36fad`. Green schema-snapshot
> tests count as verified-by-test (cite + skip the manual diff); a failing snapshot is the finding.

**Spec anchors audited:** §8 (ingestion pipeline), §18 (redaction), §16 (providers/policy), §5 (data/state model) + the 2.S task anchors §14 (INV-allowlist), §7 (HostPort), §4 (#3 chokepoint).

## Verdict: **CLEAR** — 5 anchors audited, 0 DRIFT / 0 STALE-DOC / 0 ambiguous

---

## §8 — Ingestion pipeline

| Statement | Verdict | Evidence |
|---|---|---|
| discover: source-agnostic, `.gitignore`+`.brainignore` honored | VERIFIED | `core/ingest/discover.py:31,68` — both read; gitwildmatch via `pathspec` |
| discover: never follows symlinks | VERIFIED | `discover.py:82-105` — `followlinks=False` + explicit `is_symlink()` guards (dirs AND files) |
| discover: always excludes `.git` + `.project-brain` | VERIFIED | `discover.py:28` — `ALWAYS_EXCLUDE_DIRS` |
| classify: four axes (doc_or_code, ownership, producer, doc_type) | VERIFIED | `classify.py:82-92` |
| classify closed sets mirror frozen `Chunk` Literals | VERIFIED-BY-TEST | `test_classify.py::test_classification_vocab_matches_chunk_contract` (get_args drift pin) |
| chunk (docs): ATX heading-split, fenced-code-immune, cap-bounded line-tiling | VERIFIED | `chunk.py:36-41,119`; `test_chunk.py::test_heading_in_fenced_code_block_not_split_point` |
| chunk (code): AST via vendored parser, 4 langs (py·ts·cpp·php), line-tiling fallback | VERIFIED | `chunk.py:261-272`; fallback `chunk.py:369-374` |
| every draft ≤ `TEXT_MAX_LEN` | VERIFIED-BY-TEST | `test_chunk.py::test_long_section_subsplit_at_line_boundary` |
| `register="plain"` v0; `deep` reserved for context-augment (Phase 3) | VERIFIED | `chunk.py:74`; `pipeline.py:235` (`context_blurb=None`) |
| `add` idempotent | VERIFIED-BY-TEST | `test_pipeline.py::test_add_idempotent_reingest` + `…_after_change` |
| R-PARTIAL: skip-not-abort on malformed/binary | VERIFIED-BY-TEST | `test_pipeline.py::test_add_partial_skips_malformed_file` |
| ChunkDraft internal; frozen Chunk/Anchor assembled at 2.4 | VERIFIED-BY-TEST | `test_chunk.py::test_chunkdraft_fields_subset_of_chunk` + closed-set test |
| LanceDB embed/persist + real git-SHA tag = Phase 3 (v0 `recipe_sha` placeholder) | VERIFIED | `pipeline.py:25-27,161-168` — explicit placeholder; documented Phase-2 scope |

## §18 — Redaction

| Statement | Verdict | Evidence |
|---|---|---|
| Redactor runs at all THREE sinks | VERIFIED-BY-TEST | `test_redactor.py::test_all_three_sinks_return_str` + `…fuzz_gate_passes_all_sinks` |
| `CatchableSetRedactor` implements frozen `Redactor` Protocol | VERIFIED-BY-TEST | `test_redactor.py::test_redactor_conforms_to_protocol` |
| Allowlist (git-SHA/ULID/UUID) BEFORE entropy | VERIFIED | `redactor.py:202-214` — `_is_allowlisted()` precedes `_shannon_bits()` |
| Idempotence via EXACT marker match | VERIFIED-BY-TEST | `test_redactor.py::test_idempotence_exact_not_prefix`; `redactor.py:111` |
| Fail-CLOSED on internal error | VERIFIED | `redactor.py:155-156` — `except Exception: return _M_FAILCLOSED` |
| Fuzz gate hard gate; recall 1.000 / FP 0.000 / git-SHA FP 0% | VERIFIED-BY-TEST | `test_redactor.py::test_fuzz_gate_passes_all_sinks` |
| Uniform across sinks v0 (D-A5/A6 owner-ratified) | VERIFIED | `redactor.py:148` — `del sink` (uniform v0) |
| redact-before-embed in pipeline (Key-safety #2) | VERIFIED-BY-TEST | `test_pipeline.py::test_add_redacts_before_embed` (secret absent from `c.text`; vector of redacted text) |

## §16 — Providers / policy

| Statement | Verdict | Evidence |
|---|---|---|
| `EmbeddingProvider` injected; `model_version` provider-only | VERIFIED | `pipeline.py:47,183,209` |
| `policy_path` stamped in manifest (Phase-2 free-form) | VERIFIED | `pipeline.py:54-57,167` |
| Redaction applies regardless of local/cloud | VERIFIED | `pipeline.py:208` — `redact(…, Sink.PERSIST)` unconditional before embed |

## §5 — Data / state model

| Statement | Verdict | Evidence |
|---|---|---|
| `Chunk` 19 frozen fields | VERIFIED-BY-TEST | `test_chunk.py::test_chunk_schema_snapshot` |
| `Anchor` 11 fields; `AnchorState` 5 values (no `deleted`) | VERIFIED | `model/anchor.py:33-37` |
| `ProjectManifest` 12 fields; camelCase aliases | VERIFIED | `model/manifest.py:51-62` |
| `ManifestArtifact` 5 fields | VERIFIED | `model/manifest.py:24-34` |
| Manifest DERIVED projection; written via `HostPort.perform` only | VERIFIED-BY-TEST | `test_pipeline.py::test_add_writes_manifest_via_hostport` + `…routes_all_mutation_via_perform` |
| Source-of-truth law: LanceDB git-SHA canonical; manifest derived | VERIFIED | `pipeline.py:120-133` — v0 `recipe_sha` placeholder; Phase-3 real-SHA carry documented |
| `StoreVersionStamp` has NO SHA field | VERIFIED-BY-TEST | `test_stamp.py::test_stamp_rejects_sha` |

## §14 INV-allowlist + §7 HostPort + §4 #3 chokepoint

| Statement | Verdict | Evidence |
|---|---|---|
| `HostPort` Protocol shape | VERIFIED-BY-TEST | `test_host.py` Intent/Action/Result schema snapshots (GREEN) |
| `HostCapability` closed 3-value StrEnum | VERIFIED-BY-TEST | `test_host.py` membership snapshot; `host.py:50-53` |
| `StoreWritePayload` fields `{rel_path, content}` (Option C) | VERIFIED-BY-TEST | `test_host.py::test_store_write_payload_schema_snapshot` |
| `HostIntent.payload` optional (None default) | VERIFIED-BY-TEST | `test_host.py` — `HostIntent(…).payload is None` |
| Fail-closed `authorize` | VERIFIED-BY-TEST | `test_host.py::test_authorize_denies_unallowlisted_capability` |
| `perform` defense-in-depth re-validation | VERIFIED-BY-TEST | `test_host.py::test_perform_denies_unallowlisted_capability_even_if_authorized` |
| INV-allowlist: no mutation outside `HostPort.perform` | VERIFIED-BY-TEST | `test_host.py::test_inv_allowlist_no_mutation_outside_hostport` (hardened AST scan, GREEN incl. `pipeline.py`) |
| `StandaloneHost` atomic temp-write + `os.replace`, contained | VERIFIED | `host.py:200-208` (`mkstemp`/`os.replace`); `_resolve_within_root` realpath containment `host.py:211-228` |
| Phase-2 default allowlist = `{OWN_STORE_WRITE}` | VERIFIED-BY-TEST | `test_host.py::test_standalone_host_default_allowlist` |

### Expected states (NOT drift — confirmed)
- §7 `HostIntent`/`HostAction` "code ahead of Appendix-A prose" on the payload field is **verified-by-test** (green snapshots); the Appendix-A §7 prose row + `core/CLAUDE.md` cross-doc row are written at this round's `/orchestrate-end` (staggered after the code commit, per the doc cadence).
- §8 `add` Phase-2 scope (frozen Chunk/Anchor vs `Fake*` + manifest via HostPort; LanceDB persist + real git-SHA tag = Phase 3.1; v0 `recipe_sha` placeholder) is documented Phase-2 scope.
- No `ProjectManifest`/`Chunk`/`Anchor` field changed this round (frozen-contract guard held).

**Drift: none. Verdict: CLEAR.**
