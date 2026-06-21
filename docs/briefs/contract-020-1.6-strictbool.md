# /tdd brief — strictbool_safety_bools

## Feature
Apply `StrictBool` to the safety/security/lifecycle boolean fields across the frozen contracts
(OWNER-APPROVED) — policy opt-ins (`mcp.expose`/`federation.visible`/`sessions.consent`), the host
capability stamp (`HostAction.authorized`), and chunk lifecycle (`tombstone`) — so a lax `"yes"`/`1`/
`"on"` can't coerce to `True` (parse-don't-trust on booleans). The last 1.6 sweep slice.

## Use case + traceability
- **Task ID:** 1.6 (atomic sub-slice **1.6c** — StrictBool; completes the 1.6 before-fork sweep; siblings 1.6a `0520304` + 1.6b `ec71d48` landed)
- **Architecture sections it implements:** `ARCHITECTURE.md §4` (parse-don't-trust at the boundary), §7 (`HostPort` — the `authorized` stamp), §16 (policy opt-ins), §5 (`Chunk.tombstone`).
- **Related context:**
  - **OWNER-APPROVED 2026-06-18** (via lead): StrictBool for safety opt-in bools uniformly across host/chunk/policy. (Origin: the 1.5b security-reviewer nit; the implementer correctly didn't change it unilaterally.)
  - **LESSON 9** (`host.py` `authorized` is the forgeable capability stamp that `perform` re-validates) — StrictBool is defense-in-depth on it: a lax-coerced `authorized="1"` is rejected at parse, on top of the `perform` capability-recheck.
  - No fail-open today (malformed bools are rejected; defaults are False) — this is parse-don't-trust hardening, and the before-fork window is the time (tightening a frozen cross-track contract post-fork is breaking).
  - `PolicyDenied.denied = Literal[True]` is deny-STRENGTHENING (a lax `1`→`True` only ever produces a deny) — **leave it** (not an opt-in bool; already constrained).

## Acceptance criteria (what "done" means)
- [ ] `policy.py`: `McpPolicy.expose`, `FederationPolicy.visible`, `SessionPolicy.consent` → `StrictBool` (defaults stay `False`).
- [ ] `host.py`: `HostAction.authorized` → `StrictBool` (the §7 capability stamp; defense-in-depth with the `perform` re-validation, LESSON 9).
- [ ] `chunk.py`: `Chunk.tombstone` → `StrictBool`.
- [ ] Each `StrictBool` field **rejects lax coercion** (`1`, `0`, `"yes"`, `"true"`, `"on"`, `"false"` → `ValidationError`) and **accepts real `bool`** (`True`/`False`). Pinned per field.
- [ ] `McpResult.truncated` per Q1 (default: include for uniformity).
- [ ] `PolicyDenied.denied` stays `Literal[True]` (unchanged — deny-strengthening).
- [ ] Audit confirms the bool inventory is complete (no other safety/lifecycle frozen bool missed).
- [ ] All existing 227 tests stay green (they construct with real bools; field-name + JSON snapshots unchanged — `StrictBool` is still a `bool` field on the wire); `/preflight` clean (canonical, visible — LESSON 5; `mypy .` — D-A3).
- [ ] Cross-doc: flag at Step 9 — no field add/remove/rename; I'll note "StrictBool" on the relevant cross-doc rows (incl. the LESSON-9 `HostAction.authorized` note) at /orchestrate-end.

## Wiring / entry point (Step 7.5)
**none — internal parse-don't-trust hardening of frozen contracts.** No new entry point; the new lax-rejection tests are reachability.

## Files expected to touch
**Modified:**
- `core/model/policy.py` — 3 opt-in bools → `StrictBool`.
- `core/ports/host.py` — `HostAction.authorized` → `StrictBool`.
- `core/model/chunk.py` — `tombstone` → `StrictBool`.
- `core/model/mcp_contract.py` — `McpResult.truncated` → `StrictBool` (per Q1).
- `core/tests/...` — `test_policy.py`, `test_host.py`, `test_chunk.py`, `test_mcp_contract.py`: add lax-rejection + bool-accept assertions.

If the audit finds another safety/lifecycle frozen bool, **flag at Step 2.5**.

## RED test outline (Step 2)
1. **`test_policy_bools_strict`** (`test_policy.py`) — `McpPolicy.expose`/`FederationPolicy.visible`/`SessionPolicy.consent` reject `1`/`"yes"`/`"true"`/`"on"`; accept `True`/`False`; defaults `False`. Why: §16 + §4 parse-don't-trust.
2. **`test_host_authorized_strict`** (`test_host.py`) — `HostAction.authorized` rejects lax; accepts `bool`. Why: §7 capability stamp (LESSON 9 defense-in-depth).
3. **`test_chunk_tombstone_strict`** (`test_chunk.py`) — `tombstone` rejects lax; accepts `bool`. Why: §5 lifecycle flag, parse-don't-trust.
4. **`test_mcp_truncated_strict`** (`test_mcp_contract.py`) — per Q1. Why: uniformity.
5. **(implicit) full suite green** — 227 + new; snapshots unchanged.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** **none** — `StrictBool` is still a `bool` field (no add/remove/rename; field-name + JSON snapshots unchanged).
- **Orchestrator doc rows to write hot:** I'll add "StrictBool" to the relevant `core/CLAUDE.md` cross-doc notes (policy opt-ins, `HostAction.authorized` LESSON-9 note, `Chunk.tombstone`) at /orchestrate-end. No Appendix-A field change.
- **§2.5-seam:** frozen contracts touched but shape-unchanged — existing snapshots staying green is the regression guard.

> **Orchestrator territory** (`core/CLAUDE.md` "must NOT touch"): flag at Step 9.

## Things to flag at Step 2.5
1. **`McpResult.truncated` → StrictBool?** My default vote: **include for uniformity** — it's a frozen-contract bool and uniform parse-don't-trust on all of them is cheap + consistent. Note: it's a *system-set output flag* (Phase-8.2 sets it), outside the owner's named host/chunk/policy scope — so it's an additive-uniform extension within the approved StrictBool posture, not a new escalation. (Leave it `bool` if you'd rather keep the owner's scope literal — soft call.)
2. **Bool inventory complete?** My default vote: the set is `policy ×3` + `host.authorized` + `chunk.tombstone` (+ `truncated` per Q1); `PolicyDenied.denied` stays `Literal[True]`. Audit + confirm no other safety/lifecycle frozen bool is missed.
3. **Mechanism — `pydantic.StrictBool`?** My default vote: yes — annotate the field type `StrictBool` (or `Annotated[bool, Strict()]`). Straightforward; verify it rejects `1`/`"true"` and accepts `True`/`False`.

## Dependencies + sequencing
- **Depends on:** 1.5b `policy.py` (`a9df580`), 1.4a `host.py`, 1.2a `chunk.py`, 1.5c2 `mcp_contract.py` — all landed. Rebases on 1.6a/1.6b (which touched these files' str/collection fields — different lines from the bools).
- **Blocks:** completes the 1.6 sweep → then spikes 0.3/0.4 → /phase-exit 1. A lax-coercible safety bool in a frozen cross-track contract post-fork = a Finding → land before /phase-exit 1.

## Estimated commit count
**1.** The owner-approved safety-bool hardening + the `HostAction.authorized` security stamp → **its own commit** (safety pin; root `CLAUDE.md` "safety-critical pin gets its own commit").

## Lessons-logged candidates anticipated
- **Convention candidate** — "Security/safety/lifecycle booleans use `StrictBool`, not `bool` — a lax `1`/`"yes"`/`"on"` must not coerce to `True` on a field that gates exposure/consent/authorization/lifecycle (parse-don't-trust on booleans); deny-strengthening `Literal[True]` markers are exempt."
- **Architecture-doc note candidate** — note `StrictBool` on the `HostAction.authorized` LESSON-9 cross-doc row (defense-in-depth layer).

## How to invoke
1. Read this brief end-to-end — esp. Q1 (`truncated`) + Q2 (inventory audit).
2. Run **`/tdd strictbool_safety_bools`**.
3. **Step 0/1** — confirm restate + the bool inventory (flag any other safety/lifecycle frozen bool).
4. **Step 2.5** — send the test-design write-up + answer the 3 Qs; wait for `APPROVED.` before GREEN.
5. **Step 9** — confirm snapshots stayed green; surface the convention candidate.
