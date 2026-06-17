This is a synthesis task. I have all the per-dimension findings and PRD→REQ coverage in the input. My job is to consolidate into a single de-duplicated, bucketed report for the human gate. Let me produce that directly — no file reads needed since the input contains everything, and I'm instructed to return findings as my final message, not write files.

Let me synthesize, de-duplicating aggressively across dimensions (many findings overlap: manifest filename inconsistency appears in D4/D5/D7; redaction zero-leak claim in D9/D11; loopback token in D8/D11; blue-green/disk in D2/D3; §2.5 DAG in D13/D14; cost model in D6/COMP; etc.).

# Nexus Brain — Architecture Finalization: Consolidated Adversarial Audit (Human Gate)

Synthesis of 15 dimension audits + PRD→REQ coverage. De-duplicated, bucketed, decisive. Citations are `file:section`. Build posture = production-grade (no timebox); error paths, idempotency, observability, secrets, deploy/rollback, and the LanceDB maintenance contract are baseline.

---

## 1. CRITICAL FINDINGS (resolve before the contract is binding)

Each finding lists the merged source IDs, a proposed fix, and whether owner confirmation is needed.

### C-1. Decision status contradiction: D-20/D-21/D-22 tagged `[proposed]` but treated as `[LOCKED]` everywhere downstream
*(D7-1)* DECISIONS.md tags D-20 (packaging), D-21 (one-core/two-adapters + monorepo + published core), D-22 (ship-instrumented-but-silent) `[proposed]`, yet CLAUDE_CODE_HANDOFF, OPEN_QUESTIONS, ARCHITECTURE_DRAFT §3/§14/§16, CONSTRAINTS, REQUIREMENTS all consume them as locked. These three fix the distribution channel, the entire module/repo topology §6 builds on, and the telemetry posture.
**Fix:** Owner locks all three → re-tag `[locked — owner]`; OR downgrade the dependent `[LOCKED]` tags and remove from the "Decided" lists. One source of truth. **Needs owner confirmation (load-bearing).** See LBD-1.

### C-2. The MCP tool contract is undefined — the single most load-bearing interface
*(D4-1; ingress half = D8a-1)* `search`/`get_file`/`graph`/`list_projects`/`status` appear as bare names with zero param/return/error/streaming/scope-filter shapes across all 18 artifacts. It is BOTH the standalone trust boundary AND the NexusOps seam. Additionally, the draft frames it as egress-only (redact-on-exit) and never specifies **ingress validation**: `get_file` path-traversal containment, `project_id`/scope authorization against the registry+policy before fan-out, and query/k/response-size caps (DoS/cost-amplification over the always-on loopback transport).
**Fix:** Appendix-A invariant defining each tool's full signature (params incl. retrieval-scope enum + project-id scoping + top-k; result = evidence chip + file:line + stable IDs + provenance packet; streaming contract; policy-denied → marker-not-error per Flow 4) AND the ingress contract (canonicalize+contain paths, authorize scope, bound sizes; Pydantic type-validation + semantic validation before store access). Pin FastMCP 3.x tool-registration shape. **Needs owner confirmation (contract).**

### C-3. The 8 port signatures are undefined — the ports-and-adapters spine and the standalone↔embedded swap point
*(D4-2)* HostPort, EventSource, EmbeddingProvider, Reranker, ContextStrategy, ModelProvider, ObservabilitySink, SecretStore — not one has a method signature. The "embedded = additive adapter, zero core refactor" claim (D-21) is unverifiable until these freeze.
**Fix:** Appendix-A interfaces: `HostPort.authorize/perform/capabilities` (StandaloneHost allowlist as a closed typed mutation enum: own-store-write | owned-doc-refresh | consented-host-config; show NexusOpsHost→ActionPlan serialization), `EmbeddingProvider.embed/dimension/model_version`, `Reranker.rerank`, `ContextStrategy.augment`, `ModelProvider.generate` (Citations API), `ObservabilitySink.emit`, `SecretStore.get_ref/resolve`, `EventSource.subscribe/poll`. **Needs owner confirmation (contract).**

### C-4. Freshness/version metadata is multi-written with NO authoritative owner — directly threatens the trust north star
*(D5-1 + D5-2 + D5-6; field-set drift = D4-13)* The index's git SHA exists in four places (chunk `ingested_from_sha`/`last_resolved_sha`, store stamp, manifest `ingestedFromSha`/`staleness_pointer`/`lance_version_tag`, registry `last_indexed_sha`) with no canonical/derived rule. Separately, the **federation router gates on the REGISTRY copy** of schema/model/dim while truth lives in the LanceDB store stamp — a stale-gate hazard that can admit a dim-mismatched store or wrongly exclude a healthy one. Store-stamp field set itself differs across DATA_MODEL/USER_FLOWS/FR-5 (is `ingested_from_sha` store-level, chunk-level, or both?). Because "never stale silently" is the load-bearing support beneath the trust north star, divergence here is the cardinal failure.
**Fix:** Declare ONE authoritative owner. Recommended: LanceDB version tag (git-SHA, GC-exempt) = canonical SHA; store-level stamp = canonical schema/model/dim; manifest + registry = **derived projections** rebuilt from the dataset on every commit and reconciled at startup. Router gates on the store's OWN stamp read at fan-out (registry = routing index only). Freshness banner = `delta(git HEAD, index.recorded_sha)` with a distinct "dirty working tree" state. Unify the store-stamp field set. **Needs owner confirmation (load-bearing).** See LBD-3.

### C-5. EpisodeCard lifecycle has NO state machine — security/consent-load-bearing
*(D2-01)* Every other entity has an enumerated machine; EpisodeCard (the most sensitive input: redaction, consent, quarantine, revocation) has only prose (Flow 7). No terminal states, no idempotency for re-ingest, no consent-revoked/quarantine state to anchor a test for "never embed raw / never embed thinking."
**Fix:** `no_consent → consent_granted → reading → redacting → (quarantined_unsafe | redacted) → summarizing → embedded → linked`, with terminals `consent_revoked` (purge embedded card + raw) and `superseded` (re-ingest same session_id). Invariants checked at `redacting→redacted`; quarantine is per-span.

### C-6. Provider blue-green swap has no orchestration state machine + disk-doubling failure mode unhandled
*(D2-02 + D3-1 + D3-10)* The blue-green swap exists only as Flow 9 + a one-line note; `swapped` is ambiguous, there's no `validating` gate before atomic swap, no `reembedding_failed/resumable` state, and dim-mismatch (hard rebuild) vs same-dim (re-embed) are unmodeled as distinct entries. **Compounding:** disk-full/ENOSPC is unhandled in ALL artifacts — blue-green writes a whole new generation before swap (doubling transient disk for a large repo in a portfolio), with no pre-flight space check or graceful-abort-keeping-prior-generation.
**Fix:** Explicit machine: `active(G_old) + building(G_new) → reembedding → validating → swapping → active(G_new) + retired(G_old) → gc_eligible → purged`; failure edges discard G_new, keep G_old. Add pre-flight free-space estimate; on ENOSPC abort in-progress generation, retain prior, surface disk-full + `cleanup_old_versions()` remediation; "low disk" is a degraded state. Tie `retired→purged` to the GC-exemption contract. **Owner must confirm:** is "new generation" a physical copy or Lance native version-layering? This materially changes the disk multiplier and pre-flight design. See LBD-7.

### C-7. Model rate-limit / 429 / timeout conflated with "API down" — both embed and generate paths exposed
*(D3-2)* Only "model down → retrieval-only" exists. 429/Retry-After, per-request timeouts, mid-stream disconnects warrant backoff + partial-result handling, not immediate hard fallback. Embed-side rate-limit during a large multi-repo ingest is entirely unaddressed (silent stall/batch-fail).
**Fix:** Provider-call resilience contract: bounded exponential backoff honoring Retry-After on 429; per-request timeout budgets distinct from "down"; embed rate-limit → pause+resume from content-hash manifest (idempotent); only after retries exhaust fall back. Add a "rate-limited/backing-off" observable status.

### C-8. CodeGraph is a stale major version with a feature that may obsolete the federation premise
*(D6-1)* The `[locked]` dependency the D-2 federation differentiator rests on shipped v1.0.0/1.0.1 (2026-06-12/13) with breaking changes (config-file removed; MCP tools cut 8→4) AND **"workspace multi-repo indexing"** — which directly undercuts the `[VERIFIED]` premise that CodeGraph has NO native cross-repo support. All pins target `0.9.7`.
**Fix:** Re-probe `@colbymchenry/codegraph@1.0.1` before finalize: (1) does workspace multi-repo subsume the brain's federation router? (2) did the SQLite schema (`schema_versions`, `nodes`/`edges`/`unresolved_refs`) survive 1.0 — D-12 reads it directly; (3) re-enumerate the 4-tool MCP surface vs the callers/callees/impact/trace assumptions; (4) bump pins in C-5/A-5/D-12. **Needs owner confirmation:** keep building federation vs lean on native multi-repo. See LBD-8.

### C-9. Voyage training opt-out is NOT programmatically enforceable — the privacy gate as specified is undeliverable
*(D6-2)* D-23/SR-2/C-12 require the cloud adapter to "enforce + document" the opt-out and "refuse cloud without opt-out confirmed." In reality it's an account-level dashboard toggle (org-Admin + payment method), not a per-request flag; pre-opt-out data stays trainable forever; opt-in is irreversible. The invariant "cloud training opt-out enforced" is not implementable.
**Fix:** Restate honestly: adapter cannot enforce an account setting. Mechanism = a documented setup gate that blocks the Voyage adapter until the user attests they toggled org-level opt-out, warns that pre-opt-out embeddings are permanently retained, and surfaces irreversibility. Consider restricting cloud to generation-only (ZDR) with local-only embedding as the hard default. **Needs owner confirmation (weakened guarantee).** See LBD-9.

### C-10. "Cloud generation over ZDR" assumes ZDR the target user won't have; Fable-5 is ZDR-incompatible
*(D6-3)* ZDR requires a separately-negotiated enterprise agreement, not on standard Enterprise, not toggleable — the single-user local-first target almost never holds it, so the default cloud path silently runs WITHOUT ZDR, contradicting the stated posture. Fable-5/Mythos-class models are not ZDR-eligible at all (mandatory 30-day retention), so ZDR+Fable-5 is structurally impossible (400).
**Fix:** Separate aspiration from default. State ZDR is enterprise-only; make the DEFAULT cloud-generation path explicit about non-ZDR retention OR make strict-local generation the default with cloud as informed opt-in. Pin generation to a ZDR-eligible model (Opus 4.8) when ZDR is configured; refuse Fable-5 under a ZDR profile. **Needs owner confirmation (default generation posture).** See LBD-10.

### C-11. Redaction "zero leaks (hard gate)" is undeliverable by the very engine it inherits
*(D11-1 + D9-4)* THREAT_MODEL T-1/SR-1 promise "zero leaks" and claim to mirror NexusOps prefix-entropy-v3 — but that engine has a MEASURED envelope of recall_catchable=1.0 / overall=0.75 with three accepted residual leak classes (≈git-SHA hex, adversarial <20-char split, sub-20-char JSON values). A literal-zero hard gate over arbitrary input either blocks every release or is silently scoped to "catchable" — a trust hole. The harness also has no recall-floor/FP-ceiling numbers, no corpus method, no generator, no leak definition, and PRD OQ#12 ("how to test transcript redaction") is still `[OPEN]`.
**Fix:** Reframe the gate to "zero leaks on the **catchable set**" (recall-floor on curated prefix/entropy/JSON-value classes), explicitly enumerate the accepted residual classes as ACCEPTED-AND-OWNED, and name **keychain-refs-only as the primary control** with redactor as defense-in-depth. Specify the harness: leak definition = secret surviving into chunk text/vector OR cloud-egress payload OR MCP result (redactor runs at all three points — assert all three); property generator + curated adversarial seed corpus; quantified recall floor + FP ceiling. Resolve OQ#12. **Needs owner confirmation (the trust gate's actual contract).** See LBD-11.

### C-12. No on-disk schema migration / backup / rollback for the local stores
*(D8a-4 + D10-2)* schema_version lives in non-cache data (manifest, registry, LanceDB store stamp). "Exclude+flag on mismatch" only EXCLUDES; it does not migrate. No forward migrator, no backup-before-migrate, no rollback on downgrade. On a brain schema bump, every project silently re-indexes (expensive cloud re-embeds). NexusOps solved exactly this via SQLite `user_version` migrations; the brain has no analogue. OQ-6 leaves the manifest schema unfrozen.
**Fix:** Forward-only migration runner keyed on schemaVersion for manifest + registry; documented procedure for store-stamp bumps (in-place metadata vs blue-green rebuild); backup-before-migrate (copy/version tag); on migration failure restore backup + surface error; on app downgrade refuse-with-guidance (never read a forward-schema store). Promote OQ-6 to a freeze-before-first-ingest gate. **Needs owner confirmation (OQ-6 freeze).** See LBD-4.

### C-13. No contract for auto-update while the sidecar is mid-write
*(D10-1)* §16 says "auto-updater" and nothing else. A Tauri/Sparkle update replaces the .app and relaunches; if the sidecar is mid-batch it's in the exact window the D-25 contract calls dangerous (un-optimized index silently drops rows; blue-green mid-swap → half-written generation; optimistic-commit conflict). No quiesce/drain/resume handshake.
**Fix:** §16 update-lifecycle: shell signals sidecar to stop ingest → drain/commit + optimize() or atomically abandon to prior generation → checkpoint resume manifest → ack "safe-to-replace" → swap .app → relaunch → run store-integrity check before serving. Define max-drain timeout + force-quit fallback (idempotent resume).

### C-14. §2.5 subsystem dependency DAG does not exist — blocks the entire parallelization plan
*(D14-1/D14-4 + D13-1)* The template mandates §2.5 (the SOLE source /tasks-gen uses to derive parallel tracks). §6 lists 16 subsystems with ZERO edges; §19 is a flat 0–10 build order (a sequence, not an import-DAG). Without it the Track map cannot be authored and the build collapses to serial by default rather than by decision. The Appendix-A freeze-before-fork contract set is also underived, and contract #2 (manifest schema) is openly OPEN (OQ-6).
**Fix:** Author §2.5: Mermaid import-direction DAG (`entrypoints → agent → {retrieval, drift, federation} → grounding → index → ingest → {redactor, providers, ports, manifest/registry}`; ports/redactor depend on nothing; observability is a leaf sink). Name the forced-serial spine (= D-18 vertical slice), the independent tracks T-A…T-G, and the 7 freeze-before-fork contracts (chunk schema, manifest+registry schema, HostPort, the 4 provider ports, Anchor, ProvenancePacket+EvidenceRef, version stamp). Model redactor + grounding as fan-in hubs, not pipeline stages. **Needs owner confirmation (DAG + freeze set).** See LBD-14.

### C-15. The grounding gate — the north-star control — has no deterministic test seam, and the test fakes don't exist
*(D9-1 + D9-3)* The gate's span-existence check is fully deterministic given a fixed retrieval result + a recorded Citations payload, but §17 lists only "anchor parse" as test-first and EVALUATION_CRITERIA places gate correctness in the non-deterministic Trust table — so the most important gate is only testable behind a live model. **Root cause:** the "injectable clock/seed" and "recorded fixtures" the whole non-deterministic strategy rests on are named as phrases but never defined as architectural seams — no Clock port, no Seed/IdGen port, no FakeEmbeddingProvider/FakeReranker/FakeModelProvider, no record/replay adapter (contrast NexusOps's explicit Clock+IdGen+FakeHarness+FakePty).
**Fix:** (a) Split the gate into a deterministic post-validation contract tested against fixed (retrieval-result, recorded-Citations-payload) fixtures (assert 100% flag of injected unsupported/stale citations) + an eval-covered end-to-end tier. (b) Add Clock + Seed/IdGen ports and named test doubles (Fake* providers + cassette-style record/replay for cloud + Citations API) to the ports list; thread Clock through anchor revalidation, drift ranking, manifest timestamps.

---

## 2. IMPORTANT FINDINGS

**Schemas / contracts (de-duped):**
- **Manifest filename inconsistency** *(D4-3 = D5-5 = D7-2)*: `.project-brain.json` (ONBOARDING R-ADD) vs `.project-brain/manifest.json` (everywhere else) — different on-disk contracts. **Fix:** standardize on the directory form `.project-brain/manifest.json`; correct/supersede ONBOARDING R-ADD.
- **policy.yaml schema undefined** *(D4-4)* — security-load-bearing config (provider+privacy, MCP-boundary filter, federation visibility, session consent) with no fields. Define as Appendix-A schema; state which fields the MCP boundary enforces vs the redactor consumes. Clarify **policy.yaml = desired config, store stamp = realized config** *(D5-8)*, with transitional behavior during blue-green.
- **Provenance Packet field-set drift** *(D4-7)*: DATA_MODEL omits `timestamps`/uses `low_confidence_links`; PRD §7.10 lists `Timestamps`/`Low-confidence association markers`. Reconcile to one frozen shape.
- **LanceDB chunk schema missing fields** *(D4-8)*: generation/version marker (blue-green), tombstone/active state, plain|deep dual-register storage, episode-card linkage + `linked_tasks`.
- **Manifest schema (OQ-6) should freeze now, not "at first ingest slice"** *(D4-9 = D8a-4 = D14-4)* — it blocks the federation/registry/ingest tracks.
- **NexusOps status mapping** *(D4-5)*: brain must emit 9 of the frozen 10-value ProjectBrain vocabulary, but no brain-state→emitted-status table exists and the vocabularies don't align 1:1. Add a binding mapping table.
- **EvidenceType serialization is lossy** *(D4-6)*: 3 chip kinds (Agent-team-run, Decision-record, Test-result) don't map cleanly onto the 11-value enum; promote the PRD §7.2 mapping into the binding data model.
- **ActionPlan wire shape absent from DATA_MODEL** *(D4-10)*; action_type subset not verified against the frozen catalog.
- **BrainEventMapping + outbox-consumer envelope** *(D4-11)* unpinned (seq-order, dedup, unknown-tolerance) — `[P2 co-design]`.

**Lifecycle states (de-duped):**
- **Worker machine** *(D2-03)* missing crash/reattach + single-writer-lease/write-blocked states (D-25 W3 load-bearing).
- **Anchor machine** *(D2-04)* no recovery edges back to `live`, no `orphaned/deleted` terminal; grounding gate keys on `live` (PR-1). **Anchor storage owner ambiguous** *(D5-4)*: chunk-inline vs separate store; determines whether revalidation write-back touches the single-writer/optimize() contract.
- **Project machine** *(D2-05)* no `index_failed/degraded`; `archived` vs `removed` conflated; no drift-dismissed edge; illegal transitions (query-while-indexing, re-add) unspecified.
- **WorkflowInstance** *(D2-06)*: 12 frozen states listed, transition graph defined nowhere. **Open: is the transition graph part of the frozen R-7 contract or brain-authored?** *(D2-11)* — co-design with NexusOps. See LBD-22-adjacent.
- **Doc-refresh** *(D2-07)* is a stateful consent+conflict workflow modeled only as a classification table (the only bounded user-file mutation — SR-4).
- **Status-bearing entities with zero enumerated states** *(D2-08)*: PlanTask, ImplementationPlan, PersonalizationRun (also flow-orphaned), ActionPlan.

**Failure modes (de-duped, promote into §18):**
- **Sidecar crash/supervision** *(D3-3)*: who respawns, in-flight-request semantics, token re-handshake, crash-loop backoff — standalone (Tauri host) vs integrated (NexusOps daemon).
- **Legitimate single-writer commit-conflict** *(D3-4 = COMP-2)*: watcher + git-hooks + re-embed can self-conflict; the serialization mechanism (per-project write queue/lock) is asserted but un-mechanized. **Also covers UI-agent vs external-MCP-agent concurrency on the same store** — define reader-during-reindex consistency and multi-caller mutation coalescing.
- **Federation partial-failure result-shape** *(D3-5)*: no `projects_requested vs answered + excluded[]` coverage field; a silently-partial 3/5 portfolio answer is the federation analogue of PR-1.
- **CodeGraph schema-mismatch gating** *(D3-6)*: behavior undefined and conflated with the LanceDB store stamp; disambiguate (store-stamp mismatch → exclude project; CodeGraph schema mismatch → degrade that repo to vector-only).
- **Runtime keychain-denied** *(D3-7)*: only setup-time handled; runtime denial mid-ask/ingest → degrade to local-only with a clear status, never plaintext fallback.
- **§18 itself is a lossy `[LOCKED]` one-paragraph** *(D3-9 + D13-9)* that under-covers its own delegated sources; expand into a full mode·trigger·signal·recovery·status·test table (tasks-gen anchors to the body, not RISKS.md).

**Security (de-duped):**
- **Loopback-HTTP token lifecycle unspecified** *(D8a-2 = D11-2)*: entropy, at-rest storage (not env-var/`ps`-readable), constant-time compare, 127.0.0.1 binding, replay protection, expiry on sidecar recycle, AND browser/WebView Origin allowlist + non-simple-header DNS-rebinding defense (D-17 allows a WebView UI). This is the one authn mechanism.
- **No stdio/loopback peer-auth analog to NexusOps getpeereid()** *(D11-3)*: state standalone MCP peer-trust (stdio = parent-process trust; loopback = token); recommend uid-level peer rejection on loopback.
- **Bounded-allowlist enforcement mechanism unspecified** *(D11-4)*: HostPort "authorizes" but no single chokepoint + architecture-invariant test (contrast NexusOps Gateway INV-SEC-1). Add the test proving no core module reaches an fs/git mutation except via `HostPort.perform`.
- **Supply-chain integrity for pulled models/binaries** *(D11-5)*: "verify" in setup is undefined — pin model + CodeGraph artifacts by SHA-256/signature, fail-closed, record a provenance manifest.
- **get_file / whole-file hydration may bypass redaction** *(D11-6)*: redaction-before-embed operates on chunks; raw hydration reads source at query time. State that ALL MCP egress (incl. hydration/get_file) passes the redactor; add a distinct fuzz case.
- **Structured app logging + log-redaction absent** *(D8a-3)*: only off-by-default OTel tracing exists; T-3 omits logs from the secret-exclusion list. Add always-on local-only JSON logs, scrubbed, never phone-home.

**Deploy/rollback (de-duped):**
- **Notarization precedent doesn't exist** *(D10-4)*: NexusOps decision-005 is `[LOCKED-PENDING-SPIKE]` (#11992). Reclassify A-7/TR-8 from "assumption/precedent" to a brain-side pre-build spike.
- **LanceDB/Lance-format pin-upgrade path** *(D10-3)*: blue-green covers model/dim, not a storage-format/library bump; add an open-old→rewrite-new migration gated by a fixture-from-previous-pin CI test.
- **Update-channel integrity + bad-release rollback** *(D10-5)*: signed feed (Tauri/Sparkle key custody), Cask sha256 auto-bump, yank/downgrade path; add to THREAT_MODEL.
- **Shell↔sidecar↔store version-skew** *(D10-6)*: handshake announcing core API/protocol range; refuse mismatched; cross-channel (Cask/pipx/brew) skew policy.
- **Uninstall reversal incomplete** *(D10-7)*: add PATH symlink, launchd/systemd unit, per-repo git hooks, update caches to the mutation ledger.
- **Registry/manifest backup + rebuild-from-manifests** *(D10-8 = D5-3)*: declare manifest = source-of-truth per-project, registry = derived index rebuildable by scanning manifests; write-temp-then-atomic-rename + last-good copy.

**Testing (de-duped, beyond C-11/C-15):**
- **Federation rank-fusion test/eval contradiction** *(D9-2)*: §17 says test-first, EVAL line 34 says eval-covered. Resolve: RRF math = deterministic/test-first with a specified total-order tie-break `(rrf_score desc, project_id asc, chunk_id asc)` + defined accumulation order; fused-result quality = eval-covered.
- **IR-1/IR-2 contract-snapshot tests missing from §17** *(D9-5)*: add schema-conformance against `nexusops-contract.schema.json 0.34.0` (22 IdKind, 11 EvidenceType, ActionPlan family) + core-public-API stability snapshot.
- **Golden-set construction unspecified** *(D9-6)*: labeling source, anchor-state ground-truth via a fixture repo with scripted edits at known SHAs, min CI set size, dataset-versioning rule for "no-regression."
- **Release-gate thresholds deferred to "first bake-off"** *(D9-7 = D15-1/2/6)*: separate absolute hard gates (zero-leak-on-catchable, zero stale-anchor false-confidence, zero unauthorized-mutation, no-egress) from comparative gates; quantify the maintenance-contract invisibility SLO.
- **No crash-injection / idempotency / atomic-swap / degraded-mode tests** *(D9-8)* despite TR-5 naming a re-embed-equivalence test.
- **MCP-boundary contract test missing** *(D9-9)*: redaction + policy-denied-omit-with-marker + loopback-token auth + CI no-egress check.

**Scope / completeness (de-duped):**
- **add idempotency** *(D8a-6)*: re-add must update-not-duplicate (registry row, manifest, watcher, hook, dataset).
- **Cloud cost/budget control** *(D6-4 = COMP-1)*: no per-query/session token-or-dollar budget, no spend telemetry, no cap. Add a cost contract (budget rule on the agentic loop, prompt-cache the stable prefix, surface estimated cost, cost/token eval). Merge with the 429 work (C-7).
- **Cloud model deprecation/sunset** *(COMP-3)*: distinct from user-initiated swap; detect model-unavailable → forced-migration + "index pinned to retired model" signal.
- **Data export/backup/restore/machine-migration** *(COMP-4)*: episode cards + provenance are NOT source-reproducible; uninstall purges. Add export/import and prioritize irreplaceable assets.
- **qwen3-embedding-4b MS MARCO license ambiguity** *(D6-5)*: downgrade from clean `[VERIFIED]` Apache-2.0; keep bge-m3 (MIT) as the clean fallback. (Personal/portfolio use may not bite — but the tag overstates certainty.)

**Diagrams** *(D12-1…4, all important)*: add planned diagrams for install/bootstrap/uninstall, propose-only ActionPlan seam, session-ingestion/episode-card pipeline, and blue-green re-embed flow.

**Task-planning anchors (de-duped, D13):** split overloaded sections — §8 → Ingestion / Retrieval / Grounding; §11 → Agent / MCP-boundary / CLI+UI; §16 → Packaging / Setup-lifecycle; add dedicated anchors for Ports-contracts, Sessions/episode-cards, NexusOps-seam consolidation (§12+§20 overlap); add the Spec Anchor Index (REQ→§) and Appendix A (model→§). Reconcile the flat §19 build order with the §2.5 DAG.

---

## 3. LOAD-BEARING DECISIONS FOR THE HUMAN GATE

One decision each; recommendation + why.

| # | Decision | Recommendation | Why |
|---|---|---|---|
| **LBD-1** | **Lock D-20, D-21, D-22?** | **Lock all three** as `[locked — owner]`. | Every downstream artifact already treats them as `[LOCKED]`; the only inconsistency is the ledger tag. They fix the distribution channel, the repo/module topology §6 builds on, and the telemetry posture — finalize cannot bind a `[proposed]` decision. (C-1) |
| LBD-2 | **MCP tool contract + ingress validation** — freeze the signatures now? | Yes; freeze as Appendix-A. | It's both the standalone trust boundary and the NexusOps seam; two surfaces + the future NexusOpsHost depend on it; unbuildable until frozen. (C-2) |
| LBD-3 | **Authoritative owner of freshness/version metadata** | LanceDB version tag = canonical SHA; store stamp = canonical schema/model/dim; manifest + registry = derived projections; router gates on the store's own stamp. | "Never stale silently" is the trust north star's load-bearing support; four uncoordinated copies + a registry-based federation gate is the cardinal failure path. (C-4) |
| LBD-4 | **Freeze the manifest schema now (close OQ-6) and adopt a migration contract?** | Yes — freeze before first ingest slice + forward migrators + downgrade-refuse. | Manifest/registry are non-cache data; "exclude+flag" forces full re-embeds on every bump; OQ-6 blocks the federation/registry/ingest/app tracks from forking. (C-12, C-14) |
| LBD-5 | **PB-8 action modes: which of the 5 ship in scope vs P-tier?** | Mode 1 (read-only) + Mode 2 (Draft, no-mutation) in scope; Mode 3 (single confirmed) standalone via HostPort allowlist; Mode 4 + Mode 5 deferred P2. | PB-8 is a MUST on all 5 but only Mode-4 maps to a flow; Draft produces no mutation so it's not even integration-gated; the architecture must say where each lives. (D1-01, coverage gap) |
| LBD-6 | **Web-console → desktop-app substitution** (PRD §12 "minimal web/dev console" vs the Tauri app) | Confirm the swap; no lighter early-milestone console. | DECISIONS.md:56 "No web app" + FR-21 supersede the PRD MVP wording; owner should ratify so no early dev console is silently expected. (coverage) |
| LBD-7 | **Blue-green = physical copy or Lance native version-layering?** | Confirm (recommend Lance version-layering if supported). | Determines the transient disk multiplier, the pre-flight space-check design, and `cleanup_old_versions()` cadence. (C-6 / D3-10) |
| LBD-8 | **CodeGraph 1.x: keep the federation router or lean on native multi-repo?** | Re-probe 1.0.1 first; keep the read-only federation router unless native multi-repo demonstrably subsumes it. | The `[locked]` dep shipped a major bump with a multi-repo feature that may obsolete the D-2 premise; pins/schema/MCP-surface all need re-verification. (C-8) |
| LBD-9 | **Voyage cloud-embed posture given opt-out is un-enforceable** | Restate the gate as attest-and-warn; consider local-only embedding as the hard default, cloud generation-only as the opt-in. | The threat-model invariant "opt-out enforced / refuse cloud without it" cannot be implemented as written. (C-9) |
| LBD-10 | **Default cloud-generation posture given ZDR is enterprise-only** | Make strict-local generation the default OR make non-ZDR retention explicit at the opt-in; pin a ZDR-eligible model + refuse Fable-5 under a ZDR profile. | ZDR won't realistically be available to the single-user target; the stated "cloud over ZDR" default silently runs without ZDR. (C-10) |
| LBD-11 | **Redaction gate contract** | "Zero leaks on the catchable set" + enumerated accepted residuals + keychain-refs-only as primary control. | A literal-zero gate is undeliverable by prefix-entropy-v3; resolve PRD OQ#12. (C-11) |
| LBD-12 | **WorkflowInstance transition graph: frozen R-7 contract or brain-authored?** | Confirm with NexusOps; if only the state set is frozen, brain authors transitions for its heuristics + a contract-snapshot test. | Determines whether D2-06's graph is co-designed or unilateral; BrainEventMapping is "a live design surface on both sides." (D2-11) |
| LBD-13 | **Local adversary scope: same-uid process trusted?** | Recommend (A) same-uid trusted (token defends different-uid users + browser pages; same-uid exfil = stated non-goal). | D-5 ("single OS user") implies same-uid trust but T-6 ("untrusted caller") is in tension; this sizes the loopback-token + peer-auth work (LBD-2-adjacent). (D11-8) |
| LBD-14 | **§2.5 DAG + the 7 freeze-before-fork contracts + build mode (agent-team vs single-operator)** | Author multi-track DAG (correct dependency truth, survives both modes); confirm build mode. | §2.5 is the sole source /tasks-gen reads for tracks; the owner is a solo dev (leans single-operator → DAG collapses to a serial hint) but the production posture suggests team-mode. (C-14, D14-6/7) |
| LBD-15 | **Reference hardware baseline** for all perf budgets | Pin a chip tier + unified-RAM baseline + minimum-supported spec. | "Typical Mac" spans an order of magnitude in memory bandwidth; every latency/RAM/throughput budget is meaningless without it. (D15-7) |
| LBD-16 | **Interactive query-latency + Freshness success-metric thresholds** | Set p50/p95 for classic vs agentic-RAG paths, plus index-lag / drift-latency / time-to-first-grounded-answer numbers (or explicitly defer with acknowledged GA risk). | Three are declared PRD Success Metrics; thresholdless they cannot pass/fail at GA. (D15-1, D15-2) |
| LBD-17 | **Finalized §-numbering becomes the append-only baseline** | Confirm; the draft's §0–§21 are discarded as non-binding. | Once IMPLEMENTATION_PLAN.md cites these anchors they cannot be reordered; the recommended ~24-section list renumbers the draft. (D13-13) |
| LBD-18 | **Shared signing identity / notarization / update-feed key with NexusOps?** | Confirm shared-vs-separate Apple Developer ID + appcast key + CI secret store. | Load-bearing for the release pipeline, supply-chain trust, and the eventual integrated bundle. (D10-11) |

---

## 4. PRD → REQ UNCOVERED ROWS (explicit list to resolve)

1. **PB-8 — five action modes** (read-only/draft/confirmed/approved-workflow/policy-automation): MUST on all five; only propose-only Action-Plan production is requirement-pinned; policy-automation explicitly deferred; draft/confirmed/approved-workflow unenumerated. **→ LBD-5.** (load-bearing)
2. **PB-7 SHOULDs** — index workflow commands/skills/subagents/hooks/manifests AND expose readiness/drift to the platform: not enumerated in any FR; "template availability ≠ readiness" MUST only implicit. **Question:** folded into FR-16 or dropped?
3. **PB-6 linking** — plan-task linkability (Linear/GH/sessions/branches/worktrees/PRs/commits) + "preserve manual linking before auto-sync": SHOULDs not pinned to a dedicated FR. **Question:** confirm folded into FR-15.
4. **PB-4 register distinction** — "distinguish authored plain/deep registers from generated summaries" (a MUST): not enumerated; only implicit via doc_type. **Question for human.**
5. **Standalone "minimal web/dev console"** swapped for the Tauri desktop app. **→ LBD-6.** (load-bearing)
6. **Embedded drawer UX (§11)** — drawer modes (Plan/Review/Decisions/Memory unflowed — D1-02), 7-chip scope selector, Answer UI, Action-Plan UI controls: deferred [P2], no REQ pins the drawer contract. **Question:** bind finalize to MAIN_PLATFORM_INTERFACE v0.2 rather than leaving requirement-orphaned.
7. **Non-trust Success Metrics** — memory-utility (déjà-vu hit rate, time-to-find) + platform-readiness (% answers with shared IDs, % sessions linked, % instances correctly classified): thinner/absent in EVALUATION_CRITERIA vs the trust metrics. **Question:** intentionally deferred or dropped?

Also confirm at finalize: **Provenance Packet full field list** is pinned (PB-10) and **action-request audit responsibility** split (PB-11) is intentionally platform-owned.

---

## 5. RECOMMENDED FINAL §-SECTION LIST + §2.5 DAG

### §-sections (open-ended §N, one per subsystem; append-only baseline — see LBD-17)
§1 Goals & non-goals · §2 System overview · **§2.5 Subsystem dependency DAG & parallelization seams** · §3 Locked decisions (pointer → DECISIONS) · §4 Domain model & invariants · §5 Data & state model (three stores; chunk / version-stamp / manifest / registry schemas; all state machines incl. EpisodeCard + blue-green) · **§6 LanceDB store & maintenance contract** (PH-1; split out — highest-risk day-one deliverable) · **§7 Ports & adapter contracts** (HostPort + 6 ports; freeze-before-fork home) · §8 Ingestion & indexing · §9 Retrieval & answering · **§10 Grounding, anchors & provenance** (north star; split out) · §11 Federation router & registry · §12 Sync & freshness (watcher+hooks, drift radar, blue-green re-embed) · §13 Embedded agent (LlamaIndex Workflow) · **§14 MCP server & trust boundary** (T-6/FR-13 invariants stand alone) · §15 CLI & desktop UI surfaces · §16 Providers (pluggable, version-stamped) · §17 Session memory & episode cards (opt-in) · §18 Security & trust boundaries (pointer → THREAT_MODEL + binding invariants) · §19 Observability & evals · §20 Packaging & distribution · §21 Setup, provisioning & lifecycle (idempotent/reversible host-config) · §22 Failure modes & recovery (full table, inline contracts) · §23 NexusOps integration seam (forward, P2) · §24 Build order & sequencing (critical path) · §N Cross-cutting concerns · §N+1 Open questions & spikes · **Spec Anchor Index** (every FR/NFR/PH → §) · **Appendix A** (every contract model → §; mark freeze-before-fork).

### §2.5 DAG
- **Import direction (one-way):** `entrypoints (cli / mcp / app / host-adapters) → agent → {retrieval, drift, federation} → grounding → index → ingest → {redactor, providers, ports, manifest/registry}`. **ports & redactor depend on nothing**; **observability is a leaf sink** every node emits to; **no upward or cross-sibling imports**. Model **redactor** (index-time + MCP-egress + cloud-egress) and **grounding** (retrieval + agent + drift + federation answer) as **fan-in hubs**, not pipeline stages.
- **Forced-serial spine (Track-0, single-track):** ports → manifest+chunk-schema → ingest (incl. redact) → index (embed/write/optimize/version) → retrieval → grounding → agent = the **D-18 first vertical slice**. No track forks until this reaches a queryable + grounded one-repo index.
- **Independent tracks (fork after spine + frozen contracts):** T-A federation router (reads N indexes read-only) · T-B sync/freshness + drift radar · T-C sessions/episode-cards · T-D MCP server · T-E Tauri desktop UI (behind frozen core public API) · T-F observability wiring (leaf, last) · T-G provider bake-offs (behind the provider ports, from day one). Plus a dashed **T-P2 NexusOpsHost** (forks behind frozen HostPort + published core API; never touches the spine). §19's ordering is a sequencing *preference* for these, not a dependency constraint.
- **Shared contracts to FREEZE before any post-spine track forks (Appendix A):** (1) LanceDB chunk schema · (2) `.project-brain/manifest.json` + global registry schema *(OQ-6 — fork blocker, freeze now)* · (3) HostPort interface · (4) EmbeddingProvider/Reranker/ContextStrategy/ModelProvider port signatures · (5) Anchor · (6) ProvenancePacket + EvidenceRef (1:1 to the 11-value EvidenceType / 22 IdKind) · (7) store-level version stamp `{model, dim, schema, sha}`. Add **redactor interface + fuzz corpus** and the **Anchor state machine** as freeze-before-fork for the MCP and drift tracks.
- **Single- vs multi-track:** author multi-track (correct dependency truth); under single-operator it reads as a serial sequencing hint. **→ confirm build mode (LBD-14).**

---

## 6. NICE-TO-HAVE / PROPOSED-EDITS

- First-run / empty-portfolio UX flow (D1-03 / COMP-5); name-and-defer P3 flows (Since-you-left, cross-project impact — D1-07); doc-completeness nudge sub-flow (D1-06); user-initiated provider/policy-change trigger flow for F9 (D1-05); scope-switch interaction flow (D1-08, question).
- Cross-cutting fail-closed rule for undefined state transitions (D2-09); CodeGraph connection-state note (D2-10).
- Status-tag normalization in DECISIONS (D-12/D-13/D-15 plain `[locked]` vs `[locked — owner]` — D7-4); PRD "service"/[OPEN] framing pass (D7-3); transport-primacy clarity for shell↔core link (D7-5, question).
- `.brainignore` format/precedence (D4-14); CodeGraph structural-tool call contract (D4-12); CodeGraph schema-version re-probe cadence (D5-7).
- Chunker fallback + dual-register parity tests (D9-10); CI Langfuse-dependency clarity (D9-11, question).
- Federation fan-out latency budget (D15-4); re-embed cost budget (D15-5); grounding-gate sync-vs-background latency (D15-8, question).
- Telemetry-consent UX (COMP-6); desktop a11y baseline (COMP-7); indexed-third-party-code licensing vs cloud egress (COMP-8); i18n/non-English scope note (COMP-9); portfolio disk-budget governance (COMP-10); FastMCP exact-minor pin + background-task auth-scope check (D6-6); cloud-reranker paid-API posture (D6-7, question); HostPort-from-day-one cost confirmation (D8-7); ResourceType 20-vs-21 forward-seam awareness (D7-6); Linux deploy/update re-derivation note (D10-9); deploy-specific CI gates (D10-10); desktop sidecar-lifecycle inset (D12-5).

---

**Bottom line:** the draft is architecturally coherent (the trust/grounding/maintenance spine, ownership of the three stores, and the integrated-mode security posture are strong and consistent with NexusOps ground truth). It is **not overbuilt** vs the agreed scope. The binding blockers are: (a) three contracts that exist only as names (MCP tools, ports, policy.yaml/manifest); (b) one ownership ambiguity that threatens the trust north star (freshness metadata); (c) three external-dependency facts that invalidate stated invariants (CodeGraph 1.x, Voyage opt-out, ZDR/Fable-5); (d) the redaction "zero-leak" reframe; (e) the two missing structural artifacts /tasks-gen requires (§2.5 DAG + Appendix A / Spec Anchor Index); and (f) the production-baseline operability gaps (schema migration, auto-update quiesce, 429/cost, deterministic test seams). Resolving LBD-1 through LBD-18 unblocks the binding ARCHITECTURE.md.