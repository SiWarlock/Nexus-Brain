# /tdd brief — hostport_contract

## Feature
Freeze the `HostPort` (§7) — the **sole mutation chokepoint** (Key safety rule #4 / §4 invariant #3): `capabilities()` / `authorize(intent)` / `perform(action)`, gated by the closed `HostCapability` allowlist `{own_store_write, owned_doc_refresh, consented_host_config}`, **fail-closed**. Freeze the Protocol + the allowlist enum + the Intent/Action/Result data contracts + `HostDenied` + the `FakeHost` double. First of Phase 1.4's port slices (HostPort is safety-critical → its OWN slice/commit).

## Use case + traceability
- **Task ID:** 1.4 (slice **1.4a** — HostPort; provider ports / CodeGraphPort / Event·Secret·Observability follow as 1.4b/1.4c/1.4d)
- **Architecture sections it implements:** `ARCHITECTURE.md §7` (Ports — HostPort signature + closed allowlist), §4 (invariant #3 — side-effects flow only through the active `HostPort`), §14 (the INV-allowlist test — *no core module reaches an fs/git mutation except via `HostPort.perform`*; the enforcement test lands when mutation-capable modules exist, Phase 2+), §2.5 (seam → schema-snapshot). Appendix-A:218 (HostPort row).
- **Related context:** mirrors the 1.1 port pattern (`core/ports/idgen.py` — `Protocol` + real adapter + `Fake*` double; `@runtime_checkable` for the conformance test; LESSON 1). The allowlist enum follows LESSON 6 (named domain enum = `StrEnum` + membership snapshot). **SAFETY-CRITICAL** — security-reviewer runs every-slice; this is its own commit (never bundled).

## Acceptance criteria (what "done" means)
- [ ] `HostCapability` is a closed `StrEnum` with **exactly 3 values** `{own_store_write, owned_doc_refresh, consented_host_config}`, pinned by a `test_host_capability_values` membership snapshot (LESSON 6; this IS the "closed typed allowlist" the 1.4 acceptance names).
- [ ] `HostPort` is a `@runtime_checkable Protocol` with `capabilities() -> frozenset[HostCapability]`, `authorize(intent: HostIntent) -> HostAction`, `perform(action: HostAction) -> HostResult`.
- [ ] `HostIntent`, `HostAction`, `HostResult` are frozen Pydantic v2 contracts (`frozen=True`, `extra="forbid"`), each pinned by a `spec(§7)` schema-snapshot (§2.5-seam ★ freeze). Concrete per-capability payloads are **deferred to Phase-2** (carried as a minimal/typed-but-extensible shape now — see Q3).
- [ ] **Fail-closed `authorize` (the safety pin):** an intent whose `capability ∉ capabilities()` raises **`HostDenied`** — never silently allowed; an unrecognized/undefined capability denies (most-restrictive). `authorize` returns a `HostAction` only for an allowlisted intent.
- [ ] **`perform` requires an authorized action:** the contract is that `perform` executes only a `HostAction` produced by `authorize`; a non-authorized/forged action is rejected. Pinned behaviorally via `FakeHost` (Python can't enforce a private constructor; the module-level INV-allowlist test — §14 — lands in Phase 2 when mutation-capable modules exist).
- [ ] `FakeHost` (in `core/testing/fakes.py`) faithfully upholds the `HostPort` contract (LESSON 1 fidelity): configurable `capabilities()`, fail-closed `authorize`, and a `perform` that records performed actions for test assertions. A `*_conform` test asserts `isinstance(FakeHost(...), HostPort)`.
- [ ] **INV-allowlist tripwire (architecture-invariant test) present + green** — a static scan asserts no `core/` module (excl. `tests/`/`.venv`) calls an FS/git mutation primitive outside the allowlisted host-adapter path (`core/ports/host.py`). Passes now; guards forward (see Wiring). **This is item #1 of the lead's Step-9 safety confirmation.**
- [ ] Any string fields on the Intent/Action contracts use `StringConstraints(strip_whitespace=True, min_length=1)` (LESSON 7).
- [ ] All unit tests in `core/tests/ports/test_host.py` pass; `/preflight` clean (canonical visible gate; `mypy .`).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes the `core/CLAUDE.md` row + confirms Appendix-A:218).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2+.** HostPort is the freeze-before-fork mutation chokepoint; no core module performs a mutation yet, so nothing routes through `perform` this phase (by design — the chokepoint exists *before* its callers). Exported as `ports.host`; `FakeHost` is the seam every track injects. Not a tested-but-unwired gap.

**INV-allowlist architecture-invariant test — SEED the tripwire form NOW (lead safety ask).** The full §14 proof (every mutation-capable module routes through `HostPort.perform`) needs callers, so it matures in Phase 2. But 1.4a seeds the **static-scan tripwire**: an architecture-invariant test that scans every `core/` module (excluding `tests/` + `.venv`) for FS/git mutation primitives — `os.remove/rename/replace/mkdir/rmdir/unlink`, `shutil` mutators, `open(... 'w'/'a'/'x' ...)`, `pathlib.Path.write_*/unlink/mkdir/rename`, `subprocess`/git-mutation calls — and asserts NONE appear **outside the allowlisted host-adapter path** (`core/ports/host.py`; the Phase-2 `StandaloneHost` module joins the allowlist when it lands). It **passes trivially today** (nothing in `core/` mutates) and becomes the **tripwire that fails the moment a Phase-2 module tries to mutate outside the chokepoint** — putting the chokepoint enforcement on the record from Phase 1. (AST-based scan preferred over regex for robustness; `ast.walk` the module trees.)

## Files expected to touch
**New:**
- `core/ports/host.py` — `HostPort` Protocol + `HostCapability` `StrEnum` + `HostIntent`/`HostAction`/`HostResult` frozen contracts + `HostDenied`.
- `core/tests/ports/test_host.py` — enum snapshot + Protocol conformance + fail-closed authorize + perform-requires-authorized + FakeHost behavior.

**Modified:**
- `core/testing/fakes.py` — add `FakeHost` (the test double; implementer territory — it's a test fake, not orchestrator-owned).

**Orchestrator territory (flag at Step 9, do NOT edit):** `core/CLAUDE.md` cross-doc row, `ARCHITECTURE.md` Appendix-A:218.

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/ports/test_host.py` (`pytestmark = pytest.mark.unit`; `from ports.host import HostPort, HostCapability, HostIntent, HostAction, HostResult, HostDenied`; `from testing.fakes import FakeHost`):

1. **`test_host_capability_values`** — Asserts: `{c.value for c in HostCapability} == {"own_store_write","owned_doc_refresh","consented_host_config"}`. Why: LESSON 6 — the closed mutation allowlist is a frozen contract (§7/Appendix-A:218).
2. **`test_hostport_protocol_conformance`** — Asserts: `isinstance(FakeHost(...), HostPort)` (runtime_checkable). Why: LESSON 1 — the Fake satisfies the port.
3. **`test_host_intent_schema_snapshot`** / **`test_host_action_schema_snapshot`** / **`test_host_result_schema_snapshot`** — Asserts: each `set(Model.model_fields) == EXPECTED_*`. Why: §2.5-seam ★ freeze (`spec(§7)`).
4. **`test_intent_action_result_frozen_extra_forbid`** — Asserts: each rejects an unknown kwarg + post-construct mutation. Why: §4 parse-don't-trust.
5. **`test_authorize_allows_allowlisted_capability`** — Asserts: `authorize(HostIntent(capability=own_store_write, …))` returns a `HostAction`. Why: §7 happy path.
6. **`test_authorize_denies_unallowlisted_capability`** — Asserts: an intent whose capability ∉ a FakeHost's `capabilities()` raises `HostDenied`. Why: **fail-closed (Key safety rule #4 / §4 #3) — the cardinal safety pin.**
7. **`test_perform_executes_authorized_action`** — Asserts: `perform(authorize(intent))` returns a `HostResult` (ok) AND the FakeHost recorded the action. Why: the authorize→perform happy path + the chokepoint is observable.
8. **`test_perform_rejects_unauthorized_action`** — Asserts: a `HostAction` NOT produced by `authorize` (forged/hand-built) is rejected by `perform`. Why: the chokepoint is not bypassable through `perform` directly (fail-closed).
9. **`test_fakehost_fidelity`** — Asserts: `FakeHost` enforces the same fail-closed allowlist contract a real host must (configurable capabilities; deny outside; record performed). Why: LESSON 1 — no looser-fake fidelity trap on a safety seam.
10. **`test_host_intent_strip_identity`** — Asserts: Intent/Action string fields strip + reject empty/whitespace. Why: LESSON 7.
11. **`test_inv_allowlist_no_mutation_outside_hostport`** (architecture-invariant) — Asserts: an AST scan of every `core/` module (excl. `tests/`/`.venv`) finds NO FS/git mutation primitive (`os.remove/rename/replace/mkdir/rmdir/unlink`, `shutil` mutators, `open(...,'w'/'a'/'x')`, `pathlib.Path.write_*/unlink/mkdir/rename`, `subprocess`) outside the allowlisted host-adapter path (`core/ports/host.py`). Why: §14/§4 #3 — the chokepoint tripwire (passes now; fails the first Phase-2 bypass). **Lead Step-9 safety item #1.**

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** NEW port `HostPort` + `HostCapability` enum + `HostIntent`/`HostAction`/`HostResult` — §7 / Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - `core/CLAUDE.md` cross-doc table — NEW `HostPort` row (Protocol + 3-value `HostCapability` membership snapshot; Intent/Action/Result `spec(§7)` shapes; fail-closed authorize; `FakeHost`; pin `test_host.py`). Note the deferred per-capability payload + the Phase-2 INV-allowlist test.
  - `ARCHITECTURE.md` Appendix-A:218 — **confirm** the HostPort row matches (`capabilities()/authorize(intent)/perform(action)` + the 3-value allowlist + NexusOpsHost→ActionPlan); reconcile only if the slice diverges (e.g. annotate that Intent/Action payloads are Phase-2-deferred + StandaloneHost is Phase-2).
- **§2.5-seam (shared-contract) touched?** YES — HostPort §7 is §2.5-crossed; RED includes the enum membership snapshot (#1) + the Intent/Action/Result schema-snapshots (#3).
- **Safety:** this slice touches Key safety rule #4 — flag the fail-closed authorize + the chokepoint contract explicitly at Step 9; security-reviewer every-slice.

## Things to flag at Step 2.5
1. **StandaloneHost scope — defer the REAL adapter to Phase 2?** Default vote: **YES.** 1.4a freezes the Protocol + `HostCapability` + Intent/Action/Result + `HostDenied` + `FakeHost`; the real `StandaloneHost` (whose `perform` does actual LanceDB write / owned-doc refresh / host-config) is **Phase-2** — the mutation operations don't exist yet, so a "real adapter" would be a stub. The freeze-before-fork deliverable is the interface + the Fake (per the 1.4 acceptance "interfaces + Fake doubles + cassette"), and the fail-closed `authorize` logic IS frozen + Fake-tested now. If you'd rather ship a minimal `StandaloneHost` shell (capabilities()+authorize() real, perform() routing to an empty Phase-2 handler map) → ping `TWEAK`; my vote keeps it to the Fake to avoid a half-built real host.
2. **Intent→Action flow: does `authorize` transform intent→authorized action?** Default vote: **YES — `authorize(intent: HostIntent) -> HostAction`** (returns an authorized, capability-stamped action) and **`perform(action: HostAction)` executes only authorized actions**; `authorize` raises `HostDenied` fail-closed. Rationale: makes the chokepoint *type-shaped* (you obtain a `HostAction` only from `authorize`) — the strongest expression of Key safety rule #4 Python allows. (Alternative: `intent == action`, `authorize -> bool` — rejected; loses the type-shaped chokepoint.)
3. **Intent/Action payload — minimal/deferred now?** Default vote: **minimal now, concrete per-capability payloads deferred to Phase-2** — `HostIntent`/`HostAction` carry `{capability, summary}` (+ an extensible-but-typed slot if needed), with the actual mutation payload (what `own_store_write` writes) landing when the mutations exist. Same deferral discipline as EvidenceType-membership / index_freshness-vocab (don't over-specify a payload before its operation exists). The `spec(§7)` snapshot pins the current shape; later per-capability enrichment is additive.
4. **`HostCapability` = `StrEnum` + membership snapshot (LESSON 6)?** Default vote: **YES** — the closed mutation allowlist is the canonical example of a named, load-bearing domain enum; `StrEnum` + a `test_host_capability_values` membership snapshot (a value add/remove to the *mutation allowlist* must be a loud test failure).
5. **Where do Intent/Action/Result live — `ports/host.py` or `model/`?** Default vote: **co-locate in `ports/host.py`** — they're the port's own vocabulary, tightly coupled to the Protocol, and small; splitting them into `model/` adds an import hop for no gain. (Cross-doc row still lists them under the HostPort §7 contract.)
6. **`HostResult` shape?** Default vote: minimal frozen `{ok: bool, detail?}` (or capability-tagged) — enough to express perform success/failure; richer per-capability results defer to Phase-2 with the payloads.

## Dependencies + sequencing
- **Depends on:** 1.1 port pattern (Protocol + real + Fake; `@runtime_checkable`). No dependency on the 1.2/1.3 models.
- **Blocks:** every Phase-2+ mutation (all FS/git side-effects route through `perform`); the §14 INV-allowlist architecture test (Phase 2); the NexusOpsHost adapter (P2, serializes intents to ActionPlans). Parallel-eligible with 1.4b/1.4c/1.4d once dispatched.

## Estimated commit count
**1.** One focused ★ freeze-before-fork **safety-critical** port (HostPort + allowlist + Intent/Action/Result + HostDenied + FakeHost). **Never bundled** — a safety-invariant slice (Key safety rule #4) always gets its own commit (template "Estimated commit count" + root `CLAUDE.md`).

## Lessons-logged candidates anticipated
- **Convention candidate** — possibly "a type-shaped chokepoint: the privileged operation's input type is only obtainable from the authorizer" (if Q2's authorize→action pattern proves reusable for other gated seams). Else covered by LESSON 1/6.
- **Architecture-doc note candidate** — Appendix-A:218 annotation: Intent/Action payloads + StandaloneHost are Phase-2; the §14 INV-allowlist test is Phase-2.
- **Future TODO — belongs-to-phase** — (a) real `StandaloneHost` + per-capability perform handlers → Phase 2; (b) the §14 INV-allowlist architecture-invariant test → Phase 2 (first mutation-capable module); (c) `NexusOpsHost` adapter (intents→ActionPlan, propose-only) → P2.

## How to invoke
1. **Read this brief end-to-end** — 6 Step-2.5 questions; Q1 (StandaloneHost scope) + Q2 (authorize→action) are load-bearing on a safety seam.
2. **Run `/tdd hostport_contract`** (session oriented — no `/session-start`).
3. **Step 0 (Restate)** — confirm HostPort interface + allowlist + Fake (NOT the real StandaloneHost).
4. **Step 1 (Identify files)** — `core/ports/host.py` + `core/tests/ports/test_host.py` + `core/testing/fakes.py` (FakeHost).
5. **Step 2.5** — tight write-up + acceptance→test coverage map; answer the 6 Qs (esp. Q1/Q2). Wait for `APPROVED.`/`TWEAK:`/`ADD:`. **Flag the safety pin (#6 fail-closed authorize) prominently.**
6. **Step 9** — categorized flags + the HostPort cross-doc row ask + ship-ask. **Include an explicit SAFETY block I will relay verbatim to the lead (team-lead's one-time ask for this safety-critical slice):** (1) the INV-allowlist tripwire test is present + green (quote the test name + scan scope); (2) the closed typed allowlist is the 3-value `HostCapability` `StrEnum`, asserted by `test_host_capability_values` (note: `StandaloneHost`-the-adapter is Phase-2, but the closed set it will use is frozen+closed+tested now); (3) the `security-reviewer` verdict on the chokepoint.
