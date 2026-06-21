# contract-007 — 2026-06-20 — Phase 0 spike 0.4: LanceDB maintenance-contract bake-off rig

- **Phase:** 0 (Pre-build spikes). Task **0.4** (O-LANCE-BAKEOFF — the maintenance-contract bake-off RIG, scope B).
- **Track:** contract (worktree `project-brain-contract`, branch `track/contract`).
- **Predecessor session:** [contract-005 (Phase 1.5 + 1.6)](contract-005-2026-06-20-phase1.5-boundary-contracts-and-1.6-hardening-sweep.md) · orchestrator handoff [contract-006](contract-006-2026-06-20-phase1.5-1.6-orchestrator-handoff.md)
- **Successor session:** _(next implementer session — post-fork-gate, after the merge + `/team-end`)_

## Why this session existed

The fresh full-runway team's stretch to the **fork gate**. Phase 1 (1.1–1.6) was frozen + pushed last
round (suite 232/232). The remaining before-fork work was the two Phase-0 spikes: **0.3** (O-FED, federation
cross-repo resolution — handled orchestrator-side as an investigation) and **0.4** (O-LANCE-BAKEOFF, the
LanceDB maintenance-contract bake-off rig — **this session**). 0.4 was the **last Phase-0 spike**; after it,
the orchestrator runs `/orchestrate-end` → `/phase-exit 1` → merge `track/contract` → `main` = the fork gate.

This doc covers **0.4 only** (per the orchestrator: 0.3 federation was its own orchestrator-side investigation).

## What was built

A reusable, dependency-free **measurement RIG** for the `ARCHITECTURE.md §6` LanceDB maintenance contract,
mirroring spike 0.1's `ci/eval/redaction_fuzz/` rig. **Scope B (D-A17):** the rig + REAL stdlib
instrumentation + a documented methodology + a best-effort local baseline against a `Fake` target. The
**authoritative real reference-Mac bake-off** (real `lancedb` + real embedding model + real multi-repo
corpus) is an explicit **Phase-3 carry — deferred, not dropped.** No new runtime dependency.

### Files created (all under `ci/bench/lancedb_maintenance/`)
- `__init__.py` — package header (anchor §6; O-LANCE-BAKEOFF; "rig, not the real run"; SAFETY/NETWORK/DEP notes).
- `types.py` — `MaintenanceMetric` StrEnum; `CorpusChunk`/`Corpus`/`IndexStats`/`BakeoffReport`/`BudgetEnvelope`
  frozen records; the `MaintenanceTarget` `@runtime_checkable` Protocol (the §6 op surface the Phase-3 real
  adapter implements; `upsert_batch` carries the optional git-SHA version tag). Bench-local schemas — **not**
  Appendix-A models.
- `corpus.py` — seeded synthetic multi-repo corpus generator (`random.Random(seed)` → reproducible) + the
  documented default "representative portfolio" profile (5 repos × 200 chunks, ASCII text ∈ [128,2048]B).
- `harness.py` — `run_bakeoff()` + REAL stdlib instrumentation (`measure_latency_ms` monotonic-delta /
  `measure_peak_ram_bytes` tracemalloc / `measure_dir_bytes` dir-walk) + the `PROPOSED_*` envelope constants
  (5000ms / 2GB / 5GB) + `print_report` + the CLI `main()`.
- `fake_store.py` — `FakeMaintenanceStore` REFERENCE FAKE (deterministic in-memory + temp-dir double that
  writes real bytes; **not** real `lancedb`); models the §6 unindexed-rows monitor + GC-exempt SHA tags.
- `test_harness_infra.py` — 15 out-of-band pytest tests (run under the `core/` uv env, as 0.1 does).
- `README.md` — purpose, layout, **measurement methodology**, PROPOSED budgets, and the **Phase-3
  authoritative-run carry** note (D-A17), made unmissable per the orchestrator/lead directive.

### Files modified
- None outside the new rig directory. No `core/` file touched (the rig is `ci/` tooling above `core/`; the
  one-way `core ⊥ ci/` import rule holds both directions — confirmed by the security review).

## Decisions made

- **`MaintenanceTarget` Protocol shape** — minimal §6 op set (`upsert_batch`/`optimize`/`index_stats`/
  `cleanup_old_versions`/`dataset_path`/`num_versions`), with `upsert_batch(rows, sha_tag=None)` modelling
  git-SHA version-tagging at version-creation rather than a separate `tag_version` method (keeps the Phase-3
  swap surface minimal + cleanly backs the GC-exempt assertion). Orchestrator-approved at Step 2.5.
- **Standalone determinism** — a standalone seeded `random.Random(seed)` + an injectable monotonic-clock
  callable; the rig does **not** import `core/` (0.1 precedent, lower coupling). Approved.
- **stdlib-only instrumentation** — latency = monotonic delta; RAM = `tracemalloc` peak; disk = dir-walk byte
  sum (no `psutil`/`lancedb` dep; each unit-tested against a known quantity). Approved.
- **`num_unindexed_rows == 0` folded into `gate_pass`** — the §6 post-optimize monitor is a real contract
  failure, so it gates alongside the three metric ceilings (a §6 strengthening; orchestrator endorsed).
- **Review-driven fidelity fix: the RAM meter spans ingest + `optimize()`** — the real `lancedb` index build
  RAM lives in `optimize()`, not ingest; wrapping only ingest would read ~0 on the real Phase-3 target. The
  meter now spans the whole ingest+optimize window (times `optimize()` within it). Orchestrator confirmed this
  is the right call.

## Decisions explicitly NOT made (deferred)

- **The authoritative real-hardware budget numbers** — set in Phase 3 from the real reference-Mac run, not
  agent-side here (D-A17). The `PROPOSED_*` ceilings are placeholders, flagged as such in-docstring + README.
- **CLI argparse upper-bound validation** (`--n-repos`/`--chunks-per-repo`) — deferred; a local operator-facing
  bench tool, not a trust boundary (security review: low, not in-scope acceptance work). Orchestrator accepted.
- **`BakeoffReport.metric()` exhaustiveness** on a future 4th `MaintenanceMetric` value — extensibility nit;
  deferred (KeyError on a not-yet-existent enum value).

## TDD compliance

- **Core slice (the 11 primary tests): clean strict RED→GREEN.** Step 2.5 test-design write-up sent + approved
  before any implementation; RED confirmed for the right reason (`ModuleNotFoundError`); GREEN after.
- **Process note (not a violation of the slice):** the **4 review-driven hardening tests** (symlink-skip,
  outer-tracemalloc preservation, `cleanup` keep=0, negative-keep rejection) were added **together** with their
  fixes during the Step-8 review fold rather than as a separate watched-RED run. Each asserts behavior the
  pre-fix code would have failed (symlink double-count, outer-session teardown, negative-keep inversion) or pins
  a previously-untested edge (keep=0). Suite re-confirmed GREEN (15/15); **no production code is left
  uncovered.** Recorded here for transparency.

## Reachability

- **The rig is reachable from** (a) the CLI `python -m ci.bench.lancedb_maintenance.harness` (runs end-to-end
  against the Fake — verified: 4 repos × 300 chunks → 10 versions, gate PASS, rc=0) and (b) `run_bakeoff(...)`
  imported by the Phase-3 maintenance-contract task to drive a real `lancedb`-backed `MaintenanceTarget`.
- **Not wired into `core/` production — by design.** Per the brief (§Wiring), Phase-0 reachability = the CLI
  runs against the Fake + the harness-infra tests pass; production wiring lands in Phase 3 where real `lancedb`
  exists. This is a documented Phase-3 carry, **not** a silent tested-but-unwired gap.

## Open follow-ups

Step-9 categorized list (routed hot to the orchestrator; it writes the docs at `/orchestrate-end`):
- **ARCH-DOC NOTE** → the PROPOSED §6 maintenance budget envelope (optimize latency 5000ms · index-build RAM
  2GB · steady-state disk 5GB + the `num_unindexed==0` monitor). Fold the **real** ceilings into §6 / the perf
  baseline once Phase 3 measures them.
- **FUTURE TODO (Phase 3)** → the authoritative real reference-Mac bake-off run: swap the Fake for a real
  `lancedb`-backed `MaintenanceTarget`, reuse this rig unchanged, set the authoritative budget numbers. The
  O-LANCE-BAKEOFF acceptance unknown is **deferred, not dropped** (D-A17). Documented in README "What Phase 3
  must do."
- **CONVENTION CANDIDATE** → "A reusable measurement RIG ships REAL instrumentation + a Fake target now and
  PROPOSES its budget envelope as named `PROPOSED_*` constants; the authoritative numbers land where the real
  backend lands — never bake a real-hardware budget into the rig." (Orchestrator routing: → LESSON 18 + the
  `core/CLAUDE.md` index.)
- **CROSS-DOC INVARIANT change: NONE.** No `core/` contract touched; no schema-snapshot applies.

## How to use what was built

```bash
# Rig validation (out-of-band, under the core/ uv env — like spike 0.1):
cd project-brain-contract/core
uv run python -m pytest ../ci/bench/lancedb_maintenance/test_harness_infra.py -v

# Fake baseline (CLI):
cd project-brain-contract
python -m ci.bench.lancedb_maintenance.harness --verbose

# Phase 3: import run_bakeoff + DEFAULT_ENVELOPE, drive a real lancedb-backed MaintenanceTarget,
# set the authoritative ceilings. See ci/bench/lancedb_maintenance/README.md "What Phase 3 must do".
```

**Round seal:** slice commit `ad8972f` (the 7 rig files) + this session doc. _(Orchestrator's `/orchestrate-end`
round commit carries the 0.3 federation spike doc + the Step-9 doc routing + push.)_
