# /tdd brief — identity_alias_consolidation_and_hardening

## Feature
Consolidate the 11 duplicated identity-string aliases into ONE cross-cutting `core/_types.py`
`IdentityStr` (strip + min_length + **control-char/NUL rejection + max_length cap**) + a `TextStr`
for content fields, and retrofit every identity field across `model/` + `ports/` — closing the §5
validation gap (chunk = **bare `str`, zero validation**; stamp/manifest/registry = `min_length` but
**no strip**). The before-fork identity-hardening pass.

## Use case + traceability
- **Task ID:** 1.6 (atomic sub-slice **1.6a** — identity consolidation + hardening; 1.6b list→tuple + 1.6c StrictBool follow)
- **Architecture sections it implements:** `ARCHITECTURE.md §4` (parse-don't-trust at the boundary), §5 (the data-contract identity fields), §7 (the port identity fields). Applies **LESSON 7** (identity strings strip + min_length) + extends it with control-char/NUL + max_length.
- **Related context:**
  - Carry-forward (a)+(b)+(d): whitespace-strip retrofit of the 1.2 §5 fields + consolidate ONE shared `IdentityStr` + control-char/NUL + max_length cap.
  - **Current state (verified):** `chunk.py` identity fields are **bare `str`** (no min_length, no strip — predates LESSON 7); `stamp.py`/`manifest.py`/`registry.py` use `Field(min_length=1)` **without strip** (admit `"   "`); 11 files redefine `_StrippedStr`/`IdentityStr` (model: anchor/evidence/provenance/policy/mcp_contract + the §5 trio + chunk; ports: codegraph/host/events/observability/secrets/providers).
  - **DAG constraint (load-bearing):** the shared alias must live in a **cross-cutting** `core/_types.py` — NOT `core/model/_types.py`, because `ports/` importing from `model/` is a forbidden cross-sibling import (§2.5 DAG). `core/_types.py` is a cross-cutting foundational module ("cross-cutting layers can be imported from anywhere").
  - Field NAMES are unchanged → all `spec(§5)`/`spec(§7)`/`spec(§10)`/`spec(§14)` field-name + on-disk-key snapshots STAY GREEN; this is constraint-tightening only.

## Acceptance criteria (what "done" means)
- [ ] `core/_types.py` (NEW) defines `IdentityStr` = `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=IDENTITY_MAX_LEN, pattern=<reject control/NUL>)]` + `TextStr` for content (per Q2/Q4) + the named length constants. Cross-cutting (imported by both `model/` + `ports/`).
- [ ] All 11 local `_StrippedStr`/`IdentityStr` defs removed; every identity field imports `IdentityStr` from `_types`.
- [ ] **§5 gap closed:** `chunk.py` identity fields (chunk_id, project_id, source_path, producer, doc_type, anchor, content_hash, last_resolved_sha, ingested_from_sha, embedding_model_version) → `IdentityStr` (were bare `str`); `stamp`/`manifest`/`registry` identity fields → `IdentityStr` (now strip). Aliased fields keep their `alias=` (e.g. `ingestedFromSha`).
- [ ] **Content fields** `chunk.text`, `chunk.context_blurb` (optional), `providers.cited_text`, `GenerateResult.text` → `TextStr` (per Q2 — not the tight identity cap).
- [ ] New rejection tests: a control char / NUL is rejected; an over-`max_length` value is rejected; a whitespace-only value is rejected + strip applied — proven on a representative model field AND a representative port field, PLUS the newly-covered §5 fields (chunk/stamp/manifest/registry whitespace-only now rejected — previously accepted).
- [ ] **All existing 212 tests stay green** (field-name + on-disk-key snapshots unchanged; existing valid data still valid — constraint-tightening is additive-rejection).
- [ ] Out of scope (separate sub-slices): `chunk.vector`/`ProvenancePacket` `list`→`tuple` = **1.6b**; `chunk.tombstone`/policy/host bools → `StrictBool` = **1.6c**. The `mcp_contract` `get_file` path validator + `query` max_length alias stay as-is (specialized ingress — Q5).
- [ ] `/preflight` clean (canonical, visible — LESSON 5; `uv run mypy .` — D-A3).

## Wiring / entry point (Step 7.5)
**none — internal hardening of frozen contracts.** No new production entry point; the retrofit tightens existing models that Phase 2+ consumes. Reachability = the existing + new validation tests across the suite.

## Files expected to touch
**New:**
- `core/_types.py` — `IdentityStr` + `TextStr` + length constants.

**Modified (model):** `chunk.py`, `anchor.py`, `evidence.py`, `provenance.py`, `policy.py`, `mcp_contract.py`, `stamp.py`, `manifest.py`, `registry.py`.
**Modified (ports):** `codegraph.py`, `host.py`, `events.py`, `observability.py`, `secrets.py`, `providers.py`.
**Modified (tests):** add the rejection tests (per model/port touched); confirm existing snapshots stay green.

If the review surface feels too wide, **propose splitting model vs ports at Step 2.5** — I'll approve.

## RED test outline (Step 2)
1. **`test_identity_str_rejects_control_and_nul`** (`core/tests/model/test_types.py`) — `IdentityStr` rejects `\x00`, a C0 control, `\x7f`. Why: §4 parse-don't-trust + carry-forward (d).
2. **`test_identity_str_max_length`** — over `IDENTITY_MAX_LEN` rejected; at-limit accepted. Why: bounded identity (d).
3. **`test_identity_str_strips_and_rejects_whitespace_only`** — surrounding whitespace stripped; `"   "` rejected. Why: LESSON 7.
4. **`test_text_str_allows_inline_whitespace_rejects_nul`** — `TextStr` accepts `\n`/`\t` (content) but rejects `\x00`; over `TEXT_MAX_LEN` rejected. Why: Q2/Q4 (content ≠ identity).
5. **`test_chunk_identity_fields_hardened`** (`test_chunk.py`) — `chunk_id`/`project_id`/… reject empty, whitespace-only, control char (were bare `str`). Why: the §5 gap (chunk pre-LESSON-7).
6. **`test_stamp_manifest_registry_strip`** — a representative §5 identity field strips + rejects whitespace-only (was `min_length` only). Why: the §5 strip gap.
7. **`test_port_identity_field_hardened`** — a representative port field (e.g. `SecretRef.service`) rejects a control char (proves ports use the shared hardened alias). Why: consolidation + hardening.
8. **(implicit) full suite green** — run all 212 + the new tests; snapshots unchanged.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** **none** — no field added/removed/renamed; field-name + on-disk-key snapshots unchanged. This is constraint-tightening on existing fields.
- **Orchestrator doc rows to write hot:** minimal — the `core/CLAUDE.md` cross-doc rows already cite "strip+min_length (LESSON 7)"; I'll refine the relevant notes to "+control-char/max_length (1.6a)" + add the `core/_types.py` shared-alias note to the module-layout at /orchestrate-end. No Appendix-A field change.
- **§2.5-seam:** the frozen contracts are touched but **shape-unchanged** — no new schema-snapshot needed (the existing ones must stay green; that IS the regression guard).

> **Orchestrator territory** (`core/CLAUDE.md` "must NOT touch"): flag at Step 9.

## Things to flag at Step 2.5
1. **Shared alias HOME.** My default vote: **`core/_types.py`** (cross-cutting; importable by `model/` + `ports/` without a forbidden `ports`→`model` cross-sibling import). Per-package (`model/_types.py` + `ports/_types.py`) is the fallback if you'd rather not introduce a root module — but it keeps two copies. (Plan's task text already corrects to `core/_types.py`.)
2. **Identity vs content split.** My default vote: **two aliases** — `IdentityStr` (tight: strip + min_length + reject ALL control/NUL + cap ~1024) for ids/paths/SHAs/markers; `TextStr` (strip + min_length + reject NUL + allow `\t\n\r` + cap ~8192) for `chunk.text`/`context_blurb`/`cited_text`/`GenerateResult.text` (model output / cited spans — legitimately multi-line). Confirm the content-field list (I have: chunk.text, chunk.context_blurb, providers.cited_text, GenerateResult.text; everything else identity, incl. provenance `citations` file:line tokens + `index_freshness`).
3. **`max_length` values.** My default vote: `IDENTITY_MAX_LEN = 1024`, `TEXT_MAX_LEN = 8192` — well above any real id/path/SHA / cited span, below DoS. Push back with better numbers.
4. **Control-char mechanism.** My default vote: a `pattern` in `StringConstraints` (e.g. `IdentityStr` rejects `[\x00-\x1f\x7f]`; `TextStr` rejects `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]` so `\t\n\r` pass) — pure declarative, applied post-strip. Confirm the pattern is checked after strip + the exact ranges (or use an `AfterValidator` if cleaner).
5. **Specialized ingress aliases — leave as-is?** My default vote: **leave** `mcp_contract`'s `get_file` path `AfterValidator` (the ASCII allow-list) + the `query` `max_length=MAX_QUERY_LEN` alias untouched — they're purpose-built ingress validators, not generic identities. `IdentityStr` is for plain identity fields. (`mcp_contract`'s plain identity fields like `project_id` DO move to `IdentityStr`.)
6. **Slice size — keep whole, or split model/ports?** My default vote: **one slice** (the consolidation is atomic + mechanical + bisectable as a unit). If the diff is too large to review well, split model (incl. the critical chunk/§5 gap) from ports — your call at Step 2.5.

## Dependencies + sequencing
- **Depends on:** 1.2/1.3/1.4/1.5 (all the frozen contracts being hardened — landed).
- **Blocks:** nothing downstream forks until /phase-exit 1; 1.6b (list→tuple) + 1.6c (StrictBool) are independent siblings (any order). Whitespace/control-char-loose identity in a frozen cross-track contract post-fork = a Finding — so this MUST land before /phase-exit 1.

## Estimated commit count
**1.** The identity consolidation + hardening is one atomic, mechanical change (a half-consolidated state is worse to bisect). Not a safety-invariant pin per se, but a wide frozen-contract retrofit → keep it its own commit (don't bundle with 1.6b/1.6c).

## Lessons-logged candidates anticipated
- **Convention candidate** — "shared cross-cutting types (the identity/text aliases) live in `core/_types.py`, importable by both `model/` and `ports/` without a cross-sibling violation; identity vs content get distinct hardened aliases (tight cap + reject-all-control vs larger cap + allow `\t\n\r`)." (extends LESSON 7)
- **Architecture-doc note candidate** — add `core/_types.py` to the `core/CLAUDE.md` module-layout (the cross-cutting foundation).
- **Future TODO** — none expected (the remaining sweep items are 1.6b/1.6c).

## How to invoke
1. Read this brief end-to-end — esp. Q1 (alias home/DAG), Q2 (identity vs content), Q6 (slice size).
2. Run **`/tdd identity_alias_consolidation_and_hardening`**.
3. **Step 0/1** — confirm restate + the wide file list (15 files + new `_types.py`).
4. **Step 2.5** — send the test-design write-up + answer the 6 Qs (+ propose a model/ports split if warranted); wait for `APPROVED.` before GREEN.
5. **Step 9** — confirm snapshots stayed green + flag the `core/_types.py` module-layout note.
