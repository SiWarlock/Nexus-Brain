# spine-002 — `add` ingest orchestration + ★HostPort §14 runtime proof (2.4 + 2.S)

- **Date:** 2026-06-21
- **Track / Phase:** spine · Phase 2 (Ingestion + Redactor) — the 2.4 + 2.S bundle; Phase 2 SEALED (`/phase-exit 2` CLEAR)
- **Predecessor:** [spine-001-2026-06-21-phase2-ingest-surfaces.md](spine-001-2026-06-21-phase2-ingest-surfaces.md)
- **Successor:** _(none yet)_
- **Round commits (track/spine):** `20ac95d` (2.S ★SAFETY) · `2b36fad` (2.4) · this session doc commit · (+ orchestrator `/orchestrate-end` round-seal)
- **Brief:** `docs/briefs/spine-005-2.4-2.S-add-pipeline-hostport-proof.md`

## Why this session existed

Phase 2's ingest *front* (2.1 discover/classify, 2.2 chunk, 2.3 redactor) had landed as pure functions with their production reachability deferred. This session built the **`add` orchestration** that wires them into one production path AND landed the cardinal **Key-safety-rule-#4** proof (Task 2.S) — the real `StandaloneHost` (the first `core/` module that performs an FS mutation) plus the §14 INV-allowlist *runtime* per-mutator proof. Acceptance(2)-gated: Phase 2 could not close without 2.S. Owner-locked **Option C** for the §7 payload shape; `security-reviewer` mandatory on both commits.

## What was built

### Files created
- **`core/ingest/pipeline.py`** — the `add` orchestration: `discover → classify → chunk_docs/chunk_code → redact(persist) → embed → assemble frozen Chunk+Anchor → write manifest via HostPort.perform`. Idempotent, R-PARTIAL, atomic no-half-swap. Helpers: `_ingest_file` (per-file error boundary), `_sanitize_content` (Trojan-Source strip), `_recipe_sha` (v0 generation marker), `_build_manifest`, `_write_manifest`; `AddResult`/`_Ingested` NamedTuples.
- **`core/tests/ingest/test_pipeline.py`** — 11 unit/integration tests for 2.4 (empty repo, full pipeline assembly, redact-before-embed, manifest-via-HostPort, artifact derivation, idempotency ×2, malformed-skip, Trojan-bidi strip, atomic no-half-swap, runtime-mutation-via-perform).

### Files modified
- **`core/ports/host.py`** — real `StandaloneHost` adapter (atomic `mkstemp`(O_EXCL)+`os.replace` write, realpath containment, fail-closed authorize/perform with capability re-check + unhandled-cap fail-close; default `capabilities()={own_store_write}`). Added `StoreWritePayload{rel_path: IdentityStr, content: bytes}` (frozen, extra-forbid) and optional `payload: StoreWritePayload | None` on `HostIntent`/`HostAction` (owner-locked **Option C**, additive).
- **`core/tests/ports/test_host.py`** — +14 tests/assertions: `StandaloneHost` conformance, fail-closed authorize, perform capability-recheck, atomic write, path-escape (incl. symlinked component), runtime proof, the unhandled-allowlisted-cap fail-close (**test 25**, orchestrator ADD), updated Intent/Action/Payload schema-snapshots; **hardened the §14 tripwire scanner** (`_scan_source` + `_module_aliases`/`_environ_names`/`_getattr_hit`/`_is_environ`/`_session_state_hits`) to catch module-aliasing, getattr/dynamic-dispatch, and session-state writes (`os.environ[...]`/`.update`/`pop`/`putenv`/`unsetenv`/`del`, incl. the `from os import environ` form).

## Decisions made

- **`StoreWritePayload.content` = `bytes`, NOT `TextStr`** (Step-2.5 Q1; deviated from the brief default, orchestrator APPROVED). `TextStr`'s `TEXT_MAX_LEN=8192` would reject a realistic manifest; a file is fundamentally bytes; and `bytes` avoids a later str→bytes widen when 3.1's binary LanceDB write lands.
- **Default `StandaloneHost.capabilities()` = `{OWN_STORE_WRITE}`** (orchestrator refinement): the host offers only the capability it handles, so authorize+perform stay consistent. An EXPLICIT empty allowlist (`StandaloneHost(root, [])`) is the "denies all" case; an allowlisted-but-unhandled cap fails CLOSED at `perform` (defense-in-depth, pinned by test 25).
- **Per-file content boundary = two coherent layers** (LESSON 16): NUL/C0/DEL self-reject at the chunker's `TextStr` boundary → caught → file skipped (the carry-forward pin's "catch the raise, degrade to skip"); Trojan-Source bidi/zero-width (valid per `TextStr`) are STRIPPED pre-chunk so they never reach a chunk. Artifact emitted only for a file producing ≥1 chunk.
- **v0 `recipe_sha` generation marker** (Step-2.5 Q4): deterministic sha256 over sorted `(path, raw-content-hash)` pairs, host-mediated (no git shell-out). Reused for manifest `ingested_from_sha`/`lance_version_tag` + chunk/anchor `last_resolved_sha` + chunk `ingested_from_sha`.
- **Idempotency key** (Q5): `ManifestArtifact.content_hash = sha256(raw file bytes)`, per-file. `Chunk.content_hash` is the redacted-chunk-text hash (a distinct per-chunk identity).
- **Review-driven in-slice hardening:** unpredictable `mkstemp` temp (closes a leaf-symlink-precreate vector) + cleanup-on-failure (closes a leaked-temp); the `from os import environ` scanner evasion the code-quality-reviewer found.

## Decisions explicitly NOT made (deferred)

- **§7 payload cross-doc rows** — the `HostIntent`/`HostAction` payload growth + `StoreWritePayload` need the §7 Appendix-A row + `core/CLAUDE.md` HostPort cross-doc row. Flagged at Step 9; **orchestrator writes hot at `/orchestrate-end`** + raises the cross-track Finding to the lead (shared safety §2.5-seam contract growth).
- **Parent-dir-swap TOCTOU (★SAFETY Finding → Phase-8.2 carry).** `StandaloneHost` resolves the target then writes; a same-uid attacker swapping a parent component to a symlink between resolve and write escapes the root. In-slice mitigations landed (mkstemp O_EXCL leaf; realpath containment test-pinned). Full fix = `dir_fd` + `O_NOFOLLOW` (or re-validate realpath immediately before `os.replace`). **Outside the declared §18/LBD-13 same-uid-trusted threat model** (stated non-goal) → routed by the orchestrator to the lead as a Phase-8.2 carry alongside `get_file` realpath-containment. Did NOT block `/phase-exit 2`.
- **Anchor-vs-sanitized-source (§8/§10 arch-note).** Stripping Trojan-bidi pre-chunk means anchors are accurate against the SANITIZED source, not the raw file — Phase-4 grounding/anchor-revalidation must revalidate against sanitized source (or re-sanitize on read). Orchestrator writes the note hot.
- **Real version-tag wiring (Phase-3 carry).** `ingested_from_sha`/`lance_version_tag`/`last_resolved_sha` carry the v0 `recipe_sha` placeholder now; the real LanceDB git-SHA version tag replaces it at 3.1. Chunk-level tombstone+replace idempotency = §12 (Phase 3).
- **Skipped-file observability (Phase-3).** The per-file boundary skips silently; wire an `ObservabilitySink` hook when the obs seam threads through ingest.
- **Context-augment** (`register="deep"` blurb) — reserved for the Phase-3 embedding path; v0 keeps `register="plain"`, `context_blurb=None`.

## TDD compliance

**Clean — final state is test-first with observed RED on both commits.** Process note (transparency): the `host.py` implementation was initially drafted *before* its tests; I caught this, **reverted `host.py` to HEAD**, wrote the tests, confirmed a clean RED (`ImportError: cannot import name 'StandaloneHost'` / `ModuleNotFoundError: ingest.pipeline`), then re-applied the implementation to GREEN — so the committed history is honest test-first. The Step-2.5 review gate ran (orchestrator APPROVED with one ADD = test 25). The review-driven `from os import environ` scanner fix shipped *with* its test assertions; the `mkstemp` hardening kept the existing atomic-write test green (its rare `os.replace`-failure cleanup branch is not separately pinned — see Open follow-ups).

## Reachability

- `discover` / `classify` / `chunk_docs` / `chunk_code` / `CatchableSetRedactor.redact` / `host.authorize` / `host.perform` — **reachable from `core/ingest/pipeline.py::add`** (their first production caller; closes the 2.1/2.2/2.3 declared deferral). Confirmed at Step 7.5 + by grep.
- `add` / `StandaloneHost` — reachable from tests this slice; user-facing production entry = **`nexus add <repo>` CLI = Phase 5 (§15)**, declared deferral (no CLI exists yet). Not a silent gap.
- The hardened §14 tripwire + the runtime-proof tests are live entry points landed this slice.

## Open follow-ups

- **[Cross-doc invariant — orchestrator territory]** §7 Appendix-A row + `core/CLAUDE.md` HostPort cross-doc row for the `payload`/`StoreWritePayload` growth (flagged Step 9; orchestrator writes hot).
- **[★SAFETY Finding → lead, Phase-8.2 carry]** parent-dir-swap TOCTOU on `StandaloneHost` containment (`dir_fd`/`O_NOFOLLOW`).
- **[Architecture-doc notes — orchestrator]** (a) §8 `add` Phase-2 scope; (b) §8/§10 anchor-vs-sanitized-source; (c) `Chunk.content_hash` (redacted) vs `ManifestArtifact.content_hash` (raw) distinction.
- **[Phase-3 carries]** real git-SHA version tag for `ingested_from_sha`/`lance_version_tag`/`last_resolved_sha`; chunk-level tombstone+replace (§12); skipped-file observability hook; `StoreWritePayload` → per-capability union widen at 3.x.
- **[LESSON candidates — orchestrator]** (i) "first FS mutator proves the chokepoint at runtime — a recording host + a hardened static scan (aliasing/getattr/session-state) upgrade a static tripwire to a runtime per-mutator proof"; (ii) "grow a frozen safety contract additively (optional payload, absent→None) — existing wire shapes still validate, snapshots stay green except the intended field."
- **[Test debt — minor]** the `StandaloneHost` write `os.replace`-failure cleanup branch (leaked-temp removal) is defensive and not separately unit-tested (hard to induce deterministically); the happy-path atomic write + no-leftover-temp IS pinned.

## How to use what was built

```python
from ingest.pipeline import add
from ports.host import StandaloneHost
# inject the determinism + provider seams (Fake* in tests; real adapters in the Phase-5 CLI)
result = add(repo_root, project_id="my-proj", host=StandaloneHost(repo_root),
             embedder=embedder, clock=clock, idgen=idgen, redactor=redactor)
# result.chunks / result.anchors (frozen records) + result.manifest (written to
# <root>/.project-brain/manifest.json via the HostPort chokepoint).
```
