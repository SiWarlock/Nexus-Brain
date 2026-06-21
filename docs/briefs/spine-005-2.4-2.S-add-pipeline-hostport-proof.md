# /tdd brief — add_ingest_pipeline_and_hostport_runtime_proof

> **BUNDLE (2 commits, owner bundle-aggressively directive).** ONE brief, ONE implementer cycle, but
> **two Step-10 commits** because Task 2.S is the cardinal **Key-safety-rule-#4** proof and a
> safety-critical pin **always gets its own commit** (template "Estimated commit count"). Order:
> **Commit 1 = 2.S** (the HostPort chokepoint: real `StandaloneHost` + tripwire hardening + runtime
> proof) lands FIRST so Commit 2 (the `add` pipeline) wires its manifest write *through* the proven
> chokepoint. security-reviewer is **mandatory** on BOTH commits; 2.S gets dedicated test + review
> surface — the bundle must not dilute it.

## Feature
Build the **`add` ingest orchestration** (`core/ingest/pipeline.py`) — discover→classify→chunk→
context-augment→**redact**→assemble frozen `Chunk`+`Anchor`→**write the manifest** — idempotent
(re-add updates, never duplicates), R-PARTIAL (ingest whatever exists; per-file malformed-content
error boundary; temp-write + atomic swap, no half-swap) — AND land Task **2.S**, the ★SAFETY **§14
INV-allowlist FULL runtime proof**: the real `StandaloneHost` adapter (the manifest write is the
first `core/` FS mutation and MUST route through `HostPort.perform`), the hardened static tripwire,
and the runtime per-mutator proof. This closes the 2.1/2.2/2.3 reachability deferral — `discover`/
`classify`/`chunk_docs`/`chunk_code`/`CatchableSetRedactor` all get their first production caller.

## Use case + traceability
- **Task ID:** 2.4 + 2.S (bundle)
- **Architecture sections it implements:**
  - `ARCHITECTURE.md §8` (the ingest pipeline order + **`add` idempotent** + **R-PARTIAL temp generation, no half-swap**; the Phase-2 impl note at §8 line 104 is the binding scope for chunk-stage output)
  - `ARCHITECTURE.md §5` (the **source-of-truth law**: manifest is a DERIVED projection; recipe fields = `embedding_model`/`dimension`/`chunker_version`; `ingested_from_sha` mirrors the version tag)
  - `ARCHITECTURE.md §14` + **§4 #3** (the **INV-allowlist**: "no core module reaches an fs/git mutation except via `HostPort.perform`" — Task 2.S upgrades the 1.4a static tripwire to the runtime per-mutator proof and extends it to **session-state** writes)
  - `ARCHITECTURE.md §7` (the `HostPort` contract + the real `StandaloneHost` adapter — per-capability `perform` handlers; the Phase-2-deferred payload lands here)
  - `ARCHITECTURE.md §16` (`policy_path` in the manifest; not exercised beyond the field this slice)
- **Phase-scope note:** this brief **widens phase scope because** Task **2.S** lives in Phase 2 but implements the **§14 INV-allowlist runtime proof** + the **§7 `HostPort` `StandaloneHost`** (+ **§4 #3** chokepoint) — exactly as the `### 2.S` tracker heading cites (`implements §14/§4 #3`). The Phase-2 header's Spec anchors (§8/§18/§16/§5) cover 2.4; §14/§7/§4 are the safety task's anchors. Other §-mentions are **reference-only, not implemented here**: §2.5 (the seam the `HostPort` growth crosses), §23 (the NexusOps `ActionPlan` rationale for a self-describing action), §12 (Phase-3 sync/tombstone carry), §15 (Phase-5 CLI wiring).
- **Related context:** prior spine slices 2.1 (`discover`/`classify`, `dc5a9aa`), 2.2 (`chunk_docs`/`chunk_code`, `c10ea79`+`434c46a`), 2.3 (`CatchableSetRedactor`, `723db12`). Frozen contracts consumed: `core/model/manifest.py` (`ProjectManifest`/`ManifestArtifact`), `core/model/chunk.py` (`Chunk`, all-required), `core/model/anchor.py` (`Anchor`, all-required), `core/ports/host.py` (`HostPort`/`HostCapability`/`HostIntent`/`HostAction`/`HostResult`/`HostDenied`). Inject **`Fake*` providers** for the non-deterministic seams: `FakeEmbeddingProvider` (vector + `dimension` + `model_version`), `FakeClock`, `FakeIdGen` (all in `core/testing/fakes.py`). LESSONS **19/20** (ChunkDraft + `get_args` pin + assemble-where-context-exists), **21/22** (redactor), **9** (chokepoint), **6** (allowlist membership), **8** (tuple containers / deep-frozen), **16** (content/Trojan-Source sanitization is the consuming phase's job), **14** (containment at the boundary).

## ✅ Owner-gated decision (load-bearing safety contract) — RESOLVED: Option C (owner-ratified 2026-06-21)
**The manifest write must carry a payload (path + content) to `StandaloneHost.perform`, but the frozen
§7 `HostIntent`/`HostAction` are `{capability, summary}` only — per-capability payloads are explicitly
"Phase-2-deferred" (host.py:53). Growing this FROZEN cardinal-safety §2.5-seam contract was escalated
(category #1/#4). **OWNER RULED — Option C (LOCKED):** add ONE optional typed
`payload: StoreWritePayload | None` (fields `{rel_path, content}`) on `HostIntent`/`HostAction`,
covering `OWN_STORE_WRITE` only; widen to the per-capability discriminated union (A) **additively**
when `owned_doc_refresh`/`consented_host_config` mutators land at 3.x.** It keeps the action
self-describing (faithful to §7 + the §23 NexusOps `ActionPlan` serialization), is **additive**
(absent → `None`; existing contentless intents still validate — backward-compatible), and **does not
weaken** the Key-safety-#4 invariant (`perform` still re-validates the allowlist).
**→ GO GREEN on Commit-1's schema-snapshots against Option C — no further sign-off needed on the
payload shape.** This is a shared-frozen-contract change → a **cross-track Finding** (additive +
backward-compatible, so NO premature cross-track interrupt — parallel tracks pick it up on their next
main-pull; providers via the planned spine-5.3→main handshake). The orchestrator writes the §7
Appendix-A growth (integration-routed) + the `core/CLAUDE.md` cross-doc row hot at round close.

## Acceptance criteria (what "done" means)

### Commit 1 — ★SAFETY 2.S (HostPort runtime proof) — OWN COMMIT, security-reviewer mandatory
- [ ] **Real `StandaloneHost`** in `core/ports/host.py` conforms to the `HostPort` Protocol (`isinstance` runtime-checkable): `capabilities()` returns its configured closed allowlist; `authorize` is **fail-closed** (capability ∉ allowlist → `HostDenied`, empty allowlist denies all); `perform` executes ONLY an authorized action AND **re-validates the capability allowlist** (defense-in-depth — a forged `authorized=True` for a non-allowlisted capability is still `HostDenied`). The 1.4a capability-recheck was pinned only on `FakeHost`; pin it on the REAL host now.
- [ ] **`OWN_STORE_WRITE` perform handler** writes `payload.content` to `<root>/payload.rel_path` **atomically** (write temp + `os.replace` rename — the no-half-swap primitive; both FS mutators live in `host.py`, the sole allowlisted file). Returns `HostResult(ok=True)`. **Write-target containment** (LESSON 14): `rel_path` is rejected (`HostDenied`) if absolute, contains a `..` segment, or escapes the project-brain root — containment runs on the resolved realpath.
- [ ] **Hardened static tripwire** (`test_inv_allowlist_no_mutation_outside_hostport` upgraded) catches the **1.4a residuals**: (a) **module-aliasing** (`import os as _os; _os.remove(...)`), (b) **getattr/dynamic-dispatch** resolution (`getattr(os, "remove")(...)`), and (c) **session-state writes** — `os.environ[...] = `, `os.environ.update/pop/setdefault`, `os.putenv`/`os.unsetenv` (Key-safety-#4 covers fs/git/**external/session** state). Still GREEN over all `core/` modules except `host.py`.
- [ ] **Runtime per-mutator proof:** a deterministic test drives `StandaloneHost.perform(OWN_STORE_WRITE, payload)` against a tmp root and asserts the file landed *and* that `perform` is the path it went through (a recording `StandaloneHost` subclass / spy captures performed actions). Combined with the hardened static scan (no mutator escapes any non-`host.py` module), this is the runtime upgrade of the 1.4a static-only tripwire.
- [ ] `StoreWritePayload` (per the owner-gated default) is `frozen=True`, `extra="forbid"`; `rel_path` `IdentityStr`; `content` `TextStr` (or `bytes` — flag at 2.5). `HostIntent`/`HostAction` carry it optionally (absent → `None`).
- [ ] **Cross-doc invariant flagged at Step 9** (§7 contract growth — orchestrator writes the rows): the `HostIntent`/`HostAction` schema-snapshots in `test_host.py` update; the §7 Appendix-A row + `core/CLAUDE.md` cross-doc row grow the payload note. **§2.5-seam shared safety contract → also a cross-track Finding** (the orchestrator notifies the lead).

### Commit 2 — 2.4 (`add` ingest orchestration), security-reviewer mandatory
- [ ] `add(root, *, host, embedder, clock, idgen, redactor, ...)` in `core/ingest/pipeline.py` runs the full pipeline: `discover` → `classify` → `chunk_docs`/`chunk_code` (dispatched on `doc_or_code`) → **`redact(text, Sink.PERSIST)` before embed** (forbidden-pattern #2 pinned at the pipeline) → assemble frozen `Chunk`+`Anchor` (vector ← `FakeEmbeddingProvider`, `chunk_id` ← `idgen`, `created_at` ← `clock`, `content_hash`/`last_resolved_sha`/`generation`/`register` per the §8 chunk-schema; anchor span from the `ChunkDraft`). Returns the assembled records.
- [ ] **Manifest written via the chokepoint:** `add` builds a `ProjectManifest` (DERIVED projection; `artifacts` = one `ManifestArtifact` per ingested source unit; `chunker_version`/`embedding_model`/`dimension` stamped from the recipe), serializes it, and writes it to `<root>/.project-brain/manifest.json` **only** through `host.authorize`→`host.perform(OWN_STORE_WRITE)` — NEVER a raw FS call (the hardened static tripwire over `pipeline.py` proves this).
- [ ] **Idempotent re-add:** running `add` twice on an unchanged repo produces an identical manifest (artifacts deduped/keyed on `ManifestArtifact.content_hash` of the **raw source unit**); modifying a file then re-adding updates that artifact's `content_hash` (update, never append-duplicate).
- [ ] **R-PARTIAL:** a doc-less / empty repo yields a manifest with `artifacts=()` (no crash; `ProjectManifest` allows `()`). A **single malformed file does not abort the repo** — the per-file error boundary skips/quarantines it and ingests the rest.
- [ ] **CONTENT sanitization (the consuming phase, LESSON 16):** pre-redaction **NUL/C0/DEL** and **Trojan-Source bidi/control** chars in a source file are stripped/quarantined at the file boundary (they currently hard-reject at `ChunkDraft`/`Chunk` `TextStr` and would abort a file). The carry-forward pin `test_chunk_docs_nul_byte_raises_at_boundary` is satisfied by the 2.4 boundary catching that raise and degrading to skip — **not** by loosening `TextStr`.
- [ ] **Atomic / no half-swap:** a failure mid-`add` leaves no partial manifest (temp-write + atomic rename via the host); a pre-existing manifest is retained on failure.
- [ ] **Reachability:** `discover`/`classify`/`chunk_docs`/`chunk_code`/`CatchableSetRedactor` are now reachable from `add` (the 2.1/2.2/2.3 deferral closes). CLI `nexus add` wiring is **Phase 5** (declared below).
- [ ] `/preflight` clean (ruff · format · `mypy .` · pytest); **no new runtime dependency** (flag immediately if you reach for one). `pip-audit` is absent in-env — that's the Phase-2-EXIT gate's concern (`/phase-exit 2`), not this slice.

## Wiring / entry point (Step 7.5)
**Commit 1:** `StandaloneHost` is wired as the mutation chokepoint that **Commit 2's `add` calls** — the production caller is `pipeline.add`. The runtime proof test + the hardened tripwire are live entry points this slice lands.
**Commit 2:** `core/ingest/pipeline.py::add` is the orchestration entry point. Its production user-facing caller is the **`nexus add <repo>` CLI — Phase 5 (§15); `none — CLI wiring lands in Phase 5`.** Within this slice `add` is the real caller that wires the 2.1/2.2/2.3 pure functions + the redactor + the `StandaloneHost` into one path (closing their declared reachability deferral). Confirm at Step 7.5 that `discover`/`classify`/`chunk_*`/`redact`/`host.perform` are each invoked from `add`, not only from tests.

## Files expected to touch
**New:**
- `core/ingest/pipeline.py` — the `add` orchestration (Commit 2).
- `core/tests/ingest/test_pipeline.py` — 2.4 unit/integration tests (Commit 2).
- `core/tests/ingest/test_inv_allowlist_runtime.py` *(or extend `test_host.py`)* — the runtime per-mutator proof + add-routes-via-perform (split across commits; flag your placement at 2.5).

**Modified:**
- `core/ports/host.py` — real `StandaloneHost` adapter + `StoreWritePayload` + optional `payload` on `HostIntent`/`HostAction` (Commit 1).
- `core/tests/ports/test_host.py` — `StandaloneHost` conformance + capability-recheck + atomic-write + path-escape + **hardened tripwire** (aliasing/getattr/session-state) + updated Intent/Action schema-snapshots (Commit 1).
- `core/model/manifest.py` — **only if** a field is genuinely required (see Step-2.5 Q3); default expectation is **no change** (the frozen 12+5-field shape suffices). A field add is a cross-doc invariant change (flag at Step 9).

If implementation needs files/deps beyond this list, **flag at Step 2.5** before GREEN.

## RED test outline (Step 2)

### Commit 1 — 2.S (`core/tests/ports/test_host.py` + runtime test); tag each `# spec(§7)` / `# spec(§14)` / `# spec(§4)`
1. **`test_standalone_host_conforms_to_protocol`** — Asserts: real `StandaloneHost` `isinstance`s `HostPort`. Why: §7 LESSON 1 fidelity on a safety seam.
2. **`test_standalone_host_authorize_fail_closed`** — Asserts: capability ∉ allowlist → `HostDenied`; empty allowlist denies all. Why: §4 #3 / Key-safety-#4 fail-closed (on the REAL host, not just Fake).
3. **`test_standalone_host_perform_capability_recheck`** — Asserts: a forged `authorized=True` for a non-allowlisted capability → `HostDenied` on `StandaloneHost.perform`. Why: LESSON 9 + the 1.4a residual (only `FakeHost` pinned this).
4. **`test_standalone_host_own_store_write_atomic`** — Asserts: `perform(OWN_STORE_WRITE, payload)` writes `content` to `<root>/rel_path`, atomically (temp+rename), returns `HostResult(ok=True)`. Why: §5/§8 manifest write; no-half-swap primitive.
5. **`test_standalone_host_rejects_path_escape`** — Asserts: `rel_path` absolute / `..`-segment / root-escaping → `HostDenied`. Why: §14 / LESSON 14 write-boundary containment.
6. **`test_store_write_payload_schema_snapshot`** — Asserts: `set(StoreWritePayload.model_fields) == {"rel_path","content"}`; `frozen`+`extra="forbid"`. Why: §7 frozen-shape pin (owner-gated default).
7. **`test_host_intent_payload_schema_snapshot`** — Asserts: `set(HostIntent.model_fields) == {"capability","summary","payload"}`; absent payload → `None`. Why: §7 schema-snapshot UPDATE (cross-doc change — flag at 9).
8. **`test_host_action_payload_schema_snapshot`** — Asserts: `set(HostAction.model_fields) == {"capability","summary","authorized","payload"}`. Why: §7 schema-snapshot UPDATE.
9. **`test_inv_allowlist_tripwire_catches_module_aliasing`** — Asserts: the scanner flags `import os as _os; _os.remove(...)`. Why: §14 1.4a residual (a).
10. **`test_inv_allowlist_tripwire_catches_getattr_dispatch`** — Asserts: the scanner flags `getattr(os,"remove")(...)` / dynamic dispatch. Why: §14 1.4a residual (b).
11. **`test_inv_allowlist_tripwire_scans_session_state`** — Asserts: the scanner flags `os.environ[k]=`, `os.environ.update(...)`, `os.putenv/unsetenv`. Why: §14 / Key-safety-#4 session-state mutation (new axis).
12. **`test_inv_allowlist_no_mutation_outside_hostport`** *(existing, must stay GREEN)* — Asserts: hardened scan over all `core/` except `host.py` finds zero mutators. Why: §4 #3 the chokepoint holds.
13. **`test_standalone_host_runtime_proof`** — Asserts: a recording `StandaloneHost` shows the only FS write went through `perform`; the file landed. Why: §14 runtime per-mutator upgrade.

### Commit 2 — 2.4 (`core/tests/ingest/test_pipeline.py`); tag each `# spec(§8)` / `# spec(§5)`
14. **`test_add_empty_repo_writes_empty_manifest`** — Asserts: doc-less repo → manifest with `artifacts=()`, no crash. Why: §8 R-PARTIAL.
15. **`test_add_full_pipeline_assembles_chunks`** — Asserts: a doc + a code file → `add` returns assembled frozen `Chunk`+`Anchor` (Fake vector/ids/clock); each chunk's text is post-redaction. Why: §8 stage order; forbidden-#2.
16. **`test_add_redacts_before_embed`** — Asserts: a file with a `ghp_…` secret → the assembled chunk text is redacted (redact ran at the persist sink before the Fake embed). Why: §18/§8 + Key-safety-#2 at the pipeline.
17. **`test_add_writes_manifest_via_hostport`** — Asserts: `manifest.json` lands at `<root>/.project-brain/`, written via `host.perform(OWN_STORE_WRITE)` (recording host shows the call); no raw FS write. Why: §5/§14 chokepoint.
18. **`test_add_manifest_artifacts_derive_from_files`** — Asserts: one `ManifestArtifact` per ingested unit with correct `path`/`content_hash`/`doc_type`/`producer`/`ownership`; recipe fields stamped. Why: §5 derived projection.
19. **`test_add_idempotent_reingest`** — Asserts: `add` twice on an unchanged repo → identical manifest (no dup artifacts). Why: §8 `add` idempotent.
20. **`test_add_idempotent_after_change`** — Asserts: edit a file, re-add → that artifact's `content_hash` updates (no append). Why: §8 update-not-duplicate.
21. **`test_add_partial_skips_malformed_file`** — Asserts: a NUL/C0/DEL file is skipped/quarantined; the rest ingests; `add` does not raise. Why: §8 R-PARTIAL + LESSON 16 (satisfies the `…nul_byte_raises_at_boundary` carry-forward at the boundary).
22. **`test_add_sanitizes_trojan_source_bidi`** — Asserts: bidi/control chars are stripped/quarantined before chunking. Why: LESSON 16 content sanitization (consuming phase).
23. **`test_add_atomic_no_half_swap_on_failure`** — Asserts: an induced mid-`add` failure leaves no partial manifest; a prior manifest is retained. Why: §8 temp-generation/no-half-swap.
24. **`test_add_routes_all_mutation_via_perform`** *(the 2.S runtime proof via `add`)* — Asserts: running `add`, the manifest write is the only FS mutation and it is observed through `host.perform`. Why: §14 runtime INV-allowlist with the real first mutator.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** **`HostIntent` + `HostAction` grow `payload` + new `StoreWritePayload` (§7).** This is a **cross-doc invariant change on a frozen ★safety §2.5-seam contract** → flag at Step 9 categorized. The orchestrator writes the §7 Appendix-A row + the `core/CLAUDE.md` `HostPort` cross-doc row hot, AND raises a **cross-track Finding** to the lead (shared safety contract growth). The schema-snapshot tests (#6/#7/#8) are authored in THIS cycle and reviewed at 2.5.
- **`ProjectManifest`/`ManifestArtifact`:** **default = no field change** (frozen guard holds, like 2.1/2.2/2.3). If a field is genuinely required, it's an additional cross-doc invariant change (flag at 9) + its own schema-snapshot update — do NOT add speculatively.
- **§2.5-seam schema-snapshot:** §7 `HostIntent`/`HostAction` ARE §2.5-seam-crossed (the `HostPort` fan-in) → the snapshot tests (#7/#8) are **required in this cycle** (they already exist; this updates them).
- **`ChunkDraft`/`Chunk`/`Anchor`:** consumed, not changed — `ChunkDraft`→`Chunk` assembly is the LESSON-20 "assemble where context exists" step finally executing; no contract edit.

## Things to flag at Step 2.5
1. **`StoreWritePayload.content`: `str` (`TextStr`) or `bytes`?** Manifest JSON is text, but a future `own_store_write` (a LanceDB fragment) is binary. Default vote: **`TextStr` now** (manifest is JSON text; widen to `bytes`/union when 3.1's binary write lands — additive). Ping back if you want `bytes` now to avoid a later widen.
2. **Where does the runtime proof + the add-routes-via-perform test live** (extend `test_host.py` vs a new `test_inv_allowlist_runtime.py`)? Default vote: **the pure-host runtime proof (#13) in `test_host.py`; the add-flow proof (#24) in `test_pipeline.py`** (it needs `add`). Keeps each commit's tests with its code.
3. **Does `add` need any new `ProjectManifest` field?** Walk the §5/§8 recipe against the existing 12 fields before adding anything. Default vote: **no change** — `chunker_version`/`embedding_model`/`dimension`/`ingested_from_sha`/`artifacts`/`policy_path`/`staleness_pointer` already cover it; `ingested_from_sha`/`lance_version_tag` get a v0 placeholder (real git-SHA/version-tag wiring is Phase 3 with LanceDB). Flag a concrete gap if you find one.
4. **`ingested_from_sha` / `lance_version_tag` in Phase 2 (no LanceDB yet).** Default vote: **v0 deterministic placeholder** (e.g. a content-derived marker via the recipe, NOT `git` shelling — that'd be an FS/external read; keep `add` host-mediated). Real version-tag mirroring lands at 3.1. Note it as a Phase-3 carry.
5. **Idempotency key granularity.** Default vote: **`ManifestArtifact.content_hash` of the raw source unit** (per-file), so an unchanged file is byte-identical across re-adds and a changed file flips exactly one artifact. Chunk-level dedup is Phase 3 (LanceDB tombstone+replace, §12).
6. **`add` failure-injection for the no-half-swap test (#23).** Default vote: **inject via a host whose `perform` raises** (or a Fake embedder that raises on the Nth chunk) — deterministic, no real I/O fault needed.

## Dependencies + sequencing
- **Depends on:** 2.1 (`discover`/`classify`), 2.2 (`chunk_*`), 2.3 (`CatchableSetRedactor`) — all landed; 1.4a (`HostPort` freeze + static tripwire) — landed.
- **Internal order:** Commit 1 (2.S) BEFORE Commit 2 (2.4) — `add` writes through the chokepoint 2.S builds.
- **Blocks:** **Acceptance(2)** (Phase 2 does NOT close without the 2.S runtime proof) → `/phase-exit 2`. Phase 3.1 (LanceDB writer extends the same `HostPort.perform` proof + real version-tag/embedding; reuses `add`'s pipeline). The providers track's cloud-egress guard reconciles against the same Redactor iface + `Sink` (owner directive — no change here, just keep the redactor call sink-parameterized as it already is).

## Estimated commit count
**2.**
- **Commit 1 — ★SAFETY (2.S):** `feat(ports): real StandaloneHost + §14 INV-allowlist runtime proof + tripwire hardening (2.S)` — the cardinal Key-safety-#4 proof; **own commit, never bundled with 2.4** (template safety rule). security-reviewer mandatory.
- **Commit 2 — (2.4):** `feat(ingest): add orchestration — idempotent, R-PARTIAL, redact-before-embed, manifest-via-HostPort (2.4)` — the pipeline wiring the chunk/redact stages + the chokepoint. security-reviewer mandatory (touches the redact-before-embed + host-write paths).

(Both are individually ≥30 lines + the safety pin demands separation — this is the template's "do NOT bundle into one commit" case, satisfied by 2 commits under 1 brief, exactly the lead's "dedicated surface, don't dilute" instruction.)

## Lessons-logged candidates anticipated
- **Convention candidate** — "the first FS mutator proves the chokepoint at runtime: a recording host + a hardened static scan (aliasing/getattr/session-state) together upgrade a static tripwire to a runtime per-mutator proof."
- **Convention candidate** — "grow a frozen safety contract additively (optional payload, absent→None) so existing wire shapes still validate + snapshots stay green except the intended field."
- **Architecture-doc note candidate** — §8 `add` Phase-2 scope: assembles frozen `Chunk`/`Anchor` against `Fake*` + writes the manifest via `HostPort`; LanceDB embed/persist + real version-tag = 3.1.
- **Future TODO — Phase 3 carry** — real `ingested_from_sha`/`lance_version_tag` from the LanceDB git-SHA version tag; chunk-level tombstone+replace idempotency (§12); `StoreWritePayload` widen to `bytes`/per-capability union at 3.1.

## How to invoke
1. **Read this brief end-to-end** — especially the ⚠ owner-gated decision + the 2-commit structure.
2. Pre-flight: confirm clean tree + suite green, then **`/tdd add_ingest_pipeline_and_hostport_runtime_proof`**.
3. **Step 0 (Restate):** confirm the bundle = 2 commits (2.S first, then 2.4) + security-reviewer on both.
4. **Step 1:** confirm the file list.
5. **Step 2.5:** send the test-design write-up (one `Asserts: <invariant> (§anchor)` per test + the acceptance→test coverage map). **The payload shape is RESOLVED — Option C (locked); go GREEN on Commit-1's schema-snapshots against it.** The only open payload sub-question is Step-2.5 Q1 (`content` `TextStr` vs `bytes`; default `TextStr`).
6. **Step 8:** security-reviewer mandatory on BOTH commits (it is `every-slice` policy regardless; called out here because it's the cardinal safety bundle).
7. **Step 9:** surface the `HostIntent`/`HostAction` §7 growth as a `Cross-doc invariant change` (+ any manifest field if one proved necessary).
