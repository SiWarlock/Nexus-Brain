# /tdd brief — anchor_aware_chunking_code

## Feature
The **code** chunking path of the §8 anchor-aware chunk stage: split source-code files AST-aware via the **VENDORED** `CodeHierarchyNodeParser` (MIT — copied verbatim into `core/ingest/_code_hierarchy.py`) into anchored `ChunkDraft`s scoped to code structures (function/class/method, with the deep parent/child hierarchy preserved), with a **deterministic line-tiling fallback** (the 2.2a cap-bounded helper) for unsupported languages or parse failures so no file is ever dropped (R-PARTIAL). Reuses the `ChunkDraft` contract + the cap/anchor helpers from 2.2a.

## Use case + traceability
- **Task ID:** 2.2b
- **Architecture sections it implements:** `ARCHITECTURE.md §8` (chunk stage — "code AST via `CodeHierarchyNodeParser`, pinned + tree-sitter fallback"), `ARCHITECTURE.md §5` (the frozen `Chunk` field contract whose chunk-derivable subset + closed sets `ChunkDraft` mirrors).
- **Related context — REMEDIATION C (owner-decided):** The architecture-pinned `CodeHierarchyNodeParser` ships only in `llama-index-packs-code-hierarchy`, which the prior validation (this slice's first pass) found **DEPRECATED + un-importable on Python 3.12** (its `__init__` eagerly imports an Agent pack → `llama_index.core.llama_pack`, a module removed from current core). The parser LOGIC itself is fine: `code_hierarchy.py` (≈35 KB, **MIT**) imports only `llama_index.core.*` (NodeParser/schema/CodeSplitter/bridge/callbacks/extractors/utils) + tree-sitter — no Agent-pack/llms refs. **Owner decision: Option C — VENDOR `code_hierarchy.py` into `core/ingest/_code_hierarchy.py`**, retain the MIT notice. Rationale (build to intent): the deep parent/child hierarchy (class→method nesting, walk-up retrieval) is the **load-bearing capability for north-star anchored answers** — it must be preserved; alternatives lose it (Chonkie = flat, no nesting tree) or are unproven narrow new deps (ASTChunk). C reuses already-committed deps (`llama-index-core` — Phase-5 Workflows; + `tree-sitter-language-pack`) with proven logic = lowest risk.
- **STANDING INSTRUCTION (owner condition):** proceed with C, BUT if during implementation you find a *maintained* library that genuinely beats the vendored parser on a **material capability** (esp. the hierarchy/walk-up), STOP and surface it to the orchestrator → lead BEFORE finalizing — do not plow ahead, and do not silently swap. The owner will reconsider only on a genuine improvement.
- **Prior state:** 2.2a landed `ChunkDraft` (frozen internal type) + `chunk_docs()` + the cap-bounded sub-split helpers (`_raw_specs`/`_merge_blanks`, the `_Section`/`_Spec` NamedTuples) + `TEXT_MAX_LEN`/`IDENTITY_MAX_LEN` cap-respect + `ANCHOR_SPAN_FIELDS` — all in `core/ingest/chunk.py`. This slice adds `chunk_code()` to the same module.

## Acceptance criteria (what "done" means)
- [ ] `core/ingest/_code_hierarchy.py` is the vendored MIT `CodeHierarchyNodeParser`, **copied verbatim** with the **original MIT copyright + license notice retained** in the file header (+ a one-line provenance comment: source package + version it was vendored from). No logic edits beyond what's strictly needed to import under current `llama-index-core` (any such edit noted in-file + flagged at Step 9).
- [ ] The vendored file is **excluded from `mypy --strict` + ruff** (it is vendored-not-authored third-party code) — config-only (the `_`-prefix + a scoped exclude/per-module override); **our wrapper/seam in `chunk.py` stays strict**.
- [ ] `chunk_code(text, classification, source_path)` returns a deterministic `tuple[ChunkDraft, ...]`, one (or more, under the cap) draft per code scope (function / class / method), in source order.
- [ ] Each code `ChunkDraft` carries the same fields as a docs draft: `text`, `source_path`, the four classification axes, `register`, `anchor` span string, `target_line_start`/`target_line_end` (1-based, `end >= start`), and `target_symbol` = the **qualified scope name** the parser exposes (e.g. `ClassName.method`), else `None`.
- [ ] Every `ChunkDraft.text` ≤ `TEXT_MAX_LEN` and every `target_symbol` ≤ `IDENTITY_MAX_LEN` — an over-cap code scope is sub-split with the **same line-tiling guarantee** as 2.2a (contiguous, gap-free, full coverage; over-long symbol truncated). Reuse the 2.2a helper; do not re-implement.
- [ ] **Fallback (R-PARTIAL):** a file whose language is unsupported, OR that raises any parse error, is chunked by the 2.2a line-tiling fallback (whole-file → cap-bounded drafts, `target_symbol=None`) — never dropped, never raised past the function. A reachable test forces the fallback path.
- [ ] The parser invocation is **deterministic** (same input → identical draft tuple) and **isolated behind a small internal seam** so it is mockable in tests and the fallback is cleanly triggerable.
- [ ] Line spans are derived deterministically (char-offset → 1-based line, the 2.2a convention) — code + docs drafts use one span representation.
- [ ] `get_args` closed-set drift + the `ANCHOR_SPAN_FIELDS` subset pins from 2.2a still hold (no `ChunkDraft` shape change).
- [ ] `/preflight` clean (ruff · format · `mypy .` · pytest); **`-W error` import clean** — the vendored module + its deps import with NO `DeprecationWarning` (the whole point of C: we escape the broken/deprecated pack `__init__`).

## Wiring / entry point (Step 7.5)
**none — wiring lands in 2.4.** `chunk_code()` is a pure function alongside `chunk_docs()`; the `add` pipeline (`core/ingest/pipeline.py`, Task 2.4) dispatches `doc_or_code == "code"` → `chunk_code`, else `chunk_docs`, then assembles the frozen `Chunk` + `Anchor` from each `ChunkDraft` + ingest-context. Reachability at this slice is intentionally test-only (declared deferral).

## Files expected to touch
**New:**
- `core/ingest/_code_hierarchy.py` — the vendored MIT `CodeHierarchyNodeParser` (verbatim + MIT notice + provenance comment).
- (No new test file — code-path tests extend the 2.2a test module.)

**Modified:**
- `core/ingest/chunk.py` — add `chunk_code(...) -> tuple[ChunkDraft, ...]` + the parser seam (wrapping the vendored parser) + the AST-node→span/symbol mapping; reuse the existing cap/tiling helpers.
- `core/tests/ingest/test_chunk.py` — add the code-path tests.
- `core/pyproject.toml` — add `llama-index-core` + `tree-sitter-language-pack` (pins proposed at Step 2.5) + the lint/type exclude for `_code_hierarchy.py`. + `uv.lock`.

If implementation needs files/deps beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests added to `core/tests/ingest/test_chunk.py` (tag each `# spec(§8)` except the contract guards `# spec(§5)`):

1. **`test_chunk_code_splits_by_scope`** — Asserts: a Python source with 2 functions + 1 class → drafts scoped per top-level structure, source order. Why: §8 code-AST chunking.
2. **`test_chunk_code_target_symbol_is_scope_name`** — Asserts: `target_symbol` == the function/class (qualified) name the parser exposes. Why: §8 anchor symbol for code.
3. **`test_chunk_code_line_span_bounds_scope`** — Asserts: `target_line_start/end` bound the scope's lines (1-based, `end>=start`); `anchor` == the `"start-end"`/`"N"` string. Why: §8 anchor-aware spans (shared with docs).
4. **`test_chunk_code_carries_classification`** — Asserts: each draft's four axes + `source_path` mirror the input. Why: §8 classify→chunk hand-off.
5. **`test_chunk_code_unsupported_language_falls_back`** — Asserts: a file in a parser-unsupported language → line-tiling fallback drafts (`target_symbol=None`), full coverage. Why: §8 tree-sitter/fallback, R-PARTIAL.
6. **`test_chunk_code_parse_error_falls_back`** — Asserts: a forced parser exception (via the seam) → line-tiling fallback, no exception escapes. Why: §8 R-PARTIAL (never drop a file).
7. **`test_chunk_code_oversized_scope_subsplit`** — Asserts: a code scope > `TEXT_MAX_LEN` → multiple cap-bounded drafts, contiguous + full coverage (reuses the 2.2a tiling). Why: §5 `TextStr` cap honored.
8. **`test_chunk_code_oversized_symbol_truncated`** — Asserts: a scope name > `IDENTITY_MAX_LEN` → truncated `target_symbol` (no crash). Why: §5 `IdentityStr` cap honored.
9. **`test_chunk_code_deterministic`** — Asserts: two calls → identical tuple. Why: determinism posture (AST parse is deterministic → `/tdd`-eligible).
10. **`test_chunk_code_empty_file_returns_empty`** — Asserts: empty/whitespace-only source → `()`. Why: §8 no-content edge (mirrors docs).
11. **`test_chunk_code_register_value`** — Asserts: code drafts get the v0 `register` value (design Q4). Why: §5 closed-set field populated.
12. **`test_chunkdraft_contract_pins_still_hold`** — `# spec(§5)` — Asserts: the `get_args` closed-set + `ANCHOR_SPAN_FIELDS` subset pins from 2.2a are unchanged. Why: §5 no regression to the draft↔`Chunk` alignment.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes: NONE.** `Chunk`/`Anchor` frozen; `ChunkDraft` unchanged from 2.2a (a shape change is a Finding-class regression — flag it). This slice adds a producer, not a contract.
- **Orchestrator doc rows to write hot (Step 9):** (1) the **atomic §8 + tech-stack-table edit** recording the pinned-pack reference → **vendored MIT copy** (owner-decided Option C) — orchestrator writes this integration-routed, **same round as the 2.2b commit** (per the lead). (2) extend the pending §8 chunk-stage note with the code path + the fallback ladder. (3) Likely cross-doc note: `chunker_version` (a `ProjectManifest` field) records the vendored-parser provenance/version — confirm at Step 9 whether 2.2b stamps it or 2.4 does (my read: 2.4, at manifest assembly).
- **New dependencies** (`llama-index-core` + `tree-sitter-language-pack` + transitive tree-sitter) — flag at Step 9; first heavy framework deps; relevant to the Phase-2-exit `pip-audit` gate + CI install time + arm64 wheel availability (the prior validation already confirmed arm64 wheels resolve).

## Things to flag at Step 2.5
1. **VENDOR + VERIFY FIRST (before the full suite).** Copy `code_hierarchy.py` verbatim into `core/ingest/_code_hierarchy.py` (MIT notice + provenance comment retained), then confirm via a throwaway import that (a) it imports clean under the pinned current `llama-index-core` + `tree-sitter-language-pack` on Python 3.12 with **NO `DeprecationWarning`** (the C win), (b) it exposes per-node **line/char spans + scope name** in node metadata (the data the anchor needs), (c) it parses a real Python sample into the nesting hierarchy. If a core API the NodeParser uses was ALSO removed in current core (prior analysis says NOT — only the pack `__init__`/AgentPack chain is broken), note the minimal import-fix in-file + flag it. If C proves unworkable for a reason the analysis missed, STOP and flag-back (don't substitute silently).
2. **Dependency pins.** My default: pin `llama-index-core` to the line the vendored parser needs (the prior validation saw 0.14.22 resolve) + `tree-sitter-language-pack` tightly; lockfile captures the transitive tree. Propose exact pins from PyPI at Step 2.5.
3. **"tree-sitter fallback" semantics.** My default: a **two-tier** fallback — (1) the vendored AST chunker; (2) on unsupported-language or parse-error → the **2.2a line-tiling** fallback. No raw-tree-sitter intermediate tier in v0 (the vendored parser is already tree-sitter-backed; a third tier is complexity without v0 payoff) — flag a raw-tree-sitter tier as a future-TODO. Confirm.
4. **`register` for code drafts.** My default: code → `"plain"` in v0 (same as docs); `"deep"` reserved for the post-chunk context-augment stage. Consistent with 2.2a.
5. **Scope granularity + hierarchy.** The owner's intent is to PRESERVE the deep parent/child hierarchy. My default for v0: flatten the parser's hierarchy to a draft list in source order (the `ChunkDraft` contract has no parent-child field), but **preserve the qualified `target_symbol`** (`Class.method`) so the nesting is recoverable from the symbol path; do NOT collapse nested scopes into one draft. Capturing explicit parent-child chunk links is a future-TODO (needs a contract field — escalate if v0 needs it). Confirm this honors the intent without a contract change.
6. **Lint/type posture for the vendored file.** My default: exclude `_code_hierarchy.py` from `mypy --strict` + ruff (vendored-not-authored; config-only per-module override/exclude); keep the `chunk.py` seam strict. Confirm (alternative — make the 35 KB third-party file pass `--strict` — is high-cost, low-value).

## Dependencies + sequencing
- **Depends on:** 2.2a (`ChunkDraft` + the cap/tiling/anchor helpers — landed `c10ea79`), 1.2 (`Chunk`), 1.3 (`Anchor`).
- **Blocks:** 2.4 (`add` pipeline dispatches doc/code → the two chunkers, assembles frozen `Chunk`+`Anchor`). Completes task `### 2.2` (anchor-aware chunking) together with 2.2a.

## Estimated commit count
**1.** The code chunking path + the vendored parser are one logical unit, extend the 2.2a module, **no safety invariant** (HostPort proof is 2.4/2.S; redactor is 2.3). The vendored file rides this commit (with its MIT notice). One Step-10 commit.

## Lessons-logged candidates anticipated
- **Convention candidate** — "When an architecture-pinned dependency is deprecated/un-importable but its LOGIC is sound + permissively licensed, VENDOR the single needed module (license notice retained) behind an internal seam, exclude it from strict lint, and pin only the libs it actually imports — rather than fighting a broken package `__init__` or silently swapping tools."
- **Architecture-doc-note candidate** — §8 + tech-stack: pinned-pack → vendored MIT copy; the code-AST fallback ladder; `chunker_version` provenance stamping.
- **Future TODO — operational** — raw-tree-sitter intermediate fallback tier; explicit parent-child chunk links (needs a contract field); line:col spans now that the AST exposes columns; per-language tuning; periodic re-sync of the vendored file vs. upstream.

## How to invoke
1. **Read this brief end-to-end** — especially Step-2.5 Q1 (vendor + verify FIRST) + the owner's standing instruction (surface a genuinely-better maintained lib before finalizing).
2. **`/tdd anchor_aware_chunking_code`** (the spine implementer session is already oriented).
3. **Step 0 (Restate)** — confirm against the Feature line (vendored parser, not the pip pack).
4. **Step 1 (Identify files)** — confirm the vendored file + the `chunk.py` extension.
5. **Step 2.5** — after vendoring + verifying, send the test-design write-up + acceptance→test coverage map with answers to the six design questions.
6. **Step 9 (summarize)** — surface the vendored-file provenance/any import-fix, the deps (pins + transitive weight), the §8 doc-edit, and `chunker_version` ownership.
