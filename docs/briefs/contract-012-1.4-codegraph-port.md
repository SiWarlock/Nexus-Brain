# /tdd brief — codegraph_port_contract

## Feature
Freeze the `CodeGraphPort` (§7) — the read-only structural-graph seam over the external CodeGraph (`=1.0.1`): `query(kind, sym)` over a closed `CodeGraphQueryKind` set, the `CODEGRAPH_DIR` resolver, the `schema_versions >= 5` gate, and the `FakeCodeGraph` double. Bakes in the Phase-0 spike-0.2 corrections (D-A4). Third Phase-1.4 slice.

## Use case + traceability
- **Task ID:** 1.4 (slice **1.4c** — CodeGraphPort; Event/Secret/Observability = 1.4d next)
- **Architecture sections it implements:** `ARCHITECTURE.md §7` (the `CodeGraphPort` signature: `query(kind, sym)` over CLI shell-out, 5-table reads, `schema_versions` assert, `CODEGRAPH_DIR`-aware, tree-sitter fallback). §2.5 (seam → schema-snapshot for the result/enum). Appendix-A:220 (CodeGraphPort row).
- **Related context:** **spike 0.2 / D-A4** (`ci/probes/codegraph_coldiff.md`) — the live-tool corrections this brief MUST reflect; forbidden-pattern rule 5 + D-27 (resolve via `CODEGRAPH_DIR`, query table `nodes`, no hardcoded `.codegraph/`, no `codegraph_trace`/`codegraph_context`). Mirrors the HostPort (1.4a) scoping: freeze the Protocol + enum + deterministic helpers + Fake; the real CLI shell-out adapter defers to Phase-3 (federation/retrieval consumers). Uses `tuple[…]` for any collection field (LESSON 8 refinement).

## Acceptance criteria (what "done" means)
- [ ] `CodeGraphPort` is a `@runtime_checkable Protocol`: `query(kind: CodeGraphQueryKind, sym: str) -> CodeGraphResult` (+ the documented contract: a real adapter asserts `schema_versions` + resolves `CODEGRAPH_DIR` + version-gates + tree-sitter-falls-back — see Wiring).
- [ ] `CodeGraphQueryKind` is a closed `StrEnum` with exactly 5 values `{explore, node, callers, callees, search}`, pinned by a membership snapshot (LESSON 6).
- [ ] **Spike-0.2 Risk-2 pinned:** each kind maps to its 1.0.1 CLI command — `explore`/`node`/`callers`/`callees` map to the same verb; **`search` maps to `query`** (NOT `search` — no such command). Pin the mapping (`kind.cli_command`) by test.
- [ ] **Spike-0.2 Risk-1 pinned:** a schema-gate helper asserts `max_schema_version >= 5` (NOT `= 1`) — forward-safe (`>= 5` accepts 6+); `< 5` raises a clear error.
- [ ] **`CODEGRAPH_DIR` resolver** (pure, spike §5): default `.codegraph`; a valid single-path-segment override is accepted; an invalid value (contains a separator / `.` / `..` / is absolute) falls back to `.codegraph` (with the value rejected). Frozen + tested.
- [ ] `CodeGraphResult` is a frozen Pydantic v2 type (`frozen=True`, `extra="forbid"`) pinned by a `spec(§7)` schema-snapshot; the structured per-kind output parse is **deferred to Phase-3** (spike Risk-4 — populated-index output shape unverified); collection fields use `tuple[…]`.
- [ ] `FakeCodeGraph` (in `core/testing/fakes.py`) is a faithful deterministic double (canned results per kind; configurable; `*_conform` isinstance test) — LESSON 1.
- [ ] **Forbidden-pattern compliance:** the module hardcodes no `.codegraph/` literal (resolves via the `CODEGRAPH_DIR` resolver) and references no `codegraph_trace`/`codegraph_context` (rule 5 / D-27).
- [ ] String fields strip+min_length (LESSON 7); all unit tests in `core/tests/ports/test_codegraph.py` pass; `/preflight` clean (`mypy .`).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + confirms/annotates Appendix-A:220 with the spike-0.2 corrections).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 3 (federation/retrieval).** `CodeGraphPort` is a freeze-before-fork read-only seam; no core module queries the graph yet. **The real CLI shell-out adapter is Phase-3** (it needs the live `.codegraph` store + a seeded fixture to verify populated-index output shapes, spike Risk-4): it shells out the `kind.cli_command` verbs (`-j` JSON for `query`/`callers`), **version-gates** (`codegraph --version >= 1.0.1` fail-fast — the system binary is 0.9.7 and lacks `explore`/`node`; OR routes via the 1.0.1 MCP daemon, spike Risk-3), asserts `schema_versions >= 5` against the real DB, and **tree-sitter-falls-back** when CodeGraph is down. This slice freezes the interface + enum + the pure helpers (CODEGRAPH_DIR, schema-gate) + the Fake — the freeze-before-fork need. Exported as `ports.codegraph`. Not a tested-but-unwired gap.

## Files expected to touch
**New:**
- `core/ports/codegraph.py` — `CodeGraphPort` Protocol + `CodeGraphQueryKind` StrEnum (+ `cli_command` mapping) + `CodeGraphResult` + the `CODEGRAPH_DIR` resolver + the schema-gate helper.
- `core/tests/ports/test_codegraph.py` — conformance + enum/mapping snapshots + resolver + schema-gate + Fake fidelity.

**Modified:**
- `core/testing/fakes.py` — add `FakeCodeGraph`.

**Orchestrator territory (flag at Step 9):** `core/CLAUDE.md` row, `ARCHITECTURE.md` Appendix-A:220.

## RED test outline (Step 2)
Tests in `core/tests/ports/test_codegraph.py` (`pytestmark = pytest.mark.unit`; `from ports.codegraph import CodeGraphPort, CodeGraphQueryKind, CodeGraphResult, resolve_codegraph_dir, assert_schema_compatible`; `from testing.fakes import FakeCodeGraph`):

1. **`test_codegraph_protocol_conformance`** — Asserts: `isinstance(FakeCodeGraph(...), CodeGraphPort)`. Why: LESSON 1.
2. **`test_query_kind_values`** — Asserts: `{k.value for k in CodeGraphQueryKind} == {"explore","node","callers","callees","search"}`. Why: LESSON 6 closed set (§7/Appendix-A:220).
3. **`test_query_kind_cli_mapping`** — Asserts: `CodeGraphQueryKind.search.cli_command == "query"`; the other 4 map to their own verb. Why: **spike-0.2 Risk-2** (`search`→`query`, no `codegraph search` exists).
4. **`test_schema_gate`** — Asserts: `assert_schema_compatible(5)` + `(6)` pass; `(4)`/`(1)` raise. Why: **spike-0.2 Risk-1** (`>= 5`, forward-safe; NOT `= 1`).
5. **`test_codegraph_dir_default`** — Asserts: no/empty `CODEGRAPH_DIR` → `".codegraph"`. Why: spike §5 default.
6. **`test_codegraph_dir_valid_override`** — Asserts: a single-segment value (e.g. `"cg_index"`) is accepted. Why: spike §5.
7. **`test_codegraph_dir_invalid_fallback`** — Asserts: a value with a separator / `.` / `..` / absolute path → falls back to `".codegraph"` (rejects the value). Why: spike §5 (path-segment containment).
8. **`test_codegraph_result_snapshot`** — Asserts: `set(CodeGraphResult.model_fields) == EXPECTED`; frozen + extra-forbid; collection fields are `tuple`. Why: §2.5-seam `spec(§7)` (shape pinned; structured parse Phase-3-deferred).
9. **`test_query_contract`** — Asserts: `FakeCodeGraph.query(kind, sym) -> CodeGraphResult`. Why: §7 port shape.
10. **`test_fakecodegraph_fidelity`** — Asserts: deterministic canned results; same input → same result; configurable per kind (LESSON 1).
11. **`test_no_hardcoded_codegraph_path`** — Asserts: the `ports/codegraph.py` source contains no literal `.codegraph/` outside the resolver's default constant + no `codegraph_trace`/`codegraph_context`. Why: forbidden-rule 5 / D-27 (a focused static check on the one module).
12. **`test_codegraph_result_strip_identity`** — Asserts: result string fields strip + reject empty/ws. Why: LESSON 7.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW port `CodeGraphPort` + `CodeGraphQueryKind` + `CodeGraphResult` + the resolver/gate helpers — §7/Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc table — NEW `CodeGraphPort` row (behavioral Protocol; 5-value `CodeGraphQueryKind` + the `search→query` mapping; `CODEGRAPH_DIR` resolver; `schema_versions >= 5` gate; result Phase-3-parse-deferred; FakeCodeGraph; pin `test_codegraph.py`).
  - `ARCHITECTURE.md` Appendix-A:220 — reconcile the row with the **spike-0.2 corrections** (`schema_versions >= 5` not `=1`; `search`→`query`; version `>= 1.0.1` fail-fast / MCP-route; real adapter + output-parse Phase-3) — these correct the plan's stale `=1`/`search` values (D-A4, already lead-acknowledged). Orchestrator writes hot.
- **§2.5-seam:** `CodeGraphResult` + `CodeGraphQueryKind` cross into federation/retrieval → snapshots (#2/#8).

## Things to flag at Step 2.5
1. **Real CLI shell-out adapter scope — defer to Phase-3?** Default vote: **YES** (HostPort precedent). 1.4c freezes the Protocol + enum (+ cli_command) + `CODEGRAPH_DIR` resolver + schema-gate helper + `FakeCodeGraph`; the real adapter (subprocess shell-out, version fail-fast, schema-assert-vs-real-DB, output parsing, tree-sitter fallback) lands in Phase-3 where federation/retrieval consume it + a seeded fixture exists to verify output shapes (spike Risk-4). If you'd ship a minimal real adapter now, ping `TWEAK` — my vote keeps it to the pure helpers + Fake to avoid an unverifiable output parser.
2. **`kind.cli_command` mapping — on the enum vs a separate dict?** Default vote: **on the enum** (a `cli_command` property/lookup) — keeps the spike-verified mapping co-located with the kind + test-pinned (the `search→query` correction is load-bearing; it belongs with the kind, not buried in the deferred adapter).
3. **`CodeGraphResult` shape — minimal/raw now?** Default vote: **minimal** — `{kind, items: tuple[...], ...}` or a raw passthrough; the structured per-kind parse defers to Phase-3 (Risk-4). Freeze the shell + the snapshot; enrich additively. Flag your preferred minimal shape.
4. **schema-gate + CODEGRAPH_DIR as module-level pure functions vs methods on a base adapter?** Default vote: **module-level pure functions** (`assert_schema_compatible(max_version)`, `resolve_codegraph_dir(env_value)`) — deterministic, testable without a real adapter, reusable by the Phase-3 adapter + the MCP-route path. (No base class needed yet.)
5. **Version fail-fast (`>= 1.0.1`) — freeze a pure comparator now or defer?** Default vote: **defer the live `codegraph --version` check to the Phase-3 adapter** (it needs subprocess); optionally freeze a pure `is_version_supported(ver_str) -> bool` comparator now if cheap. Your call — minimal is fine.

## Dependencies + sequencing
- **Depends on:** 1.1 port pattern. Independent of HostPort/providers/1.2/1.3. Spike-0.2 (landed, `ci/probes/codegraph_coldiff.md`).
- **Blocks:** Phase-3 federation/retrieval (the real adapter + graph tools); parallel-eligible with 1.4d.

## Estimated commit count
**1.** One focused port (CodeGraphPort + enum + helpers + Fake). Not bundled with 1.4d (distinct seam + the spike-0.2 corrections give it its own traceability).

## Lessons-logged candidates anticipated
- **Convention candidate** — likely none new (LESSON 1/6 cover the port + enum); possibly "spike-verified external-tool facts are pinned in-contract by test (the `search→query` mapping), not left to the deferred adapter."
- **Architecture-doc note candidate** — the Appendix-A:220 spike-0.2 reconciliation (schema `>=5`, `search→query`, version-gate, Phase-3 adapter).
- **Future TODO — belongs-to-phase** — (a) real CLI shell-out adapter + output parser (seeded fixture) → Phase-3; (b) version fail-fast / MCP-route → Phase-3; (c) tree-sitter fallback → Phase-3.

## How to invoke
1. **Read this brief end-to-end** + skim `ci/probes/codegraph_coldiff.md` (the spike corrections). Q1 (adapter scope) is the load-bearing one.
2. **Run `/tdd codegraph_port_contract`** (session oriented).
3. **Step 0 (Restate)** — confirm the Protocol + enum + helpers + Fake (NOT the real shell-out adapter).
4. **Step 1 (Identify files)** — `core/ports/codegraph.py` + `core/tests/ports/test_codegraph.py` + `core/testing/fakes.py`.
5. **Step 2.5** — write-up + coverage map; answer the 5 Qs. Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9** — categorized flags + the CodeGraphPort cross-doc row ask + the Appendix-A:220 spike-0.2 reconciliation + ship-ask.
