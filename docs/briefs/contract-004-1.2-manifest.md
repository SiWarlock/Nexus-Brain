# /tdd brief — project_manifest

## Feature
Freeze the **ProjectManifest** (`.project-brain/manifest.json`) — the per-repo §5 catalog that is a
**DERIVED projection** (rebuilt from the LanceDB dataset on every commit, reconciled at startup), plus its
**ManifestArtifact** row sub-model — as frozen Pydantic v2 models with snapshot-pinned field sets. Third of
the four §5 data-contract slices (chunk ✓ → stamp ✓ → **manifest** → registry → migrations). Registry is 1.2c2.

## Use case + traceability
- **Task ID:** 1.2
- **Architecture sections it implements:** `ARCHITECTURE.md §5` — the **DERIVED-projection** half of the
  source-of-truth law: the manifest is NOT canonical (the dataset + the git-SHA **version tag** are); it is
  rebuilt from the dataset on commit + reconciled at startup. `ingestedFromSha` is explicitly **derived**.
- **Related context:** field detail in `docs/planning/DATA_MODEL.md` line 40 + Appendix-A "Manifest + Registry"
  row. **Field-set reconciliation:** Appendix-A lists 9 manifest fields; DATA_MODEL.md adds 3
  (`doc_format_spec_range`, `staleness_pointer`, `lance_version_tag`). I adjudicate the **12-field union**
  (all real + needed); reconcile the Appendix-A row at Step-9. The manifest is a **sibling to the read-only
  `.scaffolding/manifest.json`** — project-brain-owned, never the scaffolding one (§4 invariant 7).
- Conventions inherited (LESSONS §1/§3): `frozen=True`, `extra="forbid"`, `Field(...)`-required,
  omit-each-field test, shadow-name check; `min_length=1` on terminal identity strings (cf. 1.2b).

## Acceptance criteria (what "done" means)
- [ ] `ProjectManifest` + `ManifestArtifact` Pydantic v2 models in `core/model/manifest.py`, each `frozen=True`
      + `extra="forbid"`, with the field sets below.
- [ ] **Schema-snapshot tests** (`spec(§5)`): the manifest field set + the artifact field set each == a
      checked-in frozen set (the §2.5-seam freeze pins — one per model).
- [ ] **On-disk JSON contract pinned:** the serialized `.project-brain/manifest.json` keys are the frozen
      **camelCase** contract (`schemaVersion`, `ingestedFromSha`, …). A `model_dump(by_alias=True)` round-trip
      test pins those exact JSON keys (the on-disk format other tools/versions read).
- [ ] `ingestedFromSha` documented as **derived** (from the version tag); the model docstring states the
      manifest is a derived projection (rebuilt-from-dataset, reconciled-at-startup), NOT canonical.
- [ ] No inline `now()`/`uuid4`; terminal identity strings (`project_id`, `source_repo`, hashes) `min_length=1`.
- [ ] `artifacts: list[ManifestArtifact]`; an artifact carries `path·content_hash·doc_type·producer·ownership`.
- [ ] `/preflight` clean (`uv run mypy .`); `-W error` import clean.
- [ ] Cross-doc: orchestrator reconciles the Appendix-A manifest row to the 12-field union (Step-9).

## Wiring / entry point (Step 7.5)
none — wiring lands in Phase 2/3. The manifest is a derived projection with no production entry point this
slice: it is first **written/rebuilt** by the Phase-3 ingest/writer (projected from the dataset) and
**reconciled** at startup; the Phase-1.2c2 registry is built by scanning manifests. Exported from `core/model/`.

## Files expected to touch
**New:**
- `core/model/manifest.py` — `ManifestArtifact` + `ProjectManifest`.
- `core/tests/model/test_manifest.py` — incl. the two `spec(§5)` snapshots + the by-alias JSON-key test.

## RED test outline (Step 2)
Tests in `core/tests/model/test_manifest.py` (all `spec(§5)`-tagged, `unit`):
1. **`test_manifest_schema_snapshot`** — `set(ProjectManifest.model_fields)` == the 12-field frozen set. Freeze pin.
2. **`test_artifact_schema_snapshot`** — `set(ManifestArtifact.model_fields)` == the 5-field frozen set. Freeze pin.
3. **`test_manifest_json_keys_camelcase`** — `set(m.model_dump(by_alias=True))` == the frozen camelCase JSON-key
   set (incl. `schemaVersion`, `ingestedFromSha`). Why: the on-disk `.project-brain/manifest.json` format is a contract.
4. **`test_manifest_valid_construction`** — full construction validates + nested artifacts validate.
5. **`test_manifest_rejects_extra_field`** + **`test_artifact_rejects_extra_field`** — `extra="forbid"`.
6. **`test_manifest_is_frozen`** + **`test_artifact_is_frozen`** — `frozen=True`.
7. **`test_manifest_all_required`** + **`test_artifact_all_required`** — omit-each-field → ValidationError (LESSONS §3).
8. **`test_manifest_roundtrip`** — `model_validate_json(model_dump_json(by_alias=True))` == m (on-disk round-trip).
9. **`test_manifest_identity_min_length`** — empty `project_id`/`source_repo` rejected.

## Frozen field sets (the snapshots)
**ProjectManifest (12):** `schema_version` · `project_id` · `source_repo` · `ingested_from_sha` · `embedding_model` ·
`dimension` · `chunker_version` · `doc_format_spec_range` · `artifacts` · `staleness_pointer` · `policy_path` ·
`lance_version_tag`  *(Python snake_case; JSON camelCase via alias — see Q1)*
**ManifestArtifact (5):** `path` · `content_hash` · `doc_type` · `producer` · `ownership`

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW frozen `ProjectManifest` + `ManifestArtifact` (★ freeze-before-fork, §5/Appendix A).
- **§2.5-seam → schema-snapshot tests REQUIRED** (RED #1, #2) + the by-alias JSON-key pin (#3).
- **Orchestrator rows (Step 9):** reconcile Appendix-A manifest row 9→12 fields (integration); add `core/CLAUDE.md`
  ProjectManifest + ManifestArtifact cross-doc rows + lookup. (DATA_MODEL is a draft — note, don't re-edit.)

## Things to flag at Step 2.5
1. **JSON casing / alias (load-bearing — the on-disk contract).** Default vote: **snake_case Python fields +
   camelCase `serialization_alias`/`validation_alias`** (`populate_by_name=True`) so the model is idiomatic
   Python while `.project-brain/manifest.json` keeps its frozen camelCase keys (`schemaVersion`, `ingestedFromSha`).
   The field-name snapshot (#1) pins the **Python snake names**; the by-alias test (#3) pins the **camelCase JSON
   keys**. Alt: camelCase Python fields throughout (ugly, non-idiomatic). Confirm before GREEN.
2. **`artifacts` empty allowed?** Default vote: **yes, `[]` allowed** — R-PARTIAL (partial-ingest): ingest whatever exists;
   a doc-less repo has zero artifacts. (Do NOT `min_length=1` the list.)
3. **`staleness_pointer` / `doc_format_spec_range` / `lance_version_tag` types.** Default vote: `str` for now
   (`staleness_pointer` = a freshness ref; `doc_format_spec_range` = a version range string; `lance_version_tag`
   = the git-SHA version tag). Tighten in their consuming phases. Flag if any should be structured.
4. **`policy_path` is a path str**, not the loaded `policy.yaml` (that's 1.5). Default vote: **`str` path**.
5. **Derived vs stored `ingested_from_sha`.** It mirrors the version tag (derived). Default vote: keep it a
   field (the manifest is a serialized snapshot; it records the derived value) — but document it as derived,
   not canonical.
6. **Shadow check (LESSONS §3):** none of the field names obviously shadow BaseModel/ABCMeta — include the
   omit-each test regardless; verify no UserWarning at GREEN.

## Dependencies + sequencing
- **Depends on:** 1.2a/1.2b conceptually (the manifest's `embedding_model`/`dimension`/`lance_version_tag` mirror
  the stamp + version tag — derived consistency the writer enforces). No runtime import of 1.1.
- **Blocks:** 1.2c2 (the global registry is built by scanning manifests), Phase-3 ingest/writer (projects it),
  the later sync layer (the freshness banner reads `staleness_pointer` + the version tag).

## Estimated commit count
**1.** Two co-designed models (manifest + its artifact row) frozen together = one logical unit, one commit.
(The registry — a separate ★ model — is 1.2c2, its own commit.)

## Lessons-logged candidates anticipated
- **Architecture-doc note** — Appendix-A manifest row 9→12 reconcile; the Python-snake / JSON-camel alias mapping
  for the on-disk manifest format.
- **Convention candidate (maybe)** — "serialized-file contract models pin BOTH the Python field-name snapshot
  AND the by-alias on-disk key snapshot" — bank only if Step 9 confirms it's a recurring pattern (registry +
  policy.yaml will mirror it).

## How to invoke
1. Read end-to-end — Q1 (JSON casing/alias) is the load-bearing on-disk-contract decision; confirm before GREEN.
2. Reuse the session: `/tdd project_manifest`.
3. Step 0 → Step 1 → Step 2.5 (send the write-up + both snapshots + the camelCase JSON-key set + Q answers).
4. Step 9 — surface anything beyond the anticipated candidates.
