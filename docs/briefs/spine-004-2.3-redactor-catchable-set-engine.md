# /tdd brief — redactor_catchable_set_engine

## Feature
The **catchable-set secret-redaction engine** (Key safety rule #2) — `core/ingest/redactor.py`, implementing the frozen 1.5 `Redactor` Protocol: detect + redact the four catchable secret classes (prefix-token, high-entropy KV, JSON-sensitive-value, env-dump) at all three sinks, pass through the three §18 accepted residuals (git-SHA **zero-tolerance**, adversarial <20-char split, sub-20-char JSON), and **pass the 0.1 fuzz gate** (recall ≥ floor, FP ≤ ceiling, git-SHA FP = 0%) wired as a hard CI gate.

## Use case + traceability
- **Task ID:** 2.3
- **Architecture sections it implements:** `ARCHITECTURE.md §18` (the redaction gate — catchable-set, accepted residuals, three sinks, fuzz-harness-asserted), `ARCHITECTURE.md §8` (the chunk→**redact**→embed pipeline position — redact runs at the persist sink before embed), `ARCHITECTURE.md §16` (per-project `policy.yaml` privacy local|cloud — relevant to the sink-strictness D-A5 question).
- **Related context:** Implements the frozen `Redactor` Protocol + `Sink` alphabet in `core/model/redactor_iface.py` (1.5a). The fuzz rig already exists: `ci/eval/redaction_fuzz/` — `run_harness(redact_fn, sinks) -> dict[Sink, HarnessReport]`, `HarnessReport.gate_pass(recall_floor, fp_ceiling)`, constants `PROPOSED_RECALL_FLOOR=0.95` / `PROPOSED_FP_CEILING=0.05` in `harness.py` (the SSoT). The catchable classes + accepted residuals are enumerated in `ci/eval/redaction_fuzz/types.py` (`SecretClass`, `AcceptedResidualClass`). **`core` must NOT import `ci/`** (core ⊥ ci/, both directions in core code) — the engine lives in `core/ingest/redactor.py`; the GATE (in `ci/`) imports the engine, never the reverse. `FakeRedactor` (prefix-strip double, makes no recall claim) is in `core/testing/fakes.py`.

## ⚠ Owner-gated parameters (D-A5/D-A6) — surface at Step 2.5
The exact recall/FP threshold (**D-A6**) and whether `cloud_egress` redacts MORE strictly than the other sinks (**D-A5/FLAG-4**) are **owner-reserved** and now due at this slice. The orchestrator has escalated them to the owner. **Build the engine against the PROPOSED defaults** (floor 0.95 / ceiling 0.05, **uniform across all three sinks**) and confirm the final numbers at Step 2.5 — they may already be answered by the time you reach it. The frozen iface is sink-parameterized so a uniform engine and a cloud-stricter one are both accommodated; uniform is the v0 default.

## Acceptance criteria (what "done" means)
- [ ] `Redactor` engine class in `core/ingest/redactor.py` satisfies the frozen `core.model.redactor_iface.Redactor` Protocol (`isinstance` runtime-checkable) — `redact(payload: str, sink: Sink) -> str`.
- [ ] **Catchable classes redacted** (each replaced by a fixed secret-free marker): prefix-token (`ghp_`, `github_pat_`, `sk-`, `xox[baprs]-`, `AKIA…`, PEM `-----BEGIN…`, JWT three-segment base64url), high-entropy `KEY=value` / shell-export, JSON sensitive value (key ∈ password/token/secret/api_key/access_key, value ≥ 20 chars), env-dump (multi-line KEY=VALUE).
- [ ] **Accepted residuals pass through UNREDACTED** (§18): a 40/64-char git-SHA hex (**zero-tolerance — redacting one is a cardinal failure**, breaks LanceDB version tag + `last_resolved_sha`), an adversarial <20-char split fragment, a sub-20-char JSON sensitive value.
- [ ] **Behavioral invariants** (frozen-iface contract, all pinned): idempotent (`redact(redact(p,s),s) == redact(p,s)` — the marker never re-triggers), never-raises (empty / NUL / control / very-long / non-ASCII / env-dump input), pure (no network/file I/O), returns `str` for every `Sink`.
- [ ] **Fuzz gate PASSES** as a hard CI gate: `run_harness(engine.redact)` → for every sink `gate_pass(PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING)` is `True`, AND the git-SHA false-positive subclass is exactly 0%. Wired so CI fails on a regression (the rig runs out-of-band under the core uv env; `core` stays import-clean of `ci/`).
- [ ] **security-reviewer mandatory** (safety-critical slice).
- [ ] `/preflight` clean (ruff · format · `mypy .` · pytest); no new runtime dependency (pure-Python).

## Wiring / entry point (Step 7.5)
**Persist-sink wiring lands in 2.4** (the `add` pipeline calls `redact(chunk.text, Sink.PERSIST)` before embed); MCP-egress + hydration-egress wiring land in Phase 8 / Phase 4. **The CI fuzz gate IS a real entry point this slice lands** — `run_harness(engine.redact)` invokes the engine on the full corpus. Name it: the gate-runner in `ci/eval/redaction_fuzz/` (swap the `stub_redactor` for the real engine) is the production-adjacent caller proving the engine works end-to-end. Pipeline persist-sink call: `none — wiring lands in 2.4`.

## Files expected to touch
**New:**
- `core/ingest/redactor.py` — the catchable-set engine implementing the frozen `Redactor` Protocol.
- `core/tests/ingest/test_redactor.py` — unit tests (per class, per residual, behavioral invariants) + the gate-pass assertion.

**Modified:**
- `ci/eval/redaction_fuzz/` — wire the real engine as the gate target (replace/augment `stub_redactor`); add a thin gate-runner if needed. (`ci/` may import `core`; never the reverse.)

If implementation needs files/deps beyond this list, **flag at Step 2.5** before going GREEN. **No new runtime dependency expected** — flag immediately if you reach for one.

## RED test outline (Step 2)
Tests in `core/tests/ingest/test_redactor.py` (tag each `# spec(§18)`):

1. **`test_redactor_conforms_to_protocol`** — Asserts: the engine `isinstance`s the frozen `Redactor` Protocol. Why: §18 implements the 1.5 freeze.
2. **`test_redacts_prefix_tokens`** — Asserts: `ghp_`/`github_pat_`/`sk-`/`xox*`/`AKIA`/PEM/JWT samples are absent from the output. Why: §18 PREFIX_TOKEN class.
3. **`test_redacts_high_entropy_kv`** — Asserts: a high-entropy `API_KEY=<32-char>` value is redacted. Why: §18 HIGH_ENTROPY_KV.
4. **`test_redacts_json_sensitive_value`** — Asserts: `{"password": "<≥20-char>"}` value redacted; key preserved. Why: §18 JSON_SENSITIVE_VALUE.
5. **`test_redacts_env_dump`** — Asserts: a multi-line env dump has its secret values redacted. Why: §18 ENV_DUMP.
6. **`test_git_sha_passthrough_zero_tolerance`** — Asserts: 40- AND 64-char git-SHA hex (lower + UPPER) survive **verbatim** for all three sinks. Why: §18 / D-14 cardinal residual (redacting one is the failure).
7. **`test_adversarial_short_split_passes`** — Asserts: a sub-20-char fragment is not redacted. Why: §18 accepted residual.
8. **`test_sub_20_char_json_passes`** — Asserts: `{"token": "short"}` (<20) is not redacted. Why: §18 accepted residual (FP floor).
9. **`test_idempotent`** — Asserts: `redact(redact(p,s),s) == redact(p,s)` across classes (marker is secret-free, doesn't re-trigger). Why: frozen-iface idempotence.
10. **`test_never_raises`** — Asserts: empty / NUL / C0-control / 100KB / non-ASCII / env-dump inputs all return a `str`, no exception. Why: frozen-iface never-raises.
11. **`test_pure_no_io`** — Asserts: no network/file I/O (monkeypatch/`assert` no side effects). Why: safety rule #6 + frozen-iface purity.
12. **`test_all_three_sinks_return_str`** — Asserts: every `Sink` returns a `str`. Why: frozen-iface sink-total.
13. **`test_marker_contains_no_secret`** — Asserts: the redaction marker contains none of the original secret characters. Why: §18 the redaction actually removes the secret.
14. **`test_fuzz_gate_passes_all_sinks`** — Asserts: `run_harness(engine.redact)` → `report.gate_pass(PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING)` True for all three sinks AND git-SHA FP subclass == 0%. Why: §18 the catchable-set envelope (the acceptance gate). *(This test imports the rig from `ci/`; it lives in the test file which is allowed to reach `ci/`, but the engine module must not.)*

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes: none.** The engine implements a frozen behavioral Protocol — no new contract, no field. (`Redactor`/`Sink` already frozen.)
- **Cross-doc table:** the `Redactor` row currently says "the *engine* is Phase-2.3 `core/ingest/redactor.py`" — at Step 9 flag that the engine has landed (the orchestrator updates the row's status note + may add an §18 architecture-doc-note recording the marker format + the gate-wiring). Integration-routed.
- **Owner-gate outcome:** record the D-A5/D-A6 resolution (final threshold + uniform-vs-cloud-stricter) into §18 + the `Redactor` row — orchestrator writes hot once the owner answers.

## Things to flag at Step 2.5
1. **⚠ D-A5/D-A6 (owner-gate, #1 priority).** Confirm the final recall/FP threshold + whether `cloud_egress` is stricter. Default (build against this): PROPOSED **0.95 / 0.05, uniform across sinks**. If unanswered when you reach Step 2.5, proceed on the default and I'll route the owner's final number hot before the gate is locked.
2. **Redaction marker format.** My default: a **fixed secret-free sentinel** carrying the class, e.g. `‹redacted:prefix_token›` (or a plain `[REDACTED]`) — must contain nothing secret-shaped so idempotence holds (the marker must not match any detector). Confirm the exact token.
3. **"Quarantine high-confidence-unsafe" semantics.** The plan task says "quarantine"; the frozen iface returns only `str` (no separate quarantine channel). My default: **quarantine == aggressive redaction** (replace the unsafe span/payload with the marker) — there is no out-of-band quarantine output in the frozen contract. Confirm this reading (a true quarantine channel would be a contract change = a Finding).
4. **High-entropy detection (Shannon) — threshold + min-length.** My default: Shannon entropy over the candidate value with a **≥20-char min-length floor** (below which the §18 sub-20 residual + FP concerns dominate) and a tuned bits/char threshold; allowlist git-SHA/ULID/UUID shapes BEFORE the entropy test so they pass through. Confirm the floor + that the allowlist precedes entropy.
5. **CONTENT sanitization is OUT of this slice.** Trojan-Source bidi/zero-width in `chunk.text` (LESSON 14/16) AND the 2.2a NUL/C0/DEL finding are **content** concerns, distinct from **secret** redaction. My default: 2.3 is the secret engine only; content-control sanitization + the file-level malformed-content R-PARTIAL boundary land at **2.4 (pipeline)** / a focused sibling — keeps this safety-critical commit single-purpose. Confirm we're NOT folding them in here.
6. **`ci/` gate wiring shape.** My default: add a gate-runner module/test in `ci/eval/redaction_fuzz/` that imports the real `core.ingest.redactor` engine and asserts `gate_pass`; the engine module stays `ci/`-free. The `ci.Sink` (str-enum) and `core.Sink` (StrEnum) share values so the callable is compatible; confirm the mypy/typing seam (the rig runs under the core uv env out-of-band). Note any `ci/` enhancement (FLAG-1 encoding-aware oracle · FLAG-2 JWT shape-matcher in the corpus · FLAG-3 binary corpus) you touch vs. defer.

## Dependencies + sequencing
- **Depends on:** 1.5a (`Redactor`/`Sink` frozen — landed), 0.1 (the fuzz rig — landed). **Independent of 2.1/2.2** (does not consume chunks; operates on payload strings) — which is why it runs now while 2.2b is owner-blocked.
- **Blocks:** 2.4 (the `add` pipeline calls `redact()` at the persist sink before embed). Also reused at MCP-egress (Phase 8) + hydration-egress (Phase 4).

## Estimated commit count
**1 — and it is its OWN commit, never bundled** (safety-critical pin per the bundling rules: Key safety rule #2). The engine + its tests + the gate wiring are one logical safety unit. security-reviewer mandatory.

## Lessons-logged candidates anticipated
- **Convention candidate** — "An allowlist (git-SHA/ULID/UUID) runs BEFORE the entropy detector, never after — an entropy filter that sees a SHA first will redact it (the cardinal §18 residual failure)."
- **Architecture-doc-note candidate** — the marker format + the gate-wiring + the D-A5/A6 resolution into §18.
- **Future TODO — operational** — FLAG-1 encoding-aware oracle (base64/url-encoded secret detection); FLAG-3 binary-payload corpus; per-provider cloud-egress strictness if D-A5 goes that way.

## How to invoke
1. **Read this brief end-to-end** — especially the D-A5/D-A6 owner-gate + the §18 accepted-residual zero-tolerance on git-SHA.
2. **`/tdd redactor_catchable_set_engine`** (the spine implementer session is already oriented).
3. **Step 0 (Restate)** — confirm against the Feature line.
4. **Step 1 (Identify files)** — confirm `core/ingest/redactor.py` + the test + the `ci/` gate wiring.
5. **Step 2.5** — send the test-design write-up + acceptance→test coverage map with answers to the six design questions; **flag D-A5/D-A6 explicitly** (default = PROPOSED 0.95/0.05 uniform).
6. **Step 8** — security-reviewer mandatory (safety-critical).
7. **Step 9 (summarize)** — surface the marker format, the gate result (per-sink recall/FP numbers), the D-A5/A6 resolution, and any `ci/` enhancements touched/deferred.
