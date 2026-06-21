# /tdd brief — discovery_and_classification

## Feature
The front of the §8 ingest pipeline: **source-agnostic file discovery** under a repo root (honoring `.gitignore` + `.brainignore`) and **classification** of each discovered file into the four ingest axes that feed the frozen `Chunk` contract — `doc_or_code`, `producer`, `doc_type`, `ownership`.

## Use case + traceability
- **Task ID:** 2.1
- **Architecture sections it implements:** `ARCHITECTURE.md §8` (Discover → classify, source-agnostic, `.gitignore`+`.brainignore`, producer/`doc_type`/owned·foreign·supplemental), `ARCHITECTURE.md §5` (the `Chunk` field contract whose closed sets `doc_or_code`/`ownership` the classifier's output must match).
- **Related context:** First spine slice post-fork; `core/ingest/` is greenfield (does not exist yet). `Chunk` (`core/model/chunk.py`) is frozen: `doc_or_code: Literal["doc","code"]`, `producer: IdentityStr` (open-ended), `doc_type: IdentityStr` (open-ended), `ownership: Literal["owned","foreign","supplemental"]`. `IdentityStr` lives in `core/_types.py`. This slice produces the **classification inputs** the `add` pipeline (Task 2.4) later folds into `Chunk`s — it does NOT build `Chunk`s itself (those need `chunk_id`/`vector`/`anchor`, minted downstream).

## Acceptance criteria (what "done" means)
- [ ] `discover(root)` returns every regular file under `root` as a deterministic, sorted tuple of `DiscoveredFile` (relative POSIX paths).
- [ ] Discovery honors a root-level `.gitignore` AND a root-level `.brainignore` (gitignore/gitwildmatch syntax); a path matching either is excluded.
- [ ] Discovery ALWAYS excludes `.git/` (and the brain's own `.project-brain/` output dir) regardless of ignore files.
- [ ] Discovery is source-agnostic: `.github/` and other dotfile dirs ARE discovered (only the explicit always-exclude set is dropped) — a dotfile dir is not blanket-excluded.
- [ ] Discovery does not follow symlinks (no escape outside `root`, no cycles).
- [ ] `classify(file)` returns a frozen `FileClassification` with `doc_or_code` ∈ {doc, code}, `ownership` ∈ {owned, foreign, supplemental}, and non-empty `producer` / `doc_type`.
- [ ] `doc_or_code`: known doc extensions (`.md/.rst/.txt/.adoc`) → `doc`; everything else → `code`.
- [ ] `ownership`: a path under a known-vendor dir → `foreign`; a generated/auxiliary file (lockfiles) → `supplemental`; otherwise → `owned`.
- [ ] `producer`: a name/path-based generated marker (lockfiles, `*.lock`, `*_pb2.py`) → `generated`; otherwise → `human`.
- [ ] `doc_type`: filename-mapped for docs (`README*`→`readme`, `ARCHITECTURE*`→`architecture`, `CHANGELOG*`→`changelog`, ADR-shaped→`adr`, else `guide`); code → `source`.
- [ ] **Vocab-alignment guard:** `FileClassification`'s `doc_or_code` and `ownership` `Literal` args are EXACTLY `Chunk`'s — a drift test (`typing.get_args`) fails if the frozen contract and the classifier diverge.
- [ ] All unit tests in `core/tests/ingest/test_discover.py` + `core/tests/ingest/test_classify.py` pass.
- [ ] `/preflight` clean (ruff · format · `mypy .` · pytest).

## Wiring / entry point (Step 7.5)
**none — wiring lands in 2.4.** `discover()` and `classify()` are pure functions; their production caller is the `add` ingest pipeline (`core/ingest/pipeline.py`, Task 2.4), which composes discover → classify → chunk → … . This slice lands the two functions + their unit tests; Task 2.4 wires them behind the `add` CLI path. Reachability at this slice is intentionally test-only (declared deferral).

## Files expected to touch
**New:**
- `core/ingest/__init__.py` — package marker.
- `core/ingest/discover.py` — `DiscoveredFile` (frozen) + `discover(root, *, extra_ignores=()) -> tuple[DiscoveredFile, ...]`.
- `core/ingest/classify.py` — `FileClassification` (frozen) + `classify(file, *, root=None) -> FileClassification`.
- `core/tests/ingest/__init__.py`
- `core/tests/ingest/test_discover.py`
- `core/tests/ingest/test_classify.py`

**Modified:**
- `core/pyproject.toml` — add the `pathspec` runtime dependency (gitwildmatch ignore matching). First runtime dep beyond `pydantic` — flag at Step 9.

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/ingest/test_discover.py` (tag each `# spec(§8)`):

1. **`test_discover_finds_regular_files`** — Asserts: every regular file in a temp tree is returned. Why: §8 source-agnostic discovery.
2. **`test_discover_honors_gitignore`** — Asserts: a path matching a root `.gitignore` pattern is absent. Why: §8 `.gitignore` honoring.
3. **`test_discover_honors_brainignore`** — Asserts: a path matching a root `.brainignore` pattern is absent (and combines with `.gitignore`). Why: §8 `.brainignore` honoring.
4. **`test_discover_always_excludes_git_dir`** — Asserts: nothing under `.git/` is returned even with empty/absent ignore files. Why: §8 always-exclude floor.
5. **`test_discover_includes_github_dir`** — Asserts: a `.github/workflows/*.yml` file IS returned. Why: §8 source-agnostic (dotfile dirs not blanket-dropped).
6. **`test_discover_deterministic_sorted_order`** — Asserts: two calls on the same tree return byte-identical tuples in sorted order. Why: determinism posture (reproducible ingest).
7. **`test_discover_does_not_follow_symlinks`** — Asserts: a symlink (esp. to a dir outside `root`) is not traversed. Why: §8 containment / no-escape.

Tests in `core/tests/ingest/test_classify.py` (tag each `# spec(§8)`, except the vocab guard `# spec(§5)`):

8. **`test_classify_doc_vs_code`** — Asserts: `.md`→`doc`, `.py`→`code`. Why: §8 `doc_or_code` split.
9. **`test_classify_doc_or_code_fallback_unknown_ext`** — Asserts: an unknown extension → `code`. Why: §8 source-agnostic fallback (design Q4).
10. **`test_classify_ownership_owned_default`** — Asserts: a first-party `src/foo.py` → `owned`. Why: §8 ownership default.
11. **`test_classify_ownership_foreign_vendored`** — Asserts: `node_modules/x/y.js` → `foreign`. Why: §8 foreign/vendored.
12. **`test_classify_ownership_supplemental_generated`** — Asserts: `uv.lock` → `supplemental`. Why: §8 supplemental/auxiliary.
13. **`test_classify_producer_human_default`** — Asserts: ordinary source → `human`. Why: §8 producer default.
14. **`test_classify_producer_generated_marker`** — Asserts: a lockfile / `*_pb2.py` → `generated`. Why: §8 producer detection v0.
15. **`test_classify_doc_type_known_names`** — Asserts: `README.md`→`readme`, `ARCHITECTURE.md`→`architecture`, a `.py`→`source`. Why: §8 `doc_type` mapping.
16. **`test_classification_vocab_matches_chunk_contract`** — Asserts: `get_args(FileClassification.model_fields["doc_or_code"].annotation) == get_args(Chunk.model_fields["doc_or_code"].annotation)` and same for `ownership`. Why: §5 frozen-`Chunk` closed-set alignment (anti-drift; mirrors `test_chunk_closed_set_fields_reject_unknown`).
17. **`test_classification_rejects_unknown_closed_set`** — Asserts: constructing `FileClassification(doc_or_code="image", …)` raises `ValidationError`. Why: §5 closed-set integrity / parse-don't-trust.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** none. `DiscoveredFile` + `FileClassification` are **internal ingest-stage types**, not Appendix-A contracts — no schema-snapshot test, no cross-doc row. They reuse `IdentityStr` and mirror (do not modify) `Chunk`'s closed sets.
- **Not a shared-contract (import-DAG-seam) model** — the classifier consumes the frozen `Chunk` contract but adds no shared contract; no snapshot-test obligation.
- **Orchestrator doc rows to write hot (Step 9 routing):** none required. **Likely architecture-doc-note candidate:** pin the v0 `owned/foreign/supplemental` + `producer`/`doc_type` heuristic vocabulary into `ARCHITECTURE.md §8` so Task 2.4 and the sync-phase drift-radar (owned-doc-refresh is ownership-gated) share one definition. Confirm at Step 9.
- **New runtime dependency** (`pathspec`) — flag at Step 9 (first dep beyond `pydantic`; relevant to the Phase-2-exit `pip-audit` gate).

## Things to flag at Step 2.5
1. **gitignore matching — `pathspec` (gitwildmatch) vs hand-roll?** My default vote: **`pathspec`** — it replicates git's wildmatch semantics (negation, anchoring, dir-only patterns, `**`); hand-rolling gitignore is a well-known footgun. Cost: the first runtime dep beyond `pydantic` (tiny, pure-Python). Confirm the `PathSpec.from_lines("gitwildmatch", …)` API via Context7 if unsure.
2. **Ignore scope — root-level `.gitignore`+`.brainignore` only, or nested per-directory `.gitignore` too?** My default vote: **root-level only for v0** — covers the common case; nested-`.gitignore` aggregation is a bounded follow-up TODO (flag at Step 9 as a future-phase item). Keeps the slice atomic.
3. **`DiscoveredFile` / `FileClassification` shape — frozen Pydantic `BaseModel` or plain `@dataclass`?** My default vote: **frozen Pydantic `BaseModel(extra="forbid")`** — consistent with the codebase's parse-don't-trust posture, reuses `IdentityStr`, and lets the vocab guard + closed-set test pin the fields exactly like `Chunk`.
4. **`doc_or_code` fallback for unmapped extensions?** My default vote: **known doc-extension set → `doc`; everything else (schemas/config/unknown) → `code`** — discovery is source-agnostic so classify must total-map; config/schemas are structured source, not prose.
5. **`producer` detection depth in v0?** My default vote: **name/path-based generated markers only** (`*.lock`, lockfiles, `*_pb2.py`, etc.) → `generated`; else `human`. No content-header sniffing in v0 (keeps it deterministic + cheap; header-sniff + the `gstack`/`CE`/session producers are future, per the `chunk.py` "classifier may grow" note).
6. **`ownership` v0 rule — the architecture lists the three values but does not pin the rule.** My default vote: **`foreign` = path under a known-vendor dir (`node_modules/`, `vendor/`, `.venv/`, `venv/`, `site-packages/`, `third_party/`); `supplemental` = generated producer or known-auxiliary (lockfiles); else `owned`.** `owned` is the class the sync-phase drift-radar may refresh, so the rule is load-bearing later — flag the v0 definition as an architecture-doc-note at Step 9.

## Dependencies + sequencing
- **Depends on:** 1.2 (`Chunk` contract frozen — vocab alignment) + `core/_types.py` (`IdentityStr`). Both landed on `main`.
- **Blocks:** 2.2 (anchor-aware chunking consumes discovered + classified files), 2.4 (`add` pipeline wires discover → classify behind the CLI).

## Estimated commit count
**1.** Discovery + classification are one logical unit (the front of the §8 pipeline), same code area (`core/ingest/`), share the `DiscoveredFile` type, and touch **no safety invariant** (the first writer + the HostPort allowlist runtime proof are Task 2.4 / 2.S). Task 2.1 is a single tracker task with two files — bundle, one Step-10 commit.

## Lessons-logged candidates anticipated
- **Convention candidate** — "Ingest-stage classifier output mirrors the frozen `Chunk` closed sets via a `get_args` drift test — never re-declare a Literal that must equal a contract field without a pin."
- **Architecture-doc note candidate** — pin the v0 `owned/foreign/supplemental` + `producer`/`doc_type` heuristic vocabulary into `ARCHITECTURE.md §8`.
- **Future TODO — operational** — nested per-directory `.gitignore` aggregation; richer `producer` detection (content headers, session producers).

## How to invoke
1. **Read this brief end-to-end** — especially "Things to flag at Step 2.5".
2. **`/session-start`** (first slice of the spine implementer session), then **`/tdd discovery_and_classification`**.
3. **Step 0 (Restate)** — confirm against the Feature line.
4. **Step 1 (Identify files)** — confirm against "Files expected to touch".
5. **Step 2.5** — send the test-design write-up (one `Asserts: <invariant> (§anchor)` line per test + the acceptance-bullet→test coverage map) with answers to the six design questions (take defaults or push back).
6. **Step 9 (summarize)** — surface the `pathspec` dep, the §8 architecture-doc-note, and anything beyond the anticipated candidates.
