# IMPLEMENTATION_PLAN.md — Nexus Brain

> **Phase note.** Decomposition of the binding `ARCHITECTURE.md` (27 §-sections + Appendix A). **Build posture: production-grade · no timebox** (correctness/best-practice over speed; no demo phase). Build order = invariants → lifecycle correctness → tests → hardening. The **forced-serial bottleneck is Phase 1 (contracts & ports freeze)** — every track waits on it; the **first vertical slice** is the `spine` track (Phases 2–5: `add` one repo → grounded answer → eval green). Build mode = **agent-team multi-track** (worktrees per track). Locked decisions: `docs/planning/DECISIONS.md` D-1..D-27.
>
> **Reading discipline.** Read by section, not whole. The living sections (Currently-in-progress, Carry-forward, Log, Trims, Decisions) are bounded — pruned at `/orchestrate-end`.

> **Session protocol:**
> - **Start** — orchestrator `/orchestrate-start`; implementer `/session-start`. Confirm the session target with the user.
> - **End** (user-signalled) — implementer `/session-end` (TDD + cross-doc audit + Step-9 list + session doc + `/preflight`; never edits this doc); orchestrator `/orchestrate-end` (reconcile checkboxes, Log, Decisions, Carry-forward, round commit+push).

> **Reference deadlines:** none (no timebox — D-18). Sequence by the critical path, not dates.

> **Spec-anchor convention (architecture-as-contract).** Each phase header carries `**Spec anchors:**` (`ARCHITECTURE.md §N`). Re-read them at session start; a slice surfacing behavior the anchors don't cover is a cross-doc flag at `/tdd` Step 9 (missing anchor or drift). Each phase also carries `**Track:**` + `**Depends on (phases):**` (the source the Track map renders from). Mid-build tasks carry `(implements §X; origin: <slice>)` on the `### N.M` heading.

---

## Currently in progress

**Bootstrap session.** Planning chain complete (arch-draft → arch-finalize → tasks-gen). Scaffolding not yet generated; first `/tdd` slice not started.

**Next session target:** `/scaffold-generate`, then Phase 0 (spikes) → Phase 1.1 (Clock/Seed/IdGen + port interfaces).

---

## Carry-forward to upcoming briefs

- **spec-lint template assumes letter-prefixed task IDs** *(origin: 2026-06-17 spec-lint finding; fixed in-tree @track/contract 392ed4f)* — the `spec-lint.sh brief` Task-ID extraction regex was `[A-Za-z]+[0-9]*\.[0-9]+`, which fails this project's numeric `N.M` IDs (`1.1` → `FAIL no Task ID line found`, cascading to skip the anchor-subset check). Fixed locally (letter class → optional `[A-Za-z]*`). **Upstream follow-up (out of scope now):** this is a scaffolding-TEMPLATE bug — flag to the scaffolding repo / `/scaffold-upgrade` so the template carries the fix and the next upgrade doesn't clobber the local override.
- **`core/pyproject.toml` `requires-python = ">=3.12,<3.13"`** *(origin: 2026-06-17 1.1 / T6)* — upper bound pins to 3.12.x by design; needs a deliberate bump when the project moves to Python 3.13. Low-priority reminder, not a blocker.
- **`.claude/commands/preflight.md` Step-4 `uv run mypy core` is known-stale** *(origin: 2026-06-17 1.1 / D-A3)* — the flat core/ layout has no `core/core/`; correct command is `uv run mypy .` (already fixed in `core/CLAUDE.md`). Editing the command file is agent-loaded config → needs owner authorization (HITL-deferred). Core implementers override Step-4 with `mypy .` until the owner resolves it.
- **1.4 `CodeGraphPort` inputs from spike 0.2** *(origin: 2026-06-17 / D-A4; see `ci/probes/codegraph_coldiff.md`)* — pin `=1.0.1`; assert `schema_versions MAX >= 5` (NOT `=1`, the plan/§7 text); map `search` kind → CLI `codegraph query`; version-check at startup + fail-fast if `< 1.0.1` (system codegraph is v0.9.7, lacks `explore`/`node`) OR route via the 1.0.1 MCP daemon. **Reconcile the §0.2 + Appendix-A CodeGraphPort `schema_versions` value when authoring 1.4** (integration checkout).
- **1.5 `Redactor` inputs from spike 0.1** *(origin: 2026-06-17; see `docs/audits/redaction-envelope.md`)* — freeze signature `redact(payload, sink: Sink) -> str`, `Sink` = {persist, mcp_egress, cloud_egress} (all 3 required); docstring enumerates the 3 accepted residuals + cites §18/C-11; declare the envelope (recall ≥95% / FP ≤5%, git-SHA 0% FP hard); behavioral invariants idempotent + never-raises + git-SHA-passthrough. **FLAG-4 (cloud_egress stricter than persist?) DEFERRED to Phase-2.3/policy.yaml §16 — does not block the 1.5 signature freeze** (escalated to owner via lead 2026-06-17; default = signature allows per-sink strictness, decided at 2.3).
- **Phase-2.3 redactor engine inputs from spike 0.1** — wire `ci/eval/redaction_fuzz/` harness as a CI hard gate; address FLAG-1 (encoding-aware/decode-before-detect oracle), FLAG-2 (JWT shape-matcher not context-only), FLAG-3 (binary/compiled-artifact corpus — assess ingest scope).
- **Identity-field whitespace-strip sweep — MUST-do-before-fork** *(origin: 2026-06-17 1.2c1; [security low])* — `min_length=1` admits whitespace-only identity strings (`project_id="   "` passes). Apply `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` UNIFORMLY across all §5 identity fields — retrofit 1.2b (`embedding_model`/`source_root_hash`) + 1.2c1 (manifest/artifact identity strings) + bake into 1.2c2/1.3 from the start. A whitespace-loose identity in a frozen contract consumed cross-track post-fork = a Finding, so this lands **before the contract→integration merge**.
- **Manifest/registry on-disk strict key-shape rejection → 1.2d loader** *(origin: 2026-06-17 1.2c1)* — the frozen models are lenient readers (`validate_by_name` accepts snake OR camel keys; a dup-key file silently resolves to the alias). Strict on-disk key-shape rejection (wrong-key, duplicate-key) is owned by the **1.2d migrator / startup-reconcile loader**, not the model. Documented by `test_manifest` lenient-read test; the loader enforces.

---

## Deliverable map

<!-- ▼ EXAMPLE BLOCK [id=deliverable-map]: deliverable map — replace rows with the project's real required outputs (docs, deployed app, reports, etc.). ▼ -->

| Deliverable | Status | Delivered by |
|---|---|---|
| `nexus-brain-core` Python package (engine + ports) | ❌ | Phases 1–10 |
| Per-project LanceDB index + maintenance contract | ❌ | Phase 3 |
| Grounded-answer retrieval core (north star) | ❌ | Phase 4 |
| Embedded agent + `nexus`/`nb` CLI | ❌ | Phase 5 |
| Federation router (portfolio query) | ❌ | Phase 6 |
| Sync/freshness + drift radar | ❌ | Phase 7 |
| MCP server (trust boundary) | ❌ | Phase 8 |
| Opt-in session memory / episode cards | ❌ | Phase 9 |
| CI-gated eval harness + observability | ❌ | Phases 2–5, 12 |
| Tauri desktop app | ❌ | Phase 11 |
| Signed/notarized `.dmg` + Cask + `setup`/`uninstall` | ❌ | Phase 13 |
| (P1) Implementation-plan & workflow-pack awareness | ❌ | Phase 15 |
| (P2) NexusOpsHost adapter | ❌ | Phase 14 |

<!-- ▲ END EXAMPLE BLOCK [id=deliverable-map] ▲ -->
---

## Parallelization plan (Track map)

<!-- ▼ EXAMPLE BLOCK [id=parallelization-plan]: Parallelization plan / Track map — TEAM MODE ONLY. /tasks-gen authors this from ARCHITECTURE.md §2.5 refined by the per-task Depends on: graph. Authority for valid <track> names; /team-start <track> reads it. Delete this whole block for a single-track plan. ▼ -->

> **Team mode.** A *track* is a dependency-isolated region of the `ARCHITECTURE.md` §2.5 DAG. In this Python monorepo, track isolation is **by `core/` subpackage** (each track owns a subpackage + reads the frozen shared contracts read-only). Tracks fork only after the `contract` + `spine` tracks land.

**Phase/track DAG:**

```mermaid
flowchart TD
  subgraph contract[Track: contract — forced-serial bottleneck]
    P0[Phase 0 — spikes] --> P1[Phase 1 — contracts & ports freeze]
  end
  subgraph spine[Track: spine — first vertical slice]
    P2[Phase 2 — ingest + redactor] --> P3[Phase 3 — LanceDB index + maintenance]
    P3 --> P4[Phase 4 — retrieval + grounding]
    P4 --> P5[Phase 5 — agent + CLI + eval spine]
  end
  P1 --> P2
  P1 --> P6[Phase 6 — federation]
  P1 --> P7[Phase 7 — sync/freshness]
  P1 --> P8[Phase 8 — MCP server]
  P1 --> P9[Phase 9 — sessions]
  P1 --> P10[Phase 10 — providers]
  P4 --> P6
  P4 --> P8
  P3 --> P7
  P2 --> P9
  P5 --> P11[Phase 11 — desktop UI]
  P8 --> P11
  P5 --> P12[Phase 12 — observability + eval wiring]
  P5 --> P13[Phase 13 — packaging + lifecycle hardening]
  P11 --> P13
  P2 --> P15[Phase 15 — plan/workflow awareness · P1]
  P4 --> P15
  P1 -.-> P14[Phase 14 — NexusOpsHost · P2]
```

> **Critical path:** Phase 0 → 1 → 2 → 3 → 4 → 5 → 13 (the serial floor — staff it first). **Forced-serial bottleneck:** **Phase 1** (the shared-contract freeze every track waits on).

**Track map** (`<track>-<area>-<role>` per root `CLAUDE.md` naming):

| Track | Phases | Code area(s) | Worktree (branch) | Agent-team names |
|---|---|---|---|---|
| contract | 0, 1 | `core/ports`, `core/model` | `../project-brain-contract` (`track/contract`) | `contract-core-orchestrator` / `-implementer` |
| spine | 2, 3, 4, 5 | `core/{ingest,index,retrieval,grounding,agent}`, `cli` | `../project-brain-spine` (`track/spine`) | `spine-core-orchestrator` / `-implementer` |
| federation | 6 | `core/federation` | `../project-brain-federation` (`track/federation`) | `federation-core-orchestrator` / `-implementer` |
| sync | 7 | `core/{sync,drift}` | `../project-brain-sync` (`track/sync`) | `sync-core-orchestrator` / `-implementer` |
| mcp | 8 | `core/mcp` | `../project-brain-mcp` (`track/mcp`) | `mcp-core-orchestrator` / `-implementer` |
| sessions | 9 | `core/sessions` | `../project-brain-sessions` (`track/sessions`) | `sessions-core-orchestrator` / `-implementer` |
| providers | 10 | `core/providers` | `../project-brain-providers` (`track/providers`) | `providers-core-orchestrator` / `-implementer` |
| plans `[P1]` | 15 | `core/plans` | `../project-brain-plans` (`track/plans`) | `plans-core-orchestrator` / `-implementer` |
| ui | 11 | `app/` (Tauri) | `../project-brain-ui` (`track/ui`) | `ui-app-orchestrator` / `-implementer` |
| observability | 12 | `core/obs`, `ci/` | `../project-brain-observability` (`track/observability`) | `observability-core-orchestrator` / `-implementer` |
| packaging | 13 | `app/`, `ci/`, `packaging/` | `../project-brain-packaging` (`track/packaging`) | `packaging-app-orchestrator` / `-implementer` |
| nexusops `[P2]` | 14 | `core/nexusops` | `../project-brain-nexusops` (`track/nexusops`) | `nexusops-core-orchestrator` / `-implementer` |

**Integration / merge order** (topological): 1) **contract** → integration branch first (freezes Appendix-A shared contracts); 2) **spine** (the vertical slice); 3) federation · sync · mcp · sessions · providers · **plans (P1)** (parallel, after spine); 4) ui · observability; 5) packaging; 6) (P2) nexusops.

**Shared contracts across tracks (freeze in Phase 1 before forks — Appendix A):** the LanceDB chunk schema · `.project-brain/manifest.json` + registry schema · `HostPort` · the 4 provider ports + `CodeGraphPort` · `Anchor` · `ProvenancePacket`+`EvidenceRef` · the store version stamp · the `Redactor` interface + fuzz corpus · the MCP tool contract · `policy.yaml`. A change to any after fork = a cross-track Finding.

<!-- ▲ END EXAMPLE BLOCK [id=parallelization-plan] ▲ -->
---

## Phase exit checklist (template — applies to every phase)

Executed row-by-row by `/phase-exit <phase>`:

- [ ] All phase task checkboxes ticked (partial work stays unchecked + Log note).
- [ ] Acceptance criterion met (`/preflight` clean + manual smoke where there's runtime behavior).
- [ ] `/preflight` clean (incl. architecture-invariant tests).
- [ ] Cross-doc invariants verified (no model field change without an `ARCHITECTURE.md` edit same round).
- [ ] Reachability audit clean per touched area.
- [ ] Arch-drift audit clean over the phase's Spec anchors.
- [ ] Spec coverage: every phase anchor has a tagged test or waiver (`scripts/spec-lint.sh tests <phase>`).
- [ ] **Dependency audit: no NEW findings vs baseline** — `pip-audit` (core) + `cargo audit` (app) once; new finding → accepted-risk in Decisions or a Finding. _(production-grade)_
- [ ] **Whole-system security review clean (qualifying phases)** — phases with security/invariant/trust-boundary tasks; policy `invariant` → built-in `/security-review` over the track diff; critical → Finding. _(production-grade)_
- [ ] **Perf budgets met or regression flagged** — run the phase's benchmark task(s) vs `ARCHITECTURE.md` budgets; no-budget phases tick `n/a`. _(production-grade)_
- [ ] Session doc(s) exist + list files created/modified.
- [ ] Commits pushed to origin.

---

## Final-submission acceptance criteria (project-level)

- [ ] `add` one repo → `ask` → a **grounded, `file:line`-anchored answer** with a provenance packet, on a real repo (no mocks on the load-bearing path).
- [ ] Portfolio/federated query returns a coherent answer, partial results **marked** (never silently wrong).
- [ ] **Eval harness green:** grounding-gate correctness, zero stale-anchor false-confidence, redaction-recall = zero-leak-on-catchable, retrieval Recall@k on the golden set.
- [ ] LanceDB **maintenance contract invisible** on the reference Mac (O-LANCE-BAKEOFF) under a multi-repo portfolio.
- [ ] Signed/notarized `.dmg` installs; `setup` provisions deps; `uninstall` reverses every host mutation.
- [ ] **No phone-home** (CI no-egress check); secrets keychain-only; redactor runs at all three sinks.

---

## Phase 0 — Pre-build spikes

**Goal:** retire the load-bearing unknowns before they distort the build; produce reusable rigs (fuzz harness, bake-off harness) the later phases assert against.

**Spec anchors:** `ARCHITECTURE.md §24`, §26, §11, §6, §18.

**Track:** contract · **Depends on (phases):** none.

### 0.1 — Redaction property/fuzz harness (rig)
- [x] A property generator + curated adversarial seed corpus for secret-shaped inputs (prefix/entropy/JSON-value classes); leak = a secret surviving into chunk text/vector OR a (simulated) MCP-egress OR cloud-egress payload.
- [x] Quantified **recall-floor (catchable set) + FP-ceiling** — proposed **recall ≥95% / FP ≤5%** (git-SHA 0% FP, hard sub-invariant); the 3 §18-anchored accepted-residual classes (git-SHA hex · adversarial <20-char split · sub-20-char JSON) recorded, zero deviation.
- [x] Files: `ci/eval/redaction_fuzz/` (NEW), `docs/audits/redaction-envelope.md` (NEW). _(landed @track/contract `f2b5f6c`; 34/34 harness tests.)_
- [x] Cross-doc invariant: none (test rig). Depends on: none.

### 0.2 — CodeGraph 1.0.1 column-diff + CodeGraphPort smoke (O-CG-COLDIFF)
- [x] Diff the live `.codegraph` 0.9.7 column set vs `@colbymchenry/codegraph@1.0.1` `schema.sql`; confirm the 5 tables + `schema_versions` — **CORRECTION: live `MAX(version)=5`, NOT `=1`; assert `>=5`**. CLI smoke ✓ — but `search` kind → CLI `codegraph query` (NOT `codegraph search`); system codegraph is v0.9.7 (lacks `explore`/`node`).
- [x] Pin `=1.0.1` exact (verdict: SAFE); record the `trace`/`context` → `explore` migration + `CODEGRAPH_DIR` handling.
- [x] Files: `ci/probes/codegraph_coldiff.md` (NEW). _(landed @track/contract `f2b5f6c`.)_ Cross-doc invariant: none. Depends on: none.

### 0.3 — Federation cross-repo resolution spike (O-FED)
- [ ] Prototype `unresolved_refs.reference_name` + namespaced `qualified_name` resolution across 2 fixture repos; measure precision; confirm the side-by-side-marked fallback path.
- [ ] Files: `ci/probes/federation_spike.md` (NEW). Cross-doc invariant: none. Depends on: 0.2.

### 0.4 — LanceDB maintenance-contract bake-off rig (O-LANCE-BAKEOFF)
- [ ] Harness to measure `optimize()` latency, index-build RAM, steady-state disk (versions+transactions) on a representative multi-repo corpus on the reference Mac (Apple-Silicon, 16–32 GB).
- [ ] Files: `ci/bench/lancedb_maintenance/` (NEW). Cross-doc invariant: none. Depends on: none.

### 0.5 — Notarization spike
- [ ] Prove a PyInstaller sidecar + Tauri `.app` notarizes under hardened runtime (deep-sign order; `spctl`/`codesign --deep` gate). Document the signing recipe.
- [ ] Files: `packaging/notarization-spike.md` (NEW). Cross-doc invariant: none. Depends on: none.

### Acceptance criteria (0)
- [ ] All 0.X ticked; each spike has a recorded verdict; the fuzz + bake-off rigs are reusable by later phases.

---

## Phase 1 — Shared contracts & ports freeze (the bottleneck)

**Goal:** define + freeze every cross-track contract (Appendix A) and the 11 ports as typed interfaces with named test doubles. **Nothing forks until this lands.**

**Spec anchors:** `ARCHITECTURE.md §7`, §5, §4, §10, §14, §16, §18, Appendix A, §2.5.

**Track:** contract · **Depends on (phases):** 0.

### 1.1 — Determinism seams: `Clock` + `Seed`/`IdGen` ports
- [x] `Clock` and `Seed`/`IdGen` port interfaces + real + fake implementations; injectable everywhere (anchor revalidation, drift ranking, manifest timestamps, id minting). _(landed @track/contract `61853b3`; +`monotonic()`, +`Seed.rng()`; fakes in `core/testing/fakes.py`; 16 tests `spec(§7)`.)_
- [x] Files: `core/ports/clock.py`, `core/ports/idgen.py` (NEW). Cross-doc invariant: NEW (`Clock`, `Seed/IdGen` — §7). Depends on: none.

### 1.2 — The data contracts: chunk schema · version stamp · manifest + registry
- [ ] Frozen `Chunk`, store-level **version stamp**, `.project-brain/manifest.json` + global **registry** schemas (the §5 source-of-truth law: SHA-tag canonical, stamp canonical for schema/model/dim, manifest+registry derived); `schemaVersion` with a forward-only migrator + backup-before-migrate + downgrade-refuse.
- [ ] Files: `core/model/{chunk,stamp,manifest,registry}.py`, `core/model/migrations.py` (NEW). Cross-doc invariant: NEW (Chunk, version stamp, Manifest+Registry — §5; **§2.5-seam → brief RED outline MUST include the schema-snapshot test, `spec(§5)`-tagged**). Depends on: 1.1.

### 1.3 — Trust contracts: `Anchor` · `ProvenancePacket` + `EvidenceRef`
- [ ] Frozen `Anchor` (state enum incl. recovery + `orphaned`), `ProvenancePacket`, `EvidenceRef` (→ the 11-value EvidenceType / 22 IdKind at the seam).
- [ ] Files: `core/model/{anchor,provenance,evidence}.py` (NEW). Cross-doc invariant: NEW (Anchor, ProvenancePacket, EvidenceRef — §10; **§2.5-seam → schema-snapshot test `spec(§10)`**). Depends on: 1.1.

### 1.4 — The ports: Host · providers · CodeGraph · Event · Secret · Observability
- [ ] `HostPort` (`capabilities/authorize/perform`; closed allowlist enum), `EmbeddingProvider`/`Reranker`/`ContextStrategy`/`ModelProvider`, `CodeGraphPort`, `EventSource`, `SecretStore`(keychain), `ObservabilitySink` — interfaces + Fake doubles + cassette record/replay for cloud + Citations.
- [ ] Acceptance: StandaloneHost allowlist is a closed typed set `{own_store_write|owned_doc_refresh|consented_host_config}`; CodeGraphPort asserts `schema_versions` at startup + reads `CODEGRAPH_DIR`.
- [ ] Files: `core/ports/{host,providers,codegraph,events,secrets,observability}.py`, `core/testing/fakes.py` (NEW). Cross-doc invariant: NEW (the 9 ports — §7; **§2.5-seam → schema-snapshot test `spec(§7)`**). Depends on: 1.1.

### 1.5 — Boundary contracts: MCP tool contract · `policy.yaml` · `Redactor` interface
- [ ] Frozen MCP tool signatures (params incl. scope enum + project-id + top-k; result = chip+file:line+ids+provenance; streaming; policy-denied marker; **ingress validation** rules) · `policy.yaml` schema (providers/privacy `local|cloud`/boundary-filter/consent) · `Redactor` interface (`redact(payload, sink∈{persist,mcp_egress,cloud_egress})`).
- [ ] Files: `core/model/{mcp_contract,policy,redactor_iface}.py` (NEW). Cross-doc invariant: NEW (MCP contract, policy.yaml, Redactor — §14/§16/§18; **§2.5-seam → schema-snapshot test `spec(§14)`/`spec(§18)`**). Depends on: 1.1.

### Acceptance criteria (1)
- [ ] All Appendix-A freeze-before-fork models exist + have schema-snapshot tests; all 11 ports have interfaces + Fake doubles; `/preflight` clean. **This is the fork gate.**

---

## Phase 2 — Ingestion + Redactor (spine)

**Goal:** discover→classify→chunk→context-augment→**redact**→ready-to-embed, with the redaction zero-leak-on-catchable gate wired from the start.

**Spec anchors:** `ARCHITECTURE.md §8`, §18, §16, §5.

**Track:** spine · **Depends on (phases):** 1.

### 2.1 — Discovery + classification
- [ ] Source-agnostic discovery (md/code/schemas/`.github`) honoring `.gitignore`+`.brainignore`; classify producer/`doc_type`/owned·foreign·supplemental.
- [ ] Files: `core/ingest/{discover,classify}.py` (NEW). Cross-doc invariant: none. Depends on: 1.2.

### 2.2 — Anchor-aware chunking
- [ ] Docs heading-split + late-chunking; code AST via `CodeHierarchyNodeParser` (pinned) + **tree-sitter fallback**; emit `Chunk` + `Anchor`.
- [ ] Files: `core/ingest/chunk.py` (NEW). Cross-doc invariant: extended (Chunk/Anchor). Depends on: 1.2, 1.3.

### 2.3 — Redactor (catchable-set engine) + the fuzz gate
- [ ] Prefix/PEM/JWT + Shannon-entropy on KV/JSON-value, allowlist git-SHA/ULID/UUID; quarantine high-confidence-unsafe; runs at the persist sink (and is the same engine reused at MCP/cloud egress).
- [ ] Acceptance: **redaction-recall fuzz (Phase 0.1 rig) = zero-leak on the catchable set**; raw transcripts/`thinking` never reach a chunk.
- [ ] Files: `core/ingest/redactor.py` (NEW, implements 1.5 iface). Cross-doc invariant: extended (Redactor). Depends on: 1.5, 0.1.

### 2.4 — `add` ingest orchestration (idempotent)
- [ ] `add <repo>` runs the pipeline → context-augment → writes the manifest (derived projection); **re-add updates, never duplicates**; R-PARTIAL (ingest whatever exists, temp generation, no half-swap).
- [ ] Files: `core/ingest/pipeline.py`, `core/model/manifest.py` (extended) (NEW/extended). Cross-doc invariant: extended (Manifest). Depends on: 2.1, 2.2, 2.3.

### Acceptance criteria (2)
- [ ] A repo ingests to redacted, chunked, anchored, context-augmented records; fuzz gate zero-leak; `add` idempotent.

---

## Phase 3 — LanceDB index + maintenance contract (spine)

**Goal:** embed + write to a per-project LanceDB dataset with the full maintenance contract + the blue-green generation machine.

**Spec anchors:** `ARCHITECTURE.md §6`, §5, §16.

**Track:** spine · **Depends on (phases):** 2.

### 3.1 — LanceDB writer + hybrid table + version stamp
- [ ] Write chunks (vector+BM25+metadata+anchor) to a per-project dataset; stamp `{model,dim,schema,sha}`; **git-SHA version tag**; single-writer lease.
- [ ] Files: `core/index/lance_store.py` (NEW). Cross-doc invariant: extended (version stamp). Depends on: 1.2, 1.4.

### 3.2 — Maintenance contract
- [ ] `optimize()` after each upsert batch + `num_unindexed_rows≈0` monitor; scheduled `cleanup_old_versions()`; RAM-bounded batched builds; `spawn` not `fork`; arm64 wheels CI-verified.
- [ ] Acceptance: benchmark task vs the §6/§25 budgets (reference Mac) — **ONE discrete benchmark, not per-slice timing**.
- [ ] Files: `core/index/maintenance.py`, `ci/bench/lancedb_maintenance/` (extended). Cross-doc invariant: none. Depends on: 3.1, 0.4.

### 3.3 — Blue-green generation machine + ENOSPC
- [ ] Index-generation state machine (`building→reembedding→validating→swapping→active(+retired→gc→purged)`; failure discards new, keeps old); **ENOSPC pre-flight** (abort, retain prior, remediate); tombstone+replace keyed on `source_path`.
- [ ] Files: `core/index/generation.py` (NEW). Cross-doc invariant: NEW (Index-generation machine — §5; schema-snapshot `spec(§5)`). Depends on: 3.1.

### Acceptance criteria (3)
- [ ] A project indexes + serves queries; re-embed is blue-green with rollback; maintenance contract benchmark within budget on the reference Mac.

---

## Phase 4 — Retrieval + grounding (spine · NORTH STAR)

**Goal:** hybrid→rerank→hydrate→generate→**grounding gate**→provenance; the trust control with a deterministic test seam.

**Spec anchors:** `ARCHITECTURE.md §9`, §10, §11 (CodeGraphPort reads), §18.

**Track:** spine · **Depends on (phases):** 3.

### 4.1 — Hybrid retrieve + rerank + route
- [ ] Hybrid (dense+BM25) → rerank (~30–50→~10; deterministic RRF tie-break `(rrf_score desc, project_id asc, chunk_id asc)`); long-context-vs-RAG routing (<~200K → cached LC).
- [ ] Files: `core/retrieval/{hybrid,rerank,route}.py` (NEW). Cross-doc invariant: none. Depends on: 3.1, 1.4.

### 4.2 — CodeGraphPort + whole-file hydration (redacted)
- [ ] Structural tools (callers/callees/impact/explore/search) via `CodeGraphPort` CLI shell-out + tree-sitter fallback; whole-file hydration; **hydration egress passes the Redactor**.
- [ ] Files: `core/retrieval/{codegraph,hydrate}.py`, `core/ports/codegraph.py` (impl) (NEW/extended). Cross-doc invariant: extended (CodeGraphPort). Depends on: 1.4, 0.2, 2.3.

### 4.3 — Grounding gate + anchor revalidation + provenance
- [ ] Generate (ModelProvider + Citations) → **grounding gate: post-validate every cited span exists** (answer-but-flag; opt-in strict); continuous anchor revalidation (`live|stale|...` via `Clock`); attach `ProvenancePacket`.
- [ ] Acceptance: **deterministic test** against fixed `(retrieval-result, recorded-Citations-payload)` fixtures asserts 100% flag of injected unsupported/stale citations; **zero stale-anchor false-confidence**.
- [ ] Files: `core/grounding/{gate,revalidate,provenance}.py` (NEW). Cross-doc invariant: extended (Anchor, ProvenancePacket). Depends on: 1.3, 4.1, 4.2.

### Acceptance criteria (4)
- [ ] A query returns a grounded answer; the gate flags every unsupported/stale citation deterministically; provenance packet complete.

---

## Phase 5 — Embedded agent + CLI + eval spine (first vertical slice)

**Goal:** complete the vertical slice — `add` → `ask` (embedded agent or CLI) → grounded answer → eval green.

**Spec anchors:** `ARCHITECTURE.md §13`, §15, §19, §9.

**Track:** spine · **Depends on (phases):** 4.

### 5.1 — Embedded agent (LlamaIndex Workflow)
- [ ] A LlamaIndex Workflow driving the retrieval tools (Mode 1 read-only + Mode 2 draft); multi-turn state; budget rule + prompt-cache the stable prefix (cost control).
- [ ] Files: `core/agent/workflow.py` (NEW). Cross-doc invariant: none. Depends on: 4.3, 1.4.

### 5.2 — `nexus`/`nb` CLI
- [ ] `setup`/`add`/`sync`/`status`/`ask` headless commands over the core public API.
- [ ] Files: `cli/main.py` (NEW). Cross-doc invariant: none. Depends on: 5.1, 2.4.

### 5.3 — Eval harness spine + golden set
- [ ] CI-gated harness (custom evaluators → Langfuse local): grounding-gate correctness, anchor-revalidation, retrieval Recall@k; golden set = a fixture repo with scripted edits at known SHAs; hard gates separated from comparative.
- [ ] Files: `ci/eval/harness/` (NEW), `ci/eval/golden/` (NEW). Cross-doc invariant: none. Depends on: 4.3, 5.2.

### Acceptance criteria (5)
- [ ] `add` one repo → `ask` → grounded answer end-to-end on a real repo; **eval harness green** (the first-vertical-slice gate; tracks may now fork).

---

## Phase 6 — Federation router & registry

**Goal:** portfolio query — read-only fan-out over N indexes + union-rank; cross-repo resolution spike result; partial results marked.

**Spec anchors:** `ARCHITECTURE.md §11`, §5.

**Track:** federation · **Depends on (phases):** 1, 4.

### 6.1 — Registry + on-demand workers
- [ ] `~/.project-brain/` registry (derived; rebuildable by scanning manifests); on-demand worker activation + LRU idle eviction; only the router always-on.
- [ ] Files: `core/federation/{registry,workers}.py` (NEW). Cross-doc invariant: extended (Registry). Depends on: 1.2.

### 6.2 — Router fan-out + RRF + result-shape
- [ ] Read N LanceDB datasets read-only + N CodeGraph DBs; **union + RRF rank-fusion**; gate each on its **own** stamp; result carries `{projects_requested, answered, excluded[]}`; HYBRID-lean native co-indexing for same-root nests.
- [ ] Acceptance: a silently-partial portfolio answer is impossible (excluded[] always populated); optional DuckDB-Lance backing behind the same interface.
- [ ] Files: `core/federation/router.py` (NEW). Cross-doc invariant: none. Depends on: 6.1, 4.1, 0.3.

### Acceptance criteria (6)
- [ ] Cross-portfolio query returns a fused, ranked answer with excluded[] marked; cross-repo edges resolved-or-marked per the spike.

---

## Phase 7 — Sync & freshness + drift radar

**Goal:** keep indexes fresh (watcher + git-hooks) and surface staleness (never stale silently).

**Spec anchors:** `ARCHITECTURE.md §12`, §5, §10.

**Track:** sync · **Depends on (phases):** 1, 3.

### 7.1 — Watcher + git-hooks + incremental re-index
- [ ] Watchman/fswatch (debounced) + `post-commit/merge/checkout` hooks; content-hash delta → re-embed → tombstone+replace → `optimize()`; idempotent resume.
- [ ] Files: `core/sync/{watcher,hooks,incremental}.py` (NEW). Cross-doc invariant: none. Depends on: 3.1, 3.3.

### 7.2 — Drift radar + owned-doc refresh
- [ ] Revalidate anchors, rank by authority×recency×code-agreement; ownership-gated owned-doc refresh (don't-clobber 3-way-merge; the only bounded user-file mutation, via HostPort allowlist).
- [ ] Files: `core/drift/{radar,refresh}.py` (NEW). Cross-doc invariant: extended (Anchor, Doc-refresh machine). Depends on: 7.1, 4.3, 1.4.

### Acceptance criteria (7)
- [ ] Edits converge the index (watcher + hook backstop); drift surfaced + marked; owned-doc refresh never clobbers human edits.

---

## Phase 8 — MCP server & trust boundary

**Goal:** expose retrieval to external agents with ingress validation + egress redaction/policy — the trust boundary.

**Spec anchors:** `ARCHITECTURE.md §14`, §18, §9.

**Track:** mcp · **Depends on (phases):** 1, 4.

### 8.1 — FastMCP 3.x server + tools
- [ ] `search`/`get_file`/`graph`/`list_projects`/`status` per the frozen contract; streaming; policy-denied → marker-not-error; pin FastMCP major (3.0 migration budgeted).
- [ ] Files: `core/mcp/server.py`, `core/mcp/tools.py` (NEW). Cross-doc invariant: extended (MCP contract). Depends on: 1.5, 4.3.

### 8.2 — Trust boundary: ingress validation + egress redaction + transport auth
- [ ] Ingress: canonicalize+contain `get_file` paths, authorize scope vs registry+policy before fan-out, bound query/k/response sizes (Pydantic type + semantic). Egress: redactor + policy-filter regardless of caller (incl. hydration). Transport: stdio (parent-trust) + opt-in loopback (`127.0.0.1` + per-launch token, constant-time compare, Origin allowlist, DNS-rebinding defense).
- [ ] Acceptance: **INV-allowlist test** (no core module reaches fs/git mutation except via `HostPort.perform`); MCP-boundary contract test (redaction + policy-deny-marker + token auth + no-egress).
- [ ] Files: `core/mcp/boundary.py` (NEW). Cross-doc invariant: none. Depends on: 8.1, 2.3.

### Acceptance criteria (8)
- [ ] External agent queries are ingress-validated + egress-redacted/policy-filtered; loopback token auth hardened; security review clean.

---

## Phase 9 — Session memory & episode cards (opt-in)

**Goal:** opt-in, consent-gated, redacted session ingestion → episode cards (Claude first).

**Spec anchors:** `ARCHITECTURE.md §17`, §5, §18.

**Track:** sessions · **Depends on (phases):** 1, 2.

### 9.1 — EpisodeCard machine + consent gate
- [ ] State machine (`no_consent→...→embedded→linked`; terminals `consent_revoked`(purge), `superseded`); per-project consent stricter than docs; raw transcripts/`thinking` never embedded.
- [ ] Files: `core/sessions/episode.py` (NEW). Cross-doc invariant: NEW (EpisodeCard machine — §5; schema-snapshot `spec(§5)`). Depends on: 1.3, 2.3.

### 9.2 — Claude transcript ingest + commit linking
- [ ] Read Claude transcripts → redact → summarize → episode card; commit-link with confidence; Codex deferred `[P1]`.
- [ ] Files: `core/sessions/ingest.py` (NEW). Cross-doc invariant: extended (EpisodeCard). Depends on: 9.1.

### Acceptance criteria (9)
- [ ] Opt-in session ingest produces redacted episode cards; consent-revoke purges; no raw/thinking embedded.

---

## Phase 10 — Providers (pluggable) + bake-offs

**Goal:** the provider menu behind the frozen ports — user-choice local|cloud, version-stamped, blue-green on swap.

**Spec anchors:** `ARCHITECTURE.md §16`, §7.

**Track:** providers · **Depends on (phases):** 1.

### 10.1 — Local + cloud provider adapters
- [ ] Embedding (qwen3-embedding-4b local / voyage-code-3 cloud), reranker (qwen3-reranker / voyage-rerank-2.5), context (voyage-context-3 / late-chunking), generation (latest Claude); per-project `policy.yaml` selection; **honest local|cloud disclosure**; redaction+keychain regardless.
- [ ] Files: `core/providers/{embedding,rerank,context,model}.py` (NEW, implement 1.4 ifaces). Cross-doc invariant: extended (provider ports). Depends on: 1.4, 1.5.

### 10.2 — Bake-off harness (reranker + cloud embedder)
- [ ] In-domain golden-set bake-off (voyage-rerank-2.5 vs zerank-2 vs cohere; voyage-code-3 vs gemini-embedding-2) feeding the eval harness; records the chosen defaults.
- [ ] Files: `ci/eval/bakeoff/` (NEW). Cross-doc invariant: none. Depends on: 10.1, 5.3.

### Acceptance criteria (10)
- [ ] Provider swap works (blue-green re-embed); local|cloud user choice honored + disclosed; bake-off recorded.

---

## Phase 11 — Tauri desktop UI

**Goal:** the native desktop app — chat + evidence chips + freshness banner + project management, over the frozen core API.

**Spec anchors:** `ARCHITECTURE.md §15`, §2, §14.

**Track:** ui · **Depends on (phases):** 5, 8.

### 11.1 — Tauri shell + sidecar lifecycle
- [ ] Tauri host bundles the Python core sidecar (PyInstaller); loopback HTTP + per-launch token; sidecar supervise/respawn + token re-handshake.
- [ ] Files: `app/src-tauri/` (NEW). Cross-doc invariant: none. Depends on: 5.2, 8.2.

### 11.2 — Chat UI (NexusOps-ui-kit)
- [ ] Chat + evidence chips + freshness/staleness banner + provenance; project add/list/status; first-run/empty-portfolio flow.
- [ ] Files: `app/src/` (NEW). Cross-doc invariant: none. Depends on: 11.1.

### Acceptance criteria (11)
- [ ] Desktop app drives an end-to-end grounded ask with evidence chips + freshness; sidecar lifecycle robust.

---

## Phase 12 — Observability + eval wiring

**Goal:** OTel + OpenInference → Collector → Langfuse + SigNoz; ship instrumented-but-silent; eval harness fully wired as a release gate.

**Spec anchors:** `ARCHITECTURE.md §19`, §22, §25.

**Track:** observability · **Depends on (phases):** 5.

### 12.1 — OTel/OpenInference instrumentation (off-by-default, local-only)
- [ ] Instrument LlamaIndex + Anthropic + the system spans via `ObservabilitySink`; off-by-default + opt-in local diagnostics; **CI no-egress check** (never phone home).
- [ ] Files: `core/obs/otel.py` (NEW, impl 1.4 iface). Cross-doc invariant: none. Depends on: 1.4.

### 12.2 — Collector fan-out + dev/CI backends
- [ ] OTel Collector config (gen_ai→Langfuse; all→SigNoz) as dev/CI infra (compose profile, NOT shipped); wire the eval harness as a release gate.
- [ ] Files: `ci/observability/` (NEW). Cross-doc invariant: none. Depends on: 12.1, 5.3.

### Acceptance criteria (12)
- [ ] Instrumented-but-silent verified (no-egress); eval gate enforced in CI; backends are dev/CI-only.

---

## Phase 13 — Packaging + setup/lifecycle hardening

**Goal:** signed/notarized distribution + idempotent/reversible setup + auto-update quiesce + migration/backup — the production deploy/rollback path.

**Spec anchors:** `ARCHITECTURE.md §20`, §21, §22.

**Track:** packaging · **Depends on (phases):** 5, 11.

### 13.1 — `setup`/`uninstall` (idempotent · reversible · consented)
- [ ] `setup` provisions CodeGraph(`=1.0.1`)+Ollama+model (detect→install→**verify-by-hash, fail-closed**), MCP+skills registration, keychain, local|cloud choice — all via a mutation ledger; `uninstall` reverses every entry.
- [ ] Files: `core/setup/{provision,register,uninstall}.py` (NEW). Cross-doc invariant: none. Depends on: 5.2, 10.1.

### 13.2 — Packaging: `.dmg`/Cask + notarization + signed update feed
- [ ] Tauri-bundled signed/notarized `.dmg`/`.app` (per the 0.5 spike) + Homebrew Cask + auto-updater with a signed feed + Cask sha256 bump + yank/rollback.
- [ ] Files: `packaging/`, `ci/release/` (NEW). Cross-doc invariant: none. Depends on: 11.1, 0.5.

### 13.3 — Lifecycle hardening: auto-update quiesce + migration + failure-mode table
- [ ] Auto-update-while-mid-write quiesce/drain/resume handshake + store-integrity check; on-disk schema migration runner + backup + downgrade-refuse; shell↔sidecar↔store version handshake; the §22 failure-mode contracts (429/backoff, keychain-denied degrade, disk-full, crash-resume).
- [ ] Files: `core/lifecycle/{update,migrate,recovery}.py` (NEW). Cross-doc invariant: extended (manifest/registry migration). Depends on: 13.1, 3.3.

### Acceptance criteria (13)
- [ ] `.dmg` installs + notarizes; `setup`/`uninstall` fully reversible; auto-update is mid-write-safe; migration/backup/rollback proven; failure-mode tests green.

---

## Phase 14 — NexusOpsHost adapter & seam `[P2]`

**Goal:** the additive embedded adapter — propose-only via the NexusOps Gateway. **Deferred; never touches the spine.**

**Spec anchors:** `ARCHITECTURE.md §23`, §7, `docs/integrations/MAIN_PLATFORM_INTERFACE.md` v0.2.

**Track:** nexusops `[P2]` · **Depends on (phases):** 1.

### 14.1 — NexusOpsHost (propose-only)
- [ ] Implement `HostPort` as NexusOpsHost: every mutation → typed `ActionPlan`/`ActionRequest` to the Gateway; consume the redacted outbox (seq/dedup/unknown-tolerant); shared IDs; conform to frozen primitives.
- [ ] Files: `core/nexusops/host.py` (NEW). Cross-doc invariant: extended (HostPort; ActionPlan forward-shape). Depends on: 1.4.

### Acceptance criteria (14)
- [ ] Embedded mode proposes (never executes) via the Gateway; the core is unchanged (same engine, swapped adapter).

---

## Phase 15 — Implementation-plan & workflow-pack awareness `[P1]`

**Goal:** parse implementation plans into structured tasks + detect workflow pack-vs-instance state, surfaced as evidence + "what should I work on next" (FR-15/FR-16). PRD-roadmap P1; contracted at §27 (added at the tasks-gen gate per owner choice to architect-not-defer).

**Spec anchors:** `ARCHITECTURE.md §27`, §8, §5, §10.

**Track:** plans · **Depends on (phases):** 2, 4.

### 15.1 — ImplementationPlan + PlanTask parser
- [ ] Parse `IMPLEMENTATION_PLAN.md` (legacy `MVP_TASKS.md`; both names) → structured `{phases, tracks, tasks, anchors, acceptance, deps, architecture_refs}`; **degrade to whole-file ingest when unparseable** (never blocks); PlanTask manual-linking model (preserve manual links before any auto-sync).
- [ ] Files: `core/plans/parser.py` (NEW). Cross-doc invariant: NEW (ImplementationPlan, PlanTask — §27; **§2.5-seam → schema-snapshot test `spec(§27)`**). Depends on: 2.4, 1.2.

### 15.2 — Workflow pack/instance detector
- [ ] Classify cc-crew/workflow state (template-available vs personalized-instance vs the 12 R-7 states); enforce **template availability ≠ readiness**; index commands/skills/subagents/hooks/manifests; read `.scaffolding/manifest.json` **read-only**; expose readiness + drift.
- [ ] Files: `core/plans/workflow_detect.py` (NEW). Cross-doc invariant: extended (WorkflowInstance machine — §5). Depends on: 15.1, 2.1.

### 15.3 — Surface plan-tasks as evidence + "next task"
- [ ] Plan-tasks → evidence chips + the agent's "what should I work on next" reasoning; integrated, link to NexusOps shared IDs; graceful degradation on non-cc-crew repos.
- [ ] Files: `core/plans/surface.py` (NEW). Cross-doc invariant: none. Depends on: 15.1, 4.3.

### Acceptance criteria (15)
- [ ] A cc-crew project's plan parses into structured tasks; workflow state classified (template ≠ ready); plan-tasks surface as evidence; code-only repos degrade gracefully.

---

## Trims / Nice-to-Haves Catalog

_(Empty at project start; populated as scope cuts surface. Seeded nice-to-haves from the gap audit §6: first-run/empty-portfolio polish, P3 flows — since-you-left / cross-project impact, telemetry-consent UX, desktop a11y baseline, data export/backup/machine-migration, i18n scope note.)_

---

## Decisions tabled

- **Full schema-snapshot coverage (all Appendix-A models, not just §2.5-seam-crossed):** revisit off accumulated `/phase-exit` verdicts. _(Deliberate, user-approved exception to start-empty — the per-plan §2.5-seam snapshot seed.)_

---

## Log

_(Empty at project start; populated at every `/orchestrate-end`.)_
