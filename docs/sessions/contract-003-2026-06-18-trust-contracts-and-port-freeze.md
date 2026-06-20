# contract-003 — 2026-06-18 — Phase 1.3 trust contracts + Phase 1.4 the 11-port freeze

> Implementer-side session doc (track: contract). **Predecessor:** `contract-002-2026-06-17-phase1-determinism-and-data-contracts.md`. **Successor:** [`contract-005-2026-06-20-phase1.5-boundary-contracts-and-1.6-hardening-sweep.md`](contract-005-2026-06-20-phase1.5-boundary-contracts-and-1.6-hardening-sweep.md) (Task 1.5 boundary contracts + the 1.6 before-fork sweep).

## Why this session existed

END-of-1.2 cycle handed a fresh team the Phase 1.3→1.5 runway. This session drove **Phase 1.3 (trust contracts)** and **all of Phase 1.4 (the 11-port freeze)** to completion via the `/tdd` engine — 7 slices, 7 commits, one per slice. Phase 1.4 completing means the fork gate's port half is frozen; 1.5 (boundary contracts) + the sweep + spikes remain before `/phase-exit 1`.

## What was built

**Suite: 174/174 green · ruff + ruff format + `mypy .` --strict clean (39 files) · -W error clean.** All freeze-before-fork; no production wiring this phase (by design).

### Files created
- `core/model/anchor.py` (1.3a, `5b50b5f`) — frozen `Anchor` (11-field §10 grounding primitive) + 5-value `AnchorState` StrEnum {live,stale,moved,unknown,orphaned}.
- `core/model/evidence.py` (1.3c, `518da07`) — frozen `EvidenceRef` (4-field §10 evidence record) + the DEFERRED `EvidenceType` constrained-str alias (D-A11 Option B).
- `core/model/provenance.py` (1.3b, `77276e3`) — frozen `ProvenancePacket` (10-field §10 grounding record), composes `list[EvidenceRef]`. **Completes Phase 1.3.**
- `core/ports/host.py` (1.4a, `8aa6935`) — **SAFETY-CRITICAL** `HostPort` Protocol + 3-value `HostCapability` allowlist + `HostIntent`/`HostAction`/`HostResult` + `HostDenied` (the sole mutation chokepoint, Key safety rule #4).
- `core/ports/providers.py` (1.4b, `e9d1e51`) — `EmbeddingProvider`/`Reranker`/`ContextStrategy`/`ModelProvider` Protocols + `RerankResult`/`Citation`/`GenerateResult`.
- `core/ports/codegraph.py` (1.4c, `b1dafcc`) — `CodeGraphPort` + `CodeGraphQueryKind`(+`cli_command`) + `CodeGraphResult` + `resolve_codegraph_dir` (§14 allow-list) + `assert_schema_compatible` + `CodeGraphSchemaError` (bakes spike-0.2/D-A4).
- `core/ports/events.py` · `secrets.py` · `observability.py` (1.4d, `05c3551`) — `EventSource`/`SecretStore`/`ObservabilitySink` Protocols + `Event`/`SecretRef`/`ObsEvent` + `SecretNotFoundError`. **Completes Phase 1.4 (11 ports).**
- `core/tests/model/{test_anchor,test_evidence,test_provenance}.py` + `core/tests/ports/{test_host,test_providers,test_codegraph,test_events,test_secrets,test_observability}.py` — 15+13+13+14+11+12+5+6+3 = **92 new tests** this session.

### Files modified
- `core/testing/fakes.py` — added `FakeHost`, `FakeEmbeddingProvider`/`FakeReranker`/`FakeContextStrategy`/`FakeModelProvider`, `FakeCodeGraph`, `FakeEventSource`/`FakeSecretStore`/`FakeObservabilitySink` (faithful deterministic doubles, LESSON 1).

## Decisions made
- **§10 trust contracts (1.3):** Anchor `state` is a closed 5-value `StrEnum`; `deleted` is record-lifecycle, NOT a state value (§5↔Appendix-A reconciliation). EvidenceRef composes additively into ProvenancePacket's `evidence: list[EvidenceRef]` (Appendix-A:217 reconciliation, D-A7). `citations` = `list[str]` file:line tokens, NOT `list[Anchor]`.
- **D-A11 Option B (EvidenceType):** freeze the EvidenceRef *shape*; defer the externally-owned `EvidenceType` membership to Phase-4 (constrained-str alias now, NO membership snapshot, additive-narrowing-safe).
- **HostPort type-shaped chokepoint:** `authorize(intent)->HostAction` + `HostAction.authorized: bool = False` (fail-closed stamp); `perform` re-validates capability ∈ allowlist AND authorized (defense-in-depth, never trusts the forgeable stamp). The **§14 INV-allowlist AST tripwire** was seeded (lead safety ask): scans every `core/` module for FS/git mutation primitives outside `ports/host.py` — passes now, guards forward; hardened in-slice (Path.open both arg positions, from-import mutators, alias-proof subprocess, dot-dir prune) against 12 adversarial forms.
- **CodeGraphPort spike-0.2/D-A4:** schema gate `>=5` (not `=1`); `search→query` CLI mapping; `resolve_codegraph_dir` is a §14 positive-charset **ALLOW-LIST** (hardened in-slice from a deny-list after security review — a frozen seam must not bake weak semantics).
- **SecretStore Key safety rule #3:** `SecretRef{service, account}` carries NO secret material (`extra="forbid"`); plaintext only transiently via `resolve` (fail-closed `SecretNotFoundError`). ObservabilitySink `emit` purely local (never-phone-home, D-22).
- **LESSON-8 tuple convention:** from 1.4c onward, frozen-contract collection fields use `tuple[Child, ...]` (CodeGraphResult.symbols, ObsEvent.attributes). The 1.2/1.3 `list[...]` fields are queued for the before-fork hardening sweep (orchestrator-banked).

## Decisions explicitly NOT made (deferred)
- **Real adapters** (StandaloneHost / Ollama·Voyage·Anthropic / CodeGraph CLI shell-out / keychain / OTel sink / git-hook watcher) → Phase-2/3 + eval (interfaces + Fakes frozen now).
- **The full §14 INV-allowlist caller-routing proof** (every mutation-capable module routes through `perform`) → Phase-2 (Task 2.S / D-A13), once callers exist; the tripwire seeds it now.
- **Rich Citations payload** (file:line + recorded_sha) → Phase-4 §10 grounding (Q6, additive).
- **EvidenceType canonical 11 / IdKind 22** → Phase-4, from the owner's NexusOps doc (D-A11).
- **Cassette record/replay** → re-sequenced to the providers track / eval harness (Q7, lead-noted).
- **list→tuple retrofit + control-char/NUL + max_length on `_StrippedStr`** → the before-fork hardening sweep.

## TDD compliance
**CLEAN — no violations.** All 7 slices ran strict `/tdd`: RED written first, confirmed failing for the right reason (ModuleNotFoundError/attribute), Step-2.5 review (APPROVED/ADD), GREEN minimum, full suite, Step-7.5 reachability, Step-8 gates + every-slice security + code-quality reviewers, Step-9 categorized routing, Step-10 commit. The safety-critical HostPort got its own commit (never bundled). Multiple reviewer findings (incl. 2 security `[high]`s on the §14 tripwire + the CODEGRAPH_DIR allow-list) were verified and hardened in-slice; several reviewer claims were verified-and-rejected with evidence (e.g. the `_CORE_ROOT` "scans nothing" claim, empirically disproven).

## Reachability
Every contract is **freeze-before-fork — intentionally NOT wired this phase** (confirmed at each slice's Step-7.5; first consumers are Phase-2/3/4). Importable as `model.*` / `ports.*`; the Fakes are the seam every track injects. The one active guard is the §14 AST tripwire (green). **No tested-but-unwired gaps** — every unwired contract has a documented future consumer (listed in Open follow-ups). A later slice removed no prior wiring.

## Open follow-ups (Step-9 categorized — already routed hot to the orchestrator)
- **Cross-doc (orchestrator writes hot + at `/orchestrate-end`):** 7 new `core/CLAUDE.md` rows + Appendix-A reconciliations (Anchor:216 · EvidenceRef:217 D-A11-annotated · ProvenancePacket:217 +evidence[] · HostPort:218 · Providers:219 · CodeGraphPort:220 spike-0.2 · 3 NEW additive rows for Event/Secret/Obs, D-A7). All flagged at Step 9; orchestrator confirmed routing (working tree shows `core/CLAUDE.md` + `core/LESSONS.md` as its uncommitted hot edits).
- **LESSONS banked by orchestrator this session:** 6 (deferred-enum), 7 (strip-identity), 8 (composed-contract + tuple refinement), 9 (type-shaped chokepoint), 10 (§14 allow-list ingress), 11 (safety-contract excludes the dangerous field by shape).
- **Phase-2 TODOs:** real StandaloneHost + per-capability perform handlers · §14 caller-routing proof + tripwire module-alias/getattr hardening (Task 2.S/D-A13) · keychain adapter (no plaintext on `self`) + log-scrub · OTel sink (off-by-default) · EventSource watcher · CodeGraph CLI adapter (argv `--`/`shell=False` hardening, version fail-fast, tree-sitter fallback).
- **Phase-4 TODOs:** rich Citations payload · EvidenceType-11/IdKind-22 pin · `low_confidence_links` grounding-gate representation · ObsEvent attribute bounds + control-char sanitization.
- **Before-fork hardening sweep:** consolidate `_StrippedStr`/`IdentityStr` to one shared alias · list→tuple retrofit on the 1.2/1.3 collection fields · control-char/NUL + max_length on `_StrippedStr`.

## How to use what was built
Inject the `Fake*` doubles from `core/testing/fakes.py` (all DI-substitutable, deterministic). Construct the frozen models with caller-injected ids/timestamps (via the 1.1 `Clock`/`IdGen` seams). The §14 tripwire (`test_inv_allowlist_no_mutation_outside_hostport`) is the live forward-guard: any Phase-2 module that mutates the FS outside `HostPort.perform` trips it.
