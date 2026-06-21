# spine-001 — Phase 2 ingest surfaces (discover · classify · chunk · redactor)

- **Date:** 2026-06-21
- **Phase:** 2 (Ingestion + Redactor — spine track)
- **Predecessor:** fork from `track/contract` (terminal handoff `docs/team-handoffs/contract-002-2026-06-21-fork-gate-complete.md`; Phase 0+1 frozen on `main`)
- **Successor:** _(next spine implementer session — picks up the 2.4 + 2.S bundle)_
- **Branch:** `track/spine` · **Commits:** `dc5a9aa` (2.1) · `c10ea79` (2.2a) · `723db12` (2.3 ★SAFETY) · `434c46a` (2.2b)

## Why this session existed

First spine session after the fork. Build the front of the §8 ingest pipeline — source-agnostic
discovery, classification, anchor-aware chunking (docs + code), and the catchable-set redactor — all
against the frozen Phase-1 contracts + `Fake*` providers, leaving the `add` orchestration + the
HostPort runtime safety proof (2.4/2.S) for the successor.

## What was built

### Files created
- `core/ingest/__init__.py` — package marker for the §8 ingest pipeline.
- `core/ingest/discover.py` — `discover(root, *, extra_ignores=())` → sorted `tuple[DiscoveredFile]`; gitwildmatch `.gitignore`+`.brainignore` (pathspec), always-exclude `.git/`+`.project-brain/`, no symlink-follow, hardened ignore-file reads (1 MiB cap + `errors="replace"`), `NotADirectoryError` on non-dir root.
- `core/ingest/classify.py` — `classify(file, *, root=None)` → frozen `FileClassification` (doc_or_code/producer/doc_type/ownership); closed sets pinned byte-identical to the frozen `Chunk` via a `get_args` drift test.
- `core/ingest/chunk.py` — `ChunkDraft` (frozen internal stage record) + `chunk_docs()` (ATX heading-split, fenced-code immune, cap-bounded line-tiling) + `chunk_code()` (vendored-AST leaf+complement mapping) + shared `_drafts_from_sections` tiler.
- `core/ingest/redactor.py` — `CatchableSetRedactor` implementing the frozen `Redactor` Protocol (★SAFETY rule #2): PEM/prefix-token/JWT, URL-credential, assignment-value (allowlist-before-entropy) passes; fail-closed; pure; idempotent (exact marker match).
- `core/ingest/_code_hierarchy.py` — VENDORED MIT `CodeHierarchyNodeParser` (verbatim + license/provenance header + 3 flagged VENDOR-EDITs); lint/type-excluded.
- `core/ingest/pytree-sitter-queries/tree-sitter-{python,typescript,cpp,php}-tags.scm` — vendored MIT tag-query files for the 4 wired languages.
- `core/tests/ingest/{__init__,test_discover,test_classify,test_chunk,test_redactor}.py` — the slice test suites (29 + 38 + 21 across the slices).
- `ci/eval/redaction_fuzz/gate.py` — standalone hard-gate runner for the redaction fuzz harness against the real engine (ci imports core, never reverse).

### Files modified
- `core/pyproject.toml` — runtime deps: `pathspec`, `llama-index-core`, `tree-sitter`, `tree-sitter-{python,typescript,cpp,php}`. `ingest` registered in isort/mypy. ruff `extend-exclude` + mypy overrides for the vendored file; mypy `ci.*` + `llama_index.*` overrides.
- `core/uv.lock` — locked the new deps.

## Decisions made
- **2.1:** entropy/vendor heuristics are name/path-based v0; `pathspec` pinned `>=0.12,<1` (`gitwildmatch` factory; the `gitignore` rename is unreleased 1.0.0 — Context7-verified).
- **2.2a:** `ChunkDraft` is an internal stage type (not an Appendix-A contract); frozen `Chunk`/`Anchor` assembled at 2.4 (they're all-required: ids/SHA/vector). Cap discipline: every draft ≤ `TEXT_MAX_LEN` via line-tiling + char hard-split. Anchor span syntax v0 = `"N"`/`"start-end"`, 1-based.
- **2.3 (★SAFETY):** allowlist (git-SHA/ULID/UUID) runs BEFORE the entropy detector (cardinal §18 residual protection); entropy is CONTEXTUAL (assignment values only) → 0% FP. Idempotence keys on EXACT marker match (a prefix check is input-spoofable). Fail-CLOSED on internal error. D-A5/D-A6 built against PROPOSED 0.95/0.05 uniform (owner ratification pending). Fuzz gate: recall 1.000, FP 0.000, git-SHA FP 0%, all 3 sinks.
- **2.2b:** the architecture-pinned pack is deprecated/un-importable → owner chose Option C (VENDOR the MIT file). Runtime tree-sitter binding incompatibility → Option B (standard `tree_sitter` + individual grammar packages + a flagged loader edit). Anchor accuracy BY CONSTRUCTION: leaf full nodes (verbatim text + real span + qualified symbol) + line-tiled complement; skeleton nodes skipped. Dep set pruned to the 4 parser-supported languages.

## Decisions explicitly NOT made (deferred)
- **2.4 + 2.S NOT started** (cycle at WARN before the heavy safety bundle) — the `add` pipeline + the ★§14 HostPort runtime allowlist proof + real `StandaloneHost` (Acceptance(2)-gated, the cardinal Rule-#4 proof) are the successor's flagship work.
- **Parser-config extension to the full 12 languages** — substantial per-language signature/comment tuning; a tracked follow-up (owner priority: JavaScript + Rust first). v0 ships 4-with-hierarchy + 8 via line-tiling fallback (full coverage, no hierarchy).
- **CONTENT sanitization** (Trojan-Source bidi + NUL/C0/DEL) — kept OUT of the 2.3 secret engine; a 2.4/sibling concern (LESSON 14).

## TDD compliance
Clean. Every slice RED-confirmed before GREEN; the 2.2b `_raw_specs` trim refactor was driven by the failing anchor-accuracy invariant test (`test_chunk_code_draft_text_matches_source_span`) while the docs tests stayed green. The vendored `_code_hierarchy.py` is third-party (lint/type-excluded, not authored here). No violations.

## Cross-doc invariant audit (multi-track → memory check)
No frozen Appendix-A model field changed this session. `DiscoveredFile`/`FileClassification`/`ChunkDraft`/`CatchableSetRedactor` are new INTERNAL ingest types (no schema-snapshot/cross-doc row). The frozen `Chunk`/`Anchor`/`Redactor` contracts were NOT modified (the frozen-contract guard held; `ChunkDraft` mirrors `Chunk`'s closed sets via a `get_args` pin without touching `Chunk`). All architecture-doc-NOTE candidates (§8 v0 vocab; pinned-pack→vendored; redactor marker/gate; D-A5/A6) were flagged at Step 9 and confirmed received by the orchestrator (its `/orchestrate-end` routes them).

## Reachability
All ingest functions are pure; production callers land at **2.4** (`add` pipeline dispatches doc/code → `chunk_docs`/`chunk_code`, runs `redact()` at the persist sink, assembles frozen `Chunk`+`Anchor`). Test-only reachability this session is the DECLARED deferral (each slice's Step-7.5). The redaction **fuzz gate IS a live entry point** (pytest gate test + `ci/.../gate.py`). No silent unwired gaps — the deferral is intentional + documented; 2.4 wires the surfaces.

## Open follow-ups
- **★ 2.S (Acceptance(2)-gated, cardinal):** §14 INV-allowlist FULL runtime proof + real `StandaloneHost` — lands with the first mutator (2.4). Phase 2 does NOT close without it.
- **★ File-level malformed-content resilience:** pre-redaction NUL/C0/DEL hard-rejects at `ChunkDraft`/`Chunk` (TextStr) and aborts a whole file → 2.3 redactor strip/quarantine + 2.4 pipeline R-PARTIAL file-error boundary (pinned by `test_chunk_docs_nul_byte_raises_at_boundary`; LESSON 14).
- **Redactor (2.3):** corpus-coverage gap — add comma/&/brace-embedded + spaces-in-quoted + URL-under-sensitive-key cases to `ci/eval/redaction_fuzz/generator` so recall 1.000 EXERCISES them (unit tests do; the corpus doesn't); spaces-in-quoted/YAML-block secret values; input-size cap at the persist sink (10MB-paste throughput); `_ENTROPY_MIN_BITS=4.0` thin-margin calibration; **D-A5/D-A6 owner ratification** (built on PROPOSED default).
- **2.2b:** parser-config extension to reach the 12 (JS+Rust first); vendored-`assert`-under-`-O` + periodic upstream re-sync; oversized-scope coverage assertion; mid-segment symbol truncation.
- **2.1:** nested per-dir `.gitignore`; v0 vocab gaps (`__pycache__`, `bun.lockb`, `go.sum`); `IdentityStr` 1024-cap path skip-vs-abort; unbounded in-memory file list bound; case-insensitive `.git`/`.project-brain` floor (INFO).
- **2.2a:** setext/`.rst`/`.adoc` heading detection; token-aware (vs char) splitting; line:col anchor spans for code.
- **Env:** `pip-audit` tool absent — install before the Phase-2-exit dep-audit gate (12→ now lighter dep footprint after the 2.2b prune, but llama-index-core/tree-sitter are new heavy deps).

## How to use what was built
`from ingest.discover import discover` · `from ingest.classify import classify` · `from ingest.chunk import chunk_docs, chunk_code` · `from ingest.redactor import CatchableSetRedactor`. All pure + deterministic; the 2.4 `add` pipeline composes them. Run the redaction gate standalone: `uv --project core run python -m ci.eval.redaction_fuzz.gate`.
