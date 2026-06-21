# /tdd brief — anchor_aware_chunking_docs

## Feature
The chunk-stage output contract + the **docs** chunking path: define the intermediate `ChunkDraft` (the chunk-stage record the redactor/pipeline/embed consume) and split docs by heading into anchored `ChunkDraft`s, each carrying its file:line span data + the chunk-derivable subset of the frozen `Chunk` fields. (Code-AST chunking + the tree-sitter fallback is the sibling slice **2.2b**.)

## Use case + traceability
- **Task ID:** 2.2a
- **Architecture sections it implements:** `ARCHITECTURE.md §8` (the anchor-aware chunk stage — docs heading-split + late-chunking), `ARCHITECTURE.md §5` (the frozen `Chunk` field contract whose chunk-derivable subset + closed sets the draft mirrors).
- **Related context:** 2.1 landed `discover()`/`classify()` (`DiscoveredFile`, `FileClassification` in `core/ingest/{discover,classify}.py`). `Chunk` (`core/model/chunk.py`) is frozen with **19 all-required fields** — so a full `Chunk` CANNOT be built at chunk-time (no `vector` until embed/Phase-3, no `*_sha`/`chunk_id`/`created_at`/`generation` until ingest/2.4). `Anchor` (`core/model/anchor.py`) is frozen + all-required too (needs `anchor_id`/`project_id`/`last_resolved_sha`). So this stage emits the chunk+anchor **data**; the frozen `Chunk` + `Anchor` models are assembled at 2.4 with ingest-context. The file:line span *syntax* is owned by this Phase-2 producer (mirrors `Chunk.anchor`/`Anchor.source_span` being bare typed strings).

## Acceptance criteria (what "done" means)
- [ ] `chunk_docs(text, classification, source_path)` returns a deterministic `tuple[ChunkDraft, ...]`, one draft per heading section of a markdown/doc file.
- [ ] Each `ChunkDraft` carries: `text` (the section body), `source_path`, the four classification axes (`doc_or_code`/`producer`/`doc_type`/`ownership`), `register`, the `anchor` span string, and `target_line_start`/`target_line_end` (+ optional `target_symbol` = the heading title).
- [ ] The `anchor` span string follows the pinned v0 syntax: `"start-end"` for a multi-line span, `"N"` for a single line (1-based, matching `Anchor.source_span` examples).
- [ ] `target_line_start`/`target_line_end` are 1-based, `end >= start`, and bound the section's lines in the source text.
- [ ] A doc with **no headings** → exactly one whole-file `ChunkDraft` spanning the file (R-PARTIAL: never drop content).
- [ ] A heading with empty body still yields a draft (no silently-dropped section).
- [ ] `ChunkDraft`'s chunk-derivable fields are a strict subset of `Chunk`'s; a `get_args` drift test pins the closed sets (`doc_or_code`/`ownership`/`register`) byte-identical to `Chunk` (extends LESSON 19).
- [ ] Determinism: same input → identical draft tuple (stable order = source order).
- [ ] `/preflight` clean (ruff · format · `mypy .` · pytest).

## Wiring / entry point (Step 7.5)
**none — wiring lands in 2.4.** `chunk_docs()` is a pure function; the `add` ingest pipeline (`core/ingest/pipeline.py`, Task 2.4) calls it on each classified doc file, then assembles the frozen `Chunk` + `Anchor` from each `ChunkDraft` + ingest-context (project_id, SHA, IdGen, vector). The **code** chunking entry (`chunk_code`) lands in 2.2b. Reachability at this slice is intentionally test-only (declared deferral).

## Files expected to touch
**New:**
- `core/ingest/chunk.py` — `ChunkDraft` (frozen) + `chunk_docs(...) -> tuple[ChunkDraft, ...]` + the heading-split + span helpers. (Note: this is `ingest.chunk`, distinct from the frozen `model.chunk`; import the contract as `from model.chunk import Chunk` in the drift test.)
- `core/tests/ingest/test_chunk.py`

**Modified:** none expected. No new dependency (heading-split is pure-Python; heavy deps — LlamaIndex/tree-sitter — arrive in 2.2b).

If implementation needs files/deps beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/ingest/test_chunk.py` (tag each `# spec(§8)`, except the drift guard `# spec(§5)`):

1. **`test_chunk_docs_splits_by_heading`** — Asserts: a 3-heading doc → 3 drafts, each text scoped to its section. Why: §8 docs heading-split.
2. **`test_chunk_docs_section_line_span`** — Asserts: each draft's `target_line_start/end` bound its section (1-based, end>=start) and `anchor` == the `"start-end"`/`"N"` span string. Why: §8 anchor-aware spans.
3. **`test_chunk_docs_no_headings_single_draft`** — Asserts: a heading-less doc → 1 whole-file draft spanning all lines. Why: §8 R-PARTIAL (never drop content).
4. **`test_chunk_docs_empty_section_kept`** — Asserts: a heading with no body still yields a draft. Why: §8 no-silent-drop.
5. **`test_chunk_docs_target_symbol_is_heading`** — Asserts: `target_symbol` == the heading title text (single-line headings); whole-file draft → `target_symbol is None`. Why: §8 anchor symbol.
6. **`test_chunk_docs_carries_classification`** — Asserts: each draft's four axes == the passed `FileClassification`. Why: §8 classify→chunk hand-off.
7. **`test_chunk_docs_register_value`** — Asserts: `register` == the v0 default (design Q3). Why: §5 closed-set field populated.
8. **`test_chunk_docs_deterministic`** — Asserts: two calls → identical tuple, source order. Why: determinism posture.
9. **`test_chunkdraft_closed_sets_match_chunk_contract`** — `# spec(§5)` — Asserts: `get_args(ChunkDraft.model_fields["doc_or_code"].annotation) == get_args(Chunk.…)` for `doc_or_code`/`ownership`/`register`. Why: §5 frozen-`Chunk` alignment (extends LESSON 19).
10. **`test_chunkdraft_fields_subset_of_chunk`** — `# spec(§5)` — Asserts: `ChunkDraft`'s chunk-mirroring field names ⊆ `Chunk`'s field set. Why: §5 no draft field that can't fold into `Chunk`.
11. **`test_chunkdraft_rejects_unknown_closed_set`** — `# spec(§5)` — Asserts: `ChunkDraft(register="loud", …)` raises `ValidationError`. Why: §5 closed-set integrity / parse-don't-trust.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes: NONE — `Chunk` and `Anchor` are FROZEN shared contracts.** This slice must produce their data **without** adding/renaming any field. If a needed field is absent, that is a **cross-track Finding → escalate**, never a local contract edit.
- **`ChunkDraft` is an internal ingest-stage type** (like `DiscoveredFile`/`FileClassification`) — not an Appendix-A contract, no schema-snapshot/freeze obligation. It IS load-bearing across the spine (2.3 redactor, 2.4 pipeline, Phase-3 embed consume it) — design it deliberately.
- **Orchestrator doc rows to write hot (Step 9):** likely an **architecture-doc-note** extending §8: (a) the chunk-stage emits `ChunkDraft` (frozen `Chunk`/`Anchor` assembled at 2.4 — both all-required), and (b) the **v0 `register` semantics** + the **anchor span syntax** this producer owns. Confirm at Step 9. The cross-doc table's `Chunk`/`Anchor` rows may get a note naming `ingest/chunk.py` as the Phase-2 producer.

## Things to flag at Step 2.5
1. **`ChunkDraft` shape.** My default: a frozen Pydantic `BaseModel(extra="forbid")` carrying `{source_path, doc_or_code, producer, doc_type, ownership, register, text, anchor, target_line_start, target_line_end, target_symbol|None}`. Open question: include `content_hash`/`chunk_id`/`vector` placeholders? My vote: **NO** — `content_hash` is computed at 2.4 over the **post-redaction** `text` (redact precedes embed/write in §8), and ids/vector/SHAs are ingest/embed-context (2.4/Phase-3). The draft holds only chunk-derivable data.
2. **Anchor span syntax.** My default: **line-only — `"start-end"` (multi-line), `"N"` (single line)**, 1-based. The `Anchor` contract also permits `line:col` (`"10:5-12:8"`), but docs are line-granular; line:col can arrive additively for code (2.2b) if the AST gives columns. Pin the v0 string format here.
3. **`register` (Literal `plain|deep`) v0 value + meaning.** The architecture does not pin what sets it. My default: **docs → `"plain"` in v0**; `"deep"` is for context-augmented/Contextual-Retrieval chunks (the `context_blurb` stage, post-chunk) — revisit when context-augment + code chunks land. Flag the v0 meaning as the §8 architecture-doc-note.
4. **Heading-split granularity.** My default: split at **every** heading level; a section spans from its heading line through the line before the next heading of **any** level (nested subsections become their own adjacent sections). Simpler + deterministic than building a heading tree; revisit if retrieval wants hierarchical sections.
5. **"Late-chunking" — any 2.2 action?** My default: **no** — 2.2 sets chunk **boundaries** only (heading-split); late-chunking (embed full-doc context, pool per chunk) is a Phase-3 **embed** concern. 2.2 preserves source order so Phase-3 can late-chunk. Noted, not implemented here.
6. **Emit `Anchor` models now, or span data only?** My default: **span data in `ChunkDraft`**; assemble the frozen `Anchor` at 2.4 (it needs `anchor_id`/`project_id`/`last_resolved_sha` from the IdGen/ingest seams, unavailable at chunk-time). If the team prefers 2.2 to emit `Anchor` models, ingest-context must be threaded into the chunk stage — heavier coupling; my vote is to keep 2.2 context-free.

## Dependencies + sequencing
- **Depends on:** 1.2 (`Chunk` frozen), 1.3 (`Anchor` frozen), 2.1 (`FileClassification` — the chunk input). All landed.
- **Blocks:** 2.2b (code-AST chunking reuses `ChunkDraft` + the span/anchor helpers), 2.3 (redactor runs on `ChunkDraft.text`), 2.4 (`add` pipeline assembles `ChunkDraft` → frozen `Chunk` + `Anchor`).

## Estimated commit count
**1.** Docs chunking + the `ChunkDraft` contract + anchor-span helpers are one logical unit (pure-Python, same module). **No safety invariant** (the HostPort runtime proof is 2.4/2.S; the redactor is 2.3). 2.2 is atomized into 2.2a (this) + 2.2b (code AST + tree-sitter) because the code path adds two heavy deps and is large on its own — each gets its own commit.

## Lessons-logged candidates anticipated
- **Convention candidate** — "A mid-pipeline stage whose frozen output contract is all-required emits an internal `*Draft` of the derivable subset; the frozen model is assembled at the stage that has the full context (ids/SHA/vector) — never partially-construct a frozen contract."
- **Architecture-doc-note candidate** — pin into §8: the chunk-stage `ChunkDraft` boundary, the v0 `register` semantics, and the anchor span syntax.
- **Future TODO — operational** — hierarchical/nested doc sections; line:col spans for code; very-large-section sub-splitting (token budget).

## How to invoke
1. **Read this brief end-to-end** — especially "Things to flag at Step 2.5".
2. **`/tdd anchor_aware_chunking_docs`** (the spine implementer session is already oriented).
3. **Step 0 (Restate)** — confirm against the Feature line.
4. **Step 1 (Identify files)** — confirm against "Files expected to touch".
5. **Step 2.5** — send the test-design write-up + acceptance→test coverage map with answers to the six design questions (defaults or push-back). **Confirm no frozen `Chunk`/`Anchor` field is added** — a missing field is a Finding, not a local edit.
6. **Step 9 (summarize)** — surface the §8 architecture-doc-note (register/span/ChunkDraft) and anything beyond the anticipated candidates.
