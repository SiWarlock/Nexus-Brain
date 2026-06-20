# /tdd brief — mcp_contract_ingress

## Feature
Freeze the **ingress half** of the §14 MCP tool contract — the `RetrievalScope` enum + the 5 tool
**param** models (`search`/`get_file`/`graph`/`list_projects`/`status`) with **positive-allow-list
ingress validation** (LESSON 10): `get_file` path shape-allow-list, bounded `query`/`top_k`, opaque
`project_id`. The result/chip/provenance shapes + policy-denied marker + streaming are 1.5c2.

## Use case + traceability
- **Task ID:** 1.5 (atomic sub-slice **1.5c1** — MCP ingress; 1.5c2 = results/markers; siblings 1.5a Redactor `343b6fb` + 1.5b policy `a9df580`)
- **Architecture sections it implements:** `ARCHITECTURE.md §14` (MCP server & trust boundary — the ingress-validation rules), Appendix A "MCP tool contract" row. In-scope touches §4 (parse-don't-trust), §2.5 (shared-contract seam).
- **Related context:**
  - Carry-forward: **"MCP contract: ingress validation MUST use positive allow-lists (LESSON 10) — `get_file` path canonicalize+contain, query/k/response bounds via Pydantic type + positive semantic check."**
  - **LESSON 10** (`core/LESSONS.md#10`) — the §14 ingress posture, established at 1.4c `resolve_codegraph_dir`: positive charset allow-list + bypass-corpus test, never a deny-list. This brief is its first MCP application.
  - **D-A14** — the un-allow-listable CodeGraph query/symbol args are argv-hardened at Phase 4.2; at THIS contract they're bounded strings (the contract bounds the input; runtime execution-containment is 4.2).
  - The §14 frozen tool set: `search`/`get_file`/`graph`/`list_projects`/`status`. The actual canonicalize-against-real-root containment + registry-scope authorization + egress redaction + loopback-token transport are the **Phase-8 boundary** (8.1/8.2) — NOT this slice (see Q2 / Wiring).
  - Mirror prior freezes: `core/model/anchor.py` / `core/ports/codegraph.py` (StrEnum + membership snapshot + allow-list validator).

## Acceptance criteria (what "done" means)
- [ ] `RetrievalScope` is a **closed `StrEnum`**; membership snapshot tagged `spec(§14)` (LESSON 6). Default alphabet `{project, portfolio}` — see Q1.
- [ ] 5 frozen param models (`frozen=True`, `extra="forbid"`), one per tool — `SearchParams`, `GetFileParams`, `GraphParams`, `ListProjectsParams`, `StatusParams` — each with a field-name snapshot tagged `spec(§14)` (the §2.5-seam pin).
- [ ] **`get_file` path = positive allow-list (THE LESSON 10 security pin):** the path **shape** is validated by a positive allow-list — accept a bounded relative path; **reject** absolute (`/…`), drive (`C:\…`), `..` traversal (incl. mid-path `a/../b`), leading `/`, NUL/control chars, the unicode fullwidth solidus (U+FF0F), empty/whitespace. Pinned by a **bypass corpus** test (mirror the 1.4c corpus). The canonicalize-against-the-real-project-root **containment** is deferred to Phase 8.2 (needs the resolved root) — documented in-code (Q2).
- [ ] **Bounded ingress (LESSON 10 / §14 "bound query/k sizes"):** `search.query` non-empty (strip) + `max_length` capped; `top_k` `PositiveInt` + `le=MAX_TOP_K` (reject 0 / negative / over-cap); bounds live as named module constants (`MAX_TOP_K`, `MAX_QUERY_LEN`) so a future loosening is visible + test-pinned.
- [ ] `project_id` is an opaque identity string (strip + min_length; registry-authorization is Phase 8) — required where the tool needs it (`get_file`), optional where scope can default (`search`/`status`).
- [ ] `graph.kind` typed per Q3 (default: bounded str, Phase-8 maps to `CodeGraphQueryKind` — NO cross-sibling import of `ports` from `model`).
- [ ] Parse-don't-trust (§4): unknown keys rejected (`extra="forbid"`); malformed bounds raise `ValidationError` (no silent clamp).
- [ ] `/preflight` clean (canonical, visible — LESSON 5; `uv run mypy .` — D-A3).
- [ ] Cross-doc: flag at Step 9 — the `mcp_contract` cross-doc row + Appendix-A reconciliation land at **1.5c2** (when the contract is complete); c1 flags "row pending c2."

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 8** (8.1 FastMCP server builds tools from these param models; 8.2 the trust boundary does the runtime canonicalize-against-root containment + registry-scope authorization + egress redaction + loopback-token transport). A frozen contract like the 1.4 ports — no Phase-1 caller; the snapshot + ingress-validation tests are its Phase-1 reachability.

## Files expected to touch
**New:**
- `core/model/mcp_contract.py` — `RetrievalScope` + 5 param models + the `get_file` path allow-list validator + `MAX_TOP_K`/`MAX_QUERY_LEN`. (1.5c2 extends this file with results/markers.)
- `core/tests/model/test_mcp_contract.py` — the RED tests (1.5c2 extends).

**Modified:** none expected (pure data model; no port/Fake).

If implementation needs files beyond this list, **flag at Step 2.5** before GREEN.

## RED test outline (Step 2) — `core/tests/model/test_mcp_contract.py`
1. **`test_retrieval_scope_values`** — `{s.value for s in RetrievalScope} == {"project", "portfolio"}` (per Q1). Tag `spec(§14)`. Why: LESSON 6 closed alphabet.
2. **`test_param_field_name_snapshots`** — each of the 5 param models' field-name set == checked-in snapshot. Tag `spec(§14)`. Why: §2.5-seam freeze.
3. **`test_get_file_path_allowlist`** — **the LESSON 10 pin.** A bypass corpus — `/etc/passwd`, `../x`, `a/../../b`, `C:\\x`, `/leading`, `"x\x00y"`, control chars, `пример` is fine but `a／b` (U+FF0F) rejected, `""`, `"   "` — all rejected; a valid relative path (`src/app.py`) accepted. Why: §14 ingress + LESSON 10 (positive allow-list, bypass corpus).
4. **`test_search_params_bounds`** — `query` non-empty + over-`MAX_QUERY_LEN` rejected; `top_k` rejects 0/negative/over-`MAX_TOP_K`, accepts in-range; `scope` required `RetrievalScope`; `project_id` optional. Why: §14 bound query/k.
5. **`test_get_file_requires_project_id`** — `project_id` required (omitting raises). Why: get_file is project-scoped.
6. **`test_graph_params`** — `query` bounded; `kind` per Q3; `project_id` required. Why: §14 graph tool params.
7. **`test_list_projects_and_status_params`** — `ListProjectsParams` minimal/no-required; `StatusParams.project_id` optional. Why: §14 tool set completeness.
8. **`test_frozen_and_extra_forbid`** — every param model frozen (mutation raises) + unknown key rejected. Why: parse-don't-trust §4.
9. **`test_bounds_constants`** — `MAX_TOP_K` / `MAX_QUERY_LEN` exist + equal the documented values. Why: a future loosening of an ingress bound must be a visible, test-breaking change (LESSON 10 spirit).

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW (partial) — `RetrievalScope` + 5 param models (§14). The result/marker half lands in 1.5c2.
- **Orchestrator doc rows to write hot:** the `mcp_contract` cross-doc row in `core/CLAUDE.md` + the Appendix-A "MCP tool contract" reconciliation are written at **1.5c2** (the complete contract) to avoid a double-write; c1 Step-9 just flags "pending c2."
- **§2.5-seam (shared-contract) model touched?** **YES** — the MCP contract is a ★ freeze-before-fork trust-boundary contract. RED **includes** the `spec(§14)` snapshots (RetrievalScope membership + the 5 param field-name snapshots), authored this cycle.

> **Orchestrator territory** (canonical list: `core/CLAUDE.md` "must NOT touch"): flag at Step 9; orchestrator writes hot + commits at `/orchestrate-end`.

## Things to flag at Step 2.5
1. **`RetrievalScope` alphabet?** My default vote: **`{project, portfolio}`** — the breadth dimension (single project vs federated portfolio; `project_id` is a *separate* scoping param). This is OUR call (not externally-owned), definable now, narrowable additively (StrEnum ⊂ str). Alternative (content-type scope) seems less aligned with §14's "scope + project_id + top-k" triad. Confirm or propose values.
2. **`get_file` validation depth at the contract?** My default vote: **freeze the path-SHAPE positive allow-list now** (relative, no `..`/absolute/NUL/control/unicode-sep, charset-bounded) + **defer the canonicalize-against-the-real-project-root containment to Phase 8.2** (it needs the resolved root, unavailable at the frozen-contract layer). Mirrors 1.4c `resolve_codegraph_dir` (shape now) + D-A14 (runtime containment at the boundary phase). Document the deferral in-code.
3. **`graph.kind` typing?** My default vote: **a bounded `str | None`**, with Phase 8 mapping it to `CodeGraphQueryKind` — because `model/` must NOT import `ports/` (cross-sibling import is forbidden by the §2.5 DAG), and an MCP-local Literal mirroring the 5 values would silently drift from the frozen `CodeGraphQueryKind`. (If you'd rather a Literal mirror with a comment tying it to 1.4c, say so — but the bounded-str + Phase-8-map avoids the drift.)
4. **Ingress bound *values* (`MAX_TOP_K`, `MAX_QUERY_LEN`)?** My default vote: define them as named constants with sane defaults (e.g. `MAX_TOP_K = 100`, `MAX_QUERY_LEN = 4096`) — the POINT is *bounded* (LESSON 10); the exact numbers are tunable and test-pinned. Push back with better numbers if you have them.
5. **5 separate param models vs one unified params union?** My default vote: **5 separate frozen models** (one per tool) — cleaner typing + per-tool snapshots; matches the per-port granularity of 1.4.

## Dependencies + sequencing
- **Depends on:** 1.1 (landed). Independent of 1.5a/1.5b. (No import of `ports`/`CodeGraphQueryKind` — DAG.)
- **Blocks:** 1.5c2 (results/markers, same file) · Phase 8.1 (server builds tools from these params) · Phase 8.2 (boundary: runtime containment + authorization + egress).

## Estimated commit count
**1.** The ingress param contract. **The `get_file` LESSON-10 path allow-list is the security pin → its own commit** (separate from 1.5c2's result plumbing; root `CLAUDE.md` "safety-critical pin gets its own commit").

## Lessons-logged candidates anticipated
- **Convention candidate** — "Freeze the ingress input-SHAPE allow-list at the contract; defer runtime containment/authorization (needs the resolved root + registry) to the boundary phase" (extends LESSON 10 — shape-now, runtime-containment-at-the-boundary).
- **Architecture-doc note candidate** — Appendix-A "MCP tool contract" reconciliation at 1.5c2 (the complete contract; additive if the frozen field set extends the summary).
- **Future TODO — phase 8:** the runtime `get_file` canonicalize-against-root containment + registry-scope authorization + egress redaction/policy-filter + loopback-token transport (8.2); the `graph.kind` → `CodeGraphQueryKind` mapping (8.1); response-size bound (egress — 1.5c2/8.2).

## How to invoke
1. Read this brief end-to-end — esp. Step-2.5 Q1 (scope alphabet) + Q2 (validation depth) + Q3 (graph.kind), the load-bearing ones.
2. Run **`/tdd mcp_contract_ingress`**.
3. **Step 0/1** — confirm restate + file list.
4. **Step 2.5** — send the test-design write-up + answer the 5 Qs; wait for `APPROVED.` before GREEN.
5. **Step 9** — flag the cross-doc rows as pending-1.5c2 + anything beyond the anticipated candidates.
