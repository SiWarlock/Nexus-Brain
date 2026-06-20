# /tdd brief — redactor_interface_freeze

## Feature
Freeze the `Redactor` boundary contract (§18, Key safety rule #2) — the `Sink` enum + a
`@runtime_checkable Redactor` Protocol + a contract-faithful `FakeRedactor` double. This is the
Phase-1 **signature + behavioral-invariant freeze** that the Phase-2.3 engine implements; the
catchable-set recall/FP envelope is **documented** here (single source of truth = the spike's
`harness.py`) but **enforced** at 2.3 (its CI fuzz gate).

## Use case + traceability
- **Task ID:** 1.5 (atomic sub-slice **1.5a** — Redactor interface; 1.5b policy.yaml + 1.5c MCP contract follow as independent sub-slices)
- **Architecture sections it implements:** `ARCHITECTURE.md §18` (security & trust boundaries — the redaction gate), Appendix A "Redactor" row.
- **Related context:**
  - **Spike 0.1** `docs/audits/redaction-envelope.md` §7.1 — the *exact* interface contract this slice freezes (sink enum, accepted-residual docstring, envelope, behavioral contracts). Read it first.
  - **D-A5 / D-A6 (OWNER-DEFERRED — do NOT re-decide):** per-sink strictness (FLAG-4) + the 95%/5% threshold confirmation are parked for the owner at Phase 2.3. The signature must *accommodate* both, decide neither.
  - LESSON 1 (Protocol + real + Fake), LESSON 6 (closed alphabet = StrEnum + membership snapshot), LESSON 7 (identity-string constraints — n/a to a free payload, see Q3), LESSON 11 (a safety contract pins its dangerous-case behavior). Mirror the 1.4 provider/codegraph port pattern (`core/ports/providers.py`, `core/ports/codegraph.py`).

## Acceptance criteria (what "done" means)
- [ ] `Sink` is a **closed `StrEnum`** with **exactly** `{persist, mcp_egress, cloud_egress}` — membership pinned by a snapshot test tagged `spec(§18)` (LESSON 6; §18 "runs at all three sinks").
- [ ] `Redactor` is a `@runtime_checkable Protocol` with the frozen signature `redact(self, payload: str, sink: Sink) -> str` — no other required method.
- [ ] The `Redactor` (and/or `redact`) **docstring enumerates the 3 accepted-residual classes by name** — git-SHA hex · adversarial <20-char split · sub-20-char JSON — and cites **§18 / C-11**; AND documents the envelope (**recall ≥95% / FP ≤5% / git-SHA FP = 0%**) naming the spike `ci/eval/redaction_fuzz/harness.py` constants (`PROPOSED_RECALL_FLOOR` / `PROPOSED_FP_CEILING`) as the single source of truth. **No `import` of `ci/`** — core must not depend on ci/ (import-direction; the docstring references, never imports). (Spike §7.1.2–3.)
- [ ] `FakeRedactor` in `core/testing/fakes.py` satisfies `isinstance(FakeRedactor(), Redactor)` and honors every behavioral invariant below (LESSON 1; deterministic, in-memory only).
- [ ] **Behavioral invariants** pinned as deterministic tests against `FakeRedactor` (spike §7.1.4):
  - [ ] **Idempotent** — `redact(redact(p, s), s) == redact(p, s)` for every sink, multiple payloads.
  - [ ] **Never raises** — on any input string (empty, control chars / NUL, very long, non-ASCII, multi-line env-dump-shaped).
  - [ ] **Git-SHA passthrough (zero-tolerance)** — a 40-char *and* a 64-char hex SHA appear (case-insensitive) in the output on **all three sinks** (redacting a SHA would break the LanceDB git-SHA version tag + `last_resolved_sha` + manifest integrity — §18/D-14, architecture-level, not just a quality metric).
  - [ ] **Pure / no I/O** — by construction (Fake is in-memory; no network, no FS); documented.
  - [ ] **Returns `str`** for `str` input, for each sink.
- [ ] **D-A5/D-A6 deferral honored:** the signature is sink-parameterized so it accommodates BOTH uniform and cloud-stricter behavior; **no per-sink strictness behavior is frozen** in this slice (owner-parked).
- [ ] `/preflight` clean (run the **canonical** gate visibly — LESSON 5; `uv run mypy .`, never `mypy core` — D-A3).
- [ ] Cross-doc: flag the new `Redactor` cross-doc row at Step 9 (orchestrator writes it + confirms the Appendix-A row matches — no arch field change expected).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2.3** (`core/ingest/redactor.py` implements this interface; Phase-2 ingest injects a `Redactor` at the persist sink, Phase-4.2 at hydration egress, Phase-8 at MCP egress). This is a **frozen interface**, exactly like the 1.4 ports — it has no production caller in Phase 1; the `FakeRedactor` is the double downstream consumers inject. Reachability in Phase 1 = the Fake satisfying the Protocol + the behavioral tests.

## Files expected to touch
**New:**
- `core/model/redactor_iface.py` — `Sink` StrEnum + `Redactor` Protocol + the accepted-residual / envelope docstring. (Per the plan's `core/model/{...}` Files line; the *engine* is `core/ingest/redactor.py` in 2.3.)
- `core/tests/model/test_redactor_iface.py` — the RED tests.

**Modified:**
- `core/testing/fakes.py` — add `FakeRedactor` (the canonical Fake home; mirror the existing provider/codegraph fakes).

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2) — `core/tests/model/test_redactor_iface.py`
1. **`test_redactor_protocol_conformance`** — `assert isinstance(FakeRedactor(), Redactor)`.
   - Why: LESSON 1 (Fake structurally satisfies the runtime_checkable port).
2. **`test_sink_values`** — `{s.value for s in Sink} == {"persist", "mcp_egress", "cloud_egress"}`.
   - Why: LESSON 6 + §18 three-sink closed alphabet. **Tag `spec(§18)`** — this is the §2.5-seam schema-snapshot for this contract.
3. **`test_redact_accepts_all_sinks`** — `redact(payload, s)` returns a `str` for each `Sink` member.
   - Why: §18 "the redactor runs at all three sinks."
4. **`test_redact_is_idempotent`** — `redact(redact(p, s), s) == redact(p, s)` across sinks + payloads.
   - Why: spike §7.1.4 idempotence (`test_redact_is_idempotent`).
5. **`test_redact_never_raises`** — adversarial inputs: `""`, NUL/control chars, a long string, non-ASCII, a multi-line env-dump-shaped blob.
   - Why: spike §7.1.4 never-raises (a redactor that throws is a DoS at the ingest/egress boundary).
6. **`test_git_sha_passthrough`** — a 40-char and a 64-char hex SHA survive (case-insensitive) on all three sinks.
   - Why: zero-tolerance sub-invariant §18/D-14 (redacting a SHA breaks LanceDB version tagging + provenance).
7. **`test_fake_redactor_is_observably_applied`** *(see Q5)* — `FakeRedactor` removes an obvious prefix token (e.g. a `ghp_…` PAT) so downstream "was the redactor applied?" tests have a signal — while NOT claiming the catchable-set recall envelope.
   - Why: keeps the Fake a *useful, contract-faithful* double, not a silent identity.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW contract — `Sink` StrEnum + `Redactor` behavioral Protocol. Behavioral Protocol → **no field-snapshot** (like the 1.4 providers/codegraph ports); the **`Sink` membership snapshot IS the `spec(§18)` pin**.
- **Orchestrator doc rows to write hot:** add the `Redactor` row to the `core/CLAUDE.md` cross-doc table (the `ARCHITECTURE.md` Appendix-A "Redactor" row already exists — orchestrator confirms it matches; no field change expected).
- **§2.5-seam (shared-contract) model touched?** **YES** — the Redactor is a ★ freeze-before-fork contract + a fan-in hub crossing §2.5 seams. The RED outline therefore **includes the `Sink` membership snapshot test (`test_sink_values`, tagged `spec(§18)`)** — authored this same `/tdd` cycle, reviewed at Step 2.5.

> **Orchestrator territory** (canonical list: `core/CLAUDE.md` "must NOT touch"): flag at Step 9; the orchestrator writes hot + commits at `/orchestrate-end`.

## Things to flag at Step 2.5
1. **Behavioral Protocol vs frozen-model shape?** A `@runtime_checkable Protocol` (behavioral, no fields) vs a Pydantic model. My default vote: **behavioral `@runtime_checkable Protocol`** — the Redactor has *behavior*, not fields; matches LESSON 1 + the 1.4 provider/codegraph ports; the real engine is 2.3. The only snapshot surface is the `Sink` StrEnum.
2. **Envelope constants — reference or import?** My default vote: **docstring documents the envelope + names `ci/eval/redaction_fuzz/harness.py` as the single source of truth, but the interface does NOT import `ci/`** (core must not depend on ci/ — import-direction law; enforcement is the 2.3 CI gate). Spike §7.1.2–3.
3. **Payload type `str -> str`, or widen to bytes/structured?** My default vote: **exactly `redact(payload: str, sink: Sink) -> str`** (the spike-frozen signature). Binary / encoding-aware forms are FLAG-1/FLAG-3 → Phase-2.3; don't widen pre-engine. (Note: `payload` is a *free* content string, NOT an identity field — LESSON 7 strip/min_length does **not** apply; redacting must tolerate empty + whitespace + control chars, see test 5.)
4. **Per-sink strictness (FLAG-4 / D-A5)?** My default vote: **freeze NO per-sink behavior** — the sink-parameterized signature keeps both uniform and cloud-stricter open; the strictness *policy* is **owner-deferred to Phase 2.3 + policy.yaml (D-A5)**. Do **not** re-decide — just confirm `sink` is a parameter so both paths stay open.
5. **`FakeRedactor`: minimal token-strip double, or pure identity?** My default vote: **a minimal DETERMINISTIC double that observably strips a couple of obvious prefix tokens** (e.g. `ghp_…`, `sk-…`) while honoring every behavioral invariant (idempotent / never-raises / git-SHA-passthrough / pure) — explicitly docstring'd as a **TEST DOUBLE, not the catchable-set engine** (makes no recall/FP claim). Rationale: a pure-identity Fake is "a redactor that redacts nothing" — fragile when injected as a stand-in; a token-strip Fake mirrors the spike stub's spirit and gives downstream a real "was-it-applied" signal. (A pure-identity Fake also satisfies the interface contract — counter-vote fine if you prefer minimalism; if so, drop test 7.)

## Dependencies + sequencing
- **Depends on:** Phase-0 spike 0.1 (envelope — DONE, `docs/audits/redaction-envelope.md`). Task 1.1 (the `core/testing/fakes.py` Fake home — landed). No other contract dependency.
- **Blocks:** Phase 2.3 redactor engine (implements this iface) · Phase 2 ingest (injects at persist) · Phase 4.2 hydration egress · Phase 8 MCP egress. Siblings 1.5b (policy.yaml) + 1.5c (MCP contract) are independent — any order.

## Estimated commit count
**1.** A focused, safety-isolated interface freeze. **This is a Key-safety-rule-#2 contract → it gets its OWN commit** (never bundled with 1.5b/1.5c — root `CLAUDE.md` "never bundle a safety-critical slice").

## Lessons-logged candidates anticipated
- **Convention candidate** — "A boundary/safety **interface** freezes the signature + behavioral invariants + the closed sink alphabet now; the *engine* and its recall envelope are enforced where the engine lands (2.3) — never bake a recall claim into the interface or its Fake."
- **Architecture-doc note candidate** — confirm the Appendix-A "Redactor" row already enumerates the accepted residuals + envelope reference (it does → no edit expected; flag if drifted).
- **Future TODO — phase (2.3):** wire `ci/eval/redaction_fuzz/` as the hard CI gate against the real engine (spike FLAG-1 encoding-aware oracle · FLAG-2 JWT shape matcher · FLAG-3 binary corpus); owner-confirm per-sink strictness + the 95%/5% threshold (D-A5/D-A6).

## How to invoke
1. Read this brief end-to-end — esp. "Things to flag at Step 2.5" (5 design questions, default votes pre-loaded).
2. Run **`/tdd redactor_interface_freeze`** in the implementer session.
3. **Step 0 (Restate)** — confirm the restatement matches the Feature line.
4. **Step 1 (Identify files)** — confirm against "Files expected to touch."
5. **Step 2.5** — send the test-design write-up + answer the 5 design questions (take defaults or push back). Wait for `APPROVED.` before GREEN.
6. **Step 9** — surface the cross-doc `Redactor` row + anything beyond the anticipated lessons candidates.
