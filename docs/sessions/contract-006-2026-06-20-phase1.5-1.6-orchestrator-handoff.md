# contract-006 — 2026-06-20 — Phase 1.5 (boundary contracts) + 1.6 (before-fork hardening sweep) — orchestrator handoff

> **End-of-1.6 cycle (context-triggered).** Orchestrator-side round doc + contract→fresh-team handoff (track: contract). The fresh orchestrator: read this + the decision log (`docs/lead-decisions-while-away.md`, D-A1–A16) + the impl session doc (`contract-005-*`) + `IMPLEMENTATION_PLAN.md` "Currently in progress" (root/main canonical), then `/orchestrate-start` and continue at **Phase-0 spikes 0.3/0.4 → `/phase-exit 1`**.
> **Predecessor:** `contract-004` (end-of-1.4). **Successor:** `contract-008` (Phase-0 close-out + fork-gate orchestration).

## What landed this round (Phase 1.5 + 1.6 — 7 slices)

**Phase 1.5 — boundary contracts FROZEN (the last freeze-before-fork group, §14/§16/§18):**
- **1.5a Redactor interface** (`343b6fb`, §18) — `Sink` StrEnum {persist,mcp_egress,cloud_egress} + `@runtime_checkable Redactor` Protocol + `FakeRedactor`; behavioral-invariant freeze (idempotent / never-raises / git-SHA passthrough / pure); envelope documented (SSoT = spike `harness.py`), enforced at 2.3. **LESSON 12.**
- **1.5b policy.yaml** (`a9df580`, §16) — `Privacy` StrEnum {local,cloud} + frozen `ProjectPolicy` (7 fields incl. `schema_version`) + 4 sub-models; **fail-CLOSED** defaults; fail-soft is the loader's (Phase 2/3). **LESSON 13.**
- **1.5c1 MCP ingress** (`e65b9e3`, §14) — `RetrievalScope` + 5 param models; `get_file` ASCII positive allow-list + 17-entry bypass corpus (LESSON 10); bounded query/top_k. **LESSON 14.**
- **1.5c2 MCP results** (`959d5d9`, §14/§10) — `McpResultItem`/`McpResult`(composes ProvenancePacket)/`PolicyDenied` marker/`McpToolResult` union + `MAX_RESPONSE_ITEMS`. **LESSON 15.**

**Phase 1.6 — before-fork hardening sweep COMPLETE (a real `### 1.6` task, added this round):**
- **1.6a identity consolidation + hardening** (`0520304`) — 11 dup aliases → ONE cross-cutting `core/_types.py` `IdentityStr` (strip + min_length + **reject Unicode control/format/bidi/zero-width Cc/Cf/Zl/Zp** + max_length 1024) + `TextStr` (content); closed the `chunk.py` **bare-str zero-validation gap** + the §5 stamp/manifest/registry strip gap. **LESSON 16.** (Owner-approved unicode char-policy — see D-A16.)
- **1.6b list→tuple** (`ec71d48`) — ProvenancePacket's 7 collections + GenerateResult.citations + manifest.artifacts → tuple; closed the 1.5c2 catch (composed `McpResult.provenance.evidence` now deeply immutable). **LESSON 8** applied.
- **1.6c StrictBool** (`de63ead`) — all 7 frozen safety/security/lifecycle/output bools → StrictBool (policy ×3 opt-ins, HostAction.authorized, HostResult.ok, chunk.tombstone, McpResult.truncated); `PolicyDenied.denied` stays `Literal[True]` (deny-strengthening). **LESSON 17.** (Owner-approved — D-A15.)

**Suite 174 → 232 (+58); mypy --strict + ruff + format clean (47 files) throughout. LESSONS 12–17 banked. Impl session doc: `contract-005` (`356a505`).**

## Decisions (logged in `docs/lead-decisions-while-away.md`)
- **D-A15 — StrictBool uniform** for frozen safety/security/lifecycle/output bools (OWNER-APPROVED 2026-06-18). Exemption: deny-strengthening `Literal[True]` markers. → LESSON 17.
- **D-A16 — IdentityStr Unicode char-policy** (OWNER-APPROVED 2026-06-20): frozen identity fields reject Unicode control/format/bidi/zero-width (Cc/Cf/Zl/Zp), allow unicode letters; content (TextStr) stays permissive; Trojan-Source CONTENT sanitization deferred to Phase-2 redactor. Surfaced as a medium before-fork finding (1.6a); owner-confirmed (the load-bearing-cross-track-contract + security-finding class). → LESSON 16.
- **Additive Appendix-A reconciliations** (D-A7 pattern, orchestrator-adjudicated): policy.yaml row +`schema_version`; MCP tool contract row += result envelope + PolicyDenied marker + ASCII ingress allow-list + the 3 bound constants. _(Reconcile the Appendix-A row prose at the next /orchestrate-end or /phase-exit — additive, no invariant change.)_

## ★ Before-fork remaining (the fresh team's stretch → the fork gate)
1. **Phase-0 spike 0.3** (O-FED — federation cross-repo resolution) — `ci/probes/federation_spike.md`.
2. **Phase-0 spike 0.4** (O-LANCE-BAKEOFF — maintenance-contract invisibility) — `ci/bench/lancedb_maintenance/`.
   _(0.5 notarization = HITL-deferred, D-A2.)_
3. **`/phase-exit 1`** — arch-drift audit (Appendix-A ↔ code — the schema snapshots are the proof), spec-coverage (`scripts/spec-lint.sh tests 1`), dependency audit, verify-only push; **carries the D-A13 (Task 2.S §14 runtime proof) + D-A14 (Task 4.2 CodeGraph argv-hardening) fork obligations into the contract→spine handoff.**
4. **Merge `track/contract` → integration `main`** = the **fork gate** (spine + providers can then spin up).

## ★ FORK OBLIGATIONS (unchanged — still owed to the spine team)
- **D-A13 / Task 2.S** (Phase-2, ★SAFETY): the §14 INV-allowlist FULL runtime proof + real `StandaloneHost` (1.4a seeded only the static AST tripwire).
- **D-A14 / Task 4.2** (Phase-4, ★SAFETY): CodeGraph CLI shell-out argv-hardening (the PRIMARY injection defense for un-allow-listable query/symbol args).

## Deferred-to-phase (carry-forward; NOT next-slice)
- **Phase 2.3** Redactor engine + fuzz CI gate (FLAG-1/2/3); **Phase 2** Trojan-Source/bidi CONTENT sanitization (flag/strip at ingest — deferred from 1.6a TextStr, LESSON 14); SecretStore real-keychain.
- **Phase 3.1** `chunk.vector` list→tuple (LanceDB `Vector(dim)`/`LanceModel` owns its repr — deferred from 1.6b).
- **Phase 4.2/8.2** `get_file` runtime canonicalize-against-resolved-root containment (on the realpath; shape layer admits non-canonical + dotfile forms by design); file_line/citations are untrusted producer tokens → grounding gate (4.3) + egress (8.2) validate format + anchor-liveness.
- **Phase 8 §14-ingress-hardening**: `_GetFilePath` has no max_length cap (vs `_BoundedQuery`=4096); the mcp query/`_BoundedQuery` lacks the unicode-control rejection IdentityStr now has.
- **Phase 4 / spine** EvidenceType/IdKind canonical membership (D-A11); Citations payload + ProvenancePacket `index_freshness` vocab.
- **Residual:** `registry.entries` (dict) has no clean frozen form (security-confirmed acceptable; not a grounding record).
- **Doc-refinement (next /orchestrate-end or /phase-exit):** the `core/CLAUDE.md` `ProvenancePacket` cross-doc row still says `list[...]` (now tuple — 1.6b); add "StrictBool" notes to the policy/host/chunk bool rows; the Appendix-A policy.yaml/MCP reconciliations above. All additive doc-accuracy; the /phase-exit arch-drift audit will catch any drift.

## Round seal (TWO trees)
- **`track/contract`** (this worktree): slice commits `343b6fb`…`de63ead` (impl) + `contract-005` impl doc (`356a505`) + THIS round's orchestrator commit (core/CLAUDE.md cross-doc rows + LESSONS 12–17 + `core/_types.py` module-layout + 7 briefs `contract-014..020` + this doc). Pushed.
- **integration `main`** (root): `IMPLEMENTATION_PLAN.md` (1.5/1.6 ticks, ### 1.6 task, Currently-in-progress, Log, Carry-forward triage, Decisions D-A15/16) + `docs/lead-decisions-while-away.md` (D-A15/16). _(NOTE: the worktree `IMPLEMENTATION_PLAN.md` is the stale original — only its `### 1.6` heading was added for spec-lint; the canonical living-state is root/main.)_

## How to resume (fresh team)
1. `/orchestrate-start` (reads root/main `IMPLEMENTATION_PLAN.md` "Currently in progress" + this doc + the decision log).
2. Author Phase-0 spike 0.3 / 0.4 briefs (these are investigation spikes, like 0.1/0.2 — see `docs/audits/redaction-envelope.md` + `ci/probes/codegraph_coldiff.md` for the spike-doc pattern).
3. Run them → `/phase-exit 1` → merge = the fork gate.
