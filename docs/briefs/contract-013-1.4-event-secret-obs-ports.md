# /tdd brief — event_secret_obs_ports_contract

## Feature
Freeze the 3 remaining §7 ports as behavioral Protocols + Fake doubles: `EventSource` (`poll`/`subscribe`), `SecretStore` (`get_ref`/`resolve`; keychain — Key safety rule #3), `ObservabilitySink` (`emit`; instrumented-but-silent). Completes Phase 1.4 (the 11-port freeze). Bundled (3 small non-mutating behavioral ports).

## Use case + traceability
- **Task ID:** 1.4 (slice **1.4d** — Event/Secret/Observability; completes 1.4 → the 11 ports are frozen)
- **Architecture sections it implements:** `ARCHITECTURE.md §7` (EventSource `subscribe/poll`; SecretStore `get_ref/resolve` keychain; ObservabilitySink `emit`), §18 (Key safety rule #3 — secrets only in the OS keychain, keychain-refs only; never in config/index/events/logs). §2.5 (seam → schema-snapshot for the data types). Appendix-A — **no rows exist for these 3 ports** (the §2.5 freeze-9 list omits them; §7 says all 11 ports are Appendix-A contracts) → orchestrator ADDS 3 additive rows (D-A7-style, lead-noted).
- **Related context:** mirrors the 1.1/1.4b behavioral-port pattern (`Protocol` + `@runtime_checkable` + faithful deterministic `Fake*`; LESSON 1). `tuple[…]` for collections (LESSON 8); strip identity (LESSON 7). The lead **cleared the per-slice safety loop** after 1.4a — no safety-block relay here, but `security-reviewer` runs every-slice and will cover SecretStore.

## Acceptance criteria (what "done" means)
- [ ] `EventSource`, `SecretStore`, `ObservabilitySink` are `@runtime_checkable Protocol`s with the §7 signatures (see RED outline).
- [ ] `Event`, `SecretRef`, `ObsEvent` are frozen Pydantic v2 (`frozen=True`, `extra="forbid"`), each pinned by a `spec(§7)` schema-snapshot (§2.5-seam); collection fields use `tuple[…]`.
- [ ] **★ Key safety rule #3 pin:** `SecretRef` carries ONLY keychain coordinates (`{service, account}`) — **NO secret material**; `extra="forbid"` rejects a `secret`/`value`/`password`/`token` kwarg (the ref is what flows through config/events; the plaintext exists only transiently as `resolve`'s return). Pinned by `test_secret_ref_carries_no_secret`.
- [ ] `SecretStore.get_ref(name) -> SecretRef` (a ref, not the secret); `SecretStore.resolve(ref) -> str` (the transient plaintext — the ONLY plaintext path; caller never persists/logs it).
- [ ] Faithful deterministic `Fake*` doubles in `core/testing/fakes.py`: `FakeEventSource` (canned event queue), `FakeSecretStore` (in-memory test secrets; `resolve` returns them; does NOT expose them via `repr`/`SecretRef`), `FakeObservabilitySink` (records emitted events for assertions — local only, never network). `*_conform` isinstance tests (LESSON 1).
- [ ] String identity fields strip+min_length (LESSON 7).
- [ ] All unit tests pass; `/preflight` clean (`mypy .`).
- [ ] Cross-doc invariant flagged at Step 9 (orchestrator writes 3 NEW `core/CLAUDE.md` rows + 3 NEW additive Appendix-A rows).

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 2+.** These are freeze-before-fork seams; the real adapters land where consumed: EventSource (git-hook/watcher feed → Phase-2 sync; the NexusOps-outbox variant is P2), SecretStore (the OS-keychain adapter + no-plaintext-in-logs enforcement → Phase-2 setup/providers), ObservabilitySink (the OTel sink, **off-by-default + local-only + never-phone-home** → Phase-2; D-22). This slice freezes the interfaces + data types + Fakes — the freeze-before-fork need. Exported as `ports.{events,secrets,observability}`. Not a tested-but-unwired gap.

## Files expected to touch
**New:**
- `core/ports/events.py` — `EventSource` Protocol + `Event`.
- `core/ports/secrets.py` — `SecretStore` Protocol + `SecretRef`.
- `core/ports/observability.py` — `ObservabilitySink` Protocol + `ObsEvent`.
- `core/tests/ports/test_events.py`, `test_secrets.py`, `test_observability.py` (per-module convention; consolidate into one file if you judge it cleaner — flag at Step 1).

**Modified:**
- `core/testing/fakes.py` — add `FakeEventSource`, `FakeSecretStore`, `FakeObservabilitySink`.

**Orchestrator territory (flag at Step 9):** 3 `core/CLAUDE.md` rows, 3 NEW Appendix-A rows.

## RED test outline (Step 2)
`pytestmark = pytest.mark.unit`; import the Protocols/types from `ports.{events,secrets,observability}` + the Fakes from `testing.fakes`.

**EventSource (`test_events.py`):**
1. `test_eventsource_conformance` — `isinstance(FakeEventSource(...), EventSource)` (LESSON 1).
2. `test_eventsource_poll` — `poll() -> tuple[Event, ...]` (drains the canned queue; empty → `()`).
3. `test_event_snapshot` — `set(Event.model_fields) == {"kind","source"}` (or your minimal shape); frozen + extra-forbid (`spec(§7)`).
4. `test_fake_eventsource_deterministic` — same canned config → same poll sequence (LESSON 1).

**SecretStore (`test_secrets.py`):**
5. `test_secretstore_conformance` — `isinstance(FakeSecretStore(...), SecretStore)`.
6. `test_secretstore_get_ref_and_resolve` — `get_ref(name) -> SecretRef`; `resolve(ref) -> str` returns the stored test secret.
7. **`test_secret_ref_carries_no_secret`** — `set(SecretRef.model_fields) == {"service","account"}`; a `secret`/`value`/`password`/`token` kwarg raises (`extra="forbid"`). Why: **Key safety rule #3** — the ref never carries plaintext.
8. `test_fake_secretstore_no_leak` — the secret is NOT exposed via `SecretRef` fields, `repr(ref)`, or `str(ref)` (only `resolve` returns it). Why: §18 no-plaintext-in-refs/logs.
9. `test_secret_ref_snapshot` + strip identity on `service`/`account` (LESSON 7).

**ObservabilitySink (`test_observability.py`):**
10. `test_obssink_conformance` — `isinstance(FakeObservabilitySink(...), ObservabilitySink)`.
11. `test_obssink_emit` — `emit(event: ObsEvent) -> None`; `FakeObservabilitySink` records it (assertable); emitting does NOT raise / does NOT touch the network (records locally). Why: §7 emit + instrumented-but-silent.
12. `test_obsevent_snapshot` — `set(ObsEvent.model_fields) == {…}` (your minimal shape); frozen + extra-forbid; any attributes collection is `tuple` (`spec(§7)`).

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** 3 NEW ports + 3 NEW data types — §7/§18/Appendix-A.
- **Orchestrator doc rows to write hot (Step 9 routing):**
  - 3 NEW `core/CLAUDE.md` cross-doc rows (EventSource / SecretStore / ObservabilitySink — behavioral Protocols + Fakes + data-type snapshots; the SecretRef-no-secret safety pin).
  - **3 NEW Appendix-A rows (additive — D-A7-style, lead-noted for owner):** these 3 ports have no Appendix-A row today though §7 calls all 11 ports Appendix-A contracts; orchestrator adds them hot + notes the additive reconciliation.
- **§2.5-seam:** Event/SecretRef/ObsEvent cross seams (sync/setup/obs) → snapshots included.
- **Safety:** SecretStore touches Key safety rule #3 — flag at Step 9; security-reviewer every-slice.

## Things to flag at Step 2.5
1. **EventSource — `poll` + `subscribe`, or `poll`-only?** Default vote: **both** (§7 "subscribe/poll") — `poll() -> tuple[Event, ...]` (the standalone git-hook/watcher pull) + `subscribe(handler: Callable[[Event], None])` (push). If subscribe adds friction with no Phase-1 consumer, `poll`-only is acceptable — flag. The NexusOps-outbox EventSource variant is P2.
2. **`Event` shape.** Default vote: minimal `{kind, source}` (kind = event type, source = origin) + payload deferred (additive later, like the other deferred payloads). Flag your minimal shape.
3. **`SecretStore.resolve` return + `SecretRef` shape (safety).** Default vote: `resolve(ref) -> str` (transient plaintext); `SecretRef{service, account}` — keychain coordinates only, NO secret field (`extra="forbid"` pins it). The real macOS-Keychain adapter + no-plaintext-in-logs are Phase-2. Confirm the Fake stores secrets out-of-band (a private dict keyed by ref), never on the `SecretRef`.
4. **`ObservabilitySink.emit` signature + `ObsEvent` shape.** Default vote: `emit(event: ObsEvent) -> None`; `ObsEvent{name, attributes}` where `attributes` is a `tuple[tuple[str, str], ...]` (frozen pairs) OR minimal `{name}` + deferred attributes. Pick the minimal frozen shape; the OTel span/metric/log mapping is the Phase-2 real-sink concern (off-by-default, never phone home).
5. **Test-file layout** — 3 per-module files vs 1 bundled. Default vote: **3 per-module** (matches `test_clock`/`test_host`/`test_codegraph`); consolidate only if you judge it cleaner.

## Dependencies + sequencing
- **Depends on:** 1.1 port pattern. Independent of the other 1.4 ports / 1.2 / 1.3.
- **Blocks:** Phase-2 sync (EventSource), setup/providers (SecretStore), observability wiring (ObservabilitySink). **Completes Phase 1.4** → after this, 1.5 (boundary contracts) + the before-fork hardening sweep + Phase-0 0.3/0.4 remain before `/phase-exit 1`.

## Estimated commit count
**1.** One bundled slice — 3 small non-mutating behavioral ports + Fakes + data types, sharing the §7 behavioral-port pattern. SecretStore touches a safety invariant but the **interface freeze** (get_ref/resolve + the no-secret-in-ref pin) is not safety-CRITICAL the way HostPort.perform is (no fail-closed execution logic) — bundling is acceptable; the real keychain adapter + log-scrub enforcement (Phase-2) is where the safety teeth land. If security-reviewer surfaces a contract-level safety concern, we split.

## Lessons-logged candidates anticipated
- **Convention candidate** — possibly "a safety contract excludes the dangerous field by shape + `extra='forbid'` (SecretRef has no secret field; cf. StoreVersionStamp has no SHA field)" — a generalization worth banking if it recurs (it's now the 2nd instance).
- **Architecture-doc note candidate** — the 3 additive Appendix-A rows; the instrumented-but-silent/never-phone-home note on ObservabilitySink.
- **Future TODO — belongs-to-phase** — (a) real adapters: keychain (SecretStore) + OTel sink (ObservabilitySink, off-by-default) + git-hook/watcher (EventSource) → Phase-2; (b) no-plaintext-in-logs enforcement → Phase-2 (log-scrub); (c) NexusOps-outbox EventSource + EventEnvelope → P2.

## How to invoke
1. **Read this brief end-to-end** — 5 Step-2.5 questions; Q3 (SecretStore safety shape) is the load-bearing one.
2. **Run `/tdd event_secret_obs_ports_contract`** (session oriented).
3. **Step 0 (Restate)** — confirm the 3 Protocols + data types + Fakes (NOT real adapters).
4. **Step 1 (Identify files)** — confirm the 3 port modules + test layout (Q5) + fakes.py.
5. **Step 2.5** — write-up + coverage map; answer the 5 Qs. Wait for `APPROVED.`/`TWEAK:`/`ADD:`.
6. **Step 9** — categorized flags + the 3 cross-doc rows + 3 additive Appendix-A rows + the SecretStore safety note + ship-ask. **This completes Phase 1.4.**
