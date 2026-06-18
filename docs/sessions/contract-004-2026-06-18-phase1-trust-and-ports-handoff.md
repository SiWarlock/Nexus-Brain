# contract-004 — 2026-06-18 — Phase 1.3 (trust contracts) + 1.4 (11-port freeze) — orchestrator handoff + contract→spine fork obligations

> **End-of-1.4 cycle.** Orchestrator-side handoff (track: contract). The fresh orchestrator: read this + the decision log (`docs/lead-decisions-while-away.md`, D-A1–A14) + the impl session doc (`contract-003-*`) + `IMPLEMENTATION_PLAN.md` "Currently in progress", then `/orchestrate-start` and continue at **Phase 1.5**.
> **This doc doubles as the contract→spine handoff** — the §"FORK OBLIGATIONS" section is what the spine team inherits at the fork.

## What was built (this session: 1.3 + 1.4)

**Phase 1.3 — trust contracts (§10), 3 atomic ★ sub-slices, 36 tests:**
- **Anchor** (`5b50b5f`) — 11-field frozen; `AnchorState` StrEnum 5 values `{live,stale,moved,unknown,orphaned}` (membership snapshot; **`deleted` = record-lifecycle, NOT a state** — §5 line-90 reconciled); invalid-state rejected at parse; `target_symbol` optional; `confidence`∈[0,1]; `end≥start` validator; identity strip+min_length.
- **EvidenceRef** (`518da07`) — 4-field shape-only frozen `{type, label, resource_ref?, confidence?}`; **EvidenceType membership DEFERRED (D-A11)** — constrained-str alias now, no membership snapshot.
- **ProvenancePacket** (`77276e3`) — 10 fields incl. **`evidence: tuple[EvidenceRef]`** (additive Appendix-A:217 reconciliation, **D-A12**); `citations` = file:line tokens (NOT `list[Anchor]`); `low_confidence_links` NOT a field; nested parse-don't-trust + deep immutability.

**Phase 1.4 — all 11 ports frozen (interfaces + Fakes), 4 atomic sub-slices, → suite 174/174:**
- **HostPort** (`8aa6935`, ★SAFETY) — `capabilities/authorize/perform`; `HostCapability` closed 3-StrEnum; fail-closed authorize (`HostDenied`); **perform defense-in-depth re-validates capability∈caps** (forged `authorized` still denied); §14 static AST-scan tripwire seeded.
- **4 provider ports** (`e9d1e51`) — Embedding/Reranker/Context/Model behavioral Protocols + Fakes + result types (`RerankResult` `allow_inf_nan=False`, `Citation`, `GenerateResult`); `model_version` on EmbeddingProvider only.
- **CodeGraphPort** (`b1dafcc`) — `query(kind,sym)`; `CodeGraphQueryKind` 5-StrEnum + `cli_command` (search→`query`); schema-gate `≥5`; `CODEGRAPH_DIR` **positive allow-list** resolver (LESSON 10, 18-value bypass corpus); `CodeGraphSchemaError`.
- **EventSource/SecretStore/ObservabilitySink** (`05c3551`) — behavioral Protocols + Fakes; **SecretRef carries NO secret** (#3; `extra="forbid"` + no-leak); `resolve` fail-closed `SecretNotFoundError`; emit local-only never-phone-home.

## Decisions made (lead-adjudicated under owner-away authority — see decision log)
- **D-A11** EvidenceType/IdKind membership deferred to Phase-4 (external NexusOps `MAIN_PLATFORM_INTERFACE.md` v0.2; freeze shape, narrow additively).
- **D-A12** ProvenancePacket +`evidence[]` additive reconciliation (ER-map-mandated).
- **D-A13 / D-A14** — the two gated fork-crossing safety obligations (see FORK OBLIGATIONS).
- HostPort perform capability-recheck (defense-in-depth on the forgeable `authorized` stamp). CodeGraph spike-0.2 corrections baked. cassette record/replay re-sequenced to providers/eval. 3 additive Appendix-A port rows (Event/Secret/Obs).

## Decisions explicitly NOT made (deferred — owner/phase)
- D-A5/D-A6 (Redactor cloud-egress strictness + 95/5 threshold) → owner at Phase 2.3 — the 1.5 Redactor SIGNATURE freezes against both.
- D-A11 EvidenceType/IdKind canonical 11/22 → Phase-4 (owner supplies the NexusOps doc, or a flagged spine-time decision, BEFORE the post-spine fork).
- 0.5 notarization (Apple creds) → HITL (D-A2). D-A3 preflight.md edit → HITL (recommended-first owner action).

## LESSONS banked this session (§6–§11; full prose in `core/LESSONS.md`)
- **§6** named state-machine = StrEnum + membership snapshot; inline tags stay Literal; deferred/external enum freezes shape only.
- **§7** every §5/§10 identity string = `StringConstraints(strip_whitespace=True, min_length=1)`.
- **§8** composed frozen contract: `tuple[Child,...]` container + nested parse-don't-trust + deep immutability + dict→model coercion test.
- **§9** type-shaped chokepoint: authorizer-minted input + perform re-validation (forgeable stamp ≠ control).
- **§10** §14 ingress = positive allow-list, never deny-list (esp. when frozen). **← directly applies to 1.5 MCP ingress.**
- **§11** a safety contract excludes the dangerous field by shape + `extra="forbid"` (SecretRef no-secret; StoreVersionStamp no-SHA).

## ★ FORK OBLIGATIONS (contract→spine handoff — the spine team MUST honor these)
These cross the Phase-1 freeze→fork boundary. Both are tracked tasks + Acceptance gates in `IMPLEMENTATION_PLAN.md`:
1. **D-A13 — Task 2.S (Phase-2, ★SAFETY, gated Acceptance(2)):** the §14 INV-allowlist **FULL runtime proof** — every FS/git/session mutation routes via `HostPort.perform`; build the real `StandaloneHost`; extend the 1.4a static tripwire to session-state (`os.environ`) + harden the residual (module-alias/getattr). Lands with the first FS-mutator (2.4 manifest writer / 3.1 LanceDB writer). **Phase 2 does not close without it.**
2. **D-A14 — Phase 4.2 (★SAFETY, gated Acceptance(4)):** the CodeGraph CLI shell-out adapter is **argv-hardened** (`shell=False` + single fixed non-option argv per arg + `--` terminator + absolute-resolved dir) — the PRIMARY injection defense for the **query/symbol args** (un-allow-listable code identifiers; the 1.4c `CODEGRAPH_DIR` allow-list does NOT cover them). **Phase 4 does not close without a security-reviewer-verified injection test.**

Plus the Phase-deferred contract enrichments (additive, no re-freeze): EvidenceType/IdKind canonical membership (D-A11, Phase-4 before fork); Citations payload + ProvenancePacket `index_freshness` vocab + `file:line` token format (Phase-4); on-disk strict key-shape loader (Phase-2/3); SecretStore real-keychain-no-plaintext-on-self + log-scrub (Phase-2); redactor engine FLAG-1/2/3 + fuzz CI gate (Phase-2.3).

## BEFORE-FORK CHECKLIST (must clear before `/phase-exit 1`)
- [ ] **Task 1.5** — MCP tool contract · policy.yaml · Redactor interface (the last freeze-before-fork group). LESSON 10 allow-list on MCP ingress; policy fail-CLOSED; Redactor signature per spike-0.1 envelope (accommodates D-A5/D-A6 deferral).
- [ ] **Before-fork hardening sweep** (Carry-forward) — whitespace-strip retrofit of 1.2 §5 fields + shared `IdentityStr` consolidation (§7) + `list`→`tuple` for `ProvenancePacket`/`GenerateResult` collections (§8) + control-char/NUL + max_length cap.
- [ ] **Phase-0 spikes 0.3** (federation O-FED) + **0.4** (LanceDB bake-off) — non-blocking-for-1.5 but Acceptance(0) wants them before Phase-0/contract exit. (0.5 notarization HITL-deferred — D-A2.)
- [ ] **`/phase-exit 1`** — arch-drift audit (Appendix-A ↔ code; the snapshots are the proof), spec-coverage, verify-only push; carries D-A13/D-A14 into the spine handoff. Then merge `track/contract` → integration `main`.

## Round seal
- Worktree `track/contract`: slice commits `5b50b5f`…`05c3551` (impl) + this round's orchestrator doc commit (core/CLAUDE.md + core/LESSONS.md + 7 briefs + this handoff). Impl session doc `contract-003-*` (impl-committed).
- Integration `main`: `IMPLEMENTATION_PLAN.md` (1.3/1.4 ticks, Task 2.S/D-A13 + Phase-4.2/D-A14, Log, Carry-forward triage, Currently-in-progress) + `ARCHITECTURE.md` (Appendix-A:216–220 + 3 additive port rows + §5 `deleted`).
- Suite 174/174; mypy --strict + ruff clean. Not pushed beyond this round's push.
