# /tdd brief — provider_ports_contract

## Feature
Freeze the 4 pluggable, version-stamped provider ports (§7/§16) as behavioral Protocols + faithful Fake doubles: `EmbeddingProvider` (`embed`/`dimension`/`model_version`), `Reranker` (`rerank`), `ContextStrategy` (`augment`), `ModelProvider` (`generate` + Citations). Second Phase-1.4 slice (bundled — 4 related non-safety behavioral ports, like the 1.1 Clock/Seed/IdGen bundle).

## Use case + traceability
- **Task ID:** 1.4 (slice **1.4b** — provider ports; HostPort=1.4a done; CodeGraphPort=1.4c, Event·Secret·Observability=1.4d, cassette record/replay re-sequenced — see Q7)
- **Architecture sections it implements:** `ARCHITECTURE.md §7` (the 4 provider port signatures), §16 (providers pluggable + version-stamped; local|cloud; switching = blue-green re-embed), §2.5 (seam → schema-snapshot for the result data types). Appendix-A:219 (Provider ports row).
- **Related context:** mirrors the 1.1 behavioral-port pattern (`core/ports/idgen.py` — `Protocol` + `@runtime_checkable` + faithful `Fake*` in `testing/fakes.py`; LESSON 1). These are **non-deterministic surfaces** (real embeddings/generation) → the live behavior is **eval-tested**, never `/tdd`; this slice freezes the **deterministic interfaces + Fakes** (which IS `/tdd`-able). Result data types follow the frozen-model conventions (LESSON 6/7/8).

## Acceptance criteria (what "done" means)
- [ ] `EmbeddingProvider`, `Reranker`, `ContextStrategy`, `ModelProvider` are `@runtime_checkable Protocol`s with the §7/Appendix-A:219 signatures (see RED outline for exact shapes).
- [ ] Each port exposes a `model_version` identity (version-stamped, §16) where Appendix-A names it (`EmbeddingProvider.model_version` at minimum); `EmbeddingProvider.dimension` is exposed (must agree with the §5 `StoreVersionStamp.dimension`).
- [ ] Result data types `RerankResult`, `GenerateResult` (+ minimal `Citation`) are frozen Pydantic v2 (`frozen=True`, `extra="forbid"`), each pinned by a `spec(§7)` schema-snapshot (§2.5-seam — they cross into retrieval/grounding). Rich per-provider payloads (full Anthropic Citations shape) **deferred** to §10 grounding (Phase-4), additive (Q6).
- [ ] Faithful `Fake*` doubles in `core/testing/fakes.py` — **deterministic** (no wall-clock/RNG; seed via the `Seed` port if randomness is needed): `FakeEmbeddingProvider` (stable vector from text, fixed `dimension`), `FakeReranker` (deterministic scores), `FakeContextStrategy` (deterministic augment), `FakeModelProvider` (canned `generate` + citations). Each upholds the real contract (LESSON 1); `*_conform` tests assert `isinstance`.
- [ ] String identity fields on result types use `StringConstraints(strip_whitespace=True, min_length=1)` (LESSON 7).
- [ ] All unit tests in `core/tests/ports/test_providers.py` pass; `/preflight` clean (`mypy .`).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + confirms Appendix-A:219).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2/3 + the eval harness.** The real provider adapters (local Ollama / cloud Voyage·Anthropic) + the cassette record/replay are wired when ingestion/retrieval/grounding consume them (Phase 2/3) and eval-tested then. This slice freezes the interfaces + Fakes — the freeze-before-fork need (tracks inject the Fakes). Exported as `ports.providers`. Not a tested-but-unwired gap.

## Files expected to touch
**New:**
- `core/ports/providers.py` — the 4 `Protocol`s + `RerankResult`/`GenerateResult`/`Citation` frozen result types.
- `core/tests/ports/test_providers.py` — conformance + Fake fidelity + result-type snapshots.

**Modified:**
- `core/testing/fakes.py` — add the 4 `Fake*Provider` doubles.

**Orchestrator territory (flag at Step 9):** `core/CLAUDE.md` row, `ARCHITECTURE.md` Appendix-A:219.

## RED test outline (Step 2)
Tests in `core/tests/ports/test_providers.py` (`pytestmark = pytest.mark.unit`; `from ports.providers import *`; `from testing.fakes import FakeEmbeddingProvider, FakeReranker, FakeContextStrategy, FakeModelProvider`):

1. **`test_provider_protocol_conformance`** — Asserts: each `Fake*Provider` `isinstance` its `Protocol` (runtime_checkable). Why: LESSON 1.
2. **`test_embedding_provider_contract`** — Asserts: `embed(texts: Sequence[str]) -> list[list[float]]` returns one vector per input, each of length `dimension`; `dimension: int` + `model_version: str` exposed. Why: §7/§16 + the dim must match `StoreVersionStamp`.
3. **`test_fake_embedding_deterministic`** — Asserts: same input → identical vector across calls (no wall-clock/RNG). Why: LESSON 1 — a non-deterministic fake breaks the eval/test seam.
4. **`test_reranker_contract`** — Asserts: `rerank(query: str, documents: Sequence[str]) -> list[RerankResult]`; results reference inputs by `index`, carry a `score`, sorted desc; length ≤ input. Why: §7 rerank (consumed by the retrieval phase).
5. **`test_rerank_result_snapshot`** — Asserts: `set(RerankResult.model_fields) == {"index","score"}`, frozen + extra-forbid. Why: §2.5-seam `spec(§7)`.
6. **`test_context_strategy_contract`** — Asserts: `augment(chunk_text: str, document_context: str) -> str` returns a non-empty augmented string (the Contextual-Retrieval prefix + chunk). Why: §7 context-augment (consumed by the ingest phase).
7. **`test_model_provider_contract`** — Asserts: `generate(prompt: str, ...) -> GenerateResult`; `GenerateResult{text, citations}`; `citations` is a `list[Citation]` (possibly empty). Why: §7/§10 generation + Citations.
8. **`test_generate_result_and_citation_snapshot`** — Asserts: `set(GenerateResult.model_fields)`/`set(Citation.model_fields)` == checked-in sets; frozen + extra-forbid. Why: §2.5-seam `spec(§7)` (shape pinned; rich payload deferred — Q6).
9. **`test_fakes_fidelity`** — Asserts: each Fake enforces the real contract shape (return types, dimension agreement, deterministic) — no looser fake (LESSON 1).
10. **`test_provider_result_strip_identity`** — Asserts: result-type string fields strip + reject empty/whitespace. Why: LESSON 7.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW ports `EmbeddingProvider`/`Reranker`/`ContextStrategy`/`ModelProvider` + result types `RerankResult`/`GenerateResult`/`Citation` — §7/§16/Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc table — NEW `Provider ports` row (4 Protocols + Fakes; result-type snapshots; `model_version`/`dimension`; deferred Citations payload). Behavioral ports (no field-snapshot on the Protocols; the result types are snapshotted).
  - `ARCHITECTURE.md` Appendix-A:219 — confirm the row matches (`EmbeddingProvider{embed,dimension,model_version}·Reranker{rerank}·ContextStrategy{augment}·ModelProvider{generate+citations}`); annotate cassette record/replay re-sequenced (Q7) + the Citations payload Phase-4-deferred.
- **§2.5-seam:** the result data types (`RerankResult`/`GenerateResult`/`Citation`) cross into retrieval/grounding → schema-snapshots included (#5/#8). The Protocols themselves are behavioral (no field-set; like 1.1).

## Things to flag at Step 2.5
1. **`embed` batch vs single.** Default vote: **batch** — `embed(texts: Sequence[str]) -> list[list[float]]` (embedding APIs batch; the ingest pipeline embeds in batches). A single-text helper can wrap it later.
2. **Vector type — `list[float]` vs a typed `Vector`.** Default vote: **`list[float]`** (raw) — dim/finiteness validation is the Phase-3.1 LanceDB `Vector(dim)` binding (deferred per the 1.2a carry-forward); the provider returns raw floats, the writer binds the typed column.
3. **`dimension`/`model_version` — `@property` vs method.** Default vote: **`@property`** (stable attributes, not actions); Protocols declare them as properties.
4. **`Reranker.rerank` result — index-based vs document-carrying.** Default vote: **`RerankResult{index: int, score: float}`** (references the input `documents` by index + a score) — avoids copying document text through the reranker; the caller maps indices back. Sorted score-desc.
5. **`ContextStrategy.augment` return — augmented full text vs just the blurb.** Default vote: **the full augmented text** (`document_context` blurb prepended to `chunk_text`) — matches the Chunk's `context_blurb` field semantics (Contextual Retrieval); the caller stores both.
6. **`ModelProvider.generate` Citations shape — define now vs defer.** Default vote: **minimal `Citation{cited_text, source_index}` now, rich shape deferred to §10 grounding (Phase-4), additive** — the full Anthropic Citations→`file:line`+`recorded_sha` mapping is the grounding gate's concern; freezing a minimal shape (what text was cited from which source) + a `spec(§7)` snapshot keeps narrowing additive (same discipline as HostPort payloads / EvidenceType membership). Flag if you'd rather model the full Citations payload now.
7. **Cassette record/replay — re-sequence out of Phase 1?** Default vote: **YES, re-sequence to the providers-track / eval-harness** (where real cloud providers are wired) — it's eval-infra for the non-deterministic provider behavior, NOT a freeze-before-fork cross-track *contract*; the Phase-1 freeze need is the interfaces + Fakes (which this slice delivers). **I'm flagging this to the lead as a sequencing decision** (the 1.4 task text bundles "cassette record/replay"); it is not dropped — it lands with the real providers. If the lead/owner wants the cassette harness frozen in Phase 1, it becomes slice 1.4e.

## Dependencies + sequencing
- **Depends on:** 1.1 (the `Seed` port — Fakes seed via it if they need any randomness; the behavioral-port pattern). Independent of HostPort/1.2/1.3.
- **Blocks:** Phase-2 ingest (EmbeddingProvider/ContextStrategy), Phase-3 retrieval (Reranker), Phase-4 grounding (ModelProvider+Citations). Parallel-eligible with 1.4c/1.4d.

## Estimated commit count
**1.** One bundled slice — 4 related non-safety behavioral provider ports + their Fakes + the result types, sharing the §7/§16 context + one test file (the 1.1 bundle precedent). No safety invariant → bundling is correct.

## Lessons-logged candidates anticipated
- **Convention candidate** — likely none new (LESSON 1 behavioral-port pattern + LESSON 6/7/8 cover it); possibly "behavioral ports carry no field-snapshot, but their frozen *result types* do" if worth pinning.
- **Architecture-doc note candidate** — Appendix-A:219 annotations: cassette re-sequenced (Q7) + Citations payload Phase-4-deferred (Q6).
- **Future TODO — belongs-to-phase** — (a) cassette record/replay harness → providers-track/eval; (b) full Citations payload shape → §10 grounding (Phase-4); (c) real provider adapters (Ollama/Voyage/Anthropic) → Phase-2/3/providers; (d) reranker/cloud-embedder bake-offs → eval.

## How to invoke
1. **Read this brief end-to-end** — 7 Step-2.5 questions; Q6 (Citations shape) + Q7 (cassette re-sequence) are the load-bearing/flag-to-lead ones.
2. **Run `/tdd provider_ports_contract`** (session oriented — no `/session-start`).
3. **Step 0 (Restate)** — confirm the 4 provider Protocols + Fakes (NOT real adapters, NOT the cassette harness).
4. **Step 1 (Identify files)** — `core/ports/providers.py` + `core/tests/ports/test_providers.py` + `core/testing/fakes.py`.
5. **Step 2.5** — tight write-up + acceptance→test coverage map; answer the 7 Qs. Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9** — categorized flags + the provider-ports cross-doc row ask + the cassette/Citations sequencing notes + ship-ask.
