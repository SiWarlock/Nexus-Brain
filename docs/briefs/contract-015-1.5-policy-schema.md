# /tdd brief — policy_yaml_schema

## Feature
Freeze the per-project `policy.yaml` contract (§16) — the `Privacy` enum + a frozen `ProjectPolicy`
schema (providers · privacy `local|cloud` · MCP-boundary · federation visibility · session consent ·
`.brainignore`) whose **defaults are fail-CLOSED** (absent → most-restrictive local-only). The
provider *catalog* + privacy↔provider consistency are deferred to Phase 10 (freeze shape, defer
membership — the D-A11 pattern); this slice freezes the shape + the safety defaults.

## Use case + traceability
- **Task ID:** 1.5 (atomic sub-slice **1.5b** — policy.yaml; sibling of 1.5a Redactor [landed `343b6fb`] + 1.5c MCP contract)
- **Architecture sections it implements:** `ARCHITECTURE.md §16` (providers, per-project privacy — the canonical anchor for the whole policy.yaml contract per Appendix A), with in-scope touches §14 (MCP boundary section), §5 (on-disk `schema_version` migration), §4 (parse-don't-trust), §2.5 (shared-contract seam). Its other sections *feed* downstream consumers in later phases — federation visibility (Phase 6), session consent (Phase 9), `.brainignore` ingest (Phase 2), lifecycle migration (Phase 13) — but the contract itself is a §16 freeze-before-fork artifact; this brief does NOT widen Phase-1 scope.
- **Related context:**
  - Carry-forward note: **"policy model = fail-CLOSED (absent/empty/unrecognized → most-restrictive local-only)."**
  - The 1.2 serialized-file pattern: `ProjectManifest` / `Registry` (`core/model/manifest.py`, `registry.py`) — **LESSON 4 dual snapshot** (field-name + on-disk-key), `validate_by_name`/`validate_by_alias`, lenient-read/strict-write, the migration engine (`core/model/migrations.py`). Mirror it.
  - The `core/CLAUDE.md` Registry cross-doc note: *"`policy` min_length=1 (no empty privacy marker — fail-open closed; **fail-CLOSED semantics → 1.5**)"* — this is that 1.5.
  - D-A11 "freeze shape, defer externally/late-owned membership" pattern (here: the provider catalog → Phase 10). LESSON 2 (opaque ids), 4, 6, 7, 8.

## Acceptance criteria (what "done" means)
- [ ] `Privacy` is a **closed `StrEnum`** with exactly `{local, cloud}` — membership snapshot tagged `spec(§16)` (LESSON 6; §16 "explicit user choice local|cloud").
- [ ] `ProjectPolicy` is a frozen (`frozen=True`, `extra="forbid"`) top-level schema with the 6 §16 sections — `privacy`, `providers`, `mcp`, `federation`, `sessions`, `brainignore` — plus `schema_version` (forward-migration; see Q4). Field-name set pinned by a `spec(§16)` snapshot (the §2.5-seam pin).
- [ ] **Fail-CLOSED defaults (THE safety pin):** an empty/minimal policy (every optional section absent) parses to the **most-restrictive** posture — `privacy=local`, `mcp.expose=False`, `federation.visible=False`, `sessions.consent=False`, `brainignore=()`. Pinned by a dedicated test.
- [ ] **Parse-don't-trust (§4):** an unrecognized/empty `privacy` value raises `ValidationError` (not silently coerced); unknown top-level/sub-model keys rejected (`extra="forbid"`). The fail-SOFT "malformed policy → treat as most-restrictive rather than crash" is the **loader's** job (Phase 2/3 startup-reconcile), NOT this schema (see Q1).
- [ ] On-disk serialization pinned: an **on-disk-key snapshot** (LESSON 4) tagged `spec(§16)`, `validate_by_name`/`validate_by_alias` (NOT `populate_by_name`). Key convention per Q4.
- [ ] Collections are `tuple` (`brainignore: tuple[str, ...]`, default `()`), elements strip+min_length (LESSON 7/8); provider id strings opaque + min_length when present (LESSON 2/7).
- [ ] Nested sub-models coerce from `dict` (parse-don't-trust nested) + deep-frozen (LESSON 8); YAML/dict round-trip preserves equality.
- [ ] `/preflight` clean (canonical, visible — LESSON 5; `uv run mypy .` — D-A3).
- [ ] Cross-doc: flag the new `policy.yaml` cross-doc row at Step 9; flag if the field set extends the Appendix-A summary (additive reconciliation, D-A7 pattern — orchestrator writes).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2.4 / 6 / 8 / 9 / 10** (`add` writes `policy.yaml` at ingest; Phase-2 ingest reads `privacy`+`.brainignore`; Phase-8 MCP boundary reads `mcp`; Phase-6 federation reads `federation.visible`; Phase-9 sessions read `sessions.consent`; Phase-10 providers read `providers` + add the catalog/consistency validator). A frozen schema like the 1.2 manifest/registry — no Phase-1 production caller; the schema-snapshot + behavioral tests are its Phase-1 reachability.

## Files expected to touch
**New:**
- `core/model/policy.py` — `Privacy` StrEnum + `ProjectPolicy` + sub-models (`ProviderPolicy`, `McpPolicy`, `FederationPolicy`, `SessionPolicy`; names per Q3).
- `core/tests/model/test_policy.py` — the RED tests.

**Modified:** none expected (pure data model — no port/Fake).

If implementation needs files beyond this list, **flag at Step 2.5** before GREEN.

## RED test outline (Step 2) — `core/tests/model/test_policy.py`
1. **`test_privacy_values`** — `{p.value for p in Privacy} == {"local", "cloud"}`. Tag `spec(§16)`. Why: LESSON 6 + §16 closed alphabet.
2. **`test_policy_field_names_snapshot`** — top-level field-name set == checked-in snapshot. Tag `spec(§16)`. Why: §2.5-seam freeze.
3. **`test_policy_ondisk_key_snapshot`** — by-alias on-disk-key snapshot. Tag `spec(§16)`. Why: LESSON 4 (serialized contract).
4. **`test_fail_closed_defaults`** — `ProjectPolicy()` (or from `{}`) → privacy=local, mcp.expose=False, federation.visible=False, sessions.consent=False, brainignore=(). Why: **the fail-CLOSED safety pin** (carry-forward; §16 most-restrictive default — MCP/federation/session opt-ins all default off).
5. **`test_unrecognized_privacy_rejected`** — `privacy="public"` and `privacy=""` → `ValidationError`. Why: parse-don't-trust §4 (no silent coercion).
6. **`test_frozen_and_extra_forbid`** — mutation raises; an unknown key (top-level + a sub-model) raises. Why: frozen contract + `extra="forbid"`.
7. **`test_brainignore_is_tuple_immutable`** — `brainignore` is a `tuple`, elements strip+min_length, no mutable default leak. Why: LESSON 8/7.
8. **`test_provider_ids_opaque_optional`** — per-role provider fields accept opaque id strings, optional/defaulted, min_length when present. Why: LESSON 2 (opaque) + D-A11 (defer catalog).
9. **`test_nested_coercion_and_deep_frozen`** — sub-models coerce from nested `dict`; deep immutability; dict round-trip equality. Why: LESSON 8.
10. *(pending Q4)* **`test_schema_version`** — `schema_version` present, PositiveInt, on-disk key per Q4. Why: §5 forward-only migration consistency with manifest/registry.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW contract — `Privacy` enum + `ProjectPolicy` + sub-models (§16).
- **Orchestrator doc rows to write hot:** add the `policy.yaml` row to `core/CLAUDE.md` cross-doc table; confirm/reconcile the `ARCHITECTURE.md` Appendix-A "policy.yaml" row (if the frozen field set extends the summary — e.g. adding `schema_version` — that's an **additive reconciliation**, D-A7/D-A12 pattern; orchestrator adjudicates + lead-logs).
- **§2.5-seam (shared-contract) model touched?** **YES** — policy.yaml is a ★ freeze-before-fork contract read across providers/mcp/federation/sessions/ingest seams. RED **includes** the `spec(§16)` snapshot tests (field-name + on-disk-key + Privacy membership), authored this cycle.

> **Orchestrator territory** (canonical list: `core/CLAUDE.md` "must NOT touch"): flag at Step 9; orchestrator writes hot + commits at `/orchestrate-end`.

## Things to flag at Step 2.5
1. **Fail-CLOSED split — schema vs loader?** My default vote: the **schema** does restrictive defaults + parse-don't-trust reject (bad enum, extra keys); the **fail-SOFT** "malformed/unrecognized policy → most-restrictive local-only instead of crashing" lives in the **Phase-2/3 loader** (the 1.2d startup-reconcile carry-forward), not the frozen schema. Rationale: keeps the schema an honest strict parser (consistent with manifest/registry lenient-read/strict-write split); a frozen schema that silently coerces bad values hides corruption.
2. **Provider sub-model granularity?** My default vote: **opaque per-role id strings, optional** (`providers.{embedding,reranker,context,model}: str | None`) — freeze the shape, **defer the provider catalog + the privacy↔provider local|cloud consistency validator to Phase 10** (D-A11 "shape now, membership later"; the catalog doesn't exist until the Phase-10 bake-off). Rationale: avoids baking Phase-10 model names / a consistency rule the schema can't yet evaluate into a frozen contract.
3. **Top-level `privacy` only, or per-role privacy?** My default vote: **one top-level per-project `privacy: Privacy`** (§16 "per project") + a separate `providers` section. Per-role local|cloud mixing is expressed through provider selection in Phase 10, not a privacy field. Sub-model names: `ProviderPolicy`/`McpPolicy`/`FederationPolicy`/`SessionPolicy` (counter-name welcome).
4. **On-disk key convention + `schema_version`?** My default vote: **snake_case YAML keys** (user-edited file, YAML-norm) and **include `schema_version: PositiveInt`** for the §5 forward-only migration runner (consistency with manifest/registry + the 1.2 migration engine). Still pin the on-disk-key snapshot (LESSON 4) even when names==aliases. **Confirm against `core/model/migrations.py`:** if the runner keys on a specific name/case (the manifest used camelCase `schemaVersion`), match it; else snake_case.
5. **`extra="forbid"` on a user-edited file — too harsh?** My default vote: **`extra="forbid"` at the schema** (consistent with every contract; parse-don't-trust) — a typo'd key surfaces as a `ValidationError` the loader catches + fails-closed. The schema is the strict parser; leniency is the loader's. Rationale: silent ignore of unknown keys in a privacy/safety config is exactly the fail-open we're avoiding.

## Dependencies + sequencing
- **Depends on:** 1.1 (landed). The 1.2 migration engine (`migrations.py`, landed) — if `schema_version` is included (Q4). Independent of 1.5a/1.5c.
- **Blocks:** Phase 2.4 `add` (writes policy.yaml) · Phase 2 ingest (privacy + `.brainignore`) · Phase 6 federation (visibility) · Phase 8 MCP boundary (`mcp`) · Phase 9 sessions (consent) · Phase 10 providers (selection + catalog/consistency validator).

## Estimated commit count
**1.** One cohesive frozen schema. **Privacy/safety-posture contract → its own commit** (not bundled with 1.5a/1.5c).

## Lessons-logged candidates anticipated
- **Convention candidate** — "Fail-CLOSED config = most-restrictive defaults + parse-don't-trust reject at the frozen schema; the fail-SOFT 'malformed → most-restrictive' fallback belongs to the loader, not the schema."
- **Architecture-doc note candidate** — additive Appendix-A "policy.yaml" reconciliation if the field set (e.g. `schema_version`) extends the summary row (D-A7 pattern).
- **Future TODO — phase:** Phase-10 provider catalog membership + privacy↔provider local|cloud consistency validator (origin 1.5b, D-A11 pattern); Phase-8 `mcp` boundary-filter richer fields; Phase-6 federation visibility semantics; Phase-9 session-consent granularity; Phase-2/3 the policy **loader** (fail-soft + on-disk key-shape strictness — the 1.2d loader covers this).

## How to invoke
1. Read this brief end-to-end — esp. the 5 Step-2.5 questions (fail-closed split + provider granularity are the load-bearing ones).
2. Run **`/tdd policy_yaml_schema`**.
3. **Step 0/1** — confirm restate + file list.
4. **Step 2.5** — send the test-design write-up + answer the 5 Qs; wait for `APPROVED.` before GREEN. (Confirm Q4 against `migrations.py` before deciding the key case.)
5. **Step 9** — surface the cross-doc rows (incl. any additive Appendix-A reconciliation) + anything beyond the anticipated candidates.
