# Phase 1 Phase-Exit Security Review — Contract Freeze (Fork Gate)

- **Policy:** `phase-boundary` (dispatched at `/phase-exit`). Review surface = the phase's
  accumulated `track/contract` branch diff. Because the whole of `core/` was built in this phase,
  the surface over-approximates to the **entire current `core/` contract layer** (interfaces +
  Pydantic models + Fake doubles + the static INV-allowlist tripwire) — acceptable; noted per the
  phase-boundary spec.
- **Worktree:** `/Users/dreddy/Documents/Dev/AI-tools/ai-engineering-control-plane/project-brain-contract`
  · branch `track/contract` @ `063281b` (converged merge).
- **Nature of surface:** Phase-1 CONTRACT FREEZE — **no live engine**. No live FS/git/network/model
  execution exists yet. Assessment is of the **contract SHAPES**, the **fail-closed seam behavior of
  the Fakes**, and the **static INV-allowlist tripwire**. Two runtime safety proofs are correctly
  deferred as tracked fork obligations (D-A13, D-A14) — see "Correctly-deferred", below.
- **Verification depth:** beyond reading, the safety-critical controls were exercised empirically
  with the project venv (Pydantic 2.13.4 / Python 3.12.13): full suite `232 passed`; `IdentityStr`
  unicode-property rejection, the §14 `get_file` allow-list, and `HostAction` strict-bool stamping
  all confirmed live (not paper).

---

## Invariant pass — Key safety rules (root CLAUDE.md), all PASS

### #1 Grounding gate (§10) — `model/anchor.py`, `model/provenance.py`, `model/evidence.py` — PASS
- `ProvenancePacket` is `frozen + extra="forbid"`; all collection fields are `tuple` (LESSON 8 deep
  immutability — list input coerces to an immutable tuple), required-but-empty-valid so an
  ungrounded/flagged answer carries `citations=()` + `evidence=()`. `evidence` composes the frozen
  `EvidenceRef` by value (nested parse-don't-trust). A re-grounded answer mints a NEW packet — no
  in-place mutation path exists (frozen enforced; `test_*` pins post-construct mutation raises).
- `Anchor` is frozen + closed, carries `state: AnchorState` (closed 5-value alphabet, `deleted`
  correctly excluded as a row-lifecycle event), `confidence ∈ [0,1]`, and a `model_validator`
  rejecting a backwards span (`end < start`). The gate-serves-only-on-`state==live` law lives at the
  Phase-4 producer; the contract carries the typed primitive faithfully. `citations` are file:line
  TOKENS (`IdentityStr`), not embedded `Anchor`s — consistent with §10 "file:line[]" and the
  span-existence post-validation being producer-owned. No claim-emission path exists in this layer,
  so there is nothing to bypass; the trust record's shape is sound.

### #2 Redaction-before-embed (§18) — `model/redactor_iface.py` — PASS
- Closed 3-sink `Sink` StrEnum (`persist` / `mcp_egress` / `cloud_egress`), pinned by
  `test_sink_values`. Behavioral `@runtime_checkable Protocol` `redact(payload, sink) -> str`.
- Contract documents (and `FakeRedactor` upholds) the load-bearing invariants: idempotent,
  never-raises (DoS defense at the boundary — verified against empty/NUL+control/100K/non-ASCII/
  env-dump payloads), pure (no network / no file I/O — safety rule #6), and **git-SHA passthrough**
  (40/64-char hex survive byte-for-byte, case-insensitive, all three sinks — §18/D-14 zero-tolerance,
  verified). The recall/FP envelope is correctly NOT baked into the interface or Fake — it is the
  Phase-2.3 fuzz-CI gate's single source of truth; the module correctly does not import `ci/`.
  Per-sink strictness (D-A5/D-A6) is owner-deferred and the signature accommodates both — no premature
  behavior frozen.

### #3 Keychain-only secrets (§18) — `ports/secrets.py` — PASS
- `SecretRef` is frozen + `extra="forbid"` and carries ONLY `{service, account}` — both `IdentityStr`.
  `test_secret_ref_carries_no_secret` proves a `secret`/`value`/`password`/`token` kwarg is rejected.
  `test_fake_secretstore_no_leak` proves plaintext never appears in `repr`/`str`/`model_dump` of the
  ref OR the store. `resolve()` of an unknown ref fails CLOSED with `SecretNotFoundError` — never a
  silent empty string (the subtle auth footgun is explicitly closed, §25). Plaintext exists only as
  the transient `resolve` return; the no-plaintext-in-logs runtime enforcement is correctly Phase-2.

### #4 HostPort mutation chokepoint (§4/§7/§14) — `ports/host.py` + INV-allowlist tripwire — PASS
- Closed 3-value `HostCapability` allowlist (pinned by membership snapshot). `authorize(intent)`
  fails CLOSED (`HostDenied`) on any capability outside the host's set; empty allowlist denies
  everything (most-restrictive default).
- **Defense-in-depth confirmed:** the `authorized` stamp is a forgeable bool (no private ctor in
  Python), and `perform` does NOT trust it alone — `FakeHost.perform` re-validates `action.capability
  ∈ capabilities()` and raises `HostDenied` even when `authorized=True` is FORGED for a
  non-allowlisted capability (`test_perform_denies_unallowlisted_capability_even_if_authorized`).
  `authorized` is `StrictBool` (default `False`), so a lax `1`/`"true"`/`"on"` is rejected at parse
  (`test_host_authorized_strict`) — a hand-built action is fail-closed unauthorized. `FakeHost`
  upholds the SAME fail-closed contract a real host must (LESSON 1 — no looser fake on a safety seam).
- **INV-allowlist AST tripwire** (`test_inv_allowlist_no_mutation_outside_hostport`): walks every
  `core/` module (excl. `tests/`, `__pycache__`, dot-dirs), asserts NO FS/git mutation primitive
  appears outside `ports/host.py`. Covers qualified `os`/`shutil`/`subprocess` mutators, bare
  Path-mutator methods, write-mode `open()` (builtin AND attribute form), `import subprocess`, and
  `from os/shutil import <mutator>`. Passes now (nothing in `core/` mutates — independently confirmed:
  the only `import os` in non-venv `core/` is the test's own scanner). The scan's two
  self-documented blind spots (aliased `import os as _os`, `getattr` dynamic dispatch) are
  **not exercised anywhere in current `core/`** (independently scanned — zero hits) and are tracked
  for Phase-2 hardening under **D-A13 / Task 2.S** — see "Correctly-deferred". For the frozen-contract
  surface the tripwire is sound.

### #5 Single embedding model / generation (§5) — `model/stamp.py` — PASS
- `StoreVersionStamp` deliberately carries **NO SHA field** — the git-SHA is the LanceDB version tag
  (the sole canonical SHA home); a second SHA home could disagree and break source-of-truth. Frozen +
  `extra="forbid"` rejects a stray `sha=`/second-SHA kwarg. `embedding_model` is the terminal
  source-of-truth generation identity gating "one model per generation" + the federation gate.
  `index_built_at` is required-no-default (writer injects via the `Clock` seam — never inline wall
  clock). The blue-green-on-model-switch + single-writer LAWS live in the Phase-2/3 writer; the
  contract's terminal stamp shape supports them. `EmbeddingProvider.model_version` (providers.py) is
  the matching §5 generation-identity surface.

### #6 No phone-home (§19) — `ports/observability.py` — PASS
- `ObservabilitySink.emit(event) -> None` is instrumented-but-silent; `ObsEvent` frozen + closed.
  `FakeObservabilitySink` records LOCALLY only (no network), `test_obssink_emit` asserts local
  capture. The OTel real sink is off-by-default + local-only at Phase-2 (D-22) — no outbound
  endpoint, analytics, or crash beacon exists anywhere in the contract layer (confirmed: no network
  I/O in any `core/` module).

---

## General hardening pass

### §14 MCP ingress positive-allow-lists — `model/mcp_contract.py` — PASS (strongest control)
- The external untrusted-caller boundary uses POSITIVE allow-lists, never deny-lists (LESSON 10).
- `_validate_get_file_path` empirically rejects (verified live): `../` traversal (leading + mid-path),
  absolute (`/etc/passwd`), drive (`C:\…`), NUL, fullwidth-tilde homoglyph (`～`), unicode ligatures
  (`ﬁ`/`ﬀ`), bidi override (`U+202E`), whitespace, shell metachar (`$HOME`), glob (`*.py`),
  collapsed-traversal (`a//b/../../c`) — while accepting legit relative ASCII paths. Non-ASCII is
  deliberately rejected at the frozen boundary (smallest attack surface; widening is a Phase-8
  additive option). Canonicalize-against-real-root CONTAINMENT is correctly Phase-8.2 (needs the
  resolved root, unavailable here).
- Bounds are named constants (`MAX_TOP_K=100`, `MAX_QUERY_LEN=4096`, `MAX_RESPONSE_ITEMS=500`) pinned
  by `test_bounds_constants` so a future LOOSENING is a visible, test-breaking change; `top_k` is
  `Field(ge=1, le=MAX_TOP_K)`; `_BoundedQuery` is strip+non-empty+capped. `McpResult.items` is capped
  via `Field(max_length=...)` — over-bound RAISES (fail-loud backstop on a forgotten Phase-8.2
  truncation). All param models are frozen + `extra="forbid"` (incl. `ListProjectsParams` rejecting
  any kwarg). DoS surface at the boundary is bounded.
- **Discriminated `PolicyDenied` marker:** a returned VALUE (`denied: Literal[True]`), never a raised
  exception — denial can't pose as a tool-failure NOR as a non-deny. `McpToolResult = McpResult |
  PolicyDenied`. Sound marker-not-error design.

### §16 policy fail-CLOSED — `model/policy.py` — PASS
- Every section optional with a most-restrictive default: `privacy=LOCAL`, and `mcp.expose` /
  `federation.visible` / `sessions.consent` all `StrictBool=False`. An empty `policy.yaml`/`{}`
  parses to the LEAST-permissive posture. Strict parser (parse-don't-trust): a bad enum value or
  unknown key RAISES rather than silently coercing — the fail-OPEN "silently-accepted bad privacy
  marker" is explicitly rejected. Nested sub-models coerce from dict + are deep-frozen. The fail-SOFT
  "malformed → most-restrictive instead of crash" fallback is correctly the Phase-2/3 LOADER's job,
  not this frozen schema.

### §4 parse-don't-trust hardening (1.6) — `_types.py` — PASS (verified live)
- `IdentityStr` = strip + non-empty + `max_length` + unicode-property pattern
  `^[^\p{Cc}\p{Cf}\p{Zl}\p{Zp}]+$`. **Critically verified live** (Pydantic uses the Rust `regex`
  crate, which honors `\p{}` — stdlib `re` does NOT, so this had to be confirmed not-dead): it
  rejects bidi override U+202E, zero-width U+200B, NUL, line-sep U+2028, C1 NEL U+0085, and other C0
  controls, while accepting file:line tokens (`src/foo.py:42`), non-ASCII filenames (`café/…`), and
  span syntax (`10:5-12:8`). The homoglyph/bidi/invisible-char injection class is genuinely closed at
  the identity boundary. `TextStr` allows inline `\t\n\r` + multilingual (incl. format chars — rich
  content) but rejects NUL/C0/DEL/C1. `StrictBool` is applied to every safety/security/lifecycle
  bool (`HostAction.authorized`, `HostResult.ok`, all policy opt-ins) — lax truthy coercion can't
  flip a safety flag. `RerankResult` uses `allow_inf_nan=False` (NaN/inf would poison sort + RRF).
- The 11 duplicated string aliases are consolidated into ONE shared definition importable by both
  `model/` and `ports/` without a forbidden cross-sibling import (§2.5 DAG — cross-cutting layer).
  Trojan-Source CONTENT sanitization in `chunk.text` (source code) is correctly a Phase-2 ingest
  concern, not a frozen-contract hard-reject that would refuse legit multilingual content (LESSON 14).

---

## Correctly-deferred runtime proofs (TRACKED fork obligations — NOT findings)

These are explicitly out of scope for a contract-only freeze and are tracked, not gaps:

- **D-A13 / Task 2.S (Phase 2):** the §14 INV-allowlist FULL runtime proof + the real `StandaloneHost`
  per-capability `perform` handlers. The Phase-1 tripwire is a STATIC AST scan seeded now (passes
  because nothing mutates yet); it matures into the full runtime enforcement when mutation-capable
  callers exist. The scan's aliased-import / `getattr` blind spots are part of this Phase-2 hardening
  and are not currently exercised anywhere in `core/`.
- **D-A14 / Task 4.2 (Phase 4):** CodeGraph CLI argv-hardening for the un-allow-listable
  query/symbol args. At this layer they are bounded strings (`_BoundedQuery`); `resolve_codegraph_dir`
  already rejects a leading-`-` segment (argv-flag injection) via a positive allow-list. The runtime
  execution-containment lands at Phase 4.2.

---

## Findings

**None.** No critical, high, medium, or low security finding in the Phase-1 contract surface.

The contract layer is fail-closed by construction at every safety seam, parse-don't-trust at every
boundary, and the safety-critical controls are verified live (not merely inspected). No
trust-boundary violation, no bypass surface, no unvalidated external path, no fail-open default.

## Fork-gate verdict: **CLEAR**

No critical/HIGH trust-boundary finding. The fork is not blocked on security. The two deferred
runtime proofs (D-A13, D-A14) are confirmed tracked fork obligations, not gaps.
