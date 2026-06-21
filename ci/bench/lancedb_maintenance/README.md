# LanceDB Maintenance-Contract Bake-off Rig — Spike 0.4

**Purpose:** De-risks the §6 LanceDB **maintenance contract** ("maintenance-contract
invisibility", O-LANCE-BAKEOFF) by providing a reusable rig that measures the metrics
the contract must stay inside — `optimize()` latency, index-build peak RAM, and
steady-state disk growth — for any `MaintenanceTarget`.

**Anchors:** `ARCHITECTURE.md §6` (LanceDB store & maintenance contract) · `§24`/`§26`
(pre-build spike register) · `DECISIONS.md D-A17` (scope B) · `D-25` (mandatory
maintenance contract) · `D-14` (git-SHA version tags).

> ## ⚠️ SCOPE — this is the RIG, not the authoritative run (D-A17)
>
> This slice ships **scope B**: the reusable rig + REAL stdlib instrumentation + a
> documented methodology + a best-effort **Fake-target** baseline. The PROPOSED budget
> ceilings here are **placeholders**, exactly like spike 0.1's `PROPOSED_RECALL_FLOOR`.
>
> **The AUTHORITATIVE real reference-Mac bake-off — real `lancedb` + a real embedding
> model + a real multi-repo corpus, on Apple-Silicon (16–32 GB) — is an explicit
> Phase-3 carry. It is DEFERRED, NOT DROPPED.** The O-LANCE-BAKEOFF acceptance unknown
> is retired there: Phase 3 swaps the Fake for a real `lancedb`-backed `MaintenanceTarget`,
> reuses this rig unchanged, sets the real budget numbers, and folds them into §6 / the
> perf baseline. No new runtime dependency is added in this slice (no `lancedb` import).

## What this is

A measurement harness parametrized on a `MaintenanceTarget` Protocol. Give it any target
(the reference Fake now; a real `lancedb`-backed adapter in Phase 3) and a synthetic
corpus, and `run_bakeoff(target, corpus)` returns a `BakeoffReport` with:

- **`optimize()` latency** (ms) — should be "invisible" after each upsert batch.
- **index-build peak RAM** (bytes) — §6 RAM-bounded batched index builds.
- **steady-state disk** (bytes) — versions + transactions on disk.
- **`num_unindexed_rows_after_optimize`** — the §6 monitor: post-write rows must not be
  left on a flat scan (`fast_search` silently excludes them).

`BudgetEnvelope.gate_pass(report)` evaluates the report against the PROPOSED ceilings
**and** the `num_unindexed_rows == 0` monitor.

## Module layout

```
ci/bench/lancedb_maintenance/
  __init__.py            — package + scope/anchor header
  types.py               — MaintenanceMetric enum; CorpusChunk/Corpus/IndexStats/
                           BakeoffReport/BudgetEnvelope records; the MaintenanceTarget Protocol
  corpus.py              — seeded synthetic multi-repo corpus generator (+ DEFAULT_* profile)
  harness.py             — run_bakeoff() + REAL instrumentation (latency/RAM/disk) +
                           PROPOSED_* envelope constants + CLI entry point
  fake_store.py          — ⚠ REFERENCE FAKE only — deterministic in-memory + temp-dir
                           MaintenanceTarget; validates rig wiring; NOT real lancedb
  test_harness_infra.py  — pytest suite (11 tests; run under the core/ uv env, as 0.1 does)
  README.md              — this file
```

## Measurement methodology

All instrumentation is **stdlib** (no new dependency, scope B) and **unit-tested against a
known quantity** so it is ready to read real numbers when swapped onto real `lancedb`:

| Metric | How it's measured | Unit test (known quantity) |
|---|---|---|
| `optimize()` latency | monotonic-clock delta around the call (`clock` injectable) | injected `10.0→10.25s` clock → `250 ms` |
| index-build peak RAM | `tracemalloc` peak across the batched ingest build | a known ~10 MB allocation → peak ≥ 8 MB |
| steady-state disk | dir-walk byte sum over `dataset_path()` | a temp dir of known bytes → exact sum |

**Determinism:** the corpus generator is driven by a seeded `random.Random(seed)` — the
same seed yields a byte-identical `Corpus`; the latency meter takes an injectable monotonic
clock. Both keep the rig reproducible and testable (Task 1.1 determinism posture). The rig
is standalone — it does **not** import `core/` (the one-way `core ⊥ ci/` import rule).

**Corpus default profile ("representative portfolio"):** `DEFAULT_N_REPOS = 5` repos ×
`DEFAULT_CHUNKS_PER_REPO = 200` chunks, ASCII chunk text sized in `[128, 2048]` bytes. This
is a judgement call for a small multi-repo portfolio; scale it up (`n_repos`,
`chunks_per_repo`, the size bounds) for the Phase-3 real run against a real portfolio.

## Usage

### As a pytest suite (rig validation)

```bash
cd project-brain-contract/core
uv run python -m pytest ../ci/bench/lancedb_maintenance/test_harness_infra.py -v
```

### As a CLI tool (Fake baseline)

```bash
cd project-brain-contract
python -m ci.bench.lancedb_maintenance.harness
python -m ci.bench.lancedb_maintenance.harness --verbose
python -m ci.bench.lancedb_maintenance.harness --seed 7 --n-repos 3 --chunks-per-repo 50
```

### Plugging in the real Phase-3 `lancedb` target

```python
from ci.bench.lancedb_maintenance.harness import run_bakeoff, DEFAULT_ENVELOPE
from ci.bench.lancedb_maintenance.corpus import generate_corpus
# from <phase-3 module> import LanceDbMaintenanceTarget  # the real MaintenanceTarget

target = LanceDbMaintenanceTarget(...)            # real lancedb-backed adapter
corpus = generate_corpus(seed=1, n_repos=20, chunks_per_repo=2000)  # scaled-up real profile
report = run_bakeoff(target, corpus)
assert DEFAULT_ENVELOPE.gate_pass(report)         # ← Phase 3 sets the AUTHORITATIVE ceilings
```

## PROPOSED budget envelope (placeholders — Phase-3 sets the real numbers)

| Metric | PROPOSED ceiling | Status |
|---|---|---|
| `optimize()` latency | 5 000 ms | PROPOSED — pending Phase-3 real reference-Mac run |
| index-build peak RAM | 2 GB | PROPOSED — pending Phase-3 real reference-Mac run |
| steady-state disk | 5 GB | PROPOSED — pending Phase-3 real reference-Mac run |
| `num_unindexed_rows` after `optimize()` | 0 (hard) | §6 monitor — a real contract failure |

The Fake baseline (tiny synthetic numbers) sits well inside these conservative ceilings —
which is the point: it proves the rig measures real quantities end-to-end without asserting
any real hardware budget. **The authoritative ceilings are an architecture-doc note to fold
into §6 / the perf baseline once Phase 3 measures them.**

## What Phase 3 must do (the carry)

1. Implement a real `lancedb`-backed `MaintenanceTarget` (real `upsert_batch`/`optimize`/
   `index_stats`/`cleanup_old_versions`/`dataset_path`/`num_versions`; `spawn` not `fork`;
   verify arm64 wheels in CI).
2. Run it through **this rig** against a real, scaled-up multi-repo corpus + a real
   embedding model on the reference Mac.
3. Set the **authoritative** budget ceilings from that run; fold them into `ARCHITECTURE.md`
   §6 / the perf baseline (replacing the PROPOSED placeholders).
4. Retire the O-LANCE-BAKEOFF acceptance unknown (D-A17 — deferred, not dropped).
