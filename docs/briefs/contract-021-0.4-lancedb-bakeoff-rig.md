# /tdd brief — lancedb_maintenance_bakeoff_rig

## Feature
Build the **reusable LanceDB maintenance-contract bake-off RIG** (Phase-0 spike 0.4, O-LANCE-BAKEOFF) —
a measurement harness that reports `optimize()` latency, index-build peak RAM, and steady-state disk
growth (versions + transactions) for the §6 maintenance contract, driven by a representative
synthetic multi-repo corpus. This slice delivers **scope B** (owner-approved, D-A17): the **reusable
rig + real measurement instrumentation + a documented methodology + best-effort local numbers against
a `Fake` maintenance target**. The **authoritative real reference-Mac bake-off** (real `lancedb` + a
real embedding model + a real multi-repo corpus) is an explicit **Phase-3 carry**, NOT this slice — so
the O-LANCE-BAKEOFF acceptance unknown is *deferred, not dropped*. No new runtime dependency is added.

## Use case + traceability
- **Task ID:** 0.4 (Phase-0 spike — O-LANCE-BAKEOFF; reusable rig the later phases assert against)
- **Architecture sections it implements:** `ARCHITECTURE.md §6` (LanceDB store & **maintenance contract** —
  `optimize()` after each upsert batch + monitor `index_stats().num_unindexed_rows ≈ 0`; scheduled
  `cleanup_old_versions()`; git-SHA version tags GC-exempt; single-writer; RAM-bounded batched index
  builds), `§24`/`§26` (the pre-build spike register — O-LANCE-BAKEOFF "maintenance-contract invisibility").
- **Related context:**
  - **The precedent to MIRROR: spike 0.1's rig** `ci/eval/redaction_fuzz/` (read its `README.md` + `types.py`
    first). Same shape: a standalone, dependency-free measurement rig with a `types.py` (record schemas +
    a `@runtime_checkable` target Protocol), a corpus generator, a `harness.py` with PROPOSED envelope
    constants + a CLI entry, a reference **Fake** (`stub_redactor.py` ↔ here `fake_store.py`) that validates
    the harness wiring, and a `test_harness_infra.py`. The real backend (there: the 2.3 redactor; here:
    real `lancedb`) lands later and is run through the SAME rig.
  - **D-A17 (owner-approved, do NOT re-decide):** scope B. The authoritative real-hardware bake-off defers
    to Phase 3; this slice ships the rig + Fake-target baseline + methodology. Don't pull in `lancedb`.
  - **The "invisible" budget numbers are PROPOSED here, not authoritative** — exactly like 0.1's
    `PROPOSED_RECALL_FLOOR`. The real ceilings get set from the Phase-3 real run on the reference Mac
    (Apple-Silicon M-series, 16–32 GB). This slice names them as PROPOSED constants.
  - LESSON 1 (Protocol + real + Fake double), Task 1.1 (the Clock/Seed determinism posture — the rig uses
    a seeded RNG + an injectable monotonic clock so its measurements are reproducible/testable).

## Acceptance criteria (what "done" means)
- [ ] `MaintenanceTarget` is a `@runtime_checkable Protocol` capturing the §6 maintenance operations
      (`upsert_batch`, `optimize`, `index_stats`, `cleanup_old_versions`, a dataset-path accessor for disk
      measurement, a version-count accessor); `FakeMaintenanceStore` satisfies `isinstance(..., MaintenanceTarget)`
      and performs real (if trivial) in-memory work so the instrumentation produces real numbers.
- [ ] **Corpus generator is reproducible:** same seed → byte-identical corpus (repo count, chunk counts,
      chunk sizes); a different seed → a different corpus. Parameterized by `n_repos`, `chunks_per_repo`,
      and a chunk-size distribution, with a documented default "representative portfolio" profile.
- [ ] `run_bakeoff(target, corpus)` returns a `BakeoffReport` populating: `optimize()` latency, peak
      index-build RAM, steady-state disk growth across version accumulation, AND a post-`optimize()`
      `num_unindexed_rows == 0` check (§6 monitor — post-write rows must not be left on a flat scan).
- [ ] **Measurement instrumentation is REAL and unit-tested** (so it is ready to swap onto real `lancedb`):
      the latency meter captures a known injected elapsed delta (monotonic-clock delta) within tolerance;
      the RAM meter (`tracemalloc` peak, stdlib — no new dep) captures a known allocation; the disk meter
      matches a known on-disk byte total for a temp dataset dir.
- [ ] `BudgetEnvelope.gate_pass(report)` returns `False` when any metric exceeds its ceiling, `True`
      within — the ceilings are named constants (`PROPOSED_*`) documented as PROPOSED-pending-the-Phase-3
      real run (mirroring 0.1's PROPOSED envelope).
- [ ] **Best-effort local numbers:** the rig runs end-to-end against `FakeMaintenanceStore` and records a
      baseline `BakeoffReport` (the analogue of 0.1's stub-baseline table); `README.md` documents the
      measurement methodology + states the authoritative real-`lancedb` reference-Mac run is a **Phase-3 carry**.
- [ ] Runnable as a **CLI** (`python -m ci.bench.lancedb_maintenance.harness` [`--verbose`]) AND importable
      (`run_bakeoff`, the `PROPOSED_*` constants) for the Phase-3 real run to drive a real `MaintenanceTarget`.
- [ ] All harness-infra tests in `ci/bench/lancedb_maintenance/test_harness_infra.py` pass.
- [ ] `/preflight` clean — run the **canonical** gate visibly (`uv run mypy .`, never `mypy core` — D-A3; LESSON 5).
- [ ] Cross-doc invariant: **none** (a bench rig — like 0.1; no `core/` contract touched). The PROPOSED §6
      budget envelope is an **Architecture-doc-note candidate** flagged at Step 9 (fold real ceilings into
      §6 / the perf baseline once Phase-3 measures them), not a frozen invariant in this slice.

## Wiring / entry point (Step 7.5)
**none — wiring lands in Phase 3** (the maintenance-contract task, where real `lancedb` exists). This is a
reusable bench RIG exactly like spike 0.1's fuzz harness: it has no `core/` production caller in Phase 0.
Its "entry points" are (a) the CLI `python -m ci.bench.lancedb_maintenance.harness` (runs end-to-end
against the Fake) and (b) `run_bakeoff(target, corpus)`, which Phase 3 imports and drives against a real
`lancedb`-backed `MaintenanceTarget`. **Reachability in Phase 0 = the CLI runs against the Fake + the
harness-infra tests pass** (the Fake satisfying `MaintenanceTarget` + the real instrumentation verified).

## Files expected to touch
**New (mirror `ci/eval/redaction_fuzz/`'s layout):**
- `ci/bench/lancedb_maintenance/__init__.py` — package header (anchor §6; O-LANCE-BAKEOFF; "rig, not the real run").
- `ci/bench/lancedb_maintenance/types.py` — `MaintenanceMetric`/`BakeoffReport`/`BudgetEnvelope` record
  schemas + the `MaintenanceTarget` `@runtime_checkable` Protocol + the metric enum.
- `ci/bench/lancedb_maintenance/corpus.py` — the seeded synthetic multi-repo corpus generator.
- `ci/bench/lancedb_maintenance/harness.py` — `run_bakeoff(...)` + the `PROPOSED_*` envelope constants +
  the real measurement instrumentation (latency/RAM/disk) + the CLI entry point.
- `ci/bench/lancedb_maintenance/fake_store.py` — ⚠ REFERENCE FAKE only — a deterministic in-memory
  `MaintenanceTarget` that validates harness wiring; **NOT** real `lancedb`.
- `ci/bench/lancedb_maintenance/test_harness_infra.py` — the pytest suite (run under the `core/` uv env, as 0.1 does).
- `ci/bench/lancedb_maintenance/README.md` — purpose, layout, usage, the PROPOSED budgets, the methodology,
  and the **Phase-3 authoritative-run carry** note.

If implementation needs files beyond this list, **flag at Step 2.5** before going GREEN.

## RED test outline (Step 2) — `ci/bench/lancedb_maintenance/test_harness_infra.py`
1. **`test_maintenance_target_protocol_conformance`** — `assert isinstance(FakeMaintenanceStore(), MaintenanceTarget)`.
   - Why: LESSON 1 — the Fake structurally satisfies the runtime_checkable target the Phase-3 real store also must.
2. **`test_corpus_reproducible_with_seed`** — same seed → identical corpus; different seed → different.
   - Why: Task 1.1 determinism posture — a bench input must be reproducible run-to-run.
3. **`test_corpus_profile_shape`** — the generated corpus honors requested `n_repos` × `chunks_per_repo`
   and the size-distribution bounds.
   - Why: §6 / the 0.4 task — a *representative multi-repo* corpus, not a degenerate one.
4. **`test_latency_meter_captures_elapsed`** — the latency instrument measures a known injected delay
   (monotonic-clock delta) within tolerance.
   - Why: the measurement must be REAL (ready to read real `optimize()` latency in Phase 3), not faked.
5. **`test_ram_meter_captures_allocation`** — the `tracemalloc`-based peak meter captures a known allocation.
   - Why: §6 RAM-bounded index builds — the rig must really measure peak build RAM.
6. **`test_disk_meter_matches_on_disk_bytes`** — the disk meter sums a known on-disk byte total for a temp dir.
   - Why: §6 steady-state disk (versions + transactions) must be really measured.
7. **`test_run_bakeoff_report_fields`** — `run_bakeoff(Fake, corpus)` returns a `BakeoffReport` with
   latency/RAM/disk populated AND `num_unindexed_rows == 0` after `optimize()`.
   - Why: §6 maintenance contract — `optimize()` after the batch + the `num_unindexed_rows ≈ 0` monitor.
8. **`test_budget_gate_pass_and_fail`** — `gate_pass` is `True` within the PROPOSED ceilings and `False`
   when a metric exceeds one.
   - Why: the "maintenance-contract invisible" envelope evaluation (the rig's gate, like 0.1's `gate_pass`).
9. **`test_cleanup_old_versions_gc_exempts_sha_tags`** — the Fake's `cleanup_old_versions()` removes old
   versions but GC-EXEMPTS git-SHA version tags.
   - Why: §6 "git-SHA version tags GC-exempt → double as the canonical SHA" — the rig models the contract
     sub-rule the Phase-3 real run must honor.

## Cross-doc invariant impact (implementer flags at Step 9; orchestrator writes the docs)
- **Model field changes:** none — no `core/` contract is touched. The rig's `types.py` are bench-local
  record schemas (like 0.1's), not Appendix-A models.
- **Orchestrator doc rows to write hot:** none in `core/CLAUDE.md`. **Architecture-doc-note candidate**
  (Step 9): the PROPOSED §6 maintenance budget envelope — recommend folding the *real* ceilings into §6 /
  the perf baseline once Phase 3 measures them. (Orchestrator writes the note; no field change now.)
- **Shared-contract seam touched?** **No** — this is `ci/` bench tooling above `core/`; it must not be
  imported BY `core/` (the one-way import rule). No cross-track contract model, so no schema-snapshot test applies.

## Things to flag at Step 2.5
1. **`MaintenanceTarget` Protocol shape — minimal §6-operation set?** My default vote: a minimal
   `@runtime_checkable Protocol` — `upsert_batch(rows)`, `optimize()`, `index_stats() -> {num_unindexed_rows, ...}`,
   `cleanup_old_versions(keep)`, `dataset_path() -> Path`, `num_versions() -> int`. Rationale: that's exactly the
   §6 maintenance surface, and it's the contract the Phase-3 real `lancedb` adapter implements — keep it minimal
   so the swap is clean. Push back if a metric needs an op I missed.
2. **Standalone seeded RNG vs import `core`'s `Seed`/`Clock`?** My default vote: **standalone** — accept an
   injectable `seed: int` + a monotonic-clock callable, like 0.1 stayed dependency-free. Rationale: keeps the rig
   importable without dragging `core/` into `ci/`, matches the 0.1 precedent, and the determinism is still testable.
   (Counter-vote acceptable: `ci/` may import `core/` since the dependency points the allowed way — but standalone
   is the precedent + the lower-coupling choice.)
3. **Metric-capture mechanism (no new dep — scope B).** My default vote: latency = monotonic-clock delta;
   RAM = `tracemalloc` peak (stdlib); disk = a dir-walk byte sum over the dataset path. Rationale: all stdlib,
   no `psutil`/`lancedb` dependency, and each is unit-testable against a known quantity (tests 4–6).
4. **PROPOSED budget ceilings — what values?** My default vote: name conservative PLACEHOLDER ceilings as
   `PROPOSED_*` constants (e.g. an `optimize()` latency ceiling, an index-build RAM ceiling, a steady-state
   disk-growth ratio ceiling) flagged in-docstring as **PROPOSED, pending the Phase-3 real reference-Mac run** —
   exactly like 0.1's `PROPOSED_RECALL_FLOOR`. The authoritative numbers are set from the real run. Rationale:
   the spike *proposes* the envelope; it does not finalize a hardware budget agent-only (and per D-A17 the real
   numbers are a Phase-3 carry). Surface the proposed values at Step 9 for the §6 Architecture-doc note.
5. **Corpus default profile — what's "representative"?** My default vote: a parameterized generator with a
   documented default (e.g. several synthetic repos × a realistic chunk count each, with a code/doc-like chunk-size
   distribution), seeded + reproducible. Rationale: "representative" is the spike's judgement call; make it explicit
   + tunable so the Phase-3 real run can scale it up against a real portfolio.

## Dependencies + sequencing
- **Depends on:** Task 1.1 (the determinism-seam posture — the rig uses a seeded RNG + injectable monotonic clock;
  landed). The 0.1 rig (`ci/eval/redaction_fuzz/`) as the structural precedent (landed). **No `core/` contract
  dependency; no new runtime dependency** (scope B explicitly defers `lancedb`).
- **Blocks:** the **Phase-3 maintenance-contract task** — the authoritative real reference-Mac bake-off run reuses
  this rig (swaps the Fake for a real `lancedb`-backed `MaintenanceTarget` + sets the real budget numbers). Per
  D-A17 this is the deferred-not-dropped O-LANCE-BAKEOFF acceptance carry.

## Estimated commit count
**1.** The rig is one cohesive logical unit (mirrors 0.1, which landed as one rig). No safety invariant is in the
slice, so no mandatory split. If the corpus generator grows large enough to warrant its own commit, flag at
Step 2.5 — otherwise one focused `feat(bench): …`-style commit (orchestrator authors the message at Step 9).

## Lessons-logged candidates anticipated
- **Convention candidate** — "A reusable measurement RIG builds its REAL instrumentation + a Fake target now, and
  PROPOSES its budget envelope as named `PROPOSED_*` constants; the authoritative numbers land where the real
  backend lands. Never bake a real-hardware budget number into the rig."
- **Architecture-doc-note candidate** — the PROPOSED §6 maintenance budget envelope (latency / RAM / disk
  ceilings for "invisible"); fold the real ceilings into §6 / the perf baseline once Phase-3 measures them.
- **Future TODO — phase (Phase 3):** the authoritative real reference-Mac bake-off run (real `lancedb` + a real
  embedding model + a real multi-repo corpus) — the O-LANCE-BAKEOFF acceptance unknown is **deferred, not dropped**
  (owner D-A17). Carry into the Phase-3 maintenance-contract task.

## How to invoke
1. Read this brief end-to-end — esp. "Things to flag at Step 2.5" (5 design questions, default votes pre-loaded).
   Read `ci/eval/redaction_fuzz/README.md` + `types.py` first — this rig mirrors that one.
2. Run **`/tdd lancedb_maintenance_bakeoff_rig`** in the implementer session.
3. **Step 0 (Restate)** — confirm the restatement matches the Feature line (rig + Fake + methodology = scope B; real
   run is a Phase-3 carry).
4. **Step 1 (Identify files)** — confirm against "Files expected to touch."
5. **Step 2.5** — send the test-design write-up + answer the 5 design questions (take defaults or push back). Wait
   for `APPROVED.` before GREEN.
6. **Step 9** — surface the PROPOSED §6 budget envelope (Architecture-doc note) + the Phase-3 carry + anything
   beyond the anticipated lessons candidates.
