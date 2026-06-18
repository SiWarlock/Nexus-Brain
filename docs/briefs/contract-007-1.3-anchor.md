# /tdd brief — anchor_contract

## Feature
Freeze the `Anchor` trust primitive (§10 north-star) as an immutable Pydantic v2 contract: the typed `file:line[-range]` edge between a prose/answer span and a code target, carrying its revalidation `state` + `last_resolved_sha` + `confidence`. First of Phase 1.3's three trust contracts (1.3a Anchor → 1.3c EvidenceRef → 1.3b ProvenancePacket).

## Use case + traceability
- **Task ID:** 1.3 (slice **1.3a** — Anchor; EvidenceRef = 1.3c, ProvenancePacket = 1.3b follow)
- **Architecture sections it implements:** `ARCHITECTURE.md §10` (grounding/anchors/provenance — NORTH STAR), Appendix A (Anchor row, line 216), §2.5 (the import-DAG seam → schema-snapshot pin). State-machine alphabet cross-checked against §5 (line 90, Anchor machine).
- **Related context:** mirrors the §5-model conventions frozen in 1.2 (`core/model/stamp.py` is the closest exemplar — `frozen=True`/`extra="forbid"`/`Field(...)`/snapshot test). LESSONS §1–§5 (esp. §3 omit-each-field guard, §4 N/A here — Anchor is not a serialized-file model). Predecessor handoff: `docs/sessions/contract-001-…` + `contract-002-…`. The whitespace-strip before-fork sweep (Carry-forward) is **baked into this slice from the start**.

## Acceptance criteria (what "done" means)
- [ ] `Anchor` is a frozen Pydantic v2 model (`model_config = ConfigDict(frozen=True, extra="forbid")`) with **exactly 11 fields**: `anchor_id`, `project_id`, `source_file`, `source_span`, `target_path`, `target_line_start`, `target_line_end`, `target_symbol`, `state`, `last_resolved_sha`, `confidence` (matches Appendix-A line 216).
- [ ] **`spec(§10)` schema-snapshot test** pins `set(Anchor.model_fields) == EXPECTED_ANCHOR_FIELDS` (§2.5-seam ★ freeze — drift = cross-track Finding).
- [ ] `state` is a closed enum **`AnchorState`** with exactly the 5 Appendix-A values `{live, stale, moved, unknown, orphaned}`, pinned by a `test_anchor_state_values` membership snapshot (the state alphabet is itself a frozen contract).
- [ ] All identity/path string fields use `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` (the before-fork whitespace-strip sweep, baked in here): `anchor_id`, `project_id`, `source_file`, `source_span`, `target_path`, `last_resolved_sha`, and `target_symbol` *when present*. A whitespace-only identity is rejected; surrounding whitespace is stripped.
- [ ] `target_line_start` / `target_line_end` are `PositiveInt`; a model-level validator rejects `target_line_end < target_line_start` (a backwards span is never valid; single-line ⇒ start == end).
- [ ] `confidence` is a `float` constrained to `[0.0, 1.0]` (`Field(ge=0.0, le=1.0)`); out-of-range rejected.
- [ ] `extra="forbid"` rejects any unknown kwarg; `frozen=True` rejects post-construct mutation; an omit-each-required-field test proves required-ness (LESSONS §3 generic guard).
- [ ] python-mode + JSON-mode round-trips are equality-stable (`model_validate(model_dump()) == m`, `model_validate_json(model_dump_json()) == m`).
- [ ] All unit tests in `core/tests/model/test_anchor.py` pass.
- [ ] `/preflight` clean (run the **canonical** gate, visible output — `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest`; **never** a hand-rolled `>/dev/null && echo OK` — LESSON §5 / D-A3; note the `mypy .` override per D-A3).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + confirms the Appendix-A row hot).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2+.** Anchor is a foundational freeze-before-fork contract with no production entry point this phase, by design (same posture as every 1.1/1.2 contract — see contract-002 session doc "Reachability"). First constructed by the Phase-2 anchor producer (ingest/chunking) and first revalidated by the §10 grounding gate (reads the SHA via the `Clock`/CodeGraph seams). It is exported from `core/model/` for those consumers; no call path to trace yet (not a tested-but-unwired *gap*).

## Files expected to touch
**New:**
- `core/model/anchor.py` — the frozen `Anchor` model + `AnchorState` enum.
- `core/tests/model/test_anchor.py` — snapshot + state-alphabet + behavioral tests.

**Modified:** none (Appendix-A + `core/CLAUDE.md` cross-doc rows are **orchestrator territory** — flagged at Step 9, written hot by the orchestrator; the implementer does not touch them).

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests to write in `core/tests/model/test_anchor.py` (`pytestmark = pytest.mark.unit`; `from model.anchor import Anchor, AnchorState`):

1. **`test_anchor_schema_snapshot`** — Asserts: `set(Anchor.model_fields) == EXPECTED_ANCHOR_FIELDS` (the checked-in 11-field frozenset). Why: §2.5-seam ★ freeze pin (§10 / Appendix-A line 216).
2. **`test_anchor_state_values`** — Asserts: `{s.value for s in AnchorState} == {"live","stale","moved","unknown","orphaned"}`. Why: the state alphabet is a frozen contract (Appendix-A line 216); pins it against the §5-machine wording (see Step-2.5 Q1).
3. **`test_anchor_valid_construction`** — Asserts: a fully-specified valid `Anchor` constructs and round-reads its fields. Why: §10 happy-path shape.
4. **`test_anchor_rejects_extra_field`** — Asserts: an unknown kwarg raises `ValidationError`. Why: §4 parse-don't-trust (`extra="forbid"`).
5. **`test_anchor_all_required`** — Asserts: omitting each non-optional field raises (omit-each loop). Why: LESSONS §3 required-ness guard.
6. **`test_anchor_rejects_empty_identity_strings`** — Asserts: `""` and `"   "` (whitespace-only) raise for each strip+min_length string field. Why: before-fork whitespace sweep (Carry-forward) — whitespace-loose identity in a frozen cross-track contract is a Finding.
7. **`test_anchor_strips_surrounding_whitespace`** — Asserts: `" abc "` → `"abc"` for a strip field. Why: `StringConstraints(strip_whitespace=True)` behavior pin.
8. **`test_anchor_span_ordering`** — Asserts: `target_line_end < target_line_start` raises; `start == end` (single line) is valid. Why: a backwards span is never valid (§10 file:line-range semantics).
9. **`test_anchor_positive_lines`** — Asserts: `0`/`-1` for either line field raises. Why: line numbers are 1-based positive (`PositiveInt`).
10. **`test_anchor_confidence_range`** — Asserts: `-0.1` and `1.1` raise; `0.0` and `1.0` are valid. Why: confidence is a `[0,1]` probability.
11. **`test_anchor_target_symbol_optional`** — Asserts: omitting `target_symbol` (or `None`) constructs; a present non-empty value is kept; whitespace-only is rejected. Why: a line-range anchor needn't name a symbol (Step-2.5 Q2).
12. **`test_anchor_is_frozen`** — Asserts: mutating a field post-construct raises. Why: an anchor is an immutable record; revalidation produces a new instance.
13. **`test_anchor_roundtrip` / `test_anchor_json_roundtrip`** — Asserts: python + JSON round-trips are equality-stable (enum serializes to its string value). Why: persist/reload + MCP-egress boundary stability.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW model `Anchor` (+ `AnchorState` enum) — §10 / Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc-invariants table — NEW `Anchor` row (mirrors the §5-model rows; pin `test_anchor.py`; note the 11-field snapshot + 5-value `AnchorState` alphabet + whitespace-strip identity).
  - `ARCHITECTURE.md` Appendix-A line 216 — **confirm** the row already matches the frozen 11-field set (it does: `anchor_id·project_id·source_file·source_span·target_path·target_line_start/end·target_symbol·state·last_resolved_sha·confidence`); reconcile only if the slice diverges.
  - **Cross-doc reconciliation (orchestrator, not implementer):** the §5 Anchor-machine wording (line 90, `…→ orphaned/deleted`) names a `deleted` terminal the Appendix-A `state` enum omits — see Step-2.5 Q1; the orchestrator reconciles §5 prose (clarify `deleted` = record-lifecycle removal, not a `state` value) so docs agree with the frozen 5-value enum.
- **§2.5-seam (shared-contract) model touched?** YES — `Anchor` §10 is crossed by §2.5 dependency edges (retrieval/drift/grounding → … → model). The RED outline includes the `spec(§10)` schema-snapshot test (#1), authored this cycle, reviewed at Step 2.5.

## Things to flag at Step 2.5
1. **`AnchorState` value set — is `deleted` a 6th state?** Appendix-A line 216 enumerates **5** (`live|stale|moved|unknown|orphaned`); §5's machine (line 90) writes `live ⇄ stale|moved|unknown → orphaned/deleted` (+ recovery edges to `live`). My default vote: **freeze the enum to the 5 Appendix-A values; `deleted` is the record-lifecycle removal (the anchor row is purged/tombstoned), NOT a value of the live `state` field** — because Appendix-A is the frozen field-set authority and the snapshot pins it. I'll reconcile the §5 prose to say so. If you read §5 as making `deleted` a genuine 6th *state*, ping back `TWEAK` and I'll escalate the contract question + widen the enum. (This is a cross-doc drift I'm surfacing; flagged to the lead.)
2. **`target_symbol` required or optional?** Default vote: **`str | None = None` (optional)** — an anchor to a bare `file:line-range` need not resolve to a named symbol; when present it's strip+min_length=1. Rationale: §10 anchors are `file:line OR file:line-range` (per §10 + the DATA_MODEL Anchor object).
3. **`last_resolved_sha` required or optional?** Default vote: **required, strip+min_length=1** — every anchor is created/resolved against a known SHA (the §10 "grounded at a known SHA" invariant; revalidation diffs against it). A never-resolved anchor is not a valid trust primitive. If a "pending, sha-unknown" creation state is genuinely needed, we make it optional — but default required.
4. **`AnchorState` as `enum.StrEnum` vs `Literal`?** Default vote: **`StrEnum` (named `AnchorState`)** — it's a named state-machine alphabet reused by the Phase-2+ revalidation transition logic, not a one-off inline closed set (contrast Chunk's `Literal` `doc_or_code`/`ownership`/`register`, which are inline tags). StrEnum serializes to its string value (JSON-roundtrip stable) and is iterable for the membership-snapshot test.
5. **`source_span` validation depth?** Default vote: **bare strip+min_length=1 `str`; do NOT validate the span syntax** ("10" / "10-20" / "10:5-12:8") in the frozen contract — format ownership belongs to the Phase-2 anchor producer/parser, mirroring how Chunk's `anchor`/`*_sha` are bare str with format deferred (contract-002 decision "anchor/*_sha format → 1.3 seam" means the *typing seam* lands here, not a syntax validator).

## Dependencies + sequencing
- **Depends on:** 1.1 (determinism seams — `Clock`/`IdGen` inject `anchor_id`/timestamps at the Phase-2 producer; no direct import in this contract). 1.2 conventions (frozen-model pattern) landed.
- **Blocks:** 1.3c (EvidenceRef — an `EvidenceRef` may carry an anchor `resource_ref`), 1.3b (ProvenancePacket — aggregates anchors/evidence), and all of §10 grounding (Phase 4) + Phase-2 anchor production.

## Estimated commit count
**1.** One focused ★ freeze-before-fork contract (Anchor + its enum + snapshot). Not bundled with EvidenceRef/ProvenancePacket: each 1.3 model is a distinct ★ contract with its own schema-snapshot + Appendix-A row + atomic cross-doc pairing (the same reason 1.2 ran as 5 atomic sub-slices, per the template's "do NOT bundle when a cross-doc invariant change is involved / each is large on its own").

## Lessons-logged candidates anticipated
- **Convention candidate** — "Named domain state machines are `StrEnum` with a membership-snapshot test; inline closed tags stay `Literal`" (if Q4 lands as voted).
- **Convention candidate** — "Every §5/§10 identity string field is `StringConstraints(strip_whitespace=True, min_length=1)`" (the before-fork sweep generalized into a standing rule; pin = the per-model empty/whitespace tests).
- **Architecture-doc note candidate** — the §5↔Appendix-A `deleted` reconciliation (Q1): `deleted` is anchor-record lifecycle, not a `state` value.
- **Future TODO — operational** — a span-format validator/parser is the Phase-2 anchor producer's job (Q5); the typing seam (bare str) lands here.

## How to invoke
1. **Read this brief end-to-end** — don't skip "Things to flag at Step 2.5" (5 design questions; take defaults or ping back).
2. **Run `/tdd anchor_contract`** in the implementer session (session already oriented — no `/session-start`).
3. **Step 0 (Restate)** — confirm the restatement matches the Feature line (Anchor only; EvidenceRef/ProvenancePacket are later slices).
4. **Step 1 (Identify files)** — confirm the file list (`core/model/anchor.py` + `core/tests/model/test_anchor.py`).
5. **Step 2.5 (test-design pause)** — send the tight write-up (one `Asserts: <invariant> (§anchor)` line per test + the acceptance-bullet→test coverage map); answer the 5 design questions (defaults or disagreement). Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9 (summarize)** — categorized flags + the cross-doc `Anchor` row ask + the §5 `deleted` reconciliation note + ship-ask.
