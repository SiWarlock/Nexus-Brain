# contract-005 — 2026-06-20 — Phase 1.5 boundary contracts + the 1.6 before-fork hardening sweep

- **Phase:** 1 (Shared contracts & ports freeze — the bottleneck). Tasks **1.5** (a/b/c1/c2) + **1.6** (a/b/c).
- **Track:** contract (worktree `project-brain-contract`, branch `track/contract`).
- **Predecessor session:** [contract-004 (handoff — end-of-1.4 cycle)](contract-004-2026-06-18-phase1-trust-and-ports-handoff.md) · prior impl session [contract-003](contract-003-2026-06-18-trust-contracts-and-port-freeze.md)
- **Successor session:** _(next implementer session — fresh full-runway team for the fork-gate stretch: spikes 0.3/0.4 → /phase-exit 1)_
- **Cycle close-out:** end of the 1.6-complete boundary (context auto-cycle, lead-approved + owner-blessed).

## Why this session existed

Resumed Phase 1 after Tasks 1.1–1.4 froze (determinism seams, data contracts, trust contracts, the 11 ports). Two jobs remained before the Phase-1 fork gate:
1. **Task 1.5** — the last freeze-before-fork boundary contracts: the §18 Redactor interface, the §16 `policy.yaml` schema, and the §14 MCP tool contract (ingress + results).
2. **Task 1.6** — the before-fork hardening sweep: consolidate/harden identity strings, deep-freeze frozen collections, and StrictBool the safety booleans — so a loose contract doesn't propagate to every track post-fork (tightening a frozen cross-track contract after the fork is breaking).

## What was built

7 slices, each its own commit (RED→GREEN→reviewers→commit). Suite **174 → 232** (+58).

### Files created
- `core/model/redactor_iface.py` — `Sink` StrEnum {persist, mcp_egress, cloud_egress} + `@runtime_checkable Redactor` Protocol `redact(payload, sink) -> str` + accepted-residual/envelope docstring (1.5a).
- `core/model/policy.py` — `Privacy` StrEnum + frozen `ProjectPolicy` (7 fail-CLOSED sections) + 4 sub-models (1.5b).
- `core/model/mcp_contract.py` — `RetrievalScope` + 5 param models + `get_file` ASCII allow-list (1.5c1); + `McpResultItem`/`McpResult`/`PolicyDenied`/`McpToolResult` + `MAX_RESPONSE_ITEMS` (1.5c2).
- `core/_types.py` — the cross-cutting hardened `IdentityStr`/`TextStr` aliases + length constants (1.6a).
- Tests: `test_redactor_iface.py`, `test_policy.py`, `test_mcp_contract.py`, `test_types.py`.
- `FakeRedactor` added to `core/testing/fakes.py` (1.5a).

### Files modified
- **1.6a** retrofit: 9 model + 6 ports files (`anchor/evidence/provenance/policy/mcp_contract/chunk/stamp/manifest/registry` + `codegraph/host/events/observability/secrets/providers`) — 11 duplicated `_StrippedStr`/`IdentityStr` aliases → the one `core/_types.py` alias; closed the §5 chunk bare-`str` gap; content fields → `TextStr`.
- **1.6b** list→tuple: `provenance.py` (7 collections), `manifest.py` (artifacts), `providers.py` (GenerateResult.citations); `fakes.py` builds `citations=tuple(...)`; `chunk.py`/`registry.py` deferral notes.
- **1.6c** StrictBool: `policy.py` (expose/visible/consent), `host.py` (HostAction.authorized + HostResult.ok), `chunk.py` (tombstone), `mcp_contract.py` (truncated).

## Decisions made (with rationale)

- **Redactor = behavioral Protocol, no recall claim baked in** (1.5a) — the engine + its recall/FP envelope land at Phase 2.3; the interface only freezes the signature + behavioral invariants (idempotent / never-raises / git-SHA passthrough / pure). D-A5/D-A6 (per-sink strictness, 95/5 threshold) owner-deferred via the sink-parameterized signature.
- **policy.yaml fail-CLOSED** (1.5b) — every section optional with a most-restrictive default (`privacy=local`, opt-ins off); the schema is a strict parser (parse-don't-trust), the fail-SOFT "malformed → most-restrictive" fallback is the Phase-2/3 loader. snake_case keys (user-edited YAML); provider catalog Phase-10-deferred (D-A11).
- **`get_file` path = ASCII positive allow-list** (1.5c1, orchestrator TWEAK) — strictest allow-list = smallest attack surface; non-ASCII deliberately rejected at the frozen boundary (widen additively in Phase 8 with NFC-normalize). Runtime canonicalize-against-root containment deferred to Phase 8.2.
- **PolicyDenied = typed returned marker, not an exception** (1.5c2) — `denied: Literal[True]`; `McpToolResult = McpResult | PolicyDenied` with `extra="forbid"` on both arms so neither smuggles the other's keys. `MAX_RESPONSE_ITEMS` structurally enforced (over-bound raises; Phase-8.2 truncates-then-constructs).
- **IdentityStr rejects the full Unicode Cc/Cf/Zl/Zp set** (1.6a, owner-approved) — escalated the ASCII-only-scope security Finding; owner blessed extending identity hardening to reject bidi/zero-width/BOM/C1/separators while keeping legitimate unicode letters. TextStr stays content-permissive (adds C1/NEL only); Trojan-Source *content* sanitization deferred to the Phase-2 redactor.
- **list→tuple for frozen collections** (1.6b) — closes the 1.5c2 catch end-to-end (composed `McpResult.provenance.evidence` now deeply immutable). chunk.vector deferred to Phase 3.1; registry.entries (dict) a documented residual.
- **StrictBool for all frozen-contract bools** (1.6c, owner-approved) — the rule: every frozen-contract bool is StrictBool except deny-strengthening `Literal` markers (`PolicyDenied.denied` exempt). Audited inventory surfaced `HostResult.ok` beyond the brief's named set → included for uniformity.

## Decisions explicitly NOT made (deferred)

- Redactor engine + its CI fuzz gate, per-sink strictness, 95/5 threshold → Phase 2.3 (owner: D-A5/D-A6).
- Provider catalog + privacy↔provider consistency validator → Phase 10 (D-A11).
- get_file runtime canonicalize-against-real-root containment + registry-scope authz + egress redaction + loopback transport → Phase 8.2; non-ASCII path widening → Phase 8 additive.
- `chunk.vector` list→tuple → Phase 3.1 (LanceDB Vector binding owns its repr).
- `registry.entries` dict deep-immutability → residual (no clean frozen-dict; revisit if a hazard).
- Trojan-Source bidi/format CONTENT sanitization in chunk.text → Phase-2 ingest/redactor.
- `_GetFilePath` max_length cap + query control-char rejection → a Phase-8 §14 ingress-hardening pass.

## TDD compliance

**Clean — no violations.** All 7 slices followed strict `/tdd`: test authored at Step 2, Step-2.5 orchestrator review, **RED confirmed at Step 3 (for the right reason)** before any implementation, GREEN at Step 4/5, full suite at Step 7, reviewers at Step 8, commit at Step 10. The 1.6a unicode extension (post-owner-TWEAK) was re-driven RED→GREEN + security-reviewer re-confirmed before commit.

## Cross-doc invariant audit (multi-track → memory check)

Every model field change this session was flagged at Step 9 and receipt-confirmed by the orchestrator (its hot-routed `core/CLAUDE.md` + `core/LESSONS.md` edits are present in the working tree):
- **1.5a/b/c1/c2** — NEW contracts (Redactor/Sink, Privacy/ProjectPolicy, RetrievalScope+5 params, McpResult/Item/PolicyDenied). All flagged; the cross-doc rows + Appendix-A reconciliations are orchestrator-owned (written hot or at `/orchestrate-end`).
- **1.6a/b/c** — NO field add/remove/rename (constraint-tightening / container-type / StrictBool — all wire-identical to the prior shape). Flagged "none structural" each Step 9; the only doc note is the `core/_types.py` module-layout addition (1.6a). All spec(§5/§7/§10/§14/§16/§18) field-name + on-disk-key + JSON snapshots stayed green — that staying-green IS the regression guard.

No discipline violation.

## Reachability

All Phase-1 work is frozen contracts/interfaces with **no Phase-1 production caller by design** (like the 1.4 ports) — reachability = the schema-snapshot + behavioral tests. Stated at each Step 7.5; wiring tracked as Future TODOs:
- Redactor → injected at persist (Phase 2), hydration egress (4.2), MCP egress (8).
- policy.yaml → add writes it (2.4); ingest reads privacy+brainignore (2); federation (6); MCP boundary (8); sessions (9); providers (10).
- MCP contract → FastMCP server builds tools + returns McpToolResult (8.1); boundary enforces containment/authz/egress/response-bound (8.2).
- 1.6a/b/c → internal hardening; reachability = the validation tests.

No unexpected tested-but-unwired gaps (all by-design frozen-contract deferrals).

## Open follow-ups

**Step-9 categorized items (orchestrator-routed during the session; listed for the round verify pass):**
- _Cross-doc rows_ (orchestrator writes): Redactor / policy.yaml / complete mcp_contract rows in `core/CLAUDE.md`; Appendix-A reconciliations (Redactor confirmed; policy.yaml schema_version additive D-A7; MCP result envelope + marker + ingress allow-list); the `core/_types.py` module-layout note; "StrictBool"/"tuple (LESSON 8)" refinements on the relevant rows.
- _Convention candidates_ (LESSONS 12–17, orchestrator-banked): boundary-interface-freeze-without-recall-claim; fail-CLOSED-config-split; ingress-shape-gate-vs-runtime-containment; deny-as-typed-marker (both-arms-extra-forbid); cross-cutting `core/_types.py` identity-vs-content hardened aliases; frozen-collection-tuple; StrictBool-for-safety-bools.
- _Future TODOs — phases_: Redactor engine+fuzz gate (2.3); provider catalog + consistency (10); get_file runtime containment + registry authz + egress + loopback + non-ASCII widening (8.2); chunk.vector→tuple (3.1); Trojan-Source content sanitization (2 redactor); `_GetFilePath` max_length + query control-char rejection (§14 ingress-hardening pass); registry.entries dict-immutability residual.

**Before-fork checklist remaining (before `/phase-exit 1`):** Phase-0 spikes 0.3 (federation O-FED) + 0.4 (LanceDB bake-off), then `/phase-exit 1` (arch-drift audit + spec-coverage + verify-only push → merge `track/contract` → integration `main`), carrying the D-A13/D-A14 fork obligations into the spine handoff.

## Round seal (this session)
- Slice commits on `track/contract`: `343b6fb` (1.5a) · `a9df580` (1.5b) · `e65b9e3` (1.5c1) · `959d5d9` (1.5c2) · `0520304` (1.6a) · `ec71d48` (1.6b) · `de63ead` (1.6c) + this session doc.
- Suite 232/232; `mypy --strict` (`mypy .`) + ruff + ruff format clean (47 source files). Every slice security-reviewed (1.5a/1.5c1/1.6a/1.6c security-relevant — all CLEAN; 1.6a's escalated Finding drove the owner-approved unicode policy). Not pushed (orchestrator pushes at `/orchestrate-end`).
