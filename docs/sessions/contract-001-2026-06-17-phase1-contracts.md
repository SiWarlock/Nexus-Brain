# contract-001 — 2026-06-17 — Phase 0 spikes + Phase 1.1/1.2 contract freeze

> Orchestrator-side handoff doc (track: contract). End-of-1.2 cycle. Next orchestrator session: read this + `/orchestrate-start`, then continue Phase 1 (1.3 → 1.4 → 1.5).

## What was built (this session)

**Phase 0 — spikes (de-risk the freeze):**
- **0.1** redaction fuzz harness + envelope → `ci/eval/redaction_fuzz/` + `docs/audits/redaction-envelope.md` (`f2b5f6c`). Verdict: recall-floor ≥95% / FP ≤5% (git-SHA 0% FP hard); 3 §18-accepted-residuals confirmed, zero policy deviation. **De-risks 1.5 Redactor.**
- **0.2** CodeGraph 1.0.1 column-diff + CLI smoke → `ci/probes/codegraph_coldiff.md` (`f2b5f6c`). Verdict: pin `=1.0.1` SAFE; **plan corrections for 1.4**: `schema_versions MAX>=5` (NOT `=1`), `search` kind → CLI `codegraph query`, system codegraph v0.9.7 lacks explore/node (version-check+fail-fast or route via 1.0.1 MCP daemon).
- 0.3 (federation), 0.4 (LanceDB bake-off) NOT run (off the Phase-1-freeze critical path; non-blocking). 0.5 (notarization) HITL-deferred (needs Apple creds; D-A2). **All three are open Phase-0 items** (Acceptance(0) wants all 0.X — they land before the Phase-0/contract-track phase-exit; 0.5 is an owner-gated deferral).

**Phase 1.1 — determinism seams (`61853b3`):** `Clock` + `Seed`/`IdGen` ports (typing.Protocol + real adapter + Fake double in `core/testing/fakes.py`) + bootstrapped the `core/` package (uv · ruff · mypy --strict · pytest; flat layout, `mypy .`). 16 tests.

**Phase 1.2 — §5 data + migration contracts (COMPLETE):** all frozen Pydantic v2, `frozen=True`+`extra="forbid"`, snapshot-pinned, seam-fields caller-injected:
- 1.2a **Chunk** (19-field LanceDB row) — `269b68e`.
- 1.2b **StoreVersionStamp** (5-field §5 source-of-truth; NO SHA field — version tag is canonical) — `4fab4ab`.
- 1.2c1 **ProjectManifest + ManifestArtifact** (12+5; DERIVED; camelCase on-disk keys; lenient-read/strict-write) — `07c3cba`.
- 1.2c2 **Registry + RegistryEntry** (DERIVED routing index; two distinct schema_versions) — `665dd8b`.
- 1.2d **migration engine** (pure forward-only `schemaVersion` runner + downgrade-refuse; NO file I/O, host owns I/O+backup) — `bb000b1`.

Suite: **82 tests green**, mypy --strict clean, -W error clean. Branch `track/contract` (NOT pushed beyond this round's push).

## Decisions made (key adjudications)
- **§5 source-of-truth (load-bearing):** the stamp omits the SHA (git-SHA = LanceDB version tag = sole canonical SHA home); DATA_MODEL.md's draft `ingested_from_sha`-in-stamp superseded. Logged D-A8-equiv via lead. The chunk's per-chunk `ingested_from_sha` is legitimate finer-grained provenance (kept).
- **Field-set reconciliations** (Appendix-A was incomplete vs DATA_MODEL): Chunk 16→19, manifest 9→12, registry entry 5→6 (+policy). All additive, reconciled in `ARCHITECTURE.md` Appendix A (integration, main: `aa1f32d`/`4b6e742`/`c02e32b`). Logged D-A7.
- **Serialized-file models** pin TWO snapshots (Python names + by-alias on-disk keys); `validate_by_name`/`validate_by_alias` (NOT deprecated `populate_by_name` → breaks -W error). LESSON §4.
- **policy fail-open closed:** `RegistryEntry.policy` min_length=1 (privacy marker; empty = fail-open). Fail-CLOSED semantics (absent/unrecognized → most-restrictive) handed off to the **1.5 policy model**.
- **migration engine is PURE** (§4/§7): no FS I/O (import-purity-pinned); backup-before-migrate + read/write is HOST-owned (HostPort, Phase 2+).
- **spec-lint numeric-ID gate fixed** (`392ed4f`): the brief Task-ID regex required a letter prefix; made it optional so `1.1`-style IDs extract. (Scaffolding-template bug; Carry-forward for `/scaffold-upgrade`.)

## Lessons banked (`core/LESSONS.md`)
- §1 Ports = Protocol + real + faithful Fake double; inject, never construct inline.
- §2 Minted ids are opaque (kind not recoverable).
- §3 Contract-model field names can shadow BaseModel/ABCMeta (→ `Field(...)` + omit-each test + scoped warning-suppress). _(register-shadow HIGH bug, 1.2a.)_
- §4 Serialized-file models pin two snapshots; `validate_by_name`/`validate_by_alias`; lenient-read/strict-write.
- §5 Never suppress a quality-gate's output; run the canonical `/preflight`. _(gate-suppression shipped 3 E501s undetected; root enabler = D-A3.)_

## Open follow-ups / Carry-forward (next session MUST fold)
- **1.4 CodeGraphPort:** use spike-0.2 corrections (schema_versions `>=5`, `search`→`codegraph query`, v0.9.7 fail-fast/MCP-route). _(see `ci/probes/codegraph_coldiff.md`)_
- **1.5 Redactor:** use spike-0.1 envelope (sink enum 3-value, accepted-residual contract, recall≥95%/FP≤5%, behavioral invariants). **FLAG-4** (cloud_egress stricter?) + the **95/5 threshold** are OWNER-deferred to Phase 2.3/policy.yaml (D-A5/D-A6) — freeze the 1.5 signature against the deferred-strictness framing (accommodates both). _(see `docs/audits/redaction-envelope.md`)_
- **1.5 policy model:** fail-CLOSED semantics (absent/empty/unrecognized policy → most-restrictive local-only).
- **Identity-field whitespace-strip uniform sweep — MUST-do-before-fork** (retrofit 1.2b/1.2c1/1.2c2 + bake into 1.3 from start; `StringConstraints(strip_whitespace=True, min_length=1)`).
- **Manifest/registry on-disk strict key-shape rejection → owned by a future startup-reconcile loader** (the frozen models are lenient readers by design).
- **D-A3 (UPGRADED to recommended-FIRST owner action, still HITL-deferred):** `.claude/commands/preflight.md` Step-4 `mypy core`→`mypy .` — agent-edit blocked; root enabler of hand-rolled gates. core implementers override Step-4 with `mypy .`.
- **scaffolding-template:** spec-lint numeric-ID fix (`392ed4f`) → carry upstream at `/scaffold-upgrade`.

## Next session target
**Phase 1.3 — trust contracts:** `Anchor` (state enum incl. recovery + `orphaned`) · `ProvenancePacket` · `EvidenceRef` (→ 11-EvidenceType / 22 IdKind) → `core/model/{anchor,provenance,evidence}.py`. §2.5-seam → schema-snapshot tests `spec(§10)`. Depends on 1.1. Then **1.4** (ports incl. HostPort + CodeGraphPort) → **1.5** (MCP contract · policy.yaml · Redactor iface). 1.3 mirrors the §5-model conventions (frozen/extra-forbid/Field/omit-each/snapshot; LESSONS §1–§5). After 1.5 + the before-fork sweeps + Phase-0 0.3/0.4(/0.5) → `/phase-exit 1` = the fork gate.
