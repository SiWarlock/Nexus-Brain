# /tdd brief — evidence_ref_contract

## Feature
Freeze the `EvidenceRef` contract (§10) — a user-visible piece of evidence backing an answer (`{type, label, resource_ref?, confidence?}`) — freezing its **structure** now while **deferring** the externally-owned `EvidenceType` membership per lead decision D-A11 (Option B). Second of Phase 1.3's three trust contracts (after 1.3a Anchor; ProvenancePacket = 1.3b follows, as it aggregates EvidenceRefs).

## Use case + traceability
- **Task ID:** 1.3 (slice **1.3c** — EvidenceRef; ProvenancePacket = 1.3b follows)
- **Architecture sections it implements:** `ARCHITECTURE.md §10` (grounding/provenance — the evidence record), Appendix A (ProvenancePacket + EvidenceRef row, line 217), §2.5 (import-DAG seam → schema-snapshot pin). §4 (parse-don't-trust on the boundary).
- **Related context:** lead decision **D-A11** (Option B — freeze EvidenceRef *shape*; defer `EvidenceType`/`IdKind` membership, whose canonical values live in NexusOps `MAIN_PLATFORM_INTERFACE.md` v0.2, not in this repo; constraint **C-15** + the NexusOps integration seam, P2/deferred). Mirrors the §5/1.3a frozen-model conventions; **LESSON 6** (named-enum vs deferred-enum vs Literal) + **LESSON 7** (identity-string whitespace-strip) both apply directly. Predecessor: 1.3a `Anchor` landed @`5b50b5f`.

## Acceptance criteria (what "done" means)
- [ ] `EvidenceRef` is a frozen Pydantic v2 model (`frozen=True`, `extra="forbid"`) with **exactly 4 fields**: `type`, `label`, `resource_ref`, `confidence` (matches Appendix-A line 217).
- [ ] **`spec(§10)` schema-snapshot test** pins `set(EvidenceRef.model_fields) == {"type","label","resource_ref","confidence"}` (§2.5-seam ★ freeze — **field shape only**).
- [ ] **EvidenceType membership is DEFERRED (D-A11 guardrail 1):** `type` is typed via a module-level `EvidenceType` alias that is a **constrained `str`** now (`Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]`) — NOT an instantiated enum. A module docstring/comment marks it: *membership unresolved-pending-NexusOps `MAIN_PLATFORM_INTERFACE.md` v0.2; MUST be pinned to the canonical 11 at Phase-4 grounding (first consumption) before the post-spine fork wave* — cite the NexusOps seam, C-15, and D-A11. **No `EvidenceType` value-membership snapshot test** (a value snapshot would lock a set we are explicitly deferring — LESSON 6 corollary).
- [ ] **Additive-narrowing safety (D-A11 guardrail 2):** the design is such that later narrowing `EvidenceType` → a `StrEnum`/`Literal` of the canonical 11 is **non-breaking** — the field declaration `type: EvidenceType` is unchanged (snapshot-stable; the field name stays `type`) and `StrEnum ⊂ str` keeps prior string values valid. A short comment states this.
- [ ] `type` and `label` are **required** (`Field(...)`); `resource_ref` and `confidence` are **optional** (`= None`), per Appendix-A's `resource_ref?`/`confidence?`.
- [ ] All string fields (`type`, `label`, and `resource_ref` when present) use `StringConstraints(strip_whitespace=True, min_length=1)` (LESSON 7) — empty/whitespace-only rejected, surrounding whitespace stripped.
- [ ] `confidence`, when present, is a `float` in `[0.0, 1.0]` (`Field(ge=0.0, le=1.0)` on the optional); `None` is valid; out-of-range rejected.
- [ ] `extra="forbid"` rejects unknown kwargs; `frozen=True` rejects mutation; an omit-each-**required**-field test pins required-ness (LESSON 3); python + JSON round-trips are equality-stable.
- [ ] All unit tests in `core/tests/model/test_evidence.py` pass; `/preflight` clean (canonical visible gate; `mypy .` override — D-A3/LESSON 5).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + confirms Appendix-A:217's EvidenceRef portion hot).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 4+.** EvidenceRef is a freeze-before-fork §10 contract with no production entry point this phase (same posture as 1.1/1.2/1.3a). First constructed at Phase-4 §10 grounding (evidence chips on an answer's ProvenancePacket) and serialized at the NexusOps seam (P2). Exported as `model.evidence`; no call path to trace yet (not a tested-but-unwired gap).

## Files expected to touch
**New:**
- `core/model/evidence.py` — the frozen `EvidenceRef` model + the deferred `EvidenceType` constrained-str alias (with the D-A11 deferral marker).
- `core/tests/model/test_evidence.py` — snapshot (shape-only) + behavioral tests.

**Modified:** none (Appendix-A + `core/CLAUDE.md` rows are orchestrator territory — flagged at Step 9).

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/model/test_evidence.py` (`pytestmark = pytest.mark.unit`; `from model.evidence import EvidenceRef, EvidenceType`):

1. **`test_evidence_schema_snapshot`** — Asserts: `set(EvidenceRef.model_fields) == {"type","label","resource_ref","confidence"}`. Why: §2.5-seam ★ freeze pin — **shape only** (§10/Appendix-A:217).
2. **`test_evidence_valid_construction_full`** — Asserts: all 4 fields construct + round-read. Why: §10 happy path.
3. **`test_evidence_valid_construction_minimal`** — Asserts: only `type`+`label` (optionals default `None`) constructs. Why: `resource_ref?`/`confidence?` are optional.
4. **`test_evidence_rejects_extra_field`** — Asserts: unknown kwarg raises. Why: §4 parse-don't-trust (`extra="forbid"`).
5. **`test_evidence_required_fields`** — Asserts: omitting `type` or `label` raises; omitting `resource_ref`/`confidence` does NOT. Why: LESSON 3 omit-each on the required subset.
6. **`test_evidence_rejects_empty_strings`** — Asserts: `""`/`"   "` raise for `type`, `label`, and `resource_ref`-when-present. Why: LESSON 7 whitespace-strip identity.
7. **`test_evidence_strips_whitespace`** — Asserts: `" x "` → `"x"` for a string field. Why: `StringConstraints(strip_whitespace=True)` pin.
8. **`test_evidence_optional_fields`** — Asserts: `resource_ref`/`confidence` omitted/`None` ok; present kept. Why: optional-field contract.
9. **`test_evidence_confidence_range`** — Asserts: present `-0.1`/`1.1` raise; `0.0`/`1.0`/`None` valid. Why: `[0,1]` probability (optional).
10. **`test_evidence_type_membership_is_deferred`** — Asserts: `type="any_nonempty_string"` (e.g. `"code_chunk"`, `"some_future_kind"`) constructs successfully — `type` is NOT yet restricted to a fixed set. Why: **encodes D-A11** — the `EvidenceType` membership is intentionally open until the canonical 11 are pinned at Phase-4; this test + the module marker ARE the deferral record. (Deliberately the ONLY "membership" test — there is no value-set snapshot.)
11. **`test_evidence_is_frozen`** — Asserts: post-construct mutation raises.
12. **`test_evidence_roundtrip` / `test_evidence_json_roundtrip`** — Asserts: python + JSON round-trips equality-stable. Why: persist/MCP-egress boundary.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW model `EvidenceRef` (+ deferred `EvidenceType` alias) — §10 / Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc table — NEW `EvidenceRef` row (4-field shape snapshot; `type` = deferred `EvidenceType` constrained-str per D-A11, **no membership snapshot**; optionals `resource_ref`/`confidence`; whitespace-strip strings; pin `test_evidence.py`).
  - `ARCHITECTURE.md` Appendix-A:217 — **confirm** the EvidenceRef portion matches `{type∈EvidenceType, label, resource_ref?, confidence?}` (it does); the row's "11-EvidenceType" wording stays (the *target* is still 11) but is annotated as **D-A11-deferred** (membership pinned at Phase-4). Orchestrator reconciles the annotation hot.
- **§2.5-seam (shared-contract) model touched?** YES — `EvidenceRef` §10 is §2.5-crossed. The RED outline includes the `spec(§10)` **shape** snapshot (#1). Per D-A11 guardrail 2, that snapshot pins field names only, so the deferred-membership resolution at Phase-4 is additive.

## Things to flag at Step 2.5
1. **`EvidenceType` modeling — constrained-`str` alias now vs an instantiated enum (THE load-bearing one).** My default vote: **module-level `EvidenceType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` now** (a named constrained-str), field `type: EvidenceType`, with the D-A11 deferral marker + the additive-narrowing comment; **no membership snapshot**. Rationale: faithfully implements lead D-A11 Option B ("freeze shape, defer membership") + both guardrails, **without guessing** the externally-owned NexusOps set (Option C, explicitly rejected). Later, `EvidenceType` becomes a `StrEnum`/`Literal` of the canonical 11 at Phase-4 — field name unchanged ⇒ snapshot-stable; `StrEnum ⊂ str` ⇒ values stay valid. If you read D-A11 as wanting an instantiated-now `StrEnum` (which would require provisional members = the rejected guess), ping `TWEAK` and I'll re-confirm with the lead — but the constrained-str alias is the only non-guessing way to honor "defer membership."
2. **`resource_ref` semantics.** Default vote: an **opaque** locator/id of the underlying resource (a `chunk_id` / `anchor_id` / commit SHA / episode-card id / plan-task id — the DOMAIN_MODEL evidence-source set), kept opaque (LESSON 2 — no parsing kind back out; `type` carries the kind). Optional `str | None`, strip+min_length when present. No separate `resource_kind` field — `type` IS the discriminator (keeps the 4-field Appendix-A shape).
3. **`confidence` optionality + range.** Default vote: **optional** (`float | None = None`), `[0,1]` when present (mirrors `Anchor.confidence`). Appendix-A marks it `confidence?`. A `None` confidence = "evidence with no model-assigned score" (legitimate for a structural reference).
4. **`label` constraint.** Default vote: **required**, strip+min_length=1 — a user-visible evidence chip needs a non-empty human-readable label (§10 evidence chips).
5. **Should EvidenceRef reference `Anchor` directly (typed) rather than via opaque `resource_ref`?** Default vote: **NO — keep `resource_ref` an opaque str**, not a typed `Anchor`/union. An EvidenceRef points at *many* resource kinds (chunk/anchor/commit/card/task), so a typed union would couple it to every model + bloat the frozen seam; the opaque-id + `type`-discriminator shape is what serializes cleanly to the NexusOps `EvidenceRef` (Appendix-A:217). Hydration to a concrete resource is a Phase-4 retrieval concern, not the frozen contract.

## Dependencies + sequencing
- **Depends on:** 1.1 conventions; 1.3a `Anchor` (landed `5b50b5f`) — an EvidenceRef's `resource_ref` may locate an `anchor_id` (opaque, no import coupling). Lead D-A11 ruling (received).
- **Blocks:** 1.3b `ProvenancePacket` (aggregates EvidenceRefs — its `evidence: list[EvidenceRef]` field, pending that slice's Step-2.5); §10 grounding (Phase 4); the NexusOps seam (P2).

## Estimated commit count
**1.** One focused ★ freeze-before-fork contract (EvidenceRef + the deferred `EvidenceType` alias + shape snapshot). Not bundled — each 1.3 model is a distinct ★ contract with its own snapshot + Appendix-A row + atomic cross-doc pairing (same rationale as 1.2a–d / 1.3a). The D-A11 deferral makes the seam-handling here distinct enough to keep isolated for bisectability.

## Lessons-logged candidates anticipated
- **Convention candidate** — already banked: LESSON 6 (deferred/externally-owned enum freezes shape only, no membership snapshot) + §7 (whitespace-strip identity) — this slice is their first *application*; confirm they held (no new lesson expected unless the deferred-alias modeling surfaces a wrinkle).
- **Architecture-doc note candidate** — the Appendix-A:217 "11-EvidenceType" annotation as D-A11-deferred (membership pinned at Phase-4).
- **Future TODO — belongs-to-phase** — pin the canonical 11 `EvidenceType` values (+ 22 `IdKind`) at Phase-4 grounding, BEFORE the post-spine fork, from the owner's NexusOps doc or a flagged spine-time decision (D-A11 / owner-pending). Orchestrator routes to the Phase-4 tracker + Carry-forward.

## How to invoke
1. **Read this brief end-to-end** — the 5 Step-2.5 questions (Q1 is load-bearing — the EvidenceType modeling).
2. **Run `/tdd evidence_ref_contract`** (session oriented — no `/session-start`).
3. **Step 0 (Restate)** — confirm EvidenceRef only (ProvenancePacket is 1.3b).
4. **Step 1 (Identify files)** — `core/model/evidence.py` + `core/tests/model/test_evidence.py`.
5. **Step 2.5** — tight write-up (per-test `Asserts:` lines + acceptance→test coverage map); answer the 5 Qs (esp. Q1). Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9** — categorized flags + the EvidenceRef cross-doc row ask + the Appendix-A D-A11-deferral annotation + ship-ask.
