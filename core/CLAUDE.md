# Nexus Brain `core/` — Build Guide

> **You're in `core/`.** This file plus root `CLAUDE.md` both load. The root file covers global project conventions + shared comm rules (track-prefix, escalation taxonomy, messaging budget); this file owns code-area conventions for the Python engine (core).

## Launch protocol

| Working on... | cwd | Loads |
|---|---|---|
| Planning / docs / commits | repo root (`project-brain/`) | root `CLAUDE.md` only |
| the Python engine (core) code | `core/` | this `CLAUDE.md` + root |

<!-- For a multi-area project, add a row per additional code area. -->

If you find yourself fighting the wrong conventions, check your cwd.

## Session start/end protocol

**At session start:**
1. Read `IMPLEMENTATION_PLAN.md` (repo root) **by section, not whole** — `grep -n "^##" IMPLEMENTATION_PLAN.md` for offsets, then Read with offset/limit just "Currently in progress" + the active phase. (The file grows; never load it whole.)
2. Confirm with the user what feature this session is targeting.
3. Read the relevant section of `ARCHITECTURE.md` from the lookup table below.

**At session end** (only when the user explicitly says we're done):

1. **Implementer runs `/session-end`.** Implementer writes ONLY:
   - `core/` code files (the slice's implementation)
   - test files (the slice's tests)
   - dependency manifest / lockfile (deps the slice adds)
   - `docs/sessions/<NNN>-<date>-<topic>.md` (session doc, created at `/session-end` Step 5)

   **Implementer must NOT touch (all orchestrator territory).** *This list is the canonical statement
   of the territory rule — `/session-end`, the brief template, and the generated
   `scripts/guards/territory-guard.sh` PreToolUse hook (which mechanically enforces it in team mode)
   all point here.*
   - `IMPLEMENTATION_PLAN.md`
   - `core/LESSONS.md`
   - `core/CLAUDE.md` (entire file — both the Cross-doc invariants table AND the Lessons logged index)
   - `ARCHITECTURE.md`
   - `docs/orchestrator-briefing.md` / `docs/tdd-brief-template.md` / `docs/briefs/` / `docs/runbooks/`
   - other top-level deliverable / design docs
   - `.gitignore` and root-level dotfiles (unless adding a new artifact to ignore, flagged at Step 9)

   At Step 10: **explicit `git add <path>` per slice file; never `git add -A`/`.`; never stage an orchestrator-territory file.** Changes to any orchestrator-territory file (a new cross-doc model, a lesson, an arch note) are **flagged at Step 9**, not edited here — the orchestrator writes them hot (root `CLAUDE.md` + the Step-9 matrix).

2. **Orchestrator runs `/orchestrate-end`** for round close-out + Carry-forward triage + round terminal commit + push.

## Lookup table — where to find canonical info

Don't paste these sections into the prompt. Grep the file:section, read only what you need. `/check-arch <topic>` dispatches off this table.

| Topic | File (relative to repo root) | Section |
|---|---|---|
| Ports & adapter contracts (incl. Clock/Seed/IdGen determinism seams) | `ARCHITECTURE.md` | §7 |
| Data & state model (chunk schema · version stamp · manifest/registry · source-of-truth law) | `ARCHITECTURE.md` | §5 |
| Grounding · anchors · provenance (north star) | `ARCHITECTURE.md` | §10 |
| Model / contract inventory (freeze-before-fork ★) | `ARCHITECTURE.md` | Appendix A |
| CodeGraph column-diff + CLI smoke (spike 0.2) | `ci/probes/codegraph_coldiff.md` | — |
| Lessons logged (full prose) | `core/LESSONS.md` | by lesson # |

<!-- Starts near-empty. Add a row whenever a topic is looked up twice. -->

**Code intelligence & docs (when available):** prefer a code-intelligence MCP / docs MCP over grep+read loops — see root `CLAUDE.md` "Code intelligence & docs."

## Stack

<!-- ▼ EXAMPLE BLOCK [id=area-stack]: stack quick-reference for implementer sessions. Canonical stack lives in root CLAUDE.md + ARCHITECTURE.md; this is the cheat sheet. ▼ -->

- **Runtime:** Python 3.12
- **Framework:** FastMCP 3.x · LlamaIndex · LanceDB
- **Validation:** Pydantic v2
- **Lint / types / tests:** ruff / mypy --strict / pytest

<!-- ▲ END EXAMPLE BLOCK [id=area-stack] ▲ -->

## Standard commands

```bash
# Install deps (run once; re-run when the manifest changes)
uv sync

# Run the dev server (if applicable)
uv run nexus

# Tests
uv run pytest

# Quality
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Preflight (use before saying "done" with a feature)
uv run ruff check . && uv run mypy . && uv run pytest
```

## TDD protocol

**Write the failing test first.** Applies to deterministic code — see the TDD posture in root `CLAUDE.md` for what is test-first vs. exempt.

**Commit per slice when practical.** Never bundle a safety-critical slice with anything else.

## Forbidden patterns

<!-- ▼ EXAMPLE BLOCK [id=forbidden-patterns]: forbidden patterns — 3-5 narrow, enforceable, domain-specific rules. Shape: "Don't <pattern X> because <reason / past incident>; use <alternative Y>." Test-pin them where possible. Starts small; accretes as lessons surface. ▼ -->

Do not:

1. **Write code without a failing test first** (for deterministic code). Even one-line functions.
2. **Embed a chunk before it passes the Redactor** — every chunk goes through `redact(payload, sink)` at persist / MCP-egress / cloud-egress; raw transcripts + `thinking` are never embedded. (§18; pin: the redaction fuzz gate.)
3. **Reach an FS/git/external/session mutation outside `HostPort.perform`** — the core only *proposes* intents; the host adapter authorizes + executes. (§4/§7; pin: the architecture-invariant test.)
4. **Read `datetime.now()`, mint ids, or seed RNG directly** — inject the `Clock` / `Seed`/`IdGen` ports (the determinism seams). Wall-clock + ungoverned randomness break the eval/test seams.
5. **Hardcode the CodeGraph DB path or call `codegraph_trace`/`codegraph_context`** — resolve via `CODEGRAPH_DIR`, query table `nodes` (not `symbols`), use `codegraph_explore`, assert `schema_versions` at startup. (D-27.)
6. **Mix embedding models/dims in one LanceDB dataset, or open a 2nd writer** — model change = blue-green new generation; one writer per dataset; federation is read-only. (§5/§6/§11.)

**Enforcement patterns (machine-readable — `/preflight` warn-greps the staged diff against these).**

```forbidden-patterns
# rule 4 (use the Clock port): datetime\.(now|utcnow)\(
# rule 4 (use the Seed/IdGen port): \b(uuid4|random\.|secrets\.token)
# rule 5 (no deleted CodeGraph tools): codegraph_(trace|context)
# rule 5 (no hardcoded codegraph path): ['\"]\.codegraph/
```

<!-- ▲ END EXAMPLE BLOCK [id=forbidden-patterns] ▲ -->

## Cross-doc invariants — schema/docs mirroring

Several typed models in this codebase are **contracts** mirrored in `ARCHITECTURE.md` and indexed in the table below. The architecture doc is the canonical contract; the model is the executable enforcement. Drift produces silent disagreement.

**Authoring discipline (orchestrator owns this table).** The implementer never edits this table or `ARCHITECTURE.md` directly — it flags a field add/remove/rename at Step 9 as a `Cross-doc invariant change`; the orchestrator writes the row + the arch edit hot the same round (see root `CLAUDE.md` + `docs/orchestrator-briefing.md`). Commits stagger; the working tree stays aligned within the round.

| Model | `ARCHITECTURE.md` section | Notes |
|---|---|---|
| `Clock` / `Seed` / `IdGen` ports | §7 (Appendix A) | Determinism seams (C-15). `Clock{now()→tz-aware UTC, monotonic()}` · `IdGen{new_id(kind)→opaque unique str}` · `Seed{rng()→seeded Random}`. Each: real adapter + contract-faithful `Fake*` double (`core/testing/fakes.py`). Pinned by `core/tests/ports/test_clock.py` + `test_idgen.py` (`spec(§7)`). Behavioral protocols — no field-set, so no schema-snapshot test (unlike 1.2–1.5). |
| `Chunk` (+ `ManifestArtifact` pattern) | §5/§8 (Appendix A) | LanceDB row contract. 19 frozen fields (snapshot `spec(§5)`); `frozen=True`, `extra="forbid"`; `chunk_id`/`created_at` caller-injected via IdGen/Clock (no default); closed sets (`doc_or_code`/`ownership`/`register`) are Literal; `anchor`/`*_sha` bare str (format owned by 1.3/stamp). FTS/BM25 = native index, not a field. Pinned by `test_chunk.py`. |
| `StoreVersionStamp` | §5 (Appendix A) | §5 source-of-truth: canonical for `{schema,model,dim}`. 5 frozen fields (snapshot `spec(§5)`); **NO SHA field** (git-SHA = LanceDB version tag, canonical); `extra="forbid"` rejects a 2nd SHA home. `dimension`/`schema_version` PositiveInt; `embedding_model`/`source_root_hash` min_length=1; `index_built_at` AwareDatetime/Clock. Pinned by `test_stamp.py`. |
| `ProjectManifest` + `ManifestArtifact` | §5 (Appendix A) | DERIVED projection (`.project-brain/manifest.json`, rebuilt-from-dataset). Manifest 12 fields + artifact 5; two field-name snapshots + a by-alias on-disk-key snapshot (camelCase `schemaVersion`/`ingestedFromSha` only — LESSON §4). `validate_by_name`+`validate_by_alias`; lenient-read/strict-write (on-disk key-shape strictness → 1.2d loader). min_length on identity/recipe strings; `artifacts=[]` allowed. Pinned by `test_manifest.py`. |
| `Registry` + `RegistryEntry` | §5 (Appendix A) | DERIVED routing index (`~/.project-brain/registry`, scans manifests). Registry `{schema_version(file), entries: dict[project_id, RegistryEntry]}`; entry 6 fields. TWO distinct schema_versions (file-format vs per-project store). All-snake; `policy` min_length=1 (no empty privacy marker — fail-open closed; fail-CLOSED semantics → 1.5). Empty `{}` allowed. Pinned by `test_registry.py`. |
| migration engine (`migrate`/`DowngradeRefused`/`MissingMigration`) | §5 (Appendix A) | PURE forward-only `schemaVersion` runner for the serialized files; downgrade-refuse (fail-closed) + missing-migration detection; baselines=1. NO file I/O (imports only `collections.abc`+`typing` — §4/§7 by construction, import-purity-pinned); backup + I/O HOST-owned (HostPort, Phase 2+). Behavioral (no snapshot). Pinned by `test_migrations.py`. |
| `Anchor` (+ `AnchorState`) | §10 (Appendix A) | The §10 north-star trust primitive (`file:line[-range]` edge → code target). 11 frozen fields (snapshot `spec(§10)`); `frozen=True`, `extra="forbid"`. `state` = 5-value `AnchorState` **StrEnum** `{live,stale,moved,unknown,orphaned}` (membership-snapshot pinned; **`deleted` is record-lifecycle, NOT a state value** — §5 line-90 ↔ Appendix-A reconciliation); an invalid/unrecognized `state` is rejected at parse (the grounding gate keys on `state==live`, §4 parse-don't-trust). Identity/path strings use `StringConstraints(strip_whitespace=True, min_length=1)` (before-fork sweep); `target_symbol` optional (strip+min_length when present); `target_line_start/end` `PositiveInt` + an `end>=start` validator; `confidence` `[0,1]` float. Pinned by `test_anchor.py`. |
| `EvidenceRef` (+ deferred `EvidenceType`) | §10 (Appendix A) | The §10 user-visible evidence record backing an answer. 4 frozen fields `{type, label, resource_ref?, confidence?}` (**SHAPE-only** snapshot `spec(§10)`); `frozen=True`, `extra="forbid"`. `type`/`label` required, `resource_ref`/`confidence` optional; strings `StringConstraints(strip_whitespace=True, min_length=1)`; `confidence` `[0,1]` when present; `resource_ref` = opaque resource locator (LESSON 2; `type` is the kind discriminator). **`EvidenceType` membership DEFERRED (D-A11):** a constrained-`str` alias now (NOT an instantiated enum), in-code deferral marker (NexusOps `MAIN_PLATFORM_INTERFACE.md` v0.2 / C-15); **no value-membership snapshot** — narrowing to the canonical 11 at Phase-4 (before the post-spine fork) is additive (field name unchanged; `StrEnum ⊂ str`). Pinned by `test_evidence.py`. |
| `ProvenancePacket` | §10 (Appendix A) | The §10 grounding record on EVERY answer (audit of trust). 10 frozen fields `{project_ids, source_ids, citations, commit_shas, session_ids, recorded_sha?, index_freshness, confidence, drift_markers, evidence}` (snapshot `spec(§10)`); `frozen=True`, `extra="forbid"`. **`evidence: list[EvidenceRef]`** composes the frozen 1.3c contract (Appendix-A:217 reconciled +`evidence[]`, additive/D-A7; deep-immutability + nested parse-don't-trust — LESSON 8). `citations` = `list[str]` file:line tokens (NOT `list[Anchor]`; gate re-resolves vs live anchors). `recorded_sha` optional; lists required but empty-valid (no mutable default); tokens/elements `StringConstraints(strip_whitespace=True, min_length=1)`; `confidence` `[0,1]`. `low_confidence_links` is NOT a field (gate's flagged-unsupported rides low-confidence EvidenceRefs + Phase-4 output). Pinned by `test_provenance.py`. |
| `HostPort` (+ `HostCapability`, `HostIntent`/`HostAction`/`HostResult`, `HostDenied`) | §7 (Appendix A) | **The SOLE mutation chokepoint (Key safety rule #4 / §4 #3).** `@runtime_checkable Protocol`: `capabilities()→frozenset[HostCapability]` · `authorize(intent)→HostAction` · `perform(action)→HostResult`. `HostCapability` = closed 3-value `StrEnum` `{own_store_write, owned_doc_refresh, consented_host_config}` (membership snapshot, LESSON 6). **Fail-closed `authorize`:** capability ∉ `capabilities()` → `HostDenied` (empty allowlist denies all). **`perform` defense-in-depth:** re-validates capability ∈ `capabilities()` AND the `authorized` stamp — a forged `authorized=True` for a non-allowlisted capability is still denied (LESSON 9). Intent/Action/Result = frozen `spec(§7)` shapes (minimal; per-capability payloads + real `StandaloneHost` + full §14 runtime proof = Phase-2 / **Task 2.S / D-A13**). §14 AST-scan **tripwire** seeded (no FS/git mutation outside `core/ports/host.py`). `FakeHost` (testing/fakes.py) = same fail-closed contract (LESSON 1). Pinned by `test_host.py`. |

| Provider ports (`EmbeddingProvider`/`Reranker`/`ContextStrategy`/`ModelProvider`) | §7/§16 (Appendix A) | 4 `@runtime_checkable` **behavioral** Protocols (no field-snapshot, like 1.1) + 4 deterministic `Fake*` doubles (LESSON 1). `EmbeddingProvider{embed(Sequence[str])→list[list[float]], @property dimension:int, @property model_version:str}` — **`model_version` HERE ONLY** = the load-bearing §5 / Key-safety-#5 generation identity (reranker/model versions are eval/obs concerns, Appendix-A:219 asymmetry principled). `Reranker{rerank(query,docs)→list[RerankResult]}` · `ContextStrategy{augment(chunk,ctx)→str}` · `ModelProvider{generate(prompt)→GenerateResult}`. Frozen `spec(§7)` result types: `RerankResult{index, score}` (**`allow_inf_nan=False`** — a NaN/inf score poisons sort+RRF), `Citation{cited_text, source_index}`, `GenerateResult{text, citations}` (Citation minimal; rich Anthropic payload Phase-4-deferred). Cassette record/replay re-sequenced to providers/eval. Pinned by `test_providers.py`. |

| `CodeGraphPort` (+ `CodeGraphQueryKind`, `CodeGraphResult`, `CodeGraphSchemaError`, `resolve_codegraph_dir`, `assert_schema_compatible`) | §7 (Appendix A) | Read-only structural-graph seam over external CodeGraph (`=1.0.1`). `@runtime_checkable Protocol{query(kind, sym)→CodeGraphResult}` + `FakeCodeGraph` (LESSON 1). `CodeGraphQueryKind` = closed 5-value `StrEnum` `{explore,node,callers,callees,search}` (membership snapshot) + `cli_command` property: **`search`→`query`** (spike-0.2 Risk-2; no `codegraph search` exists). `assert_schema_compatible` asserts `max ≥ 5` (Risk-1, forward-safe, NOT `=1`) → raises `CodeGraphSchemaError`. **`resolve_codegraph_dir` = §14 ingress validator, positive charset ALLOW-LIST** (`[A-Za-z0-9._-]+`, reject leading `-`/`.`/`..`; default `.codegraph`) — never a deny-list on a frozen seam (LESSON 10). `CodeGraphResult{kind, symbols: tuple[str,...]}` frozen (structured per-kind parse Phase-3-deferred). No hardcoded `.codegraph/`, no `codegraph_trace/context` (forbidden-rule 5 / D-27). Real CLI adapter + version-gate(`≥1.0.1`)/tree-sitter-fallback = Phase-3. Pinned by `test_codegraph.py`. |

| `EventSource` (+ `Event`) | §7 (Appendix A) | Behavioral `@runtime_checkable Protocol{poll()→tuple[Event,...], subscribe(handler)→None}` (git-hook/watcher standalone; NexusOps-outbox variant = P2) + `FakeEventSource` (LESSON 1; poll+subscribe deliver-and-drain one consistent queue). `Event{kind, source}` frozen (`spec(§7)`; payload Phase-2-deferred). Pinned by `test_events.py`. _(Appendix-A row was additive — D-A7.)_ |
| `SecretStore` (+ `SecretRef`, `SecretNotFoundError`) | §7/§18 (Appendix A) | **Key safety rule #3.** `@runtime_checkable Protocol{get_ref(name)→SecretRef, resolve(ref)→str}` + `FakeSecretStore` (LESSON 1; test secrets held OUT-OF-BAND). **`SecretRef{service, account}` carries NO secret material** — `extra="forbid"` rejects `secret`/`value`/`password`/`token`; plaintext is never on the ref / its `repr`·`str`·`model_dump(_json)` / the store `repr` — only `resolve()` returns it transiently (LESSON 11). **`resolve` fail-closed:** a missing secret raises `SecretNotFoundError` (§25, never a silent empty). Real keychain adapter + no-plaintext-in-logs = Phase-2. Pinned by `test_secrets.py`. _(Appendix-A row additive — D-A7.)_ |
| `ObservabilitySink` (+ `ObsEvent`) | §7 (Appendix A) | Behavioral `@runtime_checkable Protocol{emit(event: ObsEvent)→None}` + `FakeObservabilitySink` (records LOCALLY, never network). `ObsEvent{name, attributes: tuple[tuple[str,str],...]}` frozen (`spec(§7)`; tuple collection LESSON 8; attribute KEY strip+non-empty per LESSON 7, value plain str). **Instrumented-but-silent: off-by-default + local-only + NEVER phone home** (D-22, §6 safety); the OTel sink is the Phase-2 adapter. Pinned by `test_observability.py`. _(Appendix-A row additive — D-A7.)_ |

<!-- Populated as contract models land. -->

## Module organization

<!-- ▼ EXAMPLE BLOCK [id=module-layout]: module layout + layer dependency rule. Replace with the project's real directory tree and import-direction DAG. ▼ -->

```
core/
  ports/        # interfaces (HostPort · Embedding/Reranker/Context/Model · CodeGraphPort · Event · Secret · Observability · Clock · Seed/IdGen) — depend on nothing
  model/        # frozen Appendix-A contracts (Chunk · Anchor · ProvenancePacket · stamp · manifest/registry · MCP-tool · policy · state machines)
  redactor/     # the Redactor (fan-in hub)
  ingest/ index/ retrieval/ grounding/ federation/ sync/ drift/ sessions/ agent/ plans/
  mcp/ providers/ obs/ setup/ lifecycle/ nexusops/   # entrypoints / adapters / P2
```

Layer dependency direction — the `ARCHITECTURE.md §2.5` import DAG (top imports bottom, never reverse; **no cross-sibling imports**):

```
entrypoints (cli · mcp · agent · host-adapters)
  → {retrieval · drift · federation} → grounding → index → ingest
  → {redactor · providers · ports · model(manifest/registry)}
```

`redactor` (index-time + MCP-egress + cloud-egress) and `grounding` are **fan-in hubs**, not pipeline stages; `observability` is a **leaf sink** every node emits to. Enforce the import-direction with a test where possible.

Cross-cutting layers can be imported from anywhere. Enforce the rule mechanically with a test where possible — the test *is* the spec for the rule.

<!-- ▲ END EXAMPLE BLOCK [id=module-layout] ▲ -->

## Subagents

See `.claude/agents/README.md` for the canonical inventory + integration points.

<!-- ▼ EXAMPLE BLOCK [id=area-subagent-candidates]: area-specific subagent candidates — list candidates that would earn their keep specifically in this area (e.g. an ABI/types syncer for a frontend area, a Pyth/feed verifier for a contracts area). Build only on real friction. ▼ -->

<!-- ▲ END EXAMPLE BLOCK [id=area-subagent-candidates] ▲ -->

## Lessons logged from prior sessions

The full prose for each lesson lives in `core/LESSONS.md`. This index is the compact orientation surface.

**Lesson numbers are stable IDs** — once assigned, they don't change. New lessons get the next sequential number. `/session-end` proposes additions when it detects them; the user approves before the entry is written and a row is added here.

Lessons start at §1.

| # | Date | Topic | Rule (one-liner) |
|--:|---|---|---|
| 1 | 2026-06-17 | [Ports = Protocol + real + Fake double](LESSONS.md#1) | Every port is a `Protocol` with a real adapter + a contract-faithful `Fake*` double in `core/testing/fakes.py`; inject by constructor, never construct/read inline. _(pin: `core/tests/ports/test_*.py` `*_conform`; pattern: forbidden-rule 4)_ |
| 2 | 2026-06-17 | [Minted ids are opaque](LESSONS.md#2) | `kind` is a minting hint, never recoverable from the id; typed fields carry kind. _(accepted: not mechanically grep-enforceable)_ |
| 3 | 2026-06-17 | [Field names can shadow BaseModel/ABCMeta](LESSONS.md#3) | Declare required fields with `Field(...)`; pin all required-ness with an omit-each-field test; scope-suppress shadow warnings in the model module (not pytest-only). _(pin: per-model omit-each tests; watch `register`/`copy`/`dict`/`json`/`schema`/`validate`/`model_*`)_ |
| 4 | 2026-06-17 | [Serialized-file models pin two snapshots](LESSONS.md#4) | Pin BOTH the Python field-name snapshot AND the by-alias on-disk-key snapshot; use `validate_by_name`/`validate_by_alias` (NOT deprecated `populate_by_name`); lenient-read/strict-write, on-disk key-shape strictness owned by the loader. _(pin: `test_manifest.py` dual snapshots)_ |
| 5 | 2026-06-17 | [Never suppress a quality-gate's output](LESSONS.md#5) | Run the canonical `/preflight` (Step 8, visible output); never hand-roll `ruff/mypy/pytest >/dev/null && echo OK` (a short-circuited failure ships silently). _(accepted: session-practice, not committed-grep-enforceable — control = use the canonical gate)_ |
| 6 | 2026-06-17 | [Named state machines = StrEnum + membership snapshot](LESSONS.md#6) | A named domain state-machine alphabet is a `StrEnum` with a value-membership snapshot test; one-off inline closed tags stay `Literal`. _(pin: `test_anchor.py::test_anchor_state_values`)_ |
| 7 | 2026-06-17 | [Identity strings strip+min_length](LESSONS.md#7) | Every §5/§10 identity/path string field uses `StringConstraints(strip_whitespace=True, min_length=1)`; whitespace-loose identity in a frozen cross-track contract is a Finding. _(pin: per-model empty/whitespace-rejection tests)_ |
| 8 | 2026-06-17 | [Composed frozen contracts: tuple containers + nested parse-don't-trust + deep immutability](LESSONS.md#8) | A frozen contract composing a sibling frozen contract by value uses **`tuple[Child, ...]`** (`frozen=True` does NOT deep-freeze a `list` — `.append()` still mutates) and extends parse-don't-trust + deep immutability to the nested element; test element rejection, the dict→model coercion, and immutability. _(pin: `test_provenance.py` nested-typed + deep-frozen + json-roundtrip; tuple-container retrofit in the before-fork sweep)_ |
| 9 | 2026-06-17 | [Type-shaped chokepoint: authorizer-minted input + perform re-validation](LESSONS.md#9) | A privileged-op chokepoint takes an input type obtained only from its authorizer AND re-validates the allowlist at execution — never trusting a forgeable `authorized` stamp alone. _(pin: `test_host.py` perform capability-recheck + fail-closed authorize)_ |
| 10 | 2026-06-17 | [§14 ingress validation = positive allow-list, never deny-list](LESSONS.md#10) | An ingress/boundary validator (path/dir-name/identifier) uses a positive charset ALLOW-LIST (`re.fullmatch`), never an enumerated deny-list — esp. when frozen into a contract; a deny-list bakes weak semantics + misses CLI-flag/null-byte/unicode-separator bypasses. _(pin: `test_codegraph.py` bypass corpus; applies to 1.5 MCP ingress)_ |
| 11 | 2026-06-17 | [A safety contract excludes the dangerous field by shape + extra-forbid](LESSONS.md#11) | A frozen contract that must NOT carry sensitive/divergent data omits the field AND actively rejects it via `extra="forbid"` (mechanically pinned, not convention): `SecretRef` has no secret field; `StoreVersionStamp` has no SHA field. Pin with a no-leak/reject test. _(pin: `test_secrets.py` SecretRef-no-secret + no-leak; `test_stamp.py` rejects-sha)_ |

<!-- Starts empty. Each row links to its `LESSONS.md` anchor. -->

<!-- Slash commands: see root CLAUDE.md "Slash commands available." Implementer pair: /session-start + /session-end. -->
