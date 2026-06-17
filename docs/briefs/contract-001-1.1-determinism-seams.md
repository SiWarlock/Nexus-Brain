# /tdd brief — determinism_seams_clock_seed_idgen

## Feature
Define and freeze the two determinism-seam ports — `Clock` and `Seed`/`IdGen` — as
typed interfaces with a real adapter + a deterministic `Fake*` double each, and bootstrap
the `core/` Python package skeleton (uv · ruff · mypy --strict · pytest) they live in.
First slice of the project: it sets the ports-and-adapters pattern every later contract mirrors.

## Use case + traceability
- **Task ID:** 1.1
- **Architecture sections it implements:** `ARCHITECTURE.md §7` (ports & adapter contracts —
  `Clock` + `Seed/IdGen` are the C-15 deterministic test seams; every port is an Appendix-A
  freeze-before-fork contract).
- **Related context:** the seams are *injected*, never called inline — first consumers are §5
  (manifest `index_built_at` timestamp + id minting, lands in 1.2) and §10 (anchor revalidation
  reads time via `Clock`). §2.5 marks these as freeze-before-fork (the Phase-1 bottleneck). This
  is greenfield: `core/` currently holds only `CLAUDE.md` + `LESSONS.md` — no Python skeleton yet.

## Acceptance criteria (what "done" means)
- [ ] `core/` Python package skeleton exists: `core/pyproject.toml` (Python 3.12 · uv · pydantic v2 ·
      pytest · ruff · mypy --strict tool config) and the package is importable + test-discoverable.
- [ ] `Clock` port: `now() -> datetime` returns a timezone-aware UTC datetime; `monotonic() -> float`
      returns non-decreasing seconds. Real `SystemClock` + deterministic `FakeClock` (settable + advanceable).
- [ ] `IdGen` port: `new_id(kind: str) -> str` mints a unique id. Real `UuidGen` (globally unique);
      deterministic `FakeIdGen` (reproducible per-kind sequence; distinct kinds never collide).
- [ ] `Seed` port: `rng() -> random.Random` yields a seeded RNG. Real `SystemSeed` (OS entropy,
      non-deterministic); deterministic `FakeSeed(seed)` (same seed ⇒ identical draw sequence).
- [ ] Real + fake of each port satisfy the port type (structural/`isinstance` conformance) — proving
      DI substitutability (§7: one port, real adapter + named fake double).
- [ ] All unit tests in `core/tests/ports/` pass.
- [ ] `/preflight` clean (ruff + mypy --strict + pytest).
- [ ] Cross-doc invariant row authored by the orchestrator (Step-9 routing) — see Cross-doc section.

## Wiring / entry point (Step 7.5)
none — wiring lands in 1.2. These are foundational *injectable* seams with no production entry point
in this slice: the first real consumer is 1.2 (manifest `index_built_at` timestamp via `Clock`;
chunk/anchor id minting via `IdGen`), then anchor revalidation (§10) reads time via `Clock`.
Reachability this slice = exported from `core/ports/` + `core/testing/`; first consumed in 1.2.
(Stated so `spec-lint brief` and `/tdd` Step 7.5 see an explicit deferral, not a gap.)

## Files expected to touch
**New (package skeleton — bootstrap):**
- `core/pyproject.toml` — uv project; deps: `pydantic>=2`; dev: `pytest`, `mypy`, `ruff`; tool config:
  `[tool.ruff]`, `[tool.mypy] strict = true`, `[tool.pytest.ini_options]`. Python `3.12`.
- `core/ports/__init__.py`
- `core/testing/__init__.py`
- `core/tests/__init__.py` · `core/tests/ports/__init__.py`

**New (the slice):**
- `core/ports/clock.py` — `Clock` port + `SystemClock` real adapter.
- `core/ports/idgen.py` — `IdGen` + `Seed` ports + `UuidGen` / `SystemSeed` real adapters.
- `core/testing/fakes.py` — `FakeClock`, `FakeIdGen`, `FakeSeed` (1.4 extends this file with the
  provider/CodeGraph fakes + cassettes; create it here as the canonical test-double home).
- `core/tests/ports/test_clock.py` · `core/tests/ports/test_idgen.py`

If implementation needs files beyond this list (e.g. a `core/uv.lock` from `uv sync`, a `core/.python-version`),
**flag at Step 2.5** before going GREEN.

## RED test outline (Step 2)
Tests in `core/tests/ports/test_clock.py`:
1. **`test_system_clock_now_is_tz_aware_utc`** — Asserts `SystemClock().now().tzinfo` is UTC-aware.
   - Why: §5/§10 timestamps + anchor revalidation must be tz-safe + deterministic to serialize.
2. **`test_system_clock_now_nondecreasing`** — Asserts two successive `now()` calls are non-decreasing.
   - Why: wall-clock sanity for freshness deltas.
3. **`test_system_clock_monotonic_nondecreasing`** — Asserts `monotonic()` is non-decreasing across calls.
   - Why: later-phase backoff/timeout budgets need a wall-clock-independent duration source (failure-mode recovery).
4. **`test_fake_clock_returns_set_time`** — Asserts `FakeClock(t0).now() == t0` (deterministic).
   - Why: C-15 determinism seam — reproducible time under test.
5. **`test_fake_clock_advance`** — Asserts `FakeClock(t0).advance(Δ)` makes `now() == t0 + Δ`.
   - Why: controllable time for anchor-revalidation/drift tests downstream.
6. **`test_clock_real_and_fake_conform`** — Asserts both `SystemClock` and `FakeClock` satisfy `Clock`.
   - Why: §7 — one port, real adapter + named fake double, DI-substitutable.

Tests in `core/tests/ports/test_idgen.py`:
1. **`test_uuidgen_new_id_unique`** — Asserts N (≥1000) `UuidGen().new_id("chunk")` values are all distinct.
   - Why: chunk/anchor/session ids (§5/§10) must be globally unique.
2. **`test_uuidgen_new_id_nonempty_str`** — Asserts `new_id("anchor")` returns a non-empty `str`.
   - Why: id-minting contract shape.
3. **`test_fake_idgen_reproducible_sequence`** — Asserts two fresh `FakeIdGen()` produce identical
   sequences for the same `kind` calls.
   - Why: C-15 determinism seam — reproducible ids under test (golden-set stability).
4. **`test_fake_idgen_distinct_kinds_no_collision`** — Asserts ids minted for `"chunk"` vs `"anchor"`
   never collide within one `FakeIdGen`.
   - Why: typed-id separation (precursor to the 1.3 IdKind enum).
5. **`test_fake_seed_reproducible_rng`** — Asserts `FakeSeed(42).rng()` and a second `FakeSeed(42).rng()`
   yield identical draw sequences.
   - Why: any future sampling/jitter draws from `Seed.rng()` and must be reproducible.
6. **`test_system_seed_varies`** — Asserts two `SystemSeed().rng()` instances diverge (entropy).
   - Why: real randomness is non-deterministic; fake is the deterministic counterpart.
7. **`test_idgen_seed_real_and_fake_conform`** — Asserts real+fake satisfy `IdGen` / `Seed`.
   - Why: §7 DI substitutability.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** none. These are *behavioral* ports (method protocols), not field-bearing
  Pydantic models.
- **§2.5-seam (shared-contract) model touched? → schema-snapshot test = N/A for 1.1.** The schema-snapshot
  test pins a model's *field-name set*; `Clock`/`Seed`/`IdGen` have no fields. The plan's task 1.1 is the
  only Phase-1 task that **omits** the `§2.5-seam → schema-snapshot test` parenthetical that 1.2–1.5 carry —
  so conformance is pinned *behaviorally* (real+fake satisfy the port) instead. **Step-2.5 question #6**
  surfaces the §7 "every port is freeze-before-fork" wording vs Appendix-A having no Clock/Seed/IdGen row.
- **Orchestrator doc rows to write hot (Step-9 routing, orchestrator territory):**
  - `core/CLAUDE.md` cross-doc invariants table → NEW row: determinism-seam ports `Clock` / `Seed` / `IdGen`
    (§7), real+fake, pinned by `core/tests/ports/test_clock.py` + `test_idgen.py` (written in this worktree).
  - `core/CLAUDE.md` lookup table → add `Ports (determinism seams) → ARCHITECTURE.md §7`.
  - `ARCHITECTURE.md` Appendix A → determinism-seam row decision (§7) — **routes to the integration checkout**
    (root tree, `main`), per the multi-track carve-out; not edited in this worktree.

## Things to flag at Step 2.5
1. **Python package layout / import root** (load-bearing — sets every import in the codebase). Options:
   (a) **flat, rooted at `core/`** — top-level packages `ports` / `model` / `testing`, tests under
   `core/tests/`, `cd core && uv run pytest`, import `from ports.clock import Clock`; matches the plan's
   literal file paths (`core/ports/clock.py`) + the `cwd = core/` convention. (b) single `nexus_brain`
   package (`core/nexus_brain/ports/clock.py`) — cleaner namespace but diverges from the plan's paths.
   My default vote: **(a) flat, rooted at `core/`** — faithful to the plan paths + cwd convention; least
   surprise for the downstream tracks reading those paths. Calling it out because it's hard to change later.
2. **Port definition style — `typing.Protocol` vs `abc.ABC`.** Default vote: **`typing.Protocol`
   (`@runtime_checkable` where a conformance test needs `isinstance`)** — idiomatic ports-and-adapters,
   fakes conform structurally without inheritance coupling. ABC if we want enforced `@abstractmethod`.
3. **Fake doubles location.** Default vote: **`core/testing/fakes.py`** (real adapters stay in
   `core/ports/*`) — keeps test doubles out of the production adapter surface while giving downstream
   tracks one importable `core.testing` home (1.4 extends it). Alt: co-locate fakes in the port module.
4. **`Clock` surface — `now()` only, or `now()` + `monotonic()`?** Default vote: **both** — freeze the
   seam once (Phase-1's whole point); a later phase's backoff/timeout budgets will want `monotonic()` and
   re-touching a frozen port later is the costly path.
5. **`IdGen` — `uuid4` vs sortable `uuid7`; `kind: str` vs the typed IdKind enum.** Default vote:
   **`uuid4` + `kind: str`** — the 11-EvidenceType / 22-IdKind enum is task 1.3's deliverable, so accept a
   `str` kind now to avoid a forward dependency; `uuid4` unless a consumer needs lexical ordering (none yet).
6. **Do these ports need Appendix-A enumeration / a snapshot?** Default vote: **no schema-snapshot
   (no fields); add the `core/CLAUDE.md` cross-doc row per the plan, and raise the Appendix-A
   determinism-seam-row question as an architecture-doc note** (does §7's "every port is freeze-before-fork"
   warrant an explicit Appendix-A row for the seam ports, or is the §7 prose sufficient?). Not slice-blocking.

## Dependencies + sequencing
- **Depends on:** none — 1.1 is the root of Phase 1.
- **Blocks:** 1.2 (manifest `index_built_at` via `Clock`; chunk/anchor id minting via `IdGen`), 1.3
  (anchor/provenance id minting), 1.4 (the ports + `core/testing/fakes.py` home it extends), and every
  downstream determinism path (anchor revalidation §10, drift ranking, eval golden-set reproducibility).

## Estimated commit count
**1.** One logical unit: the package skeleton + the two determinism-seam ports + their fakes + tests.
No safety-invariant *pin* is in this slice (the determinism seams *underpin* the grounding gate's
deterministic revalidation, but the ports themselves are not the gate), so no mandatory standalone split.

## Lessons-logged candidates anticipated
- **Convention candidate** — "Ports are `typing.Protocol`; every port ships a real adapter + a `Fake*`
  double (fakes live in `core/testing/`); inject via constructor." (The pattern 1.2–1.5 + all tracks mirror.)
- **Convention candidate (enforceable forbidden-pattern)** — "No direct wall-clock / entropy / RNG in
  `core`: never call `datetime.now()` / `uuid.uuid4()` / `random.*` inline — always via the
  `Clock`/`IdGen`/`Seed` seams." Candidate `pattern:` grep for the forbidden-patterns block.
- **Architecture-doc note candidate** — Appendix-A determinism-seam row (§7): enumerate `Clock`/`Seed`/`IdGen`
  explicitly, or rely on §7 prose?
- **Future TODO — operational** — sortable `uuid7` ids if registry/anchor ordering later benefits.

## How to invoke
1. **Read this brief end-to-end** — the Step-2.5 questions (esp. #1 package layout) need answers before GREEN.
2. **First slice of the session:** run `/session-start` to orient, then `/tdd determinism_seams_clock_seed_idgen`.
3. **Step 0 (Restate)** — confirm against the Feature line.
4. **Step 1 (Identify files)** — confirm against "Files expected to touch" (note the package-skeleton bootstrap).
5. **Step 2.5** — send the test-design write-up + answers to the six design questions (or take defaults).
6. **Step 9** — surface anything beyond the anticipated lessons-logged candidates.
